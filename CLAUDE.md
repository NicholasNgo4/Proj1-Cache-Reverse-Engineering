# Project: HW1 Cache Reverse Engineering (ECE 592, Fall 2026)

See `README.md` for full project structure, build/run commands, and the
Phase I/II/III discipline (non-negotiable — read it before running anything
involving `perf`, PMU, or cache-topology files). This file is for a fresh
Claude Code session (e.g. after SSHing into a different lab machine) to
pick up current progress without re-deriving it. Note: a Claude session's
conversation history and memory do NOT transfer between machines (each
lab machine has its own local `/home`, confirmed not NFS-shared) — this
file, the repo's data/READMEs, and git history are the only things that do.

## Current status (update this section as work progresses)

**Capacity experiment: done (with caveats, see below) on all 8 machines —
Sunbird, Crux, Skylark, Upgrade, Charnwood, Thunderbird, Ookay, and
Artemisia.** Several sessions ran this in parallel on different machines;
this section was consolidated from all of their commits/READMEs during a
merge, so re-check each machine's own `data_raw/<machine>/README.md`
before citing a number — summaries below (and Artemisia's fuller writeup
just after the per-machine list) are necessarily compressed.

- **Sunbird** (`data_raw/sunbird/capacity/`): three flat/ramp transitions
  across 1 KiB-256 MiB, confirmed via independent repeat runs. See
  `data_raw/sunbird/README.md` for a documented multi-tenant-interference
  finding and a plotting-script bug found/fixed along the way. One gap:
  its README cites a `build/cache_bench.source.dis` disassembly-evidence
  file that was never actually generated (discovered while fixing a
  `.gitignore` rule that was silently swallowing it for every machine) —
  still a TODO, flagged in the README rather than faked. **2026-09-11:
  256 KiB and ~30 MiB (31,457,280 B) re-verified and confirmed NOT to be
  genuine capacity boundaries** — a fresh, high-resolution (300 ppo, both
  patterns) targeted re-run of each on core 1 (core 2 was busy with
  another student's process at the time) shows 256 KiB sitting on the
  same continuous, boundary-free ramp already documented, and ~30 MiB
  sitting partway up the already-documented ~26-27 MiB+ monotonic climb
  toward DRAM, not at its own distinct knee; re-running
  `detect_cache_hierarchy.py` on the ~30 MiB window in isolation
  reproduces a spurious "boundary" by locking onto a 3-point interference
  spike, direct evidence for why the two values shouldn't have been
  trusted. These two byte values had been used (unresolved/provisional)
  as this machine's L2/LLC-candidate `run_line_size.sh` boundaries — see
  `data_raw/sunbird/README.md`'s line_size/ section, now updated to flag
  those two footprints as "inside the transition region" rather than "at
  a cache-level edge" (the 64B line-size result itself is unaffected).
- **Crux** (`data_raw/crux/capacity/`): `scripts/run_capacity_full.sh crux
  7` detected 4 boundaries (262144 / 9147840 / 11863280 / 16777216 bytes).
  Topmost region was still climbing at the 256 MiB default ceiling; a
  manual 256 MiB-1 GiB follow-up (3 independent runs) found it flattens
  into a genuine plateau (~245-250 ticks/access, agreeing within 0.5% at
  1 GiB). The ~64 KiB-4 MiB region is a soft ramp with no confirmed flat
  shelf, and ~4-64 MiB showed up to ~89% run-to-run spread. Also flags a
  ~3x wall-clock variance anomaly (13-40 min for the same workload,
  tracking other students' concurrent load) that didn't measurably affect
  the timing medians themselves. See `data_raw/crux/README.md`.
- **Skylark** (`data_raw/skylark/capacity/`): `run_capacity_full.sh
  skylark 10 134217728` (128 MiB coarse ceiling) detected 3 boundaries
  (16777216 / 18295680 / 21757352 bytes). A manual follow-up extended all
  the way to 2 GiB and found a genuinely settled plateau (~280 ticks/
  access, only ~2% rise from 512 MiB, flattening by ~1.7 GiB, reproduced
  within ~0.2% across 2 independent runs at 2 GiB) — this is the
  cleanest/most fully-resolved topmost-region result of any machine so
  far. Note: the pipeline's own plotting step failed mid-run on this
  machine (`matplotlib` missing); data generation completed fine and
  plots were regenerated standalone afterward. See
  `data_raw/skylark/README.md`.
- **Upgrade** (`data_raw/upgrade/capacity/`): `run_capacity_full.sh upgrade 5`
  (default 64 MiB coarse ceiling) plus a 4x tail extension (64-256 MiB).
  **README backfilled 2026-09-10/12** (first the boundary analysis, done
  remotely from already-committed CSVs without machine access; then the
  Machine Identification fields, filled in later from a session actually
  logged into `upgrade`). One clean boundary: **L1 = 32,768 B**
  (PROVISIONAL from capacity data alone, but now corroborated by a clean
  associativity knee — see the associativity section below). No confirmed
  L2/LLC boundary yet — a ~1.5-4.5 MiB region is a candidate shelf, and
  ~5-22 MiB is a noisy transition with a systematic (not scattered)
  session-level elevation in one of two repeats, both needing a dedicated
  dense sweep to resolve. Topmost region (64-256 MiB) is **NOT flat at the
  256 MiB ceiling** (+11.9% first-to-last-quarter) — needs the same
  256 MiB-1 GiB manual follow-up every other machine required. See
  `data_raw/upgrade/README.md` for full detail.
- **Charnwood** (`data_raw/charnwood/capacity/`): **unresolved, not just
  noisy — treat with caution before citing any boundary number.** Run
  concurrently with another student's `associativity` benchmark pinned on
  a different physical core the whole time (confirmed via `mpstat`/`ps`,
  not just inferred); this produced strong bimodal contamination in 4 of
  the 6 auto-detected boundaries (~1.83-11.31 MiB region, 12-157%
  run-to-run spread). Only the ~304 KiB (L1) boundary looks clean.
  Separately, the topmost region did **not** plateau within the default
  256 MiB ceiling — a manual follow-up extension to 1 GiB found a real,
  reproducible ~11-15% climb from ~12 MiB to ~600 MiB (not flat, likely
  TLB/page-walk growth, to confirm in Phase II) plus a further,
  less-reproducible divergence above ~700 MiB in one of two repeats
  (likely more shared-machine memory pressure — swap was already
  2.6-2.8 GiB in use at run time). **This machine likely needs a full
  re-run when quiet** (check `ps`/`mpstat` for the `associativity`
  process before re-running). See `data_raw/charnwood/README.md`.
- **Thunderbird** (`data_raw/thunderbird/capacity/`): AArch64/Neoverse-N1,
  the team's one ARM machine. `main_code/aarch64/timer_arm.h` was
  sanity-checked first (standalone dependent-load test — CNTFRQ_EL0 =
  25 MHz, CNTVCT_EL0 unprivileged-readable and monotonic, ~3.3 ns/step on
  an L1-resident chase — confirmed sane). `run_capacity_full.sh`'s
  automatic boundary detection returned **nothing usable here, and this
  is a general ARM issue, not just Thunderbird**: its default
  `--min-abs-ticks 3.0` assumes x86-TSC-scale ticks, but CNTVCT_EL0 only
  runs at 25 MHz so ticks/access span just ~0.08-2.4 over the whole
  1 KiB-1 GiB range — the threshold is unreachable regardless of
  `--rel-threshold`. Separately, this machine's curve is a smooth ramp
  rather than discrete steps, so no threshold tuning fixes it either —
  boundaries below (64 KiB / 32 MiB / 256 MiB) were picked by eye, not
  from the detector. Also hit a missing-`matplotlib` failure at the
  plotting step (same as Skylark), fixed with
  `pip install --user matplotlib numpy`. Manually ran the dense sweeps +
  repeats the pipeline should have triggered: L1-plateau edge ~64-75 KiB;
  a long shallow ramp (no flat L2 shelf) through ~8 MiB; a dominant,
  genuinely noisy steep transition ~16-70 MiB (20-65% run-to-run spread
  across 3 independent runs — real shared-machine interference, like
  Sunbird's and Charnwood's noise, not an artifact); then a **confirmed**
  flat DRAM plateau at ~2.3-2.4 ticks (~92-96 ns) from ~256 MiB through
  1 GiB (~2% run-to-run spread across 3 independent runs — explicitly
  checked, not assumed). See `data_raw/thunderbird/README.md` for full
  detail. Nothing outstanding on this machine.
- **Ookay** (`data_raw/ookay/capacity/`): `run_capacity_full.sh ookay 1`
  (default 64 MiB coarse ceiling) detected 6 boundaries (285864 / 440872 /
  5439336 / 6468496 / 7692384 / 11863280 bytes) — the 4 between ~5.3 and
  ~11.9 MiB are very likely one continuous steep transition rather than 4
  real levels (the dense sweep bracketing the deepest one never flattens
  anywhere within its own 1.48-94.9 MiB range, still +23%
  last-quarter-vs-prior at its ceiling); only the ~280/430 KiB (L1/L2)
  boundaries look like genuinely separate flat/ramp transitions. Topmost
  region was still gently climbing at the default 256 MiB ceiling
  (+1.6%, 254->279 ticks); a manual 256 MiB-1 GiB follow-up (run0 + 2
  independent repeats) resolved it as a **confirmed** flat plateau
  (~286-297 ticks/access, robust median-of-3 last-quarter-vs-prior only
  +3.7%) once scattered single-run interference spikes — which recurred
  at *different* sizes in each of the 3 runs, the same signature as
  Sunbird/Crux/Charnwood/Thunderbird — were filtered out via a
  median-of-3 combination. Notable anomalies: two other students' jobs
  pinned cores 0 and 2 near 100% the entire session (confirmed via
  `mpstat`/`ps`); a third user's job appeared on the originally-used core
  1 mid-session, forcing a switch to core 3 for the follow-up (re-verified
  idle first); a fourth user's job explicitly requested core 3's SMT
  sibling (CPU7) shortly before the follow-up's last repeat, though it
  had not started as of the last check; this host's VS Code Remote-SSH
  runs with `--enable-remote-auto-shutdown`, so the follow-up's last
  repeat was moved into a detached `tmux` session (`ookay_capacity`,
  confirmed outside the VS Code server's process tree via `ps`) before
  the user disconnected. `matplotlib`/`pip` unavailable on this machine
  (no passwordless `sudo`, no `ensurepip`) — same failure mode as
  Skylark/Thunderbird; plots still outstanding, pending the user
  installing it via `sudo apt install python3-matplotlib`. See
  `data_raw/ookay/README.md` for full detail.

Artemisia's original core-23 run (`data_raw/artemisia/capacity/`,
messier than Sunbird's) was **redone on 2026-09-09 on core 20** after
discovering core 23 shared its socket with other students' active processes.
The core-23 results are archived (not deleted) under
`data_processed/artemisia/capacity_prior_core23/` because the before/after
comparison itself turned out to be useful evidence, not just noise reduction:
repeating the sub-48 KiB P-state-bimodality anomaly and the 8-96 MiB
mid-transition noise on a verifiably idle core showed the sub-48 KiB anomaly
is **not** contention-related (persisted essentially unchanged — confirms the
P-state/turbo hypothesis), while the 8-96 MiB noise **partially** improved
(median rep-to-rep spread roughly halved, 7.9%->4.2%) but its worst-case
spread did not (~93-96% either way), meaning contention explains only part of
that region's noise. The 256 MiB-1 GiB random-pattern growth also dropped
from +21.8% (core 23) to +10.8% (core 20) — still climbing, still no
flattening by 1 GiB, but contention was inflating the apparent growth rate.
Sequential pattern's ~90 MiB+ plateau (~35.3-35.9 ticks/access) matched to
within 0.4% between the two runs, confirming it's genuine hardware behavior.
**Read `data_raw/artemisia/README.md` in full before trusting any number from
this machine** — the "Detected boundaries and plateau status" table and the
two Anomaly writeups (each now with a core-20-vs-core-23 comparison) are
load-bearing, not optional color. Current primary plots are
`data_processed/artemisia/capacity/plots/` (core 20); archived core-23 plots
are alongside the archived summaries. Both the original and the redo's
long-running sweeps were run inside detached `tmux` sessions specifically so
they'd survive the driving Claude Code session disconnecting (see
`data_raw/artemisia/capacity/run_full_redo_core20.sh` and
`run_extension_repeats.sh`) — for the redo, a *second* tmux session was also
used just to poll for completion, since even a background-task watcher tied
to the Claude Code session itself doesn't survive that session dying, only
tmux on the machine does. That pattern (tmux for anything that'll run longer
than one sitting, plus a tmux-based watcher if you want progress-tracking to
survive too) is worth reusing for any future long follow-up, since a single
256 MiB-1 GiB random-pattern dense sweep alone takes ~60 minutes of wall time.
Also worth reusing: don't trust a single `ps`/`proc/stat` snapshot when
picking an idle core on this machine — per-core load moved around visibly
across three consecutive 6s sampling windows taken seconds apart during the
redo's core selection.

**`scripts/run_capacity_full.sh <machine> <core> [coarse_max_bytes]` is
the one-command pipeline for running the capacity experiment.** All 8
machines have now run it at least once; only two follow-ups remain:
**Charnwood** needs a full re-run once quiet (it shared a core with
another student's `associativity` benchmark the whole session — see its
bullet above), and **Upgrade** needs its `data_raw/upgrade/README.md`
backfilled plus a topmost-region plateau check (no tail-extension appears
to have been run there). Pipeline stages: coarse sweep -> automatic
boundary detection -> dense sweep per boundary -> reproducibility repeats
on the deepest boundary -> tail-extension sweep to check for a further
plateau -> plots -> gzips its own raw CSVs (commit the `.csv.gz`, not a
decompressed copy — see `.gitignore`; the repo was already at ~291MB for
just 2 machines/1 experiment type before this convention, and Artemisia's
redo alone was 466MB of raw CSVs before compressing to 64MB). It is
deliberately non-adaptive (see the script's own header comment for why).
After it finishes on a machine, fill in that machine's
`data_raw/<machine>/README.md` using the core/seed/timestamp/boundaries
it prints at the end, and — as done for Sunbird/Crux/Skylark/Charnwood/
Thunderbird/Ookay/Artemisia — manually extend the tail further (with 1-2
repeats, gzip any ad hoc raw CSVs by hand before committing) if the
topmost region is still climbing rather than flat at the script's default
ceiling. Check early whether `python3 -c "import matplotlib"` works on the
machine (this bit Skylark, Thunderbird, and Ookay). If re-running on an
ARM machine, expect to redo boundary detection by hand as Thunderbird's
bullet above describes (no other ARM machines remain in the team's list
per `MACHINE_RESEARCH.md`, but the same coarse-counter-resolution issue
could recur on any low-frequency architected timer). Also worth reusing
from the Artemisia redo: don't trust a single `ps`/`/proc/stat` snapshot
when picking an idle core on a shared machine — sample multiple windows
seconds apart — and if a long follow-up needs to survive a disconnect,
put a second tmux session on just polling for completion, since a
background-task watcher tied to the driving Claude Code session dies with
that session even though the benchmark's own tmux session doesn't.

**Associativity experiment: L1 confirmed (8-way); L2/LLC blocked by a real
tool limitation, not just unconfirmed capacity — read this before trying
again.** `--experiment associativity` exists in `cache_bench`, with its own
`scripts/{run_associativity_full.sh,detect_associativity.py,
plot_associativity.py}` pipeline (mirrors capacity/line_size's shape: sweep
-> knee detection -> 2 repeats -> plots; see
`main_code/common/associativity.h`'s docstring for the method — a
node-to-node stride fixed at a cache level's own capacity forces every
probed node into the same set with a distinct tag, so sweeping how many
nodes are chased finds the hit->thrashing knee = associativity for that
level). Default sweep range (`main.c`'s `DEFAULT_MAX_WAYS`,
`run_associativity_full.sh`'s `MAX_WAYS`) was lowered from 64 to 32 on
2026-09-11, then raised to **40** later the same day after external
review of the pipeline (see the pipeline-hardening bullet just below):
real L1/L2/LLC associativities on modern x86/ARM never reach the low
20s, so 32 already had margin, but 40 buys a bit more headroom against
the still-unresolved L2/LLC confound question below for cheap extra wall
time (the whole sweep is still <40 points either way).

**Pipeline hardening from external review (2026-09-11), applied to
`run_associativity_full.sh`/`detect_associativity.py`/
`associativity.h` — read before trusting a NEW associativity run's
numbers; results collected before this date (Sunbird's L1/L2-candidate
data) were not regenerated under these changes, but the L1 result was
independently spot-checked against them and is unaffected (see below):**
- Reproducibility repeats now use a distinct seed per repeat
  (`base_seed + repeat_index`), not one fixed seed for every run. A fixed
  seed for "independent" repeats only re-checks system-noise
  reproducibility, not sensitivity to the dependent chase's access
  *order* — real replacement policies are commonly pseudo-LRU trees, not
  true LRU, and PLRU's eviction behavior (and thus where a knee lands) can
  be order-dependent, not just working-set-size-dependent.
- Repeats now always run, even when the base sweep finds no knee — a "no
  knee" result needs its own reproducibility check (it could be a
  borderline miss on one run, not genuinely "associativity >= max_ways" or
  "wrong cache_bytes"). The script now also flags disagreement between the
  base estimate and any repeat's estimate instead of silently reporting
  just the base number.
- `--cache-bytes` auto-detection (round-to-power-of-two from a capacity
  boundary) is now gated behind an explicit `ASSOC_ALLOW_AUTO=1`
  environment variable for exploratory runs only; a run without it and
  without an explicit `cache_bytes_csv` now hard-fails rather than
  silently falling back to an unconfirmed value. Final/reportable numbers
  must come from a hand-confirmed `cache_bytes_csv` (as Sunbird's L1 run
  already did).
- Processed per-num_ways summary CSVs (`base_random_summary.csv`,
  `rep1_random_summary.csv`, etc.) are now timestamped per run
  (`..._summary_<ts>.csv`) instead of being silently overwritten by the
  next run on the same machine/level — same rationale as Artemisia's
  core20-vs-core23 archival: repeat history is itself evidence, not just
  something to regenerate and discard.
- `detect_associativity.py`'s conversion of a detected "first thrashing at
  num_ways=A+1" knee into "reported associativity = A" was checked against
  the math and against Sunbird's hand-confirmed L1 result (flat through 8,
  step at 9 → reports 8) — it was already correct; a comment was added at
  the point of computation (`associativity = points[knee_idx - 1][0]`)
  making this explicit rather than leaving it implicit.
- `associativity.h`'s docstring gained a second "known limitation"
  paragraph: besides the existing physically-indexed-LLC-with-scattered-
  pages caveat, a sliced LLC with a non-trivial hash-based slice-selection
  function (common on modern x86) could also make a `cache_bytes` stride
  land in a different slice than the naive same-set assumption expects —
  a second, so-far-unruled-out candidate explanation for the same
  multi-step/no-knee L2/LLC symptom the DTLB-aliasing hypothesis below was
  written to explain. Both remain open; same Phase I discipline applies
  (timing-inference only, no hardware hash/slice lookups).

- **L1 = 8-way, hand-confirmed.** Ran on Sunbird core 2 at cache_bytes=32768
  (hand-confirmed L1 capacity): flat through num_ways=8, sharp step at 9,
  0% run-to-run spread across 3 runs. See `data_raw/sunbird/associativity/L1/`,
  documented in `data_raw/sunbird/README.md`.
- **Upgrade corroborates: L1 = 8-way there too (2026-09-12).** Ran
  `./scripts/run_associativity_full.sh upgrade 5 32768` (core 5, the same
  core as Upgrade's capacity run) using Upgrade's own PROVISIONAL 32,768 B
  L1 candidate as an explicit override (L2/LLC skipped — not yet confirmed
  on this machine, see the capacity bullet above). Same sharp-knee shape as
  Sunbird: flat ~6.0-6.2 ticks/access through num_ways=8, jump to ~15-19 at
  9+, identical estimate (8) from the base sweep and both reproducibility
  repeats. Second machine, second CPU vendor generation (Coffee Lake vs.
  Sunbird's), same clean 8-way result — and this associativity knee is
  itself the corroboration that promotes Upgrade's capacity-only L1
  boundary from provisional to confirmed (same logic Sunbird's own writeup
  used). See `data_raw/upgrade/README.md`'s associativity/ section and
  `data_processed/upgrade/associativity/L1/plots/`.
- **Evidence for a real L2 exists (~25-27 ticks/access hit latency,
  corroborated 3 independent ways), but its capacity/associativity is NOT
  resolved.** The original L1 test's own post-thrashing latency (num_ways
  10-37 at cache_bytes=32768) sits at a clean, flat ~25 ticks — a third tier
  distinct from L1 (~10) and LLC (~48-51, from the capacity section). Two
  follow-up associativity attempts (256 KiB, then a slope-analysis-motivated
  128 KiB) both reproduced that same ~25-27 tick tier, but neither gave a
  clean single knee.
- **Leading hypothesis (timing-inferred, NOT hardware-confirmed — see the
  Phase I caveat below before touching this again): a virtual-memory DTLB
  confound, not the real cache, is what all 4 L2/LLC associativity attempts
  actually broke on.** `--cache-bytes` must be a power of two (`main.c`'s
  hard validation), and every power-of-two candidate tried above L1
  (128 KiB, 256 KiB, 16 MiB, 32 MiB) produced a multi-step staircase
  breaking around num_ways~4-7, instead of L1's one clean knee at 9. That
  four different candidates — meant to be testing different cache levels
  with presumably different real associativities — all broke at roughly
  the *same* small num_ways is itself the Phase-I-safe evidence for a
  shared confound: a genuine cache level's associativity doesn't change
  because you guessed a different capacity for it, so something else with
  its own small, fixed way-count is the more likely common cause. The DTLB
  is the natural suspect because every "node" in this experiment lives on
  its own page (`cache_bytes` is always a multiple of 4096), so this
  experiment necessarily also exercises the DTLB, not just whichever data
  cache level it's aimed at.
- **Why this doesn't retroactively cast doubt on the clean L1 result — the
  mechanism, in variables, no hardware lookup required.** Say the DTLB has
  `S` sets and `W` ways per set (both unknown, deliberately). Node k's page
  number is `k * (cache_bytes/4096)` past the base, so which DTLB set it
  lands in cycles through `k * (cache_bytes/4096) mod S` as k increases.
  If `(cache_bytes/4096) mod S` is nonzero, consecutive nodes spread across
  more than one DTLB set, so the DTLB doesn't saturate until
  `(sets actually touched) * W` pages are resident, not just `W` — for the
  L1 stride (32,768 B = 8 pages/node) that spread evidently lines up with
  8, i.e. exactly L1's own real associativity, so the DTLB's own breaking
  point and L1's real breaking point coincide at the same num_ways. That's
  a coincidence of the specific numbers involved, not proof the DTLB was
  inactive during the L1 test — **the L1 result isn't DTLB-immune, its
  DTLB artifact just happens to land on top of the right answer.** For
  every power-of-two candidate >= 65,536 B, if `(cache_bytes/4096) mod S`
  is 0 (stride is an exact multiple of the DTLB's own set count), every
  node collides into the *same* one set with no spreading at all, so the
  DTLB saturates as soon as just `W` pages are resident — a small number,
  likely well below where a real L2/LLC's own (presumably larger)
  associativity would ever show up. That pushes the spurious knee much
  earlier than the real signal, matching the observed num_ways~4-7 breaks.
- **Phase I discipline caveat — read before repeating this line of
  investigation.** A prior pass on this hypothesis (2026-09-11) executed
  `cpuid` directly (leaf 2, the legacy cache/TLB descriptor leaf) to read
  this CPU's literal DTLB structure (it decoded to 4 KiB pages, 4-way,
  64 entries -> 16 sets, which is exactly consistent with the mechanism
  above) and wrote that up in `data_raw/sunbird/README.md` and this file
  as a confirmed root cause. **That was reverted** after re-reading
  `PROJECT 1.pdf`'s access section closely: Phase I restricts topology
  identification to an explicit whitelist (`hostname`, `uname -a`,
  `grep model name /proc/cpuinfo`, `lscpu -e=CPU,CORE,SOCKET,NODE`) and
  says "do not request cache-size fields" — `cpuid` isn't on that list,
  and leaf 2 is the exact mechanism `lscpu`'s cache columns pull from in
  the first place (the reason that command's own field list is
  restricted). The specific bytes decoded happened to be TLB-only this
  time, not L1D/L2/LLC descriptors, but the instruction executed was
  "ask the hardware to reveal its own cache/TLB descriptor table" either
  way, which is the category Phase I is walling off — the fact that this
  round only asked about the TLB doesn't make it safe. **Do not re-run a
  CPUID/`/proc/cpuinfo`-cache-field/`lscpu`-full check for this — or
  anything else cache-topology-shaped — before Phase I is frozen and
  tagged.** The reusable probe script that did this
  (`scripts/check_cpuid_tlb.c`) was deleted along with the write-ups
  citing it; nothing currently in the repo relies on it.
- **New evidence (2026-09-11): order-sensitivity re-check, using the
  hardened pipeline's per-repeat varied seeds, on the 256 KiB and 32 MiB
  candidates (the latter substituted for a requested "~30 MiB" re-test,
  since `--cache-bytes` must be an exact power of two and 31,457,280 isn't
  one).** Two new findings, both in `data_raw/sunbird/README.md`'s new
  "Order-sensitivity re-check" subsection: (1) a sharp anomaly recurs at
  exactly **num_ways=9** across every stride and seed tried on this
  machine so far (128 KiB, 256 KiB, and now 32 MiB candidates; 3 different
  seeds each on the last two) — the same way-count where the real,
  hand-confirmed L1 result breaks — which is new corroborating evidence
  for *some* shared small-way-count structure common to every stride
  (still consistent with, not proof of, the DTLB hypothesis below); (2)
  the two candidates differ in whether they're order-sensitive at all —
  256 KiB's staircase shape and detected knee genuinely shift across
  different seeds (a real access-order effect, consistent with a
  pseudo-LRU replacement policy), while 32 MiB's staircase reproduces
  essentially exactly across all three seeds (order-*independent*,
  more consistent with a page-placement/TLB-set-collision explanation
  that only cares which pages are touched). That difference means the two
  candidates most likely aren't being broken by the same confound in the
  same way — worth narrowing further before assuming one uniform
  explanation covers both.
- **Residue scan (2026-09-12): initially read as pinning the confound's
  implied set-count at S=256 — RETRACTED same day, see the falsification
  bullet right below before trusting anything about "S=256."** Tested 6
  more power-of-two `cache_bytes` candidates (512 KiB, 1/2/4/8/16 MiB =
  128/256/512/1024/2048/4096 pages-per-node) bridging the two known anchors
  (256 KiB = 64 pages/node, order-sensitive; 32 MiB = 8192 pages/node,
  order-independent), each at 3 seeds. Found a sharp, binary transition
  between 128 and 256 pages/node — clean/order-independent at 256
  pages/node and up, scattered below it — and, **because every candidate
  tested was a power of two**, initially (wrongly) read this as pinning
  S=256 under a "collides into one set at multiples of S" model. That
  reasoning was flawed: for power-of-two-only candidates, "is a multiple of
  S=256" and "is just large" are the same condition, so the experiment
  could not actually distinguish the two. See
  `data_raw/sunbird/README.md`'s "Residue scan" subsection and
  `data_processed/sunbird/associativity/residue_scan_summary/
  residue_scan_transition.png` for the (still-useful, just
  differently-interpreted) plot.
- **Falsification test + real-capacity test (2026-09-12): the S=256 model
  is wrong, AND testing at the real ~26-27 MiB LLC capacity does not
  produce a trustworthy associativity number either — the whole
  investigation is now bottlenecked on one bigger finding, below.**
  1. *Falsification test* (`main_code/common/main.c`'s hard power-of-two
     `--cache-bytes` check was relaxed to "must be a multiple of 4096,
     the page size" specifically to enable this — see that file and
     `associativity.h`): tested two NON-power-of-two candidates, 300
     pages/node (1,228,800 B) and 4200 pages/node (17,203,200 B), neither
     a multiple of 256. Result: 4200 pages/node came out completely clean
     (0 spread across 3 seeds, wall at num_ways=10) — exactly as clean as
     every multiple-of-256 candidate — directly falsifying "S=256" (a
     non-multiple should have been scattered under that model, and
     wasn't). 300 pages/node showed a genuine intermediate tier (not
     predicted cleanly either way), so the real mechanism is not simple
     linear/modular address indexing at all (real TLB/paging-structure
     hashing is often bit-XOR across several address-bit ranges on real
     hardware, which wouldn't behave like simple modular arithmetic when
     stride is varied) — this is likely not resolvable further with
     simple timing arithmetic alone.
  2. *Real-capacity test*: retested directly at three non-power-of-two
     candidates spanning the actual measured ~26-27 MiB LLC estimate
     (27,262,976 / 27,787,264 / 28,311,552 B — i.e. no more rounding to
     16/32 MiB), 3 seeds each. All three gave a clean, order-independent
     wall — but at **exactly num_ways=10, identical to nearly every other
     large-stride candidate tested this session** (10 of 13 candidates
     across 512 KiB-27 MiB, spanning a 27x byte range, break at exactly
     num_ways=10, usually preceded by the same "way=9" bump seen in 12 of
     13). A genuine capacity-driven knee should not sit at the same
     `num_ways` regardless of a 27x change in byte value — this is the
     signature of a small, fixed, page-COUNT-limited structure (~9 slots),
     not a byte-capacity cache level.
  - **Conclusion: for any stride >~1 MiB on Sunbird, this method cannot
    currently distinguish real L2/LLC associativity from this small
    universal confound — no candidate byte value fixes it, because the
    confound isn't about picking the wrong capacity, it's structural to
    the method at this stride scale (something with ~9 slots saturates
    long before any real, larger cache set would).** This is a genuine
    dead end for the current method design, not a "try more candidates"
    problem — see "What would actually need to change" below before
    repeating stride-variation attempts on another machine.
  - **This also casts new, concrete doubt on the previously-trusted L1 =
    8-way result** (`cache_bytes=32768` = 8 pages/node): that stride is
    far below the ~1 MiB threshold where this universal wall was
    characterized, and the L1 result IS the one case that's fully
    order-independent at a small page count — so it may well be a genuine,
    independent cache signal — but given how consistently a small
    fixed-entry structure has now shown up everywhere else, it is no
    longer safe to treat L1=8-way as automatically confound-free just
    because it looks clean. Flagged as unresolved, not retracted (no
    evidence has directly contradicted the L1 result itself) — a candidate
    Phase II PMU check, or a differently-designed timing test, would be
    needed to actually settle it.
  - **What would actually need to change, if this is picked back up (not
    attempted this session):** the method's core assumption — one node per
    page, stride = target capacity — seems to be what exposes every large
    stride to this small page-indexed confound. A redesign that keeps
    multiple same-set nodes on fewer distinct pages (rather than always
    one node per page) would sidestep it, but no such design has been
    worked out yet. Simply trying more candidate byte values (power-of-two
    or not) is very unlikely to help further, per the finding above.
  - Full detail: `data_raw/sunbird/README.md`'s associativity/ section, in
    particular the "Residue scan", falsification, and real-capacity-test
    subsections (search for "2026-09-12").

**New lead from Upgrade (2026-09-12): a "derived-stride scan" technique
that DOES pass the self-consistency test Sunbird's large strides all
failed — but still bottoms out on a second, not-yet-isolated structure.**
New script `scripts/run_associativity_stride_scan.sh` implements exactly
the redesign floated above ("keep multiple same-set nodes on fewer
distinct pages"): instead of `run_associativity_full.sh`'s fixed
stride = full target capacity, it tries `stride = capacity_candidate /
A_guess` for a list of candidate divisors. Any `A_guess` that evenly
divides the true associativity still yields a mathematically valid
same-set stride (same modular-arithmetic argument as
`associativity.h`'s docstring), just a smaller one — so if the *same*
knee recurs across several different `A_guess` (hence different page
counts touched), that's evidence of a real signal rather than a
page-count artifact, whereas a knee that shifts with `A_guess` is the
confound signature repeating itself.
- **Validated against known-good data first**: run at Upgrade's confirmed
  L1 stride (32,768 B) with `A_guess=1,2,4,8` all correctly recover
  knee=8 across a 200-to-25-page range — the technique and its
  self-consistency check work as designed.
- **L2 candidate (2,097,152 B, itself unconfirmed) and an LLC-region
  candidate (16,777,216 B, also unconfirmed)**: strikingly, `A_guess=1`
  through `256` (strides from the full candidate down to 65,536 B,
  400-to-102,400 pages — up to a 256x range) all report the SAME first
  knee, **4**. `A_guess=512` on the 16 MiB candidate (stride=32,768 B,
  coincidentally identical to the L1 stride) correctly falls back to
  detecting **8** instead — the scan self-detects that it has shrunk into
  L1's own set, a second unplanned validation.
- **But a full-rigor confirm run (1,000,000 samples, both patterns, 2
  repeats) at that 65,536 B stride reveals this "4" is only the first
  step of a TWO-STEP staircase, not a clean knee**: flat through ways 2-3,
  a marginal/noisy partial rise at way 4 (47% spread across the 3 runs;
  base/rep1 called it thrashing, rep2 didn't — base=4, rep1=4, rep2=3),
  a mid-plateau ways 5-8, then a second, much sharper jump at **way 9** —
  landing suspiciously close to the exact confound signature (~9-10)
  documented above from Sunbird's large-stride attempts.
  `detect_associativity.py` only ever reports the FIRST knee it finds, so
  every self-consistency result above only ever saw this marginal first
  step — none of it speaks to whether the second (~9) step is itself
  self-consistent (real, larger structure) or tracks stride/page-count
  (the same old confound, just pushed later). **Not a citable L2/LLC
  number yet, but real forward progress**: a technique that demonstrably
  works on known-good data and produces a *reproducible, non-degenerate*
  structure on unknown data, rather than immediately hitting the old
  universal ~9-10 wall the way every large fixed-capacity stride did.
- **Two concrete next steps, neither attempted yet**: (1) teach
  `detect_associativity.py` (or a sibling script) to also locate a SECOND
  knee, then re-run the stride-scan's self-consistency check specifically
  on that second knee's location across several `A_guess` values; (2) the
  marginal way=4 step needs a tighter, higher-sample re-check right at
  the ways=3-5 boundary before trusting even the first tier.
- Full detail, including the exact comparison tables:
  `data_raw/upgrade/README.md`'s associativity/ section, "L2/LLC:
  derived-stride scan" subsection. **Not yet tried on any other
  machine** — if picked up elsewhere, this Upgrade writeup (not the
  original Sunbird dead-end analysis above) is the starting point.
**Not yet started (data collection):** hit/miss latency, inclusion/
exclusion experiments — not yet implemented in `cache_bench` at all.
Line size: `--experiment line_size` exists (added by @krchen1, commit
`5aaa83f`) with its own `scripts/{run_line_size_full.sh,
run_line_size_sweep.sh,detect_line_size.py,plot_line_size.py}` pipeline;
check that machine's own `data_raw/<machine>/README.md` and recent git log
(not this paragraph) for its actual current per-machine data-collection
status, since this file lags active work in progress. PMU verification
(Phase II) and Hazel (Phase III) have not started; Phase I must be
frozen/tagged first per `README.md`.

## Known constraints from prior sessions

- Compile baseline is `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
  (see `Makefile`) — do not add optimization or drop `-g`/frame-pointer
  without updating the disassembly-inspection evidence too.
- Every `cache_bench` run must be pinned with `taskset -c <core>` (or
  `srun --cpu-bind=cores` on Hazel) — check `Cpus_allowed_list` and
  `lscpu -e=CPU,CORE,SOCKET,NODE` first to pick a full physical core (both
  SMT siblings) actually available to your session, and check `who`/`ps`
  for other students' active processes on this shared machine before
  assuming a core is quiet. On Artemisia this wasn't enough on its own —
  the actual per-core load only showed up via `/proc/stat` idle-time deltas
  over a few seconds; `ps`'s point-in-time snapshot both missed a busy core
  and flagged an idle one as busy due to a since-finished process. Sample
  `/proc/stat`, don't just trust one `ps` snapshot.
- `scripts/plot_capacity.py` combines overlapping (pattern, size) rows
  across input summary CSVs by averaging rather than letting the last
  file win — this matters because dense/repeat sweeps sharing a log-spaced
  grid will legitimately collide on many exact sizes. On a shared machine
  this averaging can be misleading if the overlapping runs span a large
  time gap (see Artemisia's Anomaly 2) — check whether high spread at a
  point is per-run-noise or a session-level split before trusting the
  combined median.
- Long dense sweeps (anything covering ~100+ MiB working sets at the
  `random` pattern) cost real wall time — roughly an hour per full sweep at
  the default sample count, since random-pattern latency is dominated by
  genuine uncached DRAM access with no prefetch help (~8x slower than the
  `sequential` pattern at the same size). Run anything in this range inside
  `tmux` (`tmux new-session -d -s <name> '<script> 2>&1 | tee -a <log>'`)
  so it survives the driving session disconnecting, and poll the log file
  for a completion sentinel rather than relying on harness-managed
  background-task tracking alone.
- `cache_bench --experiment associativity`'s `--cache-bytes` argument is
  hard-validated as an exact power of two (`main.c`'s `(cache_bytes &
  (cache_bytes - 1)) != 0` check) — a capacity estimate from a soft/gradual
  capacity-sweep knee (not a clean round number) will be rejected outright,
  not just accepted-but-imprecise. Round to the nearest power of two before
  attempting an associativity run at a boundary that isn't already one
  (see Sunbird's ~26-27 MiB LLC estimate -> tested at 16 MiB and 32 MiB
  instead, `data_raw/sunbird/README.md`).
- A dense capacity sweep started right at the left edge of the size range
  you actually care about can show a spurious "shelf" from CPU
  frequency-ramp-up (the first several points run at a lower clock before
  settling into steady-state turbo, elevating ticks/access in a way that
  decays over the first few dozen points — not a cache effect). Confirmed
  on Sunbird: a 128-512 KiB sweep starting at 131,072 B falsely showed a
  clean plateau at ~133-173 KiB; restarting the same sweep from a colder
  65,536 B start resolved it as one continuous ramp with no shelf at all.
  Start dense sweeps meaningfully below the region of actual interest, not
  exactly at its left edge.
