#!/usr/bin/env python

import click
import os
import sys

from git import Repo
from sh import git, ErrorReturnCode_1

from aeriscloud.cli.config import assistant
from aeriscloud.cli.helpers import Command, info, success, \
    move_shell_to, warning, fatal, start_box
from aeriscloud.config import projects_path, config
from aeriscloud.github import Github
from aeriscloud.project import get, from_cwd
from aeriscloud.utils import cd


# verbose git
vgit = git.bake(_out=sys.stdout, _out_bufsize=0, _err_to_out=True)


def _clone_project(project_name):
    gh = Github()

    (gh_repo, forked) = gh.get_repo(project_name, fork=True)
    if not gh_repo:
        click.echo('error: no repository named %s was found on '
                   'your user and configured organizations' %
                   click.style(project_name, bold=True))
        sys.exit(1)

    if forked:
        click.echo('We found a repository named %s and forked it to your '
                   'user, it now accessible at the following url:\n'
                   '%s' % (forked.full_name, gh_repo.html_url))

    dest_path = os.path.join(projects_path(), project_name)
    click.echo('We will clone %s in %s\n' % (gh_repo.ssh_url, dest_path))

    vgit('clone', gh_repo.ssh_url, dest_path)

    # add our upstream remote
    if gh_repo.parent:
        repo = Repo(dest_path)
        repo.create_remote('upstream', gh_repo.parent.ssh_url)


def _update_project(project):
    with cd(project.folder()):
        info('We will update the project %s' %
             click.style(project.name(), bold=True))

        repo = Repo(project.folder())
        remotes = [remote.name for remote in repo.remotes]

        updated_from_upstream = False
        if 'upstream' not in remotes:
            click.secho('warning: your repository has no configured upstream, '
                        'skipping update', fg='yellow')
        else:
            out = git('branch', '-a')
            remote_branch_name = 'remotes/upstream/' + repo.active_branch.name
            rebase = False
            for line in out.split('\n'):
                if remote_branch_name in line:
                    rebase = True
                    break

            if rebase:
                try:
                    vgit('pull', '--rebase', 'upstream', repo.active_branch)
                except ErrorReturnCode_1:
                    fatal('error: unable to update the project')
                updated_from_upstream = True

                if 'origin' in remotes:
                    vgit('push', 'origin', repo.active_branch)

        if 'origin' in remotes and not updated_from_upstream:
            vgit('pull', 'origin', repo.active_branch)

        success('The project %s has been updated' %
                click.style(project.name(), bold=True))


def _check_github_config():
    if config.get('github', 'enabled', default='false') == 'false':
        if click.confirm('GitHub configuration is missing, do you want to '
                         'run the config assistant?', default=True):
            config.set('github', 'enabled', 'true')
            assistant()

    if not config.has('github', 'token'):
        fatal('error: github is not configured')


@click.command(cls=Command, epilog='''Example:

\b
* To download a project and start the box:
$ aeris fetch --up <project>

\b
* To download a project, start the box and run make all:
$ aeris fetch --make all <project>

\b
* To download a project and select the box to start:
$ aeris fetch --up --box <box> <project>''')
@click.option('--up', is_flag=True,
              help='Start the box after fetching the project')
@click.option('--make', 'make_cmd',
              help='Run the given make command after booting up the box'
                   '(will start it even if up is not set)',
              metavar='<cmd>')
@click.option('--box', 'box_name', help='Set the box to use for up or make',
              metavar='<box>')
@click.argument('project_name', metavar='<project>', default=None,
                required=False)
def cli(up, make_cmd, box_name, project_name):
    """
    Allows you to fetch a project from GitHub
    """
    _check_github_config()

    if not project_name:
        project = from_cwd()
        if not project:
            fatal("""You are not in a project directory.
You need to specify what project you want to fetch.""")
        project_name = project.name()
    else:
        project = get(project_name)

    if not project:
        _clone_project(project_name)
    else:
        _update_project(project)

    # reload project if created
    project = get(project_name)

    # move the user in the project directory
    move_shell_to(project.folder())

    if not project.initialized():
        warning('warning: this is not an aeriscloud project, aborting...')
        sys.exit(1)

    # make_cmd implies up
    if make_cmd:
        up = True

    box = project.box(box_name)
    if up:
        info('AerisCloud will now start your box and provision it, '
             'this op might take a while.')
        start_box(box)

        if make_cmd:
            print(make_cmd)
            box.ssh_shell('make %s' % make_cmd)


if __name__ == '__main__':
    cli()
