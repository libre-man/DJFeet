import pytest
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.pickers as pickers


@pytest.fixture
def picker_base():
    yield pickers.Picker()


@pytest.fixture(params=[{}])
def user_feedback(request):
    yield request.param


def test_base_picker(picker_base, user_feedback):
    assert isinstance(picker_base, pickers.Picker)
    with pytest.raises(NotImplementedError):
        picker_base.get_next_song(user_feedback)
