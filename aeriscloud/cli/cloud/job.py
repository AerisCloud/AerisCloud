import click
import sys

from aeriscloud.ansible import run_job, list_jobs, get_job_file
from aeriscloud.cli.helpers import Command, fatal
from aeriscloud.cli.cloud import summary


def get_job_help(job):
    job_desc = None
    job_help = ''
    try:
        jobfile = get_job_file(job)
    except Exception as e:
        fatal(e.message)

    with open(jobfile) as f:
        line = f.readline()
        if line.startswith('# '):
            job_desc = line[2:].strip()
        while True:
            line = f.readline()
            if not line:
                break
            if line == '\n':
                continue
            if not line.startswith('#'):
                break
            job_help += line
    return job_desc, job_help


@click.command(cls=Command)
@click.argument('job', required=False)
@click.argument('inventory', required=False)
@click.argument('extra', nargs=-1)
def cli(job, inventory, extra):
    """
    Run maintenance jobs on remote servers.
    """
    if not job:
        for job in list_jobs():
            (job_name, job_desc) = job
            if not job_desc:
                click.echo('* %s' % (
                    click.style(job_name, bold=True),
                ))
            else:
                click.echo('* %-35s - %s' % (
                    click.style(job_name, bold=True),
                    job_desc
                ))
        return

    if not inventory:
        (job_desc, job_help) = get_job_help(job)

        click.echo(click.style(job, bold=True))
        if job_desc:
            click.echo("%s" % job_desc)
        if job_help:
            click.echo("\n%s" % job_help.strip())
        return

    summary(inventory)

    try:
        sys.exit(run_job(job, inventory, *extra, timestamp=True))
    except IOError as e:
        click.secho('error: %s' % e.message, err=True, fg='red')
        sys.exit(1)
    except NameError as e:
        click.secho('error: %s' % e.message, err=True, fg='red')
        sys.exit(1)


if __name__ == '__main__':
    cli()
