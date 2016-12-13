import pytest
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction, EPSILON
import random
from pprint import pprint

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.pickers as pickers
from dj_feet.helpers import get_all_subclasses, SongStruct


@pytest.fixture
def picker_base():
    yield pickers.Picker()


@pytest.fixture(params=[pickers.SimplePicker, pickers.NCAPicker])
def all_pickers(request):
    yield request.param


@pytest.fixture
def songs_dir():
    yield os.path.join(my_path, 'test_data', 'songs')


@pytest.fixture
def simple_picker(songs_dir):
    yield pickers.SimplePicker(songs_dir)


@pytest.fixture
def nca_picker(songs_dir):
    yield pickers.NCAPicker(songs_dir, cache_dir='/tmp/sdaas')


@pytest.fixture(params=[{}])
def user_feedback(request):
    yield request.param


def test_base_picker(picker_base, user_feedback):
    assert isinstance(picker_base, pickers.Picker)
    with pytest.raises(NotImplementedError):
        picker_base.get_next_song(user_feedback)


def test_all_pickers(all_pickers):
    assert issubclass(all_pickers, pickers.Picker)
    assert callable(all_pickers.get_next_song)
    assert all_pickers.get_next_song.__code__.co_argcount == 2


def test_simple_picker_no_files_left(monkeypatch, simple_picker):
    monkeypatch.setattr(os.path, 'isfile', lambda _: False)
    with pytest.raises(ValueError):
        simple_picker.get_next_song({})


@pytest.mark.parametrize('_', range(5))
def test_simple_picker_working_direct(monkeypatch, simple_picker, songs_dir,
                                      _):
    song_to_choose = random.choice([f for _, __, f in os.walk(songs_dir)][0])
    mock_random_choice = MockingFunction(func=lambda: song_to_choose,
                                         simple=True)
    monkeypatch.setattr(random, 'choice', mock_random_choice)
    chosen_song = simple_picker.get_next_song({})
    assert isinstance(chosen_song, SongStruct)
    assert chosen_song.file_location == song_to_choose
    assert chosen_song.end_pos is None
    assert chosen_song.start_pos == 0
    assert len(mock_random_choice.args) == 1
    assert len(mock_random_choice.args[0][0]) == 1
    assert len(mock_random_choice.args[0][1]) == 0
    assert isinstance(mock_random_choice.args[0][0][0], list)
    with pytest.raises(ValueError):
        simple_picker.get_next_song({})


def test_simple_picker_working_non_direct(monkeypatch, simple_picker):
    mock_random_choice = MockingFunction(func=random.choice)
    mock_is_file = MockingFunction(func=lambda i: i > 2, amount=True)
    monkeypatch.setattr(os.path, 'isfile', mock_is_file)
    monkeypatch.setattr(random, 'choice', mock_random_choice)
    simple_picker.get_next_song({})
    assert len(mock_is_file.args) == 3
    assert len(mock_random_choice.args) == 2


@pytest.mark.parametrize('same', [True] + [False for _ in range(2)])
def test_nca_picker_distance(nca_picker, same, songs_dir):
    song_files = [f for _, __, f in os.walk(songs_dir)][0]

    song_file1 = random.choice(song_files)
    if same:
        song_file2 = song_file1
    else:
        song_files.remove(song_file1)
        song_file2 = random.choice(song_files)

    res_1 = nca_picker.distance(song_file1, song_file2)
    res_2 = nca_picker.distance(song_file2, song_file1)
    assert res_1 == res_2
    if same:
        assert abs(res_1) <= EPSILON
    else:
        assert abs(res_1) > EPSILON


def test_nca_picker_next_song(nca_picker, monkeypatch, songs_dir):
    mock_random = MockingFunction(func=lambda: 0.99999999, simple=True)
    monkeypatch.setattr(random, 'random', mock_random)
    next_song = nca_picker.get_next_song({})
    next_song2 = nca_picker.get_next_song({})
    assert next_song == next_song2
    monkeypatch.undo()
    for _ in range(50):
        next_song2 = nca_picker.get_next_song({})
    if next_song == next_song2:
        pprint(nca_picker.song_distances)
    assert next_song != next_song2
