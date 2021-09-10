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
  echo "Check network zone configuration and report current zone on stdout."
  echo "Usage: $(basename "${0}")"
}

print_current_zone()
{
  for host_ip_addr in $(hostname -I); do
    for zone_name in ZONE_{A,B,C}; do
      for zone_host_ip_addr in ${!zone_name}; do
        if [[ "${zone_host_ip_addr}" = "${host_ip_addr}" ]]; then
          echo ${zone_name}
          exit
        fi
      done
    done
  done
}

if [[ $# -gt 0 && $1 = "-h" ]]; then
  show_help
  exit
fi

# make sure that expected zone env. variables are present,
# and log their values to stderr
ERROR=0
for env_var in ZONE_A ZONE_B ZONE_C; do
  if [[ ! -v ${env_var} ]]; then
    echo "environment variable ${env_var} is not defined" >&2
    ERROR=1
  else
    echo "$env_var=\"${!env_var}\"" >&2
  fi
done

# external zone x is optional
if [[ -v ZONE_X ]]; then
  echo "ZONE_X=\"${ZONE_X}\"" >&2
fi

# script can't report the zone if there is a problem with zone configuration
if [[ $ERROR -eq 1 ]]; then
  exit 1
fi

# find out zone we are running in
current_zone=$(print_current_zone)

# check if we are actually running in one of the zones and report the results
if [[ -v ${current_zone} ]]; then
  echo "$current_zone"
else
  echo "current node doesn't belong to any zone" >&2
  echo "output of 'hostname -I' command: $(hostname -I)" >&2
  exit 1
fi
