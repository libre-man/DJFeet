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


def test_base_transitioner(transitioner_base):
    assert isinstance(transitioner_base, transitioners.Transitioner)
    with pytest.raises(NotImplementedError):
        transitioner_base.merge(None, None)
    with pytest.raises(NotImplementedError):
        transitioner_base.write_sample(None)
