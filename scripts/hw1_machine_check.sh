#!/bin/bash
#
# hw1_machine_check.sh
#
# Availability check for the 8 ECE lab machines used in Homework I
# (cache reverse engineering). Goes beyond simple SSH reachability by also
# reporting overall system load, currently logged-in users, and the idle
# percentage of EVERY logical CPU -- since a machine can be "up" while the
# specific core you'd taskset to is busy with someone else's work.
#
# Idle% is computed by sampling /proc/stat's per-CPU counters twice, one
# second apart, and taking (idle+iowait) as a fraction of the total delta
# across all counters. This is done in plain awk against /proc/stat rather
# than via mpstat, because mpstat (the sysstat package) is not installed on
# every lab machine and users typically don't have sudo there to install it
# -- /proc/stat is always present on Linux, so this works everywhere with
# no dependency.
#
# This does NOT check the shared Google Sheet reservation log -- that
# has to be checked manually, since it records what's PLANNED, while
# this script reports what's ACTUALLY happening right now.
#
# Usage:
#   ./hw1_machine_check.sh <unity_id> [highlight_core]
#
#   unity_id        - your NCSU Unity ID (required)
#   highlight_core  - logical CPU number to mark with '*' in the per-core
#                     listing, e.g. the one you're about to taskset to
#                     (optional; no highlighting if omitted)
#
# Requires: SSH access to *.ece.ncsu.edu (VPN group 8-Workshop-Temp
# connected if running from off-campus). You will be prompted for your
# password once per reachable machine unless you've set up SSH keys.
# Each machine takes just over 1 second (the /proc/stat sampling window)
# plus SSH round-trip time.

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <unity_id> [highlight_core]" >&2
  exit 1
fi

UNITY_ID="$1"
HIGHLIGHT_CORE="${2:-}"

MACHINES=(sunbird thunderbird skylark artemisia charnwood crux ookay upgrade)

for host in "${MACHINES[@]}"; do
  fqdn="${host}.ece.ncsu.edu"

  # The remote check runs as a small self-contained bash script piped over
  # SSH via a single-quoted heredoc, so no local variable ever gets mixed
  # into the remote command's quoting -- nothing is passed as a positional
  # argument since the per-core listing covers every CPU, not just one.
  output=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    "${UNITY_ID}@${fqdn}" bash -s 2>/dev/null << 'REMOTE_EOF'
LOAD=$(uptime | grep -oE 'load average: [0-9.]+' | awk '{print $3}')
USERS=$(who | awk '{print $1}' | sort -u | paste -sd, -)

SNAP1=$(grep -E '^cpu[0-9]+ ' /proc/stat)
sleep 1
SNAP2=$(grep -E '^cpu[0-9]+ ' /proc/stat)

IDLE=$(awk -v s1="$SNAP1" -v s2="$SNAP2" '
BEGIN {
    n1 = split(s1, lines1, "\n")
    n2 = split(s2, lines2, "\n")
    n = (n1 < n2) ? n1 : n2
    out = ""
    for (i = 1; i <= n; i++) {
        nf1 = split(lines1[i], f1, " ")
        nf2 = split(lines2[i], f2, " ")
        cpu = f1[1]
        sub(/^cpu/, "", cpu)
        idle1 = f1[5] + f1[6]
        idle2 = f2[5] + f2[6]
        tot1 = 0
        for (k = 2; k <= nf1; k++) tot1 += f1[k]
        tot2 = 0
        for (k = 2; k <= nf2; k++) tot2 += f2[k]
        dtotal = tot2 - tot1
        didle = idle2 - idle1
        pct = (dtotal > 0) ? (didle / dtotal * 100) : 0
        out = out sprintf("%s:%.1f,", cpu, pct)
    }
    print out
}')

echo "LOAD:${LOAD:-?}"
echo "USERS:${USERS:-none}"
echo "IDLE:${IDLE:-?}"
REMOTE_EOF
  )
  status=$?

  if [ $status -ne 0 ] || [ -z "$output" ]; then
    printf "%-12s DOWN (unreachable or SSH auth failed)\n" "$host"
    continue
  fi

  load=$(echo "$output" | grep '^LOAD:' | cut -d: -f2)
  users=$(echo "$output" | grep '^USERS:' | cut -d: -f2)
  idle_csv=$(echo "$output" | grep '^IDLE:' | cut -d: -f2-)

  printf "%-12s UP   load(1m)=%-6s users=%s\n" "$host" "${load:-?}" "${users:-none}"

  # idle_csv is "cpu:pct,cpu:pct,...". Print one line, marking
  # HIGHLIGHT_CORE with '*' if given, so it's easy to spot the specific
  # core you're about to taskset to among possibly 16-24+ entries.
  printf "  "
  IFS=',' read -ra pairs <<< "$idle_csv"
  for pair in "${pairs[@]}"; do
    [ -z "$pair" ] && continue
    cpu="${pair%%:*}"
    pct="${pair##*:}"
    if [ -n "$HIGHLIGHT_CORE" ] && [ "$cpu" = "$HIGHLIGHT_CORE" ]; then
      printf "cpu%s=%s%%*  " "$cpu" "$pct"
    else
      printf "cpu%s=%s%%  " "$cpu" "$pct"
    fi
  done
  printf "\n\n"
done
