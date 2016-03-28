import click


def summary(inventory):
    click.secho("Your action will be executed against the following "
                "datacenters:", fg='cyan')
    click.secho('- %s\n' % inventory, fg='yellow')
