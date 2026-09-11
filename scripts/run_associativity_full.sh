#!/bin/bash
#
# run_associativity_full.sh -- one-command Phase-I associativity pipeline
# for one machine, per cache level: base sweep (num_ways=2..max_ways, both
# patterns) -> automatic knee detection -> reproducibility repeats -> plots.
# Repeated once per cache level, using that level's own capacity as the
# node-to-node stride (see main_code/common/associativity.h for why a
# stride equal to a level's capacity forces every probed node into the
# same cache set regardless of the unknown line size / way count).
#
# Mirrors run_capacity_full.sh / run_line_size_full.sh's philosophy:
# deliberately NOT adaptive, every step is a fixed rule (a dense num_ways=
# 2..32 sweep in one pass -- cheap because the whole range is only ~32
# points, unlike capacity/line_size's byte-granularity search -- plus 2
# reproducibility repeats), so it doesn't need per-machine judgment calls.
# 32 is a deliberate ceiling, not a leftover default: real L1/L2/LLC
# associativities on modern x86/ARM never reach the low 20s, so there is
# no value in paying for the extra wall time out to 64.
#
# Cache-level capacities MUST be supplied deliberately, not blindly trusted
# from auto-detection: detect_cache_hierarchy.py's coarse first-pass
# boundary is a known-unreliable heuristic for the L1 level specifically
# (confirmed on Sunbird: it returns ~279 KiB against a manually-established
# ~32 KiB L1 -- see data_raw/sunbird/README.md and the same caveat already
# documented in run_line_size_full.sh). This script will auto-detect and
# round to the nearest power of two if no override is given, but ALWAYS
# prints a loud warning to cross-check against this machine's own
# data_raw/<machine>/README.md hand-confirmed capacity boundaries first.
#
# Usage:
#   ./scripts/run_associativity_full.sh <machine> <core> [cache_bytes_csv]
#
# Example:
#   ./scripts/run_associativity_full.sh sunbird 20                       # auto-detect (see warning)
#   ./scripts/run_associativity_full.sh sunbird 20 32768,20971520,157286400  # explicit L1,L2,LLC override
#
# Output:
#   data_raw/<machine>/associativity/<level>/*.csv            raw per-batch samples
#   data_processed/<machine>/associativity/<level>/*.csv      per-num_ways distribution summaries
#   data_processed/<machine>/associativity/<level>/plots/     associativity_curve + associativity_boxplots (png+pdf)
#   data_raw/<machine>/associativity/run_associativity_full_<ts>.log  full transcript of this run
#
# After it finishes, fill in data_raw/<machine>/README.md using the
# machine/core/seed/timestamp/cache_bytes/estimate printed at the end for
# each level.
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <machine> <core> [cache_bytes_csv]" >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
CACHE_BYTES_CSV="${3:-}"

MIN_WAYS=2
MAX_WAYS=32   # real L1/L2/LLC associativities on modern x86/ARM never reach the
              # low 20s, let alone 32 -- no need to sweep past it
WAY_STEP=1
SAMPLES=1000000
BATCH=1000
WARMUP=3
SEED=12345
REPEATS=2                     # extra independent repeats of the base window

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_ROOT="data_raw/${MACHINE}/associativity"
PROC_ROOT="data_processed/${MACHINE}/associativity"
mkdir -p "$RAW_ROOT" "$PROC_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${RAW_ROOT}/run_associativity_full_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_associativity_full: machine=${MACHINE} core=${CORE} seed=${SEED} =="
echo "== timestamp=${TS} =="

make -s

level_name() {
  # level_name <index 0-based>
  case "$1" in
    0) echo "L1" ;;
    1) echo "L2" ;;
    2) echo "L3_LLC" ;;
    *) echo "L$(( $1 + 1 ))" ;;
  esac
}

round_pow2() {
  python3 -c "import math; print(2 ** round(math.log2(${1})))"
}

# ---- cache_bytes selection, one value per level ----
LEVEL_BYTES=()
if [ -n "$CACHE_BYTES_CSV" ]; then
  IFS=',' read -r -a LEVEL_BYTES <<< "$CACHE_BYTES_CSV"
  echo "-- using explicit cache_bytes override: ${LEVEL_BYTES[*]} --"
else
  CAP_DIR="data_processed/${MACHINE}/capacity"
  CAP_SUMMARY=""
  mapfile -t RAW_BOUNDARIES < <(true)
  # Same candidate-file selection as run_line_size_full.sh: explicitly
  # exclude *ext* tail-extension sweeps (no clean boundary, sorts first
  # alphabetically) and verify a candidate actually yields boundaries
  # before accepting it.
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
      RAW_BOUNDARIES=("${TRY_BOUNDARIES[@]}")
      break
    fi
  done
  if [ "${#RAW_BOUNDARIES[@]}" -eq 0 ]; then
    echo "ERROR: no capacity summary with detectable boundaries found under ${CAP_DIR}." >&2
    echo "       Run scripts/run_capacity_full.sh for ${MACHINE} first, or pass an" >&2
    echo "       explicit cache_bytes_csv override." >&2
    exit 1
  fi
  echo "-- auto-detected boundaries from ${CAP_SUMMARY}: ${RAW_BOUNDARIES[*]} --"
  for b in "${RAW_BOUNDARIES[@]}"; do
    LEVEL_BYTES+=("$(round_pow2 "$b")")
  done
  echo "-- rounded to nearest power of two: ${LEVEL_BYTES[*]} --"
  echo "WARNING: these are auto-detected, NOT hand-confirmed. detect_cache_hierarchy.py's" >&2
  echo "         coarse first-pass boundary is a known-unreliable heuristic, especially" >&2
  echo "         for L1 (confirmed off by ~9x on Sunbird: 279 KiB auto vs 32 KiB hand-" >&2
  echo "         confirmed -- see data_raw/sunbird/README.md). Cross-check each value" >&2
  echo "         above against ${MACHINE}'s own data_raw/${MACHINE}/README.md capacity" >&2
  echo "         section before trusting these results; re-run with an explicit" >&2
  echo "         cache_bytes_csv override if they disagree, e.g.:" >&2
  echo "           $0 ${MACHINE} ${CORE} <L1_bytes>,<L2_bytes>,<LLC_bytes>" >&2
fi

run_sweep() {
  # run_sweep <pattern> <cache_bytes> <out_csv>
  local pattern="$1" cache_bytes="$2" out="$3"
  taskset -c "$CORE" ./cache_bench --experiment associativity --pattern "$pattern" \
    --samples "$SAMPLES" --batch-size "$BATCH" --cache-bytes "$cache_bytes" \
    --min-ways "$MIN_WAYS" --max-ways "$MAX_WAYS" --way-step "$WAY_STEP" \
    --warmup-passes "$WARMUP" --seed "$SEED" > "$out"
  echo "  wrote $(wc -l < "$out") lines -> $out"
}

summarize() {
  python3 scripts/summarize_raw.py "$1" -o "$2" >/dev/null
}

RESULTS=()

for i in "${!LEVEL_BYTES[@]}"; do
  CACHE_BYTES="${LEVEL_BYTES[$i]}"
  LEVEL="$(level_name "$i")"
  RAW_DIR="${RAW_ROOT}/${LEVEL}"
  PROC_DIR="${PROC_ROOT}/${LEVEL}"
  PLOT_DIR="${PROC_DIR}/plots"
  mkdir -p "$RAW_DIR" "$PROC_DIR" "$PLOT_DIR"

  echo ""
  echo "== level ${LEVEL}: cache_bytes=${CACHE_BYTES} =="

  ALL_SUMMARIES=()

  # ---- base sweep ----
  echo "-- base sweep num_ways=${MIN_WAYS}-${MAX_WAYS} --"
  BASE_R="${RAW_DIR}/associativity_base_random_${TS}.csv"
  BASE_S="${RAW_DIR}/associativity_base_sequential_${TS}.csv"
  run_sweep random "$CACHE_BYTES" "$BASE_R"
  run_sweep sequential "$CACHE_BYTES" "$BASE_S"
  BASE_R_SUM="${PROC_DIR}/base_random_summary.csv"
  BASE_S_SUM="${PROC_DIR}/base_sequential_summary.csv"
  summarize "$BASE_R" "$BASE_R_SUM"
  summarize "$BASE_S" "$BASE_S_SUM"
  ALL_SUMMARIES+=("$BASE_R_SUM" "$BASE_S_SUM")

  # ---- automatic knee detection on the base random-pattern data ----
  ESTIMATE="$(python3 scripts/detect_associativity.py "$BASE_R_SUM" --machine-readable 2>/dev/null || true)"
  echo "-- detected associativity estimate: ${ESTIMATE:-none} --"

  # ---- reproducibility repeats of the same base window ----
  if [ -n "$ESTIMATE" ]; then
    for r in $(seq 1 "$REPEATS"); do
      echo "  -- repeat ${r}/${REPEATS} --"
      RR="${RAW_DIR}/associativity_rep${r}_random_${TS}.csv"
      RS="${RAW_DIR}/associativity_rep${r}_sequential_${TS}.csv"
      run_sweep random "$CACHE_BYTES" "$RR"
      run_sweep sequential "$CACHE_BYTES" "$RS"
      RR_SUM="${PROC_DIR}/rep${r}_random_summary.csv"
      RS_SUM="${PROC_DIR}/rep${r}_sequential_summary.csv"
      summarize "$RR" "$RR_SUM"; summarize "$RS" "$RS_SUM"
      ALL_SUMMARIES+=("$RR_SUM" "$RS_SUM")
    done
  else
    echo "-- no knee detected; skipping reproducibility repeats for this level --"
    echo "   (either true associativity is >= max_ways=${MAX_WAYS}, or cache_bytes=${CACHE_BYTES}" >&2
    echo "    doesn't match this level's real capacity -- see the warning above if this" >&2
    echo "    came from auto-detection)" >&2
  fi

  # ---- plots ----
  echo "-- generating plots for ${LEVEL} --"
  PLOT_ARGS=(--estimate "$ESTIMATE")
  [ -z "$ESTIMATE" ] && PLOT_ARGS=()
  python3 scripts/plot_associativity.py \
    "${ALL_SUMMARIES[@]}" \
    -o "$PLOT_DIR" --machine "$MACHINE" --level "$LEVEL" \
    --title-suffix "(Phase I timing-only, auto pipeline)" \
    "${PLOT_ARGS[@]}"

  echo "-- compressing raw CSVs for ${LEVEL} --"
  gzip -f "${RAW_DIR}"/associativity_*.csv

  RESULTS+=("${LEVEL}: cache_bytes=${CACHE_BYTES} -> associativity=${ESTIMATE:-none}")
done

echo ""
echo "== done =="
for r in "${RESULTS[@]}"; do
  echo "== ${r} =="
done
echo "== record in data_raw/${MACHINE}/README.md: core=${CORE}, seed=${SEED}, samples=${SAMPLES}, timestamp=${TS} =="
echo "== full transcript saved to: ${LOG} =="
