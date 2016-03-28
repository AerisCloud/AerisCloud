#!/usr/bin/env python

import click
import sys

from aeriscloud.cli.helpers import standard_options, Command, render_cli


@click.command(cls=Command)
@click.option('--force', is_flag=True,
              help='Connect anyway if project server is not set')
@click.argument('command', nargs=-1)
@standard_options()
def cli(box, force, command):
    """
    Launch a ssh shell on the box
    """
    if not box.is_running():
        click.secho('warning: box %s is not running' % (box.name()),
                    fg='yellow', err=True)
        sys.exit(0)

    if command and len(command):
        res = box.ssh_shell(command)
    else:
        click.echo(render_cli('services', box=box))

        if box.project.name() != 'aeriscloud':
            res = box.ssh_shell('${SHELL}')
        else:
            res = box.ssh_shell()

    if res == box.NO_PROJECT_DIR:
        if force:
            click.secho('warning: project folder does not exists!',
                        fg='yellow')
            res = box.ssh_shell()
        else:
            click.secho('error: project folder does not exists!',
                        fg='red')

    # forward exit code to the console
    sys.exit(res)

if __name__ == '__main__':
    cli()
