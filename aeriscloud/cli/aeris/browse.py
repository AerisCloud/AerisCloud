#!/usr/bin/env python

import click

from aeriscloud.cli.helpers import standard_options, Command


@click.command(cls=Command)
@click.option('-i', '--ip', is_flag=True,
              help='Use the machine IP instead of the aeris.cd domain')
@click.argument('endpoint', default='')
@standard_options(multiple=False)
def cli(box, endpoint, ip):
    """
    Open an endpoint in your default browser
    """
    url = box.browse(endpoint, ip)
    click.secho('Opening %s in your browser...' % (url), fg='green')
    click.launch(url)

if __name__ == '__main__':
    cli()
