=========================
 OCP Network Split Setup
=========================

This simple project provides functionality to block (and unblock) network
traffic between `OpenShift 4`_ cluster zones and to optionally create
additional network latency among all zones. It's intended to be used for
*testing purposes* only.

This tool can be used either in *single cluster* or *multi cluster* mode.
In a *single cluster* mode, the tool works on top of `k8s zones`_ defined in a
particular `OpenShift 4`_ cluster. While in *multi cluster* mode, zones are
defined in a custom config file so that one zone can contain multiple OpenShift
clusters or even other nodes.

Zone isolation is implemented by updating firewall rules on all nodes, while
latency is introduced by setting up netem qdisc traffic queue on all nodes.

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
   usage_multicluster.rst
   modules.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _`k8s zones`: https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
.. _`OpenShift 4`: https://docs.openshift.com/container-platform/latest/welcome/index.html
