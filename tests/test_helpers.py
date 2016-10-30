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
    struct2 = helpers.SongStruct(file_location=file_location,
                                 start_pos=start_pos,
                                 end_pos=end_pos)

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


@pytest.mark.parametrize(
    "baseclass, expected",
    [(SubClassOneOne, {SubClassTwoOne}),
    (A, {B}),
    (SubClassOneTwo, set()),
    (BaseClass, {SubClassOneOne, SubClassOneTwo, SubClassMultipleDouble, SubClassMultiple, SubClassTwoOne}),
 ])
def test_get_all_subclasses(baseclass, expected):
    assert helpers.get_all_subclasses(baseclass) == expected
