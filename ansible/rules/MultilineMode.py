import ansiblelint.utils
from ansiblelint import AnsibleLintRule
import re

class MultilineMode(AnsibleLintRule):
    id = 'AERISCLOUD0003'
    shortdesc = 'Actions with arguments must be entered in multiline mode'
    description = 'Actions with arguments must be entered in multiline mode'
    tags = ['formatting']

    def match(self, file, line):
        # Don't check syntax for meta files
        if file['type'] == "meta":
            return False

        # Ignore role from galaxy
        role = ansiblelint.utils.rolename(file['path'])
        if role.find('.') > -1:
            return False

        (module, args, kwargs) = ansiblelint.utils.tokenize(line)

        if module == 'shell' and (len(args) != 1 or args[0] != '|'):
            return "You should use the multiline literal style"

        if len(kwargs) > 1 and module not in ['when', 'value'] and not \
                module.startswith('-') and \
                re.search('^[A-Za-z0-9]+$', module) and \
                re.search('^\s*[A-Za-z0-9]+:$', line):
            return True

        return False

    def matchtask(self, file, task):
        # Don't check syntax for meta files
        if file['type'] == "meta":
            return False

        # Ignore role from galaxy
        role = ansiblelint.utils.rolename(file['path'])
        if role.find('.') > -1:
            return False

        if isinstance(task, basestring):
            return False

        if task['action']['module'] != 'shell':
            for option in task['action']:
                if option.rstrip('\n').find('\n') >= 0:
                    return "Misuse of the literal style"

        return False
