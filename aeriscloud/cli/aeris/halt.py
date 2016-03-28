#!/usr/bin/env python

import click
import sys

from aeriscloud.cli.helpers import standard_options, Command


@click.command(cls=Command)
@standard_options(multiple=True)
def cli(boxes):
    """
    Halt a box, can be started back using up
    """
    for project, project_boxes in boxes.iteritems():
        running_boxes = project_boxes.running()
        project_name = click.style(project.name(), fg='magenta')

        if not running_boxes:
            click.secho('No running boxes found for %s' % project_name,
                        fg='yellow', bold=True)
            continue

        click.secho('Halting boxes for %s' % project_name,
                    fg='blue', bold=True)
        for box in running_boxes:
            res = box.halt()
            if res == 0:
                click.echo(''.join([
                    click.style('\tbox ', fg='green'),
                    click.style(box.name(), bold=True),
                    click.style(' has been halted.', fg='green')
                ]))
            else:
                click.echo(''.join([
                    click.style('\tan error occured while halting box ',
                                fg='red'),
                    click.style(box.name(), bold=True),
                ]))
                sys.exit(res)


if __name__ == '__main__':
    cli()
