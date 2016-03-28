from __future__ import print_function

import click
import os
import sys

from aeriscloud import __version__ as ac_version
from click._compat import strip_ansi
from functools import update_wrapper
from requests.exceptions import HTTPError

from ..box import BoxList
from ..config import config, verbosity
from ..expose import ExposeConnectionError, ExposeTimeout
from ..log import set_log_level, set_log_file, get_logger
from ..project import get, from_cwd, all as all_projects
from ..utils import jinja_env, timestamp
from ..virtualbox import list_vms

logger = get_logger('cli.helpers')


# Have both -h and --help
class Command(click.Command):
    # This is inherited by the Context to switch between pure POSIX and
    # argparse-like argument parsing. Setting it to false will push any
    # unknown flag to the argument located where the flag was declared
    allow_interspersed_args = config.get('config', 'posix', default=False)

    def __init__(self, *args, **kwargs):
        cs = dict(help_option_names=['-h', '--help'])
        super(Command, self).__init__(context_settings=cs,
                                      *args, **kwargs)


# Automatically load commands from the cli folder
class AerisCLI(click.MultiCommand):
    def __init__(self, command_dir, *args, **kwargs):
        cs = dict(help_option_names=['-h', '--help'])
        params = [
            click.Option(
                param_decls=['-v', '--verbose'],
                count=True,
                help='Make commands verbose, use '
                     'multiple time for higher verbosity'
            ),
            click.Option(
                param_decls=['--log-file'],
                help='When using the verbose flag, redirects '
                     'output to this file'
            )
        ]
        super(AerisCLI, self).__init__(context_settings=cs, params=params,
                                       *args, **kwargs)
        self.command_dir = command_dir

        no_setup = 'AC_NO_ASSISTANT' in os.environ \
                   and os.environ['AC_NO_ASSISTANT'] == '1'
        if not no_setup and sys.stdout.isatty() and not config.complete():
            click.echo('''
It seems it is the first time you are launching AerisCloud, or new
configuration options were added since the last update. We can guide
you through a series of questions to setup your configuration.
''', err=True)
            if not click.confirm('Run configuration assistant', default=True):
                return
            from .config import assistant

            assistant()

    def list_commands(self, ctx):
        excluded = ['complete', 'test']

        rv = [filename[:-3].replace('_', '-') for filename in
              os.listdir(self.command_dir)
              if filename.endswith('.py') and
              filename[:-3] not in excluded and
              not filename.startswith('__')]
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        ns = {}
        fn = os.path.join(self.command_dir, name.replace('-', '_') + '.py')

        if not os.path.exists(fn):
            click.echo('error: unknown command: %s' % name)
            sys.exit(1)

        with open(fn) as f:
            code = compile(f.read(), fn, 'exec')
            eval(code, ns, ns)
        return ns['cli']

    def invoke(self, ctx):  # noqa
        # setup logging
        if 'verbose' in ctx.params and ctx.params['verbose']:
            level = max(10, 40 - ctx.params['verbose'] * 10)
            set_log_level(level)
            verbosity(ctx.params['verbose'])
        if 'log_file' in ctx.params and ctx.params['log_file']:
            set_log_file(ctx.params['log_file'])

        # try running the command
        try:
            super(AerisCLI, self).invoke(ctx)
        except SystemExit:
            raise
        except click.UsageError as e:
            click.secho('error: %s' % e.message, err=True, fg='red')
            click.echo(e.ctx.command.get_help(e.ctx), err=True)
            sys.exit(e.exit_code)
        except (ExposeTimeout, ExposeConnectionError):
            warning('warning: expose is not available at the moment')
        except KeyboardInterrupt:
            logger.error('keyboard interrupt while running subcommand "%s"',
                         ctx.invoked_subcommand, exc_info=sys.exc_info())
            warning('\nwarning: ctrl+c pressed, aborting')
        except:
            log_id = None
            if config.has('config', 'raven'):
                from raven import Client
                client = Client('requests+' + config.get('config', 'raven'))
                log_id = client.get_ident(client.captureException(
                    tags={
                        'python': sys.version,
                        'aeriscloud': ac_version,
                        'platform': sys.platform
                    },
                    extra={
                        'user': os.environ['USER']
                    }
                ))

            logger.error('uncaught exception while running subcommand "%s"',
                         ctx.invoked_subcommand, exc_info=sys.exc_info())
            if log_id:
                fatal('error: an internal exception caused "%s" '
                      'to exit unexpectedly (log id: %s)' % (ctx.info_name,
                                                             log_id))
            else:
                fatal('error: an internal exception caused "%s" '
                      'to exit unexpectedly' % ctx.info_name)


def start_box(box, provision_with=None):
    # if the vm is suspended, just resume it
    res = 0

    provision = provision_with or []

    if 'shell' not in provision and box.status() != 'not created':
        provision.append('shell')

    extra_args = []
    if provision:
        extra_args = ['--provision-with', ','.join(provision)]

    manual_provision = False
    if box.status() == 'saved':
        manual_provision = True
        click.echo('Resuming box %s' % box.name())

    if not box.is_running():
        try:
            extra_args_copy = extra_args[:]
            if '--provision-with' in extra_args_copy:
                extra_args_copy.insert(0, '--provision')
            res = box.up(*extra_args_copy)
        except (ExposeTimeout, ExposeConnectionError):
            warning('warning: expose is not available at the moment')
    else:
        hist = box.history()
        if not hist or (
            'failed_at' in hist[-1] and
                hist[-1]['failed_at']
        ) or hist[-1]['stats'][box.name()]['unreachable'] > 0:
            # run provisioning if last one failed
            res = box.vagrant('provision')

        box.expose()  # just in case

    if manual_provision:
        box.vagrant('provision', *extra_args)

    if res == 0 or res is True:
        timestamp(render_cli('provision-success', box=box))
    else:
        timestamp(render_cli('provision-failure'))

    # refresh cache
    list_vms(clear_cache_only=True)

    return res


# used by standard options, resolve a single box
def _single_box_decorator(start_prompt=True):  # noqa
    def _wrap(func):
        @click.option('-p', '--project', 'project_name',
                      metavar='[project]',
                      help='Which project to use, by default'
                           'use the current folder.')
        @click.option('-b', '--box', 'box_name',
                      metavar='[box]',
                      help='Which box to use, by default uses '
                           'the first available.')
        @click.pass_context
        def _deco(ctx, project_name, box_name, *args, **kwargs):
            if not project_name:
                project = from_cwd()
                if not project:
                    fatal('error: you must be in a project directory '
                          'or specify the --project option')
            else:
                project = get(project_name)
                if not project:
                    fatal('error: invalid project: %s' % (project_name))

            if not box_name:
                boxes = project.boxes()
                if not boxes:
                    fatal('error: no infra for project %s' % (project_name))
                box = boxes[0]
            else:
                box = project.box(box_name)
                if not box:
                    fatal('error: invalid box: %s' % (box_name))

            if not box.is_running() and start_prompt:
                if click.confirm('warning: the box you specified is not '
                                 'running, do you want to start it?',
                                 default=True):
                    try:
                        start_box(box)
                    except HTTPError as e:
                        fatal(e.message)

            return ctx.invoke(func, box=box, *args, **kwargs)

        return update_wrapper(_deco, func)
    return _wrap


def _multi_project_parser(project_names):
    projects = []
    if not project_names:
        project = from_cwd()

        if not project:
            fatal('error: you must be in a project directory '
                  'or specify the --project option')

        projects.append(project)
    else:
        for project_name in project_names:
            project = get(project_name)

            if not project:
                fatal('error: invalid project: %s' % project_name)

            projects.append(project)

    return projects


# used by standard options, resolve a multiple boxes and support --all
def _multi_box_decorator(func):
    @click.option('-p', '--project', 'project_names',
                  multiple=True,
                  metavar='[project]',
                  help='Which project to use, by default use'
                       'the current folder.')
    @click.option('-b', '--box', 'box_names', multiple=True,
                  metavar='[box]',
                  help='Which box to use, by default uses '
                       'all the boxes from the project.')
    @click.option('-a', '--all', is_flag=True,
                  help='Target all boxes from all projects')
    @click.pass_context
    def _deco(ctx, project_names, box_names, all, *args, **kwargs):
        boxes = {}

        if all:
            projects = all_projects()
            for project in projects:
                boxes[project] = project.boxes()
        else:
            projects = _multi_project_parser(project_names)

            # if we matched more than one project, it does not make sense
            # to parse boxes
            if len(projects) > 1 or not box_names:
                for project in projects:
                    boxes[project] = project.boxes()
            else:
                project = projects[0]
                for box_name in box_names:
                    box = project.box(box_name)

                    if not box:
                        fatal('error: invalid box: %s' % box_name)

                    if project not in boxes:
                        boxes[project] = BoxList()

                    boxes[project].append(box)

        return ctx.invoke(func, boxes=boxes, *args, **kwargs)

    return update_wrapper(_deco, func)


# allow a CLI command to support the --project, --box, --all options
def standard_options(multiple=False, start_prompt=True):
    """
    Add the standard --project and --box options to a command
    :param multiple: Whether to find a single or multiple boxes
    :param start_prompt: When using single boxes, ask the user to start it if
                         offline
    """
    if multiple:
        return _multi_box_decorator
    else:
        return _single_box_decorator(start_prompt)


# small cli helpers
def get_input(prompt):
    from prompt_toolkit.contrib.shortcuts import get_input as pt_get_input

    return pt_get_input(prompt)


def bold(text, **kwargs):
    return click.style(text, bold=True, **kwargs)


def success(text, **kwargs):
    click.secho(text, fg='green', **kwargs)


def info(text, **kwargs):
    click.secho(text, fg='cyan', **kwargs)


def warning(text, **kwargs):
    click.secho(text, fg='yellow', err=True, **kwargs)


def error(text, **kwargs):
    click.secho(text, fg='red', err=True, **kwargs)


def fatal(text, code=1, **kwargs):
    error(text, **kwargs)
    sys.exit(code)


class CLITable(object):
    """
    Helps displaying a dynamically sized table a la docker ps
    """
    COL_PADDING = 2

    def __init__(self, *cols):
        self._cols = cols
        self._header_out = False

    def _str(self, data, size):
        str_real_len = len(strip_ansi(data))
        return data + (' ' * (size - str_real_len))

    def _compute_col_sizes(self, data):
        sizes = {}
        # prepend data with header
        data = [dict(zip(self._cols, self._cols))] + data
        for row in data:
            for name, row_data in row.iteritems():
                real_len = len(strip_ansi(row_data))
                if name not in sizes or real_len > sizes[name]:
                    sizes[name] = real_len
        # filter unknown values
        self._sizes = dict([
            (key, length + self.COL_PADDING)
            for key, length in sizes.iteritems()
            if key in self._cols
        ])

    def _header(self):
        if self._header_out:
            return

        self._header_out = True
        for name in self._cols:
            click.echo(self._str(name.upper(), self._sizes[name]), nl=False)
        click.echo('')

    def echo(self, data):
        if not isinstance(data, list):
            data = [data]

        self._compute_col_sizes(data)
        self._header()

        for row in data:
            for name in self._cols:
                row_data = ''
                if name in row:
                    row_data = row[name]
                click.echo(self._str(row_data, self._sizes[name]), nl=False)
            click.echo('')


# Both following functions were shamelessly taken and adapted from
# http://stackoverflow.com/questions/566746
def _ioctl_gwinsz(fd):
    try:
        import fcntl
        import termios
        import struct

        rc = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
                                             '1234'))
    except:
        return
    return rc


def move_shell_to(path):
    """
    If the process is called through the function set in scripts/env.sh,
    will move the user to the given path on successful exit

    :param path: str
    """
    if 'AERIS_CD_TMP_FILE' in os.environ:
        with open(os.environ['AERIS_CD_TMP_FILE'], 'w') as f:
            f.write(path)


class JinjaColors(object):
    def __getattr__(self, item):
        return click.style('', fg=item, reset=False)


def render_cli(template, **kwargs):
    env = jinja_env('aeriscloud.cli', 'templates')
    template = env.get_template(template + '.j2')
    kwargs['fg'] = JinjaColors()
    kwargs['bold'] = click.style('', bold=True, reset=False)
    kwargs['reset'] = click.style('')
    return template.render(**kwargs)
