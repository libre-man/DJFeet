import pytest
import os
import sys
import librosa
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.transitioners as transitioners


@pytest.fixture
def transitioner_base():
    yield transitioners.Transitioner()

@pytest.fixture(params=[("tests/test_data/songs/output.wav", 10),
                        ("tests/test_data/songs/output.wav", 30),
                        ("tests/test_data/songs/output.wav", 0)])
def inf_jukebox_transitioner(request):
    yield transitioners.InfJukeboxTransitioner(request.param[0],
                                               request.param[1])

@pytest.fixture(params=[transitioners.SimpleTransitioner,
                        transitioners.InfJukeboxTransitioner])
def all_transitioners(request):
    yield request.param

def test_base_inf_jukebox_transitioner(inf_jukebox_transitioner):
    assert isinstance(inf_jukebox_transitioner,
                      transitioners.InfJukeboxTransitioner)

def test_base_transitioner(transitioner_base):
    assert isinstance(transitioner_base, transitioners.Transitioner)
    with pytest.raises(NotImplementedError):
        transitioner_base.merge(None, None)
    with pytest.raises(NotImplementedError):
        transitioner_base.write_sample(None)


def test_all_transitioners(all_transitioners):
    assert issubclass(all_transitioners, transitioners.Transitioner)

    merge = all_transitioners.merge
    assert callable(merge)
    assert merge.__code__.co_argcount == 3

    write_sample = all_transitioners.write_sample
    assert callable(write_sample)
    assert write_sample.__code__.co_argcount == 2

@pytest.mark.parametrize("songs", ["tests/test_data/songs/song1.wav",
                                   "tests/test_data/songs/song2.wav"])
def test_write_sample(inf_jukebox_transitioner, songs):
    time_series, _ = librosa.load(songs)
    inf_jukebox_transitioner.write_sample(time_series)
    time_series2, _ = librosa.load(inf_jukebox_transitioner.output)
    a = time_series == time_series2
    print(a)
    assert a and all(a)
