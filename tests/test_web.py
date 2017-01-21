import pytest
import requests
import random
import os
import sys
import json
import queue
import multiprocessing as mp
from flask import g
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.web as web
import dj_feet.core as core
import dj_feet.config as config
from dj_feet.pickers import Picker


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(web, 'im_alive', lambda: None)
    with web.app.app_context():
        yield web.start("1024", "/tmp/sdaas_input/", "/tmp/sdaas_output",
                        "localhost")

        stop_worker(g.queue, g.worker)


@pytest.fixture
def app_client(app):
    yield app.test_client()


def stop_worker(q, w):
    q.put((web.STOP, ))
    q.close()
    q.join_thread()
    w.join(15)

    if w.is_alive():
        w.terminate()
        assert False  # The worker should have been terminated.


class MyPicker(Picker):
    "A docstring"

    def __init__(self, param1):
        """Another docstring

        :param param1: Cool!"""
        pass


def test_setup(monkeypatch):
    my_post_request = MockingFunction()
    monkeypatch.setattr(requests, 'post', my_post_request)
    my_id = random.randint(0, 100000)
    my_addr = str(random.randint(0, 100000)) + "-this-is-me-" + str(my_id)

    with web.app.app_context():
        web.start(str(my_id), "/in", "/out", my_addr)
        stop_worker(g.queue, g.worker)
        assert web.app.config['INPUT_DIR'] == '/in'
        assert web.app.config['OUTPUT_DIR'] == '/out'

    assert my_post_request.called
    assert len(my_post_request.args[0][0]) == 1
    assert my_post_request.args[0][0][0] == my_addr + '/im_alive'

    data = my_post_request.args[0][1]['data']
    assert data['id'] == my_id
    assert 'MyPicker' in data['options']['Picker']
    assert 'param1' in data['options']['Picker']['MyPicker']['parts']
    assert data['options']['Picker']['MyPicker']['parts']['param1']['required']


@pytest.mark.parametrize("data", [({
    "Picker": {
        "name": "MyPicker",
        "options": [1, 2, 3, 4]
    }
})])
def test_start_music(monkeypatch, app_client, data):
    mocked_queue_put = MockingFunction()
    monkeypatch.setattr(mp.queues.Queue, 'put', mocked_queue_put)

    try:
        mocked_get_controller = MockingFunction(lambda: 'Controller')
        mocked_get_picker = MockingFunction(lambda: 'Picker')
        mocked_get_transitioner = MockingFunction(lambda: 'Transitioner')
        mocked_get_communicator = MockingFunction(lambda: 'Communicator')
        monkeypatch.setattr(config.Config, 'get_controller',
                            mocked_get_controller)
        monkeypatch.setattr(config.Config, 'get_picker', mocked_get_picker)
        monkeypatch.setattr(config.Config, 'get_transitioner',
                            mocked_get_transitioner)
        monkeypatch.setattr(config.Config, 'get_communicator',
                            mocked_get_communicator)

        response = app_client.post(
            '/start', data=json.dumps(data), content_type='application/json')
        other_res = []
        for _ in range(10):
            other_res.append(
                app_client.post(
                    '/start',
                    data=json.dumps(data),
                    content_type='application/json'))
    except Exception as exp:
        raise exp
    finally:
        monkeypatch.undo()

    assert response.status_code == 200
    assert json.loads(response.get_data(as_text=True))['ok']
    for res in other_res:
        assert res.status_code == 410
        assert not json.loads(res.get_data(as_text=True))['ok']

    assert mocked_queue_put.called
    assert mocked_queue_put.args[0][0][0][0] == web.START_LOOP
    assert mocked_queue_put.args[0][0][0][1] == [
        'Controller',
        'Picker',
        'Transitioner',
        'Communicator',
    ]

    assert mocked_get_controller.called
    assert mocked_get_picker.called
    assert mocked_get_transitioner.called
    assert mocked_get_communicator.called


@pytest.mark.parametrize("data", [({
    "Picker": {
        "name": "MyPicker",
        "options": [1, 2, 3, 4]
    }
})])
def test_start_music_in_full(monkeypatch, app_client, data):
    mocked_queue_put = MockingFunction()
    mocked_queue_get_nowait = MockingFunction(func=lambda: None, simple=True)
    monkeypatch.setattr(mp.queues.Queue, 'put', mocked_queue_put)
    monkeypatch.setattr(mp.queues.Queue, 'get_nowait', mocked_queue_get_nowait)

    try:
        mocked_get_controller = MockingFunction(lambda: 'Controller')
        mocked_get_picker = MockingFunction(lambda: 'Picker')
        mocked_get_transitioner = MockingFunction(lambda: 'Transitioner')
        mocked_get_communicator = MockingFunction(lambda: 'Communicator')
        monkeypatch.setattr(config.Config, 'get_controller',
                            mocked_get_controller)
        monkeypatch.setattr(config.Config, 'get_picker', mocked_get_picker)
        monkeypatch.setattr(config.Config, 'get_transitioner',
                            mocked_get_transitioner)
        monkeypatch.setattr(config.Config, 'get_communicator',
                            mocked_get_communicator)

        response = app_client.post(
            '/start', data=json.dumps(data), content_type='application/json')
    except Exception as exp:
        raise exp
    finally:
        monkeypatch.undo()

    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert not data['ok']

    assert mocked_get_controller.called
    assert mocked_get_picker.called
    assert mocked_get_transitioner.called
    assert mocked_get_communicator.called
    assert mocked_queue_put.called
    assert mocked_queue_put.args[0][0][0] is None
    assert mocked_queue_get_nowait.called
