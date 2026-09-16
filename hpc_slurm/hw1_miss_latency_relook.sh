#!/bin/bash
#
# hw1_miss_latency_relook.sh -- generic re-run of scripts/run_miss_latency_full.sh
# for one Hazel generation, writing into a SEPARATE nested subdirectory under
# that machine's own data_raw/data_processed tree (data_raw/<machine>/phase1_v2/
# latency/miss/..., via a MACHINE_ARG of the form "hazel_<gen>/phase1_v2")
# rather than overwriting the original run's own latency/miss/ directory. This
# re-run exists because CAPACITY_RESULTS.md's L1/L2/LLC boundary values for
# several Hazel generations were revised after the original miss_latency pass
# ran against the old values -- see CLAUDE.md's Hazel status section and
# CAPACITY_RESULTS.md itself. Original data is kept as-is, not clobbered.
#
# Use the SAME MACHINE_ARG for this script's sibling
# hw1_hit_latency_relook.sh and hw1_inclusion_policy_relook.sh runs on the
# same generation -- inclusion_policy's calibration reads THIS run's own raw
# output under data_processed/<MACHINE_ARG>/latency/miss/<transition>/, so
# it must run (and complete) before an inclusion_policy_relook job sharing
# this same MACHINE_ARG is submitted.
#
# One shared script for every generation -- per-run specifics (constraint,
# transition spec, output/error log paths) are passed via sbatch command-line
# overrides at submit time, e.g.:
#   sbatch --constraint=broadwell \
#     --output=data_raw/hazel_broadwell/hw1_broadwell_miss_latency_v2_%j.log \
#     --error=data_raw/hazel_broadwell/hw1_broadwell_miss_latency_v2_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_broadwell/phase1_v2,TRANSITIONS_ARG=L1_to_L2:32768:262144+L2_to_LLC:262144:33554432+LLC_to_DRAM:33554432:536870912 \
#     hpc_slurm/hw1_miss_latency_relook.sh
#
# TRANSITIONS_ARG uses '+' (NOT ',') to separate the transition specs -- see
# hw1_line_size_relook.sh's header comment for why (sbatch --export splits on
# top-level commas with no escaping). Converted back to ',' before calling
# run_miss_latency_full.sh.
#
#SBATCH --job-name=hw1_misslat_relook
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
#SBATCH --partition=compute_partners

set -euo pipefail

: "${MACHINE_ARG:?must set MACHINE_ARG via --export, e.g. hazel_broadwell/phase1_v2}"
: "${TRANSITIONS_ARG:?must set TRANSITIONS_ARG via --export, e.g. L1_to_L2:32768:262144+L2_to_LLC:262144:33554432+LLC_to_DRAM:33554432:536870912 (use '+' to separate -- see header comment)}"

TRANSITIONS_CSV="${TRANSITIONS_ARG//+/,}"

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

echo "=== Running scripts/run_miss_latency_full.sh (HAZEL_MODE=1) for ${MACHINE_ARG}, transitions=${TRANSITIONS_CSV} ==="
HAZEL_MODE=1 ./scripts/run_miss_latency_full.sh "${MACHINE_ARG}" "${CORE:-0}" "${TRANSITIONS_CSV}"

echo
echo "=== Done ==="
