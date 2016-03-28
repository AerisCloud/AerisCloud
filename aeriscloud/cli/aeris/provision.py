#!/usr/bin/env python

import click

from aeriscloud.cli.helpers import standard_options, Command, render_cli
from aeriscloud.utils import timestamp


@click.command(cls=Command)
@click.argument('extra', nargs=-1)
@standard_options()
def cli(box, extra):
    """
    Provision a box
    """
    res = box.vagrant('provision', *extra)

    if res == 0:
        timestamp(render_cli('provision-success', box=box))
    else:
        timestamp(render_cli('provision-failure'))


if __name__ == '__main__':
    cli()
