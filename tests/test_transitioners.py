import pytest
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.transitioners as transitioners


@pytest.fixture
def transitioner_base():
    yield transitioners.Transitioner()


@pytest.fixture(params=[transitioners.SimpleTransitioner])
def all_transitioners(request):
    yield request.param


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
