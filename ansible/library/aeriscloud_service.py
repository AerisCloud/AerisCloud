# this is a virtual module that is entirely implemented server side

DOCUMENTATION = '''
---
module: aeriscloud_service
short_description: Define AerisCloud services.
description:
    - Configure the services listed when accessing a server using AerisCloud.
options:
  name:
    description:
      - Name of the file containing the services. It should be the name of your role.
    required: true
    default: null
  services:
    description:
      - List of services to define.
    required: true
    default: null
requirements: []
author: Emilien Kenler
extends_documentation_fragment: aeriscloud
'''

EXAMPLES = '''
- name: "Add AerisCloud service definition"
  aeriscloud_service:
    name: nginx
    services:
      - name: Web Server
        port: 80
        path: /
        protocol: http
'''
