# -*- coding: utf8 -*-

# Copyright 2021 Martin Bukatovič <mbukatov@redhat.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module generates ``MachineConfig`` to deploy network-split systemd units,
which implements the network split functionality.

References:

* `MachineConfigDaemon`_
* `Ignition Configuration Specification v3.1.0`_

.. _`MachineConfigDaemon`: https://github.com/openshift/machine-config-operator/blob/master/docs/MachineConfigDaemon.md
.. _`Ignition Configuration Specification v3.1.0`: https://coreos.github.io/ignition/configuration-v3_1/
.. moduleauthor:: Martin Bukatovič
"""


import base64
import os
import os.path
import textwrap

import yaml


HERE = os.path.abspath(os.path.dirname(__file__))
SYSTEMD_DIR = os.path.join(HERE, "systemd")


MACHINECONFIG_SKELL = textwrap.dedent(
    """
    apiVersion: machineconfiguration.openshift.io/v1
    kind: MachineConfig
    metadata:
      name: TODO
      labels:
        machineconfiguration.openshift.io/role: TODO
    spec:
      config:
        ignition:
          version: 3.1.0
        storage:
          files: []
        systemd:
          units: []
"""
)


FILE_SKEL = textwrap.dedent(
    """
    path: TODO
    contents:
      source: TODO
    mode: 0444
    user:
      name: root
    group:
      name: root
"""
)


UNIT_SKEL = textwrap.dedent(
    """
    name: TODO
    enabled: true
    contents: TODO
"""
)


def create_file_dict(basename, content, target_dir="/etc"):
    """
    Create Ignition config spec for given file basename and content, to be used
    in a ``MachineConfig`` spec. File will be placed given ``target_dir``, but
    note that MCO can only change files in ``/etc`` and ``/var`` directories.

    Args:
        basename (str): basename of the file
        content (str): content of the file
        target_dir (str): absolute path where to place the file, eg. ``/etc``

    Returns:
        dict: Ignition storage file config spec

    Raises:
        ValueError: if given ``basename`` or ``target_dir`` is invalid
    """
    if basename is None or len(basename) == 0:
        raise ValueError("basename should not be empty")
    file_dict = yaml.safe_load(FILE_SKEL)
    # MCO can deploy files to /etc and /var directories only
    if not target_dir.startswith("/"):
        raise ValueError(
            f"target_dir '{target_dir}' shouldn't be relative, use abs. path")
    target_dir = os.path.normpath(target_dir)
    if not (target_dir.startswith("/etc") or target_dir.startswith("/var")):
        raise ValueError(
            f"target_dir '{target_dir}' should not be outside of /etc or /var")
    file_dict["path"] = os.path.join(target_dir, basename)
    # Ignition requires content of storage.file entry to be provided via an
    # URL and accepts rfc2397 "data" URL scheme.
    source_prefix = "data:text/plain;charset=utf-8;base64,"
    content_base64 = base64.b64encode(content.encode()).decode()
    file_dict["contents"]["source"] = source_prefix + content_base64
    return file_dict


def create_unit_dict(name, content):
    """
    Create Ignition config spec for given systemd unit name and content, to be
    used in a ``MachineConfig`` spec.

    Args:
        name (str): name of systemd unit
        content (str): content of the file

    Returns:
        dict: Ignition systemd unit config spec
    """
    if name is None or len(name) == 0:
        raise ValueError("name of the unit should not be empty")
    unit_dict = yaml.safe_load(UNIT_SKEL)
    unit_dict["name"] = name
    unit_dict["contents"] = content
    return unit_dict


def get_new_mc(role, name_suffix, priority=99):
    """
    Initialize new (almost empty) MachineConfig dict.

    Args:
        role (string): name of ``MachineConfig`` role
        name_suffix (string): suffix of resulting MachineConfig name
    """
    mcd = yaml.safe_load(MACHINECONFIG_SKELL)
    mcd["metadata"]["name"] = str(priority) + "-" + role + "-" + name_suffix
    mcd["metadata"]["labels"]["machineconfiguration.openshift.io/role"] = role
    return mcd


def create_script_dict(script_name):
    """
    Create file dict with given shell script from ocpnetsplit module.

    Args:
        script_name (string): name of the shell script

    Returns:
        dict: Ignition storage file config spec
    """
    with open(os.path.join(HERE, script_name), "r") as script_file:
        script_dict = create_file_dict(script_name, script_file.read())
        # the script needs to be executable
        script_dict["mode"] = 0o544
    return script_dict


def create_systemdunit_dict(unit_filename):
    """
    Create file dict with given systemd unit file from ocpnetsplit module.

    Args:
        unit_filename (string): name of the systemd unit file

    Returns:
        dict: Ignition storage file config spec
    """
    with open(os.path.join(SYSTEMD_DIR, unit_filename), "r") as unit_file:
        unit_dict = create_unit_dict(unit_filename, unit_file.read())
    return unit_dict


def create_zone_mc_dict(role, zone_env):
    """
    Create ``MachineConfig`` dict with network zone config env file.

    Args:
        mcp (string): name of ``MachineConfig`` role (and also
            ``MachineConfigPool``) where the ``MachineConfig`` generated by
            this function should be deployed. Usually ``master`` or ``worker``.
        zone_env (string): content of ``network-split.env`` file with zone
            configuration, as created by
            :py:meth:`ocpnetsplit.zone.ZoneConfig.get_env_file`

    Returns:
        dict: MachineConfig dict
    """
    mcd = get_new_mc(role, "network-zone-config", priority=95)

    # add env file with zone configuration
    env_dict = create_file_dict("network-split.env", zone_env)
    mcd["spec"]["config"]["storage"]["files"].append(env_dict)

    # include zone checking and detection script file
    script_dict = create_script_dict("network-zone.sh")
    mcd["spec"]["config"]["storage"]["files"].append(script_dict)

    # drop systemd section, which is not necessary in this case
    del mcd["spec"]["config"]["systemd"]

    return mcd


def create_split_mc_dict(role):
    """
    Create ``MachineConfig`` dict with network-split systemd units and scripts.

    Args:
        mcp (string): name of ``MachineConfig`` role (and also
            ``MachineConfigPool``) where the ``MachineConfig`` generated by
            this function should be deployed. Usually ``master`` or ``worker``.

    Returns:
        dict: MachineConfig dict
    """
    mcd = get_new_mc(role, "network-split")

    # include firewall script file
    script_dict = create_script_dict("network-split.sh")
    mcd["spec"]["config"]["storage"]["files"].append(script_dict)

    # and include all systemd units from systemd directory
    for unit_filename in os.listdir(SYSTEMD_DIR):
        if not unit_filename.startswith("network-split"):
            continue
        unit_dict = create_systemdunit_dict(unit_filename)
        mcd["spec"]["config"]["systemd"]["units"].append(unit_dict)

    return mcd


def create_latency_mc_dict(role, latency):
    """
    Create ``MachineConfig`` dict with latency systemd units and scripts.

    Args:
        mcp (string): name of ``MachineConfig`` role (and also
            ``MachineConfigPool``) where the ``MachineConfig`` generated by
            this function should be deployed. Usually ``master`` or ``worker``.
        latency (int): zone latency created via Linux Traffic Control in ms

    Returns:
        dict: MachineConfig dict
    """
    mcd = get_new_mc(role, "network-latency")

    # include a config file to modprobe sch_netem kernel module
    file_dict = create_file_dict(
            "sch_netem.conf",
            "sch_netem",
            target_dir="/etc/modules-load.d")
    mcd["spec"]["config"]["storage"]["files"].append(file_dict)

    # include latency script file
    script_dict = create_script_dict("network-latency.sh")
    mcd["spec"]["config"]["storage"]["files"].append(script_dict)

    # include systemd unit service for the latency script
    unit_dict = create_systemdunit_dict("network-latency.service")
    # hardcode the given latency value into systemd service unit
    unit_dict["contents"] = unit_dict["contents"].replace(
        "{{ latency }}", str(latency))
    mcd["spec"]["config"]["systemd"]["units"].append(unit_dict)

    return mcd
