import pytest
import os
import sys
from helpers import MockingFunction
import time
import random
import datetime
import requests

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.core as core


@pytest.fixture
def patched_post(monkeypatch):
    mocked_post = MockingFunction()
    monkeypatch.setattr(requests, 'post', mocked_post)
    yield mocked_post


@pytest.fixture
def mock_forcing_picker():
    class MockPicker:
        def __init__(self):
            self.feedback = []
            self.emitted = []

        def get_next_song(self, _, force):
            if force:
                return random.random()
            else:
                return -1

    yield MockPicker()


@pytest.fixture
def mock_picker():
    class MockPicker:
        def __init__(self):
            self.feedback = []
            self.emitted = []

        def get_next_song(self, feedback, force):
            to_emit = random.random()
            self.feedback.append(feedback)
            self.emitted.append(to_emit)
            return to_emit

    yield MockPicker()


@pytest.fixture(params=[(4, 100), (5, 100), (10, 100), (0, 100), (2, -1),
                        (1000, random.random)])
def mock_controller(request):
    class MockController:
        def __init__(self, amount, waittime_amount):
            self.amount = amount
            self.called_amount = 0
            self.waittime_emitted = []
            self.waittime_amount = waittime_amount
            self.waittime_args = []

        def should_continue(self):
            self.called_amount += 1
            return self.amount >= self.called_amount

        def waittime(self, sample):
            to_emit = None
            if callable(self.waittime_amount):
                to_emit = self.waittime_amount()
            else:
                to_emit = self.waittime_amount
            self.waittime_args.append(sample)
            self.waittime_emitted.append(to_emit)
            return to_emit

    yield MockController(*request.param)


@pytest.fixture
def mock_exception_transitioner():
    class MockTransitioner:
        def __init__(self):
            self.prev = None
            self.throw = False
            self.out = None

        def merge(self, _, new):
            if self.throw:
                self.throw = False
                raise ValueError('WAAA!')
            self.throw = True
            assert new != self.prev
            self.prev = new
            self.out = random.random()
            return self.out, 30

        def write(self, sample):
            assert sample == self.out

    yield MockTransitioner()


@pytest.fixture
def mock_transitioner():
    class MockTransitioner:
        def __init__(self):
            self.merge_args = []
            self.write_args = []
            self.merge_emitted = []
            self.merge_times = []
            self.first = True
            self.max_size = 100

        def merge(self, prev, new):
            self.merge_args.append((prev, new))
            to_emit = random.random()
            self.merge_emitted.append(to_emit)
            if self.first:
                self.first = False
                new_time = 100
            else:
                new_time = random.random() * self.max_size
            self.merge_times.append(new_time)
            return to_emit, new_time

        def write(self, sample):
            self.write_args.append(sample)

    yield MockTransitioner()


@pytest.fixture
def mock_communicator():
    class MockCommunicator:
        def __init__(self):
            self.called_amount = 0
            self.emitted = []
            self.end_time = 0.0

        def get_user_feedback(self, start, end):
            self.called_amount += 1
            self.emitted.append(random.random())
            self.end_time = end
            return self.emitted[-1]

    yield MockCommunicator()


def test_loop_excpetion(monkeypatch, mock_controller, mock_forcing_picker,
                        mock_exception_transitioner, mock_communicator, capsys,
                        patched_post):
    mock_sleep = MockingFunction(lambda: None, simple=True)
    monkeypatch.setattr(time, 'sleep', mock_sleep)
    core.loop(0, 'localhost', mock_controller, mock_forcing_picker,
              mock_exception_transitioner, mock_communicator)
    _, err = capsys.readouterr()


def test_loop(monkeypatch, mock_controller, mock_picker, mock_transitioner,
              mock_communicator, capsys, patched_post):
    mock_sleep = MockingFunction(lambda: None, simple=True)
    monkeypatch.setattr(time, 'sleep', mock_sleep)
    now = int(time.time())
    my_id = random.randint(1, 10010101)
    my_addr = str(random.random()) + "/local"
    core.loop(my_id, my_addr, mock_controller, mock_picker, mock_transitioner,
              mock_communicator)
    _, err = capsys.readouterr()

    iterations = mock_controller.amount

    if err:
        assert mock_controller.waittime_amount < 0
    else:
        assert mock_controller.waittime_emitted == [
            x[0][0] for x in mock_sleep.args
        ]
    assert all([x[0][0] > 0 for x in mock_sleep.args])
    assert mock_controller.amount + 1 == mock_controller.called_amount

    assert mock_transitioner.merge_emitted == mock_transitioner.write_args

    if mock_controller.amount >= 5:
        assert mock_controller.amount == mock_communicator.called_amount + 4
    assert len(mock_communicator.emitted) == max(
        len(mock_picker.feedback) - 4, 0)
    assert mock_communicator.emitted == mock_picker.feedback[4:]

    assert (not mock_picker.feedback) or mock_picker.feedback[0] == {}

    if iterations > 4:
        correct_time = mock_transitioner.max_size * (
            iterations - 4) + mock_transitioner.merge_times[-4]
        assert mock_communicator.end_time == correct_time
        assert isinstance(mock_communicator.end_time, float)

    if iterations > 0:
        assert patched_post.called
        assert patched_post.args[0][0][0] == my_addr + '/controller_started/'
        assert patched_post.args[0][1]['data']['id'] == my_id
        assert patched_post.args[0][1]['data']['epoch'] == now

    i = 0
    for prev, new in mock_transitioner.merge_args:
        if i == 0:
            assert prev is None
        else:
            assert mock_picker.emitted[i - 1] == prev
        assert mock_picker.emitted[i] == new
        i += 1
