#!/usr/bin/env python

import click
import json
import os
import re
import sys

from ordereddict import OrderedDict

from aeriscloud.cli.helpers import Command
from aeriscloud.basebox import baseboxes
from aeriscloud.config import basebox_bucket


@click.group()
def cli():
    """
    Manage base boxes
    """
    pass


@cli.command(cls=Command)
@click.option('-j', '--json', 'output_json', is_flag=True)
def list(output_json):
    """
    List the available base boxes
    """
    boxes = baseboxes()

    if output_json:
        json.dump(boxes, sys.stdout)
        return

    click.secho('The following boxes are available:\n', fg='yellow')

    if not boxes:
        click.secho('  No box found', fg='cyan')
        sys.exit(0)

    for infra in boxes:
        click.secho('* %s:' % (infra), fg='blue', bold=True)
        for box in boxes[infra]:
            click.echo('\t* %s' % (click.style(box, fg='green')))


def _generate_meta(metadata, basebox, box, version):
    if basebox not in metadata:
        metadata[basebox] = {
            'versions': [],
            'name': basebox,
            'description': 'This is a simple %s box.' % (box),
            'short_description': 'A standard %s box.' % (box)
        }

        if basebox.endswith('prepackaged'):
            metadata[basebox]['description'] = ''.join([
                'This is a prepackaged %s box, which contains ' % box,
                'all the required packages to start your project.'
            ])

            metadata[basebox]['short_description'] = \
                'A prepackaged %s box.' % box

    url = 'http://%s/%s-%s.box' % (basebox_bucket(), basebox, version)
    metadata[basebox]['versions'].append({
        'status': 'active',
        'version': version,
        'providers': [
            {
                'url': url,
                'name': 'virtualbox'
            }
        ]
    })


@cli.command(cls=Command)
@click.option('-j', '--json', 'output_json', is_flag=True,
              help="Output metadata as JSON")
@click.option('-p', '--path', 'output_path', default='meta',
              help="Where to save the metadata files")
def generate(output_json, output_path):
    """
    Generate metadata for boxes (sysadmin tool)
    """
    boxes = baseboxes()
    semver = re.compile(r'\d+.\d+.\d+')

    metadata = OrderedDict()
    for infra in boxes:
        for box in boxes[infra]:
            box, version = box[:box.rfind('-')], box[box.rfind('-') + 1:-4]
            basebox = '/'.join([infra, box])

            if not semver.match(version):
                continue

            _generate_meta(metadata, basebox, box, version)

    # if the path is empty, default to json
    if output_json or not output_path:
        json.dump(metadata, sys.stdout)
        return

    if output_path:
        if not os.path.exists(output_path):
            os.mkdir(output_path)

    # create the proper folder architecture for vagrant
    for basebox, data in metadata.iteritems():
        infra, name = basebox.split('/')

        infra_dir = os.path.join(output_path, infra)
        if not os.path.exists(infra_dir):
            os.mkdir(infra_dir)

        box_file = os.path.join(infra_dir, name)
        with open(box_file, 'w') as outfile:
            json.dump(data, outfile)

    click.secho(
        'The metadata files have been saved in the %s directory.\n'
        'You can upload them to s3 with the following command:\n'
        % output_path,
        fg='green')

    click.echo('s3cmd put --recursive %s -m'
               '\"application/json\" s3://%s/'
               % (output_path, basebox_bucket()))


if __name__ == '__main__':
    cli()
