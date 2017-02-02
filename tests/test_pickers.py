import pytest
import os
import sys
import librosa
from configparser import ConfigParser
from helpers import MockingFunction, EPSILON, slow
from itertools import product
import random
from pprint import pprint
import gc

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.song
import dj_feet.helpers
import dj_feet.pickers as pickers
from dj_feet.helpers import get_all_subclasses


@pytest.fixture(autouse=True)
def no_process_data():
    # F*ck you monkeypatch you don't f*cking work
    old = dj_feet.song.Song.set_process_data
    dj_feet.song.Song.set_process_data = lambda x: True
    yield
    dj_feet.song.Song.set_process_data = old


@pytest.fixture
def cache_dir():
    yield '/tmp/sdaas/'


@pytest.fixture
def picker_base():
    yield pickers.Picker()


@pytest.fixture(params=[pickers.SimplePicker, pickers.NCAPicker])
def all_pickers(request):
    yield request.param


@pytest.fixture
def simple_picker(songs_dir):
    yield pickers.SimplePicker(songs_dir)


@pytest.fixture(params=product([True, False]
                               if pytest.config.getoption("--runslow") else
                               [True], [(2, None), (4, [0.2, 0.3, 0.2, 0.3])]))
def nca_picker(request, cache_dir, songs_dir):
    cache, (weight_amount, weights) = request.param
    picker = pickers.NCAPicker(
        songs_dir,
        cache_dir=cache_dir if cache else None,
        weight_amount=weight_amount,
        weights=weights)
    assert weights is None or len(picker.weights) == len(weights)
    yield picker
    assert weights is None or len(picker.weights) == len(weights)
    gc.collect()


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
    assert all_pickers.get_next_song.__code__.co_argcount == 3

    assert callable(all_pickers.process_song_file)
    for var in dj_feet.helpers.get_args(all_pickers.process_song_file):
        if var != 'song_file':
            assert var in dj_feet.helpers.get_args(all_pickers.__init__)


def test_simple_picker_no_files_left(monkeypatch, simple_picker):
    monkeypatch.setattr(os.path, 'isfile', lambda _: False)
    with pytest.raises(ValueError):
        simple_picker.get_next_song({})


@pytest.mark.parametrize('_', range(5))
def test_simple_picker_working_direct(monkeypatch, simple_picker,
                                      random_song_file, _):
    mock_random_choice = MockingFunction(
        func=lambda: random_song_file, simple=True)
    monkeypatch.setattr(random, 'choice', mock_random_choice)
    chosen_song = simple_picker.get_next_song({})
    assert isinstance(chosen_song, dj_feet.song.Song)
    assert chosen_song.file_location == random_song_file
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
def test_nca_picker_distance(nca_picker, same, songs_dir, random_song_files):
    file1 = random_song_files[0]
    if same:
        file2 = file1
    else:
        file2 = random_song_files[1]

    res_1 = nca_picker.distance(file1, file2)
    res_2 = nca_picker.distance(file2, file1)
    assert res_1 == res_2
    if same:
        assert abs(res_1) <= EPSILON
    else:
        assert abs(res_1) > EPSILON


def text_nca_picker_feedback(nca_picker, monkeypatch, songs_dir):
    def my_get_userfeedback(feedback):
        assert feedback['old'] == feedback['good_old']
        assert feedback['new'] == feedback['good_new']
        assert feedback['old'].file_location != feedback['old'].file_location
        return feedback['number']

    mocked__optimize_weights = MockingFunction()
    mocked_get_userfeedback = MockingFunction(func=my_get_userfeedback)
    songs = []

    monkeypatch.setattr(nca_picker, 'get_userfeedback',
                        mocked_get_userfeedback)
    monkeypatch.setattr(nca_picker, '_optimize_weights',
                        mocked__optimize_weights)

    songs.append(nca_picker.get_next_song(None))
    songs.append(nca_picker.get_next_song(None))
    songs.append(nca_picker.get_next_song(None))

    # Here (4th time) the core will start sending feedback. However this uses a
    # non existing Seg-1 so it should not be used. See docs/timing.dt for more
    # information.
    songs.append(nca_picker.get_next_song(None))

    for i in range(10):
        songs.append(
            nca_picker.get_next_song({
                'good_old': songs[-5],
                'good_new': songs[-4],
                'number': i,
            }))

    assert mocked_get_userfeedback.called
    assert mocked__optimize_weights.called


def test_nca_picker_next_song(nca_picker, monkeypatch, songs_dir):
    real_rand = random.random

    def feedback_test(feedback):
        options = {
            "1453492_Regina_Original_Mix.wav": 0.8,
            "1665536_Hear_Me_Out_Original_Mix.wav": 0.3,
            "2064084_New_Day_Original_Mix.wav": 0.7,
            "2739576_Hunger_Original_Mix.wav": 0.1,
            "1313776_Slazenger_Joseph_Capriati_Remix.wav": 0.1,
            "1588390_Where_2D_Meets_3D_Chris_Liebing_Remix.wav": 0.1,
            "1928097_Egoist_Original_Mix.wav": 0.1,
            "22538_Panikattack_Original_Mix.wav": 0.1,
            "3030059_Neve___Me_Original_Mix.wav": 0.1,
        }
        needle = False
        if feedback['old'].find("Bubbler") > 0:
            needle = feedback['new']
        if feedback['new'].find("Bubbler") > 0:
            needle = feedback['old']
        if needle:
            for key, value in options.items():
                if key.find(needle) > 0:
                    return value

        return real_rand()

    mock_random = MockingFunction(func=lambda: 0.99999999999, simple=True)
    monkeypatch.setattr(random, 'random', mock_random)
    real_rand()
    assert not mock_random.called

    mock_feedback = MockingFunction(func=feedback_test)
    nca_picker.get_feedback = mock_feedback

    streak = 0

    next_song = nca_picker.get_next_song({})
    next_song2 = nca_picker.get_next_song({})
    assert isinstance(next_song2, dj_feet.song.Song)
    songs = [next_song.file_location]
    assert next_song.file_location == next_song2.file_location
    monkeypatch.undo()
    for _ in range(50):
        next_song2_new = nca_picker.get_next_song({}, force=streak > 3)
        if next_song2.file_location == next_song2_new.file_location:
            streak += 1
        else:
            streak = 0
        next_song2 = next_song2_new
        songs.append(next_song2.file_location)
        assert next_song2 is not None
        assert isinstance(next_song2, dj_feet.song.Song)
    if next_song == next_song2:
        pprint(nca_picker.song_distances)
    pprint(songs)
    assert mock_feedback.called
    assert len(songs) == 51


@pytest.mark.parametrize(
    "kwargs", [
        {},
        {
            'weight_amount': 20,
            'mfcc_amount': 20
        },
        {
            'weight_amount': 2,
            'weights': [0.5, 0.5]
        },
        {
            'weight_amount': 2,
            'weights': [0, 1]
        },
        pytest.mark.xfail(
            {
                'weight_amount': 2,
                'weights': [0, 2]
            },
            raises=ValueError,
            strict=True),
        pytest.mark.xfail(
            {
                'weight_amount': 2,
                'weights': [0.25, 0.25, 0.25, 0.25]
            },
            raises=ValueError,
            strict=True),
        pytest.mark.xfail(
            {
                'weight_amount': 20,
                'mfcc_amount': 19
            },
            raises=ValueError,
            strict=True),
    ])
def test_broken_nca_config(monkeypatch, songs_dir, cache_dir, kwargs):
    monkeypatch.setattr(pickers.NCAPicker, 'calculate_songs_characteristics',
                        lambda x, y, z: (True, True, False))
    pickers.NCAPicker(songs_dir, cache_dir=cache_dir, **kwargs)


@pytest.mark.parametrize('_', range(20))
def test_preserving_force(monkeypatch, nca_picker, _):
    amount = 0
    prev = None

    def call_and_add(amount, prev):
        new = nca_picker.get_next_song({})
        if prev is None or new.file_location != prev.file_location:
            return amount + 1, new
        return amount, new

    mock_get_feedback = MockingFunction(func=lambda: 1, simple=True)
    nca_picker.get_feedback = mock_get_feedback
    monkeypatch.setattr(nca_picker, '_optimize_weights',
                        lambda: mock_get_feedback({}))

    i = 0
    for _ in range(5):
        amount, prev = call_and_add(amount, prev)
        if i > 100:
            assert False
    assert not mock_get_feedback.called

    for _ in range(10):
        forced = nca_picker.get_next_song({}, force=True)
        assert forced.file_location != prev.file_location
        prev = forced

    assert not mock_get_feedback.called
    assert len(nca_picker.picked_songs) == 5

    i = 0
    while amount <= 5:
        amount, prev = call_and_add(amount, prev)
        if i > 100:
            assert False

    assert len(nca_picker.picked_songs) == 5
    if not mock_get_feedback.called:
        print(nca_picker.picked_songs)
    assert mock_get_feedback.called


@slow
@pytest.mark.parametrize("amount", [1, 5, 20])
def test_get_mfcc(random_song_file, amount):
    song, sr = librosa.load(random_song_file)
    mfcc = librosa.feature.mfcc(song, sr, None, amount)
    mfcc_res, _ = pickers.NCAPicker.get_mfcc_and_tempo(random_song_file,
                                                       amount)
    same = mfcc_res == mfcc
    assert hasattr(same, '__iter__') and same.all()
