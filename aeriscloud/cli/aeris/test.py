#!/usr/bin/env python

import click
import os
import glob
import re
import sys

# we could import the flake8 package, but somehow their public API is just
# useless as their default reporter print directly to stdout with no way
# to catch what it is doing, just run the binary and work with it's output
from sh import Command as ShCommand, ErrorReturnCode

from aeriscloud.ansible import ansible_env, get_env_path, \
    ansible_path, organization_path
from aeriscloud.cli.helpers import Command
from aeriscloud.config import module_path, aeriscloud_path

python = ShCommand(os.path.join(aeriscloud_path, 'venv/bin/python'))


def _run_flake8():
    click.echo('Running flake8 on codebase ... ', nl=False)
    flake8_bin = os.path.join(aeriscloud_path, 'venv/bin/flake8')

    keys = ['file', 'row', 'col', 'message']
    reports = [dict(zip(keys, line.strip().split(':')))
               for line in python(flake8_bin, '--max-complexity', 11,
                                  module_path(), _ok_code=[0, 1])]

    errors = 0
    last_file = None
    if reports:
        click.echo('[%s]\n' % click.style('FAIL', fg='red'))

        for report in reports:
            report_file = report['file'][len(module_path()) + 1:]
            if report_file != last_file:
                click.secho('  Errors in file: %s' % report_file,
                            fg='blue', bold=True)
                last_file = report_file

            click.echo('    line %s char %s: %s' % (
                click.style(report['row'], fg='green'),
                click.style(report['col'], fg='green'),
                click.style(report['message'], fg='red'),
            ))
            errors += 1

        click.echo('')
    else:
        click.echo('[%s]' % click.style('OK', fg='green'))

    return errors


def _run_nosetests():
    click.echo('Running unit tests ... ', nl=False)
    nose_bin = os.path.join(aeriscloud_path, 'venv/bin/nosetests')

    errors = 0
    try:
        python(nose_bin, '-v', '--with-id', module_path(),
               _err_to_out=True, _ok_code=[0])
        click.echo('[%s]' % click.style('OK', fg='green'))
    except ErrorReturnCode as e:
        click.echo('[%s]\n' % click.style('FAIL', fg='red'))

        for line in e.stdout.split('\n')[:-2]:
            if line.startswith('#'):
                print(line)
                (id, name, test_file, ellipsis, res) = line.rstrip().split(' ')

                if res == 'ok':
                    res = click.style(res, fg='green', bold=True)
                elif res == 'FAIL':
                    res = click.style(res, fg='red', bold=True)

                line = ' '.join([
                    click.style(id, bold=True, fg='yellow'),
                    click.style(name, fg='blue'),
                    test_file,
                    ellipsis,
                    res
                ])
            elif line.startswith('FAIL:'):
                (_, name, test_file) = line.split(' ')

                line = ' '.join([
                    click.style('FAIL', bold=True, fg='red') + ':',
                    click.style(name, fg='blue'),
                    test_file
                ])

            click.echo('  ' + line)
            errors += 1
    return errors


def _run_ansible_lint(organization):
    al_bin = os.path.join(aeriscloud_path, 'venv/bin/ansible-lint')

    env = ansible_env(os.environ.copy())

    if organization:
        environment_files = glob.glob(get_env_path(organization) + '/*.yml')
    else:
        environment_files = glob.glob(organization_path + '/*/*.yml')

    if not environment_files:
        return 0

    args = environment_files + ['-r', os.path.join(ansible_path, 'rules')]

    click.echo('Running ansible-lint ... ', nl=False)

    errors = 0
    try:
        python(al_bin, *args,
               _env=env, _err_to_out=True, _ok_code=[0])
        click.echo('[%s]' % click.style('OK', fg='green'))
    except ErrorReturnCode as e:
        parser = re.compile(
            r'^\[(?P<error_code>[^\]]+)\] (?P<error_message>[^\n]+)\n'
            r'%s(?P<file_name>[^:]+):(?P<line_number>[0-9]+)\n'
            r'Task/Handler: (?P<task_name>[^\n]+)\n\n' % (ansible_path + '/'),
            re.MULTILINE
        )

        click.echo('[%s]\n' % click.style('FAIL', fg='red'))

        last_file = None
        pos = 0
        while pos < len(e.stdout):
            match = parser.match(e.stdout, pos)
            if not match:
                click.secho("Error: %s" % e.stdout)
                errors += 1
                break
            error = match.groupdict()

            if error['file_name'] != last_file:
                click.secho('  Errors in file: %s' % error['file_name'],
                            fg='blue', bold=True)
                last_file = error['file_name']

            click.echo('    line %s task %s: %s %s' % (
                click.style(error['line_number'], fg='green'),
                click.style(error['task_name'], fg='green'),
                click.style(error['error_code'], fg='red'),
                click.style(error['error_message'], fg='red'),
            ))
            errors += 1
            pos = match.end()
    return errors


@click.command(cls=Command)
@click.option('--organization', default=None)
def cli(organization):
    """
    Test and Lint the aeriscloud code
    """
    errors = 1
    if _run_flake8():
        errors += 1
    if _run_nosetests():
        errors += 2
    if _run_ansible_lint(organization):
        errors += 4
    sys.exit(errors-1)


if __name__ == '__main__':
    cli()
