from __future__ import print_function

import re
import sys

from click import style

FIELDS = [
        'invocation',
        'ansible_facts',
        'cmd',
        'command',
        'msg',
        'stdout',
        'stderr'
        ]

# this re-implements click.secho to use print instead of click.echo
# as click.echo will detect the ansible environment as not being a
# tty and strip colors
def secho(text, nl=True, err=False, **kwargs):
    print(style(text, **kwargs),
          end=nl and '\n' or '',
          file=err and sys.stderr or sys.stdout)


def print_line(title, color, content):
    out = ''

    if isinstance(content, list):
        content = ' '.join(content)

    # Deal with CRs: that is, only print the last output
    data = content.split('\r')
    for line in data:
        if line.endswith('\n'):
            out += '%s\n' % (line)

    out += '%s\n' % (data[-1])

    secho(':::: |%s|\n%s' % (title.encode('utf-8'), out.encode('utf-8')),
          fg=color)


def human_log(_, res):
    if type(res) == type(dict()):
        for field in FIELDS:
            if field not in res.keys() or not res[field]:
                continue

            data = res[field]

            if field == 'invocation':
                module_name = res['invocation']['module_name']

                if module_name in ['shell', 'command', 'set_fact', 'setup']:
                    continue

                secho(':::: |%s::%s|' % (field, module_name), fg='cyan')

                if module_name == 'fail':
                    args = [('msg', res['invocation']['module_args'][4:])]
                else:
                    args = re.findall(r'(\S+)=(".*?"|\S+)',
                                      res['invocation']['module_args'])

                for key, val in args:
                    secho('      %s' % key, fg='blue', nl=False)
                    secho(' = ', fg='magenta', nl=False)
                    for line in val.split('\n'):
                        secho(line)

            elif field == 'ansible_facts':
                if res['invocation']['module_name'] != 'set_fact':
                    continue

                secho(':::: |%s|' % (field), fg='cyan')

                for key, val in data.iteritems():
                    secho('      %s' % key, fg='blue', nl=False)
                    secho(' = ', fg='magenta', nl=False)
                    secho(str(val))

            elif field == 'stderr':
                print_line(field, 'red', data)
            elif field == 'cmd':
                print_line(field, 'magenta', data)
            else:
                print_line(field, 'cyan', data)

            print('')

    secho('*' * 79)

class CallbackModule(object):

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(self, host, res, ignore_errors=False):
        if not ignore_errors:
            secho('\n'.join([
                '!' * 79,
                'An error has occured while executing this task. '
                'See below for more information',
                '!' * 79
            ]), fg='red')

            human_log(host, res)

            # Unexpected error
            if not res['invocation']['module_name'] == "fail":
                secho('''Most likely, this has been caused by a bug in our playbooks. Please
take a moment to report the issue by visiting:

%s

and open an issue containing:

* The command you ran
* The log output of the error (right above this message)
* A link to your application on GitHub (if applicable)
* A link to the inventory file you are using (if applicable)
''' % (style('https://github.com/AerisCloud/issues/new', fg='magenta')))

            secho('\n' + ('!' * 79), fg='red')
        else:
            human_log(host, res)

    def runner_on_ok(self, host, res):
        human_log(host, res)

    def runner_on_error(self, host, msg):
        pass

    def runner_on_skipped(self, host, item=None):
        pass

    def runner_on_unreachable(self, host, res):
        human_log(host, res)

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        human_log(host, res)

    def runner_on_async_ok(self, host, res, jid):
        human_log(host, res)

    def runner_on_async_failed(self, host, res, jid):
        human_log(host, res)

    def playbook_on_start(self):
        pass

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, pattern):
        pass

    def playbook_on_stats(self, stats):
        pass
