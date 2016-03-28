import click

from aeriscloud.ansible import shell
from aeriscloud.cli.helpers import Command


@click.command(cls=Command)
@click.argument('inventory')
@click.argument('extra', nargs=-1)
def cli(inventory, extra):
    """
    Open a shell on multiple remote servers.
    """
    try:
        shell(inventory, *extra)
    except IOError as e:
        click.secho('error: %s' % e.message, err=True, fg='red')

if __name__ == '__main__':
    cli()
