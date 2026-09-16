#!/bin/bash
#
# hw1_associativity_relook.sh -- generic re-run of scripts/run_associativity_full.sh
# for one Hazel generation, writing into a SEPARATE nested subdirectory under
# that machine's own data_raw/data_processed tree (data_raw/<machine>/phase1_v2/
# associativity/..., via a MACHINE_ARG of the form "hazel_<gen>/phase1_v2")
# rather than overwriting the original run's own associativity/ directory.
# This re-run exists because CAPACITY_RESULTS.md's L1/L2/LLC boundary values
# for several Hazel generations were revised after the original associativity
# pass ran against the old values -- see CLAUDE.md's Hazel status section and
# CAPACITY_RESULTS.md itself. Original data is kept as-is, not clobbered.
#
# One shared script for every generation -- per-run specifics (constraint,
# which cache_bytes_csv to use, output/error log paths) are passed via sbatch
# command-line overrides at submit time, e.g.:
#   sbatch --constraint=broadwell \
#     --output=data_raw/hazel_broadwell/hw1_broadwell_associativity_v2_%j.log \
#     --error=data_raw/hazel_broadwell/hw1_broadwell_associativity_v2_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_broadwell/phase1_v2,CACHE_BYTES_ARG=32768+262144+33554432 \
#     hpc_slurm/hw1_associativity_relook.sh
#
# CACHE_BYTES_ARG uses '+' (NOT ',') to separate the L1/L2/LLC values -- sbatch's
# --export parser splits its whole argument on top-level commas with no
# escaping, so a literal ',' here would get silently truncated (real bug found
# and documented in hw1_line_size_relook.sh's own header comment, 2026-09-15).
# This script converts '+' back to ',' before calling run_associativity_full.sh.
#
# CACHE_BYTES_ARG's LLC value must already be page-aligned (a multiple of 4096
# -- main.c's ASSOC_CACHE_BYTES_ALIGN check) even if CAPACITY_RESULTS.md's own
# LLC byte value for that generation isn't -- round to the nearest 4096-byte
# multiple by hand first (same fix already applied to 4 of the 8 original
# associativity jobs, see CLAUDE.md's Hazel status section).
#
#SBATCH --job-name=hw1_assoc_relook
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=compute_partners

set -euo pipefail

: "${MACHINE_ARG:?must set MACHINE_ARG via --export, e.g. hazel_broadwell/phase1_v2}"
: "${CACHE_BYTES_ARG:?must set CACHE_BYTES_ARG via --export, e.g. 32768+262144+33554432 (use '+' to separate -- see header comment)}"

CACHE_BYTES_CSV="${CACHE_BYTES_ARG//+/,}"

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

echo "=== Running scripts/run_associativity_full.sh (HAZEL_MODE=1) for ${MACHINE_ARG}, cache_bytes=${CACHE_BYTES_CSV} ==="
HAZEL_MODE=1 ./scripts/run_associativity_full.sh "${MACHINE_ARG}" "${CORE:-0}" "${CACHE_BYTES_CSV}"

echo
echo "=== Done ==="
