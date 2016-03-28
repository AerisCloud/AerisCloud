Rsync Mode
==========

By default your project folder is shared with your vagrant VM by using the `NFS`_
protocol and mounting your project folder to ``/home/vagrant/{project name}``.
NFS allows accessing the same files both on the host and the guest but it comes
with a trade-off: it can be fairly slow when doing many small file operations.

When you hit that kind of bottleneck, two solutions become available:

* Move the file operations to another folder, using /data work well or
* Enable the :ref:`aeriscloud-yml-use_rsync` flag

When using the rsync mode, instead of using NFS, files will be copied from your
local system to the VM when running aeris commands, making filesystem operations
a lot more efficient at the cost of potential desyncs.

.. _NFS: nfs.com

How?
----

To enable rsync mode:

* First stop your box by calling ``aeris halt``, suspend will not work for
  this operation.
* Edit your :doc:`../configuration/aeriscloud.yml` file and set the :ref:`aeriscloud-yml-use_rsync`
  flag to true.
* Start your box by running ``aeris up``.

Depending on the size of the project, the first copy might take a while. Once
everything is up and running, files will be synchronized from your project
folder to your VM on the following actions:

* :ref:`aeris-up`
* :ref:`aeris-git`
* :ref:`aeris-make`
* :ref:`aeris-sync`
* :ref:`aeris-watch`

If you run any other command, synchronization will not happen so be careful.

Exclude Files from Sync
-----------------------

When synchronization happens it deletes any file on the VM that does not
exist in your local folder, the issue that can emerge with this behaviour
is that folders such as ``node_modules`` or sqlite dbs might be erased.
To prevent this behaviour you can use the :ref:`aeriscloud-yml-rsync_ignores`
option in your :doc:`../configuration/aeriscloud.yml` file.

Manual Sync
-----------

While the commands described above sync data to the VM, you might want to
retrieve the data back to your local environment, to do so AerisCloud
gives you two commands:

* :ref:`aeris-sync` **up** to copy files from your computer to the VM
* :ref:`aeris-sync` **down** to copy files from the VM to your computer

Disabling Rsync
---------------

If you want to go back to NFS at any point, running the same steps as above
but removing the :ref:`aeriscloud-yml-use_rsync` flag will work.

If you wish to keep any file the application might have created on the box,
the easiest way is to remove the :ref:`aeriscloud-yml-rsync_ignores`
configuration and run :ref:`aeris-sync` ``down`` before shutting down the VM.

If you didn't run :ref:`aeris-sync` before restarting, your data is still
safely stored in ``/data/{project name}``.