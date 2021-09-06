# -*- coding: utf8 -*-

import os
import textwrap

import pytest

from ocpnetsplit import machineconfig


def test_create_file_dict_emptyname():
    """
    ValueError is raised when basename is empty.
    """
    with pytest.raises(ValueError):
        machineconfig.create_file_dict(basename="", content="foobar")


def test_create_file_dict_relativedir():
    """
    ValueError is raised when target_path is relative.
    """
    with pytest.raises(ValueError):
        machineconfig.create_file_dict(
            basename="foo", content="bar", target_dir="etc/ssh.d")


def test_create_file_dict_wrongdir():
    """
    ValueError is raised when target_path is outside of MCO managed dirs.
    """
    with pytest.raises(ValueError):
        machineconfig.create_file_dict(
            basename="foo", content="bar", target_dir="/tmp")
    with pytest.raises(ValueError):
        machineconfig.create_file_dict(
            basename="foo", content="bar", target_dir="/etc/../opt/")


def test_create_unit_dict_emptyname():
    """
    ValueError is raised when unit name is empty.
    """
    with pytest.raises(ValueError):
        machineconfig.create_unit_dict(name="", content="foobar")


def test_create_file_dict_simplecontent():
    """
    Check that create_file_dict() fills out the dictionary properly.
    """
    fd = machineconfig.create_file_dict("test.file", "hello world")
    assert fd["path"] == "/etc/test.file"
    expected_source = "data:text/plain;charset=utf-8;base64,aGVsbG8gd29ybGQ="
    assert fd["contents"]["source"] == expected_source


def test_create_file_dict_simplecontent_targetdir():
    """
    Check that create_file_dict() fills out the dictionary properly.
    """
    fd = machineconfig.create_file_dict("test.conf", "hello world", "/etc/ssh")
    assert fd["path"] == "/etc/ssh/test.conf"
    expected_source = "data:text/plain;charset=utf-8;base64,aGVsbG8gd29ybGQ="
    assert fd["contents"]["source"] == expected_source


def test_create_unit_dict_simplecontent():
    """
    Check that create_unit_dict() fills out the dictionary properly.
    """
    ud = machineconfig.create_unit_dict("test-unit", "content")
    assert ud["name"] == "test-unit"
    assert ud["contents"] == "content"
    assert ud["enabled"] is True


def test_create_split_mc_dict_metadata():
    """
    Check that create_split_mc_dict() fills up MachineConfig metadata properly.
    """
    mcd = machineconfig.create_split_mc_dict("worker")
    assert mcd["kind"] == "MachineConfig"
    assert mcd["metadata"]["name"] == "99-worker-network-split"
    role_label = "machineconfiguration.openshift.io/role"
    assert mcd["metadata"]["labels"][role_label] == "worker"


def test_create_zone_mc_dict_content():
    """
    Create production like machineconfig dictionary and check the resulting
    MachineConfig dictionary.
    """
    zone_env = textwrap.dedent(
        """
        ZONE_A="10.1.161.27"
        ZONE_B="10.1.160.175 10.1.160.180 10.1.160.188 10.1.160.198"
        ZONE_C="10.1.161.115 10.1.160.192 10.1.160.174 10.1.160.208"
    """
    )
    mcd = machineconfig.create_zone_mc_dict("worker", zone_env)

    # there is a network zone env file
    assert len(mcd["spec"]["config"]["storage"]["files"]) == 1
    assert mcd["spec"]["config"]["storage"]["files"][0]["path"] == "/etc/network-split.env"

    # there is no systemd section in the machineconfig
    assert "systemd" not in mcd["spec"]["config"]


def test_create_split_mc_dict_content():
    """
    Create production like machineconfig dictionary and check the resulting
    MachineConfig dictionary.
    """
    mcd = machineconfig.create_split_mc_dict("worker")

    # there is a network split script
    assert len(mcd["spec"]["config"]["storage"]["files"]) == 1
    assert mcd["spec"]["config"]["storage"]["files"][0]["path"] == "/etc/network-split.sh"

    # there is systemd unit attached for each systemd unit file
    units = set(un["name"] for un in mcd["spec"]["config"]["systemd"]["units"])
    unit_files = set(os.listdir(os.path.join(machineconfig.HERE, "systemd")))
    assert units == unit_files


def test_create_latency_mc_dict_content():
    """
    Create production like machineconfig dictionary and check the resulting
    MachineConfig dictionary.
    """
    mcd = machineconfig.create_latency_mc_dict("worker", latency=10)

    # there is a network split script
    file_list = mcd["spec"]["config"]["storage"]["files"]
    assert len(file_list) == 1
    assert file_list[0]["path"] == "/etc/modules-load.d/sch_netem.conf"
