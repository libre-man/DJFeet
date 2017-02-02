from libfaketime import reexec_if_needed
import os
import random
import pytest
import logging

logging.basicConfig(level=logging.ERROR)

my_path = os.path.dirname(os.path.abspath(__file__))


def pytest_configure():
    reexec_if_needed()


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="run slow tests")


@pytest.fixture
def songs_dir():
    yield os.path.join(my_path, 'test_data', 'songs')


@pytest.fixture
def random_song_file(songs_dir):
    song_files = [
        os.path.join(songs_dir, f) for f in os.listdir(songs_dir)
        if os.path.isfile(os.path.join(songs_dir, f)) and f != ".DS_Store"
    ]
    yield random.choice(song_files)


@pytest.fixture
def random_song_files(songs_dir):
    song_files = [
        os.path.join(songs_dir, f) for f in os.listdir(songs_dir)
        if os.path.isfile(os.path.join(songs_dir, f)) and f != ".DS_Store"
    ]
    random.shuffle(song_files)
    yield song_files
