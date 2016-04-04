from github3 import authorize, GitHubError, GitHub
from platform import node

from .config import config


class Github:
    def __init__(self, _ask_credentials=None, _ask_2fa=None):
        self.last_error = None

        self._ask_credentials = _ask_credentials
        self._ask_2fa = _ask_2fa

        self.gh = GitHub(token=self._get_authorization_token())
        self.user = self.gh.user()

    def _get_authorization_token(self):
        if not config.has('github', 'token') or \
           not config.get('github', 'token'):
            if not self._ask_credentials:
                raise RuntimeError('Github Token is not set in the '
                                   'configuration and no function was set to '
                                   'ask for credentials')

            token = self._gen_authorization_token()
            config.set('github', 'token', token)
            config.save()

        return config.get('github', 'token')

    def _gen_authorization_token(self, counter=0, creds=None):
        """
        This function creates the authorization token for AerisCloud.
        If an existing token exists for this computer, it adds a #N counter
        next to the name.
        """
        if creds:
            user, pwd = creds['user'], creds['pwd']
        else:
            (user, pwd) = self._ask_credentials()

        note = 'AerisCloud on %s' % (node())
        if counter > 0:
            note += ' #%d' % counter

        try:
            auth = authorize(user, pwd, ['repo', 'read:org'], note=note,
                             two_factor_callback=self._ask_2fa)
            return auth.token
        except GitHubError as e:
            if not e.errors or e.errors[0]['code'] != 'already_exists':
                raise

            # token exists, increment counter
            counter += 1
            return self._gen_authorization_token(counter=counter,
                                                 creds={'user': user,
                                                        'pwd': pwd})

    def get_organizations(self):
        return [org for org in self.gh.iter_orgs()]

    def get_repo(self, name, fork=False):
        """
        Find a repository in the available ogranizations, if fork is set to
        True it will try forking it to the user's account
        """
        # check on the user
        repo = self.gh.repository(self.user.login, name)

        if repo:
            return repo, None

        if not config.has('github', 'organizations'):
            return False, None

        # then on configured organization
        organizations = config.get('github', 'organizations').split(',')

        for org in organizations:
            repo = self.gh.repository(org, name)
            if repo:
                break

        if not repo:
            return False, None

        if not fork:
            return repo, None

        return repo.create_fork(), repo
