#!/usr/bin/env python

import click
import os
import sys

from aeriscloud.ansible import ansible_path, get_job_file, list_jobs
from aeriscloud.cli.helpers import standard_options, Command


@click.command(cls=Command)
@click.argument('job', required=False)
@click.argument('extra', nargs=-1)
@standard_options(start_prompt=False)
def cli(box, job, extra):
    """
    Run a maintenance job in a box.

    Call without a job to get the job list
    """
    if not job:
        for job in list_jobs():
            (job_name, job_desc) = job
            if not job_desc:
                print('* %s' % (
                    click.style(job_name, bold=True),
                ))
            else:
                print('* %-35s - %s' % (
                    click.style(job_name, bold=True),
                    job_desc
                ))
        return

    if not box.is_running():
        click.secho('error: box %s is not running' % box.name(), fg='red')
        sys.exit(1)

    playbook = os.path.join(ansible_path, 'dev_jobs.yml')
    ansible = box.ansible()
    ansible(playbook,
            '--extra-vars', 'job_file=%s' % get_job_file(job),
            '--extra-vars', 'deploy_user="vagrant"',
            '--private-key', box.ssh_key(),
            *extra,
            _out=sys.stdout,
            _err=sys.stderr)


if __name__ == '__main__':
    cli()
