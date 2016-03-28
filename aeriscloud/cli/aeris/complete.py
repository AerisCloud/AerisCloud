import click
import os
import sys

from aeriscloud import __version__ as version
from aeriscloud.cli.helpers import Command, render_cli
from aeriscloud.cli.main import get_cli
from aeriscloud.config import aeriscloud_path

complete_cmd = os.path.join(aeriscloud_path, 'venv', 'bin', 'aeris-complete')


def cmd_complete(out, name, cmd, level=1):
    ctx = click.Context(cmd)

    cmpl = {
        'name': name,
        'cmd': cmd,
        'level': level,
        'flags': [opts for param in cmd.params for opts in param.opts
                  if isinstance(param, click.Option)],
        'complete_cmd': complete_cmd
    }

    params = [opts for param in cmd.params for opts in param.opts
              if isinstance(param, click.Parameter) and
              not isinstance(param, click.Option)]

    if isinstance(cmd, click.MultiCommand):
        cmds = cmd.list_commands(ctx)

        for cmd_name in cmds:
            cmd_complete(
                out,
                name + '_' + cmd_name,
                cmd.get_command(ctx, cmd_name),
                level + 1
            )

        cmpl['cmds'] = cmds

        out.write(render_cli('autocomplete-multi', **cmpl))
    else:
        # TODO: we might want to move that list of params somewhere else
        completable = [
            'command',
            'direction',
            'endpoint',
            'env',
            'host',
            'inventory',
            'inventory_name',
            'job',
            'limit',
            'organization_name',
            'platform',
            'project',
            'server',
        ]
        if len(params) == 1 and params[0] in completable:
            cmpl['param'] = params[0]
        elif len(params) > 1:
            cmpl['params'] = [el for el in params if el in completable]

        out.write(render_cli('autocomplete-single', **cmpl))

    if level == 1:
        out.write('complete -F _{0}_completion {0}\n'.format(name))


@click.command(cls=Command)
def cli():
    """
    Generates bash auto-completion script
    """
    sys.stdout.write('# AerisCloud %s\n' % version)
    cmd_complete(sys.stdout, 'aeris', get_cli('aeris'))
    cmd_complete(sys.stdout, 'cloud', get_cli('cloud'))
