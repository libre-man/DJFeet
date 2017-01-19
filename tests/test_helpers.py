import pytest
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

import dj_feet.helpers as helpers


@pytest.mark.parametrize("file_location, start_pos, end_pos", [('/', 2, None)])
def test_song_struct(file_location, start_pos, end_pos):
    struct = helpers.SongStruct(file_location, start_pos, end_pos)
    struct2 = helpers.SongStruct(
        file_location=file_location, start_pos=start_pos, end_pos=end_pos)

    assert struct[0] == file_location
    assert struct[1] == start_pos
    assert struct[2] == end_pos

    assert struct.file_location == file_location
    assert struct.start_pos == start_pos
    assert struct.end_pos == end_pos

    assert struct == struct2


class BaseClass:
    pass


class Stub:
    pass


class A:
    pass


class B(A):
    pass


class SubClassOneOne(BaseClass):
    pass


class SubClassOneTwo(BaseClass):
    pass


class SubClassTwoOne(SubClassOneOne):
    pass


class SubClassMultiple(dict, BaseClass):
    pass


class SubClassMultipleDouble(SubClassMultiple, Stub):
    pass


@pytest.mark.parametrize("baseclass, expected", [
    (SubClassOneOne, {SubClassTwoOne}),
    (A, {B}),
    (SubClassOneTwo, set()),
    (BaseClass, {
        SubClassOneOne, SubClassOneTwo, SubClassMultipleDouble,
        SubClassMultiple, SubClassTwoOne
    }),
])
def test_get_all_subclasses(baseclass, expected):
    assert helpers.get_all_subclasses(baseclass) == expected


@pytest.mark.parametrize("desc_short, desc_long, removed, params,returns", [
    ("A very short description", "This is a long description\nwith\nnewlines",
     "", {
         "this_is_a_value": ("long_type", "Wow what a nice value!\nWow"),
         "An_int": ("int", "me is normal for me")
     }, "Return a nice int\nright"),
    ("", "This is a long description\nwith\nnewlines", "", {
        "this_is_a_value": ("another_type", "Wow what a nice value!\nWow"),
        "An_int": ("int", "me is normal for me")
    }, "Return a nice int\nright"),
    ("", "This is a long description\nwith\nnewlines\n\n", "", {},
     "Return a nice int\nright"),
    ("", "This is a long description\nwith\nnewlines\n\n",
     ":rtype: int\n     :type priority:BLAA", {
         "int": ("a nice integer", "5")
     }, "Return a nice int\nright"),
])
def test_parse_docstring(desc_short, desc_long, params, returns, removed):
    string = desc_short + "\n\n" + desc_long + "\n\n" + removed + "\n\n"
    for key, desc in params.items():
        string += ":param " + desc[0] + " " + key + ": " + desc[1] + "\n"
    string += ":returns: " + returns
    res = helpers.parse_docstring(string)
    for key, val in params.items():
        assert key in res['params']
        assert res['params'][key] == val[1]
    assert res['returns'] == returns
    assert res['short'] == desc_short.strip()
    assert res['long'] == desc_long.strip()
