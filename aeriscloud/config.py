import sys
import os

from appdirs import user_config_dir, user_data_dir

from .utils import memoized

# python3 compat
if sys.version_info[0] < 3:
    import ConfigParser as configparser
else:
    import configparser


@memoized
def module_path():
    return os.path.dirname(__file__)


class Config(object):
    """
    Wrapper around ConfigParser that provides a way to check for existence
    as well as a default kwargs for get that provides a default value
    """

    def __init__(self):
        self._config = configparser.SafeConfigParser()
        self.load()

    def load(self):
        self._config = configparser.SafeConfigParser()

        if not os.path.isdir(config_dir()):
            os.makedirs(config_dir())

        if os.path.exists(config_ini_path()):
            self._config.read(config_ini_path())
        else:
            self.save()

    def has(self, section, option):
        """
        Checks if the given section and option exists

        :param section: str
        :param option: str
        :return: bool
        """
        if not self._config.has_section(section):
            return False
        return self._config.has_option(section, option)

    def get(self, section, option, **kwargs):
        """
        Get an option from the configuration, if the option does not exists
        and no default is set, raises a configparser.Error

        :param section: str
        :param option: str
        :param default: any
        :return: str
        """
        if 'default' in kwargs:
            if not self.has(section, option):
                return kwargs['default']
            del kwargs['default']
        return self._config.get(section, option, **kwargs)

    def set(self, section, option, value):
        """
        Set an option in the configuration, does not save the config

        :param section: str
        :param option: str
        :param value: any
        :return:
        """
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, option, value)

    def unset(self, section, option):
        """
        Unset an option in the configuration, does not save the config

        :param section: str
        :param option: str
        :return: bool
        """
        if not self._config.has_section(section):
            return False
        if not self._config.has_option(section, option):
            return False
        self._config.remove_option(section, option)
        return True

    def save(self):
        """
        Save the config file

        :return: bool
        """
        with os.fdopen(os.open(config_ini_path(),
                               os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                               0640), 'w') as f:
            self._config.write(f)
            return True

    def dump(self):
        items = {}
        for section in self._config.sections():
            items[section] = {}
            for key, value in self._config.items(section):
                items[section][key] = value
        return items

    def complete(self):
        """
        Checks if the configuration has all basic config items set

        :return: bool
        """

        base_conf = {
            'config': ['projects_path'],
            'github': ['enabled']
        }

        for section, items in base_conf.iteritems():
            if not self._config.has_section(section):
                return False
            for item in items:
                if not self._config.has_option(section, item):
                    return False

        if self._config.get('github', 'enabled') == 'true' and \
                not self._config.has_option('github', 'token'):
            return False

        # if no expose url, or expose url is set but no account
        if expose_url() is None or (expose_url() and
                                    not config.has('aeris', 'token')):
            return False

        return True


def inventory_path():
    """
    Return the path to the ansible inventory files

    :return:
    """
    return os.path.join(aeriscloud_path, 'ansible', 'inventory')


def config_dir():
    return user_config_dir(app_name, app_author)


def data_dir():
    return user_data_dir(app_name, app_author)


def config_ini_path():
    # if os.path.exists(os.path.join(aeriscloud_path(), '.games.ini')):
    # return os.path.join(aeriscloud_path(), '.games.ini')
    return os.path.join(config_dir(), 'config.ini')


def projects_path():
    return config.get('config', 'projects_path', default=None)


def basebox_bucket():
    return config.get('config', 'basebox_bucket', default=None)


def default_organization():
    return config.get('config', 'default_organization', default=None)


def expose_username():
    email = config.get('aeris', 'email', default=None)
    if not email:
        return None
    return email.split('@')[0]


def expose_url():
    return config.get('aeris', 'url', default=None)


def verbosity(val=None):
    if not hasattr(verbosity, "val"):
        verbosity.val = 0
    if val is None:
        return verbosity.val
    verbosity.val = val


app_name = 'AerisCloud'
app_author = 'Wizcorp'

aeriscloud_path = os.path.dirname(module_path())
config = Config()
