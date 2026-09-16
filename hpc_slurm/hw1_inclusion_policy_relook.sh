#!/bin/bash
#
# hw1_inclusion_policy_relook.sh -- generic re-run of
# scripts/run_inclusion_policy_full.sh for one Hazel generation, writing into
# a SEPARATE nested subdirectory under that machine's own data_raw/
# data_processed tree (data_raw/<machine>/phase1_v2/inclusion_policy/..., via
# a MACHINE_ARG of the form "hazel_<gen>/phase1_v2") rather than overwriting
# the original run's own inclusion_policy/ directory. This re-run exists
# because CAPACITY_RESULTS.md's L1/L2/LLC boundary values for several Hazel
# generations were revised after the original inclusion_policy pass ran
# against the old values -- see CLAUDE.md's Hazel status section and
# CAPACITY_RESULTS.md itself. Original data is kept as-is, not clobbered.
#
# MUST use the SAME MACHINE_ARG as this generation's own
# hw1_miss_latency_relook.sh job, and MUST be submitted with a
# --dependency=afterok on that job's ID -- this script's calibration reads
# that run's own raw output under
# data_processed/<MACHINE_ARG>/latency/miss/<transition>/ (see
# run_inclusion_policy_full.sh's header comment).
#
# One shared script for every generation -- per-run specifics (constraint,
# pairing spec, assumed line size, output/error log paths) are passed via
# sbatch command-line overrides at submit time, e.g.:
#   sbatch --constraint=broadwell --dependency=afterok:<miss_latency_v2_job_id> \
#     --output=data_raw/hazel_broadwell/hw1_broadwell_inclusion_policy_v2_%j.log \
#     --error=data_raw/hazel_broadwell/hw1_broadwell_inclusion_policy_v2_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_broadwell/phase1_v2,PAIRINGS_ARG=L1_vs_L2:32768:262144:L1_to_L2+L2_vs_LLC:262144:33554432:L2_to_LLC+L1_vs_LLC:32768:33554432:LLC_to_DRAM,ASSUMED_LINE_SIZE_BYTES=64 \
#     hpc_slurm/hw1_inclusion_policy_relook.sh
#
# PAIRINGS_ARG uses '+' (NOT ',') to separate the pairing specs -- see
# hw1_line_size_relook.sh's header comment for why (sbatch --export splits on
# top-level commas with no escaping). Converted back to ',' before calling
# run_inclusion_policy_full.sh. ASSUMED_LINE_SIZE_BYTES defaults to 64 inside
# run_inclusion_policy_full.sh itself if not exported -- override per this
# generation's own confirmed line_size/ result if it differs.
#
#SBATCH --job-name=hw1_inclpol_relook
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:55:00
#SBATCH --partition=compute_partners

set -euo pipefail

: "${MACHINE_ARG:?must set MACHINE_ARG via --export, e.g. hazel_broadwell/phase1_v2}"
: "${PAIRINGS_ARG:?must set PAIRINGS_ARG via --export, e.g. L1_vs_L2:32768:262144:L1_to_L2+L2_vs_LLC:262144:33554432:L2_to_LLC+L1_vs_LLC:32768:33554432:LLC_to_DRAM (use '+' to separate -- see header comment)}"

PAIRINGS_CSV="${PAIRINGS_ARG//+/,}"

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

echo "=== Running scripts/run_inclusion_policy_full.sh (HAZEL_MODE=1) for ${MACHINE_ARG}, pairings=${PAIRINGS_CSV}, assumed_line_size_bytes=${ASSUMED_LINE_SIZE_BYTES:-64} ==="
HAZEL_MODE=1 ./scripts/run_inclusion_policy_full.sh "${MACHINE_ARG}" "${CORE:-0}" "${PAIRINGS_CSV}"

echo
echo "=== Done ==="
