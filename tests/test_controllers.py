import pytest
import os
import sys
from configparser import ConfigParser
import time
from helpers import MockingFunction
import datetime
from libfaketime import fake_time as freeze_time

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.controllers as controllers
import dj_feet.helpers as helpers


@pytest.fixture
def controller_base():
    yield controllers.Controller()


@pytest.fixture(params=[controllers.SimpleController])
def all_controllers(request):
    yield request.param


@pytest.fixture
def simple_controller_cls():
    yield controllers.SimpleController


def test_base_controller(controller_base):
    assert isinstance(controller_base, controllers.Controller)
    with pytest.raises(NotImplementedError):
        controller_base.should_continue()
    with pytest.raises(NotImplementedError):
        controller_base.get_waittime(None, None)


def test_all_controllers(all_controllers):
    assert issubclass(all_controllers, controllers.Controller)

    should_continue = all_controllers.should_continue
    assert callable(should_continue)
    assert should_continue.__code__.co_argcount == 1

    get_waittime = all_controllers.get_waittime
    assert callable(get_waittime)
    assert get_waittime.__code__.co_argcount == 3


@pytest.mark.parametrize("amount", [10, 0, 1, -1, 20])
def test_simple_controller_should_continue(simple_controller_cls, amount):
    simple_controller = simple_controller_cls(amount)
    for _ in range(amount):
        assert simple_controller.should_continue()
    assert not simple_controller.should_continue()


@pytest.mark.parametrize("time_to_wait", [0, 2.5, 1, 10, 99])
def test_simple_controller_get_waittime(simple_controller_cls, time_to_wait):
    simple_controller = simple_controller_cls(sys.maxsize)
    then = datetime.datetime.now()
    with freeze_time(then):
        assert simple_controller.get_waittime(then.timestamp(), 30) == 0
        simple_controller.should_continue()
        assert simple_controller.get_waittime(then.timestamp(), 30) == 30
    now = datetime.datetime.fromtimestamp(then.timestamp() + time_to_wait)
    with freeze_time(now):
        assert abs(
            simple_controller.get_waittime(then.timestamp(), 30) - 30.0 +
            time_to_wait) <= helpers.EPSILON
        simple_controller.should_continue()
        assert abs(
            simple_controller.get_waittime(then.timestamp(), 30) - 2 * 30.0 +
            time_to_wait) <= helpers.EPSILON
        simple_controller.should_continue()
        assert abs(
            simple_controller.get_waittime(then.timestamp(), 30) - 3 * 30.0 +
            time_to_wait) <= helpers.EPSILON
        simple_controller.should_continue()
        assert abs(
            simple_controller.get_waittime(then.timestamp(), 30) - 4 * 30.0 +
            time_to_wait) <= helpers.EPSILON
