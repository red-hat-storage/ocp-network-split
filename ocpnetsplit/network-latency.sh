#!/bin/bash

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

show_help()
{
  echo "Configure egress network latency via netem qdisc for a 3 zone cluster"
  echo "Usage: $(basename "${0}") [-d] <egress latency>"
}

if [[ $# = 0 ]]; then
  show_help
  exit
fi

# debug mode
if [[ $1 = "-d" ]]; then
  # shellcheck disable=SC2209
  DEBUG_MODE=echo
  shift
else
  unset DEBUG_MODE
fi

# integer with egress latency is the only argument of the script
case $1 in
  help|-h)   show_help; exit;;
  [0-9]*)    latency=$1; shift;;
  *)         show_help; exit 1
esac

# check zone configuration and detect current zone (we are running inside)
script_dir=$(realpath "$(dirname "$0")")
if ! current_zone=$("${script_dir}"/network-zone.sh); then
  echo "zone configuration is invalid, script can't continue"
  exit 1
fi

# report current zone
echo "current zone: $current_zone"

# locate main network interface (assuming all nodes are on a single network)
iface=$(ip route show default | cut -d' ' -f5)

# TODO: polish this to create as few changes in traffic queues as possible,
# so that the original configuration could be restored without node reboot
$DEBUG_MODE tc qdisc del dev "${iface}" root
$DEBUG_MODE tc qdisc add dev "${iface}" root handle 1: prio
$DEBUG_MODE tc qdisc add dev "${iface}" parent 1:1 handle 2: netem delay "${latency}"ms

# create tc filter/classifier for nodes in other zones, and direct traffic
# heading to them via netem qdisc
for zone_name in ZONE_A ZONE_B ZONE_C; do
  if [[ $current_zone = "${zone_name}" ]]; then
    continue
  fi
  for ip_addr in ${!zone_name}; do
    $DEBUG_MODE tc filter add dev "${iface}" parent 1: protocol ip prio 2 u32 match ip dst ${ip_addr}/32 flowid 3:1
  done
done
