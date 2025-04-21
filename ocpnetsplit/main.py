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
Module with a public API of ocp-network-split project. One can either use the
command line tools (as implemented via main functions in this module), or to
use the python functions defined here directly.
"""


from datetime import datetime, timedelta
import argparse
import configparser
import logging
import socket
import subprocess
import sys

import yaml

from ocpnetsplit import machineconfig
from ocpnetsplit import ocp
from ocpnetsplit import zone


LOGGER = logging.getLogger(name=__file__)


def run_ssh_node(cmd_list, node, timeout=600):
    """
    Run given command on given node via ssh assuming connection details like
    username and keys are specified via ~/.ssh/config file.

    Args:
        cmd_list (list): a command to run, eg. ``["uname", "-a"]`` will
            execute ``uname -a`` process on the node
        node (str): hostname of k8s node where to execute the command
        timeout (int): command timeout specified in seconds, optional

    Returns:
        tuple: ssh stdout, ssh souterr
    """
    # using sudo in all cases, we don't need to care if we are connecting to
    # the node as root or coreos user
    ssh_cmd = ["ssh", node, "sudo"] + cmd_list
    LOGGER.info("going to execute %s", ssh_cmd)
    comp_proc = subprocess.run(
        ssh_cmd,
        capture_output=True,
        timeout=timeout)
    # log whole output of the process
    proc_log_level = logging.DEBUG
    if comp_proc.returncode > 0:
        proc_log_level = logging.WARNING
    LOGGER.log(proc_log_level, "ssh stdout: %s", comp_proc.stdout)
    LOGGER.log(proc_log_level, "ssh stderr: %s", comp_proc.stderr)
    LOGGER.log(proc_log_level, "ssh return code: %d", comp_proc.returncode)
    # after the logging is done, we can raise the exception if necessary
    comp_proc.check_returncode()
    # if all is ok, let's return output
    ssh_stdout = comp_proc.stdout.decode()
    ssh_stderr = comp_proc.stderr.decode()
    return ssh_stdout, ssh_stderr


def get_zone_config(zone_a, zone_b, zone_c, zone_x_addrs=None, kubeconfig=None):
    """
    For each valid ocp-network-split zone name (see
    :py:const:`ocpnetsplit.zone.ZONES`), translate it's given
    ``topology.kubernetes.io/zone`` label into list of ip addresses of all
    nodes in the zone.

    Args:
        zone_a (str): value of zone ``a`` label
        zone_b (str): value of zone ``b`` label
        zone_c (str): value of zone ``c`` label
        zone_x_addrs (list): list of ip addresses in external zone ``x``
        kubeconfig (str): file path to kubeconfig

    Returns:
        ZoneConfig: object with list of node ip addresses for each zone name
            *ocp network split* works with (``a``, ``b``, ...),
            see :py:const:`ocpnetsplit.zone.ZONES`).
    """
    zc = zone.ZoneConfig()
    for zone_name, label in zip(zone.ZONES, [zone_a, zone_b, zone_c]):
        LOGGER.debug("listing all ip addresses of nodes in zone %s", zone)
        cluster_nodes = ocp.list_cluster_nodes(label, kubeconfig=kubeconfig)
        for node in cluster_nodes:
            zc.add_nodes(zone_name, ocp.get_all_node_ip_addrs(node, kubeconfig=kubeconfig))
    if zone_x_addrs is not None:
        zc.add_nodes("x", zone_x_addrs)
    return zc


def get_zone_config_fromfile(file_content, translate_hostname=True):
    """
    Get zone config from ini file, which contains node fqdn entries for each
    zone.
    """
    config = configparser.ConfigParser(allow_no_value=True)
    config.read_string(file_content)
    zc = zone.ZoneConfig()
    for zone_name in zone.ZONES:
        if not config.has_section(zone_name):
            continue
        for host_name in config[zone_name]:
            if translate_hostname:
                try:
                    host = socket.gethostbyname(host_name)
                except socket.gaierror as ex:
                    msg = f"DNS lookup for '{host_name}' failed: {ex.strerror} [errno {ex.errno}]"
                    raise Exception(msg)
            else:
                host = host_name
            zc.add_node(zone_name, host)
    return zc


def get_networksplit_mc_spec(zone_env=None, split=False, latency=0, latency_spec=None):
    """
    Create ``MachineConfig`` spec to install network split firewall tweaking
    script and unit files on all cluster nodes.

    Args:
        zone_env (str): content of firewall zone env file specifying node ip
            addresses for each cluster zone, as created by
            :py:meth:`ocpnetsplit.zone.ZoneConfig.get_env_file`
        split (bool): when true, support for net splits will be included
        latency (int): default zone latency created via Linux Traffic Control
            in ms, when the value is zero, support for latency is not included
        latency_spec (:py:class`ocpnetsplit.zone.ZoneLatSpec`): specific
            latency between given zones (optional).

    Returns:
        machineconfig_spec: list of dictionaries with ``MachineConfig`` spec
    """
    mc_spec = []
    for role in "master", "worker":
        if zone_env is not None:
            mc_spec.append(machineconfig.create_zone_mc_dict(role, zone_env))
        if latency != 0:
            mc_spec.append(machineconfig.create_latency_mc_dict(role, latency, latency_spec))
        if split:
            mc_spec.append(machineconfig.create_split_mc_dict(role))
    return mc_spec


def schedule_split(nodes, split_name, target_dt, target_length, use_ssh=False, kubeconfig=None):
    """
    Schedule start and stop of network split on all nodes of the cluster.

    Args:
        nodes (list): list of all nodes from all zones
        split_name (str): network split configuration specification, eg.
            ``ab``, see
            :py:const:`ocpnetsplit.zone.NETWORK_SPLITS` constant
        target_dt (datetime): requested start time of the network split
        target_length (int): number of minutes specifying how long the network
            split configuration should be active
        use_ssh (bool): if true, connect to the nodes via ssh; use oc debug
            node otherwise
        kubeconfig (str): file path to kubeconfig

    Raises:
        ValueError: in case invalid ``split_name`` or ``target_dt`` is
            specified.
    """
    # input validation
    if split_name not in zone.NETWORK_SPLITS:
        raise ValueError(f"invalid split_name specified: '{split_name}'")
    now_dt = datetime.now()
    # let's not schedule in the past
    if target_dt - now_dt <= timedelta(minutes=0):
        msg = (
            "target start time has already passed, "
            "it's not possible to schedule a network split in the past"
        )
        LOGGER.error(msg)
        raise ValueError(msg)
    # scheduling could take about 30 seconds for a cluster with 9 machines
    if target_dt - now_dt <= timedelta(minutes=1):
        msg = (
            "target start time is not at least 1 minute in the future, "
            "and it's not possible to guarantee that start timers will be "
            "scheduled across all nodes in time"
        )
        LOGGER.error(msg)
        raise ValueError(msg)
    # convert start timestamp into unix time (number of seconds since epoch)
    start_ts = int(target_dt.timestamp())
    # compute target stop timestamp
    stop_ts = start_ts + (target_length * 60)
    # generate systemd timer unit names
    start_unit = f"network-split-{split_name}-setup@{start_ts}.timer"
    stop_unit = f"network-split-teardown@{stop_ts}.timer"
    # schedule both timers on every node of the cluster
    for node in nodes:
        cmd_list = ["systemctl", "start",  start_unit, stop_unit]
        if use_ssh:
            run_ssh_node(cmd_list, node)
        else:
            ocp.run_oc_debug_node(cmd_list, node, kubeconfig=kubeconfig)


def check_split(nodes, split_name, use_ssh=False):
    """
    Checks status of split via ``systemctl list-timers`` on all nodes of the
    cluster.

    Args:
        nodes (list): list of all nodes from all zones
        split_name (str): network split configuration specification, eg.
            ``ab``, see :py:const:`ocpnetsplit.zone.NETWORK_SPLITS`
            constant
        use_ssh (bool): if true, connect to the nodes via ssh; use oc debug
            node otherwise

    Raises:
        ValueError: when invalid ``split_name`` is specified
    """
    # input validation
    if split_name not in zone.NETWORK_SPLITS:
        raise ValueError(f"invalid split_name specified: '{split_name}'")
    # generate systemd timer unit pattern for list-timers
    start_unit_pattern = f"network-split-{split_name}-setup*"
    # check status of start timer on every node of the cluster
    for node in nodes:
        print(node)
        cmd_list = ["systemctl", "list-timers", start_unit_pattern]
        if use_ssh:
            stdout, _ = run_ssh_node(cmd_list, node)
        else:
            stdout, _ = ocp.run_oc_debug_node(cmd_list, node)
        for line in stdout.splitlines():
            if line.startswith("Pass --all to see"):
                continue
            if line.endswith("timers listed."):
                continue
            print(line)


def main_setup():
    """
    Simple command line interface to generate MachineConfig yaml to deploy to
    make scheduling network splits possible.

    Example usage::

         $ ocp-network-split-setup -a arbiter -b d1 -c d2 -o mc.yaml
         $ oc create -f mc.yaml
         $ oc get mcp

    """
    ap = argparse.ArgumentParser(description="network split setup helper")
    ap.add_argument(
        "--print-env-only",
        action="store_true",
        default=False,
        help="just show firewall zone env file and exit")
    ap.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="name of yaml file with MachineConfig to deploy on OCP cluster")
    ap.add_argument(
        "-a",
        "--zone-a",
        dest="a",
        metavar="LABEL",
        required=True,
        help="topology.kubernetes.io/zone label of zone a")
    ap.add_argument(
        "-b",
        "--zone-b",
        dest="b",
        metavar="LABEL",
        required=True,
        help="topology.kubernetes.io/zone label of zone b")
    ap.add_argument(
        "-c",
        "--zone-c",
        dest="c",
        metavar="LABEL",
        required=True,
        help="topology.kubernetes.io/zone label of zone c")
    ap.add_argument(
        "--zone-x-addrs",
        dest="x_addrs",
        metavar="IP_ADDRS",
        help="comma separated list of IP addresses of external services")
    ap.add_argument(
        "--no-zone-env",
        action="store_true",
        default=False,
        help="don't include zone env MachineConfig")
    ap.add_argument(
        "--no-split",
        action="store_true",
        default=False,
        help="don't include netsplit MachineConfig")
    ap.add_argument(
        "--latency",
        "-l",
        default=0,
        type=int,
        help="default network latency in ms to be created among zones")
    ap.add_argument(
        "--latency-spec",
        nargs="*",
        type=str,
        help='network latency in ms among given zones, eg. "ab=10 ac=25"')
    ap.add_argument(
        "--debug",
        action="store_true",
        help="set log level to DEBUG")
    args = ap.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # get node ip addresses of each zone via zone config
    if args.x_addrs is not None:
        addr_list = args.x_addrs.split(",")
    else:
        addr_list = None

    if args.no_zone_env:
        zone_env = None
        if args.print_env_only:
            err_msg = (
                "options --no-zone-env and --print-env-only can't be both "
                "used at the same time")
            print(err_msg, file=sys.stderr)
            return 1
    else:
        zone_config = get_zone_config(args.a, args.b, args.c, addr_list)
        zone_env = zone_config.get_env_file()
        if args.print_env_only:
            print(zone_env)
            return

    # get zone latency spec object if latency_spec was specified via argument
    if args.latency_spec is not None:
        latency_spec = zone.ZoneLatSpec()
        latency_spec.load_arguments(args.latency_spec)
    else:
        latency_spec = None

    # get MachineConfig spec (ready to deploy list of dics)
    mc = get_networksplit_mc_spec(
            zone_env,
            split=(not args.no_split),
            latency=args.latency,
            latency_spec=latency_spec)
    args.output.write(yaml.dump_all(mc))


def main_multisetup():
    """
    Simple multi cluster version of command line interface to generate
    MachineConfig yaml and env file to deploy on OCP/Ceph clusters.

    Example usage::

        $ ocp-network-split-multisetup zones.ini --mc mc.yaml --env network-split.env

    """
    ap = argparse.ArgumentParser(
            description="multi cluster network split setup helper")
    ap.add_argument(
        "zonefile",
        type=argparse.FileType("r"),
        help="ini file with list of node fqdn for each zone a, b and c")
    ap.add_argument(
        "--mc",
        metavar="FILE",
        required=True,
        type=argparse.FileType("w"),
        help="name of an output yaml file with MachineConfig entries")
    ap.add_argument(
        "--env",
        metavar="FILE",
        default=sys.stdout,
        type=argparse.FileType("w"),
        help="name of an output env file with zone configuration")
    ap.add_argument(
        "--no-split",
        action="store_true",
        default=False,
        help="don't include netsplit MachineConfig")
    ap.add_argument(
        "--latency",
        "-l",
        default=0,
        type=int,
        help="default network latency in ms to be created among zones")
    ap.add_argument(
        "--latency-spec",
        nargs="*",
        type=str,
        help='network latency in ms among given zones, eg. "ab=10 ac=25"')
    ap.add_argument(
        "--debug",
        action="store_true",
        help="set log level to DEBUG")
    args = ap.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # get zoneconfig from the ansible inventory like ini file
    try:
        zone_config = get_zone_config_fromfile(args.zonefile.read())
    except Exception as ex:
        print(f"Failed to process zonefile: {ex}", file=sys.stderr)
        return 1
    zone_env = zone_config.get_env_file()
    # save separate zoneconfig (for ansible deployment later)
    args.env.write(zone_env)

    # get zone latency spec object if latency_spec was specified via argument
    if args.latency_spec is not None:
        latency_spec = zone.ZoneLatSpec()
        latency_spec.load_arguments(args.latency_spec)
    else:
        latency_spec = None

    # get MachineConfig spec (ready to deploy list of dics)
    mc = get_networksplit_mc_spec(
            zone_env,
            split=(not args.no_split),
            latency=args.latency,
            latency_spec=latency_spec)
    args.mc.write(yaml.dump_all(mc))


def main_sched():
    """
    Simple command line interface to schedule given cluster network split.

    Example usage::

         $ ocp-network-split-sched ab-bc -t 2021-03-18T18:45 --split-len 30
         $ ocp-network-split-sched ab-bc
    """
    ap = argparse.ArgumentParser(description="network split scheduler")
    ap.add_argument(
        "split_name",
        choices=zone.NETWORK_SPLITS,
        help="which split configuration to schedule")
    ap.add_argument(
        "-t",
        "--timestamp",
        help="moment when to schedule the network split (in ISO format)")
    ap.add_argument(
        "--split-len",
        metavar="MIN",
        default=15,
        type=int,
        help="how long the network split should take (in minutes)")
    ap.add_argument(
        "--zonefile",
        type=argparse.FileType("r"),
        help=("ini file with list of node fqdn for each zone, "
              "will use ssh instead of `oc debug` when specified"))
    ap.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="set log level to DEBUG")
    args = ap.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # get list of all nodes (across all zones)
    if args.zonefile is not None:
        zone_config = get_zone_config_fromfile(
                args.zonefile.read(), translate_hostname=False)
        nodes = zone_config.get_nodes()
        use_ssh = True
    else:
        nodes = ocp.list_cluster_nodes()
        use_ssh = False

    if args.timestamp is None:
        check_split(nodes, args.split_name, use_ssh)
        return

    try:
        start_dt = datetime.fromisoformat(args.timestamp)
    except ValueError as ex:
        print(ex)
        return 1

    schedule_split(nodes, args.split_name, start_dt, args.split_len, use_ssh)
