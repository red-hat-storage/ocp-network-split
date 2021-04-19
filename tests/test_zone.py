# -*- coding: utf8 -*-

import textwrap

import pytest

from ocpnetsplit import zone


def test_valid_zone_splits():
    """
    Check that zone splits references valid zones.
    """
    for split_config in zone.NETWORK_SPLITS:
        for split in split_config.split("-"):
            assert len(split) == 2
            assert split[0] in zone.ZONES
            assert split[1] in zone.ZONES


def test_zoneconfig_invalid_zone():
    """
    Check that when invalid zone name is used, add_node raises ValueError.
    """
    zc = zone.ZoneConfig()
    invalid_zone = "d"
    assert invalid_zone not in zone.ZONES
    with pytest.raises(ValueError):
        zc.add_node(invalid_zone, "192.128.0.11")


def test_zoneconfig_add_nodes():
    zc = zone.ZoneConfig()
    zone_b = ["10.1.160.175", "10.1.160.180", "10.1.160.188"]
    zone_c = ["10.1.161.115", "10.1.160.192", "10.1.160.174"]
    zc.add_node("b", zone_b[0])
    zc.add_node("b", zone_b[1])
    zc.add_node("b", zone_b[2])
    zc.add_nodes("c", zone_c)
    assert zc.get_nodes("b") == set(zone_b)
    assert zc.get_nodes("c") == set(zone_c)
    zc.add_node("b", zone_b[0])
    assert zc.get_nodes("b") == set(zone_b)


def test_zoneconfig_env_file():
    zc = zone.ZoneConfig()
    zc.add_node("a", "10.1.161.11")
    zc.add_nodes("b", ["10.1.160.175", "10.1.160.180", "10.1.160.188"])
    zc.add_nodes("c", ["10.1.160.115", "10.1.160.192", "10.1.160.174"])
    expected_content = textwrap.dedent(
        """\
        ZONE_A="10.1.161.11"
        ZONE_B="10.1.160.175 10.1.160.180 10.1.160.188"
        ZONE_C="10.1.160.115 10.1.160.174 10.1.160.192"
    """
    )
    assert zc.get_env_file() == expected_content
