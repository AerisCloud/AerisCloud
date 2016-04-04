AerisCloud Lint rules
=====================

This folder contains the rules used by [ansible-lint](https://github.com/willthames/ansible-lint) to check playbooks for practices and behaviour that could potentially be improved.

Installation
------------

[ansible-lint](https://github.com/willthames/ansible-lint), which is a separate repository, will be installed with AerisCloud in the *virtualenv*.

You can run `aeris test` to run `ansible-lint` against all the playbooks of your AerisCloud organizations.

Recommended practices for writing roles
---------------------------------------------

* These guidelines are in extension of Ansible
  [Best Practices](http://docs.ansible.com/ansible/playbooks_best_practices.html).
  Please refer to them when in doubt.
* Indent: 2 space. 4 space should be used in script, shell, or raw commands.

### Roles

#### `README.md`

**Must** contain:

* Description of what this role offers
* Documentation of all the configuration variables
* Example entry in an inventory

#### `meta/main.yml`

The supported platforms **must** be indicated.

### Tasks

#### Structure

All tasks **must**:

* Have a descriptive name, which explains what the task will be doing
* Have tags as described in the [Tags](#Tags) section
* When using variables, use spaces between the variable name and
  the opening/closing brackets
* Actions with arguments must be entered in multiline mode
* Use shell for any command execution, and use multiline (However the shell module should be avoided as much as possible).

General example:

```yaml
- name: "Ensure Couchbase is running, and starts on boot"
  service: >
    name=couchbase-server
    state=started
    enabled=yes
  tags:
    - couchbase
```

Example (with shell, running a one-liner):

```yaml
- name: "Add nodes to the cluster"
  shell: |
    {{ couchbase_cmd }} server-add \
      -c {{ hostvars[bootstrap]['ansible_' + private_interface]['ipv4']['address'] }}:8091 \
      -u {{ admin_user }} \
      -p {{ admin_password }} \
      --server-add={{ hostvars[inventory_hostname]['ansible_' + private_interface]['ipv4']['address'] }}:8091 \
      --server-add-username={{ admin_user }} \
      --server-add-password={{ admin_password }}
  when: is_member.rc != 0
  tags:
    - couchbase
    - bootstrap
```

Example with an inline python script - notice the > change to a |;
refer to [YAML documentation for more details](http://www.yaml.org/spec/1.2/spec.html) (TL;DR: check
[this StackOverflow question](http://stackoverflow.com/questions/3790454/in-yaml-how-do-i-break-a-string-over-multiple-lines))

#### Tags

All tasks **must** be tagged in the following fashion:

* With the **name of the role**;
* With **repos** if this task involves preparing a package manager's repositories;
* With **pkgs** if this task copy or installs any packages to a system;
* With **firewall** if this task involves firewall configuration;
* With **files** if this task involves copying a file (either from file or template);
* With **sysctl** if this task uses the [`sysctl`](http://docs.ansible.com/sysctl_module.html) module.

In cases where more than one rule apply (for instance, most configs includes files), always use both tags.

See also
--------

* [ansible-lint repo on Github](https://github.com/willthames/ansible-lint)
* [Ansible Best Practices](http://docs.ansible.com/ansible/playbooks_best_practices.html)
