#!/bin/bash
#
# run_capacity_full.sh -- one-command Phase-I capacity pipeline for one
# machine: coarse sweep -> automatic boundary detection -> dense sweep
# bracketing each detected boundary -> reproducibility repeats on the
# deepest boundary -> a fixed-ratio tail-extension sweep to check for a
# plateau beyond the coarse ceiling -> combined plots.
#
# This is deliberately NOT adaptive (no "did it plateau, should I extend
# further?" loop). Every step is a fixed rule learned from doing this by
# hand on Sunbird, applied uniformly so it doesn't need per-machine
# judgment calls or debugging: a 4x tail extension beyond the coarse
# ceiling (memory-safety clamped), a +-3 octave dense window around each
# auto-detected boundary, and 2 extra independent repeats only on the
# deepest boundary's window, since that's the one that turned out
# ambiguous on Sunbird. If a machine's result still looks unresolved after
# this, that's a single targeted manual follow-up for that machine, not a
# reason to add more adaptive logic here.
#
# Usage:
#   ./scripts/run_capacity_full.sh <machine> <core> [coarse_max_bytes]
#
# Example:
#   ./scripts/run_capacity_full.sh artemisia 4
#   ./scripts/run_capacity_full.sh charnwood 2 33554432   # smaller desktop chip, 32 MiB coarse ceiling
#
# Output:
#   data_raw/<machine>/capacity/*.csv            raw per-batch samples
#   data_processed/<machine>/capacity/*.csv      per-size distribution summaries
#   data_processed/<machine>/capacity/plots/     capacity_curve + capacity_boxplots (png+pdf)
#   data_raw/<machine>/capacity/run_capacity_full_<ts>.log   full transcript of this run
#
# After it finishes, fill in data_raw/<machine>/README.md using the
# machine/core/seed/timestamp/boundaries printed at the end.
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <machine> <core> [coarse_max_bytes]" >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
COARSE_MAX="${3:-67108864}"   # default 64 MiB
COARSE_MIN=1024
SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
PPO_COARSE=8
PPO_DENSE=48
REPEATS=2                     # extra independent repeats on the deepest boundary's window

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_DIR="data_raw/${MACHINE}/capacity"
PROC_DIR="data_processed/${MACHINE}/capacity"
PLOT_DIR="${PROC_DIR}/plots"
mkdir -p "$RAW_DIR" "$PROC_DIR" "$PLOT_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_DIR}/run_capacity_full_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_capacity_full: machine=${MACHINE} core=${CORE} coarse_max=${COARSE_MAX} seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

run_sweep() {
  # run_sweep <pattern> <min_bytes> <max_bytes> <points_per_octave> <out_csv>
  local pattern="$1" min="$2" max="$3" ppo="$4" out="$5"
  taskset -c "$CORE" ./cache_bench --experiment capacity --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size "$BATCH" \
    --min-bytes "$min" --max-bytes "$max" --points-per-octave "$ppo" \
    --warmup-passes "$WARMUP" --seed "$SEED" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out"
}

summarize() {
  python3 scripts/summarize_raw.py "$1" -o "$2" >/dev/null
}

ALL_SUMMARIES=()

# ---- coarse sweep ----
echo "-- coarse sweep ${COARSE_MIN}-${COARSE_MAX} bytes --"
COARSE_R="${RAW_DIR}/capacity_coarse_random_${TS}.csv"
COARSE_S="${RAW_DIR}/capacity_coarse_sequential_${TS}.csv"
run_sweep random "$COARSE_MIN" "$COARSE_MAX" "$PPO_COARSE" "$COARSE_R"
run_sweep sequential "$COARSE_MIN" "$COARSE_MAX" "$PPO_COARSE" "$COARSE_S"
COARSE_R_SUM="${PROC_DIR}/coarse_random_summary.csv"
COARSE_S_SUM="${PROC_DIR}/coarse_sequential_summary.csv"
summarize "$COARSE_R" "$COARSE_R_SUM"
summarize "$COARSE_S" "$COARSE_S_SUM"
ALL_SUMMARIES+=("$COARSE_R_SUM" "$COARSE_S_SUM")

# ---- fixed-ratio tail-extension sweep beyond the coarse ceiling ----
# Memory safety clamp: never let the tail exceed 25% of currently available RAM.
MEM_AVAIL_KB=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
MEM_AVAIL_BYTES=$((MEM_AVAIL_KB * 1024))
SAFE_CAP=$((MEM_AVAIL_BYTES / 4))
TAIL_MAX=$((COARSE_MAX * 4))
if [ "$TAIL_MAX" -gt "$SAFE_CAP" ]; then
  echo "  (clamping tail-extension ceiling from ${TAIL_MAX} to ${SAFE_CAP} bytes: 25% of available RAM)"
  TAIL_MAX="$SAFE_CAP"
fi

TAIL_R_SUM=""
if [ "$TAIL_MAX" -gt "$COARSE_MAX" ]; then
  echo "-- tail-extension sweep ${COARSE_MAX}-${TAIL_MAX} bytes --"
  TAIL_R="${RAW_DIR}/capacity_coarse_ext_random_${TS}.csv"
  TAIL_S="${RAW_DIR}/capacity_coarse_ext_sequential_${TS}.csv"
  run_sweep random "$COARSE_MAX" "$TAIL_MAX" "$PPO_COARSE" "$TAIL_R"
  run_sweep sequential "$COARSE_MAX" "$TAIL_MAX" "$PPO_COARSE" "$TAIL_S"
  TAIL_R_SUM="${PROC_DIR}/coarse_ext_random_summary.csv"
  TAIL_S_SUM="${PROC_DIR}/coarse_ext_sequential_summary.csv"
  summarize "$TAIL_R" "$TAIL_R_SUM"
  summarize "$TAIL_S" "$TAIL_S_SUM"
  ALL_SUMMARIES+=("$TAIL_R_SUM" "$TAIL_S_SUM")
else
  echo "-- skipping tail-extension sweep (available RAM too limited relative to coarse_max) --"
fi

# ---- automatic boundary detection on the combined random-pattern data ----
COMBINED_SUM="${PROC_DIR}/coarse_combined_random_summary.csv"
{
  head -1 "$COARSE_R_SUM"
  tail -n +2 "$COARSE_R_SUM"
  if [ -n "$TAIL_R_SUM" ]; then tail -n +2 "$TAIL_R_SUM"; fi
} > "$COMBINED_SUM"

mapfile -t BOUNDARIES < <(python3 scripts/detect_cache_hierarchy.py "$COMBINED_SUM" --machine-readable || true)
echo "-- detected boundaries (bytes): ${BOUNDARIES[*]:-none} --"

# ---- dense sweep bracketing each detected boundary (+-3 octaves) ----
BOUNDARY_ARGS=()
LAST_IDX=$((${#BOUNDARIES[@]} - 1))
for i in "${!BOUNDARIES[@]}"; do
  B="${BOUNDARIES[$i]}"
  DMIN=$((B / 8)); if [ "$DMIN" -lt 1024 ]; then DMIN=1024; fi
  DMAX=$((B * 8)); if [ "$DMAX" -gt "$TAIL_MAX" ]; then DMAX="$TAIL_MAX"; fi
  if [ "$DMAX" -le "$DMIN" ]; then
    echo "-- skipping dense sweep for boundary ${B} (degenerate range ${DMIN}-${DMAX}) --"
    continue
  fi
  echo "-- dense sweep around boundary ${B} bytes: ${DMIN}-${DMAX} --"
  DR="${RAW_DIR}/capacity_dense${i}_random_${TS}.csv"
  DS="${RAW_DIR}/capacity_dense${i}_sequential_${TS}.csv"
  run_sweep random "$DMIN" "$DMAX" "$PPO_DENSE" "$DR"
  run_sweep sequential "$DMIN" "$DMAX" "$PPO_DENSE" "$DS"
  DR_SUM="${PROC_DIR}/dense${i}_random_summary.csv"
  DS_SUM="${PROC_DIR}/dense${i}_sequential_summary.csv"
  summarize "$DR" "$DR_SUM"; summarize "$DS" "$DS_SUM"
  ALL_SUMMARIES+=("$DR_SUM" "$DS_SUM")
  BOUNDARY_ARGS+=(--boundary "${B}")

  if [ "$i" -eq "$LAST_IDX" ]; then
    for r in $(seq 1 "$REPEATS"); do
      echo "  -- repeat ${r}/${REPEATS} of deepest boundary's dense window --"
      RR="${RAW_DIR}/capacity_dense${i}_rep${r}_random_${TS}.csv"
      RS="${RAW_DIR}/capacity_dense${i}_rep${r}_sequential_${TS}.csv"
      run_sweep random "$DMIN" "$DMAX" "$PPO_DENSE" "$RR"
      run_sweep sequential "$DMIN" "$DMAX" "$PPO_DENSE" "$RS"
      RR_SUM="${PROC_DIR}/dense${i}_rep${r}_random_summary.csv"
      RS_SUM="${PROC_DIR}/dense${i}_rep${r}_sequential_summary.csv"
      summarize "$RR" "$RR_SUM"; summarize "$RS" "$RS_SUM"
      ALL_SUMMARIES+=("$RR_SUM" "$RS_SUM")
    done
  fi
done

# ---- dense-sample past the deepest boundary, looking for a further plateau ----
if [ -n "$TAIL_R_SUM" ] && [ "${#BOUNDARIES[@]}" -gt 0 ]; then
  LAST_B="${BOUNDARIES[$LAST_IDX]}"
  TDMIN=$((LAST_B * 2)); if [ "$TDMIN" -lt "$COARSE_MAX" ]; then TDMIN="$COARSE_MAX"; fi
  TDMAX="$TAIL_MAX"
  if [ "$TDMAX" -gt "$TDMIN" ]; then
    echo "-- dense sweep past deepest boundary, checking for a further plateau: ${TDMIN}-${TDMAX} --"
    ER="${RAW_DIR}/capacity_denseTail_random_${TS}.csv"
    ES="${RAW_DIR}/capacity_denseTail_sequential_${TS}.csv"
    run_sweep random "$TDMIN" "$TDMAX" "$PPO_DENSE" "$ER"
    run_sweep sequential "$TDMIN" "$TDMAX" "$PPO_DENSE" "$ES"
    ER_SUM="${PROC_DIR}/denseTail_random_summary.csv"
    ES_SUM="${PROC_DIR}/denseTail_sequential_summary.csv"
    summarize "$ER" "$ER_SUM"; summarize "$ES" "$ES_SUM"
    ALL_SUMMARIES+=("$ER_SUM" "$ES_SUM")
  fi
fi

# ---- plots ----
echo "-- generating plots --"
python3 scripts/plot_capacity.py \
  "${ALL_SUMMARIES[@]}" \
  -o "$PLOT_DIR" --machine "$MACHINE" \
  --title-suffix "(Phase I timing-only, auto pipeline)" \
  "${BOUNDARY_ARGS[@]}"

echo "== done =="
echo "== plots: ${PLOT_DIR}/capacity_curve.{png,pdf}, ${PLOT_DIR}/capacity_boxplots.{png,pdf} =="
echo "== detected boundaries (bytes): ${BOUNDARIES[*]:-none} =="
echo "== record in data_raw/${MACHINE}/README.md: core=${CORE}, seed=${SEED}, samples=${SAMPLES}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
