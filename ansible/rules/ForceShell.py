import ansiblelint.utils
from ansiblelint import AnsibleLintRule

class ForceShell(AnsibleLintRule):
    id = 'AERISCLOUD0004'
    shortdesc = 'Use shell or raw for any command execution'
    description = 'Use shell or raw for any command execution'
    tags = ['productivity']


    def matchtask(self, file, task):
        # The meta files don't have any tasks
        if file['type'] == 'meta':
            return False

        # Ignore role from galaxy
        role = ansiblelint.utils.rolename(file['path'])
        if role.find('.') > -1:
            return False

        if isinstance(task, basestring):
            return False

        # Task should not use the command module
        if task['action']['module'] == 'command':
            return True

        return False
