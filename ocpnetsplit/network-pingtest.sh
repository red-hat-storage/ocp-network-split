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

# Debugging helper script: ping all machines from each zone and report it's RTT

script_dir=$(realpath "$(dirname "$0")")
script_env=${script_dir}/network-split.env
if [[ -f "${script_env}" ]]; then
  # shellcheck source=/dev/null
  source "${script_env}"
else
  echo "file ${script_env} not found" >&2
  exit 1
fi

for zone_name in ZONE_A ZONE_B ZONE_C ZONE_X; do
  echo ===============================================================================
  echo $zone_name
  echo ===============================================================================
  for ip_addr in ${!zone_name}; do
    echo -n "PING $ip_addr "
    ping -4 -q -c3 $ip_addr | grep ^rtt
  done
done
