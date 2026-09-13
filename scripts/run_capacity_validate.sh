#!/bin/bash
#
# run_capacity_validate.sh -- targeted discrete-size boundary validation,
# complementing run_capacity_full.sh's log-spaced auto-detection sweep.
#
# run_capacity_full.sh's automatic detector (scripts/detect_cache_hierarchy.py)
# flags a knee from an 8-points-per-octave coarse sweep; on a wide/gradual
# transition (see CLAUDE.md's discussion of Sunbird's own detector output)
# a single reported boundary can actually be a waypoint partway up a ramp
# rather than a genuine flat-then-step edge, and a fixed 8-pts/octave grid
# can also straddle a real boundary without ever landing a point close
# enough to it (e.g. the expected 256 KiB L2 edge). This script instead
# tests a fixed, hand-picked list of exact working-set sizes bracketing
# each candidate boundary (below/near/above, closely spaced), with
# REPEATS independent repeats per size -- fresh malloc+warmup each time,
# a distinct seed per repeat (base_seed + repeat_index), matching the
# associativity pipeline's reproducibility convention (see CLAUDE.md's
# "Pipeline hardening" section) -- so a gradual-ramp candidate can be told
# apart from a genuine plateau/step using percentile spread across repeats,
# not just a single point estimate.
#
# Pattern is random only (the dependent pointer chase this experiment
# cares about); sequential is not run here since it's a prefetcher-sanity
# control for the main sweep pipeline, not part of this validation.
#
# No numactl on this checkout (not installed, no passwordless sudo to add
# it -- see data_raw/<machine>/README.md). Memory locality is still
# achieved without it: taskset is applied to the process *before* it mallocs
# or touches any node memory, and Linux's default NUMA policy allocates a
# faulted page on the local node of the faulting CPU -- since this is a
# single-threaded process pinned to one core for its entire lifetime
# (including the untimed warm-up passes that actually fault the pages in),
# every page lands on that core's own node under the default policy with no
# explicit --membind needed. This is *not* independently verified via
# /proc/<pid>/numa_maps in this run -- flag that gap in the README the same
# way Skylark's/Upgrade's capacity READMEs flag their own NUMA-pinning gaps
# if this matters later.
#
# Usage:
#   ./scripts/run_capacity_validate.sh <machine> <core> <group> [group...]
#   groups: l1d l2 l3 dram all
#
# Example:
#   ./scripts/run_capacity_validate.sh sunbird 6 all
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <group> [group...]  (groups: l1d l2 l3 dram all)" >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
shift 2
RUN_GROUPS=("$@")

SAMPLES=1000000
BATCH=1000
WARMUP=3
BASE_SEED=12345
REPEATS=5   # independent repeats per size, per the task spec ("at least five")
PATTERN=random

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ---- candidate working-set sizes, in bytes ----
# Chosen for this machine's expected hierarchy (32 KiB L1D / 256 KiB L2 /
# 30 MiB shared L3 per socket, per a dual-socket Xeon E5-2680 v3) -- edit
# these arrays for a different chip's expected sizes.
L1D_BYTES=(16384 24576 28672 32768 36864 40960 49152 65536)
L2_BYTES=(131072 196608 229376 262144 294912 327680 393216 524288)
# Includes 26999993 (25.7492 MiB), the previously-reported candidate
# boundary being re-tested here, bracketed by round MiB neighbors on both
# sides so a ramp vs. a genuine step can be told apart.
L3_BYTES=(16777216 20971520 25165824 26999993 29360128 31457280 33554432 37748736 41943040 50331648 67108864)
# Includes 149999845 (143.051 MiB), the other previously-reported candidate
# being re-tested here (already closely bracketed by 128/160 MiB).
DRAM_BYTES=(100663296 134217728 149946368 149999845 167772160 268435456)

RAW_DIR="data_raw/${MACHINE}/capacity_validate"
PROC_DIR="data_processed/${MACHINE}/capacity_validate"
mkdir -p "$RAW_DIR" "$PROC_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_DIR}/run_capacity_validate_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_capacity_validate: machine=${MACHINE} core=${CORE} groups=${RUN_GROUPS[*]} =="
echo "== base_seed=${BASE_SEED} repeats=${REPEATS} samples=${SAMPLES} pattern=${PATTERN} =="
echo "== timestamp=${TS} =="

make -s

# Throwaway warm-up invocation (discarded): the very first cache_bench
# process launched in a session can run a bit slower than steady state
# before the core settles into turbo -- the same CPU-frequency-ramp-up
# effect documented in CLAUDE.md for dense sweeps started right at a
# region's left edge (confirmed on Sunbird there: a false "shelf" from a
# cold start, resolved by starting further back). One untimed-for-our-
# purposes run here absorbs that ramp-up before any real per-size data is
# recorded, instead of leaving the very first size point of the first
# group contaminated by it.
echo "-- warm-up pass (discarded) --"
taskset -c "$CORE" ./cache_bench --experiment capacity --pattern "$PATTERN" \
  --samples 200000 --batch-size 1000 \
  --min-bytes 1048576 --max-bytes 1048576 --points-per-octave 1 \
  --warmup-passes "$WARMUP" --seed "$BASE_SEED" > /dev/null

run_point() {
  # run_point <bytes> <seed> <out_csv>  (appends; caller writes the header once)
  local bytes="$1" seed="$2" out="$3"
  taskset -c "$CORE" ./cache_bench --experiment capacity --pattern "$PATTERN" \
    --samples "$SAMPLES" --batch-size "$BATCH" \
    --min-bytes "$bytes" --max-bytes "$bytes" --points-per-octave 1 \
    --warmup-passes "$WARMUP" --seed "$seed" >> "$out"
}

run_group() {
  # run_group <name> <bytes...>
  local name="$1"; shift
  local sizes=("$@")
  local raw="${RAW_DIR}/capacity_validate_${name}_${PATTERN}_${TS}.csv"
  : > "$raw"
  local header_written=0
  for bytes in "${sizes[@]}"; do
    for r in $(seq 0 $((REPEATS - 1))); do
      seed=$((BASE_SEED + r))
      echo "-- group=${name} bytes=${bytes} repeat=${r} seed=${seed} --"
      if [ "$header_written" -eq 0 ]; then
        run_point "$bytes" "$seed" "$raw"
        header_written=1
      else
        # cache_bench re-prints its own '#'-comment header and CSV header
        # line every invocation; strip both so repeated appends to the
        # same file stay parseable by summarize_raw.py, which skips '#'
        # lines but not a second literal CSV header row.
        tmp="$(mktemp)"
        run_point "$bytes" "$seed" "$tmp"
        grep -v '^size_bytes,num_nodes,pattern,batch_index,avg_ticks_per_access$' "$tmp" >> "$raw"
        rm -f "$tmp"
      fi
    done
  done
  echo "  wrote $(wc -l < "$raw") lines -> $raw"
  local sum="${PROC_DIR}/${name}_summary.csv"
  python3 scripts/summarize_raw.py "$raw" -o "$sum" >/dev/null
  echo "  summary -> $sum"
}

for g in "${RUN_GROUPS[@]}"; do
  case "$g" in
    l1d) run_group l1d "${L1D_BYTES[@]}" ;;
    l2)  run_group l2 "${L2_BYTES[@]}" ;;
    l3)  run_group l3 "${L3_BYTES[@]}" ;;
    dram) run_group dram "${DRAM_BYTES[@]}" ;;
    all)
      run_group l1d "${L1D_BYTES[@]}"
      run_group l2 "${L2_BYTES[@]}"
      run_group l3 "${L3_BYTES[@]}"
      run_group dram "${DRAM_BYTES[@]}"
      ;;
    *) echo "Unknown group '$g' (expected l1d|l2|l3|dram|all)" >&2; exit 1 ;;
  esac
done

echo "-- compressing raw CSVs --"
gzip -f "${RAW_DIR}"/capacity_validate_*.csv

echo "== done =="
echo "== summaries: ${PROC_DIR}/{l1d,l2,l3,dram}_summary.csv (whichever groups were run) =="
echo "== full transcript saved to: ${LOG} =="
