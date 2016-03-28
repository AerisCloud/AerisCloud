import click

from aeriscloud.ansible import run_env
from aeriscloud.cli.helpers import Command
from aeriscloud.cli.cloud import summary


@click.command(cls=Command)
@click.argument('env')
@click.argument('inventory')
@click.argument('extra', nargs=-1)
def cli(env, inventory, extra):
    """
    Provision remote servers.
    """
    summary(inventory)

    (organization, env) = env.split('/', 1)

    try:
        run_env(organization, env, inventory, *extra, timestamp=True)
    except IOError as e:
        click.secho('error: %s' % e.message, err=True, fg='red')

if __name__ == '__main__':
    cli()
