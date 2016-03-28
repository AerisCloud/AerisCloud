from __future__ import print_function

import json
import os
import platform
import re
import six

from subprocess32 import call, Popen, PIPE

from .ansible import ansible_env
from .config import aeriscloud_path, data_dir, verbosity, default_organization
from .log import get_logger
from .organization import Organization
from .utils import timestamp, cd

logger = get_logger('vagrant')

VAGRANT_DATA_FOLDER = os.path.join(os.getenv('HOME'), '.vagrant.d')


class Machine(object):
    def __init__(self, id, json_data):
        self.id = id
        self.vagrant_path = json_data.get('local_data_path')
        self.name = json_data.get('name')
        self.provider = json_data.get('provider')
        self.state = json_data.get('state')
        self.vagrantfile = os.path.join(
            json_data.get('vagrantfile_path'),
            json_data.get('vagrantfile_name', 'Vagrantfile') or 'Vagrantfile'
        )
        self.extra_data = json_data.get('extra_data', {})

        self.data_path = os.path.join(
            self.vagrant_path,
            'machines',
            self.name,
            self.provider
        )
        self._uuid = None

    @property
    def uuid(self):
        id_file = os.path.join(self.data_path, 'id')
        if not os.path.exists(id_file):
            return None

        if not self._uuid:
            with open(id_file) as fd:
                self._uuid = fd.read()
        return self._uuid


class MachineIndex(object):
    machines = {}
    machine_index_file = os.path.join(VAGRANT_DATA_FOLDER, 'data',
                                      'machine-index', 'index')

    def __init__(self):
        if MachineIndex.machines:
            return

        with open(MachineIndex.machine_index_file) as fd:
            machine_index = json.load(fd)
            machines = machine_index.get('machines', {})
            for mid, json_data in six.iteritems(machines):
                MachineIndex.machines[mid] = Machine(mid, json_data)

    def get(self, mid):
        return MachineIndex.machines.get(mid)

    def get_by_name(self, name):
        for machine in MachineIndex.machines.values():
            if machine.name == name:
                return machine
        return None

    def get_by_uuid(self, uuid):
        for machine in MachineIndex.machines.values():
            if machine.uuid == uuid:
                return machine
        return None


class NFS(object):
    nfs_exports = '/etc/exports'
    re_exports_headers = re.compile(
        r'^# VAGRANT-(?P<type>BEGIN|END):(?P<uid> [0-9]+) '
        r'(?P<uuid>[a-z0-9-]+)', re.I)
    re_exports_path = re.compile(r'^("[^"]+"|\S+)', re.I)

    def __init__(self, export_file=nfs_exports):
        self.exports = {}
        self.export_file = export_file

        self.parse_exports()

    def parse_exports(self):
        if not os.path.exists(self.export_file):
            return

        current_uuid = None
        current_exports = []
        with open(self.export_file) as fd:
            for line in fd:
                match = NFS.re_exports_headers.match(line.strip())
                if match:
                    # store exports
                    if match.group('type') == 'END':
                        self.exports[current_uuid] = current_exports
                        current_uuid = None
                        current_exports = []
                        continue

                    # ignore uids that are not ours
                    if match.group('uid') and \
                            int(match.group('uid').strip()) != os.getuid():
                        continue

                    current_uuid = match.group('uuid')
                elif current_uuid:
                    path_match = NFS.re_exports_path.match(line.strip())
                    if not path_match:
                        continue
                    export_path = path_match.group(0).strip('"')
                    current_exports.append(export_path)

    def fix_anomalies(self):
        to_prune = []

        # machine_index = MachineIndex()
        for uuid, exports in six.iteritems(self.exports):
            # machine = machine_index.get_by_uuid(uuid)
            # machine cannot be found in the index
            # if not machine:
            #    to_prune.append(uuid)
            #    continue

            # one of the path does not exists anymore
            if [path for path in exports if not os.path.exists(path)]:
                to_prune.append(uuid)
                continue

        # remove all exports that have issues
        for uuid in to_prune:
            logger.info('pruning NFS entry for %s' % uuid)

            # taken from vagrant/plugins/hosts/linux/cap/nfs.rb
            extended_re_flag = '-r'
            sed_expr = '\\\x01^# VAGRANT-BEGIN:( {user})? {id}\x01,' \
                       '\\\x01^# VAGRANT-END:( {user})? {id}\x01 d'.format(
                           id=uuid,
                           user=os.getuid()
                       )
            if platform.system() == 'Darwin':
                extended_re_flag = '-E'
                sed_expr = '/^# VAGRANT-BEGIN:( {user})? {id}/,' \
                           '/^# VAGRANT-END:( {user})? {id}/ d'.format(
                               id=uuid,
                               user=os.getuid()
                           )

            cmd = [
                'sed',
                extended_re_flag,
                '-e',
                sed_expr,
                '-ibak',
                self.export_file
            ]

            # if we do not have write access, use sudo
            if not os.access(self.export_file, os.W_OK):
                cmd = [
                    'sudo',
                    '-p'
                    'Fixing invalid NFS exports. Administrators privileges '
                    'are required\n[sudo] password for %u',
                    '--'
                ] + cmd

            if call(cmd) != 0:
                raise RuntimeError('could not prune invalid nfs exports '
                                   '"%s" from /etc/exports' % uuid)


def run(pro, *args, **kwargs):
    """
    Run vagrant within a project
    :param pro: .project.Project
    :param args: list[string]
    :param kwargs: dict[string,string]
    :return:
    """
    with cd(pro.folder()):
        # fix invalid exports for vagrant
        NFS().fix_anomalies()

        new_env = ansible_env(os.environ.copy())

        new_env['PATH'] = os.pathsep.join([
            new_env['PATH'],
            os.path.join(aeriscloud_path, 'venv/bin')
        ])
        new_env['VAGRANT_DOTFILE_PATH'] = pro.vagrant_dir()
        new_env['VAGRANT_CWD'] = pro.vagrant_working_dir()
        new_env['VAGRANT_DISKS_PATH'] = os.path.join(data_dir(), 'disks')

        # We might want to remove that or bump the verbosity level even more
        if verbosity() >= 4:
            new_env['VAGRANT_LOG'] = 'info'

        new_env['AERISCLOUD_PATH'] = aeriscloud_path
        new_env['AERISCLOUD_ORGANIZATIONS_DIR'] = os.path.join(data_dir(),
                                                               'organizations')

        org = default_organization()
        if org:
            new_env['AERISCLOUD_DEFAULT_ORGANIZATION'] = org

        organization_name = pro.organization()
        if organization_name:
            organization = Organization(organization_name)
        else:
            organization = Organization(org)

        basebox_url = organization.basebox_url()
        if basebox_url:
            new_env['VAGRANT_SERVER_URL'] = basebox_url

        args = ['vagrant'] + list(args)
        logger.debug('running: %s\nenv: %r', ' '.join(args), new_env)

        # support for the vagrant prompt
        if args[1] == 'destroy':
            return call(args, env=new_env, **kwargs)
        else:
            process = Popen(args, env=new_env, stdout=PIPE,
                            bufsize=1, **kwargs)
            for line in iter(process.stdout.readline, b''):
                timestamp(line[:-1])
            # empty output buffers
            process.poll()
            return process.returncode


def version():
    try:
        from sh import vagrant
        return str(vagrant('--version'))[8:].rstrip()
    except ImportError:
        return None
