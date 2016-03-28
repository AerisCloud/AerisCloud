#!/usr/bin/env python

import click
import errno
import sys

from aeriscloud.cli.helpers import Command, move_shell_to
from aeriscloud.config import projects_path
from aeriscloud.project import get


@click.command(cls=Command)
@click.argument('project', required=False)
def cli(project):
    """
    Goto a project's directory
    """
    if not project:
        move_shell_to(projects_path())
        return

    pro = get(project)

    if not pro:
        click.secho('error: project %s does not exists' % project,
                    fg='red', err=True)
        sys.exit(errno.ENOENT)

    move_shell_to(pro.folder())


if __name__ == '__main__':
    cli()
