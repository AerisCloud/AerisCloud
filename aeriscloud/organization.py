import os

from .ansible import get_env_path
from .log import get_logger

logger = get_logger('organization')


class Organization(object):
    """
    Represents an AerisCloud organization

    :param folder: str The folder where the organization is stored
    """

    def __init__(self, name):
        self._name = name
        self._folder = get_env_path(name)
        self._config_file = os.path.join(self._folder, 'config.yml')
        self._initialized = False
        self._config = None
        self._logger = get_logger(self.folder(True), logger)

        if os.path.isfile(self._config_file):
            self._initialized = True

    def _load_config(self):
        if not os.path.isfile(self._config_file):
            self._config = {}
            return

        import yaml

        with open(self._config_file) as fd:
            self._config = yaml.load(fd) or {}

    def folder(self, base=False):
        if base:
            return os.path.basename(self._folder)
        return self._folder

    def config(self):
        if self._config is None:
            self._load_config()
        return self._config

    def basebox_url(self):
        if 'basebox_url' not in self.config():
            return None
        return self.config()['basebox_url']
