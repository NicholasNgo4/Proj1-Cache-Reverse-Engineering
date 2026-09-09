#!/bin/bash
#
# run_line_size_full.sh -- one-command Phase-I line-size pipeline for one
# machine: auto-pick a footprint from an existing capacity boundary ->
# coarse stride sweep (random + sequential) -> automatic transition
# detection -> dense stride sweep bracketing the estimate -> reproducibility
# repeats -> combined plots.
#
# Mirrors run_capacity_full.sh's philosophy: deliberately NOT adaptive, every
# step is a fixed rule (a 1.2x footprint-over-boundary multiplier, a
# +-2x-estimate dense bracket, 2 reproducibility repeats), so it doesn't need
# per-machine judgment calls.
#
# Why a footprint override matters: real cache occupancy for this sweep is
# (distinct lines touched) * true_line_size, which is flat at footprint_bytes
# for stride <= true_line_size and falls off past it. That transition is
# only visible if footprint_bytes is chosen just ABOVE a known capacity
# boundary (so small strides spill and large strides fit) -- if the
# footprint always fits regardless of stride, there is no signal at all.
# This script reads that boundary from an already-completed capacity run
# (data_processed/<machine>/capacity/*summary*.csv); run
# run_capacity_full.sh first if that doesn't exist yet.
#
# Usage:
#   ./scripts/run_line_size_full.sh <machine> <core> [footprint_bytes_override]
#
# Example:
#   ./scripts/run_line_size_full.sh artemisia 4
#   ./scripts/run_line_size_full.sh charnwood 2 49152   # manual footprint override
#
# Output:
#   data_raw/<machine>/line_size/*.csv                raw per-batch samples
#   data_processed/<machine>/line_size/*.csv          per-stride distribution summaries
#   data_processed/<machine>/line_size/plots/         line_size_curve + line_size_boxplots (png+pdf)
#   data_raw/<machine>/line_size/run_line_size_full_<ts>.log   full transcript of this run
#
# After it finishes, fill in data_raw/<machine>/README.md using the
# machine/core/seed/timestamp/footprint/estimate printed at the end.
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <machine> <core> [footprint_bytes_override]" >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
FOOTPRINT_OVERRIDE="${3:-}"

MULTIPLIER=2.0                # footprint_bytes = ceil(L1_boundary * MULTIPLIER)
                               # Needs to leave several dense-sweep points of clean
                               # plateau between the line-size knee (at true_line_size,
                               # independent of MULTIPLIER) and the capacity-driven
                               # fall-off (at true_line_size * MULTIPLIER -- see
                               # scripts/detect_line_size.py's module docstring) for
                               # detect_line_size.py's default --confirm=5 to have
                               # enough room to confirm the plateau. Measured on Sunbird:
                               # MULTIPLIER=1.2-1.5 leaves only 0-3 clean plateau points
                               # before the fall-off starts and detection fails; 2.0
                               # reliably leaves ~8-9.
FOOTPRINT_FALLBACK=65536      # used only if no capacity data exists yet for this machine
MIN_STRIDE=8
MAX_STRIDE=1024
STRIDE_STEP_COARSE=8
STRIDE_STEP_DENSE=1
ALIGN_BYTES=4096
SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
REPEATS=2                     # extra independent repeats of the dense bracket

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_DIR="data_raw/${MACHINE}/line_size"
PROC_DIR="data_processed/${MACHINE}/line_size"
PLOT_DIR="${PROC_DIR}/plots"
mkdir -p "$RAW_DIR" "$PROC_DIR" "$PLOT_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_DIR}/run_line_size_full_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_line_size_full: machine=${MACHINE} core=${CORE} seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

# ---- footprint selection ----
L1_BOUNDARY=""
if [ -n "$FOOTPRINT_OVERRIDE" ]; then
  FOOTPRINT_BYTES="$FOOTPRINT_OVERRIDE"
  echo "-- using footprint_bytes override: ${FOOTPRINT_BYTES} --"
else
  CAP_DIR="data_processed/${MACHINE}/capacity"
  CAP_SUMMARY=""
  # Build the candidate list explicitly rather than looping over globs
  # directly: bash expands each glob's matches in alphabetical order, and a
  # *coarse*random*summary.csv glob also matches tail-extension sweeps like
  # "coarse_ext256_random_summary.csv" or "coarse_ext_random_summary.csv"
  # (built to check for a further plateau at a coarse step over a huge
  # high-end range, not to resolve a clean low-end/L1 boundary) -- and
  # "coarse_ext..." sorts alphabetically BEFORE "coarse_random...", so the
  # old single-glob loop below would silently pick the tail-extension file
  # first on any machine lacking a *combined* summary (hit Sunbird: silently
  # fell back to FOOTPRINT_FALLBACK with a misleading "no capacity summary
  # found" warning, even though a perfectly good coarse_random_summary.csv
  # was sitting right there). Explicitly exclude *ext* files, and verify
  # each candidate actually yields a boundary before accepting it (instead
  # of accepting the first candidate that merely exists).
  CAP_CANDIDATES=()
  for pat in "${CAP_DIR}"/*combined*random*summary.csv "${CAP_DIR}"/coarse_random_summary.csv "${CAP_DIR}"/summary.csv; do
    for f in $pat; do
      [ -f "$f" ] || continue
      case "$f" in *ext*) continue ;; esac
      CAP_CANDIDATES+=("$f")
    done
  done
  for f in "${CAP_CANDIDATES[@]}"; do
    mapfile -t TRY_BOUNDARIES < <(python3 scripts/detect_cache_hierarchy.py "$f" --machine-readable 2>/dev/null || true)
    if [ -n "${TRY_BOUNDARIES[0]:-}" ]; then
      CAP_SUMMARY="$f"
      L1_BOUNDARY="${TRY_BOUNDARIES[0]}"
      break
    fi
  done
  if [ -n "$L1_BOUNDARY" ]; then
    FOOTPRINT_BYTES=$(python3 -c "import math; print(math.ceil(${L1_BOUNDARY} * ${MULTIPLIER}))")
    echo "-- using L1 boundary ${L1_BOUNDARY} bytes from ${CAP_SUMMARY} -> footprint_bytes=${FOOTPRINT_BYTES} --"
  else
    FOOTPRINT_BYTES="$FOOTPRINT_FALLBACK"
    echo "WARNING: no capacity summary found under ${CAP_DIR} -- run scripts/run_capacity_full.sh"
    echo "         for ${MACHINE} first for a real boundary. Falling back to footprint_bytes=${FOOTPRINT_BYTES}." >&2
  fi
fi

run_sweep() {
  # run_sweep <pattern> <min_stride> <max_stride> <step> <out_csv>
  local pattern="$1" min="$2" max="$3" step="$4" out="$5"
  taskset -c "$CORE" ./cache_bench --experiment line_size --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size "$BATCH" \
    --footprint-bytes "$FOOTPRINT_BYTES" --min-stride "$min" --max-stride "$max" \
    --stride-step "$step" --align-bytes "$ALIGN_BYTES" \
    --warmup-passes "$WARMUP" --seed "$SEED" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out"
}

summarize() {
  python3 scripts/summarize_raw.py "$1" -o "$2" >/dev/null
}

ALL_SUMMARIES=()

# ---- coarse sweep ----
echo "-- coarse sweep ${MIN_STRIDE}-${MAX_STRIDE} bytes (step ${STRIDE_STEP_COARSE}) --"
COARSE_R="${RAW_DIR}/line_size_coarse_random_${TS}.csv"
COARSE_S="${RAW_DIR}/line_size_coarse_sequential_${TS}.csv"
run_sweep random "$MIN_STRIDE" "$MAX_STRIDE" "$STRIDE_STEP_COARSE" "$COARSE_R"
run_sweep sequential "$MIN_STRIDE" "$MAX_STRIDE" "$STRIDE_STEP_COARSE" "$COARSE_S"
COARSE_R_SUM="${PROC_DIR}/coarse_random_summary.csv"
COARSE_S_SUM="${PROC_DIR}/coarse_sequential_summary.csv"
summarize "$COARSE_R" "$COARSE_R_SUM"
summarize "$COARSE_S" "$COARSE_S_SUM"
ALL_SUMMARIES+=("$COARSE_R_SUM" "$COARSE_S_SUM")

# ---- automatic transition detection on the coarse random-pattern data ----
# detect_line_size.py finds the ramp-SATURATION point directly (see its
# module docstring) -- this is already the true line-size estimate and
# needs no footprint/boundary correction, unlike the old drop-based
# approach this pipeline used to call with --boundary-bytes.
mapfile -t LS_ESTIMATE_ARR < <(python3 scripts/detect_line_size.py "$COARSE_R_SUM" --machine-readable 2>/dev/null || true)
ESTIMATE="${LS_ESTIMATE_ARR[0]:-}"
echo "-- detected line-size estimate (bytes): ${ESTIMATE:-none} --"

# ---- dense sweep bracketing the estimate, +- 2x, clamped to swept range ----
PLOT_BOUNDARY_ARGS=()
if [ -n "$ESTIMATE" ]; then
  DMIN=$(python3 -c "print(max(${MIN_STRIDE}, int(${ESTIMATE} / 2)))")
  DMAX=$(python3 -c "print(min(${MAX_STRIDE}, int(${ESTIMATE} * 2) + 1))")
  if [ "$DMAX" -le "$DMIN" ]; then
    echo "-- skipping dense sweep (degenerate range ${DMIN}-${DMAX}) --"
  else
    echo "-- dense sweep around estimate ${ESTIMATE} bytes: ${DMIN}-${DMAX} (step ${STRIDE_STEP_DENSE}) --"
    DR="${RAW_DIR}/line_size_dense_random_${TS}.csv"
    DS="${RAW_DIR}/line_size_dense_sequential_${TS}.csv"
    run_sweep random "$DMIN" "$DMAX" "$STRIDE_STEP_DENSE" "$DR"
    run_sweep sequential "$DMIN" "$DMAX" "$STRIDE_STEP_DENSE" "$DS"
    DR_SUM="${PROC_DIR}/dense_random_summary.csv"
    DS_SUM="${PROC_DIR}/dense_sequential_summary.csv"
    summarize "$DR" "$DR_SUM"; summarize "$DS" "$DS_SUM"
    ALL_SUMMARIES+=("$DR_SUM" "$DS_SUM")

    for r in $(seq 1 "$REPEATS"); do
      echo "  -- repeat ${r}/${REPEATS} of the dense window --"
      RR="${RAW_DIR}/line_size_dense_rep${r}_random_${TS}.csv"
      RS="${RAW_DIR}/line_size_dense_rep${r}_sequential_${TS}.csv"
      run_sweep random "$DMIN" "$DMAX" "$STRIDE_STEP_DENSE" "$RR"
      run_sweep sequential "$DMIN" "$DMAX" "$STRIDE_STEP_DENSE" "$RS"
      RR_SUM="${PROC_DIR}/dense_rep${r}_random_summary.csv"
      RS_SUM="${PROC_DIR}/dense_rep${r}_sequential_summary.csv"
      summarize "$RR" "$RR_SUM"; summarize "$RS" "$RS_SUM"
      ALL_SUMMARIES+=("$RR_SUM" "$RS_SUM")
    done
  fi
  PLOT_BOUNDARY_ARGS=(--boundary "$ESTIMATE")
else
  echo "-- no transition detected in the coarse sweep; skipping dense/repeat stages --"
  if [ -z "$FOOTPRINT_OVERRIDE" ] && [ -n "$L1_BOUNDARY" ]; then
    echo "WARNING: footprint_bytes=${FOOTPRINT_BYTES} was auto-derived from" >&2
    echo "         detect_cache_hierarchy.py's boundary=${L1_BOUNDARY} on ${CAP_SUMMARY}," >&2
    echo "         but no ramp-saturation plateau was found at that footprint. That" >&2
    echo "         detector's first boundary is a coarse first-pass heuristic and is" >&2
    echo "         NOT guaranteed to be the true L1 capacity (it can be off by an" >&2
    echo "         order of magnitude -- confirmed on Sunbird, where it returns" >&2
    echo "         ~279 KiB against a manually-established ~32 KiB L1). A footprint" >&2
    echo "         built from a wrong boundary can span multiple cache levels, which" >&2
    echo "         produces exactly this noisy/no-transition shape instead of a clean" >&2
    echo "         line-size signal. The plot below is generated from ONLY the coarse" >&2
    echo "         (noisy) data and should NOT be treated as a valid result -- re-run" >&2
    echo "         with an explicit override, e.g.:" >&2
    echo "           $0 ${MACHINE} ${CORE} <known_good_footprint_bytes>" >&2
    echo "         (a good starting point is ~2x this machine's own confirmed L1" >&2
    echo "         boundary from its capacity README section, not this script's" >&2
    echo "         auto-detected one)." >&2
  fi
fi

# ---- plots ----
echo "-- generating plots --"
python3 scripts/plot_line_size.py \
  "${ALL_SUMMARIES[@]}" \
  -o "$PLOT_DIR" --machine "$MACHINE" \
  --title-suffix "(Phase I timing-only, auto pipeline)" \
  "${PLOT_BOUNDARY_ARGS[@]}"

echo "== done =="
echo "== plots: ${PLOT_DIR}/line_size_curve.{png,pdf}, ${PLOT_DIR}/line_size_boxplots.{png,pdf} =="
echo "== detected line-size estimate (bytes): ${ESTIMATE:-none} =="
echo "== record in data_raw/${MACHINE}/README.md: core=${CORE}, seed=${SEED}, samples=${SAMPLES}, footprint_bytes=${FOOTPRINT_BYTES}, boundary_bytes=${L1_BOUNDARY:-fallback}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
