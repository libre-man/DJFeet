import os
import pytest
import random

my_path = os.path.dirname(os.path.abspath(__file__))

EPSILON = 0.000000001

slow = pytest.mark.skipif(
    not pytest.config.getoption("--runslow"),
    reason="need --runslow option to run")


@pytest.fixture
def songs_dir():
    yield os.path.join(my_path, 'test_data', 'songs')


@pytest.fixture
def random_song_file(songs_dir):
    song_files = [
        os.path.join(songs_dir, f) for f in os.listdir(songs_dir)
        if os.path.isfile(os.path.join(songs_dir, f))
    ]
    yield random.choice(song_files)


@pytest.fixture
def random_song_files(songs_dir):
    song_files = [
        os.path.join(songs_dir, f) for f in os.listdir(songs_dir)
        if os.path.isfile(os.path.join(songs_dir, f))
    ]
    random.shuffle(song_files)
    yield song_files


class MockingFunction():
    def __init__(self, func=None, simple=False, pack=False, amount=False):
        self.called = False
        self.args = list()
        self.func = func
        self.simple = simple
        self.pack = pack
        self.amount = amount
        self._amount = 0

    def __call__(self, *args, **kwargs):
        self.called = True
        self.args.append((args, kwargs))
        self._amount += 1
        if self.func is not None:
            if self.simple:
                return self.func()
            elif self.pack:
                return self.func(args)
            elif self.amount:
                return self.func(self._amount)
            else:
                return self.func(*args, **kwargs)
