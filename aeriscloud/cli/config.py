import click
import os
import re
import sys

from click.exceptions import Abort
from github3 import GitHubError
from requests.exceptions import HTTPError

from .prompt import AerisCompletableList, AerisPrompt
from ..config import config, projects_path
from ..expose import Client
from ..github import Github
from ..utils import memoized

_bold_aeriscloud = click.style('AerisCloud', bold=True)


# cannot import from helpers :(
def _warning(text):
    click.secho(text, fg='yellow', err=True)


def _error(text):
    click.secho(text, fg='red', err=True)


def _fatal(text, code=1):
    _error(text)
    sys.exit(code)


def _setup_project_folder():
    if projects_path():
        return

    click.echo('''You will need to define a projects folder where all
your %s projects will be stored.
''' % _bold_aeriscloud)

    default_pf = '~/AerisCloudProjects'
    pf = click.prompt('Where do you want to store your projects?',
                      default=default_pf)

    if not pf.strip():
        pf = default_pf

    if pf.startswith('~'):
        pf = os.path.expanduser(pf)

    if not os.path.exists(pf):
        if click.confirm('The folder %s does not exist, do you want to '
                         'create it?' % pf, default=True):
            os.makedirs(pf)
        else:
            _fatal('error: configuration aborted, %s does not exists' % pf)
    elif not os.path.isdir(pf):
        _fatal('error: a file named %s already exists and is not a directory')

    config.set('config', 'projects_path', pf)


@memoized
def _github_ask_2fa():
    code = None
    while not code:
        code = click.prompt('Github 2FA code')
    return code


def _github_ask_credentials():
    click.echo('''
We need your GitHub credentials to create an access token to be stored in
AerisCloud. Your credentials won't be stored anywhere.

The access token will allow AerisCloud to access your private repositories
as well as those owned by any organization you might be a member of.

You can revoke this access token at any time by going to this URL:
%s
''' % (click.style('https://github.com/settings/applications', bold=True)))

    user = None
    pwd = None
    while not user:
        user = click.prompt('Github username')
    while not pwd:
        pwd = click.prompt('Github password', hide_input=True)

    return user, pwd


def _setup_github_orgs(gh):
    organizations = [org.login for org in gh.get_organizations()]
    org_compl_list = AerisCompletableList(organizations)

    click.echo('''
Which {0} do you wish to use? (autocomplete available)
You can enter {0} on different lines, or several on the same line separated \
by spaces.
'''.format(click.style('organizations', bold=True)))

    orgs_cli = AerisPrompt('> ', completer=org_compl_list)
    while True:
        click.echo('Available organizations:')
        for org in organizations:
            if org in org_compl_list.selected:
                click.echo('* %s' % click.style(org, fg='green'))
            else:
                click.echo('* %s' % org)
        click.echo('')

        orgs_input = orgs_cli.get_input()

        if orgs_input:
            for organization in orgs_input.strip().split(' '):
                if not organization:
                    continue
                if organization in organizations:
                    org_compl_list.select(organization)
                elif (organization[0] == '-' and
                        organization[1:] in org_compl_list):
                    org_compl_list.unselect(organization[1:])
                else:
                    _error('''%s was not recognized as a valid organization.
Please enter a valid organization.''' % organization)
        else:
            break

    config.set('github', 'organizations', ','.join(org_compl_list.selected))


def _try_setup_github():
    try:
        gh = Github(_ask_credentials=_github_ask_credentials,
                    _ask_2fa=_github_ask_2fa)
        _setup_github_orgs(gh)
    except GitHubError as e:
        if e.code == 401:
            _error('error: %s' % e.message)
            raise e
        _fatal('error: %s' % e.message)
    except BaseException as e:
        _fatal('error: %s' % e.message)


def _setup_github():
    if (config.has('github', 'enabled') and
            config.get('github', 'enabled') == 'false'):
        return

    if (config.has('github', 'token') and
            config.has('github', 'organizations')):
        return

    if not click.confirm('Do you wish to enable Github integration?',
                         default=True):
        config.set('github', 'enabled', 'false')
        return

    config.set('github', 'enabled', 'true')

    for i in range(0, 3):
        try:
            _try_setup_github()
            break
        except GitHubError:
            pass
    else:
        sys.exit(1)


def _test_aeris_credentials(email, pwd):
    try:
        client = Client(email, password=pwd)
        return client
    except RuntimeError as e:
        click.echo('error: %s' % e.message)
    except HTTPError as e:
        if e.message == '401 Client Error: Unauthorized':
            click.echo('error: invalid credentials')


def _ask_aeriscd_credentials():
    click.echo('''We will now setup your connection to aeris.cd

If this is the first time signing up to aeris.cd,
please enter new credentials now.
If you already have an account, please enter your
registered credentials instead.
''')

    user_email = config.get('aeris', 'email', default=None)
    # TODO: that regexp is actually bad, or at least we should convert
    # unicode domains to their ascii representation
    re_email = re.compile(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', re.I)
    while True:
        email = click.prompt('Please enter your email', default=user_email)
        if re_email.match(email):
            break
        click.echo('Please enter a valid email')
        email = ''

    client = None
    while not client:
        pwd = click.prompt('Please enter your aeris.cd password',
                           hide_input=True)
        if pwd:
            client = _test_aeris_credentials(email.strip(), pwd)

    return client


def _setup_aeriscd():
    if not config.has('aeris', 'url'):
        click.echo('''If your organization provides an aeris.cd service,
provide the API url now (ask your sysops if you do not know the url).
''')

        api_url = click.prompt('aeris.cd url', default='')
        config.set('aeris', 'url', api_url)

        if not api_url:
            click.echo('''
No url provided, aeris.cd and the expose feature will be disabled, if you
wish to enable it later just call %s.
''' % click.style('aeris config aeris.url "your.url.tld"', bold=True))
            return

    # if the url was set to empty, just exit
    if not config.get('aeris', 'url'):
        return

    if config.has('aeris', 'token') and config.has('aeris', 'email'):
        return

    client = _ask_aeriscd_credentials()

    config.set('aeris', 'email', client.get_email())
    config.set('aeris', 'token', client.get_token())


def assistant():
    """
    Do the initial configuration for AerisCloud
    """
    click.echo('''
Hello, this assistant will guide you through configuring
%s for the first time.
''' % _bold_aeriscloud)

    try:
        _setup_project_folder()
        _setup_github()
        _setup_aeriscd()
    except (KeyboardInterrupt, Abort):
        click.secho('error: setup interrupted by the user', fg='red')
        sys.exit(1)

    config.save()
