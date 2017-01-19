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
    ({
        'a': 1,
        'b': 2
    }, NoInitClass, NoInitClass.__name__, {}),
    ({
        'a': 1,
        'b': 2
    }, NoArgsClass, NoArgsClass.__name__, {}),
    ({}, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {}),
    ({}, TwoArgsClass, TwoArgsClass.__name__, KeyError),
    ({
        'a': 1
    }, TwoArgsClass, TwoArgsClass.__name__, KeyError),
    ({
        'a': 1,
        'b': 2
    }, TwoArgsClass, TwoArgsClass.__name__, {
        'a': 1,
        'b': 2
    }),
    ({
        'a': 1
    }, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {
        'a': 1
    }),
    ({
        'b': 3
    }, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {
        'b': 3
    }),
    ({
        'a': 'a',
        'b': 3
    }, OnlyDefaultsClass, OnlyDefaultsClass.__name__, {
        'a': 'a',
        'b': 3
    }),
    ({}, DefaultsMixingClass, OnlyDefaultsClass.__name__, KeyError),
    ({
        'b': 3
    }, DefaultsMixingClass, OnlyDefaultsClass.__name__, KeyError),
    ({
        'a': 4,
        'b': 3
    }, DefaultsMixingClass, OnlyDefaultsClass.__name__, {
        'a': 4,
        'b': 3
    }),
    ({
        'a': 4
    }, DefaultsMixingClass, OnlyDefaultsClass.__name__, {
        'a': 4
    }),
    ({
        'a': 4,
        1: 100
    }, DefaultsMixingClass, OnlyDefaultsClass.__name__, {
        'a': 4
    }),
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


@pytest.mark.parametrize("basecls, cls, cls_args", [
    (B, C, {
        'a': 1,
        'b': 2
    }),
    (B, A, {}),
    (A, B, {}),
    (A, C, {
        'a': 1,
        'b': 2
    }),
    (C, C, {
        'a': 'c',
        'b': -1
    }),
])
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
                                {'main': {
                                    basecls.__name__: cls_name
                                }})
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
def test_get_the_class_instance(config, monkeypatch, get_types_func, cls,
                                boolean):
    mock_get_class_instance = MockingFunction(cls, simple=True)
    monkeypatch.setattr(config, '_get_class_instance', mock_get_class_instance)
    func = "get_" + get_types_func.__name__.lower()
    if boolean:
        inst = getattr(config, func)(cls)
        assert mock_get_class_instance.called
        assert mock_get_class_instance.args[0][0] == (
            get_types_func,
            cls, )
    else:
        inst = getattr(config, func)()
        assert mock_get_class_instance.called
        assert mock_get_class_instance.args[0][0] == (
            get_types_func,
            None, )

    assert isinstance(inst, cls)


class BaseClassOne():
    pass


class SubClassOneOne(BaseClassOne):
    """This should not influence params.

    :param nice: wow not showing."""
    assertions = {
        'doc': {
            'short': "This should not influence params.",
            'long': ""
        },
        'parts': {
            'required': {
                'fixed': False,
                'required': True,
                'doc': "This is required"
            },
            'non_required': {
                'fixed': False,
                'required': False,
                'doc': "This is not required"
            }
        }
    }

    def __init__(self, required, non_required=None):
        """This is a function

        :param required: This is required
        :param non_required: This is not required
        """
        pass


class SubClassOneTwo(BaseClassOne):
    """

    This should be long


    """
    assertions = {
        'doc': {
            'short': '',
            'long': "This should be long"
        },
        'parts': {
            'non_required2': {
                'fixed': False,
                'required': False,
                'doc': "This is not required"
            }
        }
    }

    def __init__(self, non_required2=None):
        """This is a function

        :param non_required2: This is not required
        """
        pass


class BaseClassTwo():
    pass


class SubClassTwoOne(BaseClassTwo):
    """This is short

    And this is very long.
    """
    assertions = {
        'doc': {
            "short": "This is short",
            'long': "And this is very long."
        },
        'parts': {}
    }

    def __init__(self):
        """This is a function
        """
        pass


class SubClassTwoTwo(BaseClassTwo):
    assertions = {
        'doc': {
            'short': "",
            'long': ""
        },
        'parts': {
            'song_folder': {
                'fixed': True,
                'required': True,
                'doc': "This is required but fixed"
            },
        }
    }

    def __init__(self, song_folder):
        """This is a function

        :param song_folder: This is required but fixed
        """
        pass


class SubClassTwoThree(BaseClassTwo):
    "This is subclass 23"
    assertions = {
        'doc': {
            'short': "This is subclass 23",
            'long': ''
        },
        'parts': {
            'required2': {
                'fixed': False,
                'required': True,
                'doc': ""
            },
        }
    }

    def __init__(self, required2):
        """This is a function
        """
        pass


@pytest.mark.parametrize("default", [True, False])
def test_get_all_options(default):
    if default:
        res = Config.get_all_options()
        assert len(res) == 4
    else:
        res = Config.get_all_options([BaseClassOne, BaseClassTwo])
        assert len(res) == 2
        base_1 = res['BaseClassOne']
        base_2 = res['BaseClassTwo']

        assert len(base_1) == 2
        assert len(base_2) == 3

        assert 'SubClassOneOne' in base_1
        assert 'SubClassOneTwo' in base_1

        assert 'SubClassTwoOne' in base_2
        assert 'SubClassTwoTwo' in base_2
        assert 'SubClassTwoThree' in base_2

        all_subs = base_1.copy()
        all_subs.update(base_2)

        for name, items in all_subs.items():
            assertions = globals()[name].assertions
            for a_name, a_value in assertions['parts'].items():
                assert a_name in items['parts']
                for part in ['fixed', 'required', 'doc']:
                    assert a_value[part] == items['parts'][a_name][part]
                del items['parts'][a_name]
            assert items['parts'] == {}
            del items['parts']
            assert items['doc']['short'] == assertions['doc']['short']
            assert items['doc']['long'] == assertions['doc']['long']
            del items['doc']
            assert items == {}
