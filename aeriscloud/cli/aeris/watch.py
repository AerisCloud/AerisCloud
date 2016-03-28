#!/usr/bin/env python
from __future__ import print_function

import click
import os
import signal
import sys
import time

from watchdog.observers import Observer
from watchdog.tricks import AutoRestartTrick

from aeriscloud.cli.aeris.sync import sync
from aeriscloud.cli.helpers import standard_options, Command


class BoxCommandAutoRestart(AutoRestartTrick):
    def __init__(self, box, command, **kwargs):
        AutoRestartTrick.__init__(self, [], **kwargs)
        self.box = box
        self.command = command
        self.state = 'stopped'
        # minimum time between restarts in seconds
        self.last_event = 0
        self.event_buffer = 0.2

    def start(self):
        self.state = 'starting'
        sync(self.box, 'up')
        self.process = self.box.ssh_shell(self.command, popen=True)
        self.state = 'started'

    def poll(self):
        """
        Used to detect if the process quit unexpectedly
        """
        if self.state in ['restarting', 'starting']:
            return None
        if not self.process or self.state == 'stopped':
            return -1
        return self.process.poll()

    def on_any_event(self, event):
        if (time.time() - self.last_event) < self.event_buffer:
            return

        self.state = 'restarting'
        self.stop()
        self.start()
        self.last_event = time.time()


def _setup_watchdog(box, command):
    """
    Setup the watchdog library and return a handler and observer

    :return (BoxCommandAutoRestart, watchdog.observers.Observer)
    """
    # get project config
    project_dir = box.project.folder()
    project_config = box.project.config()

    patterns = ['*.js']
    ignore_patterns = None
    directories = [project_dir]
    run = []
    if 'watch' in project_config:
        watch_config = project_config['watch']

        if 'directories' in watch_config:
            directories = map(lambda x: os.path.join(project_dir, x),
                              watch_config['directories'])

        if 'patterns' in watch_config:
            patterns = watch_config['patterns']

        if 'ignores' in watch_config:
            ignore_patterns = watch_config['ignores']

        if 'run' in watch_config:
            run = watch_config['run'].split(' ')

    if command:
        run = command

    handler = BoxCommandAutoRestart(box, run,
                                    patterns=patterns,
                                    ignore_patterns=ignore_patterns,
                                    stop_signal=signal.SIGTERM)

    click.echo("Watching for changes on files matching %s on directories:" %
               click.style(', '.join(patterns), bold=True))

    observer = Observer(timeout=0.4)
    for directory in directories:
        click.echo(' * %s' % directory)
        observer.schedule(handler, directory, recursive=True)

    return handler, observer


@click.command(cls=Command)
@click.argument('command', nargs=-1, required=False)
@standard_options()
def cli(box, command=None):
    """
    Sync files and restart your application upon file changes
    """
    if not command:
        command = []
    if not box.is_running():
        click.secho('error: box %s is not running' % (box.name()),
                    fg='red', err=True)
        sys.exit(1)

    if box.project.name() == 'aeriscloud':
        click.secho('error: cannot be used on infra boxes',
                    fg='red', err=True)
        sys.exit(1)

    # Handle SIGTERM in the same manner as SIGINT so that
    # this program has a chance to stop the child process.
    def handle_sigterm(_signum, _frame):
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, handle_sigterm)

    (handler, observer) = _setup_watchdog(box, command)

    click.echo('Starting app and watcher')
    handler.start()
    observer.start()

    try:
        while True:
            res = handler.poll()
            if res is not None and res != 0:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()

    click.echo('Stopping watcher and app')

    observer.stop()
    observer.join()
    handler.stop()


if __name__ == '__main__':
    cli()
