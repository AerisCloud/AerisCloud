import os

from slugify import slugify

from .box import Box, BoxList
from .config import projects_path, aeriscloud_path
from .log import get_logger
from .utils import jinja_env
from .vagrant import run

logger = get_logger('project')

BASEBOX_DEFAULT_CPU = 1
BASEBOX_DEFAULT_RAM = 1024


# caches the project list but allows reloading the list
# TODO: extend dict and provide the right helpers
class ProjectList(object):
    def __init__(self):
        self.project_list = {}

    def load(self):
        self.project_list = {}

        search_path = projects_path()
        if not os.path.isdir(search_path):
            return

        sub_files = [os.path.join(search_path, name)
                     for name in os.listdir(search_path)]
        for project_dir in sub_files:
            if not os.path.isdir(project_dir):
                continue

            if not os.path.isfile(os.path.join(project_dir,
                                               '.aeriscloud.yml')):
                continue

            project = Project(project_dir)
            if project._initialized and project.name() \
                    and project.name().lower() not in self.project_list:
                self.project_list[project.name().lower()] = project

    def __call__(self):
        # lazy loading
        if not self.project_list:
            self.load()
        return self.project_list


def all():
    """
    Return every projects available on the local host
    :return: list[Project]
    """
    return projects().values()


def get(name):
    """
    Return the project corresponding to the given project name or directory

    :param name: str
    :return: Project|None
    """
    project_list = projects()
    if name in project_list:
        return project_list[name]
    if os.path.isdir(os.path.join(projects_path(), name)):
        return Project(os.path.join(projects_path(), name))
    return None


def from_cwd():
    path = os.getcwd()
    pro_path = projects_path()

    # walk path upward until we find a .aeriscloud.yml file or until we
    # reach the project folder
    while True:
        pro = from_path(path)

        if pro:
            return pro

        if path == pro_path or not path.startswith(pro_path):
            break

        path = os.path.dirname(path)

    return None


def from_path(path):
    """
    Return the project stored in the given folder if any

    :return: Project|None
    """
    if not os.path.isfile(os.path.join(path, '.aeriscloud.yml')):
        return None

    return Project(path)


class Project(object):
    """
    Represents an AerisCloud project

    :param folder: str The folder where the project is stored
    """

    def __init__(self, folder):
        self._folder = folder
        self._config_file = os.path.join(self._folder, '.aeriscloud.yml')
        self._initialized = False
        self._config = None
        self._boxes = BoxList()
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

    def _load_infra(self):
        if self._boxes:
            return
        # We store boxes in a list as python dicts are not ordered
        if 'boxes' in self.config():
            self._boxes = BoxList([Box(self, box)
                                  for box in self.config()['boxes']])

    def initialized(self):
        return self._initialized

    def name(self):
        """
        Return the name of the project
        :return: str
        """
        if not self._config or 'project_name' not in self.config():
            return self.folder(True)
        return self.config()['project_name']

    def set_name(self, name):
        self.config()['project_name'] = name
        self._logger = get_logger(self.name(), logger)

    def get_production_url(self):
        if 'production_url' not in self.config():
            return None
        return self.config()['production_url']

    def id(self):
        if 'id' not in self.config():
            return None
        return self.config()['id']

    def set_id(self, project_id):
        self.config()['id'] = project_id

    def organization(self):
        if 'organization' not in self.config():
            return None
        return self.config()['organization']

    def set_organization(self, organization):
        self.config()['organization'] = organization

    def services(self):
        if 'services' not in self.config():
            return []
        return self.config()['services']

    def set_services(self, services):
        self.config()['services'] = services

    def add_box(self, basebox, basebox_url=None):
        if 'boxes' not in self.config():
            self.config()['boxes'] = []

        if 'basebox' not in basebox:
            raise ValueError('Invalid basebox dict provided')

        basebox.setdefault('name', slugify(basebox['basebox']))
        basebox.setdefault('cpu', BASEBOX_DEFAULT_CPU)
        basebox.setdefault('ram', BASEBOX_DEFAULT_RAM)

        if basebox in self.config()['boxes']:
            return

        if basebox_url:
            self.config()['basebox_url'] = basebox_url

        self.config()['boxes'].append(basebox)
        self._load_infra()

    def folder(self, base=False):
        if base:
            return os.path.basename(self._folder)
        return self._folder

    def config(self):
        if self._config is None:
            self._load_config()
            self._load_infra()
        return self._config

    def config_file(self):
        return self._config_file

    def boxes(self):
        """
        Return the list of boxes available for this project
        :return: BoxList[Box]
        """
        self._load_infra()
        return self._boxes

    def rsync_enabled(self):
        return 'use_rsync' in self.config() and self.config()['use_rsync']

    def box(self, name=''):
        """
        Retrieve a box by name
        :param name: str
        :return: Box|None
        """
        self._load_infra()
        if not self._boxes:
            return None
        if not name:
            return self.boxes()[0]
        for box in self._boxes:
            if box.name() == name:
                return box
        return None

    def save(self):
        self._logger.info('writing .aeriscloud.yml')

        env = jinja_env()
        env.filters['yaml'] = _yaml_filter
        config = env.get_template('aeriscloud.yml.j2') \
            .render(config=_ProjectConfig(self.config()))

        with open(self._config_file, 'w') as fd:
            fd.write(config)
            self._initialized = True

    def vagrant(self, *args, **kwargs):
        self._logger.info('running: vagrant %s', ' '.join(args))
        return run(self, *args, **kwargs)

    def vagrant_dir(self):
        return os.path.join(self.folder(), '.vagrant')

    def vagrant_working_dir(self):
        return aeriscloud_path

    def endpoints(self):
        if 'browse' in self.config():
            return self.config()['browse']
        else:
            return {}

    def __repr__(self):
        return '<Project %s [%s]>' % (self.name(), self._folder)


def _yaml_filter(val, name=None):
    import yaml

    if name:
        return yaml.dump({name: val}, default_flow_style=False)
    return yaml.dump(val, default_flow_style=False)


class _ProjectConfig():
    def __init__(self, config):
        self._config = config
        self._accessed = []

    def __getattr__(self, key):
        if key not in self._config:
            return None
        if key not in self._accessed:
            self._accessed.append(key)
        return self._config[key]

    def extra(self):
        return dict([(key, item) for key, item in self._config.iteritems()
                     if key not in self._accessed])


# load projects on import
projects = ProjectList()
