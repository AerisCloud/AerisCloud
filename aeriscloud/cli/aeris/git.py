#!/usr/bin/env python

import click
import sys

from aeriscloud.cli.aeris.sync import sync
from aeriscloud.cli.helpers import standard_options, Command
from aeriscloud.utils import quote


@click.command(cls=Command)
@click.argument('command', nargs=-1)
@standard_options()
def cli(box, command):
    """
    Run a git command
    """
    if not box.is_running():
        click.secho('error: box %s is not running' % (box.name()),
                    fg='red', err=True)
        sys.exit(1)

    if sync(box, 'up') is False:
        # sync failed, message should already be displayed, exit
        sys.exit(1)

    res = box.ssh_shell('git %s' % ' '.join(map(quote, command)))

    if res == box.NO_PROJECT_DIR:
        click.secho('error: project folder does not exists!',
                    fg='red')

    if sync(box, 'down') is False:
        # sync failed, message should already be displayed, exit
        sys.exit(1)

    sys.exit(res)


if __name__ == '__main__':
    cli()
