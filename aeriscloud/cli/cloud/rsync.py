import click

from subprocess32 import call

from aeriscloud.ansible import ACHost
from aeriscloud.cli.helpers import Command, fatal
from aeriscloud.cli.cloud import summary
from aeriscloud.log import get_logger
from aeriscloud.utils import quote

logger = get_logger('cloud.rsync')


def _update_rsync_uri(inventory, uri):
    if ':' not in uri:
        return uri, []

    hostname, path = uri.split(':')
    try:
        host = ACHost(inventory, hostname)
    except NameError as e:
        fatal(e.message)

    return ':'.join([host.ssh_host(), path])


@click.command(cls=Command)
@click.argument('inventory')
@click.argument('src')
@click.argument('dest')
@click.argument('extra', nargs=-1)
def cli(inventory, src, dest, extra):
    """
    Sync files between your local machine and remote servers.
    """
    summary(inventory)

    src = _update_rsync_uri(inventory, src)
    dest = _update_rsync_uri(inventory, dest)

    cmd = ['rsync', '-av'] + list(extra) +\
          [src, dest]

    logger.info('Running %s' % ' '.join(map(quote, cmd)))

    call(cmd)


if __name__ == '__main__':
    cli()
