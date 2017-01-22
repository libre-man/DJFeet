import pytest
import os
import sys
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.web as web


def test_app_test(monkeypatch):
    mocked_start = MockingFunction()
    monkeypatch.setattr(web, 'start', mocked_start)

    mocked_getenv = MockingFunction(lambda: 500, simple=True)
    monkeypatch.setattr(os, 'getenv', mocked_getenv)

    import dj_feet.wsgi as wsgi

    assert mocked_start.called
    assert mocked_getenv.called
    assert len(mocked_getenv.args) == 4

    for idx, var in enumerate([
            'SDAAS_ID', 'SDAAS_INPUT_DIR', 'SDAAS_OUTPUT_DIR',
            'SDAAS_REMOTE_URL'
    ]):
        assert var == mocked_getenv.args[idx][0][0]
