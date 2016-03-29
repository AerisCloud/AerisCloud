AerisCloud
===========

`Getting Started`_ | `Full Documentation`_ | `Releases`_ | `Issues`_

AerisCloud is a tool that gives application developers development environments
that are identical to the production servers, and gives system administrators a
way to organize their infrastructure as it is growing in size.

.. _`Getting Started`: https://aeriscloud.github.io/AerisCloud/getting-started.html
.. _`Full Documentation`: https://aeriscloud.github.io/AerisCloud/
.. _`Releases`: https://github.com/AerisCloud/AerisCloud/releases
.. _`Issues`: https://github.com/AerisCloud/AerisCloud/issues

Installation
------------

Read the instructions in the `Getting Started`_ page from the documentation.

Usage
-----

.. highlight:: bash

Please note, that to make the following commands to work,
you need to set up an organization as described in the `Organization`_ documentation page.

For developers::

  # Create a new project
  aeris init foo

  # Start VMs
  aeris up

  # Stop VMs
  aeris halt

Read the full documentation in the `Getting Started`_ page from the documentation.

For server operators::

  # Provision production servers for projectA
  cloud provision my-org/production my-org/projectA

  # Execute a job
  cloud job my-org/role-name/job-name my-org/projectA --limit="group-name" \
                                                      --extra-vars="aws_access_key=xxx" \
                                                      --extra-vars="aws_secret_key=xxx"

Read the full documentation in the `server operators Getting Started`_ page from the documentation.

.. _`server operators Getting Started`: https://aeriscloud.github.io/AerisCloud/server-operators/getting-started.html
.. _`Organization`: https://aeriscloud.github.io/AerisCloud/organization.html

Why should I use AerisCloud?
----------------------------

- As a developer, you will have an easy method to define the environment in which your application will run in,
  and other developers will be able to easily replicate the same environment.

- As a server operator, it will help you to organize your inventories and playbooks in one place.
  The CLI will be easier to understand as you will only have to provide the names of the playbook and inventory to use,
  instead of whole paths, options and arguments of *ansible-playbook*.

- The ansible playbooks are shared among development and production environments.

Contributing
------------

See the `contributing guide`_ in the documentation.

.. _`contributing guide`: https://wizcorp.github.io/AerisCloud/contributing.html
