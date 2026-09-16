#!/bin/bash
#
# hw1_software_hit_rate_relook.sh -- generic run of
# scripts/run_software_hit_rate_sweep.sh (Problem 8.5 parts 1-3, no PMU) for
# one Hazel generation, writing into a nested subdirectory under that
# machine's own data_raw/data_processed tree (data_raw/<machine>/phase1_v2/
# software_hit_rate/..., via a MACHINE_ARG of the form "hazel_<gen>/phase1_v2")
# -- this is the FIRST time this experiment has been run on any Hazel
# generation (CLAUDE.md's software-hit-rate section only covers the 8 lab
# machines), so there is no prior Hazel data to avoid clobbering, but the
# same phase1_v2 subdirectory convention as this generation's other relook
# jobs is used anyway for a self-contained, one-place record of this batch.
#
# Deliberately PMU-free -- no `perf`/PMU access on Hazel per the assignment
# (see CLAUDE.md), so only scripts/run_hit_rate_pmu_validation.sh (part 4,
# NOT this script) is off-limits here; this script never touches perf.
#
# One shared script for every generation -- per-run specifics (constraint,
# footprint sweep list, boundary spec for plot annotations, output/error log
# paths) are passed via sbatch command-line overrides at submit time, e.g.:
#   sbatch --constraint=broadwell \
#     --output=data_raw/hazel_broadwell/hw1_broadwell_software_hit_rate_v2_%j.log \
#     --error=data_raw/hazel_broadwell/hw1_broadwell_software_hit_rate_v2_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_broadwell/phase1_v2,FOOTPRINTS_ARG=4096+16384+32768+65536+131072+262144+1048576+4194304+8388608+16777216+33554432+67108864+134217728+268435456+536870912,BOUNDARIES_ARG=L1:32768+L2:262144+LLC:33554432+DRAM:536870912 \
#     hpc_slurm/hw1_software_hit_rate_relook.sh
#
# FOOTPRINTS_ARG/BOUNDARIES_ARG use '+' (NOT ',') to separate values -- see
# hw1_line_size_relook.sh's header comment for why (sbatch --export splits on
# top-level commas with no escaping). Both converted back to ',' before
# calling run_software_hit_rate_sweep.sh. Anchor FOOTPRINTS_ARG to this
# generation's own CAPACITY_RESULTS.md L1/L2/LLC boundaries (inserting them
# into the default log-spaced list) -- do not use the script's Sunbird-shaped
# default for a Hazel generation.
#
#SBATCH --job-name=hw1_swhitrate_relook
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --partition=compute_partners

set -euo pipefail

: "${MACHINE_ARG:?must set MACHINE_ARG via --export, e.g. hazel_broadwell/phase1_v2}"
: "${FOOTPRINTS_ARG:?must set FOOTPRINTS_ARG via --export (use '+' to separate -- see header comment)}"
: "${BOUNDARIES_ARG:?must set BOUNDARIES_ARG via --export, e.g. L1:32768+L2:262144+LLC:33554432+DRAM:536870912 (use '+' to separate -- see header comment)}"

FOOTPRINTS_CSV="${FOOTPRINTS_ARG//+/,}"
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

echo "=== Running scripts/run_software_hit_rate_sweep.sh (HAZEL_MODE=1) for ${MACHINE_ARG} ==="
HAZEL_MODE=1 ./scripts/run_software_hit_rate_sweep.sh "${MACHINE_ARG}" "${CORE:-0}" "${FOOTPRINTS_CSV}" "${BOUNDARIES_CSV}"

echo
echo "=== Done ==="
