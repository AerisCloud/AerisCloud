from __future__ import print_function

import collections
import contextlib
import os
import re
import sys

from arrow import now
from click import secho
from functools import update_wrapper
from jinja2 import Environment, PackageLoader
from platform import system
from sh import Command, CommandNotFound


# python3 compat
if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
    from shlex import quote
else:
    # imported from python 3.3
    _find_unsafe = re.compile(r'[^\w@%+=:,./-]').search

    def quote(s):
        """Return a shell-escaped version of the string *s*."""
        if not s:
            return "''"
        if _find_unsafe(s) is None:
            return s

        # use single quotes, and put single quotes into double quotes
        # the string $'b is then quoted as '$'"'"'b'
        return "'" + s.replace("'", "'\"'\"'") + "'"


# inspired from https://wiki.python.org/moin/PythonDecoratorLibrary
def memoized(func):
    _cache = {}

    def _deco(*args, **kwargs):
        if 'clear_cache' in kwargs or 'clear_cache_only' in kwargs:
            _cache.clear()
            if 'clear_cache_only' in kwargs:
                return  # we don't care about the output
            del kwargs['clear_cache']
        if not isinstance(args, collections.Hashable):
            return func(*args, **kwargs)
        if args in _cache:
            return _cache[args]
        else:
            value = func(*args, **kwargs)
            _cache[args] = value
            return value

    return update_wrapper(_deco, func)


@contextlib.contextmanager
def cd(path):
    """
    Change the context dir of the following folders
    Example:

    with cd(project.path()):
        do_something()

    :param path: str
    :return: None
    """
    oldPath = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldPath)


def timestamp(text, **kwargs):
    """
    Writes text with a timestamp
    :param text:
    :return:
    """
    for line in text.split('\n'):
        # TODO: something we could do is detect the last ansi code on each
        # line and report it to the next line so that multiline codes
        # are not reset/lost
        secho('[%s] ' % (now().format('HH:mm:ss')), fg='reset', nl=False)
        secho(line, **kwargs)


@memoized
def jinja_env(package_name='aeriscloud', package_path='templates'):
    return Environment(loader=PackageLoader(package_name, package_path))


def local_ip():
    """
    Retrieve the first ip from the interface linked to the default route

    :return str
    """
    sys_name = system()
    if sys_name == 'Darwin':
        # OSX
        route = Command('route')
        ifconfig = Command('ifconfig')

        iface = [
            line.strip()
            for line in route('-n', 'get', 'default')
            if line.strip().startswith('interface')
        ][0].split(':')[1].strip()
        return [
            line.strip()
            for line in ifconfig(iface)
            if line.strip().startswith('inet ')
        ][0].split(' ')[1]
    elif sys_name == 'Linux':
        try:
            ip = Command('ip')
            iface = [
                line.strip()
                for line in ip('route')
                if line.strip().startswith('default ')
            ][0].split(' ')[4]
        except CommandNotFound:
            route = Command('route')
            iface = [
                line.strip()
                for line in route('-n')
                if line.startswith('0.0.0.0')
            ][0].split(' ').pop()

        try:
            # try with IP
            ip = Command('ip')
            return [
                line.strip()
                for line in ip('addr', 'show', iface)
                if line.strip().startswith('inet ')
            ][0].split(' ')[1].split('/')[0]
        except CommandNotFound:
            pass

        # fallback to ifconfig
        ifconfig = Command('ifconfig')
        return [
            line.strip()
            for line in ifconfig(iface)
            if line.strip().startswith('inet ')
        ][0].split(' ')[1]

    return None
