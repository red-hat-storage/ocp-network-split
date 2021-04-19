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
import logging
import sys

import yaml

from ocpnetsplit import machineconfig
from ocpnetsplit import ocp
from ocpnetsplit import zone


LOGGER = logging.getLogger(name=__file__)


def get_zone_config(zone_a, zone_b, zone_c, zone_x_addrs=None):
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

    Returns:
        ZoneConfig: object with list of node ip addresses for each zone name
            *ocp network split* works with (``a``, ``b``, ...),
            see :py:const:`ocpnetsplit.zone.ZONES`).
    """
    zc = zone.ZoneConfig()
    for zone_name, label in zip(zone.ZONES, [zone_a, zone_b, zone_c]):
        LOGGER.debug("listing all ip addresses of nodes in zone %s", zone)
        cluster_nodes = ocp.list_cluster_nodes(label)
        for node in cluster_nodes:
            zc.add_nodes(zone_name, ocp.get_all_node_ip_addrs(node))
    if zone_x_addrs is not None:
        zc.add_nodes("x", zone_x_addrs)
    return zc


def get_networksplit_mc_spec(zone_env):
    """
    Create ``MachineConfig`` spec to install network split firewall tweaking
    script and unit files on all cluster nodes.

    Args:
        zone_env (str): content of firewall zone env file specifying node ip
            addresses for each cluster zone, as created by
            :py:meth:`ocpnetsplit.zone.ZoneConfig.get_env_file`

    Returns:
        machineconfig_spec: list of dictionaries with ``MachineConfig`` spec
    """
    mc_spec = []
    for role in "master", "worker":
        mc_spec.append(machineconfig.create_mc_dict(role, zone_env))
    return mc_spec


def schedule_split(split_name, target_dt, target_length):
    """
    Schedule start and stop of network split on all nodes of the cluster.

    Args:
        split_name (str): network split configuration specification, eg.
            ``ab``, see
            :py:const:`ocpnetsplit.zone.NETWORK_SPLITS` constant
        target_dt (datetime): requested start time of the network split
        target_length (int): number of minutes specifying how long the network
            split configuration should be active

    Raises:
        ValueError: in case invalid ``split_name`` or ``target_dt`` is
            specified.
    """
    # input validation
    if split_name not in zone.NETWORK_SPLITS:
        raise ValueError(f"invalid split_name specified: '{split_name}'")
    now_dt = datetime.now()
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
    for node in ocp.list_cluster_nodes():
        cmd_list = ["systemctl", "start",  start_unit, stop_unit]
        ocp.run_oc_debug_node(cmd_list, node)


def check_split(split_name):
    """
    Checks status of split via ``systemctl list-timers`` on all nodes of the
    cluster.

    Args:
        split_name (str): network split configuration specification, eg.
            ``ab``, see :py:const:`ocpnetsplit.zone.NETWORK_SPLITS`
            constant

    Raises:
        ValueError: when invalid ``split_name`` is specified
    """
    # input validation
    if split_name not in zone.NETWORK_SPLITS:
        raise ValueError(f"invalid split_name specified: '{split_name}'")
    # generate systemd timer unit pattern for list-timers
    start_unit_pattern = f"network-split-{split_name}-setup*"
    # check status of start timer on every node of the cluster
    for node in ocp.list_cluster_nodes():
        print(node)
        cmd_list = ["systemctl", "list-timers", start_unit_pattern]
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
    zone_config = get_zone_config(args.a, args.b, args.c, addr_list)
    zone_env = zone_config.get_env_file()

    if args.print_env_only:
        print(zone_env)
        return

    # get MachineConfig spec (ready to deploy list of dics)
    mc = get_networksplit_mc_spec(zone_env)
    args.output.write(yaml.dump_all(mc))


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
        "-d",
        "--debug",
        action="store_true",
        help="set log level to DEBUG")
    args = ap.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.timestamp is None:
        check_split(args.split_name)
        return

    try:
        start_dt = datetime.fromisoformat(args.timestamp)
    except ValueError as ex:
        print(ex)
        return 1
    schedule_split(args.split_name, start_dt, args.split_len)
