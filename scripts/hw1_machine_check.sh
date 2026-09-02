#!/bin/bash
#
# hw1_machine_check.sh
#
# Availability check for the 8 ECE lab machines used in Homework I
# (cache reverse engineering). Goes beyond simple SSH reachability by
# also reporting overall system load, currently logged-in users, and
# the idle percentage of a SPECIFIC logical CPU (the one you intend to
# taskset your benchmark to) -- since a machine can be "up" while the
# exact core you care about is busy with someone else's work.
#
# This does NOT check the shared Google Sheet reservation log -- that
# has to be checked manually, since it records what's PLANNED, while
# this script reports what's ACTUALLY happening right now.
#
# Usage:
#   ./hw1_machine_check.sh <unity_id> [core_number]
#
#   unity_id     - your NCSU Unity ID (required)
#   core_number  - logical CPU to report idle% for (default: 4)
#
# Requires: SSH access to *.ece.ncsu.edu (VPN group 8-Workshop-Temp
# connected if running from off-campus). You will be prompted for your
# password once per reachable machine unless you've set up SSH keys.

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <unity_id> [core_number]" >&2
  exit 1
fi

UNITY_ID="$1"
CORE="${2:-4}"

MACHINES=(sunbird thunderbird skylark artemisia charnwood crux ookay upgrade)

printf "%-12s %-8s %-10s %-30s %-14s\n" "MACHINE" "STATUS" "LOAD(1m)" "LOGGED-IN USERS" "CORE${CORE}_IDLE%"
printf '%s\n' "--------------------------------------------------------------------------------------"

for host in "${MACHINES[@]}"; do
  fqdn="${host}.ece.ncsu.edu"

  # The remote check runs as a small self-contained bash script piped
  # over SSH via a single-quoted heredoc, so no local variable ever
  # gets mixed into the remote command's quoting -- only $CORE is
  # passed explicitly as a positional argument to the remote script.
  output=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    "${UNITY_ID}@${fqdn}" bash -s -- "${CORE}" 2>/dev/null << 'REMOTE_EOF'
CORE_ARG="$1"
LOAD=$(uptime | grep -oE 'load average: [0-9.]+' | awk '{print $3}')
USERS=$(who | awk '{print $1}' | sort -u | paste -sd, -)
if command -v mpstat >/dev/null 2>&1; then
  IDLE=$(mpstat -P "$CORE_ARG" 1 1 2>/dev/null | awk '/Average/ {print $NF}')
else
  IDLE="n/a"
fi
echo "LOAD:${LOAD:-?}"
echo "USERS:${USERS:-none}"
echo "IDLE:${IDLE:-?}"
REMOTE_EOF
  )
  status=$?

  if [ $status -ne 0 ] || [ -z "$output" ]; then
    printf "%-12s %-8s %-10s %-30s %-14s\n" "$host" "DOWN" "-" "-" "-"
    continue
  fi

  load=$(echo "$output" | grep '^LOAD:' | cut -d: -f2)
  users=$(echo "$output" | grep '^USERS:' | cut -d: -f2)
  idle=$(echo "$output" | grep '^IDLE:' | cut -d: -f2)

  printf "%-12s %-8s %-10s %-30s %-14s\n" "$host" "UP" "${load:-?}" "${users:-none}" "${idle:-?}"
done