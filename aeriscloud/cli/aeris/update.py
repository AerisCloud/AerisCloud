#!/usr/bin/env python

import click
import requests
import semver
import sys
import tempfile

from subprocess32 import call

from aeriscloud import __version__ as version
from aeriscloud.cli.helpers import Command, fatal
from aeriscloud.github import Github
from aeriscloud.cli.config import config


@click.command(cls=Command)
@click.option('-f', '--force', is_flag=True, help='Force update')
def cli(force):
    """
    Update AerisCloud
    """
    if not force and config.get('github', 'enabled', default=False) == 'true':
        client = Github().gh
        repo = client.repository('aeriscloud', 'aeriscloud')
        latest_release = repo.iter_releases().next()
        latest_version = latest_release.tag_name[1:]

        if semver.compare(version, latest_version) != -1:
            click.secho('AerisCloud is already up to date!', fg='green')
            sys.exit(0)

        click.echo('A new version of AerisCloud is available: %s (%s)' % (
            click.style(latest_version, fg='green', bold=True),
            click.style(latest_release.name, bold=True)
        ))

    # retrieve install script in a tmpfile
    tmp = tempfile.NamedTemporaryFile()
    r = requests.get('https://raw.githubusercontent.com/' +
                     'AerisCloud/AerisCloud/develop/scripts/install.sh')
    if r.status_code != 200:
        fatal('error: update server returned %d (%s)' % (
            r.status_code, r.reason))

    tmp.write(r.content)
    tmp.flush()

    call(['bash', tmp.name])

    tmp.close()

if __name__ == '__main__':
    cli()
