from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import jinja2
import os
from ansible.plugins.action import ActionBase
from ansible.utils.hashing import checksum_s
from ansible.utils.unicode import to_bytes

class ActionModule(ActionBase):

    TRANSFERS_FILES = True

    def create_aeriscloud_directory(self, tmp, task_vars):
        module_args = {
            'path': '/etc/aeriscloud.d',
            'state': 'directory',
            'mode': 0755,
            'owner': 'root',
            'group': 'root'
        }
        return self._execute_module(module_name='file',
                                    module_args=module_args,
                                    tmp=tmp,
                                    task_vars=task_vars)

    def get_checksum(self, dest, all_vars, try_directory=False, source=None, tmp=None):
        try:
            dest_stat = self._execute_remote_stat(dest, all_vars=all_vars, follow=False, tmp=tmp)

            if dest_stat['exists'] and dest_stat['isdir'] and try_directory and source:
                base = os.path.basename(source)
                dest = os.path.join(dest, base)
                dest_stat = self._execute_remote_stat(dest, all_vars=all_vars, follow=False, tmp=tmp)

        except Exception as e:
            return dict(failed=True, msg=to_bytes(e))

        return dest_stat['checksum']

    def run(self, tmp=None, task_vars=None):
        ''' handler for template operations '''
        if task_vars is None:
            task_vars = dict()

        res = self.create_aeriscloud_directory(tmp, task_vars)
        if 'failed' in res:
            return res

        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name', None)
        services = self._task.args.get('services', None)

        data = {
            'services': []
        }

        for service in services:
            if 'when' in service and not self._task.evaluate_conditional(service['when'], task_vars):
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

        # Expand any user home dir specification
        dest = self._remote_expand_user(os.path.join('/etc/aeriscloud.d', name))
        directory_prepended = True

        remote_user = task_vars.get('ansible_ssh_user') or self._play_context.remote_user
        if not tmp:
            tmp = self._make_tmp_path(remote_user)
            self._cleanup_remote_tmp = True

        local_checksum = checksum_s(resultant)
        remote_checksum = self.get_checksum(dest, task_vars, not directory_prepended, source=dest, tmp=tmp)
        if isinstance(remote_checksum, dict):
            # Error from remote_checksum is a dict.  Valid return is a str
            result.update(remote_checksum)
            return result

        diff = {}
        new_module_args = {
            'mode': 0644,
            'owner': 'root',
            'group': 'root'
        }

        if (remote_checksum == '1') or (local_checksum != remote_checksum):

            result['changed'] = True
            # if showing diffs, we need to get the remote value
            if self._play_context.diff:
                diff = self._get_diff_data(dest, resultant, task_vars, source_file=False)

            if not self._play_context.check_mode:  # do actual work through copy
                xfered = self._transfer_data(self._connection._shell.join_path(tmp, 'source'), resultant)

                # fix file permissions when the copy is done as a different user
                self._fixup_perms(xfered, remote_user)

                # run the copy module
                new_module_args.update(
                    dict(
                        src=xfered,
                        dest=dest,
                        original_basename=os.path.basename(dest),
                        follow=True,
                    ),
                )
                result.update(self._execute_module(
                    module_name='copy',
                    module_args=new_module_args,
                    task_vars=task_vars,
                    tmp=tmp,
                    delete_remote_tmp=False))

            if result.get('changed', False) and self._play_context.diff:
                result['diff'] = diff

        else:
            # when running the file module based on the template data, we do
            # not want the source filename (the name of the template) to be used,
            # since this would mess up links, so we clear the src param and tell
            # the module to follow links.  When doing that, we have to set
            # original_basename to the template just in case the dest is
            # a directory.
            new_module_args.update(
                dict(
                    path=dest,
                    src=None,
                    original_basename=os.path.basename(dest),
                    follow=True,
                ),
            )
            result.update(self._execute_module(
                module_name='file',
                module_args=new_module_args,
                task_vars=task_vars,
                tmp=tmp,
                delete_remote_tmp=False))

        self._remove_tmp_path(tmp)

        return result
