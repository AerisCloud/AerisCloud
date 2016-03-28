import click

from aeriscloud.ansible import run
from aeriscloud.cli.helpers import Command
from aeriscloud.cli.cloud import summary
from aeriscloud.utils import quote


@click.command(cls=Command)
@click.argument('inventory')
@click.argument('limit')
@click.argument('command', nargs=-1)
def cli(inventory, limit, command):
    """
    Run shell command on multiple remote servers.
    """
    summary(inventory)

    try:
        command = ' '.join(map(quote, command))
        click.echo('Running %s' % command)
        run(inventory, command, limit)
    except IOError as e:
        click.secho('error: %s' % e.message, err=True, fg='red')

if __name__ == '__main__':
    cli()
