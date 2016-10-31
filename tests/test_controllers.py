import pytest
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.controllers as controllers


@pytest.fixture
def controller_base():
    yield controllers.Controller()


def test_base_controller(controller_base):
    assert isinstance(controller_base, controllers.Controller)
    with pytest.raises(NotImplementedError):
        controller_base.should_continue()
    with pytest.raises(NotImplementedError):
        controller_base.get_waittime(None)
