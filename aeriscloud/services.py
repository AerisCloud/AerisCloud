import os

from .ansible import organization_path


def services(organization, env='production'):
    service_list = {}

    if not organization:
        return service_list

    service_file = os.path.join(organization_path,
                                organization,
                                'env_%s.yml' % env)

    with open(service_file) as f:
        service = None
        for line in f.readlines():
            if service:
                service_name = line[line.find(':') + 1:].strip()
                service_list[service_name] = service
                service = None
            elif line.startswith('# service:'):
                service = {
                    'description': line[line.find(':') + 1:].strip(),
                    'default': False
                }
            elif line.startswith('# default service:'):
                service = {
                    'description': line[line.find(':') + 1:].strip(),
                    'default': True
                }

    return service_list
