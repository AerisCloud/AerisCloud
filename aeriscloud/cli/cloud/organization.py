#!/usr/bin/env python

import click
import os
import shutil
import sys
import tarfile

from sh import git, curl, ErrorReturnCode, Command as shCommand

from aeriscloud.cli.helpers import Command, info, fatal, success, move_shell_to
from aeriscloud.ansible import get_organization_list, get_env_path, \
    organization_path
from aeriscloud.config import config, aeriscloud_path
from aeriscloud.github import Github


@click.group()
def cli():
    """
    Manage organizations
    """
    pass


vgit = git.bake(_out=sys.stdout, _out_bufsize=0, _err_to_out=True)


def run_galaxy_install(organization):
    roles_path = os.path.join(get_env_path(organization), 'roles')
    dependencies_path = os.path.join(roles_path, 'dependencies.txt')
    if not os.path.exists(dependencies_path):
        return

    last_mtime = None
    last_mtime_file = os.path.join(get_env_path(organization), '.galaxy')
    if os.path.exists(last_mtime_file):
        with open(last_mtime_file, 'r') as f:
            last_mtime = f.readline()

    mtime = str(os.stat(dependencies_path).st_mtime)

    if last_mtime == mtime:
        return

    info("Updating dependencies for %s ..." % organization)
    galaxy = shCommand(os.path.join(aeriscloud_path, 'scripts', 'wrapper.sh'))
    galaxy(os.path.join(aeriscloud_path, 'venv', 'bin', 'ansible-galaxy'),
           'install', '-f', '-p', roles_path, '-r', dependencies_path,
           _out=sys.stdout, _out_bufsize=0, _err_to_out=True)

    with open(last_mtime_file, 'w') as f:
        f.write(mtime)


def update():
    for organization in get_organization_list():
        if not os.path.exists(os.path.join(get_env_path(organization),
                                           '.git')):
            info("Skip %s" % organization)
            continue

        info("Updating %s ..." % organization)
        os.chdir(get_env_path(organization))

        if not git('remote').strip():
            info("No remotes are set for this organization, skipping")
            continue

        try:
            vgit('pull')
        except ErrorReturnCode:
            fatal("Unable to update the organizations.")

        run_galaxy_install(organization)

    success("All the organizations have been updated.")


@cli.command(cls=Command)
@click.argument('name', required=False)
@click.argument('path', required=False)
def install(name, path):
    """
    Install organization.
    """
    if not name:
        update()
        return

    if not name.isalnum():
        fatal("Your organization name should only contains alphanumeric "
              "characters.")

    dest_path = get_env_path(name)
    if os.path.exists(dest_path):
        click.echo('We will update the %s organization' % name)
        os.chdir(dest_path)
        if os.path.exists(os.path.join(dest_path, '.git')):
            try:
                vgit('pull')
            except ErrorReturnCode:
                fatal("Unable to update the organization %s." % name)
            success("The %s organization has been updated." % name)

        run_galaxy_install(name)
        return

    if not path:
        fatal("You must specify a path to a local directory or an URL to a "
              "git repository to install a new organization.")

    if os.path.exists(path) and os.path.isdir(path):
        os.symlink(path, dest_path)
    else:
        click.echo('We will clone %s in %s\n' % (path, dest_path))
        try:
            vgit('clone', path, dest_path)
        except ErrorReturnCode:
            fatal("Unable to install the organization %s." % name)

    success("The %s organization has been installed." % name)

    run_galaxy_install(name)


@cli.command(cls=Command)
@click.argument('organization_name')
def remove(organization_name):
    """
    Remove organizations.
    """
    if not organization_name.isalnum():
        fatal("Your organization name should only contains alphanumeric "
              "characters.")

    dest_path = get_env_path(organization_name)
    if not os.path.exists(dest_path):
        fatal("The %s organization doesn't exist." % organization_name)

    if not click.confirm("Do you want to delete the %s organization?" %
                         organization_name,
                         default=False):
        info("Aborted. Nothing has been done.")
        return

    if os.path.isdir(dest_path) and not os.path.islink(dest_path):
        shutil.rmtree(dest_path)
    else:
        os.remove(dest_path)
    success("The %s organization has been removed." % organization_name)


@cli.command(cls=Command)
def list():
    """
    List organizations.
    """
    for organization in get_organization_list():
        print(organization)


@cli.command(cls=Command)
@click.argument('name')
@click.argument('repository', required=False)
def init(name, repository):
    """
    Initialize a new organization.

    The following usages are supported:

        cloud init <name>

    It will create a new AerisCloud organization locally.

        cloud init <name> <git repository url>

    \b
It will create a new AerisCloud organization and set the origin remote to
the specified url.

    \b
If the GitHub integration is enabled, you can also use the following
commands:

        cloud init <github organization name>

    \b
It will create a new AerisCloud organization and set the origin remote to
git@github.com/<organization>/aeriscloud-organization.git

        cloud init <github organization name>/<project name>

    \b
It will create a new AerisCloud organization and set the origin remote to
git@github.com/<organization>/<project>-aeriscloud-organization.git

        cloud init <github organization name>/<customer>/<project name>

    \b
It will create a new AerisCloud organization and set the origin remote to
git@github.com/<organization>/<customer>-<project>-aeriscloud-organization.git
"""
    if (not repository and
            config.has('github', 'enabled') and
            config.get('github', 'enabled') == 'true' and
            config.has('github', 'token')):
        gh = Github()

        if '/' in name:
            split = name.split('/')
            name = split[0]
            repo_name = '-'.join(split[1:]) + "-aeriscloud-organization"
        else:
            repo_name = "aeriscloud-organization"

        orgs = [org for org in gh.get_organizations()
                if org.login.lower() == name.lower()]
        if orgs:
            repos = [repo.name for repo in orgs[0].iter_repos()
                     if repo.name.lower() == repo_name.lower()]
            if repos:
                repository = "git@github.com:{org}/{repo}.git".format(
                    org=name,
                    repo=repo_name
                )

    dest_path = get_env_path(name)
    if os.path.exists(dest_path):
        fatal("The organization %s already exists." % name)

    archive_url = "https://github.com/AerisCloud/sample-organization/" \
                  "archive/master.tar.gz"

    os.makedirs(dest_path)
    os.chdir(dest_path)
    curl(archive_url,
         o='%s/master.tar.gz' % dest_path,
         silent=True,
         location=True)

    tar = tarfile.open("%s/master.tar.gz" % dest_path, 'r:gz')
    members = [m for m in tar.getmembers() if '/' in m.name]
    for m in members:
        m.name = m.name[m.name.find('/') + 1:]
    tar.extractall(path=dest_path, members=members)
    tar.close()

    os.unlink("%s/master.tar.gz" % dest_path)

    vgit("init")

    move_shell_to(dest_path)

    success("The %s organization has been created." % name)

    run_galaxy_install(name)

    if repository:
        vgit("remote", "add", "origin", repository)


@cli.command(cls=Command)
@click.argument('organization_name', required=False, default=None)
def goto(organization_name):
    """
    Go to the organization directory.
    """
    if organization_name is None:
        move_shell_to(organization_path)
        print(organization_path)
        return

    if not organization_name.isalnum():
        fatal("Your organization name should only contains alphanumeric "
              "characters.")

    dest_path = get_env_path(organization_name)
    if not os.path.exists(dest_path):
        fatal("The %s organization doesn't exist." % organization_name)

    move_shell_to(dest_path)
    print(dest_path)


if __name__ == '__main__':
    cli()
