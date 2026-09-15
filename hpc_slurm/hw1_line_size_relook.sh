#!/bin/bash
#
# hw1_line_size_relook.sh -- generic re-run of scripts/run_line_size.sh for
# specific level(s) on one Hazel generation, writing into a SEPARATE nested
# subdirectory under that machine's own data_raw/data_processed tree
# (data_raw/<machine>/line_size_rerun/line_size/..., via a MACHINE_ARG of the
# form "hazel_<gen>/line_size_rerun") rather than overwriting the original
# run's own level_<boundary>/ directories. The family-of-curves plots for
# several machines' L2/L3 levels didn't look clean on the first pass (see
# CLAUDE.md / each data_raw/<machine>/README.md's line_size/ section) -- the
# original data is kept as-is for comparison, not clobbered.
#
# One shared script for all 8 generations -- per-run specifics (constraint,
# machine/core, which boundary byte value(s) to re-test, output log paths)
# are passed via sbatch command-line overrides at submit time, e.g.:
#   sbatch --constraint=broadwell \
#     --output=data_raw/hazel_broadwell/hw1_line_size_relook_%j.log \
#     --error=data_raw/hazel_broadwell/hw1_line_size_relook_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_broadwell/line_size_rerun,CORE_ARG=22,BOUNDARIES_ARG=25874000 \
#     hpc_slurm/hw1_line_size_relook.sh
#
# Multi-boundary example (re-testing BOTH L2 and L3 in one job):
#   sbatch --constraint=genoa \
#     --output=data_raw/hazel_genoa/hw1_line_size_relook_%j.log \
#     --error=data_raw/hazel_genoa/hw1_line_size_relook_%j.err.log \
#     --export=ALL,MACHINE_ARG=hazel_genoa/line_size_rerun,CORE_ARG=6,BOUNDARIES_ARG=1048576+33554432 \
#     hpc_slurm/hw1_line_size_relook.sh
#
# BOUNDARIES_ARG uses '+' (NOT ',') to separate multiple boundary values --
# real bug found 2026-09-15: sbatch's --export parser splits its whole
# argument on top-level commas to find each NAME=VALUE pair, with no
# escaping/quoting for a comma that's meant to be part of one value. A
# first attempt at passing BOUNDARIES_ARG=<L2>,<L3> for the 4 generations
# needing both levels (genoa, icelake_8358, sapphirerapids, turin) had
# sbatch itself split that into "BOUNDARIES_ARG=<L2>" and a second,
# malformed "<L3>" token -- silently truncating BOUNDARIES_ARG to just the
# L2 value with no error, so L3 was never re-run in that first batch (caught
# only by noticing the missing level_<L3>/ output, then resubmitted
# separately per machine). '+' never collides with sbatch's own parsing, so
# this script now accepts it and converts back to the comma-separated form
# scripts/run_line_size.sh actually expects.
#
#SBATCH --job-name=hw1_ls_relook
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --partition=compute_partners

set -euo pipefail

: "${MACHINE_ARG:?must set MACHINE_ARG via --export, e.g. hazel_broadwell/line_size_rerun}"
: "${CORE_ARG:?must set CORE_ARG via --export}"
: "${BOUNDARIES_ARG:?must set BOUNDARIES_ARG via --export, e.g. 25874000 or 1048576+33554432 (use '+' to separate multiple boundaries -- see header comment)}"

# BOUNDARIES_ARG comes in '+'-separated (sbatch --export is comma-delimited
# at the top level, so a literal ',' here would get silently truncated --
# see header comment); run_line_size.sh itself wants the usual comma-separated form.
BOUNDARIES_CSV="${BOUNDARIES_ARG//+/,}"

echo "=== Machine identification (Phase Discipline whitelist only) ==="
hostname
uname -a
grep -m1 -E 'model name|Hardware|Processor' /proc/cpuinfo
echo "Assigned core (informational): ${CORE_ARG}, SLURM_JOB_ID=${SLURM_JOB_ID:-unset}"
echo

if ! git merge-base --is-ancestor predictions-frozen HEAD 2>/dev/null; then
  echo "predictions-frozen is NOT an ancestor of HEAD -- refusing to run." >&2
  exit 1
fi

source hpc_slurm/hazel_python_env.sh

echo "=== Running scripts/run_line_size.sh (HAZEL_MODE=1) for ${MACHINE_ARG}, boundaries=${BOUNDARIES_CSV} ==="
HAZEL_MODE=1 ./scripts/run_line_size.sh "${MACHINE_ARG}" "${CORE_ARG}" "${BOUNDARIES_CSV}"

echo
echo "=== Done ==="
