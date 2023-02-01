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


ZONES = ("a", "b", "c", "x")
"""
Stable zone identifiers as defined and used by ocp-network-split.
"""


NETWORK_SPLITS = ("ab", "bc", "ab-bc", "ab-ac", "ax", "ax-bx-cx")
"""
Available network split configurations. For every valid network split value,
there is a systemd timer unit named ``network-split-{split}-setup@.timer``.
Network split configuration consists of list of zone tuples, where each zone
tuple represents a disrupted zone connection.
"""


class ZoneConfig:
    """
    ZoneConfig is tracking ip addresses of nodes in each cluster zone.
    """

    def __init__(self):
        self._zones = {}

    def add_node(self, zone, node):
        """
        Add a node ip address into a zone.

        Args:
            zone (str): zone identification (one of ``ZONES``)
            node (str): ip address of a node
        """
        if zone not in ZONES:
            raise ValueError("Invalid zone name: {zone}")
        self._zones.setdefault(zone, set()).add(node)

    def add_nodes(self, zone, nodes):
        """
        Add list of node ip addresses into a zone.

        Args:
            zone (str): zone identification (one of ``ZONES``)
            nodes (list): list of string representation of node ip addresses
        """
        for node in nodes:
            self.add_node(zone, node)

    def get_nodes(self, zone=None):
        """
        Return set of node ip addresses in given zone.

        Args:
            zone (str): zone identification (one of ``ZONES``), if not
            specified, zone filtering is not applied and all nodes will be
            returned

        Returns:
            list: string representation of node ip addresses of given zone
        """
        if zone is not None:
            return self._zones.get(zone)
        nodes = []
        for zone in self._zones.keys():
            nodes += self._zones.get(zone)
        return nodes

    def get_env_file(self):
        """
        Generate content of env file for firewall script.

        Returns:
            str: content of firewall environment file with zone configuration
        """
        lines = []
        for zone, node_list in self._zones.items():
            nodes = " ".join(sorted(node_list))
            lines.append(f'ZONE_{zone.upper()}="{nodes}"')
        return "\n".join(lines) + "\n"


class ZoneLatSpec:
    """
    Describe latency values between given zones.

    Validation of input latency spec is necessary to catch mistakes as early as
    possible (debugging the problem later on a live cluster increases cost of
    debugging and a fix significantly).
    """

    def __init__(self, **kwargs):
        self._latspec = {}
        if kwargs is not None and len(kwargs) > 0:
            self.load_dict(kwargs)

    def load_arguments(self, latency_spec):
        """
        Load latency spec from the given list produced by argparse parser.

        Args:
            latency_spec (list): List of latency specs from argument parser.
                Eg.: ``['ab=10', 'bc=10']``.
        """
        lat_spec_dict = {}
        for latspec in latency_spec:
            zones, v = latspec.split("=")
            if zones in lat_spec_dict and lat_spec_dict[zones] != v:
                raise ValueError(
                    f"Latency between {zones} zones specified multiple times.")
            lat_spec_dict[zones] = v
        self.load_dict(lat_spec_dict)

    def load_dict(self, latency_spec):
        """
        Load latency spec from the given dict.

        Args:
            latency_spec (dict): specific latency between given zones, for
            example ``{'ab'=11}`` will represent 22ms RTT latency between zones
            ``a`` and ``b``.
        """
        for zones, v in latency_spec.items():
            if type(v) == str:
                if not v.isnumeric():
                    raise ValueError(f"non numeric latency value in '{zones}={v}'")
            elif type(v) != int:
                raise ValueError(f"non numeric latency value in '{zones}={v}'")
            if len(zones) != 2:
                raise ValueError(
                    f"Invalid number of zones in latenc spec '{zones}={v}'")
            for zone in zones:
                if zone not in ZONES:
                    raise ValueError(
                        f"Invalid zone '{zone}' in latency spec '{zones}={v}'")
            zones = "".join(sorted(zones))
            if zones in self._latspec and self._latspec[zones] != v:
                raise ValueError(
                    f"Latency between {zones} zones specified multiple times.")
            self._latspec[zones] = v

    def get_cli_args(self):
        """
        Generate command line arguments for network-latency.sh script
        representing latency spec of this object.
        """
        arglist = []
        for zones, latency in self._latspec.items():
            arglist.append(f"-l {zones}={latency}")
        return " ".join(arglist)
