import ansiblelint.utils
from ansiblelint import AnsibleLintRule

#
# The errors could be fixed with the following commands:
# - sed -E -i '' 's/- name: ([^"].*[^"])$/- name: "\1"/' ansible/roles/*/tasks/*.yml
# - sed -E -i '' 's/- name: ([^"].*[^"])$/- name: "\1"/' ansible/roles/*/handlers/*.yml
#


class NameBetweenQuotes(AnsibleLintRule):
    id = 'AERISCLOUD0001'
    shortdesc = 'Names must be between quotes'
    description = 'Names must between quotes'
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
        if module == 'name' and \
                not (args[0].startswith('"') and args[-1].endswith('"')):
            if file['type'] in ['tasks', 'handlers'] and not line.startswith('-'):
                return False
            return True
