#!/bin/bash
#
# run_associativity_stride_scan.sh -- EXPLORATORY diagnostic for the
# large-stride DTLB/page confound documented in CLAUDE.md's associativity
# section (2026-09-12 falsification + real-capacity-test findings on
# Sunbird): every power-of-two node-to-node stride tried above ~1 MiB broke
# at nearly the same num_ways (~9-10) regardless of the actual byte value
# tested -- the signature of a small, fixed, page-count-limited structure
# (DTLB or similar), not real L2/LLC associativity.
#
# Why a smaller stride can help: run_associativity_full.sh always uses the
# FULL target cache level's capacity C as the node-to-node stride, because
# that's the one value provably valid regardless of the (unknown) true
# associativity A_true -- capacity = sets * line_size * ways is always a
# whole multiple of the true minimal set-stride C/A_true, and any multiple
# of a valid same-set stride is itself a valid same-set stride (see
# associativity.h's docstring for the modular-arithmetic argument). But
# that also means every probed node lands on its own distinct page for any
# C above 4 KiB -- for L2/LLC-scale C (hundreds of KiB to tens of MiB), a
# max_ways=40 sweep touches up to 40 different pages, plausibly exhausting
# the DTLB well before it exhausts the real cache set.
#
# This script instead tries C/A_guess for a list of candidate divisors
# A_guess: if A_guess evenly divides the TRUE associativity A_true, then
# C/A_guess is STILL a valid same-set stride (it's C/A_true multiplied by
# A_true/A_guess, an integer >= 1 -- still a whole multiple of the true
# minimal stride) -- but it's a smaller stride, touching fewer distinct
# pages for the same num_ways swept. Critically, per the same argument, the
# REPORTED KNEE (num_ways at which thrashing starts) should be the SAME
# real answer A_true regardless of which valid A_guess/stride you used --
# a cache set holds A_true distinct tags no matter what multiple-of-minimal
# stride you used to generate those tags' addresses. So: if the same knee
# recurs across two or more DIFFERENT A_guess values (hence different
# stride sizes, hence different page counts touched), that's evidence for
# a real signal. If the reported knee instead tracks page count / A_guess
# choice, that's the confound signature repeating itself, same as the
# large-stride case.
#
# If A_guess does NOT divide A_true, C/A_guess is generally NOT a valid
# same-set stride at all -- the constructed "conflict ring" nodes won't
# actually collide into one set, so the expected (safe) failure mode is NO
# knee detected within max_ways, not a misleading result.
#
# This is a SCAN, not a final-result pipeline: reduced sample count,
# random pattern only, no reproducibility repeats -- fast enough to try
# several candidates in one sitting. A self-consistent candidate found
# here must still be confirmed with run_associativity_full.sh's full rigor
# (1,000,000 samples, both patterns, 2 seed-varied repeats) before citing
# any number in the report -- this script's output is a hypothesis
# generator, same relationship detect_cache_hierarchy.py's coarse pass has
# to a real dense-sweep-confirmed capacity boundary.
#
# Usage:
#   ./scripts/run_associativity_stride_scan.sh <machine> <core> <capacity_bytes> [A_guess_csv]
# Example (2 MiB candidate L2 shelf, testing 7 divisor guesses):
#   ./scripts/run_associativity_stride_scan.sh upgrade 5 2097152 1,2,4,8,16,32,64
#
# Output:
#   data_raw/<machine>/associativity/stride_scan/<ts>/*.csv.gz        raw per-batch samples, one per A_guess
#   data_processed/<machine>/associativity/stride_scan/<ts>/*.csv    per-num_ways summaries, one per A_guess
#   data_processed/<machine>/associativity/stride_scan/<ts>/comparison.csv   A_guess,stride_bytes,pages_in_arena,detected_ways -- the actual diagnostic table
#   data_raw/<machine>/associativity/stride_scan/run_stride_scan_<ts>.log    full transcript
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "Usage: $0 <machine> <core> <capacity_bytes> [A_guess_csv]" >&2
  echo "       capacity_bytes: a capacity candidate for the level under test (need not" >&2
  echo "                       be hand-confirmed -- this is an exploratory scan)" >&2
  echo "       A_guess_csv: comma-separated candidate divisors of capacity_bytes to try" >&2
  echo "                    as the stride shrink factor (default: 1,2,4,8,16,32,64)." >&2
  echo "                    A_guess=1 reproduces the current full-capacity-stride method," >&2
  echo "                    included as the baseline comparison point." >&2
  exit 1
fi

MACHINE="$1"
CORE="$2"
CAP_BYTES="$3"
AGUESS_CSV="${4:-1,2,4,8,16,32,64}"

PAGE=4096
SAMPLES=200000          # reduced from the final-pipeline's 1,000,000 -- this is a scan
BATCH=1000
WARMUP=2
MIN_WAYS=2
MAX_WAYS=24             # reduced from 40 -- every confound knee characterized so far
                         # broke well under this; raise if a candidate here shows no
                         # knee at all within range
WAY_STEP=1
SEED=12345

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RAW_DIR="data_raw/${MACHINE}/associativity/stride_scan/${TS}"
PROC_DIR="data_processed/${MACHINE}/associativity/stride_scan/${TS}"
mkdir -p "$RAW_DIR" "$PROC_DIR"

LOG="data_raw/${MACHINE}/associativity/stride_scan/run_stride_scan_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

echo "== run_associativity_stride_scan (EXPLORATORY, not a final result): machine=${MACHINE} core=${CORE} =="
echo "== capacity_bytes=${CAP_BYTES} A_guess candidates=${AGUESS_CSV} =="
echo "== timestamp=${TS} =="
echo "== samples=${SAMPLES} (reduced), max_ways=${MAX_WAYS} (reduced), random pattern only, no repeats =="

make -s

COMPARISON="${PROC_DIR}/comparison.csv"
echo "a_guess,stride_bytes,pages_in_arena,detected_ways,summary_csv" > "$COMPARISON"

IFS=',' read -r -a AGUESSES <<< "$AGUESS_CSV"

for A in "${AGUESSES[@]}"; do
  echo ""
  echo "-- A_guess=${A} --"
  if [ $(( CAP_BYTES % A )) -ne 0 ]; then
    echo "   skip: ${CAP_BYTES} not evenly divisible by ${A}"
    continue
  fi
  STRIDE=$(( CAP_BYTES / A ))
  if [ "$STRIDE" -lt "$PAGE" ] || [ $(( STRIDE % PAGE )) -ne 0 ]; then
    echo "   skip: derived stride ${STRIDE} is not a positive multiple of ${PAGE} (page size) -- cache_bench would reject it"
    continue
  fi
  PAGES_IN_ARENA=$(( (STRIDE * (MAX_WAYS + 1) + PAGE - 1) / PAGE ))
  echo "   stride=${STRIDE} bytes (capacity/${A}), arena spans ~${PAGES_IN_ARENA} pages"

  RAW="${RAW_DIR}/stride_scan_a${A}_${TS}.csv"
  taskset -c "$CORE" ./cache_bench --experiment associativity --pattern random \
    --samples "$SAMPLES" --batch-size "$BATCH" --cache-bytes "$STRIDE" \
    --min-ways "$MIN_WAYS" --max-ways "$MAX_WAYS" --way-step "$WAY_STEP" \
    --warmup-passes "$WARMUP" --seed "$SEED" > "$RAW"
  echo "   wrote $(wc -l < "$RAW") lines -> $RAW"

  SUM="${PROC_DIR}/a${A}_summary.csv"
  python3 scripts/summarize_raw.py "$RAW" -o "$SUM" >/dev/null

  EST="$(python3 scripts/detect_associativity.py "$SUM" --machine-readable 2>/dev/null || true)"
  echo "   detected knee: ${EST:-none}"
  echo "${A},${STRIDE},${PAGES_IN_ARENA},${EST:-none},${SUM}" >> "$COMPARISON"
done

echo ""
echo "== comparison table (${COMPARISON}) =="
column -s, -t "$COMPARISON"

echo ""
echo "== self-consistency check =="
python3 - "$COMPARISON" <<'PYEOF'
import csv, sys
from collections import defaultdict

path = sys.argv[1]
by_estimate = defaultdict(list)
with open(path, newline="") as f:
    for row in csv.DictReader(f):
        est = row["detected_ways"]
        if est != "none":
            by_estimate[est].append((row["a_guess"], row["pages_in_arena"]))

if not by_estimate:
    print("No candidate produced a detectable knee -- no signal to evaluate yet.")
else:
    recurring = {est: hits for est, hits in by_estimate.items() if len(hits) >= 2}
    if recurring:
        for est, hits in recurring.items():
            a_guesses = sorted(set(a for a, _ in hits))
            pages = sorted(set(p for _, p in hits))
            print(f"knee={est}: recurs across A_guess={a_guesses} (pages_in_arena={pages}) "
                  f"-- {'SAME page count, not yet distinguishing' if len(pages) == 1 else 'DIFFERENT page counts -- self-consistency evidence for a real signal'}")
    else:
        print("Every detected knee is unique to its own A_guess/stride -- looks like the "
              "confound (knee tracks stride/page-count choice), or too few candidates "
              "produced a knee at all to compare. Not self-consistent; do not cite a number "
              "from this scan.")
PYEOF

echo ""
echo "-- compressing raw CSVs --"
gzip -f "${RAW_DIR}"/stride_scan_*.csv 2>/dev/null || true

echo ""
echo "== done (EXPLORATORY SCAN -- not a final result) =="
echo "== full transcript: ${LOG} =="
echo "== comparison table: ${COMPARISON} =="
