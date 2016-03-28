#!/usr/bin/env python

import click
import json
import os
import re
import requests
import sys

from sh import git, ErrorReturnCode

from aeriscloud.ansible import get_organization_list
from aeriscloud.basebox import baseboxes
from aeriscloud.cli.aeris.sync import sync
from aeriscloud.cli.helpers import Command, fatal, warning, \
    error, get_input, start_box, move_shell_to
from aeriscloud.cli.prompt import AerisCompletableList, AerisPrompt
from aeriscloud.config import aeriscloud_path, config, basebox_bucket, \
    projects_path
from aeriscloud.project import Project
from aeriscloud.services import services as list_services


style = click.style
vgit = git.bake(_out=sys.stdout, _out_bufsize=0, _err_to_out=True)


default_baseboxes = [
    'chef/centos-6.6',
    'chef/centos-7.0',
    'debian/wheezy64',
    'debian/jessie64',
    'ubuntu/trusty64',
    'ubuntu/vivid64'
]
default_basebox = 'chef/centos-7.0'


def _title(title):
    click.secho('\n%s\n%s' % (title, '-' * len(title)), fg='cyan')


def _get_git_root():
    """
    Retrieve the git directory, or prompt to create one if not found
    """
    git_root = None

    try:
        git_root = str(git('rev-parse', '--show-toplevel')).strip()
    except ErrorReturnCode as e:
        if e.exit_code != 128:
            fatal(e.message, e.exit_code)

    if not git_root:
        warning('You must be in a git repository directory to '
                'initialize a new project.')

        if not click.confirm('Do you want to create a new git '
                             'repository here?', default=True):
            fatal('Please run %s' % style('git init', bold=True))

        try:
            vgit('init')
            git_root = os.getcwd()
        except ErrorReturnCode as e:
            fatal('An error occurred when trying to initialize a '
                  'new repo.', e.exit_code)

    if git_root == aeriscloud_path:
        fatal('You cannot init AerisCloud from the AerisCloud directory!')

    return git_root


def _ask_general_info(git_root):
    _title('General')

    # Take the basename of the git root as default name for the application
    default_name = os.path.basename(git_root) \
        .lower()

    app_name = None
    app_id = None

    click.secho('\nSelect your %s (only lowercase letters, numbers and '
                'dash are accepted).' % style('application name', bold=True))
    while True:
        app_name = get_input('[default: %s] > ' % default_name)
        if not app_name:
            app_name = default_name
        if re.match("^[a-z0-9-]+$", app_name):
            break
        else:
            click.echo('Only lowercase letters and numbers are accepted.')

    organization_list = AerisCompletableList(get_organization_list())

    click.secho('\nWhich organization contains the playbook you want to '
                'use to provision the boxes of this project?')
    organization = AerisPrompt('> ', completer=organization_list).get_input()

    if not organization:
        organization = config.get('config', 'default_organization',
                                  default=None)

    click.echo('\nProvide your %s.\n'
               'If you don\'t have one, ask your system operators!' %
               style('application ID', bold=True))
    while True:
        app_id = get_input('> ')
        if len(app_id) > 0:
            try:
                app_id = int(app_id)
                if app_id > 0:
                    break
                warning('Please enter a valid ID.')
            except ValueError:
                warning('Please enter a valid ID.')

    return app_name, organization, app_id


def _show_service_list(service_list, enabled_services):
    """
    Show the service list, coloring enabled services, return the list of non
    default services

    TODO: find a better command name, as it doesn't just show services
    """
    if not enabled_services:
        enabled_services = []

    service_complete = {}
    for service, service_info in sorted(service_list.iteritems()):
        if not service_info['default']:
            service_complete[service] = service_info['description']
            if service in enabled_services:
                click.secho('* %s - %s' % (
                    style(service, bold=True, fg='green'),
                    service_info['description']
                ))
            else:
                click.secho('* %s - %s' % (
                    style(service, bold=True),
                    service_info['description']
                ))
    return service_complete


def _ask_services(organization, enabled_services=None):
    """
    Ask the user which services to enable/disable, returns a list of services
    """
    service_list = list_services(organization)

    if not service_list:
        return []

    _title('Services')

    click.secho('You now will need to select what %s you would like to '
                'install, from the following list:' %
                style('services', bold=True))

    service_complete = _show_service_list(service_list, enabled_services)
    selected_services = AerisCompletableList(service_complete.keys(),
                                             service_complete)

    if enabled_services:
        for service in enabled_services:
            selected_services.select(service)

    click.echo('''
Which {0} do you wish to use? (autocomplete available)
You can enter {0} on different lines, or several on the same line separated \
by spaces.
'''.format(style('services', bold=True)))

    service_cli = AerisPrompt('> ', completer=selected_services)
    while True:
        if selected_services.selected:
            click.secho('''
Current enabled services: %s

Press %s to validate, or add another %s from the list.
You can remove a service from the list by putting a %s before its name.
''' % (
                style(','.join(selected_services.selected) or 'None',
                      fg='cyan'),
                style('ENTER', bold=True),
                style('service', bold=True),
                style('-', bold=True))
            )

        services_input = service_cli.get_input()

        if services_input:
            for service in services_input.strip().split(' '):
                if not service:
                    continue
                if service in service_list:
                    selected_services.select(service)
                elif service[0] == '-' \
                        and service[1:] in service_list:
                    selected_services.unselect(service[1:])
                else:
                    error('''%s was not recognized as a valid service.
Please enter a valid service.''' % service)
        else:
            break

    return selected_services.selected


def _check_atlas_basebox(name):
    if name.count('/') != 1:
        click.secho('error: a valid basebox name looks like owner/box_name',
                    fg='red')
        return False

    res = requests.get('https://atlas.hashicorp.com/api/v1/box/%s' % name)
    if res.status_code != 200:
        error = json.loads(res.content)
        click.secho('error: %s' % ', '.join(error['errors']), fg='red')
        return False
    return True


def _fix_basebox_url(url):
    """
    Kinda fix a basebox URL
    """
    if not url.startswith('http'):
        url = 'http://%s' % url
    if not url.endswith('/meta'):
        url += '/meta'
    return url


def _ask_basebox():
    _title('Basebox')

    basebox_list = default_baseboxes

    # if we have a custom bucket, also use that
    bucket_baseboxes = []
    if basebox_bucket():
        bucket_baseboxes = list(set([
            '%s/%s' % (infra, box[:box.rfind('-')])
            for infra, boxes in baseboxes().iteritems()
            for box in boxes
        ]))
        basebox_list += bucket_baseboxes

    basebox_list.sort()

    selected_boxes = AerisCompletableList(basebox_list)
    prompt = AerisPrompt('> ', completer=selected_boxes)

    click.echo("""
You will now need to select a basebox to use for your project, we have small
selection of boxes available if you press TAB. It is recommended you use a
box that matches your production servers.

You can also enter any box you find on Atlas:
https://atlas.hashicorp.com/boxes/search?provider=virtualbox

If none is entered, %s will be selected as a default.
""" % (click.style(default_basebox, bold=True)))

    while True:
        basebox = prompt.get_input().strip()
        if basebox:
            if basebox not in bucket_baseboxes:
                if not _check_atlas_basebox(basebox):
                    continue
                return basebox, None
            else:
                return basebox, _fix_basebox_url(basebox_bucket())
        else:
            break

    return default_basebox, None


def _ask_project_details(git_root, project):
    if not project.initialized():
        (app_name, organization, app_id) = _ask_general_info(git_root)
        services = _ask_services(organization)
        basebox, basebox_url = _ask_basebox()

        project.set_name(app_name)
        project.set_organization(organization)
        project.set_id(app_id)
        project.add_box({
            'basebox': basebox
        }, basebox_url)
    else:
        if not click.confirm('There is already a project configured in this '
                             'folder, do you want to modify it\'s config?'):
            fatal('aborting')

        services = _ask_services(project.organization(), project.services())

    project.set_services(services)


def _up(box, make):
    click.echo('\nStarting box %s\n' %
               style(box.name(), bold=True))

    if not box.is_running():
        start_box(box)
    else:
        box.vagrant('provision')

    if make:
        click.echo('\nRunning make %s in your box\n' %
                   style(make, bold=True))
        if box.ssh_shell('make %s' % make) != 0:
            fatal('make command failed!')

        if sync(box, 'down') is False:
            # sync failed, message should already be displayed, exit
            sys.exit(1)


@click.command(cls=Command)
@click.option('-u', '--up', is_flag=True)
@click.option('-m', '--make',
              metavar='<command>')
@click.option('-b', '--box', 'box_name',
              help='Which box to use for make')
@click.argument('folder', required=False)
def cli(up, make, box_name, folder):
    """
    Initialize a new AerisCloud project
    """
    if not folder:
        folderpath = os.getcwd()
    else:
        folderpath = os.path.join(os.curdir, folder)
        relpath = os.path.relpath(folderpath, projects_path())
        if relpath[:2] == '..':
            warning("""You are trying to create a new project in %s
which is outside of your projects' directory (%s).""" %
                    (os.path.abspath(folderpath), projects_path()))
            folder_in_projectpath = os.path.join(projects_path(), folder)
            if click.confirm("Do you want to create it in %s instead?" %
                             folder_in_projectpath, default=True):
                folderpath = folder_in_projectpath

    if not os.path.exists(folderpath):
        os.makedirs(folderpath)

    os.chdir(folderpath)

    git_root = _get_git_root()
    project = Project(git_root)

    _ask_project_details(git_root, project)

    click.echo('\nWriting .aeriscloud.yml ... ', nl=False)
    project.save()
    click.echo('done')

    move_shell_to(project.folder())

    if up or make:
        # Retrieve the proper box
        box = project.box(box_name)

        _up(box, make)


if __name__ == '__main__':
    cli()
