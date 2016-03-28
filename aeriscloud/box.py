import arrow
import json
import os
import sys

from paramiko import SSHClient
from sh import ssh, rsync, Command, \
    ErrorReturnCode_1, ErrorReturnCode_255, ErrorReturnCode
from slugify import slugify
from subprocess32 import call, Popen

from .config import expose_username, expose_url, data_dir, verbosity
from .expose import expose
from .log import get_logger
from .utils import quote
from .vagrant import ansible_env
from .virtualbox import list_vms, vm_network, vm_ip, \
    vm_info, vm_start, vm_suspend

logger = get_logger('box')


class BoxList(list):
    def not_created(self):
        return [box for box in self if box.status() == 'not created']

    def running(self):
        return [box for box in self if box.is_running()]

    def suspended(self):
        return [box for box in self if box.status() == 'saved']

    def status(self, status):
        return [box for box in self if box.status() == status]


class Box(object):
    """
    Represents an AerisCloud VM, might or might not be running, take
    a Project instance and an entry from the .aeriscloud.yml infra
    configuration

    :param project: project.Project
    :param data: dict[str,str]
    """

    NO_PROJECT_DIR = 254

    def __init__(self, project, data):
        self.project = project
        self.data = data
        self._vm_name = ''.join([self.project.name(), '-', self.data['name']])
        self._logger = get_logger(self._vm_name)
        self.basebox = self.data.get('basebox', 'chef/centos-7.0')

    def name(self):
        """
        Return the name of the box in the project's infra

        :return: str
        """
        return self.data['name']

    def image(self):
        return self.basebox

    def vm_name(self):
        """
        Return the VM name

        :return: str
        """
        return self._vm_name

    def info(self):
        """
        Return all the information about a box, kinda messy

        :return: dict[str,str]
        """
        return vm_info(self._vm_name)

    def status(self):
        """
        Return the current status of the VM

        :return: str
        """
        if self._vm_name not in list_vms():
            return 'not created'
        info = self.info()
        if 'VMState' in info:
            return info['VMState'].strip('"')
        return 'shutdown'

    def last_status_change(self):
        info = self.info()
        if 'VMStateChangeTime' in info:
            change_time = info['VMStateChangeTime'].strip('"')
            return arrow.get(change_time[:-10]).to('local')
        return None

    def forwards(self):
        headers = ['protocol', 'host_ip', 'host_port',
                   'guest_ip', 'guest_port']
        return dict([
            (
                info.strip('"').split(',')[0],
                dict(zip(headers, info.strip('"').split(',')[1:]))
            )
            for key, info in self.info().iteritems()
            if key.startswith('Forwarding')
        ])

    def is_running(self):
        """
        Return whether or not the VM is currently running

        :return: bool
        """
        return self._vm_name in list_vms(True)

    def network(self):
        """
        Return the information for every network interfaces on the VM
        (kinda slow)

        :return: list[map[str,str]]
        """
        return vm_network(self._vm_name)

    def ip(self, id=1):
        """
        Return the IP of a box for the given interface, by default
        aeriscloud VMs have 2 interfaces:
        * id 0: NAT interface, on the 10.0.0.0 network
        * id 1: Host Only interface on the 172.16.0.0 network

        :param id: int
        :return: str
        """
        return vm_ip(self._vm_name, id)

    def ssh_key(self):
        # Vagrant 1.7+ support
        local_key = os.path.join(self.project.vagrant_dir(), 'machines',
                                 self.name(), 'virtualbox', 'private_key')
        insecure_key = os.path.join(os.environ['HOME'], '.vagrant.d',
                                    'insecure_private_key')

        if os.path.isfile(local_key):
            self._logger.debug('using key "%s" for ssh connection', local_key)
            return local_key

        self._logger.debug('using key "%s" for ssh connection', insecure_key)
        return insecure_key

    def ssh(self, **kwargs):
        """
        Return a pre-baked ssh client method to be used for calling
        commands on the distant server. Each command called will be in
        a different connection.

        :return: sh.Command
        """
        return ssh.bake(self.ip(), '-A', '-t', i=self.ssh_key(), l='vagrant',
                        o='StrictHostKeyChecking no', **kwargs)

    def ssh_client(self):
        """
        When needing a more precise SSH client, returns a paramiko SSH client

        :return: paramiko.SSHClient
        """
        client = SSHClient()
        client.load_system_host_keys()
        client.connect(self.ip(), username='vagrant', pkey=self.ssh_key())
        return client

    def ssh_shell(self, cmd=None, cd=True, popen=False, **kwargs):
        """
        Create an interactive ssh shell on the remote VM

        :return: subprocess32.Popen
        """
        call_args = [
            'ssh', self.ip(), '-t', '-A',
            '-l', 'vagrant',
            '-i', self.ssh_key()]
        if cmd:
            if isinstance(cmd, tuple) or isinstance(cmd, list):
                cmd = ' '.join(map(quote, cmd))

            if cd:
                cmd = '[ ! -d "{0}" ] && exit {1}; cd "{0}"; {2}'.format(
                    self.project.name(),
                    self.NO_PROJECT_DIR,
                    cmd
                )
            call_args.append(cmd)
        self._logger.debug('calling %s', ' '.join(call_args))

        if popen:
            return Popen(call_args, start_new_session=True, **kwargs)
        return call(call_args, **kwargs)

    def up(self, *args, **kwargs):
        res = self.vagrant('up', *args, **kwargs)
        if res == 0:
            expose.add(self)
        return res

    def halt(self, *args, **kwargs):
        res = self.vagrant('halt', *args, **kwargs)
        if res == 0:
            expose.remove(self)
        return res

    def resume(self):
        """
        Resume a suspended box

        :return: bool
        """
        if self.status() != 'saved':
            return False

        vm_start(self._vm_name)
        expose.add(self)

        return True

    def suspend(self):
        """
        Save the state of a running box

        :return: bool
        """
        if not self.is_running():
            return False

        vm_suspend(self._vm_name)
        expose.remove(self)
        return True

    def destroy(self):
        res = self.vagrant('destroy')
        if res == 0:
            expose.remove(self)
        return res

    def expose(self):
        expose.add(self)

    def vagrant(self, *args, **kwargs):
        """
        Runs a vagrant command
        """
        args = tuple(list(args) + [self.name()])
        return self.project.vagrant(*args, **kwargs)

    def browse(self, endpoint='', ip=False):
        """
        Given an endpoint, returns the URI to that endpoint

        :param endpoint: str
        :param ip: bool
        :return: str
        """
        if not ip and expose.enabled():
            host = '%s.%s.%s.%s' % (self.data['name'],
                                    self.project.name(),
                                    expose_username(),
                                    expose_url())
        else:
            host = self.ip()

        project_config = self.project.config()
        if 'browse' in project_config \
                and endpoint in project_config['browse']:
            path = project_config['browse'][endpoint]
        else:
            services = dict()
            for service in self.services():
                if 'path' not in service:
                    continue
                services[slugify(service['name'])] = service
            if endpoint in services:
                service = services[endpoint]
                return 'http://' + self.ip() + ':' \
                       + service['port'] + service['path']

            path = '/'

        return 'http://' + host + path

    def services(self):
        """
        List the services running on the box

        :return: dict[str,str,str,str]
        """
        try:
            return [
                dict(zip(
                    ['name', 'port', 'path', 'protocol'],
                    service.strip().split(',')
                ))
                for service in self.ssh().cat('/etc/aeriscloud.d/*')
            ]
        except ErrorReturnCode_1 as e:
            self._logger.warn(e.stderr)
            return []
        except ErrorReturnCode_255 as e:
            self._logger.error(e.stderr)
            return []

    def history(self):
        try:
            return [json.loads(line.strip()) for line in
                    self.ssh().cat('/home/vagrant/.provision')]
        except ErrorReturnCode_1:
            return []

        except ErrorReturnCode_255 as e:
            self._logger.error(e.stderr)
            return []

    def ansible(self, cmd='ansible-playbook'):
        tmp_inventory_dir = os.path.join(data_dir(), 'vagrant-inventory')
        if not os.path.isdir(tmp_inventory_dir):
            os.makedirs(tmp_inventory_dir)

        # create a temporary inventory file for ansible
        tmp_inventory_file = os.path.join(tmp_inventory_dir, self.vm_name())
        with open(tmp_inventory_file, 'w') as f:
            f.write('%s ansible_ssh_host=%s ansible_ssh_port=22 '
                    'ansible_ssh_private_key_file=%s' % (
                        self.vm_name(),
                        self.ip(),
                        self.ssh_key()
                    ))

        ansible = Command(cmd)
        new_env = ansible_env(os.environ.copy())

        return ansible.bake('-i', tmp_inventory_file,
                            '--extra-vars', '@%s' %
                            self.project.config_file(),
                            _env=new_env,
                            _out_bufsize=0,
                            _err_bufsize=0)

    def rsync(self, src, dest):
        # enable arcfour and no compression for faster speed
        ssh_options = 'ssh -T -c arcfour -o Compression=no -x ' \
                      '-i "%s" -l vagrant' % self.ssh_key()

        # basic args for rsync
        args = ['--delete', '--archive', '--hard-links',
                '--one-file-system', '--compress-level=0',
                '--omit-dir-times', '-e', ssh_options]

        if verbosity():
            args.append('-v')

        if verbosity() > 1:
            args.append('--progress')

        if verbosity() > 2:
            args.append('--stats')

        # check for ignore
        conf = self.project.config()
        if 'rsync_ignores' in conf:
            # TODO: check format
            args += map(lambda x: '--exclude="%s"' % x,
                        conf['rsync_ignores'])

        # then add sec and dest
        args += [src, dest]

        self._logger.debug('running: rsync %s' % ' '.join(args))

        try:
            rsync(*args,
                  _out=sys.stdout, _err=sys.stderr,
                  _out_bufsize=0, _err_bufsize=0)
        except ErrorReturnCode:
            return False

        return True

    def rsync_up(self):
        if not self.project.rsync_enabled():
            return

        return self.rsync(
            '%s/' % self.project.folder(),
            '%s:/data/%s/' % (self.ip(), self.project.name())
        )

    def rsync_down(self):
        if not self.project.rsync_enabled():
            return

        return self.rsync(
            '%s:/data/%s/' % (self.ip(), self.project.name()),
            '%s/' % self.project.folder()
        )

    def __repr__(self):
        return '<Box %s from project %s>' % (self.name(),
                                             self.project.name())
