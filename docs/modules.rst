.. _python_usage:

============
 Python API
============

To use ocp-network-split in your python test script, see functions in module
:py:mod:`ocpnetsplit.main` which provides public API and implementation
of the command line tools referenced in the previous section.

Example
=======

Quick high level overview of API usage for *single cluster* mode:

- Generate list of dictionaries representing content of ``MachineConfig`` yaml,
  (which contains network split script and unit files) using
  :py:func:`ocpnetsplit.main.get_zone_config` and
  :py:func:`ocpnetsplit.main.get_networksplit_mc_spec`.
- Deploy the ``MachineConfig`` generated in the previous step and wait for the
  configuration to be applied on all nodes. This needs to be done only once.
- Pick desired network split configuration from
  :py:const:`ocpnetsplit.zone.NETWORK_SPLITS`.
- Schedule selected network split disruption via
  :py:func:`ocpnetsplit.main.schedule_split`, this will define 2 timers
  on each node, one to start the disruption and another one to stop it.
- Wait for the 1st timer to trigger setup of the network split.
- Wait for the 2nd timer to trigger teardown, restoring the network
  configuration back.
- Optionally schedule another network split again.

API Reference
=============

.. toctree::
   :maxdepth: 4

   ocpnetsplit
