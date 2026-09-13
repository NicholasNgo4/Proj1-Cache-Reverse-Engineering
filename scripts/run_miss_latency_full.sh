#!/bin/bash
#
# run_miss_latency_full.sh -- one-command Phase-I miss/next-level-latency
# pipeline for one machine, per source->destination cache-level transition:
# base sweep (both eviction-set traversal patterns) -> reproducibility
# repeats -> plots (annotated with the incremental miss penalty, if a
# matching hit_latency run for the source level already exists).
#
# Mirrors run_associativity_full.sh / run_hit_latency_full.sh's philosophy:
# deliberately NOT adaptive, no auto-detection exists here at all --
# target_bytes and evict_bytes MUST both be hand-confirmed capacity
# boundaries from that machine's own data_raw/<machine>/README.md, passed
# explicitly (see main_code/common/latency.h's docstring for exactly what
# each must satisfy: target_bytes inside the SOURCE level, evict_bytes past
# the source level's capacity but inside the NEXT level's).
#
# Usage:
#   ./scripts/run_miss_latency_full.sh <machine> <core> <transition>:<target_bytes>:<evict_bytes>[,...]
#
# Example:
#   ./scripts/run_miss_latency_full.sh sunbird 2 L1_to_LLC:32768:27262976
#
# Naming convention: name each transition <SOURCE>_to_<DEST> (matching the
# level names run_hit_latency_full.sh/run_associativity_full.sh use, e.g.
# L1, L2, L3_LLC/LLC, DRAM) -- this script looks for a matching completed
# hit_latency run under data_processed/<machine>/latency/hit/<SOURCE>/ to
# annotate the incremental miss penalty on the plot; if none is found yet,
# the plot is still produced, just without that annotation.
#
# Output:
#   data_raw/<machine>/latency/miss/<transition>/*.csv          raw per-trial samples
#   data_processed/<machine>/latency/miss/<transition>/*.csv    per-pattern distribution
#                                                                 summaries, timestamped per run
#   data_processed/<machine>/latency/miss/<transition>/plots/   miss_latency_boxplots (png+pdf)
#   data_raw/<machine>/latency/run_miss_latency_full_<ts>.log   full transcript of this run
#
# After it finishes, fill in data_raw/<machine>/README.md's latency/ section
# using the machine/core/seed/timestamp/target/evict values printed at the
# end for each transition.
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <transition>:<target_bytes>:<evict_bytes>[,...]" >&2
  echo "       target_bytes and evict_bytes MUST both be hand-confirmed capacity" >&2
  echo "       boundaries -- see data_raw/<machine>/README.md's capacity section and" >&2
  echo "       main_code/common/latency.h's docstring. No auto-detection exists for" >&2
  echo "       this experiment." >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
TRANSITION_SPEC_CSV="$3"

SAMPLES=200     # trial count: each sample is one single-shot reload, not a batch
                # average, so this is much smaller than the batched experiments'
                # 1,000,000 -- the full eviction-set walk re-runs untimed on EVERY
                # trial (see main_code/common/latency.c), so wall time scales with
                # samples * evict_bytes, and NOT linearly at that -- measured on
                # Sunbird (core 2, random pattern): ~74ms/trial at a 27 MiB eviction
                # set but ~604ms/trial at 64 MiB (8x the bytes but >2x the per-trial
                # cost the eviction-set size alone would predict, plausibly growing
                # TLB pressure as the walk spans more pages -- not investigated
                # further here). At 200 trials that's ~15s and ~120s per (pattern,
                # run) respectively; a many-hundred-MiB eviction set (e.g. testing
                # well past a large LLC) should be re-timed by hand first and run
                # inside tmux per this project's established long-sweep convention
                # (see CLAUDE.md's "Known constraints" section) if it's likely to
                # run past your session.
WARMUP=3
SEED=12345
REPEATS=2

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/latency/miss"
PROC_ROOT="data_processed/${MACHINE}/latency/miss"
mkdir -p "$RAW_ROOT" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="data_raw/${MACHINE}/latency/run_miss_latency_full_${TS}.log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

echo "== run_miss_latency_full: machine=${MACHINE} core=${CORE} base_seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

run_sweep() {
  # run_sweep <pattern> <target_bytes> <evict_bytes> <out_csv> [seed]
  local pattern="$1" target="$2" evict="$3" out="$4" seed="${5:-$SEED}"
  # --batch-size is meaningless to miss_latency itself (ml_cfg has no such
  # field -- every trial is its own single-shot timed access, see
  # main_code/common/latency.c), but --samples is a flag main.c broadcasts
  # to every experiment's config struct, including capacity/line_size/
  # associativity's, and their own validation unconditionally requires
  # samples >= batch_size regardless of which --experiment was actually
  # selected. Pass --batch-size 1 explicitly so that cross-check can't fail
  # just because SAMPLES here is deliberately much smaller than those other
  # experiments' defaults.
  taskset -c "$CORE" ./cache_bench --experiment miss_latency --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size 1 --target-bytes "$target" --evict-bytes "$evict" \
    --warmup-passes "$WARMUP" --seed "$seed" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out (pattern=${pattern} seed=${seed})"
}

summarize() {
  python3 scripts/summarize_raw.py "$1" -o "$2" >/dev/null
}

RESULTS=()

IFS=',' read -r -a TRANSITION_SPECS <<< "$TRANSITION_SPEC_CSV"
for spec in "${TRANSITION_SPECS[@]}"; do
  IFS=':' read -r TRANSITION TARGET_BYTES EVICT_BYTES <<< "$spec"
  if [ -z "$TRANSITION" ] || [ -z "$TARGET_BYTES" ] || [ -z "$EVICT_BYTES" ]; then
    echo "ERROR: malformed transition spec '${spec}' (expected <transition>:<target_bytes>:<evict_bytes>)" >&2
    exit 1
  fi

  RAW_DIR="${RAW_ROOT}/${TRANSITION}"
  PROC_DIR="${PROC_ROOT}/${TRANSITION}"
  PLOT_DIR="${PROC_DIR}/plots"
  mkdir -p "$RAW_DIR" "$PROC_DIR" "$PLOT_DIR"

  echo ""
  echo "== transition ${TRANSITION}: target_bytes=${TARGET_BYTES} evict_bytes=${EVICT_BYTES} =="

  ALL_SUMMARIES=()

  for run_tag in base rep1 rep2; do
    if [ "$run_tag" = "base" ]; then
      SEED_THIS="$SEED"
    else
      r="${run_tag#rep}"
      [ "$r" -gt "$REPEATS" ] && continue
      SEED_THIS=$((SEED + r))
    fi
    echo "-- ${run_tag} (seed=${SEED_THIS}) --"
    for pattern in random sequential; do
      OUT="${RAW_DIR}/miss_latency_${run_tag}_${pattern}_${TS}.csv"
      SUM="${PROC_DIR}/${run_tag}_${pattern}_summary_${TS}.csv"
      run_sweep "$pattern" "$TARGET_BYTES" "$EVICT_BYTES" "$OUT" "$SEED_THIS"
      summarize "$OUT" "$SUM"
      ALL_SUMMARIES+=("$SUM")
    done
  done

  # ---- look for a matching hit_latency run for the source level (the part
  # of the transition name before the first "_to_") to annotate the
  # incremental miss penalty. Not fatal if missing -- plot_miss_latency.py
  # just skips the annotation. ----
  SOURCE_LEVEL="${TRANSITION%%_to_*}"
  HIT_SUM_GLOB="data_processed/${MACHINE}/latency/hit/${SOURCE_LEVEL}"/*_dependent_random_summary_*.csv
  HIT_SUM_ARGS=()
  for f in $HIT_SUM_GLOB; do
    [ -f "$f" ] && HIT_SUM_ARGS+=("$f")
  done
  if [ "${#HIT_SUM_ARGS[@]}" -gt 0 ]; then
    echo "-- found source-level (${SOURCE_LEVEL}) hit_latency data for penalty annotation: ${HIT_SUM_ARGS[*]} --"
  else
    echo "-- no source-level (${SOURCE_LEVEL}) hit_latency data found under data_processed/${MACHINE}/latency/hit/${SOURCE_LEVEL}/ -- plotting without the incremental-penalty annotation --"
  fi

  echo "-- generating plots for ${TRANSITION} --"
  PLOT_ARGS=()
  [ "${#HIT_SUM_ARGS[@]}" -gt 0 ] && PLOT_ARGS=(--hit-latency-summary "${HIT_SUM_ARGS[@]}")
  python3 scripts/plot_miss_latency.py \
    "${ALL_SUMMARIES[@]}" \
    -o "$PLOT_DIR" --machine "$MACHINE" --transition "$TRANSITION" \
    --title-suffix "(Phase I timing-only, auto pipeline)" \
    "${PLOT_ARGS[@]}"

  echo "-- compressing raw CSVs for ${TRANSITION} --"
  gzip -f "${RAW_DIR}"/miss_latency_*.csv

  RESULTS+=("${TRANSITION}: target_bytes=${TARGET_BYTES} evict_bytes=${EVICT_BYTES}")
done

echo ""
echo "== done =="
for r in "${RESULTS[@]}"; do
  echo "== ${r} =="
done
echo "== record in data_raw/${MACHINE}/README.md: core=${CORE}, base_seed=${SEED} (repeats use base_seed+index)," \
     "trials=${SAMPLES}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
