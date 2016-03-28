#!/usr/bin/env python2.7
"""
This file is a basic script used by the CLI to help bash auto-completion, it
bypass click and most of the aeriscloud lib for achieving decent speed
"""

import os
import re
import sys

from aeriscloud.config import projects_path, aeriscloud_path,\
    data_dir, config_dir
from aeriscloud.ansible import get_env_path
from aeriscloud.project import get, from_cwd


def _print_commands(cmd):
    """
    This completer actually returns more commands than the normal class
    as it doesn't mask development commands
    """
    cmd_dir = os.path.join(os.path.dirname(__file__), cmd)
    print(' '.join([cmd_file[:-3] for cmd_file in os.listdir(cmd_dir)]))


def _print_projects():
    """
    Print the list of projects (uses the folder names)
    """
    project_dir = projects_path()
    print(' '.join(
        ['aeriscloud'] +
        [
            pro
            for pro in os.listdir(project_dir)
            if os.path.exists(os.path.join(project_dir, pro,
                                           '.aeriscloud.yml'))
        ]
    ))


def _print_boxes(project_name=None):
    """
    Print the list of boxes for a given project, defaults to the current dir
    if no project given
    """
    if project_name:
        pro = get(project_name)
    else:
        pro = from_cwd()

    if not pro:
        sys.exit(0)

    print(' '.join([box.name() for box in pro.boxes()]))


def _print_param(param, project_name=None, box_name=None):  # noqa
    """
    Completes subcommands parameters
    """
    if param == 'job':
        job_cache_file = os.path.join(data_dir(), 'jobs-cache')
        if not os.path.exists(job_cache_file):
            return
        with open(job_cache_file) as fd:
            jobs = [line for line in fd.read().split('\n') if line.strip()]
            print(' '.join(jobs))
    elif param == 'inventory':
        from aeriscloud.ansible import get_inventory_list

        print(' '.join([
            inventory[1]
            for inventory in get_inventory_list()
        ]))
    elif param == 'inventory_name':
        from aeriscloud.ansible import inventory_path

        print(' '.join([inventory_dir
                        for inventory_dir in os.listdir(inventory_path)
                        if inventory_dir[0] != '.']))
    elif param == 'organization_name':
        from aeriscloud.ansible import get_organization_list
        print(' '.join(get_organization_list()))
    elif param == 'env':
        from aeriscloud.ansible import get_env_path, get_organization_list
        for organization in get_organization_list():
            print(' '.join([organization + '/' + job_file[4:-4]
                            for job_file
                            in os.listdir(get_env_path(organization))
                            if job_file.endswith('.yml')]))
    elif param == 'command':
        if project_name:
            pro = get(project_name)
        else:
            pro = from_cwd()

        cmds = []
        with open(os.path.join(pro.folder(), 'Makefile')) as f:
            for line in f:
                m = re.match('([a-zA-Z0-9-]+):', line)
                if m:
                    cmds.append(m.group(1))
        print(' '.join(cmds))
    elif param == 'project':
        _print_projects()
    elif param == 'platform':
        platforms = ['ios', 'android', 'osx']
        print(' '.join(platforms))
    elif param == 'server':
        servers = ['production', 'aeris.cd', 'local']
        print(' '.join(servers))
    elif param == 'direction':
        directions = ['up', 'down']
        print(' '.join(directions))
    elif param == 'host':
        from aeriscloud.ansible import Inventory, get_inventory_file
        inventory = Inventory(get_inventory_file(project_name))
        hosts = inventory.get_hosts()
        print(' '.join([host.name for host in hosts]))
    elif param == 'limit':
        from aeriscloud.ansible import Inventory, get_inventory_file
        inventory = Inventory(get_inventory_file(project_name))
        hosts = inventory.get_hosts()
        groups = inventory.get_groups()
        print(' '.join([v.name for v in hosts + groups]))
    elif param == 'endpoint':
        if project_name:
            pro = get(project_name)
        else:
            pro = from_cwd()
        endpoints = [k for k, v in pro.endpoints().iteritems()]

        from slugify import slugify

        services = [slugify(service['name'])
                    for service in pro.box(box_name).services()]
        print(' '.join(endpoints + services))


def _print_path(name, extra=None):
    if name == 'aeriscloud':
        print(aeriscloud_path)
    elif name == 'projects_path':
        print(projects_path())
    elif name == 'data_dir':
        print(data_dir())
    elif name == 'config_dir':
        print(config_dir())
    elif name == 'organization':
        print(get_env_path(extra))


def _print_organization():
    from aeriscloud.ansible import get_organization_list
    print(' '.join(get_organization_list()))


commands = {
    'commands': _print_commands,
    'projects': _print_projects,
    'boxes': _print_boxes,
    'param': _print_param,
    'path': _print_path,
    'organization': _print_organization
}


def main():
    try:
        command = sys.argv[1]
        if command in commands:
            args = []
            if len(sys.argv) >= 3:
                args = sys.argv[2:]
            sys.exit(commands[command](*args))
        sys.exit(1)
    except SystemExit:
        raise
    except:
        sys.exit(2)

if __name__ == '__main__':
    main()
