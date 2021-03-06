from configparser import ConfigParser
import dj_feet.helpers as helpers
from .helpers import get_args
from .communicators import Communicator
from .pickers import Picker
from .controllers import Controller
from .transitioners import Transitioner


class Config():
    """The main class for the config. This stores program config and the user
    config.
    """

    #: This are the fixed options that cannot be changed by the user.
    FIXED_OPTIONS = {
        'song_folder': None,
        'cache_dir': None,
        'output_folder': None
    }
    #: These are the default baseclasses that :func:`dj_feet.core.loop` uses.
    BASECLASSES = [Picker, Controller, Transitioner, Communicator]

    def __init__(self):
        self.user_config = {cls.__name__: dict() for cls in self.BASECLASSES}
        self.user_config['main'] = dict()
        self.set_default_options()

    def set_default_options(self):
        """Set the default options of all subclasses as the only config.

        This overrides any special config that was present in the
        `self.user_config` variable. The main section of `self.user_config` is
        the only key that is preserved.

        :returns: Nothing of value.
        """
        main_cfg = self.user_config['main']
        self.user_config = {cls.__name__: dict() for cls in self.BASECLASSES}
        self.user_config['main'] = main_cfg

        for basecls in self.BASECLASSES:
            for cls in helpers.get_all_subclasses(basecls):
                if cls.__name__ not in self.user_config[basecls.__name__]:
                    self.user_config[basecls.__name__][cls.__name__] = dict()

                defaults = cls.__init__.__defaults__
                if defaults is None:
                    continue
                # zip the default arguments with its default value and set this
                # in user_config
                for arg, val in zip(
                        get_args(cls.__init__)[-len(defaults):], defaults):
                    self.user_config[basecls.__name__][cls.__name__][arg] = val

    def update_config_main_options(self, vals):
        """Set the main options.

        This means setting the used classes for every class
        :attr:`BASECLASSES`.

        :param dict[str,str] vals: The dictionary of the mapping
                                   ``baseclass:subclass``.
        :raises ValueError: If the key you want to set is present in
                            :attr:`FIXED_OPTIONS` or if the value is not a
                            subclass of the provided key according to
                            :func:`helpers.get_all_subclasses`.
        :returns: Nothing of value
        """
        for key, value in vals.items():
            if key in self.FIXED_OPTIONS:
                raise ValueError("This item cannot be set!")
            for basecls in self.BASECLASSES:
                if basecls.__name__ != key:
                    continue
                for subcls in helpers.get_all_subclasses(basecls):
                    if subcls.__name__ == value:
                        self.user_config['main'][key] = value
                        break
                else:
                    continue
                break  # if we did break break out of this loop as well.
            else:
                raise ValueError("Wrong value encountered!")

    def update_config_class_options(self, basecls, subcls, vals):
        """Update the given parameter config values for the given ``subcls``.

        This is done by overriding any value already present in the config for
        this ``basecls`` and ``subcls`` mapping. Fixed values are not
        overridden.

        :param str basecls: The baseclass to update, it should be in
                            :attr:`BASECLASSES`.
        :param str subcls: The implementation of `basecls` to update the values
                           for.
        :param dict[str] vals: The values that should be mapped option: value
                               to pass.
        :raises ValueError: If the key of a val in `vals` is present in
                            :attr:`FIXED_OPTIONS`.
        :returns: Nothing of value.
        """
        for key, val in vals.items():
            if key in self.FIXED_OPTIONS:
                raise ValueError("This value cannot be set!")
            self.user_config[basecls][subcls][key] = val

    @staticmethod
    def get_all_options(baseclasses=None):
        """Get all options for all classes.

        :param baseclasses: The classes to use, defaults
                            to :attr:`BASECLASSES`.
        :type baseclasses: list(type) or None
        :returns: The dictionary with all options. For the format see the
                  :ref:`#sdaas protocol<sdaas-protocol>`.
        :rtype: dict
        """
        configs = dict()
        if baseclasses is None:
            baseclasses = Config.BASECLASSES
        for basecls in baseclasses:
            configs[basecls.__name__] = dict()
            for subcls in helpers.get_all_subclasses(basecls):
                configs[basecls.__name__][subcls.__name__] = dict()
                configs[basecls.__name__][subcls.__name__]['parts'] = dict()
                configs[basecls.__name__][subcls.__name__]['doc'] = dict()

                cls_doc = helpers.parse_docstring(subcls.__doc__)
                init_doc = helpers.parse_docstring(subcls.__init__.__doc__)
                param_doc = init_doc['params']

                configs[basecls.__name__][subcls.__name__]['doc'][
                    'short'] = cls_doc['short']
                configs[basecls.__name__][subcls.__name__]['doc'][
                    'long'] = cls_doc['long']

                defaults = subcls.__init__.__defaults__
                default_amount = 0
                if isinstance(defaults, tuple):
                    default_amount = len(defaults)
                var_amount = subcls.__init__.__code__.co_argcount

                for idx, arg in enumerate(get_args(subcls.__init__)):
                    if arg == "self":
                        continue
                    part = {
                        'doc': param_doc[arg] if arg in param_doc else "",
                        'fixed': arg in Config.FIXED_OPTIONS,
                        'required': idx < var_amount - default_amount
                    }
                    configs[basecls.__name__][subcls.__name__]['parts'][
                        arg] = part
        return configs

    def _get_class_args(self, cls, config_key):
        """Get the arguments for the given class from the user config.

        :param type cls: The class to find the arguments for.
        :param str config_key: The config key to use as primary key
                               in :attr:`user_config`.
        :raises LookupError: If a required argument could not be found.
        :returns: The arguments of cls
        :rtype: dict
        """
        kwargs = dict()

        for key, val in self.user_config[config_key][cls.__name__].items():
            try:
                if key in get_args(cls.__init__) and key != 'self':
                    kwargs[key] = val
            except AttributeError:
                return {}

        defaults = cls.__init__.__defaults__
        default_amount = None  # Yes None is actually correct here...
        if isinstance(defaults, tuple):
            default_amount = -len(defaults)

        for key in get_args(cls.__init__):
            if key in self.FIXED_OPTIONS:
                kwargs[key] = self.FIXED_OPTIONS[key]

        for key in get_args(cls.__init__)[:default_amount]:
            if key in self.FIXED_OPTIONS:
                continue
            if key not in kwargs and key != 'self':
                raise KeyError(
                    "Key {} not found in config but is required".format(key))

        return kwargs

    def _get_class_instance(self, basecls, cls_name):
        """Get a instance of a class for the given category with the given
        name.

        :param type basecls: The baseclass to use as category.
        :param str cls_name: The subclass to find.
        :returns: A class instance of cls_name
        :rtype: subtype of basecls
        """
        cls = self.get_class(basecls, cls_name)
        return cls(**self._get_class_args(cls, basecls.__name__))

    def get_class(self, basecls, cls_name):
        """Get a class for the given category with the given name.

        .. note:: this does not return an instance, only the class.

        :param type basecls: The base class, this should be a member of
                             :attr:`BASECLASSES`.
        :param cls_name: The name of the subclass to find. This
                         class should be a subclass of basecls. If `cls_name`
                         is none the name from ``user_config['main'][basecls]``
                         is used.
        :type cls_name: str or None
        :return: The class object with the given `cls_name`
        :rtype: type
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

        :param name: The class name of the controller to find.
        :type name: str or None
        :returns: A fresh controller:
        :rtype: subclass of :class:`dj_feet.controllers.Controller`
        """
        return self._get_class_instance(Controller, name)

    def get_picker(self, name=None):
        """Get a picker, name defaults to the name in the config.

        :param name: The class name of the picker to find.
        :type name: str or None
        :returns: A fresh picker:
        :rtype: subclass of :class:`dj_feet.pickers.Picker`
        """
        return self._get_class_instance(Picker, name)

    def get_transitioner(self, name=None):
        """Get a transitioner, name defaults to the name in the config.

        :param name: The class name of the transitioner to find.
        :type name: str or None
        :returns: A fresh transitioner:
        :rtype: subclass of :class:`dj_feet.transitioners.Transitioner`
        """
        return self._get_class_instance(Transitioner, name)

    def get_communicator(self, name=None):
        """Get a communicator, name defaults to the name in the config.

        :param name: The class name of the communicator to find.
        :type name: str or None
        :returns: A fresh communicator:
        :rtype: subclass of :class:`dj_feet.communicators.Communicator`
        """
        return self._get_class_instance(Communicator, name)
