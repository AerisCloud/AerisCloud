AerisCloud Lint rules
=====================

This folder contains the rules used by [ansible-lint](https://github.com/willthames/ansible-lint) to check playbooks for practices and behaviour that could potentially be improved.

Installation
------------

[ansible-lint](https://github.com/willthames/ansible-lint), which is a separate  repository, will be installed by the AerisCloud install script in `~/.AerisCloud/ansible-lint`.


A pre-commit git hook will be installed too.
It will be run before you make a commit.
It will check the syntax of your roles to help you to follow the [guidelines](../../docs/contributors/guidelines.md).

Usage
-----

```
ansible-lint -r ansible/rules ansible/env_production.yml
```

See also
--------

* [ansible-lint repo on Github](https://github.com/willthames/ansible-lint)
* [AerisCloud development guidelines](../../docs/contributors/guidelines.md)
