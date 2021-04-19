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

    def get_nodes(self, zone):
        """
        Return set of node ip addresses in given zone.

        Args:
            zone (str): zone identification (one of ``ZONES``)

        Returns:
            list: string representation of node ip addresses of given zone
        """
        return self._zones.get(zone)

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
