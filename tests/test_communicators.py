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


def test_base_communicator(communicator_base):
    assert isinstance(communicator_base, communicators.Communicator)
    with pytest.raises(NotImplementedError):
        communicator_base.get_user_feedback()
