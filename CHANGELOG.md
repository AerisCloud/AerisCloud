Changelog
=========

v2.2.0
------

* feature: Upgrade to Ansible 2.2.1.

v2.1.2
------

* feature: `cloud rsync` now uses the `ansible_ssh_common_args` variable.
* feature: Allow to specify the user when using `cloud rsync`.
* fix: make the install playbook work with ansible 2.1.

v2.1.1
------

* feature: Upgrade to Ansible 2.1.4.
* feature: `cloud ssh` now uses the `ansible_ssh_common_args` variable.
* feature: Allow to specify the user when using `cloud ssh`.
* fix: Put the `venv` at beginning of the PATH.
* fix: Append to the default plugin paths instead of replacing them.

v2.1.0
------

* feature: Upgrade to Ansible 2.1.3.
* feature: `ansible-shell` has been replace by `ansible-console`.
* feature: Update `ansible-lint`. 
* cleanup: The `human_log` plugin has been removed.
* cleanup: The `history` plugin has been removed.
* fix: Support for `requirements.yml` in addition to `dependencies.txt` to store role dependencies.
* fix: Fix the `.editorconfig` configuration for YAML files.

v2.0.2
------

* fix: `cloud inventory list` should list inventory files by following symlinks.
* fix: Pin `sh` package version.

v2.0.1
------

* fix: Create the necessary directories if missing when installing inventories and organizations.
* fix: `cloud provision` can now be run against an inventory directory.
* fix: Bucket named with not a resolvable URL are now supported to store vagrant boxes.
* fix: Use [ansible-lint](https://github.com/willthames/ansible-lint) 2.7 instead of the latest available version.
* fix: Set the `INSTALL_DIR` variable when running `aeris update` to correctly update AerisCloud.
* doc: Add the instructions to install only cloud.


v2.0.0
------

* Import code from initial codebase.
* Add Travis CI.
* feature: Set the git remote when using `cloud organization init`.
* feature: `cloud organization init` can guess the git remote url if the organization name matches a GitHub organization.
* fix: The installation playbook must use the path defined by the user for the installation.
* fix: Allow the user to retry if he uses the wrong GitHub credentials when setting up the GitHub integration.
* fix: Don't run the configuration assistant during the install process.
* doc: Improve the README.
* doc: Reintroduce a best practices document for writing roles.

