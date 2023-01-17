.. _usage_multicluster:

======================
 Multi Cluster Usage
======================

This is a complete example of setup and usage of ``ocp-network-split`` in
*multi cluster* mode. The environment used in this example was chosen to
demonstrate all important aspects of this use case.

.. _zones_multi:

Zones in Multi Cluster Environment
==================================

For the purpose of this guide, let's assume that our multi cluster environment
consists of 2 OpenShift clusters each running in one zone and one Ceph cluster
stretched across all zones in the following way:

===========  ====================
Zone Name    Zone Members
===========  ====================
a            one Ceph Tiebreaker/Arbiter node (RHEL)
b            OpenShift cluster ``ocp1`` (6 RHEL CoreOS nodes), 3 Ceph nodes (RHEL)
c            OpenShift cluster ``ocp2`` (6 RHEL CoreOS nodes), 3 Ceph nodes (RHEL)
===========  ====================

Command line tools
==================

Overview of command line tools applicable for *multi cluster* use case:

- ``ocp-network-split-mutisetup``: based on given zone config file
  (see :ref:`zone_config_example` example)
  this tool creates env file (with zone configuration for ocp network split
  firewall scripts) and ``MachineConfig``
  yaml file. When we specify a latency value, it will also add latency setup
  into the ``MachineConfig`` yaml file. See section :ref:`mc_setup` for
  details.

- ``ocp-network-split-sched`` requires a zone config file
  (see :ref:`zone_config_example` example) to be specified via
  ``--zonefile`` option. It schedules given network split configuration which
  will start at given time and stop after given number of minutes.
  See section :ref:`mc_split_schedule` for details.

.. _mc_setup:

Setup
=====

To be able to schedule network splits or introduce additional latency, we need
to deploy ocp network split scripts on all nodes of the multi cluster
environment.

Overview of the setup process:

1) :ref:`zone_config_example`: we have both zone config and ansible inventory
   files,
2) :ref:`mc_ssh_config`: we can access all nodes in all zones via ssh,
3) Generate ``MachineConfig`` yaml and zone env files via
   ``ocp-network-split-mutisetup`` command line tool,
4) Deploy the ``MachineConfig`` yaml file on all OpenShift clusters,
5) Deploy the scripts via multicluster ansible playbook(s) on all nodes which
   are not part of any OpenShift cluster (in our case, this means on all Ceph
   nodes).

.. _zone_config_example:

Zone configuration
------------------

Based on our environment described in :ref:`zones_multi` above, we need to
specify our zone configuration in ``zone.ini`` file:

.. code-block:: ini

    [a]
    arbiter.ceph.example.com
    
    [b]
    compute-0.ocp1.example.com
    compute-1.ocp1.example.com
    compute-2.ocp1.example.com
    control-plane-0.ocp1.example.com
    control-plane-1.ocp1.example.com
    control-plane-2.ocp1.example.com
    osd-0.ceph.example.com
    osd-1.ceph.example.com
    osd-2.ceph.example.com
    
    [c]
    compute-0.ocp2.example.com
    compute-1.ocp2.example.com
    compute-2.ocp2.example.com
    control-plane-0.ocp2.example.com
    control-plane-1.ocp2.example.com
    control-plane-2.ocp2.example.com
    osd-3.ceph.example.com
    osd-4.ceph.example.com
    osd-5.ceph.example.com

Moreover we will also need an ansible inventory file with all nodes which are
not part of any OpenShift cluster. In our case this means an inventory with all
Ceph nodes. So if we still have the inventory used with cephadm-ansible, we
can just use it directly:

.. code-block:: ini

    arbiter.ceph.example.com
    osd-0.ceph.example.com
    osd-1.ceph.example.com
    osd-2.ceph.example.com
    osd-3.ceph.example.com
    osd-4.ceph.example.com
    osd-5.ceph.example.com

    [admin]
    osd-0.ceph.example.com
    osd-3.ceph.example.com

Note that the structure of this inventory doesn't matter, the playbooks we will
use simply runs on all hosts from the inventory.

Also note that in both files, we are using `fully qualified domain name`_ to
identify all nodes.

.. _mc_ssh_config:

Local ssh client configuration
------------------------------

We need to make sure that we can login as an admin user to each node via ssh
(``core`` when connecting to a CoreOS OpenShift node, ``root`` otherwise)
without ssh asking for a password. Moreover we need to configure local ssh
client so that this will all work when sheer FQDN of the node is specified,
eg.:

.. code-block:: console

   $ ssh osd-0.ceph.example.com
   Activate the web console with: systemctl enable --now cockpit.socket

   Last login: Tue Jan 10 18:12:34 2023 from 203.0.113.11
   [root@osd-0 ~]#

.. code-block:: console

   $ ssh compute-0.ocp1.example.com
   Red Hat Enterprise Linux CoreOS 412.86.202301061548-0
     Part of OpenShift 4.12, RHCOS is a Kubernetes native operating system
     managed by the Machine Config Operator (`clusteroperator/machine-config`).
   
   WARNING: Direct SSH access to machines is not recommended; instead,
   make configuration changes via `machineconfig` objects:
     https://docs.openshift.com/container-platform/4.12/architecture/architecture-rhcos.html
   
   ---
   Last login: Mon Jan 16 14:57:52 2023 from 203.0.113.11
   [core@compute-0 ~]$

To achieve this, we need to deploy our ssh keys to all machines, and then
specify all necessary ssh options (including user names) in local
``~/.ssh/config``. See the following minimal example::

    host *ceph.example.com
    user root
    IdentityFile /home/foobar/.ssh/id_rsa.example

    host *.example.com
    user core
    IdentityFile /home/foobar/.ssh/id_rsa.example

This way ``ocp-network-split`` doesn't need to care about any ssh option.

.. _mc_cli_setup:

Setting up network split
------------------------

Based on ``zone.ini`` file we created during :ref:`zone_config_example`, we
will generate both ``MachineConfig`` yaml file and an env file with zone
configuration (for ocp network split firewall scripts) using
``ocp-network-split-mutisetup`` command line tool. Option ``--mc`` specifies
desired name of the yaml file, while ``--env`` specifies
name of the file where the env file will be saved.

.. code-block:: console

   $ ocp-network-split-multisetup --mc example.mc.yaml --env example.env zone.ini

Now we can deploy the ``MachineConfig`` on all OpenShift clusters as
``kubeadmin`` user via ``oc create``:

.. code-block:: console

   $ oc create -f example.mc.yaml
   machineconfig.machineconfiguration.openshift.io/95-master-network-zone-config created
   machineconfig.machineconfiguration.openshift.io/99-master-network-split created
   machineconfig.machineconfiguration.openshift.io/95-worker-network-zone-config created
   machineconfig.machineconfiguration.openshift.io/99-worker-network-split created

This will instruct `Machine Config Operator`_ to deploy our scripts on all
nodes, updating (and rebooting) one worker and one master node in parallel:

.. code-block:: console

   $ oc get machineconfigpool
   NAME     CONFIG                                             UPDATED   UPDATING   DEGRADED   MACHINECOUNT   READYMACHINECOUNT   UPDATEDMACHINECOUNT   DEGRADEDMACHINECOUNT   AGE
   master   rendered-master-a6b09525d752c5c8771cc0e423acb313   False     True       False      3              1                   1                     0                      4h48m
   worker   rendered-worker-5bec341d2088c2cec8be7b024f9f7a05   False     True       False      3              1                   1                     0                      4h48m

So while we wait for both master and worker machine config pools to reach
``UPDATED`` condition again on all our OpenShift clusters, we can deploy the
same set of scripts on the nodes which are not part of any OpenShift cluster
via ansible plabyook ``multisetup-netsplit.yml``. In our case, this means on
all Ceph nodes, so we will reuse the ceph inventory file. Note that we need to
pass the filename of the env file (which was generated in previous step via
``ocp-network-split-multisetup``) using ``--extra-vars`` option:

.. code-block:: console

   $ ansible-playbook -i ceph.hosts --extra-vars 'env_file=example.env' multisetup-netsplit.yml

When both ansible playbook run and machine config update are finished, we can
go on and schedule network splits as explained in :ref:`mc_split_schedule`.

Introducing additional network latency
--------------------------------------

If we need to configure additional artificial network latency between nodes
from different cluster zones, we can specify the desired one way latency in
milliseconds via ``--latency`` option of ``ocp-network-split-mutisetup``
command line tool. The total RTT latency value will reach roughly 2 times the
value we specify this way.

When we know that we need both network split support and additional latency,
it's a good idea to deploy both at the same time to avoid extra MCO driven
reboots of OpenShift nodes.

So for example to set 10 ms RTT artificial latency and deploy network split
support, we will need to go through section :ref:`mc_cli_setup` above, adding
option ``--latency 5`` for ``ocp-network-split-mutisetup`` tool and then in the
end, run another playbook ``multisetup-latency.yml`` where we need to
specify the same latency value again:

.. code-block:: console

   $ ansible-playbook -i ceph.hosts --extra-vars 'latency=5' multisetup-latency.yml

While it's possible to deploy additional latency without netsplit support, this
use case is not actually tested much.

.. _mc_split_schedule:

Scheduling network split
========================

Let's schedule 5 minute long network split ``ab`` (cutting connection between
zones ``a`` and ``b``) at given moment. Note that in *multi cluster* mode, we
need to pass zone config file (created during :ref:`zone_config_example`) via
``--zonefile`` option:

.. code-block:: console

    $ ocp-network-split-sched ab --zonefile zone.ini -t 2023-01-16T19:50 --split-len 5

When the time details are omitted, the sched script will just list net split
timers for given split configuration on all nodes. In the following example,
we can see one split scheduled in about 1.5 minute:

.. code-block:: console

    $ ocp-network-split-sched ab --zonefine zone.ini | head -8
    arbiter.ceph.example.com
    NEXT                         LEFT          LAST PASSED UNIT                                    ACTIVATES
    Tue 2023-01-17 00:20:00 IST  1min 33s left n/a  n/a    network-split-ab-setup@1673895000.timer network-split@ab.service
    
    osd-2.ceph.example.com
    NEXT                         LEFT          LAST PASSED UNIT                                    ACTIVATES
    Tue 2023-01-17 00:20:00 IST  1min 31s left n/a  n/a    network-split-ab-setup@1673895000.timer network-split@ab.service

You can schedule multiple splits in advance, or wait for one network split to
end before going on with another one.


.. _`fully qualified domain name`: https://manpages.debian.org/bullseye/hostname/hostname.1.en.html#THE_FQDN
.. _`Machine Config Operator`: https://docs.openshift.com/container-platform/4.11/post_installation_configuration/machine-configuration-tasks.html#understanding-the-machine-config-operator
