Getting Started
===============

As a Server Operator your main job is to take a project and build the
infrastructure, configuration to deploy it quickly and efficiently to
production. Most of the operations a server operator will run are done
with the :doc:`../commands/cloud`.

Managing Roles and Playbooks
----------------------------

This is a quick recap of what was already said in the :doc:`../getting-started`
documentation. Your roles and playbooks are stored in what we call
``organizations``, those are git repositories unique per client/companies
you are working with and allows for easy management of private ansible roles.

If you didn't create an organization yet, a brand new organization can be
created by running the following command::

  cloud organization init my-org

You should be moved inside the organization's folder and be ready to modify it
for your needs, see :doc:`../organization` for more details.

Taking Inventory
----------------

If your company already has an inventory, installing it is as simple as running::

  cloud inventory install git@github.com:my-org/inventory.git

Any valid git repository will do. Updating all your inventories can be done by
running :ref:`cloud-inventory-install` without any repository.

Creating a new inventory
^^^^^^^^^^^^^^^^^^^^^^^^

.. highlight:: bash

The first step with getting ready for production is to create an ansible
inventory that can be used with the :doc:`../commands/cloud`::

  # Move to the inventory folder
  cloud inventory goto
  # Create a new folder for your inventory
  mkdir my-org
  # Then edit your inventory file
  mkdir my-org/projectA
  $EDITOR my-org/projectA/staging

Inventories are just standard ansible inventories, you can find more about
then in the ansible documentation about `Inventory`_.

A simple inventory that would work with the `sample organization`_::

  # Project A
  ## Install the nodejs service on those servers
  [nodejs:children]
  nodejs.host.org

  [nodejs.host.org]
  nodejs1.host.org ansible_ssh_host=172.16.0.1
  nodejs2.host.org ansible_ssh_host=172.16.0.2
  nodejs3.host.org ansible_ssh_host=172.16.0.3

  [nodejs:vars]
  node_version = 0.12.6

  ## Install the mongodb service on those servers
  [mongodb:children]
  mongodb.host.org

  [mongodb.host.org]
  mongodb1.host.org ansible_ssh_host=172.16.1.1
  mongodb2.host.org ansible_ssh_host=172.16.1.2

  [mongodb:vars]
  # Store data on EBS drives
  mongodb_data_path = /data/mongodb

Of course that inventory is missing disk setup (using the ``aeriscloud.disk``)
and a proper gateway/load balancer but you should get the gist of it.

If the ``:vars`` section becomes too large, you can create a ``group_vars``
folder next to your inventory and implement what is described in the ansible
documentation about `Splitting Out Host and Group Specific Data`_.

.. _Inventory: http://docs.ansible.com/intro_inventory.html
.. _sample organization: https://github.com/AerisCloud/sample-organization
.. _Splitting Out Host and Group Specific Data: http://docs.ansible.com/intro_inventory.html#splitting-out-host-and-group-specific-data

Provisioning
------------

Once your inventory, playbooks and roles are in tip-top shape, and your project
is working, comes the time to provision your production or staging servers. For
that the :ref:`cloud-provision` command should be used, like so::

  # Use the production playbook and provision only nodejs on the staging inventory
  cloud provision my-org/production my-org/projectA/staging --limit="nodejs"

The ``--limit`` flag is very useful if you need to provision only part of your
infrastructure or need to do it step by step (like first start with the DB, then
the app, etc...).

Jobs
----

Jobs in AerisCloud are ultra-light playbooks that specialize in running small
commands, ranging from dumping a database to managing the release process of a
project.

They are executed by running the :ref:`cloud-job` command::

  cloud job [JOB] [INVENTORY FILE] [EXTRA PARAMETERS]

Running the command with no argument will yield the list of jobs currently
available in your roles. Running the command with a job but no inventory
specified will then yield the help for that job.

The ``[EXTRA PARAMETERS]`` are passed to ansible directly, always make sure
to at least use the ``--limit`` option so that your job is not run on your
whole inventory.

Creating Jobs
^^^^^^^^^^^^^

Jobs can be created by adding a ``jobs`` folder in a role's folder, for
example creating the ``my-org/mongodb/jobs/backup.yml`` file will make the
``my-org/mongodb/backup`` job available to use with the command.

Documentation for the job is simply written as a large comment at the top
of the file.

Example job::

  # Quick description

  # Longer description, should describe available variables
  # and ansible command-line flags that the user can pass to
  # the job

  - hosts: localhost
    connection: local
    gather_facts: false
    tasks:
      - name: "do something"

