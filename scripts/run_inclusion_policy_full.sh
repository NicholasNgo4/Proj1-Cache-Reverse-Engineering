#!/bin/bash
#
# run_inclusion_policy_full.sh -- one-command Phase-I inclusion/exclusion
# pipeline for one machine, per (upper level, lower level) pairing:
# single-shot "survived" calibration -> main eviction sweep (both eviction-
# set traversal patterns, base + 2 repeats) -> classification against this
# machine's own single-shot calibration -> plots.
#
# See main_code/common/inclusion_policy.h for the full method rationale
# (why the eviction buffer uses a page-multiple stride + fixed sub-page
# offset instead of a dense buffer) and its KNOWN LIMITATION paragraphs --
# read those before trusting a result out of this script. Two load-bearing
# caveats repeated here because they directly shape this script's behavior:
#
# 1. ASSUMED LINE SIZE. The eviction buffer touches exactly one cache line
#    per PAGE (see inclusion_policy.h), so for a given byte footprint it
#    touches far fewer distinct lines than a dense buffer would -- to exert
#    capacity-COMPARABLE pressure on the lower level, this script scales
#    the lower level's real byte capacity up by (evict_stride_bytes /
#    ASSUMED_LINE_SIZE_BYTES) before passing it as --evict-bytes.
#    ASSUMED_LINE_SIZE_BYTES=64 below is a DOCUMENTED ASSUMPTION (the most
#    common modern line size), NOT a measured value -- line_size data for
#    this machine was not available when this script was written. If the
#    real line size is smaller (e.g. 32 B), this UNDERSTATES the needed
#    eviction footprint. Once real line_size data exists for this machine,
#    recompute and re-run rather than trusting this default blindly.
# 2. SINGLE-SHOT / TLB CONFOUND. A large scaled eviction footprint touches
#    many thousands of distinct pages, which can blow the DTLB regardless
#    of any real cache-level eviction -- this shows up as the CONTROL
#    channel (never touched by the eviction walk by construction) reading
#    slower than its own small-scale calibration baseline. This script's
#    classify step reports that explicitly and downgrades the verdict to
#    UNCERTAIN when it looks confound-suspected; it does not try to fix it
#    (e.g. via huge pages) -- that is documented, flagged future work, not
#    solved here.
#
# Usage:
#   ./scripts/run_inclusion_policy_full.sh <machine> <core> \
#       <label>:<target_bytes>:<lower_level_bytes>:<invalidated_transition>[,...]
#
#   target_bytes         -- UPPER level's capacity (e.g. L1, from CAPACITY_RESULTS.md).
#                            Must fit within one page's worth of index range for the
#                            avoidance construction to be meaningful (true for a typical
#                            L1; NOT reliable for an L2-or-bigger target, see
#                            inclusion_policy.h).
#   lower_level_bytes     -- the LOWER level's real byte capacity (e.g. LLC, from
#                            CAPACITY_RESULTS.md) -- this script scales it up internally
#                            (see caveat 1 above), do not pre-scale it yourself.
#   invalidated_transition -- the name of an ALREADY-COLLECTED miss_latency transition
#                            folder (data_processed/<machine>/latency/miss/<name>/) whose
#                            median single-shot reload cost represents "evicted beyond the
#                            lower level" (e.g. LLC_to_DRAM if lower_level_bytes is LLC).
#                            Run scripts/run_miss_latency_full.sh first if it doesn't
#                            exist yet -- this script does NOT auto-generate it.
#
# Example:
#   ./scripts/run_inclusion_policy_full.sh sunbird 2 L1_vs_LLC:32768:31457280:LLC_to_DRAM
#
# Output:
#   data_raw/<machine>/inclusion_policy/<label>/*.csv[.gz]
#   data_processed/<machine>/inclusion_policy/<label>/*_summary_<ts>.csv
#   data_processed/<machine>/inclusion_policy/<label>/plots/inclusion_policy_boxplots.{png,pdf}
#   data_processed/<machine>/inclusion_policy/<label>/classification_<ts>.txt
#   data_raw/<machine>/inclusion_policy/run_inclusion_policy_full_<ts>.log
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <label>:<target_bytes>:<lower_level_bytes>:<invalidated_transition>[,...]" >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
SPEC_CSV="$3"

SAMPLES=200            # single-shot trials -- same order of magnitude as miss_latency,
                        # see its own header comment for why this isn't 1,000,000
CAL_SAMPLES=500         # calibration run trials (cheap -- trivially small evict_bytes)
WARMUP=3
SEED=12345
REPEATS=2
EVICT_STRIDE_BYTES=4096
EVICT_OFFSET_BYTES=2048
ASSUMED_LINE_SIZE_BYTES=64   # see caveat 1 above -- DOCUMENTED ASSUMPTION, not measured

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/inclusion_policy"
PROC_ROOT="data_processed/${MACHINE}/inclusion_policy"
mkdir -p "$RAW_ROOT" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_ROOT}/run_inclusion_policy_full_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_inclusion_policy_full: machine=${MACHINE} core=${CORE} base_seed=${SEED} =="
echo "== assumed_line_size_bytes=${ASSUMED_LINE_SIZE_BYTES} (documented assumption, not measured) =="
echo "== timestamp=${TS} =="

make -s

run_sweep() {
  # run_sweep <pattern> <target_bytes> <evict_bytes> <out_csv> [seed]
  local pattern="$1" target="$2" evict="$3" out="$4" seed="${5:-$SEED}"
  taskset -c "$CORE" ./cache_bench --experiment inclusion_policy --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size 1 --target-bytes "$target" --evict-bytes "$evict" \
    --evict-stride-bytes "$EVICT_STRIDE_BYTES" --evict-offset-bytes "$EVICT_OFFSET_BYTES" \
    --warmup-passes "$WARMUP" --seed "$seed" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out (pattern=${pattern} seed=${seed})"
}

summarize() {
  python3 scripts/summarize_raw.py "$1" -o "$2" >/dev/null
}

RESULTS=()

IFS=',' read -r -a SPECS <<< "$SPEC_CSV"
for spec in "${SPECS[@]}"; do
  IFS=':' read -r LABEL TARGET_BYTES LOWER_BYTES INVAL_TRANSITION <<< "$spec"
  if [ -z "$LABEL" ] || [ -z "$TARGET_BYTES" ] || [ -z "$LOWER_BYTES" ] || [ -z "$INVAL_TRANSITION" ]; then
    echo "ERROR: malformed spec '${spec}' (expected <label>:<target_bytes>:<lower_level_bytes>:<invalidated_transition>)" >&2
    exit 1
  fi

  EVICT_BYTES=$(( LOWER_BYTES * EVICT_STRIDE_BYTES / ASSUMED_LINE_SIZE_BYTES ))

  RAW_DIR="${RAW_ROOT}/${LABEL}"
  PROC_DIR="${PROC_ROOT}/${LABEL}"
  PLOT_DIR="${PROC_DIR}/plots"
  mkdir -p "$RAW_DIR" "$PROC_DIR" "$PLOT_DIR"

  echo ""
  echo "== ${LABEL}: target_bytes=${TARGET_BYTES} lower_level_bytes=${LOWER_BYTES} -> evict_bytes=${EVICT_BYTES} (scaled ${EVICT_STRIDE_BYTES}/${ASSUMED_LINE_SIZE_BYTES}x) =="

  # ---- step 1: single-shot "survived" calibration (trivially small
  # evict_bytes -- nothing should be evicted). Uses target's own footprint
  # as the (harmless) eviction size, matching the diagnostic already used
  # to characterize miss_latency's single-shot overhead on this machine. ----
  echo "-- survived-class calibration (evict_bytes=target_bytes, nothing evicted) --"
  CAL_OUT="${RAW_DIR}/inclusion_policy_calibration_${TS}.csv"
  taskset -c "$CORE" ./cache_bench --experiment inclusion_policy --pattern random \
    --samples "$CAL_SAMPLES" --batch-size 1 --target-bytes "$TARGET_BYTES" \
    --evict-bytes "$TARGET_BYTES" --evict-stride-bytes "$EVICT_STRIDE_BYTES" \
    --evict-offset-bytes "$EVICT_OFFSET_BYTES" --warmup-passes "$WARMUP" --seed "$SEED" \
    > "$CAL_OUT"
  SURVIVED_TICKS=$(grep -v '^#' "$CAL_OUT" | awk -F, 'NR>1 && $6=="control"{sum+=$8;n++} END{if(n>0) print sum/n; else print "0"}')
  echo "  survived-class (single-shot, calibrated here): ${SURVIVED_TICKS} ticks"

  # ---- step 2: look up the invalidated-class calibration from this
  # machine's own already-collected miss_latency data. ----
  INVAL_SUM_GLOB="data_processed/${MACHINE}/latency/miss/${INVAL_TRANSITION}"/base_random_summary_*.csv
  INVAL_SUM=""
  for f in $INVAL_SUM_GLOB; do [ -f "$f" ] && INVAL_SUM="$f" && break; done
  if [ -z "$INVAL_SUM" ]; then
    echo "ERROR: no miss_latency summary found for transition '${INVAL_TRANSITION}' under" >&2
    echo "       data_processed/${MACHINE}/latency/miss/${INVAL_TRANSITION}/ -- run" >&2
    echo "       scripts/run_miss_latency_full.sh for this machine first." >&2
    exit 1
  fi
  INVALIDATED_TICKS=$(python3 -c "import csv; print(list(csv.DictReader(open('${INVAL_SUM}')))[0]['median'])")
  echo "  invalidated-class (from ${INVAL_SUM}): ${INVALIDATED_TICKS} ticks"

  # ---- step 3: main eviction sweep, base + repeats, both patterns ----
  ALL_SUMMARIES=()
  for run_tag in base rep1 rep2; do
    if [ "$run_tag" = "base" ]; then SEED_THIS="$SEED"; else
      r="${run_tag#rep}"; [ "$r" -gt "$REPEATS" ] && continue
      SEED_THIS=$((SEED + r))
    fi
    echo "-- ${run_tag} (seed=${SEED_THIS}) --"
    for pattern in random sequential; do
      OUT="${RAW_DIR}/inclusion_policy_${run_tag}_${pattern}_${TS}.csv"
      SUM="${PROC_DIR}/${run_tag}_${pattern}_summary_${TS}.csv"
      run_sweep "$pattern" "$TARGET_BYTES" "$EVICT_BYTES" "$OUT" "$SEED_THIS"
      summarize "$OUT" "$SUM"
      ALL_SUMMARIES+=("$SUM")
    done
  done

  # ---- step 4: classification (from the BASE random run's raw data --
  # the repeats are for reproducibility evidence in the plot, not folded
  # into the classification fractions) ----
  BASE_RAW="${RAW_DIR}/inclusion_policy_base_random_${TS}.csv"
  CLASS_OUT="${PROC_DIR}/classification_${TS}.txt"
  python3 scripts/classify_inclusion_policy.py "$BASE_RAW" \
    --survived-ticks "$SURVIVED_TICKS" --invalidated-ticks "$INVALIDATED_TICKS" \
    | tee "$CLASS_OUT"
  VERDICT_LINE=$(grep '^VERDICT:' "$CLASS_OUT" || echo "VERDICT: (none)")

  # ---- step 5: plots ----
  echo "-- generating plots for ${LABEL} --"
  python3 scripts/plot_inclusion_policy.py \
    "${ALL_SUMMARIES[@]}" \
    -o "$PLOT_DIR" --machine "$MACHINE" --label "$LABEL" \
    --title-suffix "(Phase I timing-only, auto pipeline)" \
    --survived-ticks "$SURVIVED_TICKS" --invalidated-ticks "$INVALIDATED_TICKS"

  echo "-- compressing raw CSVs for ${LABEL} --"
  gzip -f "${RAW_DIR}"/inclusion_policy_*.csv

  RESULTS+=("${LABEL}: ${VERDICT_LINE}")
done

echo ""
echo "== done =="
for r in "${RESULTS[@]}"; do
  echo "== ${r} =="
done
echo "== record in data_raw/${MACHINE}/README.md: core=${CORE}, base_seed=${SEED} (repeats use base_seed+index)," \
     "trials=${SAMPLES}, assumed_line_size_bytes=${ASSUMED_LINE_SIZE_BYTES}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
