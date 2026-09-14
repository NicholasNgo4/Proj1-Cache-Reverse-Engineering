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
- **Upgrade** (`data_raw/upgrade/README.md`'s latency/ section): hit latency
  at L1/L2/LLC/DRAM (32,768 / 262,144 / 12,582,912 / 536,870,912 B) gives a
  clean, monotonic 4-tier ladder — L1≈6.17, L2≈16.12, LLC≈155.05, DRAM≈251.56
  ticks (dependent, random, base-run median) — with independent reading
  faster than dependent at every level for the random pattern. The
  `--pattern`-aware independent-addressing fix from Sunbird's run was already
  present in the pulled code, so nothing new to fix here. One flag DID fire
  (`LLC sequential: independent >= dependent`, 6.99 vs 6.67) — investigated,
  not re-run: reproducible across all 3 seeded runs, explained by the
  hardware prefetcher hiding nearly all real latency for the sequential
  pattern at both LLC and DRAM footprints (both modes converge to within
  ~5% of the L1 floor), leaving only a small, consistent secondary effect
  (independent mode's extra `order[idx]` array read per iteration) visible
  once there's no real memory-level parallelism left to expose. Miss/next-
  level latency at L1→L2/L2→LLC/LLC→DRAM gives an increasing 67/510/605-tick
  sequence (random, base-run median) with >20% repeat-to-repeat spread at
  **all six** (transition, pattern) combinations (27.8-60.8%) — noted per
  this run's own instructions rather than re-run until clean. This
  machine's own single-shot fixed overhead was directly measured (control
  run, tiny non-evicting eviction set): median 55 ticks vs. this machine's
  ~6.17-6.35 tick L1 hit-latency median, i.e. a ~48-49 tick floor, similar
  order of magnitude to but somewhat lower than Sunbird's ~64-85 ticks (not
  identical, as expected across CPU generations). See
  `data_raw/upgrade/README.md`'s latency/ section for the full write-up.
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
- **Crux** (`data_raw/crux/latency/`, 2026-09-13): hit latency at L1/L2/LLC/DRAM
  (32,768 / 262,144 / 8,388,608 / 536,870,912 B, per `CAPACITY_RESULTS.md` —
  this machine's LLC is ~8 MiB, not Sunbird's ~30 MiB) gives a clean,
  monotonic 4-tier ladder — L1≈7.42, L2≈14.30, LLC≈43.23, DRAM≈236.80 ticks
  (dependent, random, median). Independent-load control measured faster than
  dependent at every level for the random pattern (as required), but flagged
  `[UNEXPECTED -- investigate]` for the SEQUENTIAL pattern at BOTH LLC and
  DRAM (independent slightly slower, ~5.6-6.4 ticks either way — i.e. both
  still near L1 speed). Investigated and root-caused from source rather than
  discarded: `struct node` is a bare 8-byte pointer, the same size as the
  `size_t` `order[]` index array `latency.c` allocates for independent-mode's
  sequential-pattern case — so independent mode's true working set is ~2x
  `footprint_bytes` at every level, which only matters once that doubled
  footprint exceeds the level actually being measured (LLC: 2x8 MiB vs an
  ~8 MiB LLC; DRAM: already past everything). Combined with the sequential
  pattern's dependent baseline already being fully prefetch-hidden (no MLP
  headroom left to recover), the extra `order[]` traffic tips the balance to
  a small, reproducible (confirmed across all 3 repeats individually, not
  just the aggregate) independent-mode slowdown. This is a real property of
  the independent-load control's construction, not corruption or contention
  — see `data_raw/crux/README.md`'s latency/ section for the full per-run
  numbers. Miss/next-level latency at L1→L2/L2→LLC/LLC→DRAM gives an
  increasing 77/260/437-tick sequence (random, median) with the same
  single-shot fixed-overhead caveat as Sunbird (measured directly on this
  machine: ~50-tick single-shot floor vs. ~7.42-tick batched L1 hit latency,
  i.e. ~42 ticks fixed overhead) — plus L2→LLC and LLC→DRAM both tripped the
  >20%-spread warning (up to 77.8%), not traced to a specific process this
  session.
- **Charnwood** (`data_raw/charnwood/latency/`): hit latency at L1/L2/LLC/DRAM
  (32,768 / 262,144 / 8,388,608 / 536,870,912 B, LLC per `CAPACITY_RESULTS.md`'s
  ~8 MiB row) gives a clean, monotonic 4-tier ladder — L1≈7.98, L2≈17.27,
  LLC≈107-109, DRAM≈394.6-394.8 ticks (dependent, random, ticks/access) — with
  the required independent-load control measuring faster than dependent at
  every level for the random pattern, and at L1/L2/DRAM for sequential too.
  One UNEXPECTED flag (LLC/sequential: independent slightly slower than
  dependent, 8.28 vs 8.10, reproduced consistently across all 3 runs but only
  a 2-3% gap) was investigated, not just noted: at the `sequential` pattern
  every level's latency clusters in the same narrow ~7.4-8.7 tick band
  regardless of footprint (prefetching hides the real hierarchy difference
  entirely, unlike `random`'s clean 10x-40x per-level separation), so a small
  sign-flippable gap there is expected noise, not a violation of the control's
  actual claim. Separately (not something Sunbird's writeup needed): this
  machine's L1/L2 **base** runs measured persistently ~20% higher than their
  own rep1/rep2 for the run's entire 1000-batch duration (not a brief
  startup transient) while LLC/DRAM (run later, after the core had already
  processed 6 prior runs) showed no such gap — read as a P-state/cold-start
  effect on the very first workload of the whole pipeline, the same category
  of finding as Artemisia's P-state bimodality; L1/L2 headline numbers above
  use the rep1+rep2 average, not the base run. Miss/next-level latency at
  L1→L2/L2→LLC/LLC→DRAM gives an increasing ≈107/≈644/≈852-tick sequence
  (random, base/rep1/rep2 average) — this machine's own single-shot-overhead
  control test found essentially the same ~62-tick fixed overhead Sunbird
  found (median=70 vs. this machine's own ~7.98-tick batched L1 hit latency),
  so the same "real reload latency + fixed overhead" caveat applies. 3 of 6
  (transition, pattern) combinations exceeded the pipeline's 20%-spread
  warning threshold (L1_to_L2/sequential 40.0%; LLC_to_DRAM random and
  sequential both 22.8%) — not re-run, per task instruction; same established
  pattern of shared-machine noise as every other multi-run experiment on this
  team's machines, not independently traced to a specific process here. Full
  write-up: `data_raw/charnwood/README.md`'s latency/ section.
- **Artemisia** (`data_raw/artemisia/latency/`, 2026-09-13, unattended, core
  4): hit latency at L1/L2/LLC/DRAM (49,152 / 2,097,152 / 31,457,280 /
  536,870,912 B) gives a clean, monotonic 4-tier ladder — L1≈9.9, L2≈28.1,
  LLC≈94.4, DRAM≈305.6 ticks (dependent, random, median) — independent-load
  control faster than dependent at every level/pattern except one flagged
  case: LLC+sequential briefly read `independent >= dependent`, investigated
  with 3 extra ad hoc seeds and attributed to this machine's already-
  documented per-invocation P-state/turbo bimodality disproportionately
  affecting the small, prefetcher-hidden dependent-sequential number (not a
  real independent-slower-than-dependent effect, and doesn't affect the
  primary random-pattern signal) — see `data_raw/artemisia/README.md`
  latency/ section for the full investigation. Miss/next-level latency at
  L1→L2/L2→LLC/LLC→DRAM gives an increasing 188/381/582-tick sequence
  (random, median); evict_bytes for LLC→DRAM was calibrated down from a
  ~2xLLC candidate (~1.04 s/trial, ~21 min projected) to 1.25xLLC (~0.49
  s/trial, ~9.8 min projected) to stay under the ~15-minute guideline. Same
  single-shot fixed-overhead caveat as Sunbird, independently confirmed here
  too: ~60 ticks (median 70 vs ~9.9-tick batched L1 hit latency at the same
  footprint) — same order of magnitude as Sunbird's ~64-85 ticks. 3 of 6
  (transition, pattern) combinations flagged >20% repeat spread (36-66%),
  not traced to a specific process, consistent with this project's
  established shared-machine-noise signature elsewhere. See
  `data_raw/artemisia/README.md`'s latency/ section for full detail.
- **Thunderbird** (`data_raw/thunderbird/latency/`): hit latency at
  L1/L2/LLC/DRAM (65,536 / 1,048,576 / 31,457,280 / 536,870,912 B) gives a
  clean monotonic 4-tier ladder in ns (converting via `CNTFRQ_EL0`=25 MHz,
  40 ns/tick) — L1≈5.0, L2≈11.9, LLC≈36.3, DRAM≈93.4 ns (dependent, random,
  median; LLC uses the 2 reproducible repeats, not the base run — see
  below) — agreeing closely with this machine's own independently-measured
  capacity-experiment DRAM plateau (~92-96 ns). Independent-load control
  measured faster than dependent at every level/pattern, no `[UNEXPECTED]`
  flags. LLC's base run (1.642 ticks) was flagged by `plot_hit_latency.py`
  as a 65% outlier against both repeats (0.889/0.925, agreeing within ~4%)
  — treated as a single-run interference spike, consistent with this
  project's established pattern elsewhere, not a third data point.
  **New finding: sequential-pattern hit latency is flat at ~0.09-0.12
  ticks across ALL FOUR levels** (no L1→DRAM growth at all) — the
  prefetcher fully hides footprint-driven latency under a sequential
  dependent chase on this machine, confirming the sequential control is
  working as a prefetcher-sanity check but meaning it must never be read
  as a level-specific number here. Miss/next-level latency
  (L1_to_L2:65536:131072, L2_to_LLC:1048576:2097152,
  LLC_to_DRAM:31457280:47185920; the last evict_bytes size, 1.5x LLC, was
  picked after calibration showed 2x LLC would take ~15.4 min for that
  transition alone, right at the ~15 min budget) gives random-pattern
  medians of 2.0/2.0/4.0 ticks — but this machine's coarse 25 MHz counter
  makes most of this unresolvable: a single-shot overhead control (tiny
  non-colliding evict set) measured a **median of 1 tick** (mean 0.90,
  n=2000), meaning **L1_to_L2's 2.0-tick median is statistically
  indistinguishable from pure measurement overhead** and is reported only
  for completeness, not as a real number. Only **LLC_to_DRAM's 4-tick
  median (fully reproducible across all 3 seeds) clears the overhead
  floor by a resolvable margin (~3 ticks / ~120 ns)** — the one
  citable-with-caveats miss-latency number from this machine. **Second
  new finding: sequential-pattern miss_latency collapses to ~1 tick at
  EVERY transition**, including LLC_to_DRAM where the random pattern
  clearly separates from the overhead floor — plausibly the eviction
  walk's own sequential traversal lets the prefetcher re-fetch the
  target's (adjacent) line before the timed reload, defeating the forced
  eviction; sequential-pattern miss_latency numbers should not be used as
  real latencies on this machine. Full detail, including the exact
  overhead-tick histogram and calibration numbers:
  `data_raw/thunderbird/README.md`'s latency/ section.
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
inclusion_policy` in `main_code/common/inclusion_policy.c`/`.h`), now run on
Sunbird and Artemisia — Artemisia's LLC-involving verdicts came back
decisively cleaner than Sunbird's (see its bullet below).** Pipeline:
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
- **Artemisia** (`data_raw/artemisia/inclusion_policy/{L1_vs_L2,L2_vs_LLC,L1_vs_LLC}/`,
  2026-09-13, core 4, all three pairings from `CAPACITY_RESULTS.md`'s L1/L2/LLC
  boundaries — note L2's value, 2,097,152 B, is the same one this machine's own
  capacity data already flags as NOT a confirmed boundary, run anyway per
  project-wide direction): **both LLC-involving pairings came back a clean
  100% invalidated-like / 0% ambiguous split** — L2_vs_LLC (target median 476
  vs. 88.8-tick survived/582-tick invalidated calibration) and L1_vs_LLC
  (target median 523 vs. 70.2/582) — noticeably cleaner than Sunbird's own
  ambiguous/borderline results for the equivalent pairings. **Verdict for
  both: INCLUSIVE.** L1_vs_L2, by contrast, came back 77.5% ambiguous (target
  median 160 vs. 70.1-tick survived/381-tick invalidated calibration, control
  a clean 100% survived-like) — **Verdict: UNCERTAIN** — most likely because
  this pairing's eviction footprint scales off the same unconfirmed 2 MiB L2
  candidate, making it 8x larger (128 MiB/32,768 pages) than Sunbird's
  equivalent, confirmed-capacity L1_vs_L2 pairing (16 MiB/4,096 pages),
  pushing it into the DTLB-risk regime Sunbird's writeup only expected for
  LLC-scale pairings. `ASSUMED_LINE_SIZE_BYTES` left at the default 64 —
  this machine's own line_size/ section confirms 64B at L1 and reads it as
  best-supported (though not offset-invariance-clean) at L2; no line-size
  signal exists at all at the LLC candidate after 11 independent attempts, so
  64B is simply the only measured value anywhere on this machine, not a
  blind carry-over. **Best-guess overall reading:** Artemisia's LLC reads as
  confidently inclusive of both L1 and L2 (cleaner evidence than Sunbird's
  own LLC pairings produced), while L1's own relationship to L2 remains open
  pending a re-run at a corrected eviction footprint once a real L2 capacity
  is established for this machine. Full writeup: `data_raw/artemisia/README.md`'s
  inclusion_policy/ section. Final table:
  `data_processed/artemisia/FINAL_CACHE_TABLE.md` — L1 associativity best
  guess 12-way (not machine-confirmed, unlike Sunbird/Upgrade/Charnwood's
  8-way), L2/LLC both best-guessed at 16-way (same confound as every other
  machine, reasoned from L1's floor + L2's capacity being a pure power of two
  forcing a power-of-two associativity guess; see the table's own reasoning
  section for why LLC's "clean sets" check is weaker evidence than L2's
  there). **Not yet run on any other machine besides these two.**

**Thunderbird (2026-09-13): ran all three pairings using the hardened
pipeline's per-level `ASSUMED_LINE_SIZE_BYTES` override (64 B for L1_vs_L2,
128 B for the two LLC-scale pairings, matching this machine's own confirmed
per-level line_size split) — the first machine to actually need that
override.** L1_vs_L2: EXCLUSIVE/NON-INCLUSIVE (84.5% survived-like), same
direction as Sunbird. L2_vs_LLC: formally UNCERTAIN but leans inclusive
(76.5% invalidated-like, vs. Sunbird's own near-total ambiguity at this
pairing — a different-looking, not just noisier, result). L1_vs_LLC (skip
-level): EXCLUSIVE/NON-INCLUSIVE at 80.5% — **the opposite directional lean
from Sunbird's own skip-level result** (Sunbird leaned inclusive at 75%).
New Thunderbird-specific finding, not present on Sunbird: this machine's real
L1 (65,536 B, 4-way, 256 sets) needs 14 address bits of index+offset, 2 more
than fit in one 4096 B page (Sunbird's L1 fits exactly in 12), so the
method's "eviction structurally avoids target's own set" guarantee is only
approximate here even for an L1 target, not exact — read every Thunderbird
inclusion_policy verdict as somewhat less clean than the equivalent Sunbird
one for this reason. Also: this machine's coarse 25 MHz timer compresses the
survived/invalidated calibration classes into just a few integer tick
values, making per-trial classification here inherently less crisp than on
x86. **Best-guess overall reading:** L1 vs L2 confidently non-inclusive
(matches Sunbird); unlike Sunbird, the two LLC-involving pairings do NOT
combine into one internally consistent hierarchy-wide story on this
machine — treated as genuinely unresolved rather than forcing Sunbird's
snoop-filter narrative onto different data. Full writeup:
`data_raw/thunderbird/README.md`'s inclusion_policy/ section; final table:
`data_processed/thunderbird/FINAL_CACHE_TABLE.md` (same format as Sunbird's,
including a reasoned best-guess L2=12-way/LLC=10-way associativity call —
the same cross-machine confound already documented above, now reproduced on
a fourth machine and confirmed non-monotonic in its raw numbers here, flagged
as a likely confound artifact rather than smoothed over).

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

**Upgrade (2026-09-13): hit_latency/miss_latency/inclusion_policy all now
complete, Phase I closed out for this machine — FINAL_CACHE_TABLE.md now
exists alongside Sunbird's and Skylark's.** After merging in Sunbird's
hardened `run_inclusion_policy_full.sh`, ran all three pairings in one
invocation at `ASSUMED_LINE_SIZE_BYTES=64` uniformly — unlike Skylark/
Thunderbird, this machine never produced a citable alternate line-size
value at any level (L2/LLC line_size/ data never converged across 7+
repeated runs, pure noise, not a competing measurement), so 64B (this
machine's only confirmed value, at L1) was used for every pairing rather
than guessing a different one. **L1_vs_L2: confidently NON-INCLUSIVE**
(99.0% survived-like, cleanest of the three). **L2_vs_LLC: leans
NON-INCLUSIVE** (95.5% survived-like) but weakest-confidence per the
usual L2-index-doesn't-fit-one-page caveat, plus a 90.4%-spread repeat
flagged (same "one repeat spikes hard" signature as Sunbird's own
L2_vs_LLC). **L1_vs_LLC (skip-level): classifier-UNCERTAIN** — target
landed almost exactly on the geometric-mean classification boundary (168
vs. 167.39 ticks), 95% of trials ambiguous — but a closer read found
target's tight 165-174 tick IQR sits far closer to this machine's own
on-chip LLC-hit latency (~155 ticks) than to either the survived (~46) or
invalidated (~605) calibration extremes, i.e. the walk evicts L1 but the
data is landing back in cache rather than being forced to DRAM — read as
a reasoned NON-INCLUSIVE lean rather than a non-answer (see
`data_raw/upgrade/README.md`'s inclusion_policy/ section for the full
argument). **All three pairings therefore point the same direction**
(non-inclusive), unlike Sunbird's mixed non-inclusive-L2/leaning-inclusive-
LLC result — same overall shape as Skylark's read, though Upgrade is Intel
Coffee Lake (not AMD Zen 2), so the vendor/generation correlation Skylark's
aside suggested doesn't hold uniformly across the team's own Intel
machines (Sunbird's Haswell-EP leaned the other way) — noted as an open
cross-machine question, not resolved further under Phase I discipline.
Associativity above L1 hit the same universal confound as 5 of the other
7 machines; best-guessed as **8-way for both L2 and LLC** (matching L1,
supported by the derived-stride-scan technique's full-rigor confirm run
showing a real second knee at way=9 once the shallow first-step artifact
is looked past, and the only nearby integer giving a clean S=C/(A×B)
derived-set count — 24,576 — at LLC's ~12 MiB `CAPACITY_RESULTS.md`
value). `data_processed/upgrade/FINAL_CACHE_TABLE.md` written in the same
9-column format as Sunbird's/Skylark's, every cell leading with a concrete
best-guess value. Idle-core check: core 5 (same core as every other
Upgrade run), reconfirmed idle via `/proc/stat` deltas immediately before
the run.

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

**Crux (2026-09-13): inclusion_policy run completed, Phase I closed out for
this machine — FINAL_CACHE_TABLE.md now exists alongside Sunbird's and
Skylark's.** Ran all 3 pairings in one invocation
(`./scripts/run_inclusion_policy_full.sh crux 3 L1_vs_L2:32768:262144:L2_to_LLC,
L2_vs_LLC:262144:8388608:LLC_to_DRAM,L1_vs_LLC:32768:8388608:LLC_to_DRAM`) —
line size was already confirmed 64B at all 3 levels before this ran, so no
`ASSUMED_LINE_SIZE_BYTES` override was needed. Calibrated the largest scaled
eviction footprint (512 MiB, for the two LLC-scale pairings) before
committing: only ~11.6 ms/trial on this machine (vs. Sunbird's reported
74-604 ms/trial range for miss_latency-style eviction), so the full pipeline
ran in well under a minute per pairing with no `tmux` needed. Results: **L1
vs L2 confidently non-inclusive (97.5% survived-like)**; **L2 vs LLC leans
non-inclusive with moderate confidence (90.5%)** — notably a firmer call than
Sunbird's own L2_vs_LLC pairing, which came back mostly ambiguous; **L1 vs
LLC (skip-level) is this machine's weakest result, 98% ambiguous, leaning
non-inclusive only barely** — the opposite directional lean from Sunbird's
own skip-level result (which leaned inclusive). Both LLC-scale pairings'
control channels showed elevated run-to-run spread (24-40%), read as evidence
of real DTLB pressure at the 512 MiB eviction scale (the same caveat
Sunbird's own README flags but did not observe as directly). Associativity
above L1: raw detector reports 4-way for both L2 and LLC with full 3/3
reproducibility each — but this is treated as the same confound already
documented elsewhere, not a real result, specifically because Crux's "4" at
both 262,144 B and 8,388,608 B (a 32x capacity spread) is an exact match to
Charnwood's own confound-driven "4" at those identical candidate byte values
(see Charnwood's bullet above) — best-guessed as **8-way for both L2 and
LLC** (anchored to L1's confirmed 8-way; also the only choice that makes
S=C/(A×B) come out to a clean integer at all three levels: 64/512/16,384,
each ratio exactly matching the corresponding capacity ratio). Best-guess
overall read: a uniformly non-inclusive hierarchy at every tested boundary —
a genuine contrast with Sunbird's own mixed (non-inclusive L2,
inclusive-leaning LLC-as-snoop-filter) reading. Full detail:
`data_raw/crux/README.md`'s `inclusion_policy/` section;
`data_processed/crux/FINAL_CACHE_TABLE.md` written in the same 9-column
format as Sunbird's/Skylark's, every cell leading with a concrete best-guess
value.

**Charnwood (2026-09-13): inclusion_policy run completed, Phase I closed out
for this machine — FINAL_CACHE_TABLE.md now exists alongside Sunbird's and
Skylark's.** Ran all three pairings in one invocation at `ASSUMED_LINE_SIZE_
BYTES` left at its default (64) — a checked, not blind, choice: this
machine's own line_size/ section confirms 64B at L1, finds 64B as the
leading (75%-agreement, not fully settled) candidate at LLC, and has no
competing value at all for L2 (a settled null result), so one constant is
the best-supported call here, unlike Skylark's genuine per-level 64B/128B
split. L1_vs_L2 came back the cleanest of the three (86.0% survived-like,
control 100% clean) — **EXCLUSIVE/NON-INCLUSIVE**, matching Sunbird's own
L1_vs_L2 read. Both LLC-scale pairings (L2_vs_LLC, L1_vs_LLC) triggered the
classifier's own confound warning — **control itself showed 54.0% and 40.0%
invalidated-like trials respectively, despite never being touched by the
eviction walk** — the clearest on-team evidence yet that the DTLB/large-
footprint confound (`inclusion_policy.h`'s caveat 2) can contaminate the
control channel, not just target (Sunbird's own 3 pairings kept clean
controls throughout). Per task instruction not to leave a confounded
pairing as a bare non-answer, both were given a directional best guess
using the target-vs-control gap on top of the shared noise floor rather
than the classifier's absolute threshold: **L2_vs_LLC leans invalidated/
inclusive-like, low confidence** (54-tick gap, both the DTLB and the
index-doesn't-fit-one-page caveats apply); **L1_vs_LLC leans invalidated/
inclusive-like, moderate confidence** (124-tick gap, more than double
L2_vs_LLC's, and L1's index is confirmed to fit in one page). Associativity
above L1 hit the same universal confound as 5 of the other 7 machines, with
an unusually clean same-run demonstration: L2's (262,144 B) and LLC's
(8,388,608 B) median-latency curves agree to within ~0.05 ticks/access at
every num_ways from 2-23 despite a 32x capacity difference — direct
same-machine evidence both auto-detected "4" readings are the shared DTLB
confound, not real signal. Best-guessed as **8-way for both L2 and LLC**
(matching L1, reasoning from the staircase's second jump at num_ways=9 the
way Skylark's own LLC best-guess did) — the S=C/(A×B) cross-check comes out
unusually clean here (both L1→L2 and L2→LLC set-count ratios exactly match
their capacity ratios, 8x and 32x), a stronger internal-consistency result
than Sunbird's own table got. Full detail: `data_raw/charnwood/README.md`'s
inclusion_policy/ section. `data_processed/charnwood/FINAL_CACHE_TABLE.md`
written in the same 9-column format as Sunbird's/Skylark's, every cell
leading with a concrete best-guess value.

Line size: `--experiment line_size` exists (added by @krchen1, commit
`5aaa83f`) with its own `scripts/{run_line_size_full.sh,
run_line_size_sweep.sh,detect_line_size.py,plot_line_size.py}` pipeline;
check that machine's own `data_raw/<machine>/README.md` and recent git log
(not this paragraph) for its actual current per-machine data-collection
status, since this file lags active work in progress.

**Phase II (counter- and literature-based verification): started
2026-09-13, six machines done (Sunbird, Thunderbird, Charnwood, Skylark,
Ookay, Artemisia), 2 outstanding (Crux, Upgrade).**
`phase1-timing-only` tagged at commit `7be6dac` — **two sessions tagged it
independently and concurrently (both at this same commit, so the tags
should be identical objects pointing to the same target); verify with
`git ls-remote --tags origin` before pushing again, in case that produced
two divergent tag objects of the same name that need reconciling, not
just one.** Per `README.md`'s Phase Discipline, this is the first point at
which `perf`, PMU, and cache-topology commands became allowed.

**Cross-session divergence (resolved 2026-09-13): standardized on Sunbird's
reusable pipeline.** Sunbird and Thunderbird were originally done by two
concurrent sessions that never saw each other's work, and invented two
different, incompatible Phase II conventions (a reusable
`scripts/run_pmu_verification.sh` pipeline + per-machine
`PHASE2_VALIDATION_TABLE.md` from Sunbird's session, vs. an ad hoc
per-machine script + a consolidated root-level `PHASE2_VALIDATION.md` from
Thunderbird's session). **Thunderbird has since been migrated**: re-run
under `scripts/run_pmu_verification.sh` (canonical now), its own
`data_processed/thunderbird/PHASE2_VALIDATION_TABLE.md` written, and the old
root `PHASE2_VALIDATION.md` deleted (superseded, not just orphaned). The
original ad hoc sweep's raw findings weren't discarded, though — they swept
a full range of working-set sizes the 3-point pipeline doesn't, and are kept
as an explicit "Supplementary PMU evidence" section inside Thunderbird's
`PHASE2_VALIDATION_TABLE.md` (see `data_raw/thunderbird/pmu/run_pmu_sweep.sh`
and its outputs, still present). **Every future machine should use
`scripts/run_pmu_verification.sh` + a per-machine
`data_processed/<machine>/PHASE2_VALIDATION_TABLE.md` — this is no longer an
open decision.**

- **New pipeline**: `scripts/run_pmu_verification.sh <machine> <core>
  <level>:<footprint_bytes>[,...]` (mirrors `run_hit_latency_full.sh`'s
  conventions: same `CAPACITY_RESULTS.md`-sourced footprints, base+2-seeded-
  repeats, timestamped raw output) + `scripts/summarize_pmu.py`. For each
  level, it wraps the existing `cache_bench --experiment hit_latency`
  invocation in 4 SEPARATE `perf stat -e duration_time,<2 events>,...`
  calls — `{cache-references,cache-misses}`, `{L1-dcache-loads,
  L1-dcache-load-misses}`, `{LLC-loads,LLC-load-misses}`,
  `{cycles,instructions}` — rather than one combined command. **Why 4
  separate 2-event groups**: hand-checked on Sunbird before writing the
  script — this PMU only reliably schedules 2 generic hardware counters at
  100%; a 3-event group only got 57-71% scheduled (`nmi_watchdog=1` pins one
  counter). If a future machine schedules fewer than 2 at 100% (heavier PMU
  contention from other students), that's a real, honestly-documented
  limitation to record, not a bug to work around by fabricating numbers.
  Raw perf CSVs + cache_bench's own CSV from the same invocation land in
  `data_raw/<machine>/pmu/<level>/` (gzip these by hand after a manual/ad hoc
  run — `.gitignore`'s `data_raw/**/*.csv` rule applies here too, same as
  every other experiment); parsed summaries (miss rates, cycles/access,
  perf's own wall-clock ns/access) in
  `data_processed/<machine>/pmu/<level>/pmu_summary_<ts>.csv`.
  **Now also the pipeline Thunderbird uses** — see the divergence note above.
  On an ARM machine, expect `LLC-loads`/`LLC-load-misses` to come back
  `<not supported>` (not just `<not counted>`) — confirmed on Thunderbird's
  `armv8_pmuv3_0` PMU, which has no LLC-scoped event perf can alias to that
  name; the script and `summarize_pmu.py` already tolerate this gracefully
  (recorded via the `notes` column), nothing to fix.
- **System-reported cache info**: now-allowed, no new code — `lscpu --caches`
  and full `lscpu`, plus per-instance `/sys/devices/system/cpu/cpu0/cache/
  index*/{level,type,size,ways_of_associativity,coherency_line_size,
  number_of_sets,shared_cpu_list}`, saved to
  `data_raw/<machine>/pmu/system_reported_cache_info.txt`. `shared_cpu_list`
  directly answers Table 2's "Sharing scope" column (which Phase I could
  only ever guess at architecturally) — check it per machine, don't assume
  Sunbird's own private-per-core-L1/L2 + shared-per-socket-L3 pattern holds
  everywhere (**it does not hold on Thunderbird** — see that machine's
  results below: L1/L2 are private-per-core but the LLC-equivalent SLC is
  shared across all 80 cores, not per-socket).
- **Literature reference**: Agner Fog's *microarchitecture* manual
  (`www.agner.org/optimize/microarchitecture.pdf`) for the 6 machines it
  covers (Sunbird/Haswell, Charnwood/Skylake, Crux+Ookay+Upgrade/
  Skylake-family, Skylark/Zen2) — find the right microarchitecture section
  by grepping a converted-to-text copy for the microarch name (Fog organizes
  by numbered chapter per microarchitecture, cache info is usually its own
  numbered subsection with a "Cache sizes on ..." table). For Artemisia
  (Sapphire Rapids) and Thunderbird (ARM Neoverse N1) — not covered by Fog —
  use vendor docs (Intel optimization manual/datasheet; ARM's Neoverse N1
  Technical Reference Manual) supplemented by WikiChip/Chips and Cheese
  where a specific field isn't published, each cited with exact
  section/page or URL (per explicit project direction, not assumed).
  **Thunderbird now done**: Ampere Altra Datasheet Rev A1 v1.30 (SKU-specific)
  + Arm Neoverse N1 Core TRM r3p1 (architectural), both cited by
  section/page in `data_processed/thunderbird/PHASE2_VALIDATION_TABLE.md` —
  no WikiChip/Chips and Cheese fallback was needed, both primary sources had
  what was required except load-use latency in cycles, which neither
  publishes, and the TRM doesn't cover the SLC at all (outside a per-core
  manual's scope) — Thunderbird's LLC row rests on the Ampere datasheet
  alone, one source, unlike its L1D/L2 rows. **Charnwood now done**: Fog's
  manual §11.12, Table 11.2 "Cache sizes on Skylake", p. 160 — the first
  machine on this team where Fog's table is a direct hit for the exact
  microarchitecture (Skylake client) rather than a same-family stand-in;
  cited in full in `data_processed/charnwood/PHASE2_VALIDATION_TABLE.md`.
- **Deliverable**: a single `data_processed/<machine>/
  PHASE2_VALIDATION_TABLE.md` per machine (separate file from
  `FINAL_CACHE_TABLE.md`, never edits it) — `PROJECT 1.pdf`'s Table 2
  columns (Level | Measured size | Measured ways | Derived sets | Line |
  Measured latency | Sharing scope | Reference value | Agreement) for
  L1D/L2/LLC, with every cell distinguishing Phase-I-timing vs.
  Phase-II-PMU vs. Phase-II-system-reported vs. literature before landing
  on an Agreement verdict. Disagreements get stated plainly, not smoothed
  over. Now the convention for both machines done so far.
- **Sunbird results (full detail:
  `data_processed/sunbird/PHASE2_VALIDATION_TABLE.md`)**:
  - **Size/ways/sets/line/sharing-scope: exact match across Phase I timing,
    Phase II system-report, AND literature at L1D and L2** — most
    strikingly, the system-reported L2 associativity (8-way, from
    `lscpu`/sysfs) independently confirms Phase I's confound-blocked L2
    best guess, which Phase I itself could never fully trust.
  - **LLC size: Phase I's ~30 MiB estimate matches the system-reported
    30,720 KiB (31,457,280 B) exactly, byte for byte** — remarkable given
    Phase I derived it purely from timing.
  - **LLC associativity: a real, informative disagreement.** Phase I's
    best guess was 9-way (explicitly flagged as a low-confidence "effective
    lower bound", blocked by the cross-machine DTLB-scale confound
    documented extensively in the associativity section above).
    System-reported: **20-way.** This directly confirms — not just
    suspects — that Phase I's repeatedly-observed "~9-10" wall really was
    the shared small-structure confound artifact, not real LLC
    associativity; also, only 20-way (not 9-way) gives a clean integer
    derived-set count (24,576 vs. a non-integer 54,613), additional
    post-hoc evidence 9-way was wrong. Also notable: Fog's Table 10.2
    quotes a 12-16-way *range* for the Haswell/Broadwell family in general,
    and this SKU's actual 20-way falls outside even that range — a
    concrete, textbook case of `PROJECT 1.pdf`'s own warning not to assume
    one value applies to every SKU in a generation.
  - **Latency: measured (Phase I ticks AND Phase II perf-derived
    cycles/access) reads consistently higher than Fog's reference cycle
    counts at all 3 levels** (ratio roughly 1.7-2.6x, most pronounced at
    L1/L2) — attributed to this project's `-O0` compiled dependent-chase
    loop (stack spill/reload of the chase pointer sits in the true
    dependency chain every iteration), not a contradiction; see the
    table's own caveat section for the full reasoning, including why the
    Phase-II PMU "cycles/access"/"ns/access" numbers are themselves only
    trustworthy as an order-of-magnitude cross-check (they're whole-
    process-lifetime figures divided by only the timed samples, heavily
    diluted by untimed warmup/setup at small footprints and NOT usable as
    an absolute number at the LLC footprint) — miss-rate ratios (which
    cancel most of that contamination) are the reliable Phase-II PMU
    corroboration signal, and they cleanly reproduce Phase I's own L1/L2/LLC
    boundary placement (an order-of-magnitude jump in LLC-scope miss rate,
    ~0.1-1.4% to ~11-14%, lands exactly at the LLC footprint).
  - This machine's PMU only reliably schedules 2 generic hardware counters
    at once (see pipeline note above) — a real, machine-specific
    limitation worth re-checking (not assuming) on each of the other 7.
- **Thunderbird results (full detail:
  `data_processed/thunderbird/PHASE2_VALIDATION_TABLE.md`)**: run via
  `scripts/run_pmu_verification.sh thunderbird 3
  L1:65536,L2:1048576,LLC:31457280`, core 3, timestamp `20260913T203354Z`.
  **L1D: exact match, all 3 sources** (size/ways/sets/line), the cleanest
  row on this table, same pattern as Sunbird's L1D. **L2 associativity
  disagreement resolved the same way Sunbird's LLC was**: Phase I's
  confound-suspected 12-way vs. system-reported 8-way AND literature's
  independently-agreeing 8-way — a 3-way convergence against one
  confound-blocked guess. **LLC is this machine's weakest row, and
  structurally different from Sunbird's**: `lscpu`/sysfs has NO L3/SLC entry
  at all for this core (only L1D/L1I/L2 are enumerated) — so unlike Sunbird,
  where system-report resolved the LLC associativity disagreement outright,
  Thunderbird's LLC row has no system-reported evidence to arbitrate with at
  all, only Phase I timing and one literature source (the Arm core TRM
  doesn't cover the SLC, only Ampere's own datasheet does). Two real
  ARM-PMU limitations showed up that Sunbird's x86 run never hit: (1)
  `LLC-loads`/`LLC-load-misses` come back `<not supported>` at every level
  (no LLC-scoped PMU event on this SoC that perf can alias to that name);
  (2) the generic `cache-references`/`cache-misses` group IS counted but
  tracks `L1-dcache-loads` almost exactly at every footprint (not a distinct
  LLC-scope signal the way it was on Sunbird) — so this machine's LLC-row
  miss rate reads *lower* than L2's, the wrong direction for real
  capacity-scoped evidence; documented as a real limitation, not used as
  if it were corroboration. Phase II literature does newly confirm the SLC
  is **shared across all 80 cores**, sharpening Phase I's architectural
  guess. The earlier ad hoc full-sweep pass (23 sizes, 4 KiB-512 MiB, raw
  `armv8_pmuv3_0` events) was kept as supplementary evidence inside the same
  file rather than discarded — it independently corroborates the L1D 64 KiB
  knee and the "no flat L2 shelf" finding, and its own L3 miss-rate result
  (no capacity-dependent signal anywhere, even at a 4 KiB footprint) is a
  third independent piece of evidence for "this SoC's SLC is invisible to
  per-core PMU/OS reporting," alongside sysfs's missing L3 entry and finding
  (2) above.
- **Crux results (full detail:
  `data_processed/crux/PHASE2_VALIDATION_TABLE.md`)**: run via
  `scripts/run_pmu_verification.sh crux 1 L1:32768,L2:262144,LLC:8388608`,
  core 1 (cores 0/2 were pinned by other students' jobs at the time —
  confirmed via two `/proc/stat` idle-delta samples 4s apart, not just a
  `ps` snapshot), timestamp `20260914T003352Z`. Literature: Agner Fog's
  manual, §11.12/Table 11.2 "Cache sizes on Skylake" (Coffee Lake shares
  this family for cache purposes per Fog's own §11.15 title) — same source
  category CLAUDE.md's pipeline note above already assigned to
  Crux/Ookay/Upgrade. **Machine-specific PMU finding, opposite of
  Sunbird's**: a hand-checked combined single `perf stat` invocation
  scheduled all 7 hardware events + `duration_time` at 100% simultaneously
  (3/3 repeats) — this PMU does not share Sunbird's 2-counter-at-once
  ceiling, though the script still ran its standard 4-group split
  regardless (no `<not counted>` anywhere in the output either way).
  **L1D: exact match, all 3 sources** (size/ways/sets/line/sharing) —
  same clean pattern as Sunbird's and Thunderbird's own L1D rows.
  **Two genuine, stated-plainly disagreements, both informative:**
  (1) **L2 associativity — Phase I's reasoned override was simply wrong.**
  `FINAL_CACHE_TABLE.md` explicitly set aside the raw detector's "4-way"
  reading as the cross-machine DTLB-scale confound and reasoned to an
  8-way best guess (anchoring to L1, plus a clean S=C/(A·B) integer
  argument). System-report says **4-way** — the discarded raw reading was
  the real answer all along, and sits exactly at the low end of Fog's
  quoted 4-16-way Skylake-family range. A concrete example of the
  confound heuristic (validated repeatedly elsewhere on this team) failing
  in the other direction on this specific machine. (2) **LLC size — the
  `CAPACITY_RESULTS.md` ~8 MiB value used for every Crux experiment so far
  is measurably wrong; the real LLC is 12 MiB**, confirming the conflict
  `FINAL_CACHE_TABLE.md` had already flagged (`lscpu`'s reported 12 MiB)
  but left unresolved during Phase I. LLC associativity (system-reported
  12-way) matches neither Phase I's raw confound value (4) nor its 8-way
  best guess. Latency: L2's measured ticks (~14.3-14.9) land almost
  exactly on Fog's 14-cycle figure; LLC's (~43-59 ticks) fall inside Fog's
  34-85 cycle range. Sharing scope confirmed by `shared_cpu_list`: L1/L2
  private per logical CPU (no SMT on this part), LLC shared across all 8
  cores of the one socket.
- **Charnwood results (full detail:
  `data_processed/charnwood/PHASE2_VALIDATION_TABLE.md`)**: run via
  `scripts/run_pmu_verification.sh charnwood 3
  L1:32768,L2:262144,LLC:8388608`, core 3, timestamp `20260914T003212Z`.
  Literature source: Agner Fog's manual §11.12, Table 11.2 "Cache sizes on
  Skylake", p. 160 — the first machine on the team where Fog's table covers
  this exact microarchitecture (Skylake client) rather than a related one.
  **L1D: exact match, all 3 sources** (size/ways/sets/line/sharing), same
  clean pattern as Sunbird's and Thunderbird's L1D rows. **Both L2 and LLC
  associativity were real disagreements, in opposite directions**: Phase
  I's confound-blocked best guess was 8-way for both (see
  `FINAL_CACHE_TABLE.md`'s associativity reasoning); system-reported came
  back **L2 = 4-way** (half the guess, and literature's Table 11.2
  independently corroborates 4-way as the low end of its own quoted
  "4-16 way" range, plus an exact 1,024-set match) and **LLC = 16-way**
  (double the guess; no literature ways figure exists for L3 in this table
  to arbitrate a 3rd way — an honest gap in the source, not a discrepancy).
  This is now the 3rd team machine (after Sunbird's LLC and Thunderbird's
  L2) where Phase II unlocked a real correction to a confound-blocked Phase
  I guess — the direction isn't consistent across machines (too high on
  some, too low on others), reinforcing that the underlying confound isn't
  systematically biased in one direction, just unreliable. **New finding
  not present on Sunbird/Thunderbird's PMU runs**: this run's own PMU
  counters caught a real *confirmed* multi-tenant interference effect even
  though the two other students' processes were pinned to different
  physical cores than this run's core 3 — `cycles/duration_time_ns` computed
  from this run's own counters showed core 3 running at only ~2.4-2.7 GHz
  (vs. this CPU's 3.4 GHz base), while two other physical cores sat near
  100% busy the whole time; independently corroborated via
  `scaling_cur_freq`/`scaling_governor`. Leading hypothesis: package-level
  turbo-budget suppression, not direct resource contention — a different
  interference mechanism than the same-core or shared-LLC contention this
  project has documented elsewhere, since here the contending processes
  shared neither a physical core nor (as far as tested) a demonstrated LLC
  conflict with the pinned core. This tracks with a fairly uniform ~30-36%
  inflation in this run's own `bench_avg_ticks_per_access_median` relative
  to Phase I's own (quieter-session) hit_latency numbers at all 3 levels —
  worth checking for on any future machine's PMU run where "different
  physical core, still not fully quiet" was the best idle-core check
  achievable at the time.
- **Skylark (2026-09-14): third machine done, first AMD/Zen 2 result — full
  detail: `data_processed/skylark/PHASE2_VALIDATION_TABLE.md`.** Ran
  `scripts/run_pmu_verification.sh skylark 5 L1:32768,L2:524288,LLC:8388608`
  (core 5, confirmed idle via two `mpstat` samples — cores 0/2/3 were busy
  with other students' processes at the time), timestamp
  `20260914T002932Z`, literature source Agner Fog's manual, Ch. 22 §22.16,
  Table 22.3 "Cache sizes on AMD Zen 2", p. 237.
  - **L1D and L2: exact match across Phase I timing, Phase II
    system-report, AND literature** (size/ways/sets/line) — system-reported
    L2 associativity (8-way) independently confirms Phase I's
    confound-blocked best guess, the same pattern as Sunbird's L2 row.
  - **LLC size: system-reported 16,777,216 B (16 MiB) confirms Phase I's
    own already-documented suspicion that its 8 MiB `CAPACITY_RESULTS.md`
    value was an underestimate** — lands almost exactly at the bottom of
    Skylark's own `FINAL_CACHE_TABLE.md`-flagged ~16.8-21.8 MiB re-look
    bracket, a clean resolution rather than a new puzzle.
  - **LLC associativity: Phase I's confound-blocked best guess (8-way) vs.
    system-reported 16-way — resolved in favor of the system-reported
    value**, the same confound-confirmation pattern as Sunbird's (9→20) and
    Thunderbird's L2 (12→8) rows; 16-way also sits at the low end of Fog's
    quoted 16-24-way range for this generation.
  - **Line size: a genuine, unresolved disagreement, not yet seen on
    Sunbird or Thunderbird.** Phase I independently confirmed 128 B
    specifically at the LLC-region transition via two methods (2x this
    machine's own L1/L2 line size); system-report and literature both say
    64 B uniformly at every level. Leading hypothesis (NOT confirmed —
    no dedicated follow-up run this phase): Zen 2's documented
    adjacent-line/stream prefetcher creating an apparent 128 B granularity
    for a stride-based line-size probe once the working set spills past
    L2, without the physical line actually being wider. Left open.
  - **Sharing scope: the standout finding on this machine.** Phase I had
    guessed "shared across cores/socket" for the LLC (architecturally
    typical, untested). System-reported `shared_cpu_list` shows this LLC
    is shared by only **2** logical cores per instance (spot-checked
    machine-wide across 5 other cores, not just core 5) — resolved via AMD's
    published EPYC 7532 spec: 8 CCDs x 2 CCX/CCD x 16 MiB/CCX = 256 MiB
    total L3 per socket, this exact SKU's known "cache-doubled" Rome
    binning (only 2 of 4 possible cores active per CCX, each CCX still
    granted its full 16 MiB), not a measurement artifact and not a
    contradiction of Fog's own microarchitecture-generic "one L3 per 4
    cores" figure (Table 22.3 states a generation-wide default, not a
    per-SKU guarantee — the same "don't assume one number applies to every
    SKU" lesson Sunbird's LLC-associativity finding already produced).
  - **This AMD PMU has no working LLC-scope perf event for an unprivileged
    user at all** — `LLC-loads`/`LLC-load-misses` return `<not supported>`
    (a harder failure than Sunbird's clean scheduling, and unlike
    Thunderbird's ARM PMU, also true of AMD's own raw uncore L3 events
    `l3_accesses`/`l3_misses`, blocked by this session's
    `perf_event_paranoid=2` even system-wide). The generic
    `cache-references`/`cache-misses` group's miss rate is also not a
    clean monotonic LLC-scope signal here (19.34% at L1 footprint → 11.32%
    at L2 → 46.59% at LLC — a dip, not a steady climb), most likely because
    this generic AMD alias tracks something closer to L2-request traffic
    than Intel's LLC-scope mapping does (very low absolute event counts at
    the L1 footprint support this); the LLC footprint's own sharp jump is
    still a clean, trustworthy boundary confirmation regardless.
- **Ookay results (full detail:
  `data_processed/ookay/PHASE2_VALIDATION_TABLE.md`)**: run via
  `scripts/run_pmu_verification.sh ookay 3 L1:32768,L2:262144,LLC:8388608`,
  core 3 (checked idle via 3 `mpstat` samples ~3s apart — cores 0/2 were
  each 100% busy with other students' `incl_pmu`/`cache_bench_x86`
  processes the entire session; core 3's own both SMT threads were
  independently idle throughout), timestamp `20260914T003308Z`. Literature:
  Agner Fog's Table 11.2 "Cache sizes on Skylake" (Kaby Lake is covered by
  Fog's own "Skylake and other Lakes are quite similar" framing), per this
  section's pre-existing Skylake-family assignment for Ookay/Crux/Upgrade.
  **L1D: exact match, all 3 sources** (size/ways/sets/line), same clean
  pattern as Sunbird's and Thunderbird's L1D rows, and notably the same
  `-O0` latency-inflation ratio (~3.43x vs. Fog's 4-cycle reference) as
  Sunbird's own L1 (~3.40x) despite a different CPU generation. **Both L2
  and LLC associativity disagree with Phase I's confound-blocked best guess
  (8-way at both levels, per `FINAL_CACHE_TABLE.md`'s reasoning) —
  system-reported is 4-way at L2 and 16-way at LLC**, each resolved in
  favor of the system-reported value — the same resolution pattern as
  Sunbird's LLC row and Thunderbird's L2 row, now with BOTH non-L1 levels
  disagreeing on the same machine, reinforcing that Phase I's repeated "8"
  above L1 was the shared small-structure confound, not real signal. LLC
  size matches Phase I's ~8 MiB estimate to the exact byte (8,388,608 B).
  **New finding, not seen on Sunbird/Thunderbird: the LLC-footprint run's
  own bench latency diverged +71.7% from Phase I's original hit_latency
  result** (≈128.42 vs. ≈74.78 ticks), coinciding with an unstable implied
  clock frequency across repeats (2.32-4.80 GHz, computed from `cycles ÷
  duration_time` — briefly exceeding this CPU's own 4.2 GHz max turbo) even
  though the run's own core (3) was independently confirmed idle
  throughout via `mpstat` before/during/after — attributed to
  shared-LLC/memory-bandwidth contention and per-package Turbo Boost
  power-budget sharing from two other students' processes pinned at 100%
  on cores 0 and 2 the entire session: an idle *core* doesn't insulate a
  benchmark from contention on *chip-shared* resources (LLC, package power
  budget) the way it does for private per-core L1/L2. A second, milder
  anomaly: the generic `cache-references` and `LLC-loads`-specific miss
  ratios both came back non-monotonic (higher at the small L1 footprint
  than at L2, before climbing again at LLC) — reproducible across all 3
  repeats at each level, attributed to the L1 footprint's very short timed
  loop (~3.3-4.6 ms) letting fixed one-time setup cost (fork/exec, warmup,
  permutation construction) dominate that ratio's denominator; the
  L1-dcache-specific miss rate doesn't show this artifact and climbs
  monotonically as expected, and was used as the more trustworthy per-level
  indicator instead. Neither anomaly was re-run this session — flagged
  plainly, not smoothed over, consistent with this project's practice
  elsewhere. Also worth reusing: this session's shell had a default
  `Cpus_allowed_list: 0-1`, but `taskset -c <core>` still successfully
  retargeted to any of the machine's 8 logical CPUs (verified before
  relying on it) — not a hard cgroup restriction, just an inherited
  default affinity.
- **Artemisia results (full detail:
  `data_processed/artemisia/PHASE2_VALIDATION_TABLE.md`)**: run via
  `scripts/run_pmu_verification.sh artemisia 1
  L1:49152,L2:2097152,LLC:31457280`, core 1, timestamp `20260914T003056Z`.
  This machine's CPU (2x Xeon Gold 5420+, Sapphire Rapids) postdates Agner
  Fog's published table, so literature came from Intel ARK's own SKU page
  (size only) plus two Chips and Cheese articles for latency-in-cycles
  numbers not published by Intel, per this section's existing "use vendor
  docs... supplemented by WikiChip/Chips and Cheese" guidance.
  **L1D and L2 both show an exact associativity match between Phase I's own
  explicitly-low-confidence, confound-blocked best guesses (12-way and
  16-way, respectively) and Phase II system-report** — a stronger
  confirmation story than Sunbird's or Thunderbird's, where at least one
  level's Phase I guess was wrong (Sunbird's LLC 9-way vs. real 20-way;
  Thunderbird's L2 12-way vs. real 8-way). Size/sets/line/sharing also match
  exactly at both levels, including Intel's own SKU-specific spec sheet.
  **LLC is the one real disagreement, and unlike Sunbird/Thunderbird it's a
  SIZE disagreement, not just associativity**: Phase I's `CAPACITY_RESULTS.md`
  value (~30 MiB) was always flagged as a representative, unconfirmed
  footprint (this machine's own capacity data found no discrete L2/L3
  plateau at all); system-report AND Intel ARK independently agree the real
  per-socket L3 is 52.5 MiB (55,050,240 B) — 1.75x Phase I's value. This
  directly explains why the capacity sweep never found a clean edge near
  30 MiB (deep inside the ramp, not at it) and is consistent with the
  ~90 MiB plateau onset that sweep did find. LLC associativity:
  system-reported 15-way, closer to Phase I's 16-way point estimate than to
  its own "equally plausible" 8-way alternative, but not an exact match
  either way. **This run's own LLC-footprint PMU numbers look
  contention-inflated** by another student's concurrently-running `incl_pmu`
  benchmark sharing this run's socket/LLC domain (confirmed via `ps`) — bench
  latency at the LLC footprint came back ~2.5x this machine's own original
  Phase I latency-experiment number at the identical footprint, while L1's
  and L2's re-measurements stayed much closer to their original numbers;
  documented as likely real contention on top of a genuine signal, not
  papered over. This machine's PMU schedules all 8 requested hardware events
  in one single group at 100% (unlike Sunbird's/Thunderbird's 2-event
  ceiling) — the script's existing 4-group design was kept anyway for
  cross-machine file-layout consistency, not because this machine needed it.
- **Upgrade (2026-09-14): Phase II PMU verification complete — the 8th and
  last machine, closing out this section.** Ran
  `scripts/run_pmu_verification.sh upgrade 5
  L1:32768,L2:262144,LLC:12582912` (core 5, idle-checked via 3 `/proc/stat`
  sampling windows despite another student's `incl_pmu`/`cache_bench_x86`
  job pinning cores 0/2 at 100% the whole session — the same contention
  signature Ookay's own bullet above independently documented on its own
  machine; base_seed=12345 + 2 repeats, 1,000,000 samples/run, timestamp
  `20260914T003134Z`). Literature: Agner Fog's Skylake-family table
  (§11.12, Table 11.2, p.160 — Coffee Lake is explicitly named in that
  chapter as sharing Skylake's design) plus uops.info's per-SKU Coffee Lake
  (i7-8700K) cache table as a second source, needed because Fog's family
  table gives no L3 associativity figure at all (only a size/latency
  range) — see `data_processed/upgrade/PHASE2_VALIDATION_TABLE.md`.
  **L1D: exact match, all 3 sources + literature** (8-way), the cleanest
  row, same pattern as every other machine's L1D row so far. **L2 AND LLC
  associativity both disagree with Phase I's confound-flagged
  8-way-at-both-levels best guess — system-reported gives L2=4-way/
  LLC=16-way, and both literature sources independently agree with both**
  — the same resolution pattern as Charnwood's and Ookay's own L2/LLC rows
  (4-way/16-way), and now cross-checked by 2 independent literature
  sources rather than system-report alone. All 4 perf event groups
  scheduled at 100% in every run — this machine never hit the
  2-generic-counter scheduling limit Sunbird's/Thunderbird's PMU had (same
  as Crux's/Artemisia's own finding). Notable finding: LLC-footprint
  miss-rate metrics showed high run-to-run spread (32.7-57.8%), plausibly
  from the confirmed cross-core contention (this machine's LLC is shared
  across all 12 threads) — read as corroborating, not contradicting, Phase
  I's own finding that this machine's capacity sweep never resolved a
  clean LLC edge in this size region. Full detail:
  `data_raw/upgrade/README.md`'s pmu/ section.

**Phase II PMU verification is now complete on all 8 team machines**
(Sunbird, Thunderbird, Crux, Charnwood, Skylark, Ookay, Artemisia,
Upgrade). **Running tally, cross-machine:** every x86 machine tested
reproduces the same L2/LLC-associativity confound-resolution pattern
Sunbird's LLC row first surfaced — Phase I's confound-blocked "8-way at
both levels" guess (the common fallback when the associativity method's
DTLB-scale confound blocked direct measurement) was wrong on every machine
that got a system-reported cross-check, most commonly resolving to 4-way
at L2 and 16-way at LLC (Charnwood, Ookay, Upgrade all show this exact
pair; Skylark's own L2 stayed at 8-way but LLC still corrected 8→16;
Crux's L2 also corrected to 4-way; Artemisia's is the one exception, where
both L1/L2 guesses were independently confirmed correct and only LLC
*size*, not associativity, needed correcting). L1D matched across every
source on every machine except Artemisia's (12-way, not independently
re-confirmed by PMU — see its own bullet). No single machine's PMU
counter-scheduling ceiling generalized to the whole team (2 generic
counters on Sunbird/Thunderbird; all 7-8 events at once on Crux/Artemisia/
Upgrade) — worth hand-checking fresh on any future machine rather than
assuming either extreme.

**Software-only cache hit-rate estimator (Problem 8.5): implemented and run
on Sunbird only so far (2026-09-14) — read this before running the PMU
validation piece on another machine, it has already been through one
invalid design.** `main_code/software_hit_rate/software_hit_rate.{c,h}`
(no PMU/perf access anywhere in that file) self-calibrates a resident-vs-
nonresident latency threshold (ROC/Youden's J), classifies a test
workload's single-shot access latencies against it, and debiases the raw
classified rate into Hhat via the Rogan-Gladen prevalence-correction
estimator, with a bootstrap CI. "Hit" is defined as "served by ANY cache
level, not DRAM" — see the header doc comment for the full method and its
own documented KNOWN LIMITATIONS (a single global threshold cannot
distinguish an LLC-speed hit from a DRAM miss as cleanly as an L1-speed
hit — this is not hypothetical, see the PMU validation results below).

- **Sweep (parts 1-3, standalone)**: `scripts/run_software_hit_rate_sweep.sh
  <machine> <core> [footprint_bytes_csv]` + `scripts/
  summarize_software_hit_rate.py` + `scripts/plot_software_hit_rate.py`.
  No perf involved at all — safe to run on any machine at any time,
  independent of Phase discipline. Anchor the footprint list to that
  machine's own `CAPACITY_RESULTS.md`/`FINAL_CACHE_TABLE.md` boundaries
  (the default list is Sunbird-specific). **Sunbird's own sweep already
  surfaced a real, reusable finding**: Hhat reads ~1.0 through L2-scale
  footprints as expected, but dips to 0.8664 (not ~1.0) at the EXACT L1
  capacity boundary (32768 B) — a genuine conflict/associativity-edge
  effect (a random cyclic address stream sized to exactly fill a level
  does not evenly fill every set), not noise. Keep this in mind if a
  future machine's sweep shows an unexpected dip exactly at one of its own
  capacity boundaries — it's expected, not a bug.
- **PMU validation (part 4)**: `scripts/run_hit_rate_pmu_validation.sh
  <machine> <core> <level>:<footprint_bytes>[,...]` + `scripts/
  compare_hit_rate_pmu.py`. Phase-II-only (needs `phase1-timing-only`
  tagged first, same discipline as `run_pmu_verification.sh`).
  **IMPORTANT — the version of this script now in the repo is already the
  FIXED, second design; do not re-derive the broken first version.** The
  original design (perf-wrapping `--experiment hit_rate` directly, in PMU
  validation mode, to get Hhat and H_pmu from literally identical timed
  accesses) produced unusable results on Sunbird — rel_error_pct of
  ~99-100% at every level (L1 read Hhat=0.0 for a footprint that fits
  entirely in L1). Root-caused via a controlled A/B replay (same binary/
  args/seed, only the perf wrapper differed) to TWO compounding problems:
  (1) testing each level at its EXACT `CAPACITY_RESULTS.md` boundary
  rather than safely inside it (matches the sweep's own L1-boundary dip
  above — Hhat there is genuinely seed-sensitive right at an exact
  boundary, swinging 0.37-1.0 across seeds with no perf involved at all);
  (2) `perf stat` itself reproducibly and severely distorting
  `software_hit_rate.c`'s single-shot-per-access `lfence+rdtsc...
  rdtscp+lfence` timing loop (unlike this project's `hit_latency`
  experiment's BATCHED timing, already perf-wrapped cleanly on every team
  machine) — a same-seed/same-footprint A/B pair went from p_obs=0.998
  (unwrapped, correct) to p_obs=0.317 (perf-wrapped) with wall time
  inflating from an expected ~2 ms to 2.9 seconds; a bare `perf stat --
  /bin/true` control only took 14 ms, ruling out simple perf-startup
  overhead. Leading hypothesis, not exhaustively confirmed:
  `nmi_watchdog=1` (already known to pin a PMU counter on Sunbird, see the
  Phase II PMU section above) periodically interrupting the tight
  per-access loop in a way it doesn't disrupt `hit_latency`'s coarser
  batched one; `systemd-detect-virt` confirms bare metal, ruling out a
  VM-trap explanation. **Fix, now baked into the script itself (no action
  needed on a future machine beyond just running it)**: (a) L1/L2/LLC are
  tested at HALF their given `CAPACITY_RESULTS.md` footprint, not the
  exact boundary (DRAM is left as given); (b) Hhat now comes from an
  UNWRAPPED `hit_rate` run, and H_pmu now comes from a SEPARATE
  perf-wrapped `--experiment hit_latency` run (batched timing, same
  samples/batch/warmup as `run_pmu_verification.sh`) at the same
  footprint/seed — decoupled sources instead of one perf-wrapped fragile
  loop. **Sunbird's results under the fixed design** (core 1,
  timestamp `20260914T025929Z`): L1 rel_error=30.1% (Hhat=1.0,
  H_pmu=0.768), L2 rel_error=12.4% (Hhat=0.956, H_pmu=0.851) — both sane
  and citable. **LLC (rel_error=98.7%, Hhat=0.013 vs H_pmu=0.978) and DRAM
  (rel_error=99.9%, Hhat=0.0001 vs H_pmu=0.144) still disagree hugely —
  this is EXPECTED and real, not a sign the fix didn't work; do not
  re-investigate this as a bug on another machine.** It's the estimator's
  own documented single-threshold limitation: tau (~80-84 ticks on
  Sunbird) sits well below a genuine LLC hit's true single-shot latency
  (LLC hit latency + this machine's own ~64-85 tick documented single-shot
  fixed overhead), so real LLC hits get classified "miss" regardless of
  footprint choice or perf involvement. Expect the same LLC/DRAM-diverges,
  L1/L2-agrees pattern on every future machine — that IS the citable
  finding ("this estimator reliably detects L1-scale residency only,
  despite its intended any-cache-level definition"), not something a
  redesign should try to eliminate. Full writeup, including the exact
  broken-run numbers kept as evidence:
  `data_raw/sunbird/README.md`'s `software_hit_rate/` section.
- **Redesigned PMU validation confirmed cross-architecture on Thunderbird
  (ARM, 2026-09-14) — PMU validation piece only, the sweep hasn't been run
  on this machine yet.** `./scripts/run_hit_rate_pmu_validation.sh
  thunderbird 3 L1:65536,L2:1048576,LLC:31457280,DRAM:536870912`, core 3,
  timestamp `20260914T032826Z`. **Mechanically, both fixes generalized with
  no changes needed**: no 0.0/1.0 classification flips, and perf-wrapped
  durations scaled sanely with footprint size (L1=71ms through
  DRAM=24.8s) instead of the ~1.7-2.9s fixed floor the original broken
  design produced at every footprint regardless of size. L1/L2 validated
  cleanly (rel_error 0.08%/6.4%). **LLC's disagreement (Hhat=0.36 vs.
  H_pmu=0.94) is the same expected classifier limitation, just
  numerically different for an architecture-specific reason**: every
  calibration this session produced `tau=1.0000` (ARM's 25 MHz
  `CNTVCT_EL0` is far coarser than x86 TSC), and this machine's own
  confirmed LLC hit latency (~36 ns ≈ 0.9 ticks at this resolution) sits
  close enough to tau=1 that a sizeable fraction of LLC hits land at or
  below it — unlike Sunbird's fine-grained TSC, where LLC latency
  unambiguously exceeds tau. **DRAM's H_pmu=0.9466 is a genuinely new,
  separate finding, not a harness bug**: checked directly from the raw
  perf output, `cache-misses/cache-references` = 5.3% even at full
  512 MiB DRAM scale — this machine's generic `cache-references`/
  `cache-misses` PMU alias tracks something much closer to L1-scope
  traffic than a true any-cache-vs-DRAM signal (already independently
  documented in this machine's Phase II PMU verification work above; now
  directly reproduced in the hit_rate context too). H_pmu is simply not
  trustworthy ground truth on this machine at DRAM scale, independent of
  anything the harness controls — do not read this as evidence the
  redesign failed here. Also worth reusing: this machine's own git remote
  has no cached GitHub credentials (`git fetch` fails, "could not read
  Username") — a pre-existing condition unrelated to this work; the
  redesigned scripts were copied over via `scp` instead of `git pull`.
  Full writeup: `data_raw/thunderbird/README.md`'s `software_hit_rate/`
  section.
- **Skylark (x86/AMD Zen 2, 2026-09-14): full flow run (both the sweep AND
  the PMU validation, matching Sunbird's fuller coverage rather than
  Thunderbird's PMU-only run).** Core 10 (confirmed idle via two `mpstat`
  samples), same core as this machine's other experiments.
  Sweep: `./scripts/run_software_hit_rate_sweep.sh skylark 10 <16-point list,
  with this machine's own 524,288 B L2 boundary substituted in for
  Sunbird's 262,144 B default>`, timestamp `20260914T041244Z`. **Found AND
  FIXED a latent bug in `run_software_hit_rate_sweep.sh` itself**: the
  script unconditionally hardcoded Sunbird's own boundary values when it
  called the plotting step, so Skylark's L2/LLC reference lines came out
  wrong at first (L1's 32,768 B happened to match by coincidence). This
  run's own plots were regenerated by hand with `--boundary L1:32768
  --boundary L2:524288 --boundary LLC:8388608 --boundary DRAM:536870912`
  immediately; the script was then patched the same session to take an
  optional 4th `boundary_spec` argument (`L1:<bytes>,L2:<bytes>,
  LLC:<bytes>,DRAM:<bytes>`, matching `run_hit_rate_pmu_validation.sh`'s
  existing `<level>:<bytes>` format) instead of hardcoding the flags, still
  defaulting to Sunbird's boundaries when the argument is omitted. A future
  run on any machine other than Sunbird should pass this argument
  explicitly.
  Headline: Hhat=1.0000 clear through 131,072 B (**no dip at the exact L1
  boundary**, unlike Sunbird's 0.8664 dip at its own L1 edge), then falls
  off — but non-monotonically: a dip to 0.8017 at 1,048,576 B followed by a
  partial recovery to ~0.92 at 4,194,304-8,388,608 B before resuming its
  fall at 16,777,216 B and beyond. Plausibly tied to this machine's own
  already-documented unresolved ~4-16.8 MiB capacity region (one continuous
  ramp, no confirmed shelf) rather than a new artifact — not
  re-investigated further this session.
  PMU validation: `./scripts/run_hit_rate_pmu_validation.sh skylark 10
  L1:32768,L2:524288,LLC:8388608,DRAM:536870912`, timestamp
  `20260914T042323Z`. **L2 agreement (0.78% rel. error) is the tightest of
  any machine/level this investigation has produced so far.** **L1
  disagreement (48.0%) is worse than Sunbird (30.1%) or Thunderbird
  (0.08%), explained by a limitation this machine's OWN Phase II PMU work
  already flagged** (`PHASE2_VALIDATION_TABLE.md`): the generic AMD
  `cache-references`/`cache-misses` alias produces only a small, noisy
  trickle of events at L1 scale on this CPU (~41-44K counted this run, same
  order of magnitude as the ~69K already flagged as unreliable in the
  earlier PMU-verification run) — Hhat=1.0000 is the trustworthy number.
  **LLC's row carries an extra, Skylark-specific caveat**: the tested
  footprint (half of the `CAPACITY_RESULTS.md` 8 MiB value = 4 MiB) is only
  half of the *true* system-reported 16 MiB LLC capacity's own safe-inside
  point (8 MiB) — this row is really probing the L2-to-LLC transition tail,
  not deep LLC, which is consistent with its less-than-fully-resolved
  Hhat≈0.88/H_pmu≈0.55 numbers; not re-run at a corrected footprint this
  session. DRAM's 99.98% disagreement reproduces the same generic-counter-
  is-not-an-any-cache-vs-DRAM-signal finding already seen on both other
  machines. Full writeup: `data_raw/skylark/README.md`'s
  `software_hit_rate/` section.

**Moore-style chronological master table + cross-generation plots: done
(2026-09-14), the first concrete step of Phase III/§9 — but this is
prerequisite consolidation work, NOT the frozen prediction itself, and does
NOT unblock touching Hazel.** Per `README.md`'s Phase Discipline, the
lab-only prediction must still be frozen/tagged (`PREDICTION_FREEZE.md`)
before any Hazel cache experiment — this section only builds the trend data
that freeze will be fit from.
- **Consolidated all 8 machines' `FINAL_CACHE_TABLE.md` (Phase I, frozen,
  the primary/plotted series) + `PHASE2_VALIDATION_TABLE.md` (Phase II
  PMU/system-report/literature, kept as a separate verification flag, never
  substituted in) into `CHRONOLOGICAL_MASTER_TABLE.md`** (repo root,
  alongside `CAPACITY_RESULTS.md`) and its machine-readable backing file
  `data_processed/master/chronological_master_table.csv`. Sourcing rule
  applied throughout, per `PROJECT 1.pdf`'s Table 5 instruction: every cell's
  primary value is Phase I's timing-only number; a Phase II disagreement is
  shown as `Phase I → Phase II` with an explicit match/mismatch flag, never
  silently overwritten.
- **Cross-machine findings worth citing directly in the report's §9 write-up
  (full detail: `CHRONOLOGICAL_MASTER_TABLE.md`'s own "Notable cross-machine
  data-quality findings" section):**
  1. L1D size/associativity/sets/line matched Phase II ground truth on
     **all 8 of 8 machines, zero exceptions** — the strongest validation of
     the timing-only method in this project.
  2. L2 associativity disagreed with Phase II on 5 of 8 machines; LLC
     associativity disagreed on 7 of 8 (only Artemisia's 16-vs-15 came
     close) — a now-quantified cost of the documented DTLB-scale confound
     above L1.
  3. LLC *capacity* itself (not just associativity) was wrong on 3 of 8
     machines (Crux, Skylark, Artemisia) — each time because that machine's
     own Phase-I capacity sweep never found a clean plateau at the
     `CAPACITY_RESULTS.md` value used; Phase II's system-report/vendor-spec
     closed the gap in every case.
  4. LLC sharing *domain* is not "one socket" universally — Skylark's is a
     2-core CCX slice (AMD Rome cache-doubled binning), Thunderbird's is all
     80 SoC cores (a distributed SLC) — the master table normalizes MiB/core
     to each machine's own actual domain, not blindly to total box cores.
- **Units methodology, explicit and auditable (not "cycles from nominal
  GHz"):** ns/access is derived per machine for cross-architecture
  comparability — Thunderbird via its independently-read `CNTFRQ_EL0` =
  25 MHz (a genuinely calibrated hardware constant, already established in
  Phase I); every x86 machine via that CPU's own rated base clock (an
  already-collected, Phase-I-safe `lscpu` field) under the standard
  `constant_tsc`/invariant-TSC assumption. This converts an already-measured
  elapsed-tick count into seconds — it does not fabricate a cycle count —
  and is the same conversion several individual machines'
  `PHASE2_VALIDATION_TABLE.md` files already used ad hoc (e.g. Sunbird's
  "~4.14 ns @ 2.5 GHz nominal"); this session just applied it uniformly
  across all 8 for the master table/plots.
- **15 of the 15 required chronological plots produced** (`scripts/
  plot_chronological_master.py` → `plots/chrono_01..15_*.{png,pdf}`,
  grayscale/no-gridlines/solid-marker "old-ISCA" style matching
  `plot_capacity.py`'s existing convention; distinct marker shapes for
  Intel/AMD/Arm; log2 y-axis for the 3 capacity plots; open-marker +
  dotted-tie-line overlay wherever Phase II resolved a Phase-I
  disagreement, so the correction is visible without replacing the plotted
  point). **Plot item 14 (timing-derived hit-rate/residency metric vs.
  year) is STILL NOT produced, but the reason has changed since this
  section was first drafted (in a separate, concurrent merge — see this
  file's own "Software-only cache hit-rate estimator" bullet above)**: the
  estimator (`PROJECT 1.pdf` §8.5, `main_code/software_hit_rate/`) is no
  longer an empty stub — it's implemented and has PMU-validated results on
  Sunbird, Thunderbird, and now Skylark — but a cross-machine chronological
  plot needs data from all 8 machines, and only 3 of 8 have any
  `software_hit_rate` data collected so far. Still a known gap, just a
  narrower one than "the code doesn't exist yet."
- **Still open before Hazel can be touched at all**: fit the actual
  quantitative trend models/doubling-times from this data, formulate and
  freeze the two named team "Cache Laws," fill in and tag
  `PREDICTION_FREEZE.md`, THEN (only after that tag) verify Hazel access and
  begin §8.6. Also still open, independent of Hazel: §8.4's eight-counter
  *cross-machine standardized* comparison — item 1 (the 3 fixed
  benchmarks themselves) is no longer a stub as of 2026-09-14, see the
  dedicated bullet just below, but items 2-4 (normalization, ranked
  S-curves, and the Intel/AMD/Arm + generation comparison) still need all
  8 machines' data first; and finishing §8.5's software-only hit-rate
  estimator's cross-machine coverage (implemented and validated on 3 of 8
  machines so far — see this file's own "Software-only cache hit-rate
  estimator" bullet above — not a stub anymore, just incomplete).

**Problem 8.4 (eight interesting performance counters across generations),
item 1: started 2026-09-14, Sunbird, Thunderbird, Skylark, Charnwood, Crux,
and Ookay done (6 of 8 machines).**
New pipeline
`scripts/run_standardized_benchmarks.sh` + `scripts/summarize_eight_counters.py`
runs the same `--experiment hit_latency --load-mode dependent --pattern
random` construction already used everywhere in this project (no new C
code — the "3 microbenchmarks" are just 3 standardized `--footprint-bytes`
choices of the existing benchmark) at 3 fixed, cross-machine-standardized
names — `L1_resident`, `LLC_random`, `beyond_LLC` — instead of raw byte
values, so every machine's own footprint values can differ (per its own
`FINAL_CACHE_TABLE.md`) while the benchmark identity stays comparable.
Collects a **different fixed 8-event set than `run_pmu_verification.sh`'s
own**: `cache-references`, `cache-misses`, `L1-dcache-loads`,
`L1-dcache-load-misses`, `L1-dcache-stores`, `LLC-loads`, `LLC-load-misses`,
`dTLB-load-misses` (swaps out that pipeline's `cycles`/`instructions` pair
for the L1 store-side signal and a real dTLB-miss count) — chosen because
per-access normalization (item 2) doesn't need an instructions counter, and
dTLB-load-misses gives this project's first direct measured data toward the
still-open DTLB-scale confound question from the associativity
investigation, rather than only the structural/inferential evidence
gathered so far. Same proven 4-groups-of-2 perf-scheduling split as
`run_pmu_verification.sh` (3 of 4 groups byte-identical; only the 4th
differs), same base+2-reproducibility-repeat convention.
- **Sunbird** (`data_raw/sunbird/eight_counters/`, core 1, base_seed=12345,
  timestamp `20260914T041517Z`): all 3 benchmarks + all 8 counters
  collected cleanly, ticks/access and `dtlb_load_misses` both climb
  monotonically with footprint as expected (`L1_resident`≈14.4,
  `LLC_random`≈57.7-59.5 — matching this machine's own already-documented
  ≈58.42-tick LLC hit latency almost exactly — `beyond_LLC`≈254-258
  ticks/access). One honestly-flagged anomaly: `beyond_LLC`'s latency
  reads noticeably higher than this machine's own previously-documented
  ≈207-tick DRAM hit latency, most likely from another student's
  `cache_bench_x86` process confirmed pinned on core 4 for the whole
  session (a shared memory-bandwidth/LLC-contention effect, not insulated
  by this run's own idle *core* — the same "idle core doesn't protect
  against chip-shared contention" finding already documented for Ookay's
  PMU run) — not re-run this session. Full detail:
  `data_raw/sunbird/README.md`'s `eight_counters/` section.
- **Thunderbird** (`data_raw/thunderbird/eight_counters/`, core 3,
  base_seed=12345, timestamp `20260914T043110Z`; scripts copied over via
  `scp`, same as this machine's earlier Phase II PMU work, since its git
  remote still has no cached GitHub credentials). Machine-specific PMU
  check confirmed `L1-dcache-stores` isn't even listed in `perf list` on
  this `armv8_pmuv3_0` PMU (unlike Sunbird) and, together with the
  already-documented `LLC-loads`/`LLC-load-misses`, comes back
  `<not supported>` gracefully (exit 0), no script changes needed —
  `dTLB-load-misses` counts fine. `L1_resident`≈0.085 ticks/access,
  sane and small. **Two things worth flagging, not smoothing over**: (1)
  `LLC_random`≈2.16 ticks/access reads well above this machine's own
  previously-documented ≈0.907-tick LLC hit latency, while `beyond_LLC`
  ≈2.44 stays close to its own documented ≈2.336-tick DRAM latency —
  compressing the LLC-to-DRAM gap from the documented ~2.6x down to ~1.13x
  in this run, most likely from two other students' processes (`incl_pmu`
  on core 0, `cache_bench_arm` on core 2) confirmed active the whole
  session, contending for chip-shared LLC/memory bandwidth despite core 3
  itself staying idle — the same "idle core doesn't insulate from
  chip-shared contention" pattern as Sunbird's own `beyond_LLC` anomaly
  above, not re-run this session. (2) `cache_miss_rate`≈`l1_miss_rate` at
  every footprint (0.20/0.19% at L1_resident, 5.46/5.46% at LLC_random,
  5.33/5.34% at beyond_LLC) — confirms, in this new counter set too, the
  already-documented ARM PMU quirk that this machine's generic
  `cache-references`/`cache-misses` alias tracks L1-scope traffic rather
  than a true any-cache-vs-DRAM signal. `dtlb_load_misses` climbs cleanly
  monotonic across all 3 benchmarks (~1500 → ~1.1-1.8M → ~256M),
  unaffected by that limitation. Full detail:
  `data_raw/thunderbird/README.md`'s `eight_counters/` section.
- **Skylark** (`data_raw/skylark/eight_counters/`, core 5, base_seed=12345,
  timestamp `20260914T051608Z`). Notably, **only 5 of the assignment's 8
  event names are even listed by `perf list` on this AMD Zen 2 PMU**
  (`L1-dcache-stores`, `LLC-loads`, and `LLC-load-misses` are absent from
  the listing entirely, not merely present-but-unsupported) — a stronger,
  cleaner version of the same AMD limitation already documented in this
  machine's `pmu/` section (§8.3), now cross-checked against `perf list`
  itself rather than only the runtime `<not supported>` value. All 3
  benchmarks' ticks/access match this machine's own already-documented
  Phase I `latency/` numbers almost exactly (`L1_resident`≈6.264,
  `LLC_random`≈27.24, `beyond_LLC`≈274.87 — the last one matching the
  documented ≈274.87-tick DRAM latency essentially exactly). **Unlike
  Sunbird's and Ookay's own `beyond_LLC` runs (both inflated by other
  students' processes contending for chip-shared LLC/memory bandwidth
  despite an idle core), Skylark's `beyond_LLC` shows no such anomaly**,
  even though another student's process was confirmed active on core 3
  the whole session — not further investigated. `dtlb_load_misses` climbs
  cleanly monotonic across all 3 benchmarks (~691 → ~2,905 → ~10,901).
  Full detail: `data_raw/skylark/README.md`'s `eight_counters/` section.
- **Charnwood** (`data_raw/charnwood/eight_counters/`, core 3,
  base_seed=12345, timestamp `20260914T052928Z`). All 4 perf groups
  scheduled at 100% for every (benchmark, run_tag) — no `<not counted>`
  anywhere. **The cleanest cross-check of any machine's `eight_counters`/
  `pmu` run so far**: this session's idle-core check found the machine
  fully quiet (the two other students' processes documented in this
  machine's `pmu/` section had both since exited), and the resulting
  `bench_avg_ticks_per_access_median` ladder (`L1_resident`≈8.016,
  `LLC_random`≈106.185, `beyond_LLC`≈394.551) matches this machine's own
  already-documented Phase I `latency/` numbers (≈7.98 / ≈106.9-109.1 /
  ≈394.6-394.8) to within ~0.5%, ~1%, and ~0.06% respectively — unlike
  Sunbird's, Thunderbird's, and Ookay's own `beyond_LLC`/PMU runs, none of
  which had a comparably quiet session and all of which showed a
  contention-driven divergence from their own Phase I baseline. `l1_miss_rate`
  (1.08%→8.83%→13.42%) and `llc_miss_rate` (14.0%→15.9%→47.5%, the last a
  clean order-of-magnitude jump exactly at `beyond_LLC`) both climb as
  expected. `dtlb_load_misses` climbs cleanly monotonic across all 3
  benchmarks (2,025 → 1,096,978 → 253,582,411). Full detail:
  `data_raw/charnwood/README.md`'s `eight_counters/` section.
- **Crux** (`data_raw/crux/eight_counters/`, core 1, base_seed=12345,
  timestamp `20260914T052920Z`; footprints `L1_resident:32768,
  LLC_random:8388608` per this machine's own `FINAL_CACHE_TABLE.md`,
  `beyond_LLC:536870912` universal). Core re-verified idle via two
  `/proc/stat` idle-delta samples 4s apart immediately before this run
  (the other students' jobs that had pinned cores 0/2 during this
  machine's earlier `pmu/` §8.3 session had since exited — all 8 cores
  ~99-100% idle this time). **The cleanest of the four runs done so far**:
  `L1_resident`≈6.94, `LLC_random`≈42.25, `beyond_LLC`≈237.64 ticks/access,
  each within ~6.5% of this machine's own already-documented Phase I
  `latency/` hit-latency numbers at the matching footprint (7.42/43.23/
  236.80) — no contention-driven `beyond_LLC` inflation the way Sunbird's,
  Thunderbird's, and (in the §8.3 pipeline) Ookay's runs all showed, most
  likely because every core (not just the pinned one) was genuinely idle
  this time, not only the run's own core. `l1_miss_rate` climbs cleanly
  monotonically across all 3 benchmarks (1.05% → 8.80% → 13.4%) — unlike
  this machine's own `pmu/` section, where the ratio saturates and drops
  once past L1 into L2/LLC territory, here it keeps climbing because
  `beyond_LLC` goes past LLC entirely, not just past L1. `dtlb_load_misses`
  climbs cleanly and monotonically (median 1,349 → 1,080,275 → 254,971,011),
  consistent with Sunbird/Thunderbird/Skylark's own pattern. Full detail:
  `data_raw/crux/README.md`'s `eight_counters/` section.
- **Ookay** (`data_raw/ookay/eight_counters/`, core 3, base_seed=12345,
  timestamp `20260914T052901Z`; machine independently confirmed idle on
  every core via 3 `mpstat` samples before running — the two other
  students' processes from this machine's earlier `pmu/` run had since
  finished). All 3 benchmarks + all 8 counters collected cleanly, no
  `<not counted>` anywhere. Ticks/access climb monotonically as expected
  (`L1_resident`≈7.60, `LLC_random`≈80.24, `beyond_LLC`≈287.44), closely
  matching this machine's own Phase I numbers (≈7.49/≈74.78/≈284.45).
  Notably, `LLC_random`'s ≈80.24 sits much closer to Phase I's ≈74.78 than
  this same machine's earlier (contended) `pmu/` run's LLC reading
  (≈128.42) did — corroborating that run's own hypothesis that its
  inflation came from other students' processes contending for
  chip-shared LLC/memory bandwidth, not a measurement problem, since this
  run's machine was confirmed quiet throughout. `l1_miss_rate` climbs
  cleanly monotonic (0.96% → 8.79% → 13.36%); unlike this morning's
  `pmu/` run, the generic `cache_miss_rate` and `llc_miss_rate` also climb
  monotonically here rather than dipping at the middle footprint,
  plausibly for the same quiet-machine reason (footprints aren't directly
  comparable between the two pipelines, so not conclusive).
  `dtlb_load_misses` climbs cleanly across 3 orders of magnitude (1,838 →
  1,091,713 → 252,964,812) — real hardware data toward the DTLB-confound
  question, not yet interpreted (needs all 8 machines first). Full detail:
  `data_raw/ookay/README.md`'s `eight_counters/` section.
- **6 of 8 machines done (Sunbird, Thunderbird, Skylark, Charnwood, Crux,
  Ookay); 2 remaining** (Artemisia, Upgrade). Each needs the same command
  (`./scripts/run_standardized_benchmarks.sh <machine> <core>
  L1_resident:<L1_bytes>,LLC_random:<LLC_bytes>,beyond_LLC:536870912`) with
  its own `FINAL_CACHE_TABLE.md` L1/LLC values. Items 2-4 of 8.4 cannot be
  attempted until all 8 machines have this data.

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
