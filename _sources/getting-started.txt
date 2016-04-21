Getting Started
===============

This guide will step you through installing AerisCloud on your computer, then
starting a new project.

Dependencies
------------

* A UNIX-based operating systems, OSX and Linux are both supported
* Python 2.7
* python-virtualenv
* Virtualbox
* Vagrant 1.7+
* git
* rsync

When using Linux, also make sure to have the a working NFS server installed.

Manual Installation
-------------------

If you already have all the dependencies installed, the first step is to clone
the AerisCloud repository where you want it to be installed (something like
``/opt/aeriscloud`` is a good idea)::

  git clone https://github.com/aeriscloud/aeriscloud.git
  cd aeriscloud

Then run ``make install`` to install all the necessary python dependencies in the
current folder and generate the auto-completion.

When updating, just enter the AerisCloud folder, then just pull the latest
version before running ``make install``.

Setting up AerisCloud
---------------------

Once AerisCloud is installed, the first step is to create a new organization.
Organizations are AerisCloud's way to store your custom playbooks, roles and
anything that might be private to your company, to do so run::

  cloud organization init my-org

If it is your first time launching an AerisCloud command, you should be greeted
by a short assistant to set the global configuration of the tool. Just answer
each step as they are presented to you and if you do not know the answer/right
configuration at that time, feel free to skip that step as you can always make
changes later.

You terminal will then be moved to the folder containing ``my-org``, where the
structure of files should look like::

  ├── README.md
  ├── env_dev.yml
  ├── env_production.yml
  └── roles
      ├── aeriscloud.disk
      ├── aeriscloud.dotdeb
      ├── aeriscloud.elasticsearch
      ├── ... more roles
      └── dependencies.txt

The default generated organization should have several general purpose ansible
roles already installed to allow you to start hacking as soon as possible, but if
anything is missing then ``dependencies.txt`` and ``env_production.yml`` are the
two files to take a look at, more on that in :doc:`organization`.

You are now ready to start using AerisCloud. For more details on the available
configuration options provided by the tool, just jump to :doc:`configuration/index`.

Starting a New Project
----------------------

Now that everything is up and ready, it is time to start a new project, type::

  aeris init my-project --up

A short assistant will ask for your project name, services you wish to enable
and vagrant basebox, the default ``chef/centos-7.0`` basebox should be a safe
starting box but feel free to use your favorite box from Atlas. Just keep in
mind that `AerisCloud roles <https://github.com/AerisCloud>`_ are mainly
designed around CentOS and might not work on other distributions.

The box should start booting up right after that and the provisioning should
start. It will take some time for the provisioning to finish the first time so
you can go a grab a coffee, read your mails, build that treehouse you promised
your kids last summer, etc...

If you want to set some custom variables or edit the virtual machine in any way
before starting it up, remove the ``--up`` flag and take a look at the
:doc:`configuration/aeriscloud.yml` file. Once done you can just manually run::

  aeris up

Once the provisioning is done, you'll have a fully running virtual machine with
the services you selected already installed and running, you can ssh in the machine
with ``aeris ssh``, you can suspend it by running ``aeris suspend``, halt it by
running ``aeris halt`` and finally destroy all traces of it by running ``aeris destroy``.

Your code is mounted to ``/home/vagrant/my-project``, one can use their favorite
language, provided that the proper roles have been installed. The recommended
way to manage dependencies, builds, etc... is through makefiles, the format is
relatively simple though maybe limited. The recommended way to run your make
commands is either via ``aeris ssh`` or the ``aeris make`` shortcut.

.. highlight:: makefile

Here is a sample ``Makefile`` for a tentative node.js app::

  .PHONY: all deps build run

  all: build

  node_modules:
  	npm install

  deps: node_modules

  build: deps
  	gulp assets

  run:
  	node .

What's Next?
------------

At this point you can already work on your application and test it in a contained
environment, but the whole point of AerisCloud is to be able to run the same
provisioning scripts on both your local box and your online servers. To learn how
to do so, proceed to :doc:`commands/cloud` for more details on how ansible is
used and how to write proper roles for your organization.
