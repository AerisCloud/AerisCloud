#!/usr/bin/env python

import click

from requests.exceptions import HTTPError

from aeriscloud.cli.helpers import standard_options, Command, start_box, fatal


def _parse_provision(ctx, param, value):
    if not value:
        return []
    provisioners = value.split(',')
    for provisioner in provisioners:
        if provisioner not in ['ansible', 'shell']:
            raise click.BadParameter('provisioner must be on of ansible or '
                                     'shell')
    return provisioners


@click.command(cls=Command)
@click.option('--provision-with', default=None, callback=_parse_provision)
@standard_options(start_prompt=False)
def cli(box, provision_with):
    """
    Starts the given box and provision it
    """
    try:
        return start_box(box, provision_with)
    except HTTPError as e:
        fatal(e.message)


if __name__ == '__main__':
    cli()
