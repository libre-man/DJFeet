import pytest
import os
import sys
import numpy
import librosa

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.song as song


@pytest.fixture
def no_process_base_song(random_song_file):
    yield song.Song(random_song_file, process=False)


@pytest.fixture
def process_base_song(random_song_file):
    yield song.Song(random_song_file)


def test_no_process_data(no_process_base_song):
    assert no_process_base_song.tempo is None
    assert no_process_base_song.beat_track is None
    assert no_process_base_song.time_series is None
    assert no_process_base_song.sampling_rate is None
    no_process_base_song.set_process_data()
    assert isinstance(no_process_base_song.tempo, numpy.float)
    assert isinstance(no_process_base_song.beat_track, numpy.ndarray)
    assert isinstance(no_process_base_song.time_series, numpy.ndarray)
    assert isinstance(no_process_base_song.sampling_rate, int)


def test_process_data(process_base_song):
    assert isinstance(process_base_song.tempo, float)
    assert isinstance(process_base_song.beat_track, numpy.ndarray)
    assert isinstance(process_base_song.time_series, numpy.ndarray)
    assert isinstance(process_base_song.sampling_rate, int)


@pytest.mark.parametrize(
    "begin,amount,size",
    [(True, 1, 30), (False, 2, 15), (True, 2, 15), (True, 30, 1)])
def test_next_segment(process_base_song, begin, amount, size):
    start, end = librosa.core.time_to_samples(
        numpy.array([0, size]), process_base_song.sampling_rate)
    delta = end - start
    for x in range(amount):
        out = process_base_song.next_segment(size, begin=begin)
        if x == 0 and begin:
            assert out[0] == 0
        elif x > 0:
            assert out[0] != 0
        assert out[0] < out[1]
        assert delta == out[1] - out[0]
        begin = False


@pytest.mark.parametrize("start,frames,expected",
                         [(10, 0, 0), (0, 0, 0), (-1, -1, -1)])
def test_time_delta(process_base_song, start, frames, expected):
    if frames < 0:
        start = 0
        frames = len(process_base_song.time_series) - 1
        expected = librosa.samples_to_time(
            numpy.array([frames]), process_base_song.sampling_rate)[0]
    assert process_base_song.time_delta(start, start + frames) == expected


def test_frame_to_segment_time(process_base_song):
    pass


@pytest.mark.parametrize("time, start", [(10, 0), (0, 0), (25, 10)])
def test_frame_to_segment_time(process_base_song, time, start):
    frame_idx = process_base_song.frame_to_segment_time(time, start)
    if time == 0:
        assert frame_idx == start
    assert process_base_song.time_delta(start, frame_idx) == time


@pytest.mark.parametrize("start, end, expected",
                         [(0, 50000, True), (0, 0, False), (1000, 0, False),
                          (1000, 1100, False), (50000, 100000, True)])
def test_beat_tracks_in_segement(process_base_song, start, end, expected):
    beats = process_base_song.beat_tracks_in_segment(start, end)
    if expected:
        assert beats
    else:
        assert not beats
