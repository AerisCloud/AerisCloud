#!/usr/bin/env python

import click

from aeriscloud.cli.helpers import standard_options, Command


@click.command(cls=Command)
@standard_options(start_prompt=False)
def cli(box):
    """
    Destroy a box
    """
    box.destroy()


if __name__ == '__main__':
    cli()
