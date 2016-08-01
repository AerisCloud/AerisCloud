#!/usr/bin/env python

import click
import os
import shlex
import shutil
import sys

from sh import git, ErrorReturnCode

from aeriscloud.cli.helpers import Command, info, fatal, success, warning, \
    move_shell_to
from aeriscloud.ansible import inventory_path, get_inventory_list


@click.group()
def cli():
    """
    Manage inventories
    """
    pass


vgit = git.bake(_out=sys.stdout, _out_bufsize=0, _err_to_out=True)


def update():
    for inventory in os.listdir(inventory_path):
        if not os.path.exists(os.path.join(inventory_path, inventory, '.git')):
            info("Skip %s" % inventory)
            continue

        info("Updating %s ..." % inventory)
        os.chdir(os.path.join(inventory_path, inventory))
        try:
            vgit('pull')
        except ErrorReturnCode:
            fatal("Unable to update the inventories.")
    success("All the inventories have been updated.")


def update_inventory(name, dest_path):
    if not os.path.exists(os.path.join(dest_path, '.git')):
        warning("The %s inventory is not a git repository and has not "
                "been updated." % name)
        return

    click.echo('We will update the %s inventory' % name)
    os.chdir(dest_path)
    try:
        vgit('pull')
    except ErrorReturnCode:
        fatal("Unable to update the inventory %s." % name)
    success("The %s inventory has been updated." % name)


@cli.command(cls=Command)
@click.argument('name', required=False)
@click.argument('path', required=False)
def install(name, path):
    """
    Install inventories.
    """
    if not name:
        update()
        return

    if not name.isalnum():
        fatal("Your inventory name should only contains alphanumeric "
              "characters.")

    dest_path = os.path.join(inventory_path, name)
    if os.path.exists(dest_path):
        update_inventory(name, dest_path)
        return

    if not path:
        fatal("You must specify a path to a local directory or an URL to a "
              "git repository to install a new inventory.")

    if os.path.exists(path) and os.path.isdir(path):
        if not os.path.exists(os.path.dirname(dest_path)):
            os.mkdir(os.path.dirname(dest_path))
        os.symlink(path, dest_path)
    else:
        click.echo('We will clone %s in %s\n' % (path, dest_path))
        try:
            vgit('clone', path, dest_path)
        except ErrorReturnCode:
            fatal("Unable to install the inventory %s." % name)
    success("The %s inventory has been installed." % name)


@cli.command(cls=Command)
@click.argument('inventory_name')
def remove(inventory_name):
    """
    Remove inventories.
    """
    if not inventory_name.isalnum():
        fatal("Your inventory name should only contains alphanumeric "
              "characters.")

    dest_path = os.path.join(inventory_path, inventory_name)
    if not os.path.exists(dest_path):
        fatal("The %s inventory doesn't exist." % inventory_name)

    if not click.confirm("Do you want to delete the %s inventory?" %
                         inventory_name,
                         default=False):
        info("Aborted. Nothing has been done.")
        return

    if os.path.isdir(dest_path) and not os.path.islink(dest_path):
        shutil.rmtree(dest_path)
    else:
        os.remove(dest_path)
    success("The %s inventory has been removed." % inventory_name)


@cli.command(cls=Command)
def list():
    """
    List inventories.
    """
    for inventory in get_inventory_list():
        print(inventory[1])


@cli.command(cls=Command)
@click.argument('inventory')
def edit(inventory):
    """
    Edit an inventory file.
    """
    EDITOR = os.environ.get('EDITOR', 'vim')
    editor = shlex.split(EDITOR)
    editor.append(os.path.join(inventory_path, inventory))

    from subprocess import call

    try:
        call(editor)
    except OSError:
        raise Exception("Failed to open editor (%s): %s" % (EDITOR, inventory))


@cli.command(cls=Command)
@click.argument('inventory_name', required=False, default=None)
def goto(inventory_name):
    """
    Go to the inventory directory.
    """
    if inventory_name is None:
        move_shell_to(inventory_path)
        print(inventory_path)
        return

    if not inventory_name.isalnum():
        fatal("Your inventory name should only contains alphanumeric "
              "characters.")

    dest_path = os.path.join(inventory_path, inventory_name)
    if not os.path.exists(dest_path):
        fatal("The %s inventory doesn't exist." % inventory_name)

    move_shell_to(dest_path)
    print(dest_path)


if __name__ == '__main__':
    cli()
