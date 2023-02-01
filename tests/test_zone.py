# -*- coding: utf8 -*-

import argparse
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
    zone_b = ["198.51.100.175", "198.51.100.180", "198.51.100.188"]
    zone_c = ["198.51.100.115", "198.51.100.192", "198.51.100.174"]
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
    zc.add_node("a", "198.51.100.11")
    zc.add_nodes("b", ["198.51.100.175", "198.51.100.180", "198.51.100.188"])
    zc.add_nodes("c", ["198.51.100.115", "198.51.100.192", "198.51.100.174"])
    expected_content = textwrap.dedent(
        """\
        ZONE_A="198.51.100.11"
        ZONE_B="198.51.100.175 198.51.100.180 198.51.100.188"
        ZONE_C="198.51.100.115 198.51.100.174 198.51.100.192"
    """
    )
    assert zc.get_env_file() == expected_content


def test_zonelatspec_null():
    zls = zone.ZoneLatSpec()
    assert zls.get_cli_args() == ""


def test_zonelatspec_invalid():
    with pytest.raises(ValueError):
        zone.ZoneLatSpec(ab=7,ah=11)
    with pytest.raises(ValueError):
        zone.ZoneLatSpec(ac=7,abc=5)


def test_zonelatspec_invalid_nan():
    with pytest.raises(ValueError):
        zone.ZoneLatSpec(ab=101.1)
    with pytest.raises(ValueError):
        zone.ZoneLatSpec(ab='foo')


def test_zonelatspec_simple():
    zls = zone.ZoneLatSpec(ab=10)
    assert zls.get_cli_args() == "-l ab=10"


def test_zonelatspec_canonical():
    zls1 = zone.ZoneLatSpec(ab=101)
    zls2 = zone.ZoneLatSpec(ba=101)
    assert zls1.get_cli_args() == zls2.get_cli_args()


def test_zonelatspec_valid_duplicates():
    zls = zone.ZoneLatSpec(ab=101,ba=101)
    assert zls.get_cli_args() == "-l ab=101"


def test_zonelatspec_complex():
    zls = zone.ZoneLatSpec(ab=11,ac=7,ax=100,bx=100)
    assert zls.get_cli_args() == "-l ab=11 -l ac=7 -l ax=100 -l bx=100"


def test_zonelatspec_from_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", nargs="*", type=str)
    args = parser.parse_args('-l ab=11 ac=7'.split())
    zls = zone.ZoneLatSpec()
    zls.load_arguments(args.l)
    assert zls.get_cli_args() == "-l ab=11 -l ac=7"
