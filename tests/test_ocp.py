# -*- coding: utf8 -*-


import logging
import subprocess

import pytest

from ocpnetsplit import ocp


def test_oc_run_positive():
    ocp.run_oc(["-l", "/bin/sh"], oc_executable="ls")


def test_oc_run_failure():
    with pytest.raises(subprocess.CalledProcessError):
        ocp.run_oc(["-l", "/bin/foo"], oc_executable="ls")


def test_oc_run_timeout():
    with pytest.raises(subprocess.TimeoutExpired):
        ocp.run_oc(["10s"], oc_executable="sleep", timeout=1)


def test_oc_run_positive_output():
    stdout, stderr = ocp.run_oc(["-l", "/bin/sh"], oc_executable="ls")
    # let's check that expected output is returned properly
    assert "/bin/sh" in stdout
    assert "root" in stdout
    assert len(stderr) == 0


def test_oc_run_positive_logging(caplog):
    caplog.set_level(logging.INFO)
    ocp.run_oc(["/bin/sh"], oc_executable="ls")
    assert caplog.records[0].message == "going to execute ['ls', '/bin/sh']"
    assert len(caplog.records) == 1
    # tryting again, with DEBUG log level
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    ocp.run_oc(["/bin/sh"], oc_executable="ls")
    assert len(caplog.records) == 4
    assert '/bin/sh' in caplog.records[1].message
    assert caplog.records[1].message.startswith('oc stdout:')
    assert caplog.records[2].message == ("oc stderr: b''")


def test_oc_run_negative_logging(caplog):
    caplog.set_level(logging.INFO)
    with pytest.raises(subprocess.CalledProcessError):
        ocp.run_oc(["/bin/foo"], oc_executable="ls")
    assert caplog.records[0].message == "going to execute ['ls', '/bin/foo']"
    assert caplog.records[1].message.startswith('oc stdout:')
    assert caplog.records[2].message.startswith('oc stderr:')
    assert "No such file or directory" in caplog.records[2].message
    assert len(caplog.records) == 4
