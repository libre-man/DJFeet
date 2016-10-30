import pytest
import os
import sys
from configparser import ConfigParser
from helpers import MockingFunction

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, my_path + '/../')

from dj_feet.config import Config
import dj_feet.helpers as helpers
from dj_feet.communicators import Communicator
from dj_feet.pickers import Picker
from dj_feet.controllers import Controller
from dj_feet.transitioners import Transitioner


@pytest.fixture(params=[True, False])
def boolean(request):
    yield request.param


@pytest.fixture(params=[Communicator, Picker, Controller, Transitioner])
def get_types_func(request):
    yield request.param

@pytest.fixture
def config_file():
    return os.path.join(my_path, 'test_data', 'config.cfg')


@pytest.fixture
def config(config_file):
    conf = Config()
    conf.parse_user_config(config_file)
    yield conf


def test_user_config(config, config_file):
    conf_parser = ConfigParser()
    conf_parser.read_file(open(config_file))
    assert config.user_config == conf_parser


def test_global_config(config):
    assert isinstance(config, Config)


class NoArgsClass:
    def __init__(self):
        pass


class NoInitClass:
    pass


class TwoArgsClass:
    def __init__(self, a, b):
        pass


class OnlyDefaultsClass:
    def __init__(self, a=None, b=2):
        pass


class DefaultsMixingClass:
    def __init__(self, a, b=2):
        pass


@pytest.mark.parametrize("config_dict,cls,clsname,expected", [
    ({'a': 1,
      'b': 2}, NoInitClass, NoInitClass.__name__, {}),
    ({'a': 1,
      'b': 2}, NoArgsClass, NoArgsClass.__name__, {}),
    ({}, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {}),
    ({}, TwoArgsClass, TwoArgsClass.__name__, KeyError),
    ({'a': 1}, TwoArgsClass, TwoArgsClass.__name__, KeyError),
    ({'a': 1,
      'b': 2}, TwoArgsClass, TwoArgsClass.__name__, {'a': 1,
                                                     'b': 2}),
    ({'a': 1}, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {'a': 1}),
    ({'b': 3}, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {'b': 3}),
    ({'a': 'a',
      'b': 3}, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {'a': 'a',
                                                               'b': 3}),
    ({}, DefaultsMixingClass, OnlyDefaultsClass.__name__, KeyError),
    ({'b': 3}, DefaultsMixingClass, OnlyDefaultsClass.__name__, KeyError),
    ({'a': 4,
      'b': 3}, DefaultsMixingClass, OnlyDefaultsClass.__name__, {'a': 4,
                                                                 'b': 3}),
    ({'a': 4}, DefaultsMixingClass, OnlyDefaultsClass.__name__, {'a': 4}),
    ({'a': 4,
      1: 100}, DefaultsMixingClass, OnlyDefaultsClass.__name__, {'a': 4}),
])
def test_get_class_args(config, monkeypatch, config_dict, cls, clsname,
                        expected):
    monkeypatch.setattr(config, 'user_config', {clsname: config_dict})
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            kwargs = config._get_class_args(cls, clsname)
    else:
        kwargs = config._get_class_args(cls, clsname)
        assert kwargs == expected


class A:
    pass


class B(A):
    pass


class C(B):
    def __init__(self, a, b):
        self.a = a
        self.b = b


@pytest.mark.parametrize("basecls, cls, cls_args", [(B, C, {'a': 1,
                                                            'b': 2}),
                                                    (B, A, {}),
                                                    (A, B, {}),
                                                    (A, C, {'a': 1,
                                                            'b': 2}),
                                                    (C, C, {'a': 'c',
                                                            'b': -1}), ])
def test_get_class_instance(config, monkeypatch, basecls, cls, cls_args):
    mock_get_class = MockingFunction(lambda: cls, simple=True)
    mock_get_class_args = MockingFunction(lambda: cls_args, simple=True)
    monkeypatch.setattr(config, "_get_class", mock_get_class)
    monkeypatch.setattr(config, "_get_class_args", mock_get_class_args)

    cls_instance = config._get_class_instance(basecls, cls.__name__)

    assert vars(cls_instance) == cls_args

    assert isinstance(cls_instance, cls)
    assert mock_get_class.called
    assert mock_get_class.args[0][0] == (basecls, cls.__name__)

    assert mock_get_class_args.called
    assert mock_get_class_args.args[0][0] == (cls, basecls.__name__)


@pytest.mark.parametrize("basecls, cls_name, subclasses, expected", [
    (A, B.__name__, [A, C, B], B),
    (C, A.__name__, [A, C, B], A),
    (A, A.__name__, [C, B], KeyError),
    (A, A.__name__, [], KeyError),
    (C, 'NOPE', [A, C, B], KeyError),
    (C, C.__name__, [A, C, B], C),
])
def test_get_class(config, monkeypatch, expected, basecls, cls_name,
                   subclasses, boolean):
    mock_get_all_subclasses = MockingFunction(lambda: subclasses, simple=True)
    monkeypatch.setattr(helpers, 'get_all_subclasses', mock_get_all_subclasses)

    def get():
        if boolean:
            return config._get_class(basecls, cls_name)
        else:
            monkeypatch.setattr(config, "user_config",
                                {'main': {basecls.__name__: cls_name}})
            return config._get_class(basecls, None)

    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            get()
    else:
        assert expected == get()
        assert mock_get_all_subclasses.called
        assert mock_get_all_subclasses.args[0][0] == (basecls, )

@pytest.mark.parametrize("cls", [
    (A),
    (A),
    (B),
    (B),
])
def test_get_the_class_instance(config, monkeypatch, get_types_func, cls, boolean):
    mock_get_class_instance = MockingFunction(lambda: cls(), simple=True)
    monkeypatch.setattr(config, '_get_class_instance', mock_get_class_instance)
    func = "get_" + get_types_func.__name__.lower()
    if boolean:
        inst = getattr(config, func)(cls)
        assert mock_get_class_instance.called
        assert mock_get_class_instance.args[0][0] == (get_types_func, cls,)
    else:
        inst = getattr(config, func)()
        assert mock_get_class_instance.called
        assert mock_get_class_instance.args[0][0] == (get_types_func, None,)

    assert isinstance(inst, cls)
