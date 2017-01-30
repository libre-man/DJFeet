import pytest
import os
import sys
import requests
import random
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.communicators as communicators


@pytest.fixture
def communicator_base():
    yield communicators.Communicator()


@pytest.fixture
def protocol_communicator():
    yield communicators.ProtocolCommunicator()


@pytest.fixture
def simple_communicator():
    yield communicators.SimpleCommunicator()


@pytest.fixture(params=[
    communicators.SimpleCommunicator, communicators.ProtocolCommunicator
])
def all_communicators(request):
    yield request.param


def test_base_communicator(communicator_base):
    assert isinstance(communicator_base, communicators.Communicator)
    with pytest.raises(NotImplementedError):
        communicator_base.get_user_feedback(None, None, None, None)


def test_all_communicators(all_communicators):
    assert issubclass(all_communicators, communicators.Communicator)
    assert callable(all_communicators.get_user_feedback)
    assert all_communicators.get_user_feedback.__code__.co_argcount == 5


def test_simple_communicator(simple_communicator):
    res = simple_communicator.get_user_feedback(None, None, None, None)
    assert isinstance(res, dict)
    assert not res


@pytest.mark.parametrize('_', range(2))
@pytest.mark.parametrize('data', [{
    'feedback': ['Wow', random.randint(4000, 5000)]
}])
def test_protocol_communicator(protocol_communicator, monkeypatch, data, _):
    class MyResponse:
        def json(self):
            return data

    mocked_post_request = MockingFunction(MyResponse, simple=True)
    monkeypatch.setattr(requests, 'post', mocked_post_request)

    remote = str(random.randint(0, 1000)) + '-remote'
    app_id = str(random.randint(1000, 2000)) + '-id'
    start = str(random.randint(2000, 3000)) + '-start'
    end = str(random.randint(3000, 4000)) + '-end'

    res = protocol_communicator.get_user_feedback(remote, app_id, start, end)

    assert res == data['feedback']
    assert mocked_post_request.called
    assert mocked_post_request.args == [((remote + '/get_feedback/', ), {
        'json': {
            'start': start,
            'end': end,
            'id': app_id
        }
    })]
