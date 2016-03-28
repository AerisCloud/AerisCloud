from __future__ import absolute_import

from click.core import Group
from sphinx.ext.autodoc import Documenter

from aeriscloud.cli.main import get_cli


def setup(app):
    app.add_autodocumenter(ClickDocumenter)


class ClickDocumenter(Documenter):
    """
    This is not a generic documenter for click, even though I'd like it to be,
    that is because we use a custom MultiCommand with symbolic links all over
    the place
    """
    objtype = "click"
    titles_allowed = True

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return False

    def resolve_name(self, modname, parents, path, base):
        return (path or '') + base, []

    def generate(self, more_content=None, real_modname=None,
                 check_module=False, all_members=False):
        self.directive.info('Building doc for command %s' % self.name)

        # retrieve main cli object
        cli = get_cli(self.name)

        self.add_block(command_header.format(
            name=self.name,
            subline=(len(self.name)+4) * '-'
        ), self.name)

        ctx = cli.make_context(self.name, [''])

        # add general documentation
        self.add_block(cli.get_help(ctx), self.name, indent=2)

        self.gen_subcommands(cli, ctx)

    def gen_subcommands(self, multi_cmd, ctx):
        for cmd_name in multi_cmd.list_commands(ctx):
            subctx = multi_cmd.make_context('%s %s' % (
                ctx.info_name,
                cmd_name
            ), [''])

            self.add_block(subcommand_header.format(
                name=subctx.info_name,
                ref_name=subctx.info_name.replace(' ', '-'),
                subline=(len(subctx.info_name)+4) * '-'
            ), cmd_name)

            # get command and retrieve help
            cmd = multi_cmd.get_command(subctx, cmd_name)
            self.add_block(cmd.get_help(subctx), cmd_name, indent=2)

            if isinstance(cmd, Group):
                self.gen_subcommands(cmd, subctx)

    def add_block(self, text, source, indent=0):
        for line in text.split('\n'):
            self.add_line((u' ' * indent) + line.decode('utf-8'), source)


command_header = """
.. _command-{name}:

``{name}``
{subline}

 ::
"""

subcommand_header = """
.. _{ref_name}:

``{name}``
{subline}

 ::
"""
