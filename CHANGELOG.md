Changelog
=========

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

