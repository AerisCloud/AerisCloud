import ansible.callbacks
import ansible.constants
import ansible.inventory
from ansible.runner import Runner
import ansible.utils
import json
import os
import sys
import time
import yaml

from aeriscloud import __version__ as ac_version
from aeriscloud.config import aeriscloud_path

# Inspired from https://github.com/ansible/ansible/blob/1408a01498e14ac1112f334e34be05396c003146/lib/ansible/utils/__init__.py#L892-L930
def _git_repo_info(repo_path):
    ''' returns a string containing git branch, commit id and commit date '''
    result = None
    if os.path.exists(repo_path):
        # Check if the .git is a file. If it is a file, it means that we are in a submodule structure.
        if os.path.isfile(repo_path):
            try:
                gitdir = yaml.safe_load(open(repo_path)).get('gitdir')
                # There is a possibility the .git file to have an absolute path.
                if os.path.isabs(gitdir):
                    repo_path = gitdir
                else:
                    repo_path = os.path.join(repo_path[:-4], gitdir)
            except (IOError, AttributeError):
                return ''
        f = open(os.path.join(repo_path, "HEAD"))
        line = f.readline().rstrip("\n")
        if line.startswith("ref:"):
            branch_path = os.path.join(repo_path, line[5:])
        else:
            branch_path = None
        f.close()
        if branch_path and os.path.exists(branch_path):
            branch = '/'.join(line.split('/')[2:])
            f = open(branch_path)
            commit = f.readline().rstrip("\n")
            f.close()
        else:
            # detached HEAD
            commit = line
            branch = 'detached HEAD'

        result = {
            'branch': branch,
            'commit': commit
        }

    return result


class CallbackModule(object):
    def __init__(self):
        self.executed_task = []
        self.failed_at = {}
        self.disable = False
        self.pipein, self.pipeout = os.pipe()
        self.runner_pid = os.getpid()

        # Enable the plugin only if we are provisioning
        for arg in sys.argv:

            # Skip all the optional parameters
            if arg[0:2] == '--':
                continue

            # Is there an argument following the env_*.yml pattern?
            if arg.endswith('.yml') and \
                    os.path.basename(arg).startswith('env_'):
                break
        else:
            self.disable = True

    def runner_on_failed(self, host, res, ignore_errors=False):
        if not ignore_errors and self.executed_task:
            if os.getpid() == self.runner_pid:
                self._fill_failed_at([host, self.executed_task[-1]])
            else:
                os.close(self.pipein)
                os.write(self.pipeout, host + "\n")
                os.write(self.pipeout, self.executed_task[-1] + "\n")

    def playbook_on_task_start(self, name, is_conditional):
        self.executed_task.append(name)

    def _fill_failed_at(self, data):
        host = None
        for row in data:
            row = row.strip()
            if not host:
                host = row
            else:
                self.failed_at[host] = row
                host = None

    def playbook_on_stats(self, stats):
        if self.disable:
            return

        history = {}

        history['stats'] = {}
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            history['stats'][h] = stats.summarize(h)

        os.close(self.pipeout)
        pipein = os.fdopen(self.pipein)
        failed_at = pipein.readlines()
        self._fill_failed_at(failed_at)

        history['failed_at'] = self.failed_at

        history['roles'] = list(set([role[:role.find('|')].strip()
                                     for role in self.executed_task
                                     if role.find('|') != -1]))

        history['date'] = time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                        time.gmtime())

        history['ansible_version'] = ansible.utils.version("ansible")

        history['aeriscloud_version'] = ac_version

        ac_repo_path = os.path.join(aeriscloud_path, '.git')
        history['aeriscloud_commit'] = _git_repo_info(ac_repo_path)['commit']

        if os.path.isfile('.aeriscloud.yml'):
            import yaml
            with open('.aeriscloud.yml') as fd:
                history['services'] = yaml.load(fd).get('services')

        # Re-create a parser and extract all the parameters we need
        # to run ansible
        parser = ansible.utils.base_parser(
            constants=ansible.constants,
            runas_opts=True,
            subset_opts=True,
            async_opts=True,
            output_opts=True,
            connect_opts=True,
            check_opts=True,
            diff_opts=False,
            usage='%prog <host-pattern> [options]'
        )

        filtered_arguments = []
        for arg in sys.argv:
            for opt in [
                'limit',
                'inventory-file',
                'private-key',
                'user',
                'connection'
            ]:
                if arg.startswith('--' + opt + '='):
                    filtered_arguments.append(arg)

        if '-i' in sys.argv:
            inventory_index = sys.argv.index('-i')
            if inventory_index > -1:
                filtered_arguments.append(sys.argv[inventory_index])
                filtered_arguments.append(sys.argv[inventory_index + 1])

        (options, args) = parser.parse_args(filtered_arguments)

        inventory_manager = ansible.inventory.Inventory(options.inventory)
        if options.subset:
            inventory_manager.subset(options.subset)

        # Create the command to append the history data to the file
        command = "echo '" + json.dumps(history) + "' >> ~/.provision"

        # Disable the callback plugins to have no output
        ansible.callbacks.callback_plugins = []
        runner = Runner(
            inventory=inventory_manager,
            subset=options.subset,
            module_name='raw',
            module_args=command,
            private_key_file=options.private_key_file,
            remote_user=options.remote_user,
            transport=options.connection,
            callbacks=None
        )
        runner.run()
