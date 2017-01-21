import pytest
import requests
import random
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.web as web
from dj_feet.pickers import Picker


class MyPicker(Picker):
    "A docstring"

    def __init__(self, param1):
        """Another docstring

        :param param1: Cool!"""
        pass


def test_setup(monkeypatch):
    my_post_request = MockingFunction()
    monkeypatch.setattr(requests, 'post', my_post_request)
    my_id = random.randint(0, 100000)
    my_addr = str(random.randint(0, 100000)) + "-this-is-me-" + str(my_id)

    web.start(str(my_id), "/in", "/out", my_addr)

    assert my_post_request.called
    assert len(my_post_request.args[0][0]) == 1
    assert my_post_request.args[0][0][0] == my_addr + '/im_alive'

    data = my_post_request.args[0][1]['data']
    assert data['id'] == my_id
    assert 'MyPicker' in data['options']['Picker']
    assert 'param1' in data['options']['Picker']['MyPicker']['parts']
    assert data['options']['Picker']['MyPicker']['parts']['param1']['required']
