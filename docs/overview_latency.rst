.. _overview_latency:

Additional latency setup overview
=================================

A quick overview of what opc-network-split does to introduce latency among
nodes of different cluster zones.

Network latency script
----------------------

Latency between nodes from different zones is introduced by setting up `netem
qdisc`_ traffic queue on each node of the cluster so that packets targeted to
nodes in other zones flows through a netem qdisc which introduces given delay.
Total RTT (round-trip time) added this way equals two times this delay.

This setup is implemented in ``network-latency.sh`` script, which consumes
requested delay latency in miliseconds (half of RTT) as a command line
argument. Zone configuration and detection are handled in the same way as in
``network-latency.sh`` script (in fact, both scripts share this part).

.. _`netem qdisc`: https://wiki.linuxfoundation.org/networking/netem

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
   current zone: ZONE_A
   tc qdisc del dev wlp61s0 root
   tc qdisc add dev wlp61s0 root handle 1: prio
   tc qdisc add dev wlp61s0 parent 1:1 handle 2: netem delay 15ms
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.109/32 flowid 3:1
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.96/32 flowid 3:1
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.97/32 flowid 3:1
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.99/32 flowid 3:1
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.103/32 flowid 3:1
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.84/32 flowid 3:1
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.87/32 flowid 3:1
   tc filter add dev wlp61s0 parent 1: protocol ip prio 2 u32 match ip dst 198.51.100.98/32 flowid 3:1

The script doesn't implement teardown to revert into the original traffic queue
configuration.

Systemd Unit
------------

The latency setup script is started during boot of a node via systemd service
``network-latency``. Checking status of this service on given node reveals
whether and how was the latency reconfigured on a given node.

MachineConfig
-------------

In a *single cluster* mode,
a MachineConfig resource is used to deploy both the script and systemd service
unit file on each node of OpenShift cluster.

Using openshift interface has an advantage of better visibility of such
changes, which can be easily inspected via machine config operator (MCO) API.
Moreover the latency setup would survive a node reboot (assuming ip address of
the node don't change).

Ansible Playbook
----------------

In *multi cluster* mode ansible playbook ``multisetup-latency.yml`` is used
to deploy the latency script and systemd service to RHEL machines which are
part of a zone but outside of any OpenShift cluster.

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
