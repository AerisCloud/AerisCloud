#!/usr/bin/env python

import arrow
import click
import re
import sys

from aeriscloud.cli.helpers import standard_options, Command, render_cli


@click.command(cls=Command)
@click.option('-q', '--quiet', is_flag=True)
@standard_options()
def cli(box, quiet):
    """
    Shows provisioning history for a box
    """
    if not box.is_running():
        click.secho('error: box %s is not running' % box.name(), fg='red')
        sys.exit(1)

    history = box.history()

    # cleanup ansible output
    av = re.compile(r'ansible (\d+\.\d+\.\d+)( \(detached HEAD (\w+)\) '
                    'last updated (.*))?$')
    mv = re.compile(r'([A-Za-z0-9/_-]+): \(detached HEAD (\w+)\) '
                    'last updated (.*)$')

    for deployment in history:
        ansible = {'extra': [], 'modules': {}}
        for line in deployment['ansible_version'].split('\n'):
            line = line.strip()

            match = av.match(line)
            if match:
                ansible['version'] = match.group(1)
                if match.group(2):
                    ansible['rev'] = match.group(3)
                    ansible['last_update'] = arrow.get(match.group(4),
                                                       'YYYY/MM/DD HH:mm:ss')
                continue

            match = mv.match(line)
            if match:
                ansible['modules'][match.group(1)] = {
                    'rev': match.group(2),
                    'last_update': arrow.get(match.group(3),
                                             'YYYY/MM/DD HH:mm:ss')
                }
                continue

            ansible['extra'].append(line)

        deployment['date'] = arrow.get(deployment['date'],
                                       'DD MMM YYYY HH:mm:ss Z')
        deployment['ansible_version'] = ansible

    click.echo(render_cli('history', history=history, quiet=quiet), nl=False)


if __name__ == '__main__':
    cli()
