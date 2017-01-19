from configparser import ConfigParser
import dj_feet.helpers as helpers
from .communicators import Communicator
from .pickers import Picker
from .controllers import Controller
from .transitioners import Transitioner


class Config():
    """The main class for the config. This stores program config and the user
    config.
    """
    FIXED_OPTIONS = ['song_folder']

    def __init__(self):
        self.user_config = ConfigParser()

    def parse_user_config(self, config_file):
        """Read the user config for the given config file. This eagerly checks
        if the config_file can be opened.
        """
        self.user_config.read_file(open(config_file))

    @staticmethod
    def get_all_options(baseclasses=None):
        """Get all options for all classes according to this scheme:"""
        configs = dict()
        if baseclasses is None:
            baseclasses = [Picker, Controller, Transitioner, Communicator]
        for basecls in baseclasses:
            configs[basecls.__name__] = dict()
            for subcls in helpers.get_all_subclasses(basecls):
                configs[basecls.__name__][subcls.__name__] = dict()
                defaults = subcls.__init__.__defaults__
                default_amount = 0
                if isinstance(defaults, tuple):
                    default_amount = len(defaults)
                var_amount = len(subcls.__init__.__code__.co_varnames)
                doc = helpers.parse_docstring(subcls.__init__.__doc__)
                param_doc = doc['params']
                for idx, arg in enumerate(
                        subcls.__init__.__code__.co_varnames):
                    if arg == "self":
                        continue
                    configs[basecls.__name__][subcls.__name__][arg] = {
                        'doc': param_doc[arg] if arg in param_doc else "",
                        'fixed': arg in Config.FIXED_OPTIONS,
                        'required': idx < var_amount - default_amount
                    }
        return configs

    def _get_class_args(self, cls, config_key):
        """Get the arguments for the given class from the user config. If a
        required argument cannot be found this raises a LookupError.
        """
        kwargs = dict()
        for key, val in self.user_config[config_key].items():
            try:
                if key in cls.__init__.__code__.co_varnames and key != 'self':
                    kwargs[key] = val
            except AttributeError:
                return {}
        defaults = cls.__init__.__defaults__
        default_amount = None
        if isinstance(defaults, tuple):
            default_amount = -len(defaults)
        for key in cls.__init__.__code__.co_varnames[:default_amount]:
            if key not in kwargs and key != 'self':
                raise KeyError(
                    "Key {} not found in config but is required".format(key))
        return kwargs

    def _get_class_instance(self, basecls, cls_name):
        """Get a instance of a class for the given category with the given
        name.
        """
        cls = self._get_class(basecls, cls_name)
        return cls(**self._get_class_args(cls, basecls.__name__))

    def _get_class(self, basecls, cls_name):
        """Get a class for the given category with the given name. Note: this
        does not return an instance, only the class.
        """
        if cls_name is None:
            cls_name = self.user_config["main"][basecls.__name__]
        for cls in helpers.get_all_subclasses(basecls):
            if cls.__name__ == cls_name:
                return cls
        raise KeyError("Class {} could not be found as a subclass of {}".
                       format(cls_name, basecls.__name__))

    def get_controller(self, name=None):
        """Get a controller, name defaults to the name in the config.
        """
        return self._get_class_instance(Controller, name)

    def get_picker(self, name=None):
        """Get a picker, name defaults to the name in the config.
        """
        return self._get_class_instance(Picker, name)

    def get_transitioner(self, name=None):
        """Get a transitioner, name defaults to the name in the config.
        """
        return self._get_class_instance(Transitioner, name)

    def get_communicator(self, name=None):
        """Get a communicator, name defaults to the name in the config.
        """
        return self._get_class_instance(Communicator, name)
