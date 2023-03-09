.. _overview_latency:

Additional latency approach
===========================

A quick overview of what ocp-network-split does to introduce latency among
nodes of different cluster zones.

Network latency script
----------------------

Latency between nodes from different zones is introduced by setting up `netem
qdisc`_ egress `traffic queue`_ on each node of the cluster so that packets
targeted to nodes in other zones flows through a netem qdisc which introduces
given delay. This means that for latency to be introduced for incoming packets
as well, it's necessary to setup netem introduced latency on all nodes of the
cluster(s) and the total RTT (round-trip time) added this way equals two times
the specified delay.

This setup is implemented in ``network-latency.sh`` script, which consumes
requested delay latency in miliseconds (half of RTT) as a command line
argument. Zone configuration and detection are handled in the same way as in
``network-latency.sh`` script (in fact, both scripts share this part).

One can see what changes will be introduced via ``-d`` option, which
makes the script report what it would do instead of performing the setup:

.. code:: console

   $ export ZONE_A="198.51.100.199"
   $ export ZONE_B="198.51.100.109 198.51.100.96 198.51.100.97 198.51.100.99"
   $ export ZONE_C="198.51.100.103 198.51.100.84 198.51.100.87 198.51.100.98"
   $ ./network-latency.sh -d 15
   ZONE_A="198.51.100.199"
   ZONE_B="198.51.100.109 198.51.100.96 198.51.100.97 198.51.100.99"
   ZONE_C="198.51.100.103 198.51.100.84 198.51.100.87 198.51.100.98"
   current zone: ZONE_B
   network interface: ens192
   tc qdisc del dev ens192 root
   tc qdisc add dev ens192 root handle 1: prio bands 4
   tc qdisc add dev ens192 parent 1:4 handle 40: netem delay 15ms
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.199/32 flowid 1:4
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.103/32 flowid 1:4
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.84/32 flowid 1:4
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.87/32 flowid 1:4
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.98/32 flowid 1:4
   tc qdisc show dev ens192
   tc class show dev ens192

It's also possible to specify specific latencies between particular zones, eg.
command ``network-latency.sh -l ab=25 -l ac=35 5`` will setup 25 ms (50ms RTT)
latency between zones ``a`` and ``b``, 35ms between zones ``a`` and ``c``, and
5ms (10ms RTT) between rest of the zones (which in this particular case means
between ``b`` and ``c``).

.. code:: console

   $ ./network-latency.sh -d -l ab=25 -l ac=35 5
   ZONE_A="198.51.100.199"
   ZONE_B="198.51.100.109 198.51.100.96 198.51.100.97 198.51.100.99"
   ZONE_C="198.51.100.103 198.51.100.84 198.51.100.87 198.51.100.98"
   current zone: ZONE_B
   network interface: ens192
   tc qdisc del dev ens192 root
   tc qdisc add dev ens192 root handle 1: prio bands 6
   tc qdisc add dev ens192 parent 1:4 handle 40: netem delay 5ms
   tc qdisc add dev ens192 parent 1:6 handle 60: netem delay 35ms
   tc qdisc add dev ens192 parent 1:5 handle 50: netem delay 25ms
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.199/32 flowid 1:5
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.103/32 flowid 1:4
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.84/32 flowid 1:4
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.87/32 flowid 1:4
   tc filter add dev ens192 parent 1: protocol ip prio 1 u32 match ip dst 198.51.100.98/32 flowid 1:4
   tc qdisc show dev ens192
   tc class show dev ens192

As you can see, the script removes existing root qdisc and creates new traffic
queues filtering packets for particular zones to qdiscs with netem introduced
latency. This is obviously not optimal from production perspective, but it's
a good trade-off for testing purposes.

The script can remove the extra latency via it's teardown command:
``network-latency.sh teardown``.
But note that the script does it by removing the root qdisc relying on the
fact that the default qdisc will be recreated. The script doesn't provide
ability to revert to the original traffic queue configuration applied before
the latency was set (as noted above, the original configuration gets deleted).

See also:

- `Classful Queueing Disciplines`_
- `Classifying packets with filters`_
- Description of `PRIO qdisc`_
- Description of `netem qdisc`_ network delay and loss emulator

.. _`Classful Queueing Disciplines`: https://lartc.org/howto/lartc.qdisc.classful.html
.. _`Classifying packets with filters`: https://lartc.org/howto/lartc.qdisc.filters.html
.. _`netem qdisc`: https://wiki.linuxfoundation.org/networking/netem
.. _`PRIO qdisc`: https://linux.die.net/man/8/tc-prio
.. _`traffic queue`: https://www.coverfire.com/articles/queueing-in-the-linux-network-stack/

Systemd Unit
------------

The latency script described above is not used directly, but via systemd
``network-latency.service`` unit. Starting the service configures the latency,
while stopping the service removes the latency setup (via the teardown
command as described above). This means that checking status of this service on
given node reveals whether the additional latency is currently in effect.
When deployed via MachineConfig or Ansible Playbook as explained below, the
latency service is started during boot.

.. code:: console

   [root@example-0 ~]# systemctl status network-latency
   ● network-latency.service - Linux Traffic Control enforced network latency setup
      Loaded: loaded (/etc/systemd/system/network-latency.service; enabled; vendor preset: disabled)
      Active: active (exited) since Fri 2023-02-03 15:31:54 UTC; 17s ago
     Process: 20864 ExecStop=/usr/bin/bash -c /etc/network-latency.sh teardown (code=exited, status=0/SUCCESS)
     Process: 20882 ExecStart=/usr/bin/bash -c /etc/network-latency.sh -l ab=11 -l ac=7 5 (code=exited, status=0/SUCCESS)
    Main PID: 20882 (code=exited, status=0/SUCCESS)
   
   Feb 03 15:31:54 osd-0 bash[20917]: qdisc netem 60: parent 1:6 limit 1000 delay 11ms
   Feb 03 15:31:54 osd-0 bash[20917]: qdisc netem 40: parent 1:4 limit 1000 delay 5ms
   Feb 03 15:31:54 osd-0 bash[20917]: qdisc netem 50: parent 1:5 limit 1000 delay 7ms
   Feb 03 15:31:54 osd-0 bash[20918]: class prio 1:1 parent 1:
   Feb 03 15:31:54 osd-0 bash[20918]: class prio 1:2 parent 1:
   Feb 03 15:31:54 osd-0 bash[20918]: class prio 1:3 parent 1:
   Feb 03 15:31:54 osd-0 bash[20918]: class prio 1:4 parent 1: leaf 40:
   Feb 03 15:31:54 osd-0 bash[20918]: class prio 1:5 parent 1: leaf 50:
   Feb 03 15:31:54 osd-0 bash[20918]: class prio 1:6 parent 1: leaf 60:
   Feb 03 15:31:54 osd-0 systemd[1]: Started Linux Traffic Control enforced network latency setup.

MachineConfig
-------------

MachineConfig resource is used to deploy both the script and systemd service
unit file on each node of OpenShift cluster.

Using openshift interface has an advantage of better visibility of such
changes, which can be easily inspected via machine config operator (MCO) API.
Moreover the latency setup would survive a node reboot (assuming ip address of
the node don't change).

Both ``ocp-network-split-setup`` (single cluster mode) and
``ocp-network-split-multisetup`` tools which generates MachineConfig resources
can include latency setup there when latency configuration is specified via
``--latency`` and ``--latency-spec`` options.

Example of passing latency values to ``ocp-network-split-multisetup`` tool:

.. code:: console

   $ ocp-network-split-multisetup zone.ini --mc example.mc.yaml --env example.env --latency 5 --latency-spec ab=50 ac=50

Ansible Playbook
----------------

In *multi cluster* mode ansible playbook ``multisetup-latency.yml`` is used
to deploy the latency script and systemd service to RHEL machines which are
part of a zone but outside of any OpenShift cluster. The playbook receives
the latency values via the following variables:

=================== =================================== ======================
Variable name       Meaning                             Example
=================== =================================== ======================
``latency``         default latency between zones       ``5``
``latency_spec``    dictionary with zone spec latency   ``{"ab":"50","ac":"50"}``
=================== =================================== ======================

Example of passing the values via ``--extra-vars``:

.. code:: console

   $ ansible-playbook -i ceph.hosts --extra-vars '{"latency":"5","latency_spec":{"ab":"50","ac":"50"}}' multisetup-latency.yml

If *multi cluster* zones contain both OpenShift nodes and classic RHEL
machines outside of any OpenShift cluster, one needs to use both MachineConfig
and ansible playbook setup so that the latency service is deployed and running
on all nodes of all zones.

Single Cluster Example
----------------------

This example assumes we deployed network latency MachineConfig, and the
OpenShift cluster have already applied the configuration on all it's nodes.

For demonstration purposes, we connect to some cluster node via ``oc
debug`` and check status of ``network-latency`` service there:

.. code:: console

    sh-4.4# systemctl status network-latency
    ● network-latency.service - Linux Traffic Control enforced network latency setup
       Loaded: loaded (/etc/systemd/system/network-latency.service; enabled; vendor preset: disabled)
       Active: inactive (dead) since Tue 2021-09-28 00:32:15 UTC; 4min 59s ago
      Process: 1614 ExecStart=/usr/bin/bash -c /etc/network-latency.sh 106 (code=exited, status=0/SUCCESS)
     Main PID: 1614 (code=exited, status=0/SUCCESS)
          CPU: 46ms

    Sep 28 00:32:15 compute-5 systemd[1]: Starting Linux Traffic Control enforced network latency setup...
    Sep 28 00:32:15 compute-5 bash[1614]: ZONE_A="198.51.100.94"
    Sep 28 00:32:15 compute-5 bash[1614]: ZONE_B="198.51.100.109 198.51.100.96 198.51.100.97 198.51.100.99"
    Sep 28 00:32:15 compute-5 bash[1614]: ZONE_C="198.51.100.103 198.51.100.84 198.51.100.87 198.51.100.98"
    Sep 28 00:32:15 compute-5 bash[1614]: current zone: ZONE_C
    Sep 28 00:32:15 compute-5 bash[1614]: Error: Cannot delete qdisc with handle of zero.
    Sep 28 00:32:15 compute-5 systemd[1]: network-latency.service: Succeeded.
    Sep 28 00:32:15 compute-5 systemd[1]: Started Linux Traffic Control enforced network latency setup.
    Sep 28 00:32:15 compute-5 systemd[1]: network-latency.service: Consumed 46ms CPU time

There we can see that the delay introduced is 106 ms, we see the zone
configuration, detected zone of the node, and that the setup succeeded. Now
when we try to ping some node from zone A or B, we will observe that RTT is
two times the delay, 212 ms:

.. code:: console

    sh-4.4# ping 198.51.100.96
    PING 198.51.100.96 (198.51.100.96) 56(84) bytes of data.
    64 bytes from 198.51.100.96: icmp_seq=1 ttl=64 time=212 ms
    64 bytes from 198.51.100.96: icmp_seq=2 ttl=64 time=212 ms
    64 bytes from 198.51.100.96: icmp_seq=3 ttl=64 time=212 ms
    64 bytes from 198.51.100.96: icmp_seq=4 ttl=64 time=212 ms
    ^C
    --- 198.51.100.96 ping statistics ---
    4 packets transmitted, 4 received, 0% packet loss, time 3004ms
    rtt min/avg/max/mdev = 212.292/212.326/212.347/0.564 ms

But when we try to ping a node from the same zone C, we see that there is no
additional delay:

.. code:: console

    sh-4.4# ping 198.51.100.84
    PING 198.51.100.84 (198.51.100.84) 56(84) bytes of data.
    64 bytes from 198.51.100.84: icmp_seq=1 ttl=64 time=0.086 ms
    64 bytes from 198.51.100.84: icmp_seq=2 ttl=64 time=0.059 ms
    64 bytes from 198.51.100.84: icmp_seq=3 ttl=64 time=0.060 ms
    ^C
    --- 198.51.100.84 ping statistics ---
    3 packets transmitted, 3 received, 0% packet loss, time 2053ms
    rtt min/avg/max/mdev = 0.059/0.068/0.086/0.014 ms

Verifying latency via a testing script
--------------------------------------

To make sure that the latency configuration works as expected, both the
``MachineConfig`` and the Ansible Playbook deploys a simple testing script
``/etc/network-pingtest.sh``
on all machines where the latency scripts are installed.

See an example of the usage from a machine in zone ``b``:

.. code:: console

   # /etc/network-pingtest.sh
   ===============================================================================
   ZONE_A
   ===============================================================================
   PING 198.51.100.43 rtt min/avg/max/mdev = 10.300/10.377/10.510/0.125 ms
   ===============================================================================
   ZONE_B
   ===============================================================================
   PING 198.51.100.131 rtt min/avg/max/mdev = 0.202/0.223/0.243/0.016 ms
   PING 198.51.100.159 rtt min/avg/max/mdev = 0.035/0.041/0.052/0.007 ms
   PING 198.51.100.160 rtt min/avg/max/mdev = 0.172/0.200/0.218/0.026 ms
   ===============================================================================
   ZONE_C
   ===============================================================================
   PING 198.51.100.109 rtt min/avg/max/mdev = 10.213/10.242/10.296/0.122 ms
   PING 198.51.100.140 rtt min/avg/max/mdev = 10.171/10.196/10.214/0.118 ms
   PING 198.51.100.176 rtt min/avg/max/mdev = 10.223/10.254/10.286/0.086 ms
   ===============================================================================
   ZONE_X
   ===============================================================================
