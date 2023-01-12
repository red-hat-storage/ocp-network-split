.. _assumptions:

Assumptions and limitations
===========================

We assume that all nodes are using static IPv4 addresses.

A node can be member of only one zone.

Single cluster mode
-------------------

The `OpenShift 4`_ cluster has 3 `k8s zones`_.

There is no limitation on actual zone names (values of
``topology.kubernetes.io/zone`` label key).

We assume that there are only ``master`` and ``worker`` MachineConfigPools_
(which is the default state of OCP cluster). If you have created another
machine config pool such as ``infra``, the network split configuration won't
be able to change firewall rules on nodes in this additional pool.

You have ``oc`` command installed and you are logged in as ``kubeadmin`` user.

No new cluster nodes joins the cluster later.

Multi cluster cluster mode
--------------------------

A zone in multi cluster mode can contain both OpenShift 4 (RHEL CoreOS) and
RHEL machines, and it's not related to `k8s zones`_ which may be defined in any
of OpenShift clusters.

In theory, one can define a zone so that it contains only part of the cluster,
but in the intended use case there are one or more clusters per zone, with
an optional set of additional machines in each zone.

No new nodes joins neither the zones or clusters which are part of the zones.

You have ssh access configured for all nodes of the multi cluster environment,
so that one can connect to every node via sheer ``ssh fqdn`` command, where
``fqdn`` is `fully qualified domain name`_ of the node. This requires ssh client
configuration and ssh keys.

Network split specific assumptions
----------------------------------

While Linux kernel of RHEL CoreOS (RHCOS) uses ``nftables`` internally, the
``iptables`` cli tool which uses ``nftables`` backed is preinstalled on RHCOS
hosts of OCP 4 clusters. The firewall script thus assumes that ``iptables`` cli
tool is available on the nodes of the cluster.

All nodes keep it's time synchronized via ntp. For OpenShift 4 cluster, see
`configuring chrony time service`_.

Latency specific assumptions
----------------------------

Linux traffic control tool ``iproute-tc`` and ``kernel-modules-extra`` package
(which provides ``sch_netem`` kernel module) are preinstalled on all RHCOS
hosts of the OCP cluster.

All cluster nodes are interconnected on a single network.

.. _`configuring chrony time service`: https://docs.openshift.com/container-platform/latest/post_installation_configuration/machine-configuration-tasks.html#installation-special-config-chrony_post-install-machine-configuration-tasks
.. _`k8s zones`: https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
.. _MachineConfigPools: https://www.redhat.com/en/blog/openshift-container-platform-4-how-does-machine-config-pool-work
.. _`fully qualified domain name`: https://manpages.debian.org/bullseye/hostname/hostname.1.en.html#THE_FQDN
.. _`k8s zones`: https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
.. _`OpenShift 4`: https://docs.openshift.com/container-platform/latest/welcome/index.html
