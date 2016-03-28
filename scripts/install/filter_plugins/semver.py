# Uses code from python-semver

import re

_REGEX = re.compile('^(?P<major>(?:0|[1-9][0-9]*))'
                    '\.(?P<minor>(?:0|[1-9][0-9]*))'
                    '(\.(?P<patch>(?:0|[1-9][0-9]*)))?'
                    '(\-(?P<prerelease>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?'
                    '(\+(?P<build>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$')

def _parse_semver(version):
    """
    Parse version to major, minor, patch, pre-release, build parts.
    """
    match = _REGEX.match(version)
    if match is None:
        raise ValueError('%s is not valid SemVer string' % version)

    verinfo = match.groupdict()

    for key in ['major', 'minor', 'patch']:
        if verinfo[key] is not None:
            verinfo[key] = int(verinfo[key])

    return verinfo

def _compare(v1, v2):
    for key in ['major', 'minor', 'patch']:
        if key not in v1 or key not in v2:
            break
        if v1[key] > v2[key]:
            return 1
        if v1[key] < v2[key]:
            return -1
    return 0

_operators = ['>', '<', '==', '!=', '<=', '>=', '~=']
def semver(value, operator, version):
    if operator not in _operators:
        raise RuntimeError('invalid operator %s' % operator)

    value = _parse_semver(value)
    version = _parse_semver(version)
    comparison = _compare(value, version)

    possibilities = {
        '>': [1],
        '<': [-1],
        '>=': [0, 1],
        '<=': [-1, 0],
        '==': [0],
        '!=': [-1, 1],
        '~=': [0] # same as equal actually
    }

    if operator in possibilities:
        return comparison in possibilities[operator]

class FilterModule(object):
    filter_map = {
        'semver': semver
    }

    def filters(self):
        return self.filter_map
