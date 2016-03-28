import ansiblelint.utils
from ansiblelint import AnsibleLintRule


class TaskHasTag(AnsibleLintRule):
    id = 'AERISCLOUD0002'
    shortdesc = 'Tasks must have tag'
    description = 'Tasks must have tag'
    tags = ['productivity']

    def matchtask(self, file, task):
        # The meta files don't have tags
        if file['type'] == 'meta':
            return False

        if isinstance(task, basestring):
            return False

        if file['type'] == 'playbook':
            return False

        # If the task include another task or make the playbook fail
        # Don't force to have a tag
        if task['action']['module'] in ['include', 'fail']:
            return False

        role = ansiblelint.utils.rolename(file['path'])

        # Ignore role from galaxy
        if role.find('.') > -1:
            return False

        # Task should have tags
        if 'tags' not in task:
            return True

        if role.find('ansible-') > -1:
            role = role[8:]

        if role and role not in task['tags']:
            return 'The tag "' + role + '" is not present in this block.'

        if task['action']['module'] == 'apt' and 'pkgs' not in task['tags']:
            return 'The tag "pkgs" must be present'

        if task['action']['module'] == 'apt_repository' \
                and 'repos' not in task['tags']:
            return 'The tag "repos" must be present'

        if task['action']['module'] == 'yum' \
                and set(task['tags']).isdisjoint(['repos', 'pkgs']):
            return 'One of the following tags must be present "repos", "pkgs"'

        if task['action']['module'] == 'copy' \
                and task['action']['dest'].find('/etc/yum.repos.d') >= 0 \
                and 'repos' not in task['tags']:
            return 'The tag "repos" must be present'

        if task['action']['module'] in ['copy', 'template'] \
                and 'files' not in task['tags']:
            return 'The tag "files" must be present'

        if task['action']['module'] == 'sysctl' \
                and 'sysctl' not in task['tags']:
            return 'The tag "sysctl" must be present'

        if task['action']['module'] == 'aeriscloud_service' \
                and 'announce' not in task['tags']:
            return 'The tag "announce" must be present'

        return False
