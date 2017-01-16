import pytest
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.communicators as communicators


@pytest.fixture
def communicator_base():
    yield communicators.Communicator()


@pytest.fixture
def simple_communicator():
    yield communicators.SimpleCommunicator()


@pytest.fixture(params=[communicators.SimpleCommunicator])
def all_communicators(request):
    yield request.param


def test_base_communicator(communicator_base):
    assert isinstance(communicator_base, communicators.Communicator)
    with pytest.raises(NotImplementedError):
        communicator_base.get_user_feedback(None, None)


def test_all_communicators(all_communicators):
    assert issubclass(all_communicators, communicators.Communicator)
    assert callable(all_communicators.get_user_feedback)
    assert all_communicators.get_user_feedback.__code__.co_argcount == 3


def test_simple_communicator(simple_communicator):
    res = simple_communicator.get_user_feedback(None, None)
    assert isinstance(res, dict)
    assert not res
