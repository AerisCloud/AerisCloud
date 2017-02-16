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
        return uri, None

    hostname, path = uri.split(':')

    user = None
    if '@' in hostname:
        (user, hostname) = hostname.split('@', 1)

    try:
        host = ACHost(inventory, hostname)
    except NameError as e:
        fatal(e.message)

    new_uri = '@'.join(filter(None, [
        user,
        ':'.join([host.ssh_host(), path])
    ]))
    return new_uri, host.variables()


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

    src, src_hostvars = _update_rsync_uri(inventory, src)
    dest, dest_hostvars = _update_rsync_uri(inventory, dest)

    ssh_args = None
    if src_hostvars and 'ansible_ssh_common_args' in src_hostvars:
        ssh_args = src_hostvars['ansible_ssh_common_args']
    if dest_hostvars and 'ansible_ssh_common_args' in dest_hostvars:
        ssh_args = dest_hostvars['ansible_ssh_common_args']

    cmd = ['rsync', '-av']
    if ssh_args:
        cmd += ['-e', 'ssh %s' % ssh_args]
    cmd += list(extra) + [src, dest]

    logger.info('Running %s' % ' '.join(map(quote, cmd)))

    call(cmd)


if __name__ == '__main__':
    cli()
