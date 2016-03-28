#!/usr/bin/env python

import click
import sys

from functools import update_wrapper
from json import dumps
from requests.exceptions import HTTPError

from aeriscloud.cli.helpers import Command, CLITable, success, fatal
from aeriscloud.config import expose_url, expose_username
from aeriscloud.expose import expose_client, expose


def check_expose(func):
    @click.pass_context
    def _deco(ctx, *args, **kwargs):
        if not expose.enabled():
            click.secho('warning: aeris.cd is not enabled', fg='yellow')
            sys.exit(1)
        try:
            return ctx.invoke(func, *args, **kwargs)
        except HTTPError as e:
            fatal(e.message)
    return update_wrapper(_deco, func)


@click.group()
def cli():
    """
    Manage project exposition
    """
    pass


@cli.command(cls=Command)
@click.option('-p', '--project', 'project_names', multiple=True)
@click.option('-i', '--infra', 'infra_names', multiple=True)
@click.option('-b', '--box', 'box_names', multiple=True)
@click.option('--json', is_flag=True)
@check_expose
def list(project_names, infra_names, box_names, json):
    """
    List the exposed projects
    """
    client = expose_client()
    exposed = dict([
        (service['hostname'], service)
        for service in client.get_vms()
        if service['hostname'].endswith(expose_username())
    ])

    services = {}
    for service in expose.list():
        if project_names and service['project'] not in project_names:
            continue

        if infra_names and service['infra'] not in infra_names:
            continue

        box_name = '%s-%s' % (service['project'], service['infra'])
        if box_names and box_name not in box_names:
            continue

        hostname = '%s.%s' % (service['service'], expose_username())
        domain = 'http://%s.%s' % (hostname,
                                   expose_url())

        if service['project'] not in services:
            services[service['project']] = []

        services[service['project']].append({
            'url': domain,
            'port': service['port'],
            'exposed': hostname in exposed
        })

    if json:
        click.echo(dumps(services))
    else:
        exposes = []
        for project in services:
            for domain in services[project]:
                expose_status = click.style('not exposed', fg='red')
                if domain['exposed']:
                    expose_status = click.style('exposed', fg='green')

                exposes.append({
                    'project': project,
                    'url': click.style(domain['url'], fg='cyan'),
                    'port': domain['port'],
                    'status': expose_status
                })

        expose_list_table = CLITable('project', 'url', 'status')
        expose_list_table.echo(exposes)


@cli.command(cls=Command)
@check_expose
def announce():
    """
    Announce all the running services
    """
    res = expose.announce()
    if res:
        success(res)
    else:
        fatal('Expose is not available or misconfigured')


@cli.command(cls=Command)
def start():
    """
    Start the expose server
    """
    expose.start()

    if expose.enabled():
        success('Expose started')
    else:
        fatal('Expose could not start')


@cli.command(cls=Command)
def stop():
    """
    Stop the expose server
    """
    expose.stop()

    if not expose.enabled():
        success('Expose stopped')
    else:
        fatal('Expose could not stop')


@cli.command(cls=Command)
def status():
    """
    Check the status of the expose server
    """
    if expose.enabled():
        success('Expose is running')
    else:
        fatal('Expose is stopped')


if __name__ == '__main__':
    cli()
