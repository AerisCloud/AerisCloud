#!/usr/bin/env python

import click
import sys

from aeriscloud.cli.helpers import standard_options, Command


def sync(box, direction):
    if not box.project.rsync_enabled():
        return None

    if direction == 'down':
        click.secho('Syncing files down from the box...',
                    fg='cyan', bold=True)
        if box.rsync_down():
            click.secho('Sync down done!', fg='green', bold=True)
        else:
            click.secho('Sync down failed!', fg='red', bold=True)
            return False
    elif direction == 'up':
        click.secho('Syncing files up to the box...',
                    fg='cyan', bold=True)
        if box.rsync_up():
            click.secho('Sync up done!', fg='green', bold=True)
        else:
            click.secho('Sync up failed!', fg='red', bold=True)
            return False
    else:
        click.secho('error: invalid direction %s' % direction,
                    fg='red', bold=True)
        return False

    return True


@click.command(cls=Command)
@click.argument('direction', required=False, default='up',
                type=click.Choice(['up', 'down']))
@standard_options()
def cli(box, direction='up'):
    """
    Sync data up or down
    """
    if not box.is_running():
        click.secho('error: box %s is not running' % (box.name()),
                    fg='red', err=True)
        sys.exit(1)

    if box.project.name() == 'aeriscloud':
        click.secho('error: cannot be used on infra boxes',
                    fg='red', err=True)
        sys.exit(1)

    res = sync(box, direction)

    if res is None:
        click.secho('error: rsync is not enabled on this project',
                    fg='red', err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
