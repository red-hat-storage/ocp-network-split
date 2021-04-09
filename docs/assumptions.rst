.. _assumptions:

Assumptions and limitations
===========================

We assume that the cluster has 3 zones.

There is no limitation on actuall zone names (values of
``topology.kubernetes.io/zone`` label key).

While Linux kernel of RHEL CoreOS (RHCOS) uses ``nftables`` internally, the
``iptables`` cli tool which uses ``nftables`` backed is preinstalled on RHCOS
hosts of OCP 4 clusters. The firewall script thus assumes that ``iptables`` cli
tool is available on the nodes of the cluster.

Nodes of openshift cluster keep it's `time synchronized via ntp`_.

We assume that there are only ``master`` and ``worker`` MachineConfigPools
(which is the default state of OCP cluster). If you have created another
machine config pool such as ``infra``, the network split configuration won't
be able to change firewall rules on nodes in this additional pool.

.. _`time synchronized via ntp`: https://docs.openshift.com/container-platform/4.6/post_installation_configuration/machine-configuration-tasks.html#installation-special-config-chrony_post-install-machine-configuration-tasks
