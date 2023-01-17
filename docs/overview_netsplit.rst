.. _overview_netsplit:

Overview of the network split approach
======================================

A quick overview of what and how opc-network-split does to block network
traffic between cluster zones.

Network split firewall script
-----------------------------

Traffic from zone ``a`` to zone ``b`` is blocked by inserting ``DROP`` rules
for each machine of zone ``b`` into ``INPUT`` and ``OUTPUT`` chains of default
``iptables`` table on all machines of zone ``a`` via ``iptables`` tool.

This is implemented via ``network-split.sh`` script, which consumes zone
configuration via ``ZONE_A``, ``ZONE_B`` and ``ZONE_C`` env variables, detects
zone it is running within and applies firewall changes based on the split
configuration which it received from the command line.

Split configuration specifies list of zone tuples, and the network split is
made for traffic between each zone tuple. For example:

- ``ab`` means that traffic between zone ``a`` and ``b`` will be dropped in
  both directions (via changes in firewall configuration of zone ``a``)
- ``ab-bc`` means that communication in both directions is blocked between
  zone ``a`` and zone ``b``, and also between zone ``b`` and zone ``c``

One can see what changes will be made via ``-d`` option:

.. code-block:: console

    $ export ZONE_A="198.51.100.27"
    $ export ZONE_B="198.51.100.175 198.51.100.180 198.51.100.188 198.51.100.198"
    $ export ZONE_C="198.51.100.115 198.51.100.192 198.51.100.174 198.51.100.208"
    $ ./network-split.sh -d setup ab-ac
    ZONE_A="198.51.100.27"
    ZONE_B="198.51.100.175 198.51.100.180 198.51.100.188 198.51.100.198"
    ZONE_C="198.51.100.115 198.51.100.192 198.51.100.174 198.51.100.208"
    current zone: ZONE_A
    ab: ZONE_B will be blocked from ZONE_A
    iptables -A INPUT -s 198.51.100.175 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.175 -j DROP -v
    iptables -A INPUT -s 198.51.100.180 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.180 -j DROP -v
    iptables -A INPUT -s 198.51.100.188 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.188 -j DROP -v
    iptables -A INPUT -s 198.51.100.198 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.198 -j DROP -v
    ac: ZONE_C will be blocked from ZONE_A
    iptables -A INPUT -s 198.51.100.115 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.115 -j DROP -v
    iptables -A INPUT -s 198.51.100.192 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.192 -j DROP -v
    iptables -A INPUT -s 198.51.100.174 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.174 -j DROP -v
    iptables -A INPUT -s 198.51.100.208 -j DROP -v
    iptables -A OUTPUT -d 198.51.100.208 -j DROP -v

Systemd Units
-------------

The firewall script is not used directly, but through *stoppable oneshot
service* template ``network-split@.service``. To use it, we need to chose
particular network split configuration, eg. ``ab-bc``,  and then form so
called "instantiated" service name ``network-split@ab-ac.service``.
When such "instantiated" service is started, firewall changes to achieve
selected network split are applied and since then systemd is tracking this
service as started. Stopping the service reverts the firewall changes back,
removing the network split. The logs from the firewall script available via
journald as expected.

Example of starting network split for ``ab-bc`` and checking it's status:

.. code-block:: console

    # systemctl start  network-split@ab-bc
    # systemctl status network-split@ab-bc
    ● network-split@ab-bc.service - Firewall configuration for a network split
       Loaded: loaded (/etc/systemd/system/network-split@.service; disabled; vendor preset: disabled)
       Active: active (exited) since Sat 2021-03-06 00:23:18 UTC; 4min 49s ago
      Process: 16380 ExecStart=/usr/bin/bash -c /etc/network-split.sh setup ab-bc (code=exited, status=0/SUCCESS)
     Main PID: 16380 (code=exited, status=0/SUCCESS)
          CPU: 8ms

    Mar 06 00:23:18 compute-5 systemd[1]: Starting Firewall configuration for a network split...
    Mar 06 00:23:18 compute-5 bash[16380]: ZONE_A="198.51.100.27"
    Mar 06 00:23:18 compute-5 bash[16380]: ZONE_B="198.51.100.175 198.51.100.180 198.51.100.188 198.51.100.198"
    Mar 06 00:23:18 compute-5 bash[16380]: ZONE_C="198.51.100.115 198.51.100.192 198.51.100.174 198.51.100.208"
    Mar 06 00:23:18 compute-5 bash[16380]: current zone: ZONE_C
    Mar 06 00:23:18 compute-5 bash[16380]: ab: ZONE_B will be blocked from ZONE_A
    Mar 06 00:23:18 compute-5 bash[16380]: bc: ZONE_C will be blocked from ZONE_B
    Mar 06 00:23:18 compute-5 systemd[1]: Started Firewall configuration for a network split.

This would work well on a single node, but in our case we need to apply this
on multiple machines at the same time. Moreover we also need to make sure that
the service is stopped after some time, reverting the network split issue.
For this reason, we don't start the network split service directly, but via
systemd timers, which allows us to schedule start and stop of the network split
service in advance at the same time on all nodes of the cluster.

For each network split configuration we have in stretch cluster test plan,
there is one setup timer template which starts the service at given time:

- ``network-split-ab-ac-setup@.timer``
- ``network-split-ab-setup@.timer``
- ``network-split-ab-bc-setup@.timer``
- ``network-split-bc-setup@.timer``

And then single teardown timer template ``network-split-teardown@.timer``,
which is used to schedule stop of any of the network split services to revert
the firewall changes back into original state.

Parameter of these timer templates is a unix epoch timestamp of the time when
we intend to start or stop the network split, eg.
``network-split-teardown@1614990498.timer``.

This is how a network split configuration is applied during test setup,
and restored during test teardown.

References:

- `systemd.service(5) <https://www.freedesktop.org/software/systemd/man/systemd.service.html>`_
  (for details about service templates or example of stoppable oneshot service)
- `systemd.timer(5) <https://www.freedesktop.org/software/systemd/man/systemd.timer.html>`_

MachineConfig
-------------

For the approach explained above to work, we need to deploy firewall script,
file with ``ZONE_{A,B,C}`` environment variables and systemd service and timer
units. We achieve this via MachineConfig, which allows us to deploy files in
``/etc`` directory and system units on all nodes of both ``master`` and
``worker`` MachineConfigPools.

Using openshift interface has an advantage of better visibility of such
changes, which can be easily inspected via machine config operator (MCO) API.
Downside of this approach is that MCO is going to drain and reboot every node
one by one, which increases time necessary to deploy the configuration.

For this reason, we use MachineConfig only to deploy the script and unit files,
while scheduling of the timers to setup and teardown a network split is done
via direct connection (using ssh or oc debug) to each node.

References:

- `How does Machine Config Pool work? <https://www.redhat.com/en/blog/openshift-container-platform-4-how-does-machine-config-pool-work>`_
- `Post-installation machine configuration tasks <https://docs.openshift.com/container-platform/4.6/post_installation_configuration/machine-configuration-tasks.html#using-machineconfigs-to-change-machines>`_
- `machine-config-operator docs <https://github.com/openshift/machine-config-operator/tree/master/docs>`_
- `Ignition Configuration Specification v3.1.0 <https://coreos.github.io/ignition/configuration-v3_1/>`_

Ansible Playbook
----------------

In *multi cluster* mode, ansible playbook ``multisetup-netsplit.yml`` is used
to deploy the scripts and systemd unit files mentioned above
to RHEL machines which are part of a zone but outside of any OpenShift cluster.

If *multi cluster* zones contain both OpenShift nodes and classic RHEL
machines outside of any OpenShift cluster, one needs to use both MachineConfig
and ansible playbook setup so that the network split scripts are deployed
on all nodes of all zones.
