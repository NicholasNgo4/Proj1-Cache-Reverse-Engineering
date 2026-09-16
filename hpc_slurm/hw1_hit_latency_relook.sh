#!/bin/bash
#
# hw1_hit_latency_relook.sh -- generic re-run of scripts/run_hit_latency_full.sh
# for one Hazel generation, writing into a SEPARATE nested subdirectory under
# that machine's own data_raw/data_processed tree (data_raw/<machine>/phase1_v2/
# latency/hit/..., via a MACHINE_ARG of the form "hazel_<gen>/phase1_v2")
# rather than overwriting the original run's own latency/hit/ directory. This
# re-run exists because CAPACITY_RESULTS.md's L1/L2/LLC boundary values for
# several Hazel generations were revised after the original hit_latency pass
# ran against the old values -- see CLAUDE.md's Hazel status section and
# CAPACITY_RESULTS.md itself. Original data is kept as-is, not clobbered.
#
# Use the SAME MACHINE_ARG for this script's sibling
# hw1_miss_latency_relook.sh and hw1_inclusion_policy_relook.sh runs on the
# same generation -- miss_latency and inclusion_policy both look for prior
# output under data_processed/<MACHINE_ARG>/latency/{hit,miss}/, so they must
# share this run's own MACHINE_ARG to find each other.
#
# One shared script for every generation -- per-run specifics (constraint,
# boundary spec, output/error log paths) are passed via sbatch command-line
# overrides at submit time, e.g.:
#   sbatch --constraint=broadwell \
#     --output=data_raw/hazel_broadwell/hw1_broadwell_hit_latency_v2_%j.log \
#     --error=data_raw/hazel_broadwell/hw1_broadwell_hit_latency_v2_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_broadwell/phase1_v2,BOUNDARIES_ARG=L1:32768+L2:262144+LLC:33554432+DRAM:536870912 \
#     hpc_slurm/hw1_hit_latency_relook.sh
#
# BOUNDARIES_ARG uses '+' (NOT ',') to separate the level:bytes pairs -- see
# hw1_line_size_relook.sh's header comment for why (sbatch --export splits on
# top-level commas with no escaping). Converted back to ',' before calling
# run_hit_latency_full.sh.
#
#SBATCH --job-name=hw1_hitlat_relook
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=compute_partners

set -euo pipefail

: "${MACHINE_ARG:?must set MACHINE_ARG via --export, e.g. hazel_broadwell/phase1_v2}"
: "${BOUNDARIES_ARG:?must set BOUNDARIES_ARG via --export, e.g. L1:32768+L2:262144+LLC:33554432+DRAM:536870912 (use '+' to separate -- see header comment)}"

BOUNDARIES_CSV="${BOUNDARIES_ARG//+/,}"

echo "=== Machine identification (Phase Discipline whitelist only) ==="
hostname
uname -a
grep -m1 -E 'model name|Hardware|Processor' /proc/cpuinfo
CORE=$(numactl -s 2>/dev/null | awk '/physcpubind/{print $2}')
echo "Assigned logical CPU: ${CORE:-unknown}, SLURM_JOB_ID=${SLURM_JOB_ID:-unset}"
echo

if ! git merge-base --is-ancestor predictions-frozen HEAD 2>/dev/null; then
  echo "predictions-frozen is NOT an ancestor of HEAD -- refusing to run." >&2
  exit 1
fi

source hpc_slurm/hazel_python_env.sh

echo "=== Running scripts/run_hit_latency_full.sh (HAZEL_MODE=1) for ${MACHINE_ARG}, boundaries=${BOUNDARIES_CSV} ==="
HAZEL_MODE=1 ./scripts/run_hit_latency_full.sh "${MACHINE_ARG}" "${CORE:-0}" "${BOUNDARIES_CSV}"

echo
echo "=== Done ==="
