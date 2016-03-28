#!/usr/bin/env python
import os
import sys

# Import the CLI system
from .helpers import AerisCLI
from ..config import module_path

cmd_help = {
    'aeris': 'Manage your local development environments',
    'cloud': 'Manage your remote servers and datacenters'
}


def get_cli(command_name):
    command_dir = os.path.join(module_path(), 'cli', command_name)
    return AerisCLI(command_dir, help=cmd_help[command_name])


def main():
    """
    This is our main entry point, it is used by setuptools to create
    the wrappers for aeris and cloud
    """

    # Prevent LC_* from leaking in VM
    os.environ['LC_ALL'] = 'en_US.UTF-8'

    # Extract command name
    command_name = os.path.basename(sys.argv[0])
    if command_name.endswith('.py'):
        command_name = command_name[:-3]

    if command_name not in cmd_help:
        # default to aeris if the command does not exists
        command_name = 'aeris'

    cli = get_cli(command_name)

    return cli()
