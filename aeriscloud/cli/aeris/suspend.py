#!/usr/bin/env python

import click

from aeriscloud.cli.helpers import standard_options, Command


@click.command(cls=Command)
@standard_options(multiple=True)
def cli(boxes):
    """
    Suspend a running box, see resume
    """
    for project, project_boxes in boxes.iteritems():
        running_boxes = project_boxes.running()
        project_name = click.style(project.name(), fg='magenta')

        if not running_boxes:
            click.secho('No running boxes found for %s' % project_name,
                        fg='yellow', bold=True)
            continue

        click.secho('Suspending boxes for %s' % project_name,
                    fg='blue', bold=True)
        for box in running_boxes:
            box.suspend()
            click.echo(''.join([
                click.style('\tBox ', fg='green'),
                click.style(box.name(), bold=True),
                click.style(' has been suspended.', fg='green')
            ]))


if __name__ == '__main__':
    cli()
