=========================
 OCP Network Split Setup
=========================

This simple project provides functionality to block (and unblock) network
traffic between `k8s zones`_ of an `OpenShift 4`_ cluster and to optionally
create additional network latency among all zones of the cluster. It's intended
to be used for *testing purposes* only.

Zone isolation is implemented by updating firewall rules on all RHEL CoreOS
nodes of the cluster, while latency is introduced by setting up netem qdisc
traffic queue on all nodes.

This is useful when you need to separate network between given zones, without
affecting other traffic and with no assumptions about networking configuration
of the platform the cluster is deployed on (under normal conditions, network
separation like this could be done by tweaking network components between
zones).

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   assumptions.rst
   overview_netsplit.rst
   overview_latency.rst
   usage.rst
   modules.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _`k8s zones`: https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
.. _`k8s label`: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/
.. _`OpenShift 4`: https://docs.openshift.com/container-platform/4.8/welcome/index.html
