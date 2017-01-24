import pytest
import os
import sys
import random
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
    yield conf


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


class WithFixedClass:
    def __init__(self, song_folder, b):
        pass


@pytest.mark.parametrize("config_dict,cls,clsname,expected", [
    ({
        'a': 1,
        'b': 2
    }, NoInitClass, NoInitClass.__name__, {}),
    ({
        'song_folder': 'Wowsers I will override!',
        'b': 2
    }, WithFixedClass, WithFixedClass.__name__, {
        'song_folder': Config.FIXED_OPTIONS['song_folder'],
        'b': 2
    }),
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
    monkeypatch.setattr(config, "get_class", mock_get_class)
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
            return config.get_class(basecls, cls_name)
        else:
            monkeypatch.setattr(config, "user_config",
                                {'main': {
                                    basecls.__name__: cls_name
                                }})
            return config.get_class(basecls, None)

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


@pytest.mark.parametrize('amount', [2])
def test_parse_default_args(monkeypatch, amount):
    monkeypatch.setattr(Config, 'BASECLASSES', [BaseClassOne, BaseClassTwo])
    cfg = Config()

    # We do this test multiple times to make sure we actually override values
    for _ in range(amount):

        base_1 = cfg.user_config['BaseClassOne']
        base_2 = cfg.user_config['BaseClassTwo']

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
            for part, val in assertions['parts'].items():
                assert (part in items) != val['required']
                if part in items:
                    if random.random() > 0.5:
                        del items[part]
                    else:
                        items[part] = random.random()

        cfg.set_default_options()


def test_set_class_options(config):
    my_val = random.randint(100000, 10000000)

    def find_keys():
        for basecls, subclases in config.user_config.items():
            for subcls, values in subclases.items():
                for key in values.keys():
                    if key in config.FIXED_OPTIONS:
                        continue
                    return basecls, subcls, key
        assert False

    outercls, innercls, set_key = find_keys()

    config.update_config_class_options(outercls, innercls, {set_key: my_val})

    assert config.user_config[outercls][innercls][set_key] == my_val

    with pytest.raises(ValueError):
        config.update_config_class_options(outercls, innercls,
                                           {'song_folder': my_val})


def test_set_main_option(config, monkeypatch):
    class MyName():
        def __init__(self, num):
            self.__name__ = str(num)

    my_picker = str(random.randint(100000, 10000000))
    my_picker2 = str(random.randint(0, 100000 - 1))

    mocked_get_all_subclasses = MockingFunction(
        lambda: map(MyName, [0, my_picker2, my_picker]), simple=True)
    monkeypatch.setattr(helpers, 'get_all_subclasses',
                        mocked_get_all_subclasses)

    config.update_config_main_options({"Picker": my_picker})
    assert config.user_config['main']['Picker'] == my_picker

    config.update_config_main_options({"Picker": my_picker2})
    assert config.user_config['main']['Picker'] == my_picker2

    with pytest.raises(ValueError):
        config.update_config_main_options({"Picker": my_picker * 2})
    with pytest.raises(ValueError):
        config.update_config_main_options({"song_folder": my_picker})
