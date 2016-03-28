import json
import os
import sys

from .config import config, expose_url, \
    configparser, data_dir
from .log import get_logger
from .utils import local_ip


class ExposeError(RuntimeError):
    def __init__(self, e):
        super(RuntimeError, self).__init__(e.message)
        self.e = e


class ExposeTimeout(ExposeError):
    pass


class ExposeConnectionError(ExposeError):
    pass


class Expose(object):
    def __init__(self):
        self._config = configparser.SafeConfigParser()
        self._logger = get_logger('expose')

        if not os.path.isdir(data_dir()):
            os.makedirs(data_dir())

        if os.path.exists(self.file()):
            self.load()
        else:
            self.save()

    def load(self):
        self._config.read(self.file())

    def file(self):
        return os.path.join(data_dir(), 'expose.ini')

    def save(self):
        with open(self.file(), 'w') as f:
            self._config.write(f)
            return True

    def start(self):
        config.set('aeris', 'enabled', 'true')
        config.save()

    def stop(self):
        config.set('aeris', 'enabled', 'false')
        config.save()

    def enabled(self):
        default = 'true'
        if not config.get('aeris', 'url', default=None):
            default = 'false'
        return config.get('aeris', 'enabled', default=default) == 'true'

    def announce(self):
        client = expose_client()
        if not client:
            return False

        service_list = [{'service': service['service'],
                         'port': service['port']}
                        for service in self.list()]
        return client.service(service_list, replace=True)

    def add(self, box, announce=True):
        project_name = box.project.name()
        forwards = box.forwards()

        if 'web' not in forwards:
            return

        port = forwards['web']['host_port']

        if not self._config.has_section(project_name):
            self._config.add_section(project_name)

        self._logger.info('adding %s-%s (port %s)' %
                          (project_name, box.name(), port))
        self._config.set(project_name, box.name(), port)

        self.save()

        if self.enabled() and announce:
            self.announce()

    def remove(self, box, announce=False):
        project_name = box.project.name()

        if not self._config.has_section(project_name):
            return

        self._config.remove_option(project_name, box.name())

        if not self._config.items(project_name):
            self._config.remove_section(project_name)

        self.save()

        if self.enabled() and announce:
            self.announce()

    def list(self):
        services = []

        for section in self._config.sections():
            infras = self._config.items(section)
            for infra, port in infras:
                services.append({
                    'service': '.'.join([infra, section]),
                    'project': section,
                    'infra': infra,
                    'port': port
                })

        return services


class Client:
    def __init__(self, email, username=None, password=None, token=None,
                 api_url=None, fullname=None):
        if not api_url and config.has('aeris', 'url'):
            api_url = config.get('aeris', 'url')

        import requests

        self._requests = requests
        self._email = email
        self._api_url = api_url
        self._username = username or email.split('@')[0]
        self._token = token

        if not self._api_url.startswith('http'):
            self._api_url = 'http://%s' % self._api_url

        if not token and password:
            err, res = self.signup(password, fullname)
            if err:
                if not err.startswith('User already exists'):
                    raise RuntimeError(err)
                res = self.get_token(password)
            self._token = res['token']

    def get_email(self):
        return self._email

    def _do_request(self, type, *args, **kwargs):
        from requests.exceptions import Timeout, ConnectionError

        met = self._requests.get
        if type == 'post':
            met = self._requests.post

        try:
            return met(*args, timeout=5, **kwargs)
        except Timeout as e:
            trace = sys.exc_info()[2]
            raise ExposeTimeout(e), None, trace
        except ConnectionError as e:
            trace = sys.exc_info()[2]
            raise ExposeConnectionError(e), None, trace

    def set_token(self, token):
        self._token = token

    def get_headers(self, type=None):
        if type == 'token':
            return {
                'content-type': 'application/json',
                'Auth-Username': self._username,
                'Auth-Token': self._token
            }
        else:
            return {'content-type': 'application/json'}

    def get_vms(self):
        url = self._api_url + '/api/vms'

        r = self._do_request('get', url, headers=self.get_headers())

        if r.status_code == 400:
            return r.text.strip('"'), None

        r.raise_for_status()

        return r.json()

    def signup(self, password, fullname=None):
        if not self._api_url:
            return

        url = self._api_url + '/api/signup'

        payload = {
            'username': self._username,
            'password': password,
            'details': {
                'email': self._email,
                'localip': local_ip(),
                'fullname': fullname
            }
        }

        r = self._requests.post(url,
                                data=json.dumps(payload),
                                headers=self.get_headers())

        if r.status_code == 400:
            return r.text.strip('"'), None

        r.raise_for_status()

        return None, r.json()

    def get_user(self, username):
        url = self._api_url + '/api/users/%s' % username

        r = self._requests.get(url, headers=self.get_headers('token'))
        if r.status_code == 401:
            return None

        r.raise_for_status()

        return r.json()

    def update(self):
        url = self._api_url + '/api/update'

        payload = {
            'localip': local_ip()
        }

        r = self._requests.post(url,
                                data=json.dumps(payload),
                                headers=self.get_headers('token'))
        r.raise_for_status()

        return r.json()

    def service(self, services, replace=False):
        if replace:
            url = self._api_url + '/api/replace'
        else:
            url = self._api_url + '/api/service'

        payload = {
            'localip': local_ip(),
            'services': services
        }

        r = self._do_request('post', url,
                             data=json.dumps(payload),
                             headers=self.get_headers('token'))
        r.raise_for_status()

        return r.json()

    def get_token(self, password=None):
        if self._token:
            return self._token

        from requests.auth import HTTPBasicAuth

        url = self._api_url + '/api/token'
        r = self._requests.get(url,
                               headers=self.get_headers(),
                               auth=HTTPBasicAuth(self._username, password))
        r.raise_for_status()
        return r.json()


def expose_client():
    """
    Return the expose client from the config
    :return:
    """
    if not expose_url():
        return None

    email = config.get('aeris', 'email', default=None)
    token = config.get('aeris', 'token', default=None)

    if not email or not token:
        return None

    return Client(email, token=token)


expose = Expose()
