===================
 OCP Network Split
===================

Project ``ocp-network-split`` provides functionality to block (and unblock)
network traffic between `OpenShift 4`_ cluster zones and to optionally create
additional network latency among all zones. It's intended to be used for
*testing purposes* only. The feature can be used either via command line tools
or a python module.

This is useful when you need to separate network between given zones for
*testing purposes*, without affecting other traffic and with no assumptions
about networking configuration of the platform the cluster is deployed on
(under normal conditions, network separation like this could be done by
tweaking network components between zones).

Documentation
-------------

The primary documentation is available at
https://mbukatov.gitlab.io/ocp-network-split

Source files of the documentation are maintained as a `Sphinx
<https://www.sphinx-doc.org/en/master>`_ project in ``docs`` directory.

Source code
-----------

Upstream: https://gitlab.com/mbukatov/ocp-network-split

Mirrors:

- https://github.com/mbukatov/ocp-network-split

License
-------

Copyright 2023 Martin Bukatovič

Distributed under the terms of the `Apache License 2.0`_ license;
you may not use this project except in compliance with the License.

.. _`k8s zones`: https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
.. _`OpenShift 4`: https://docs.openshift.com/container-platform/latest/welcome/index.html
.. _`Apache License 2.0`: http://www.apache.org/licenses/LICENSE-2.0
