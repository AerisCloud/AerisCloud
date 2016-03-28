#!/usr/bin/env python

import click
import json
import os
import re
import sh
import sys

from ansible import __version__ as ansible_version
from git import Repo

from aeriscloud import __version__ as ac_version
from aeriscloud.cli.helpers import Command, render_cli
from aeriscloud.config import aeriscloud_path
from aeriscloud.vagrant import version as vagrant_version
from aeriscloud.virtualbox import version as virtualbox_version


def _linux_version():
    if os.path.exists('/etc/os-release'):
        os_release = {}
        with open('/etc/os-release') as f:
            for line in f.read().split('\n'):
                if not line.strip():
                    continue

                (key, value) = line.split('=')
                value = value.strip('"')

                os_release[key.lower()] = value

        version = {
            'version': os_release['name'],
            'name': os_release['name']
        }
        if 'pretty_name' in os_release:
            version['version'] = version['pretty_name'] = \
                os_release['pretty_name']

        if 'home_url' in os_release:
            version['home_url'] = os_release['home_url']

        return version

    # older non-standard distros
    for release_file in ['system-release', 'redhat-release',
                         'debian_version']:
        if not os.path.exists(os.path.join('/etc', release_file)):
            continue
        with open(os.path.join('/etc', release_file)) as f:
            return {'version': f.read().strip()}

    return None


def _ruby_version():
    re_ver = re.compile(r'^ruby ([^\s]+) \(([^\)]+)\)')

    try:
        ruby_version = str(sh.ruby('--version')).strip()
        matches = re_ver.match(ruby_version)
        if not matches:
            return ruby_version

        return {
            'version': matches.group(1),
            'revision': matches.group(2)
        }

    except sh.CommandNotFound:
        return None


def _python_version():
    if sys.hexversion >= 0x2070000:
        return '%s.%s.%s-%s' % (
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
            sys.version_info.releaselevel,
        )
    else:
        return '%s.%s.%s-%s' % (
            sys.version_info[0],
            sys.version_info[1],
            sys.version_info[2],
            sys.version_info[3],
        )


@click.command(cls=Command)
@click.option('--json', 'is_json', is_flag=True)
def cli(is_json):
    """
    See the aeriscloud version information
    """
    versions = {
        'aeriscloud': {'version': ac_version},
        'ansible': {'version': ansible_version},
        'vagrant': {'version': vagrant_version()},
        'virtualbox': {'version': virtualbox_version()},
        'ruby': _ruby_version(),
        'python': {'version': _python_version()},
        'git': {'version': str(sh.git('--version'))[12:].strip()}
    }

    # aeriscloud get information
    if os.path.exists(os.path.join(aeriscloud_path, '.git')):
        repo = Repo(aeriscloud_path)
        rev = str(repo.head.commit)[:8]
        branch = str(repo.active_branch)

        versions['aeriscloud']['revision'] = rev
        versions['aeriscloud']['branch'] = branch

    # operating system
    linux_version = _linux_version()
    if linux_version:
        versions['linux'] = linux_version
    else:
        try:
            # this is for osx
            sw_vers = dict([map(unicode.strip, line.split(':'))
                            for line in sh.sw_vers()])
            versions['osx'] = {
                'name': sw_vers['ProductName'],
                'version': sw_vers['ProductVersion'],
                'build': sw_vers['BuildVersion']
            }
        except sh.CommandNotFound:
            pass

    try:
        uname = str(sh.uname('-sr')).strip()
        versions['kernel'] = {'version': uname}
    except sh.CommandNotFound:
        pass

    if is_json:
        click.echo(json.dumps(versions))
    else:
        click.echo(render_cli('version', **versions))

if __name__ == '__main__':
    cli()
