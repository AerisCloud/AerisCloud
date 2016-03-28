from __future__ import print_function, absolute_import

import os

from subprocess32 import Popen, PIPE, call

from .config import aeriscloud_path, verbosity, data_dir
from .log import get_logger
from .utils import quote, timestamp

ansible_path = os.path.join(aeriscloud_path, 'ansible')
plugin_path = os.path.join(ansible_path, 'plugins')
job_path = os.path.join(ansible_path, 'jobs')
inventory_path = os.path.join(data_dir(), 'inventory')
organization_path = os.path.join(data_dir(), 'organizations')

logger = get_logger('ansible')


def ansible_env(env):
    env['PATH'] = os.pathsep.join([
        env['PATH'],
        os.path.join(aeriscloud_path, 'venv/bin')
    ])

    # disable buffering for ansible
    env['PYTHONUNBUFFERED'] = '1'

    env['ANSIBLE_BASE_PATH'] = ansible_path
    env['ANSIBLE_ACTION_PLUGINS'] = os.path.join(plugin_path, 'actions')
    env['ANSIBLE_CALLBACK_PLUGINS'] = os.path.join(plugin_path, 'callbacks')
    env['ANSIBLE_CONNECTION_PLUGINS'] = os.path.join(plugin_path,
                                                     'connections')
    env['ANSIBLE_FILTER_PLUGINS'] = os.path.join(plugin_path, 'filters')
    env['ANSIBLE_LOOKUP_PLUGINS'] = os.path.join(plugin_path, 'lookups')
    env['ANSIBLE_VARS_PLUGINS'] = os.path.join(plugin_path, 'vars')
    env['ANSIBLE_NOCOWS'] = '1'
    env['ANSIBLE_FORCE_COLOR'] = '1'
    env['DISPLAY_SKIPPED_HOSTS'] = 'false'

    env['ANSIBLE_ROLES_PATH'] = os.path.join(ansible_path, 'roles')
    env['ANSIBLE_LIBRARY'] = os.path.join(ansible_path, 'library')

    return env


class ACHost(object):
    """
    Wrap an host from an aeriscloud inventory and provides ssh informations
    for scripts
    """

    def __init__(self, inventory, hostname):
        from ansible.inventory import Inventory as AnsibleInventory

        inv_file = os.path.join(inventory_path, inventory)
        if not os.path.isfile(inv_file):
            raise IOError('Inventory %s does not exists' % inventory)
        self._name = inventory
        self._hostname = hostname
        self._inventory = AnsibleInventory(host_list=inv_file)
        self._host = self._inventory.get_host(hostname)
        if not self._host:
            raise NameError('Host "%s" not found in the inventory %s'
                            % (hostname, inventory))
        self._vars = self._host.get_variables()

    def ssh_host(self):
        if 'ansible_ssh_host' in self._vars:
            return self._vars['ansible_ssh_host']
        return self._hostname

    def ssh_key(self):
        if 'ansible_ssh_private_key_file' in self._vars:
            return self._vars['ansible_ssh_private_key_file']
        return None

    def ssh_user(self):
        if 'ansible_ssh_user' in self._vars:
            return self._vars['ansible_ssh_user']

        if 'username' in self._vars:
            return self._vars['username']

        return None

    def variables(self):
        return self._vars


def get_organization_list():
    if not os.path.exists(organization_path):
        return []

    return [organization
            for organization in os.listdir(organization_path)
            if organization[0] != '.']


def get_env_path(organization):
    return os.path.join(organization_path, organization)


def get_env_file(organization, environment):
    env_playbook = os.path.join(get_env_path(organization),
                                'env_%s.yml' % environment)
    if not os.path.isfile(env_playbook):
        raise IOError('Environment %s does not exists' % environment)
    return env_playbook


def list_jobs():
    jobs = list()
    with open(os.path.join(data_dir(), 'jobs-cache')) as jc:
        for job_name in jc:
            job_name = job_name.strip()
            job_desc = None
            with open(get_job_file(job_name)) as f:
                line = f.readline()
                if line.startswith('# '):
                    job_desc = line[2:].strip()

            jobs.append((job_name, job_desc))
    return jobs


def get_job_file(job):
    try:
        organization, role_name, job_name = job.split('/', 2)
    except ValueError:
        raise NameError('Invalid job name "%s"' % job)

    job_playbook = os.path.join(data_dir(), 'organizations', organization,
                                'roles', role_name,
                                'jobs', '%s.yml' % job_name)
    if not os.path.isfile(job_playbook):
        job_playbook = os.path.join(data_dir(), 'organizations', organization,
                                    'roles', 'aeriscloud.%s' % role_name,
                                    'jobs', '%s.yml' % job_name)
        if not os.path.isfile(job_playbook):
            raise IOError('Job %s does not exists' % job)
    return job_playbook


def get_inventory_file(inventory):
    inv_file = os.path.join(inventory_path, inventory)
    if not os.path.isfile(inv_file):
        raise IOError('Inventory %s does not exists' % inventory)
    return inv_file


def get_inventory_list():
    """
    Return the list of inventory files found in the AerisCloud inventory
    directory
    :return: List of inventory files
    :rtype: List
    """
    inventory_list = []
    for dirname, dirnames, filenames \
            in os.walk(inventory_path):
        if os.sep + '.git' in dirname:
            continue

        for filename in filenames:
            if filename[0] != '.':
                path = os.path.join(dirname, filename)
                inventory_list.append([
                    inventory_path,
                    os.path.relpath(path, inventory_path)
                ])
    return inventory_list


def run_job(job, inventory, *args, **kwargs):
    return run_playbook(get_job_file(job), get_inventory_file(inventory),
                        *args, **kwargs)


def run_env(organization, environment, inventory, *args, **kwargs):
    return run_playbook(get_env_file(organization, environment),
                        get_inventory_file(inventory),
                        *args, **kwargs)


def run_playbook(playbook, inventory, *args, **kwargs):
    env = ansible_env(os.environ.copy())
    cmd = ['ansible-playbook', '-i', inventory, playbook] + list(args)

    if verbosity():
        cmd += ['-' + ('v' * verbosity())]

    show_timestamp = False
    if 'timestamp' in kwargs:
        show_timestamp = kwargs['timestamp']
        del kwargs['timestamp']

    output = print
    if show_timestamp:
        output = timestamp

    logger.info('running %s', ' '.join(cmd))
    logger.debug('env: %r', env)

    process = Popen(cmd, env=env, stdout=PIPE,
                    bufsize=1, **kwargs)
    for line in iter(process.stdout.readline, b''):
        output(line[:-1])
    # empty output buffers
    process.poll()
    return process.returncode


def run(inventory, shell_cmd, limit, *args, **kwargs):
    env = ansible_env(os.environ.copy())
    cmd = [
        'ansible', limit, '-i', get_inventory_file(inventory),
        '-m', 'shell'
    ]

    if verbosity():
        cmd += ['-' + ('v' * verbosity())]

    cmd += args
    cmd += ['-a', shell_cmd]

    logger.info('running %s', ' '.join(map(quote, cmd)))
    logger.debug('env: %r', env)

    return call(cmd, start_new_session=True, **kwargs)


def shell(inventory, *args, **kwargs):
    env = ansible_env(os.environ.copy())
    cmd = ['ansible-shell', '-i', get_inventory_file(inventory)] + list(args)

    if verbosity():
        cmd += ['-' + ('v' * verbosity())]

    logger.info('running %s', ' '.join(cmd))
    logger.debug('env: %r', env)

    return call(cmd, start_new_session=True, **kwargs)


class Inventory(object):
    def __init__(self, inventory_path):
        """
        The Inventory class provides methods to extract information from the
        specified ansible inventory file.

        :param inventory_path: The path to the inventory file
        :type inventory_path: String
        """
        from ansible.inventory import Inventory as AnsibleInventory

        self._inventory = AnsibleInventory(host_list=inventory_path)

    def get_ansible_inventory(self):
        return self._inventory

    def get_hosts(self, pattern='all'):
        return self._inventory.get_hosts(pattern)

    def get_groups(self):
        return self._inventory.get_groups()
