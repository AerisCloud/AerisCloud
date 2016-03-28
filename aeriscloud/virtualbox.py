"""
This module encapsulate VirtualBox commands in an easy to use set of commands
"""

from sh import Command, CommandNotFound, ErrorReturnCode_1
import re

from .utils import memoized


class VMNotFound(Exception):
    """
    Thrown when an invalid virtual machine name is provided to one
    of the functions in this lib
    """
    def __init__(self, vm_name):
        msg = 'Virtual Machine "%s" does not exists' % vm_name
        super(Exception, self).__init__(msg)


class HDDNotFound(Exception):
    """
    Thrown when an invalid hdd uuid is provided to one
    of the functions in this lib
    """
    def __init__(self, uuid):
        msg = 'Virtual Hard Drive "%s" does not exists' % uuid
        super(Exception, self).__init__(msg)


class InvalidState(Exception):
    pass

_vbm = None


def VBoxManage(*args, **kwargs):
    global _vbm
    if not _vbm:
        _vbm = Command('VBoxManage')
    return _vbm(*args, **kwargs)


@memoized
def list_vms(running=False):
    """
    Return the list of VM in for the form name => uuid, when the running bool
    is set to true, only return running VMs
    :param running: bool
    :return: dict[str,str]
    """
    try:
        LIST_PARSER = re.compile(r'"(?P<name>[^"]+)" \{(?P<uuid>[^\}]+)\}')
        vms = {}
        list = running and 'runningvms' or 'vms'
        for line in VBoxManage('list', list, _iter=True):
            res = re.match(LIST_PARSER, line)
            if res:
                vms[res.group('name')] = res.group('uuid')
        return vms
    except CommandNotFound:
        return {}


@memoized
def list_hdds():
    """
    Return the list of HDDs in for the form
    uuid => {state, type, location, format, cap}
    :return: dict[str,dict[str,str]]
    """
    hdds = {}
    uuid = None
    for line in VBoxManage('list', 'hdds', _iter=True):
        if not line.strip():
            continue

        key, val = line.strip().split(':')
        val = val.strip()

        if key == 'UUID':
            uuid = val
            hdds[uuid] = {}
        elif uuid:
            hdds[uuid][key] = val

    return hdds


@memoized
def hdd_info(uuid):
    try:
        info = {}
        for line in VBoxManage('showhdinfo', uuid, _iter=True):
            if not line.strip():
                continue
            key, val = line.strip().split(':')
            val = val.strip()
            info[key] = val
        return info
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise HDDNotFound(uuid)
        # something else happened, just let it go
        raise


def hdd_detach(uuid, controller_name, port, device):
    try:
        VBoxManage('storageattach', uuid, '--storagectl', controller_name,
                   '--port', port, '--device', device, '--type', 'hdd',
                   '--medium', 'none')
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise HDDNotFound(uuid)
        # something else happened, just let it go
        raise


def hdd_clone(uuid, new_location, existing=False):
    try:
        if existing:
            VBoxManage('clonehd', uuid, new_location, '--existing')
        else:
            VBoxManage('clonehd', uuid, new_location)
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise HDDNotFound(uuid)
        # something else happened, just let it go
        raise


def hdd_close(uuid, delete=False):
    try:
        if delete:
            VBoxManage('closemedium', 'disk', uuid, '--delete')
        else:
            VBoxManage('closemedium', 'disk', uuid)
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise HDDNotFound(uuid)
        # something else happened, just let it go
        raise


@memoized
def vm_info(name):
    """
    Wrapper around VBoxManage showvminfo
    Return all the information about an existing VM
    :param name: str
    :return: dict[str,str]
    """
    try:
        INFO_PARSER = re.compile(
            r'^("(?P<quoted_key>[^"]+)"|(?P<key>[^=]+))=(?P<value>.*)$')
        info = {}
        for line in VBoxManage('showvminfo', name, '--machinereadable',
                               _iter=True):
            matches = re.match(INFO_PARSER, line)
            if matches:
                key = matches.group('key') or matches.group('quoted_key')
                value = matches.group('value')

                if key and value:
                    info[key] = value
        return info
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise VMNotFound(name)
        # something else happened, just let it go
        raise


@memoized
def vm_network(name):
    """
    Return IP, Mac, Netmask, Broadcast and Status about every interfaces
    of a running VM
    :param name: str
    :return: list[dict[str,str]]
    """
    try:
        networks = []
        count = int(str(VBoxManage('guestproperty', 'get',
                        name, '/VirtualBox/GuestInfo/Net/Count'))[7:])

        mappings = {
            'ip': '/VirtualBox/GuestInfo/Net/%d/V4/IP',
            'mac': '/VirtualBox/GuestInfo/Net/%d/MAC',
            'netmask': '/VirtualBox/GuestInfo/Net/%d/V4/Netmask',
            'status': '/VirtualBox/GuestInfo/Net/%d/Status',
            'broadcast': '/VirtualBox/GuestInfo/Net/%d/V4/Broadcast'
        }

        for i in range(count):
            network = {}
            for map, property in mappings.iteritems():
                prop = VBoxManage('guestproperty', 'get', name, property % i)
                network[map] = str(prop)[7:].strip()
            networks.append(network)

        return networks
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise VMNotFound(name)
        # something else happened, just let it go
        raise


@memoized
def vm_ip(name, id):
    """
    Return a running VMs IP for the given VM name and interface id,
    returns None if not running or the id does not exists
    :param name: str
    :param id: int
    :return: None|str
    """
    try:
        prop = '/VirtualBox/GuestInfo/Net/%d/V4/IP' % (id)
        value = str(VBoxManage('guestproperty', 'get',
                    name, prop))
        if value == 'No value set!':
            return None
        return value[7:].strip()
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise VMNotFound(name)
        # something else happened, just let it go
        raise


def vm_start(name, headless=True):
    """
    Start or resume a VM in headmode by default
    :param name: str
    :param headless: bool
    :return: None
    """
    try:
        VBoxManage('startvm', name, '--type', headless and 'headless' or 'gui')
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise VMNotFound(name)
        if 'VBOX_E_INVALID_OBJECT_STATE' in e.stderr:
            raise InvalidState(e.stderr.split('\n')[0][17:])
        # something else happened, just let it go
        raise


def vm_suspend(name):
    """
    Save the state of a running VM, raises an InvalidState exception
    if the VM is not in a state where it can be saved
    :param name: str
    :return: None
    """
    try:
        VBoxManage('controlvm', name, 'savestate')
    except ErrorReturnCode_1 as e:
        # if the VM was not found
        if 'VBOX_E_OBJECT_NOT_FOUND' in e.stderr:
            raise VMNotFound(name)
        if 'Machine in invalid state' in e.stderr:
            raise InvalidState(e.stderr[17:])
        # something else happened, just let it go
        raise


def version():
    try:
        return str(VBoxManage('--version')).rstrip()
    except CommandNotFound:
        return None
