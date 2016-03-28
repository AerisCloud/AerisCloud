#!/usr/bin/env python

import click
import sys

from aeriscloud.cli.helpers import Command
from aeriscloud.config import config


def _display_option(section, option, value):
    if sys.stdout.isatty():
        click.echo('%s.%s = %s' % (
            click.style(section, fg='blue'),
            click.style(option, fg='blue'),
            click.style(value, fg='green')
        ))
    else:
        # remove spaces when piped so that users can send that
        # to cut/awk/etc...
        click.echo('%s.%s=%s' % (section, option, value))


def _unset_option(option):
    try:
        section, key = option.split('.')
        if not config.unset(section, key):
            raise ValueError('unknown option')
        config.save()
    except BaseException:
        click.secho('error: unknown option %s' % option,
                    fg='red', err=True)
        sys.exit(1)


@click.command(cls=Command)
@click.option('-a', '--all', is_flag=True, help='Show all options')
@click.option('-u', '--unset', is_flag=True, help='Unset an option')
@click.option('--raw', is_flag=True, default=False)
@click.argument('option', default=None, required=False)
@click.argument('value', default=None, required=False)
@click.pass_context
def cli(ctx, all, unset, raw, option, value):
    """
    Get and set your AerisCloud options
    """
    if all:
        for section, values in config.dump().iteritems():
            for key, value in values.iteritems():
                _display_option(section, key, value)
        return

    if unset:
        if not option:
            click.secho('error: missing option name', fg='red', err=True)
            click.echo(cli.get_help(ctx))
            sys.exit(1)
        _unset_option(option)
        return

    if option:
        section, key = option.split('.')

        if not config.has(section, key) and not value:
            click.secho('error: unknown option %s' % option,
                        fg='red', err=True)
            sys.exit(1)

        if not value:
            value = config.get(section, key)
            if raw:
                click.echo(value)
            else:
                _display_option(section, key, value)
            return
        else:
            config.set(section, key, value)
            config.save()
            _display_option(section, key, config.get(section, key))
    else:
        click.echo(cli.get_help(ctx))


if __name__ == '__main__':
    cli()
