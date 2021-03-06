import pytest
import os
import sys
import librosa
import numpy
import pydub
from configparser import ConfigParser
from helpers import EPSILON, MockingFunction
from pprint import pprint

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.transitioners as transitioners
from dj_feet.song import Song


@pytest.fixture
def song_output_file():
    yield os.path.join(my_path, 'test_data', 'output.wav')


@pytest.fixture
def transitioner_base():
    yield transitioners.Transitioner()


@pytest.fixture(params=[10, 14])
def inf_jukebox_transitioner(request, song_output_file):
    yield transitioners.InfJukeboxTransitioner(
        song_output_file, segment_size=request.param)


@pytest.fixture(params=[transitioners.InfJukeboxTransitioner])
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


@pytest.mark.parametrize("_", range(2))
def test_write_sample(inf_jukebox_transitioner, _, random_song_file,
                      monkeypatch):
    mocking_export = MockingFunction()

    class MyAudioSegment:
        def __init__(self, wav):
            assert wav.startswith('/tmp/')

        def export(self, *args, **kwargs):
            mocking_export(*args, **kwargs)

    mocking_librosa = MockingFunction(lambda x, sample, sr, norm: x)
    monkeypatch.setattr(librosa.output, 'write_wav', mocking_librosa)

    mocking_pydub = MockingFunction(MyAudioSegment)
    monkeypatch.setattr(pydub.AudioSegment, 'from_wav', mocking_pydub)

    time_series, sr = librosa.load(random_song_file)

    inf_jukebox_transitioner.write_sample(time_series)
    assert len(mocking_librosa.args) == 1
    assert len(mocking_export.args) == 1

    inf_jukebox_transitioner.write_sample(time_series)
    assert len(mocking_librosa.args) == 2
    assert len(mocking_export.args) == 2

    assert mocking_librosa.called
    a = mocking_librosa.args[0][0][1] == time_series
    assert hasattr(a, '__iter__') and a.all()
    assert mocking_librosa.args[0][1]['sr'] == sr

    assert mocking_pydub.called
    assert mocking_export.args[0][0][0] == os.path.join(
        inf_jukebox_transitioner.output_folder, "part0.mp3")
    assert mocking_export.args[1][0][0] == os.path.join(
        inf_jukebox_transitioner.output_folder, "part1.mp3")


@pytest.mark.parametrize('same', [True, False])
def test_merge_sample(inf_jukebox_transitioner, random_song_files, monkeypatch,
                      same):
    mocking_append = MockingFunction(func=numpy.append)
    monkeypatch.setattr(numpy, 'append', mocking_append)
    song1 = Song(random_song_files[0])
    if same:
        song2 = song1
    else:
        song2 = Song(random_song_files[1])
    res, time_delta = inf_jukebox_transitioner.merge(song1, song2)
    assert (time_delta == inf_jukebox_transitioner.segment_size) == same
    assert mocking_append.called != same
    assert abs(
        librosa.core.get_duration(res, song1.sampling_rate) -
        inf_jukebox_transitioner.segment_size) < 0.0001


def test_time_exceeded_exception(inf_jukebox_transitioner, random_song_file):
    song = Song(random_song_file)
    song_length = int(len(song.time_series) / song.sampling_rate)
    inf_jukebox_transitioner.segment_size = song_length / 2 - 1
    inf_jukebox_transitioner.merge(song, song)
    with pytest.raises(ValueError):
        inf_jukebox_transitioner.merge(song, song)
