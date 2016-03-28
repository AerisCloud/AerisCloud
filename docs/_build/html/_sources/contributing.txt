Contributing
============

Want to contribute to AerisCloud? This page describes the development flow and
the code organization.

AerisCloud is written in Python and is targeted at 2.7 as it is the most
available version and the one provided by default on OSX.

Documentation
-------------

.. highlight:: bash

If you're looking to help document AerisCloud, you will need first to install
sphinx and optionally sphinx-autobuild. The easiest way is to install it in
the AerisCloud virtualenv::

  # Setup virtual environment
  source venv/bin/activate
  # Install Sphinx and Sphinx Autobuild
  pip install sphinx sphinx-autobuild
  # Go to documentation directory
  cd docs
  # Run autobuild
  sphinx-autobuild . _build/html

Running ``make docs`` will install the basic requirements and build the current
version of the documentation. ``make publish-docs`` can then be used to publish
to the ``gh-pages`` branch.

Working on the Source
---------------------

Most of the code is located in the ``aeriscloud`` subfolder as python files.
The recommended way to work on the project is to fork it on GitHub, clone it to
a folder of your choice then run the manual installation steps. When sourcing
``scripts/env.sh`` the ``aeris`` and ``cloud`` commands will point to
your fork, then you can just start hacking at the Python source.

Coding Standards
----------------

AerisCloud uses `flake8`_ to validate it's code, you can run the linters with
:ref:`aeris-test`, indentation is 4 spaces and line length is 80 characters.

.. _flake8: https://flake8.readthedocs.org/

Adding New Commands
-------------------

Commands are stored in the ``aeriscloud/cli/<command>`` folders and are simple
python files exporting at least a ``cli`` function that is a valid `click`_
command.

.. highlight:: python

Here is a very basic example::

  #!/usr/bin/env python
  # aerisclound/cli/aeris/debug.py

  import click

  # The Command class in cli.helpers sets a few default shared
  # between all AerisCloud commands
  from aeriscloud.cli.helpers import Command

  @click.command(cls=Command)
  def cli():
  	# click.echo should be used instead of print()
  	click.echo("hello world")

This command would then be available as ``aeris debug``, also several decorators
are available in ``aeriscloud/cli/helpers.py`` to make your life easier and are
documented in the API doc.

.. _click: http://click.pocoo.org/4/

Submitting Code
---------------

Code should be done in a branch on your fork, then submitted as a PR to the
main repo. Make sure that your PR describe what you are changing in details,
linking back to issues if necessary.

API
---

``aeriscloud.project``
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: aeriscloud.project
   :members:

``aeriscloud.box``
^^^^^^^^^^^^^^^^^^

.. automodule:: aeriscloud.box
   :members:

``aeriscloud.config``
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: aeriscloud.config
   :members:

``aeriscloud.cli.helpers``
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: aeriscloud.cli.helpers
   :members:
