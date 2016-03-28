#!/usr/bin/env python

import click

from aeriscloud.cli.helpers import standard_options, Command, CLITable

status_table = CLITable('project', 'name', 'image', 'status')


def _status_sort(status):
    return '%s-%s' % (status['project'], status['name'])


@click.command(cls=Command)
@click.option('--show-all', is_flag=True, default=False,
              help='Show boxes that are not created in virtualbox')
@standard_options(multiple=True)
def cli(boxes, show_all):
    """
    Query the status of boxes
    """

    box_status = []
    for project, project_boxes in boxes.iteritems():
        for box in project_boxes:
            # add some nice colors to box status
            status = box.status()
            if not show_all and status == 'not created':
                continue
            color_status = {
                'running': click.style('running', fg='green'),
                'saved': click.style('saved', fg='blue'),
                'poweroff': click.style('powered off', fg='yellow'),
                'not created': click.style('not created', fg='red'),
            }.get(status, status)

            box_status.append({
                'project': project.name(),
                'name': box.name(),
                'image': box.image(),
                'status': color_status
            })

    box_status = sorted(box_status, key=_status_sort)
    status_table.echo(box_status)


if __name__ == '__main__':
    cli()
