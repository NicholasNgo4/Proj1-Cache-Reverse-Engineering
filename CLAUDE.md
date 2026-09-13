# Project: HW1 Cache Reverse Engineering (ECE 592, Fall 2026)

See `README.md` for full project structure, build/run commands, and the
Phase I/II/III discipline (non-negotiable — read it before running anything
involving `perf`, PMU, or cache-topology files). This file is for a fresh
Claude Code session (e.g. after SSHing into a different lab machine) to
pick up current progress without re-deriving it. Note: a Claude session's
conversation history and memory do NOT transfer between machines (each
lab machine has its own local `/home`, confirmed not NFS-shared) — this
file, the repo's data/READMEs, and git history are the only things that do.
**For capacity boundary values specifically, `CAPACITY_RESULTS.md` is
authoritative — see the note at the top of "Current status" below.**

## Current status (update this section as work progresses)

**`CAPACITY_RESULTS.md` is the single source of truth for every machine's
capacity boundaries (L1/L2/LLC) — read it, not the narrative below, before
picking a boundary value for ANY downstream experiment (line size,
associativity, hit/miss latency, inclusion/exclusion).** The per-machine
capacity write-ups further down in this section (and the associativity
section's boundary discussion) predate a correction: this file's own
documented numbers/retractions turned out not to be accurate, and the user
directly transcribed the real per-machine boundary values from the actual
plotted graphs into `CAPACITY_RESULTS.md` (2026-09-13) to fix that. Where
this file's prose below disagrees with `CAPACITY_RESULTS.md` (e.g. a
boundary this file calls "retracted"/"not a genuine boundary" that
`CAPACITY_RESULTS.md` lists as a real per-machine value, or a byte value
that differs), **`CAPACITY_RESULTS.md` wins, unconditionally** — do not
resurrect a value this file argued for over what's in that table, and do
not re-litigate a `CAPACITY_RESULTS.md` value against this file's older
reasoning. Treat everything below as historical investigation narrative
(the reasoning/anomalies/methodology are still useful context) but always
resolve the actual boundary number from `CAPACITY_RESULTS.md`.

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

**Associativity experiment: L1 confirmed (8-way, x86; 4-way, ARM/Thunderbird);
L2/LLC blocked by a real tool limitation, not just unconfirmed capacity —
read this before trying again. Now reproduced on 3 machines (Sunbird,
Upgrade, Thunderbird), across 2 architectures — see the Thunderbird bullet
near the end of this section.** `--experiment associativity` exists in `cache_bench`, with its own
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

**2026-09-12, same day: a manually-curated `CAPACITY_RESULTS.md` (hand
reconciling every machine's capacity README into one L1/L2/LLC table) was
used to re-run `run_associativity_full.sh` for all 3 levels on Upgrade —
L2/LLC reproduced the same confound, not new data.** This session's shell
only had access to Upgrade (each lab machine is a separate, non-shared
`/home` — see the top of this file), so only Upgrade was run; the other 7
machines still need the same command (with their own CAPACITY_RESULTS.md
row) run from a session on that machine. Command:
`./scripts/run_associativity_full.sh upgrade 5 32768,262144,16777216`
(LLC's ~12 MiB candidate rounded to the nearest power of two, 16 MiB —
required by `--cache-bytes`'s hard power-of-two check — see the correction
right below before repeating this rounding step elsewhere). Result: **L1
reconfirmed at 8-way** (identical to the original run). **L2 (262,144 B)
and LLC (16,777,216 B) both again hit the same universal small-way-count
wall already documented above** — near-identical staircases 64x apart in
byte size (steps at way~5, way~9, then a further gradual climb from
way~20), LLC's repeats even disagreeing with each other (3 vs. 4) the way
a genuinely unresolved confound would. **Do not cite "L2 = 4-way" or
"LLC = 4-way" for Upgrade** — this is the same dead end, encountered from
a new starting byte value, not an independent confirmation. The 3
requested plots (L1/L2/L3_LLC) were generated regardless (per the
assignment's ask for one graph per level), but the L2/LLC ones carry an
explicit "CONFOUND SUSPECTED" caption instead of a false knee marker. Full
detail: `data_raw/upgrade/README.md`'s associativity/ section, "CAPACITY_
RESULTS.md run" subsection.

**Correction to the note just above: `--cache-bytes` no longer requires a
power of two.** That check was relaxed to "must be a multiple of 4096, the
page size" earlier the same day (2026-09-12), specifically to enable the
falsification test documented further up this section (see
`main_code/common/main.c`'s `ASSOC_CACHE_BYTES_ALIGN` and `associativity.h`)
— current `main.c` does not hard-require a power of two. The Upgrade run
above rounding its ~12 MiB LLC candidate to 16 MiB wasn't necessary by the
time it ran; harmless here (it's already deep in confound territory
either way), but a future session shouldn't round a `CAPACITY_RESULTS.md`
byte value to the nearest power of two before checking whether it's
already a valid multiple of 4096 on its own (as Thunderbird's ~30 MiB
LLC value, 31,457,280 B, was — see the Thunderbird bullet below).

**Thunderbird (2026-09-12): the same universal large-stride wall now shows
up on a THIRD machine and a different architecture (ARM, not just x86) —
cross-architecture evidence this confound isn't x86/DTLB-microarchitecture-
specific.** Ran `scripts/run_associativity_full.sh thunderbird 4
65536,1048576,31457280` (fixed-full-capacity-stride method, not yet the
derived-stride-scan technique above) using `CAPACITY_RESULTS.md`'s
consolidated L1/L2/LLC values for this machine (64 KiB / 1 MiB / ~30 MiB —
note this is a different, newer source file than the
`CAPACITY_INFERENCE_STATUS.md` gate cited throughout the rest of this
section; see the sourcing note below). Needed the same
`--min-abs-ticks` rescaling already documented for Thunderbird's capacity
detector (25 MHz `CNTVCT_EL0` keeps every level's ticks/access under ~1.1,
below `detect_associativity.py`'s x86-calibrated default of 3.0) before
any knee showed up at all.
- **L1 = 4-way, reproducible across base + both repeat seeds** (`--min-abs-ticks 0.05`):
  clean single knee, flat ~0.13 ticks through num_ways=4, jump to ~0.23 at 5.
  Not suspicious on the same grounds the Sunbird/Upgrade L1 results
  aren't (small stride, well below the "~1 MiB+" regime where the
  universal wall was characterized) — though per the caveat already
  written above for Sunbird's own L1 result, "clean and small-stride"
  is evidence of *not being confound-poisoned*, not proof of a genuine
  independent signal.
- **L2 (1,048,576 B) and LLC (31,457,280 B) both hit the wall, not each
  level's own associativity.** Both strides are exact multiples of L1's
  own 65,536 B (16x and 480x), so even the SMALL first bump in their
  curves is just L1's own thrashing re-triggering, not signal from the
  level under test — the real second knee only appears after raising
  `--min-abs-ticks` enough to skip that spurious bump (0.25 for L2, 0.2
  for LLC). That second knee lands at effectively the **same num_ways for
  both levels (L2: 11-way base / 12-way both repeats; LLC: 10-way, fully
  reproducible)** despite a 30x difference in byte capacity between them —
  the identical "two structurally different levels break at the same
  num_ways" signature already used above (Sunbird/Upgrade) as the core
  evidence for a shared confound rather than real associativity. **10-12
  is also strikingly close to Sunbird/Upgrade's own ~9-10 wall** — worth
  noting as a candidate shared-magnitude data point if this investigation
  is ever resumed with the derived-stride-scan technique on this machine,
  but not proof of exact equality (different CPU, different node size in
  bytes, no PMU cross-check yet).
- **Not yet attempted here:** the derived-stride-scan technique
  (`scripts/run_associativity_stride_scan.sh`) that produced Upgrade's more
  rigorous (if still unresolved) L2/LLC self-consistency result — this
  Thunderbird run only used the plain fixed-full-capacity-stride method,
  per the associativity graphs actually requested this session. Full
  detail, exact thresholds, and the raw per-num_ways tables:
  `data_raw/thunderbird/README.md`'s associativity/ section. Three plots:
  `data_processed/thunderbird/associativity/{L1,L2,L3_LLC}/plots/
  associativity_curve.{png,pdf}` (+ boxplots).
- **Sourcing note (applies beyond just this bullet):** as of 2026-09-12,
  `CAPACITY_RESULTS.md` (one concrete number per machine/level, no
  caveat column filled in) and the older `CAPACITY_INFERENCE_STATUS.md`
  (the PROVISIONAL/UNRESOLVED/CONTAMINATED confidence-tier gate this
  whole associativity section otherwise assumes) disagree in places —
  e.g. the gate file marks most machines' L2/LLC UNRESOLVED or
  PROVISIONAL-WEAK, while `CAPACITY_RESULTS.md` just states a number.
  This Thunderbird run used `CAPACITY_RESULTS.md`'s numbers on explicit
  instruction that it supersedes the gate file for this purpose, but the
  gate file's underlying per-machine warnings haven't been individually
  re-litigated — a future session extending associativity to another
  machine via `CAPACITY_RESULTS.md` should still sanity-check that row
  against the machine's own `data_raw/<machine>/README.md` first, the way
  this session's threshold-rescaling check did for Thunderbird.

**Charnwood (2026-09-12): L1 confirmed 8-way (3rd machine to agree, after
Sunbird and Upgrade); L2/LLC run produced a new, unusually direct A/B
confirmation of the shared-confound hypothesis, not a resolved number.** A
separate session (this machine's own `/home` is not shared with Upgrade's
or Thunderbird's) ran
`./scripts/run_associativity_full.sh charnwood 3 32768,262144,8388608`
(core 3, verified quiet first — the contending `associativity` process from
the capacity run had since exited) using L1/L2/LLC bytes taken directly from
`CAPACITY_RESULTS.md`'s cross-machine table (per explicit instruction to use
that consolidated, hand-picked table rather than re-deriving from
Charnwood's own capacity data, which independently flags the ~1.83-11.31 MiB
L2/LLC region as contaminated/unresolved — see `data_raw/charnwood/README.md`
capacity/ section; same `CAPACITY_RESULTS.md` vs. `CAPACITY_INFERENCE_
STATUS.md` sourcing caveat as the note just above applies here too). Full
detail and results table: `data_raw/charnwood/README.md`'s associativity/
section.
- **L1 = 8-way**, clean single knee, 0 disagreement across base + 2 repeats
  — same shape and number as Sunbird's and Upgrade's hand-confirmed results.
  Third machine, third result, still 8.
- **L2 (256 KiB) and LLC (8 MiB) both report "4"** from a multi-step
  staircase (jump at num_ways=4, sharper jump at num_ways=9 — the same
  anomalous "9" already documented recurring on Sunbird — then a noisy climb
  from ~num_ways=24 on), not a single knee; `detect_associativity.py` only
  ever surfaces the first step.
- **New evidence, cleaner than anything the Sunbird/Upgrade/Thunderbird
  investigations produced so far: the L2 and LLC median-latency curves are
  numerically indistinguishable (agree to within ~0.05 ticks/access) at
  every num_ways from 2 through 23**, despite a 32x difference in the
  candidate byte capacity (262,144 vs. 8,388,608). Two real, distinct cache
  levels probed at their own real capacities have no mechanism to produce
  identical curves — this is on-this-machine, same-run, A/B-comparable
  proof that both runs are dominated by one small, capacity-independent
  structure (leading suspect unchanged: the DTLB, since `cache_bytes` here
  is always a multiple of 4096 regardless of which data-cache level it
  nominally targets), not the real L2 or LLC. Treat "L2 assoc = 4" and
  "LLC assoc = 4" for Charnwood as reproducible-but-not-resolved, same
  status as every other machine's L2/LLC associativity attempt so far — do
  not cite either number as this machine's real associativity.
- Does not change the open-questions list from the Sunbird/Upgrade
  writeups above: the derived-stride-scan technique in
  `scripts/run_associativity_stride_scan.sh` remains the only proposed way
  forward and has not been tried on Charnwood.
- Three plots (L1/L2/L3_LLC curves + boxplots) generated regardless, per
  the assignment's ask for one graph per level:
  `data_processed/charnwood/associativity/{L1,L2,L3_LLC}/plots/
  associativity_curve.{png,pdf}`.

**Artemisia (2026-09-12): confound reproduced on a FIFTH machine (Sapphire
Rapids, the newest/most architecturally distant CPU on the team's list) —
arguably the cleanest demonstration yet that L2/LLC associativity isn't
resolvable with the current method, independent of which capacity value is
picked.** Ran
`./scripts/run_associativity_full.sh artemisia 4 49152,2097152,31457280`
using this session's `CAPACITY_RESULTS.md` values (L1=48 KiB, L2=2 MiB,
LLC=~30 MiB) — note L2's value (2,097,152 B) is the exact byte value
Artemisia's own capacity README already flags as NOT a real boundary (a
waypoint inside one continuous ~48 KiB-90 MiB ramp with no discrete L2/L3
shelf found on two independent runs); ran anyway per explicit instruction,
documented honestly rather than blocked on it.
- **L1: not cleanly confirmed** (unlike Sunbird/Upgrade/Charnwood's L1=8-
  way — this machine's real L1D is 48 KiB, not 32 KiB, so a different
  way-count is expected anyway). Base + repeat 1 both detect knee=12;
  repeat 2's detector reports 3, but that's a false positive from the same
  per-invocation P-state/turbo bimodal noise already documented for this
  machine's small-buffer capacity data (Anomaly 1) — all three runs,
  including repeat 2, actually transition cleanly to a low-spread
  ~16.2 ticks/access shelf at exactly num_ways=13. Plausibly
  associativity=12 (physically ordinary for a 48 KiB L1D) but not
  machine-confirmed, especially given a second, unexplained jump from
  ~16.2 to ~23 ticks/access around num_ways~25-29 that no existing
  hypothesis here accounts for yet.
- **L2 and LLC: nearly IDENTICAL curves despite a 15x stride difference
  (2 MiB vs 30 MiB)** — noisy through num_ways~6, a clean plateau at
  ~11.2-12.1 ticks through num_ways=7-12, then a jump to the SAME ~23-tick
  ceiling seen in L1's final plateau, for both levels, at every point.
  Detected knee: L2 base=6/rep1=5/rep2=6 (disagreement flagged); LLC
  base=rep1=rep2=6 (3/3 agreement, but meaningless given the identical-
  curves finding). Same "two structurally different levels break at the
  same num_ways, with numerically indistinguishable curves" signature as
  Charnwood's above and Sunbird's/Upgrade's/Thunderbird's large-stride
  attempts. **Do not cite an L2 or LLC associativity number from this
  run.** Three graphs were generated as requested
  (`data_processed/artemisia/associativity/{L1,L2,L3_LLC}/plots/
  associativity_curve.png`) but the L2/LLC ones depict this confound, not
  a resolved cache-level associativity.
- **New, not-yet-tried lead surfaced by this run**: `--huge-pages` already
  exists in `cache_bench`/`associativity.c` (collapses the whole probe
  buffer onto a single 2 MiB huge page / one TLB entry, added at some
  point after the DTLB hypothesis was first written up above, apparently
  never exercised on any machine) — directly tests the DTLB-aliasing
  hypothesis by construction, but is not wired into
  `run_associativity_full.sh` yet. Natural next step before trying more
  candidate byte values on any machine. Full detail:
  `data_raw/artemisia/README.md`'s associativity/ section.

**Running tally after Sunbird/Upgrade/Thunderbird/Charnwood/Artemisia:
every machine tried so far reproduces the same shape at L2/LLC (two byte-
capacity candidates spanning a large multiplier breaking at the same
num_ways, often with numerically indistinguishable curves), and every
machine's L1 comes back clean-ish at a small, plausible way-count (8 on
three x86 machines, 4 on ARM Thunderbird, a less-certain 12 on Artemisia's
48 KiB L1). No machine has yet produced a citable L2 or LLC associativity
number via the fixed-full-capacity-stride method** — only the derived-
stride-scan technique (validated on Upgrade's L1, inconclusive on Upgrade's
L2/LLC, untried elsewhere) and the not-yet-tried `--huge-pages` TLB-control
flag have shown any sign of a way forward. Remaining machines (Crux,
Skylark, Ookay — commits for these landed upstream around the same time as
this Artemisia run; check their own `data_raw/<machine>/README.md` rather
than assuming this paragraph is current) should expect the same outcome
absent a method change — worth reading this whole section before spending
a full session re-discovering it per machine.

**Hit latency and miss/next-level latency: implemented 2026-09-13
(`--experiment hit_latency` / `--experiment miss_latency` in
`main_code/common/latency.c`/`.h`), first data collected on Sunbird only.**
Pipeline: `scripts/run_hit_latency_full.sh` / `scripts/run_miss_latency_full.sh`
+ `scripts/plot_{hit,miss}_latency.py` (no `detect_*.py` for either — there's
no knee to find, just direct numbers per level/transition). Both footprint/
target/evict byte values MUST come from `CAPACITY_RESULTS.md` only (see the
note at the top of this "Current status" section) — do not use this file's
own per-machine capacity prose to pick them.
- **Sunbird** (`data_raw/sunbird/latency/`): hit latency at L1/L2/LLC/DRAM
  (32,768 / 262,144 / 31,457,280 / 536,870,912 B) gives a clean, monotonic
  4-tier ladder — L1≈10.4, L2≈26.8, LLC≈58.4, DRAM≈207 ticks (dependent,
  random, median) — with the required independent-load control measuring
  faster than dependent at every level and both patterns (confirms MLP is
  correctly exposed, not hidden). A real bug was caught and fixed here:
  the independent-load timer initially ignored `--pattern` entirely
  (always used a random address permutation), making a `sequential`+
  `independent` run measure slower than `sequential`+`dependent` — fixed
  so independent-mode addressing follows `--pattern` too, exactly like
  every other experiment's chase construction; see
  `main_code/common/benchmark.c`'s `measure_independent_loads_batched()`.
  Miss/next-level latency at L1→L2/L2→LLC/LLC→DRAM gives an increasing
  124/284/622-tick sequence (random, median) — but a dedicated control
  test found this experiment's single-shot (non-batched) timing carries a
  ~64-85 tick FIXED measurement overhead on this machine (confirmed via an
  eviction set too small to actually evict the target most of the time,
  which still measured far above the true ~10-tick L1 hit latency) — so
  these numbers are "real reload latency + fixed overhead", not clean
  numbers; see `main_code/common/latency.h`'s `run_miss_latency_experiment`
  docstring ("KNOWN LIMITATION") and `data_raw/sunbird/README.md`'s
  latency/ section for the full write-up, including two of three
  transitions showing substantial (26-60%) unexplained repeat-to-repeat
  spread not yet traced to a specific cause. **Not yet run on any other
  machine.**
- **Ookay** (`data_raw/ookay/latency/`, 2026-09-13, unattended run): hit
  latency at L1/L2/LLC/DRAM (32,768 / 262,144 / 8,388,608 / 536,870,912 B,
  LLC converted from `CAPACITY_RESULTS.md`'s "~8 MiB" as `8*1,048,576`)
  gives a clean, monotonic 4-tier ladder — L1≈7.49, L2≈18.53, LLC≈74.78,
  DRAM≈284.45 ticks (dependent, random, median). The pipeline's own
  independent-vs-dependent check flagged 2 of 8 cells UNEXPECTED (LLC and
  DRAM, sequential pattern only) — investigated rather than ignored: root
  cause is the hardware prefetcher fully hiding the sequential (stride-1)
  pattern at every footprint tested, collapsing both load modes to the
  same ~L1-speed floor (~7.7-7.9 ticks) regardless of level, so the
  "inversion" is sub-tick noise around a shared floor, not a broken
  measurement — LLC/DRAM sequential-pattern numbers should not be cited as
  real LLC/DRAM latency, only the random-pattern numbers should. Miss/
  next-level latency at L1→L2/L2→LLC/LLC→DRAM gives 96/723/693 ticks
  (random, median) — not monotonic (LLC→DRAM ≈ L2→LLC despite evicting one
  level further) and 4 of 6 (transition, pattern) cells showed >20%
  run-to-run spread, not resolved this session (core re-verified idle
  before/after but not monitored continuously during the run; leading
  candidate is `L2_to_LLC`'s evict_bytes sitting at exactly the LLC
  capacity estimate rather than past it with margin, not confirmed
  further). Same fixed single-shot overhead caveat as Sunbird applies,
  independently measured on this machine at ~58.5 ticks (control median 66
  vs. L1 hit-latency median 7.49) — even after subtracting it, L2→LLC and
  LLC→DRAM remain far above their own hit-latency plateaus, so real
  reload cost is elevated beyond fixed overhead alone, unresolved. See
  `data_raw/ookay/README.md`'s latency/ section for full detail.
- **Skylark** (`data_raw/skylark/latency/`, run 2026-09-13, unattended):
  hit latency at L1/L2/LLC/DRAM (32,768 / 524,288 / 8,388,608 / 536,870,912
  B) gives a clean, monotonic 4-tier ladder — L1≈6.2, L2≈16.2, LLC≈27.2,
  DRAM≈274.9 ticks (dependent, random, median) — independent-load control
  measured faster than dependent at every level/pattern, no
  `[UNEXPECTED]` flags. Miss/next-level latency at L1→L2/L2→LLC/LLC→DRAM
  (evict-bytes 524,288 / 8,388,608 / 16,777,216 — the last one picked after
  a timing calibration showed ~67.7ms/trial at 2x LLC capacity, well under
  budget) gives an increasing 96/120/360-tick sequence (random, median);
  L1→L2 and L2→LLC showed >20% repeat-to-repeat spread (21.4%/40.0%,
  flagged by the plot script, not re-run to chase away) while LLC→DRAM did
  not (~6.4%). Same single-shot fixed-overhead issue as Sunbird, isolated
  here too via the same tiny-eviction-set control: ~72-tick median vs.
  Skylark's own ~6.2-tick batched L1 hit latency → **~65.8 ticks fixed
  overhead**, consistent with Sunbird's ~64-85 tick range on different
  hardware. See `data_raw/skylark/README.md`'s latency/ section for the
  overhead-corrected approximate incremental penalties (~24/38/267 ticks)
  and full run detail.

**Inclusion/exclusion: implemented 2026-09-13 (`--experiment
inclusion_policy` in `main_code/common/inclusion_policy.c`/`.h`), first
(preliminary, uncertain-verdict) data collected on Sunbird only.** Pipeline:
`scripts/run_inclusion_policy_full.sh` + `scripts/classify_inclusion_policy.py`
+ `scripts/plot_inclusion_policy.py`. Method (see `inclusion_policy.h`'s
module doc comment for the full argument): target + an untouched control
line are freshly page-aligned; the eviction buffer places one node per
page, all at one FIXED sub-page offset different from target/control's own
(offset 0) — spans many pages (hence many lower-level sets) while
structurally never landing on target's own upper-level line, PROVIDED the
upper level's index fits within one page (true for a typical L1; NOT
reliable for an L2-or-bigger target). Classification compares the raw
per-trial reload latency against two SINGLE-SHOT calibration numbers (not
batched hit_latency medians, which would be systematically biased low by
missing the single-shot overhead documented in `latency.h`): a "survived"
class calibrated fresh each run (trivially-small eviction, nothing actually
evicted) and an "invalidated" class read from this machine's own
already-collected `miss_latency` data for the matching transition.
- **Three load-bearing caveats, deliberately left unresolved this pass (see
  `data_raw/sunbird/README.md`'s inclusion_policy/ section for the full
  writeup):** (1) the eviction buffer touches only one cache line per page,
  so exerting genuinely comparable pressure to a dense buffer requires
  scaling the lower level's byte capacity up by `page_size/line_size` —
  line_size data isn't available yet, so `run_inclusion_policy_full.sh`
  uses a **documented, unverified assumption of 64 B**; (2) touching enough
  distinct pages to do that scaling (Sunbird's L2-vs-LLC and L1-vs-LLC
  pairings: ~491,520 pages, ~1.9 GiB eviction footprint each; the L1-vs-L2
  pairing is far smaller, ~4,096 pages/16 MiB, and less exposed to this)
  risks blowing the DTLB regardless of any real cache eviction — the
  `control` channel is a live per-run check for this; (3) the "avoids the
  upper level's own set" guarantee only holds when the target's full index
  fits within one page — plausible for an L1 target, essentially never true
  for an L2 target, so any pairing testing an L2 target (L2_vs_LLC) should
  be read with the LEAST confidence of the three. A proper DTLB mitigation
  (huge-pages backing for the eviction buffer, mirroring `associativity.c`'s
  existing `--huge-pages` diagnostic) was identified as a next step and NOT
  implemented here — flagged, not solved.
- **Sunbird** (`data_raw/sunbird/inclusion_policy/{L1_vs_L2,L2_vs_LLC,L1_vs_LLC}/`):
  all three level pairings CAPACITY_RESULTS.md's L1/L2/LLC boundaries imply
  were run, each with its own single-shot calibration and its own confidence
  level:
  - **L1_vs_L2** (target=L1 32,768 B, eviction past L2 262,144 B): target
    90.0% survived-like (median 84 ticks), control 92.0% survived-like
    (median 68), paired-slower 96.5%. **Verdict: EXCLUSIVE / NON-INCLUSIVE**
    — the cleanest, most confident result of the three, and the least
    exposed to caveats 2-3 above (small eviction footprint, L1-sized target).
  - **L1_vs_LLC** (target=L1, eviction past LLC ≈30 MiB): target 75.0%
    invalidated-like (median 236, vs. 60-tick survived/622-tick invalidated
    calibration), control 97.5% survived-like (median 136), paired-slower
    98.5%. **Verdict: UNCERTAIN** — target's fraction falls just short of
    the 80% threshold for a firm call; read as strong evidence leaning
    inclusive, not a clean classification. Control stayed clean here, so
    caveat 2 looks like a minor factor for this specific pairing.
  - **L2_vs_LLC** (target=L2 262,144 B, eviction past LLC): target only
    13.5% survived-like / 1.5% invalidated-like (85.0% ambiguous, median
    212 vs. 76-tick survived/622-tick invalidated calibration), control
    96.5% survived-like (median 144), paired-slower 92.0%. **Verdict:
    UNCERTAIN**, and the least trustworthy of the three per caveat 3 — an
    L2 target gets no structural avoidance guarantee, so this pairing's
    numbers may just reflect ordinary incidental L2 eviction from the walk,
    not evidence about LLC's actual policy. Also: its target/sequential box
    showed 80% run-to-run spread, the widest disagreement of any
    inclusion_policy run so far, not yet investigated.
  - Do not cite any of these as a settled "Sunbird's cache is
    inclusive/exclusive" claim without first addressing the three caveats
    above and the "repeat with multiple target sets/addresses" requirement
    (every run above tested exactly one target buffer per repeat, just
    re-seeded). One further unexplained anomaly, L1_vs_LLC run only: its
    control/sequential box showed 77% spread (max ~756 ticks), not yet
    investigated. **Not yet run on any other machine.**
  - **Synthesis update (2026-09-13, no new runs — resolved/sharpened the
    caveats above using line_size data that now exists for Sunbird):**
    caveat 1 (assumed 64B line size) is confirmed correct, not just assumed
    (Sunbird's line_size/ section independently confirmed 64B at all 3
    footprints on 2026-09-11, before this experiment existed) — the
    eviction-footprint math for L1_vs_L2/L1_vs_LLC was already right, no
    re-run needed; `run_inclusion_policy_full.sh`'s stale "documented
    assumption, not measured" wording was corrected to say so. Caveat 3
    (L2 target's index may not fit in one page) is now a math-backed
    structural argument, not just a suspicion: L1's confirmed 64 sets x
    64B lines = exactly one page (12 bits), which is why the method works
    for an L1 target; any bigger level needs more sets than fit in that
    remaining space, so L2_vs_LLC is very likely unfixable by more repeats
    under this design. **Best-guess overall reading, combining all three
    pairings:** L1 is confidently non-inclusive w.r.t. L2, and the L1-vs-LLC
    skip-level result leans inclusive (just under the confidence threshold)
    — a pattern consistent with a non-inclusive L2 alongside an LLC that
    behaves inclusively toward L1 (acting as a cross-core inclusion/snoop
    directory), though L2_vs_LLC's own ambiguity can't confirm or deny this.
    Full writeup and caveats: `data_raw/sunbird/README.md`'s inclusion_policy/
    "Best-guess synthesis" subsection. The assignment-required final inferred
    cache table itself (level/size/line size/associativity/derived sets/hit
    latency/miss latency/sharing scope/inclusion behavior) for Sunbird now
    lives at `data_processed/sunbird/FINAL_CACHE_TABLE.md`, alongside this
    machine's other processed benchmark outputs (moved there 2026-09-13 at
    the user's request, so it sits next to `capacity/`, `line_size/`,
    `associativity/`, `latency/`, `inclusion_policy/` rather than in the
    data_raw README).

**Skylark (2026-09-13): inclusion_policy run completed, Phase I closed out
for this machine — FINAL_CACHE_TABLE.md now exists alongside Sunbird's.**
Ran both remaining pairings-pass invocations (`run_inclusion_policy_full.sh`
now supports a per-invocation `ASSUMED_LINE_SIZE_BYTES` env-var override,
used here because this machine's own line_size/ section found a genuine 2x
disagreement — 64B at L1, 128B at the deep LLC-region transition — so
L1_vs_L2 was run at 64B and L2_vs_LLC/L1_vs_LLC at 128B, rather than one
constant for the whole machine). All three pairings came back leaning
**NON-INCLUSIVE**, unlike Sunbird's mixed result (non-inclusive L2,
leaning-inclusive skip-level LLC): L1_vs_L2 is a weak lean (classifier
itself calls it UNCERTAIN — target/control medians came back nearly
identical, unlike Sunbird's clean split), while L2_vs_LLC and L1_vs_LLC
both came back numerically clean (99.5%/100% survived-like) — though both
carry a machine-specific caveat this session flagged: `CAPACITY_RESULTS.md`'s
8 MiB LLC value for Skylark is very likely an underestimate (this machine's
own capacity data shows the real LLC->DRAM knee starting closer to
~16.8-21.8 MiB), so the 256 MiB eviction footprint used for those two
pairings has a smaller effective safety margin over the *real* LLC capacity
than the scaling formula's "32x" nominally implies. Full detail:
`data_raw/skylark/README.md`'s inclusion_policy/ section. Associativity
above L1 hit the same universal confound as 5 of the other 7 machines (L2
auto-detected "9" is very likely an L1-aliasing artifact — 524,288 B is an
exact 16x multiple of L1's own stride; LLC auto-detected 8/8/7, not fully
reproducible) — best-guessed as **8-way for both L2 and LLC** (matching L1,
and the only nearby integer giving a clean S=C/(A×B) derived-set count at
LLC's confirmed 128B line size). `data_processed/skylark/FINAL_CACHE_TABLE.md`
written in the same 9-column format as Sunbird's, every cell leading with a
concrete best-guess value.

**Ookay (2026-09-13): inclusion_policy run completed, Phase I closed out for
this machine — FINAL_CACHE_TABLE.md now exists alongside Sunbird's and
Skylark's.** hit_latency/miss_latency had already been run on this machine
(see the earlier Ookay bullet above); this session merged in Sunbird's
hardened pipeline (commit `a6c0368` + follow-ups) and ran the one remaining
piece, `run_inclusion_policy_full.sh ookay 2` at all three
`CAPACITY_RESULTS.md` pairings (`ASSUMED_LINE_SIZE_BYTES` left at the
default 64 — no machine-specific line-size override needed, since this
machine's own line_size/ data doesn't contradict 64 B at any level, just
under-confirms it at L2/LLC compared to Sunbird's positive 3-footprint
confirmation). Unlike Sunbird's ~1.9 GiB/~604 ms-per-trial LLC-scale
eviction footprint, Ookay's scaled footprint (512 MiB at the 8 MiB LLC
candidate) ran at ~12 ms/trial — the whole 3-pairing pipeline finished in
under a minute, no `tmux` needed. Results: **L1_vs_L2 confidently
NON-INCLUSIVE** (100%/100% target/control survived-like, the cleanest such
result on any machine so far, cleaner even than Sunbird's own 90%/92%).
**L1_vs_LLC (skip-level) leans INVALIDATED/inclusive-like**, on the strength
of a 99.5% paired-check signal (target read slower than its own control in
essentially every trial) even though the absolute-ticks classifier calls the
median itself ambiguous (194 vs. a 198.98-tick threshold, just inside the
±15% fence). **L2_vs_LLC: UNCERTAIN with a weak lean toward
INVALIDATED/inclusive-like** (target 30.5% invalidated-like vs. control's
2.5%, ~12x) — same lowest-confidence status as every other machine's
L2_vs_LLC (L2 target's index doesn't fit in one page), and notably leaning
the *opposite* direction from Sunbird's own L2_vs_LLC result (which leaned
toward survived) — read as evidence this specific pairing doesn't produce a
reliable per-machine signal at all, not as evidence the two machines'
LLCs actually differ. Associativity above L1 hit the same universal confound
as 5 of the other 7 machines: L2 and LLC (262,144 B and 8,388,608 B
candidates) produce numerically indistinguishable two-step staircases at
the *same* num_ways breakpoints despite a 32x capacity difference — with no
extra corroborating technique available on this machine (unlike Sunbird's
use of Upgrade's derived-stride-scan to separate L2 from LLC), both were
best-guessed at the **same 8-way** (matching L1's own confirmed value and
the second staircase step at num_ways=9, the same wall documented
elsewhere) rather than inventing an artificial split; the S=C/(A×B)
cross-check is flagged as less discriminating here than on Sunbird, since
Ookay's 8 MiB LLC candidate is already an exact power of two (so nearly any
power-of-two associativity guess also yields a clean integer set count,
unlike Sunbird's non-power-of-two ~30 MiB value). Also backfilled this
session: the `line_size/` section of `data_raw/ookay/README.md`, which had
been left blank even though a teammate's commit (`990d5b6`) already added
the underlying data — narrative summary only, not independently
re-verified. Full detail: `data_raw/ookay/README.md`'s `line_size/`,
`inclusion_policy/`, and `associativity/` sections;
`data_processed/ookay/FINAL_CACHE_TABLE.md` for the consolidated table.

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
