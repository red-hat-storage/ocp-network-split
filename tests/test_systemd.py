# -*- coding: utf8 -*-

import os
import configparser

import pytest


import ocpnetsplit
from ocpnetsplit.zone import NETWORK_SPLITS


PROJECT_DIR = os.path.abspath(os.path.dirname(ocpnetsplit.__file__))
SYSTEMD_DIR = os.path.join(PROJECT_DIR, "systemd")


@pytest.mark.parametrize("unit_filename", os.listdir(SYSTEMD_DIR))
def test_unit_ini_validation(unit_filename):
    """
    Check that included systemd unit files are valid ini files and  contains
    Unit section. Moreover we also check that there are no other files in the
    systemd directory.
    """
    config = configparser.ConfigParser()
    config.read(os.path.join(SYSTEMD_DIR, unit_filename))
    assert "Unit" in config.sections()


def test_timer_for_each_network_split():
    """
    Check that there is a timer unit for each network split configuration.
    """
    timers = [file for file in os.listdir(SYSTEMD_DIR) if file.endswith("setup@.timer")]
    splits_without_timer = []
    for split in NETWORK_SPLITS:
        split_unit = f"network-split-{split}-setup@.timer"
        if split_unit not in timers:
            splits_without_timer.append(split)
    assert splits_without_timer == []
    assert len(timers) == len(NETWORK_SPLITS)


def test_teardown_service():
    """
    Check that the teardown service conflicts with all setup services. This is
    necessary for the teardown service to actually stop the split.
    """
    config = configparser.ConfigParser()
    config.read(os.path.join(SYSTEMD_DIR, "network-split-teardown.service"))
    for split in NETWORK_SPLITS:
        split_service = f"network-split@{split}.service"
        assert split_service in config['Unit']['Conflicts']
