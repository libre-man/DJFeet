import pytest
import requests
import random
import os
import sys
import json
import queue
import multiprocessing as mp
import pydub
from configparser import ConfigParser
from helpers import MockingFunction
from flask import Flask

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.pickers as pickers
import dj_feet.web as web
import dj_feet.core as core
import dj_feet.config as config
from dj_feet.pickers import Picker


@pytest.fixture
def my_flask():
    yield web.MyFlask(__name__)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(web, 'im_alive', lambda: None)
    with web.app.app_context():
        my_app = web.start("1024", "/tmp/sdaas_input/", "/tmp/sdaas_output",
                           None)
        assert isinstance(my_app, Flask)
        assert isinstance(my_app, web.MyFlask)
        yield my_app

        stop_worker(web.app.queue, web.app.worker)


@pytest.fixture
def incomplete_app_client(app):
    yield app.test_client()


@pytest.fixture
def app_client(incomplete_app_client):
    res = incomplete_app_client.post(
        '/set_options/', data=json.dumps({}), content_type='application/json')
    assert res.status_code == 200
    assert json.loads(res.get_data(as_text=True))['ok']
    yield incomplete_app_client


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
        stop_worker(web.app.queue, web.app.worker)
        assert web.app.config['INPUT_DIR'] == '/in'
        assert web.app.config['OUTPUT_DIR'] == '/out'

    assert my_post_request.called
    assert len(my_post_request.args[0][0]) == 1
    assert my_post_request.args[0][0][0] == my_addr + '/im_alive/'

    data = my_post_request.args[0][1]['json']
    assert data['id'] == my_id
    assert 'MyPicker' in data['options']['Picker']
    assert 'param1' in data['options']['Picker']['MyPicker']['parts']
    assert data['options']['Picker']['MyPicker']['parts']['param1']['required']


@pytest.mark.parametrize("func", [
    lambda x: x.started, lambda x: x.queue, lambda x: x.worker,
    lambda x: setattr(x, 'started', True)
])
def test_my_flask_getters_and_setters(monkeypatch, func, my_flask):
    mock_setup = MockingFunction()
    monkeypatch.setattr(my_flask, 'setup', mock_setup)

    func(my_flask)

    assert mock_setup.called


@pytest.mark.parametrize('empty', [True, False])
def test_start_music(monkeypatch, app_client, empty):
    mocked_queue_empty = MockingFunction(lambda: empty, simple=True)
    monkeypatch.setattr(mp.queues.Queue, 'empty', mocked_queue_empty)
    mocked_queue_put = MockingFunction()
    monkeypatch.setattr(mp.queues.Queue, 'put', mocked_queue_put)

    try:
        response = app_client.post(
            '/start/', data=json.dumps({}), content_type='application/json')
        other_res = []
        for _ in range(10):
            other_res.append(
                app_client.post(
                    '/start/',
                    data=json.dumps({}),
                    content_type='application/json'))
    except Exception as exp:
        raise exp
    finally:
        monkeypatch.undo()

    mocked_queue_empty.called

    assert response.status_code == 200
    assert json.loads(response.get_data(as_text=True))['ok'] == empty
    for res in other_res:
        assert res.status_code == (410 if empty else 200)
        assert not json.loads(res.get_data(as_text=True))['ok']

    if empty:
        assert mocked_queue_put.called
        assert mocked_queue_put.args[0][0] == ((web.START_LOOP, ), )
    else:
        assert not mocked_queue_put.called


@pytest.mark.parametrize('url,expected_code', [(
    '/delete_music/', web.DELETE_SONG), ('/add_music/', web.PROCESS_SONG)])
@pytest.mark.parametrize('throw', [False, True])
def test_add_music(monkeypatch, app_client, throw, url, expected_code):
    def my_put():
        if throw:
            raise queue.Full('Err')
        else:
            return None

    mocked_queue_put = MockingFunction(my_put, simple=True)
    monkeypatch.setattr(mp.queues.Queue, 'put_nowait', mocked_queue_put)

    try:
        my_file_loc = str(random.random()) + 'location/'
        song_id = random.randint(10, 1000)
        res = app_client.post(
            url,
            content_type='application/json',
            data=json.dumps({
                'file_location': my_file_loc,
                'id': song_id,
            }))

        assert mocked_queue_put.called
        assert mocked_queue_put.args[0][0][0] == (expected_code, my_file_loc,
                                                  song_id)

        assert json.loads(res.get_data(as_text=True))['ok'] != throw
        assert res.status_code == 200
    except Exception as exp:
        raise exp
    finally:
        monkeypatch.undo()


@pytest.mark.parametrize("raises", [Exception, MemoryError])
def test_exception_backend_worker(raises, monkeypatch):
    mocked_post = MockingFunction()
    monkeypatch.setattr(requests, 'post', mocked_post)

    def raising():
        raise raises

    mocked_split_text = MockingFunction(raising, simple=True)
    monkeypatch.setattr(os.path, 'splitext', mocked_split_text)

    worker_queue = queue.Queue()

    song_id = random.randint(1000, 10000)
    my_id = random.randint(0, 1000)
    my_host = str(random.randint(2, 1000)) + '/wowsers.html'

    worker_queue.put((web.PROCESS_SONG, '/filename/my_song.mp3', song_id))

    with pytest.raises(raises):
        web.backend_worker(worker_queue, my_host, my_id, '/output')

    assert mocked_post.called
    assert mocked_post.args[0][1]['json']['id'] == my_id
    if raises is MemoryError:
        assert mocked_post.args[0][0] == (my_host + '/ultra_died/', )
    else:
        assert mocked_post.args[0][0] == (my_host + '/died/', )


def test_backend_worker(monkeypatch):
    class MyAudioSegement():
        def __init__(self):
            self.args = []
            self.called = False

        def export(self, filename, format):
            self.args.append((filename, format))
            self.called = True

    class MyPicker(pickers.Picker):
        called = False
        args = []

        def __init__(self, other, rest=101, a=True):
            pass

        @staticmethod
        def process_song_file(song_file, rest):
            MyPicker.args.append((song_file, rest))
            MyPicker.called = True

    mocked_get_controller = MockingFunction(lambda: 'Controller')
    mocked_get_picker = MockingFunction(lambda: 'Picker')
    mocked_get_transitioner = MockingFunction(lambda: 'Transitioner')
    mocked_get_communicator = MockingFunction(lambda: 'Communicator')
    monkeypatch.setattr(config.Config, 'get_controller', mocked_get_controller)
    monkeypatch.setattr(config.Config, 'get_picker', mocked_get_picker)
    monkeypatch.setattr(config.Config, 'get_transitioner',
                        mocked_get_transitioner)
    monkeypatch.setattr(config.Config, 'get_communicator',
                        mocked_get_communicator)

    mocked_loop = MockingFunction()
    monkeypatch.setattr(core, 'loop', mocked_loop)
    my_segment = MyAudioSegement()
    mocked_from_mp3 = MockingFunction(lambda: my_segment, simple=True)
    monkeypatch.setattr(pydub.AudioSegment, 'from_mp3', mocked_from_mp3)
    # This also patches .export as this is done in MyAudioSegement

    mocked_get_class = MockingFunction(lambda: MyPicker, simple=True)
    monkeypatch.setattr(config.Config, 'get_class', mocked_get_class)

    mocked_post = MockingFunction()
    monkeypatch.setattr(requests, 'post', mocked_post)

    mocked_config_mupdate = MockingFunction()
    mocked_config_cupdate = MockingFunction()
    monkeypatch.setattr(config.Config, 'update_config_class_options',
                        mocked_config_cupdate)
    monkeypatch.setattr(config.Config, 'update_config_main_options',
                        mocked_config_mupdate)

    mocked_remove = MockingFunction()
    monkeypatch.setattr(os, 'remove', mocked_remove)

    worker_queue = queue.Queue()

    start_loop_arg = random.random()
    my_host = str(random.random()) + 'loc'
    my_id = random.randint(0, 1000)
    song_id = random.randint(1000, 10000)

    worker_queue.put((web.PROCESS_SONG, '/filename/my_song.mp3', song_id))
    worker_queue.put((web.START_LOOP, start_loop_arg))
    worker_queue.put((web.OPTIONS, {
        'Picker': {
            'name': 'MyPicker',
            'options': {
                'a': None
            }
        }
    }))
    worker_queue.put((web.DELETE_SONG, '/remove/this.mp3', song_id))
    worker_queue.put((web.STOP, ))

    web.backend_worker(worker_queue, my_host, my_id, '/output')

    assert mocked_loop.called
    assert mocked_loop.args[0][0] == (my_id, my_host, 'Controller', 'Picker',
                                      'Transitioner', 'Communicator')
    assert mocked_from_mp3.called

    assert my_segment.called
    assert my_segment.args[0][0].startswith('/tmp/')
    assert my_segment.args[0][0].endswith('/my_song.wav')
    assert my_segment.args[0][1] == 'wav'

    assert mocked_config_cupdate.called
    assert mocked_config_mupdate.called
    assert mocked_config_cupdate.args[0][0] == ('Picker', 'MyPicker', {
        'a': None
    })
    assert mocked_config_mupdate.args[0][0] == ({'Picker': 'MyPicker'}, )

    assert mocked_post.called
    assert mocked_post.args[0][0][0] == my_host + '/music_processed/'
    assert mocked_post.args[0][1]['json']['id'] == song_id

    assert mocked_post.args[1][0][0] == my_host + '/music_deleted/'
    assert mocked_post.args[1][1]['json']['id'] == song_id
    assert mocked_remove.called
    assert mocked_remove.args[0][0][0].endswith('this.wav')
    assert mocked_remove.args[0][0][0].startswith('/tmp/')

    assert mocked_get_class.called
    assert MyPicker.called
    assert MyPicker.args == [(my_segment.args[0][0], 101)]


def test_setting_user_config(incomplete_app_client):
    res = incomplete_app_client.post('/start/')

    assert res.status_code == 412
    assert not json.loads(res.get_data(as_text=True))['ok']

    res = incomplete_app_client.post(
        '/set_options/', data=json.dumps({}), content_type='application/json')

    assert res.status_code == 200
    assert json.loads(res.get_data(as_text=True))['ok']

    res = incomplete_app_client.post(
        '/set_options/', data=json.dumps({}), content_type='application/json')

    assert res.status_code == 412
    assert not json.loads(res.get_data(as_text=True))['ok']
