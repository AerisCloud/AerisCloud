from __future__ import print_function

import click
import os
import re
import subprocess32
import sys

from aeriscloud.cli.helpers import Command, standard_options, \
    error, fatal, info, success, bold
from aeriscloud.utils import local_ip, quote


def _get_local_url(box):
    forwards = box.forwards()

    if 'web' not in forwards:
        raise RuntimeError('Box has no exposed web app')

    port = forwards['web']['host_port']
    return "http://%s:%s" % (local_ip(), port)


def _get_aeris_url(box):
    return box.browse()


def _get_url(server, box):
    if not box.project.initialized():
        error("This project doesn't contain a %s file." % (
            bold(".aeriscloud.yml")))
        return None

    if server == 'local':
        return _get_local_url(box)
    elif server == 'aeris.cd':
        return _get_aeris_url(box)
    elif server == 'production':
        return box.project.get_production_url()
    else:
        return None


def _get_search_path():
    files = os.listdir(os.getcwd())

    # Unity Project
    if 'Assets' in files and 'ProjectSettings' in files:
        return os.path.join(os.getcwd(), 'Assets'), 'Unity'

    return None, None


def _search_variables(search_path, variable):
    files = set()

    cmd = "grep -rI '%s = ' %s" % (variable, quote(search_path))
    try:
        grep = subprocess32.check_output(cmd, shell=True)
    except subprocess32.CalledProcessError:
        return []

    for line in grep.split('\n'):
        if not line.strip():
            continue
        filename = line[:line.find(':')].strip()
        if filename.startswith('.'):
            continue
        files.add(filename)

    return files


def _replace_variable(filename, variable, value):
    tmp_filename = os.path.join(
        os.path.dirname(filename),
        '.' + os.path.basename(filename) + '.swp'
    )
    expr = re.compile('^(.*' + variable + '\s*=\s*[\'"]?)([^\s\'"]*)(.*)$')
    with open(filename) as input:
        with open(tmp_filename, 'w') as output:
            for line in input:
                if variable in line.decode('utf-8-sig'):
                    line = expr.sub('\g<1>' + value + '\g<3>', line)
                output.write(line)
    os.rename(tmp_filename, filename)


def _build_unity(platform, unity_path):
    methods = {
        'ios': 'BuildEditorScript.PerformiOSBuild',
        'android': 'BuildEditorScript.PerformAndroidBuild',
        'osx': 'BuildEditorScript.PerformMacOSXBuild'
    }
    if platform not in methods:
        fatal("Unsupported platform.")

    unity_path = os.path.join(unity_path, "Unity.app/Contents/MacOS/Unity")

    command = "{unity_path} -quit -batchmode " \
              "-executeMethod {method} " \
              "-logFile ./build.log " \
              "-projectPath {current_dir}" \
        .format(unity_path=quote(unity_path),
                method=methods[platform],
                current_dir=quote(os.getcwd()))
    info("""The following command will be executed:
{0}.""".format(bold(command)))
    returncode = subprocess32.call(command, shell=True)
    if returncode != 0:
        error("An error occurred, please check the content "
              "of the {0} log file.".format(bold('build.log')))
        sys.exit(returncode)

    if platform == 'ios':
        os.chdir(os.path.join(os.getcwd(), 'Build', 'iPhone'))
        command = "xcodebuild -scheme Unity-iPhone archive " \
                  "-archivePath Unity-iPhone.xcarchive"
        info("""The following command will be executed:
{0}.""".format(bold(command)))
        subprocess32.check_call(command, shell=True)
        command = "xcodebuild -exportArchive " \
                  "-exportFormat ipa " \
                  "-archivePath \"Unity-iPhone.xcarchive\" " \
                  "-exportPath \"Unity-iPhone.ipa\" " \
                  "-exportProvisioningProfile \"wildcard_Development\""
        info("""The following command will be executed:
{0}.""".format(bold(command)))
        subprocess32.check_call(command, shell=True)

    success("""
Your project has been built.
""")


def _build(project_type, platform, **kwargs):
    info("Building {project} project for {platform}.".format(
        project=bold(project_type),
        platform=bold(platform)))

    if project_type == 'Unity':
        _build_unity(platform, kwargs['unity'])
    else:
        fatal("Unsupported project type.")


@click.command(cls=Command)
@click.option('-v', '--variable', default='AERISCLOUD_SERVER_ADDRESS',
              help='Specify the variable you want to change')
@click.option('-u', '--unity', default='/Applications/Unity',
              help='Path to your Unity directory')
@click.argument('server',
                type=click.Choice(['production', 'aeris.cd', 'local']))
@click.argument('platform',
                type=click.Choice(['ios', 'android', 'osx']))
@standard_options()
def cli(box, variable, unity, server, platform):
    """
    Build your native application
    """

    search_path, project_type = _get_search_path()
    if not project_type:
        fatal("We were not able to detect the type of your project.")

    info("We detected that your project is using {project}."
         .format(project=bold(project_type)))

    url = _get_url(server, box)
    if not url:
        fatal("Unable to generate the URL for this server.")

    info("""We will replace the value of the {variable} variable by {url}
in files located in the {search_path} directory."""
         .format(variable=bold(variable),
                 url=bold(url),
                 search_path=bold(os.path.relpath(search_path, os.getcwd()))))

    files = _search_variables(search_path, variable)
    for filename in files:
        _replace_variable(filename, variable, url)

    success("""
The {variable} variable has been changed in the following files:
{files}
""".format(variable=bold(variable),
           files='\n'.join(
               map(lambda x: '* ' + bold(os.path.relpath(x, os.getcwd())),
                   files)
               )
           ))

    if platform:
        _build(project_type, platform, unity=unity)


if __name__ == "__main__":
    cli()
