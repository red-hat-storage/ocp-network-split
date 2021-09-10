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
  echo "Network split for cluster with 3 zones"
  echo "Usage: $(basename "${0}") [-d] <setup|teardown> <split-config>"
  echo
  echo "Argument split-config describes network split among 3 zones a, b and c"
  echo "While zone x denotes external nodes outside of the cluster."
  echo "eg. 'bc' means that connection between zones b and c is lost"
  echo "Examples of valid splits: bc, ab, ab-bc, ab-ac, ax"
}

if [[ $# = 0 ]]; then
  show_help
  exit
fi

# debug mode
if [[ $1 = "-d" ]]; then
  # this is done on purpose to print commands executed by this script instead
  # of executing them when debug mode is enabled
  # shellcheck disable=SC2209
  DEBUG_MODE=echo
  shift
else
  unset DEBUG_MODE
fi

# iptables mode (append rules or remove rules)
case $1 in
  help|-h)   show_help; exit;;
  setup)     OP="-A"; shift;;
  teardown)  OP="-D"; shift;;
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

# load network split specification from command line
net_split_spec=${1//-/ }

# try to apply firewall rules for each network split specification
for i in ${net_split_spec}; do
  # make sure the split specification is upper case
  split=${i^^}
  # read the split configuration
  affected_zone=ZONE_${split:0:1}
  blocked_zone=ZONE_${split:1:1}
  if [[ ${OP} = "-A" ]]; then
    op_desc=blocked
  else
    op_desc="available again"
  fi
  # log and explain selected network split configuration
  echo "${i}: ${blocked_zone} will be ${op_desc} from ${affected_zone}"
  if [[ ${current_zone} = "${affected_zone}" ]]; then
    for node_addr in ${!blocked_zone}; do
      # block all packets from or to given node
      $DEBUG_MODE iptables ${OP} INPUT  -s "${node_addr}" -j DROP -v
      $DEBUG_MODE iptables ${OP} OUTPUT -d "${node_addr}" -j DROP -v
    done
  fi
done
