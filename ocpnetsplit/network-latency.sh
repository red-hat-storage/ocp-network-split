#!/bin/bash

# Copyright 2023 Martin Bukatovič <mbukatov@redhat.com>
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
  echo
  echo "Usage: $(basename "${0}") [-d] [-l LATSPEC] <default egress latency>"
  echo
  echo "Where 'LATSPEC' defines specific latency between particular zones."
  echo "Eg.: 'AC=20' will set 20ms latency between zones A and C, while the"
  echo "rest of inter zone connections will use the default latency."
  echo
  echo The default latency is mandatory, while the optional zone specific one
  echo can be specified multiple times, for each zone connection as necessary.
  echo
  echo "Examples: $(basename "${0}") -l AB=25 -l AC=25 5"
}

if [[ $# = 0 ]]; then
  show_help
  exit
fi

# make sure we don't reuse variables from the outside environment by mistake
unset DEBUG_MODE

# dict for specific latencies
declare -A latspec

while getopts "dl:h" OPT; do
  # shellcheck disable=SC2209
  case $OPT in
  d) DEBUG_MODE=echo;;
  l) if [[ "$OPTARG" =~ ^([ABCX]{2})=([0-9]+)$ ]]; then
       zones=$(echo "${BASH_REMATCH[1]}" | grep -o . | sort | tr -d "\n");
       value=${BASH_REMATCH[2]};
       if [[ -n ${latspec[$zones]} ]]; then
         echo "Specific latency for $zones is defined multiple times." >&2;
         exit 1
       fi
       latspec[$zones]=$value;
     else
       echo "Invalid specific latency specified: ${OPTARG}" >&2;
       exit 1;
     fi;;
  h) show_help; exit;;
  *) show_help; exit 1;;
  esac
done

shift $((OPTIND-1))

if [[ $# = 0 ]]; then
  echo "The default egress latency not specified!" >&2
  exit 1
fi

# integer with default egress latency is the only mandatory argument of the
# script
if [[ $1 =~ ^[0-9]+$ ]]; then
  latency=${1}
else
  echo "The default egress latency specified $1 is not an integer value." >&2
  exit 1
fi

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
echo "network interface: $iface"

# delete all current qdiscss
# TODO: polish this so that the original configuration could be restored
# TODO: instead of deleting the original qdiscs, just alter it (would be
# more complex and error prone, it's not clear it's worth the effort)
$DEBUG_MODE tc qdisc del dev "${iface}" root

# dict for tracking qdisc with specific latency
declare -A qdisc_handles
# there will always be a qdisc with handle 1:4 for the default latency, so the
# next free minor handle is 1:5, hence:
next_minor_num=5
# for each zone specific delay value, allocate qdisc handle in qdisc_handles
for ZONES in "${!latspec[@]}"; do
  spec_latency=${latspec[$ZONES]}
  if [[ $latency -eq $spec_latency ]]; then
    continue
  fi
  if [[ -z ${qdisc_handles[${spec_latency}]} ]]; then
    qdisc_handles[${spec_latency}]=${next_minor_num}
    ((next_minor_num++))
  fi
done
# check how many bands we need: we won't touch the 3 default bands, so we
# will need one band for each lantecy
band_num=$((next_minor_num-1))

# define new qdisc structure
$DEBUG_MODE tc qdisc add dev "${iface}" root handle 1: prio bands "${band_num}"
$DEBUG_MODE tc qdisc add dev "${iface}" parent 1:4 handle 40: netem delay "${latency}"ms
# for each zone specific delay value, define new qdisc with given latency
for SP_LAT in "${!qdisc_handles[@]}"; do
  minor_num=${qdisc_handles[$SP_LAT]}
  $DEBUG_MODE tc qdisc add dev "${iface}" parent 1:${minor_num} handle ${minor_num}0: netem delay "${SP_LAT}"ms
done

# create tc filter/classifier for nodes in other zones, and direct traffic
# heading to them via netem qdisc
for zone_name in ZONE_A ZONE_B ZONE_C; do
  if [[ $current_zone = "${zone_name}" ]]; then
    continue
  fi
  for ip_addr in ${!zone_name}; do
    # check if there is a specific latency between current_zone and zone_name,
    # reling on lex. ordering of zone letters in latspec asoc. array keys
    ZX=${current_zone#ZONE_}
    ZY=${zone_name#ZONE_}
    if [[ ${ZX} < ${ZY} ]]; then
      spec_latency=${latspec[${ZX}${ZY}]}
    else
      spec_latency=${latspec[${ZY}${ZX}]}
    fi
    # if a specific latency is defined, use qdiscs for this latency, otherwise
    # use the default
    if [[ -z $spec_latency ]]; then
      handle=1:4
    else
      handle=1:${qdisc_handles[$spec_latency]:-4}
    fi
    # finally create a classifier
    $DEBUG_MODE tc filter add dev "${iface}" parent 1: protocol ip prio 1 u32 match ip dst ${ip_addr}/32 flowid ${handle}
  done
done
