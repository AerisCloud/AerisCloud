import os
from ansible import utils
from ansible import errors
from ansible.runner.return_data import ReturnData
import base64
import jinja2


class ActionModule(object):
    TRANSFERS_FILES = True

    def __init__(self, runner):
        self.runner = runner

    def create_aeriscloud_directory(self, conn, tmp, inject):
        module_args = ''
        options = {
            'path': '/etc/aeriscloud.d',
            'state': 'directory',
            'mode': 0755,
            'owner': 'root',
            'group': 'root'
        }

        return self.runner._execute_module(conn, tmp, 'file', module_args,
                                           inject=inject, complex_args=options,
                                           persist_files=True)

    def run(self, conn, tmp, module_name, module_args, inject,
            complex_args=None, **kwargs):

        if not self.runner.is_playbook:
            raise errors.AnsibleError("in current versions of ansible, "
                                      "aeriscloud_service is only usable "
                                      "in playbooks")

        # load up options
        options = {}
        if complex_args:
            options.update(complex_args)
        options.update(utils.parse_kv(module_args))

        res = self.create_aeriscloud_directory(conn, tmp, inject)
        if not res.is_successful():
            return res

        data = {
            'services': []
        }

        for service in options['services']:
            if 'when' in service \
                    and not utils.check_conditional(service['when'],
                                                    self.runner.basedir,
                                                    inject):
                continue
            if 'path' in service and 'protocol' not in service:
                service['protocol'] = 'http'
            if 'path' not in service:
                service['path'] = ''
            if 'protocol' not in service:
                service['protocol'] = 'tcp'
            data['services'].append(service)

        template = jinja2.Template("""{%- for service in services -%}
{{ service['name'] }},{{ service['port'] }},{{ service['path'] }},{{ service['protocol'] }}
{% endfor %}""")

        resultant = template.render(data)

        dest = os.path.join('/etc/aeriscloud.d', options['name'])
        module_args = ''
        options = {
            'path': dest,
            'mode': 0644,
            'owner': 'root',
            'group': 'root',
            'state': 'file'
        }

        local_checksum = utils.checksum_s(resultant)
        remote_checksum = self.runner._remote_checksum(conn, tmp, dest, inject)

        if remote_checksum in ('0', '2', '3', '4'):
            # Note: 1 means the file is not present which is fine; template
            # will create it
            result = dict(failed=True, msg="failed to checksum remote file."
                                           " Checksum error code: %s" % remote_checksum)
            return ReturnData(conn=conn, comm_ok=True, result=result)

        if local_checksum != remote_checksum:

            # template is different from the remote value

            # if showing diffs, we need to get the remote value
            dest_contents = ''

            if self.runner.diff:
                # using persist_files to keep the temp directory around to avoid needing to grab another
                dest_result = self.runner._execute_module(conn, tmp, 'slurp',
                                                          "path=%s" % dest,
                                                          inject=inject,
                                                          persist_files=True)
                if 'content' in dest_result.result:
                    dest_contents = dest_result.result['content']
                    if dest_result.result['encoding'] == 'base64':
                        dest_contents = base64.b64decode(dest_contents)
                    else:
                        raise Exception(
                            "unknown encoding, failed: %s" % dest_result.result)

            xfered = self.runner._transfer_str(conn, tmp, 'source', resultant)

            # fix file permissions when the copy is done as a different user
            if self.runner.become and self.runner.become_user != 'root':
                self.runner._remote_chmod(conn, 'a+r', xfered, tmp)

            # run the copy module
            new_module_args = dict(
                src=xfered,
                dest=dest,
                follow=True,
            )
            module_args_tmp = utils.merge_module_args(module_args,
                                                      new_module_args)

            if self.runner.noop_on_check(inject):
                return ReturnData(conn=conn, comm_ok=True,
                                  result=dict(changed=True),
                                  diff=dict(before_header=dest,
                                            after_header='',
                                            before=dest_contents,
                                            after=resultant))
            else:
                res = self.runner._execute_module(conn, tmp, 'copy',
                                                  module_args_tmp,
                                                  inject=inject,
                                                  complex_args=None)
                if res.result.get('changed', False):
                    res.diff = dict(before=dest_contents, after=resultant)
                return res
        else:
            # when running the file module based on the template data, we do
            # not want the source filename (the name of the template) to be used,
            # since this would mess up links, so we clear the src param and tell
            # the module to follow links.  When doing that, we have to set
            # original_basename to the template just in case the dest is
            # a directory.
            module_args = ''
            new_module_args = dict(
                src=None,
                follow=True,
            )
            # be sure to inject the check mode param into the module args and
            # rely on the file module to report its changed status
            if self.runner.noop_on_check(inject):
                new_module_args['CHECKMODE'] = True
            options.update(new_module_args)
            return self.runner._execute_module(conn, tmp, 'file', module_args,
                                               inject=inject,
                                               complex_args=options)
