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

Usage
-----

.. highlight:: bash

For developers::

  # Create a new project
  aeris init foo
  # Start VMs
  aeris up
  # Stop VMs
  aeris halt
  # Update VMs
  aeris update

For system admins::

  # Provision production servers for projectA
  cloud provision my-org/production my-org/projectA
  # Do a DB dump
  cloud job wizcorp/xtradb/backup my-org/projectA --limit="replica.xtradb" \
                                                  --extra-vars="aws_access_key=xxx" \
                                                  --extra-vars="aws_secret_key=xxx"

Contributing
------------

See the `contributing guide`_ in the documentation.

.. _`contributing guide`: https://wizcorp.github.io/AerisCloud/contributing.html
