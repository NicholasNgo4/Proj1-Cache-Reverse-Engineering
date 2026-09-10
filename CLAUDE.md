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
  still a TODO, flagged in the README rather than faked.
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
- **Upgrade** (`data_raw/upgrade/capacity/`): raw/processed data and plots
  were committed, but **`data_raw/upgrade/README.md` is still the blank
  template** — hostname/CPU/environment fields were never filled in.
  From the run transcript log only: `run_capacity_full.sh upgrade 5`
  (default 64 MiB coarse ceiling), detected 6 boundaries (185360 / 311744
  / 9975792 / 11863280 / 18295680 / 21757352 bytes); no tail-extension
  follow-up past the default 256 MiB ceiling appears to have been done, so
  its topmost-region plateau status is **unverified**. Needs both the
  README backfilled and a plateau check, by whoever has access to that
  machine to confirm the identification fields firsthand.
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

**Associativity experiment: code done, one real data point (Sunbird L1 =
8-way).** `--experiment associativity` now exists in `cache_bench`, with
its own `scripts/{run_associativity_full.sh,detect_associativity.py,
plot_associativity.py}` pipeline (mirrors the capacity/line_size pipeline
shape: full per-level sweep -> knee detection -> 2 reproducibility repeats
-> plots; see `main_code/common/associativity.h`'s module docstring for
the method — a node-to-node stride fixed at a cache level's own capacity
forces every probed node into the same set with a distinct tag, so sweeping
how many such nodes are chased finds the hit->thrashing knee = associativity
for that level). Ran for real on Sunbird core 2 at cache_bytes=32768 (this
team's hand-confirmed L1 capacity): **flat plateau through num_ways=8,
sharp step at num_ways=9** (~10-12 ticks -> ~21+ ticks, 0% run-to-run
spread at both the last-flat and first-thrashing points across 3
independent runs) -> **L1 = 8-way**. See
`data_raw/sunbird/associativity/L1/` and
`data_processed/sunbird/associativity/L1/plots/`, documented in
`data_raw/sunbird/README.md`'s associativity section. **Deliberately not
yet run for L2/LLC on Sunbird or at all on the other 7 machines**: L2/LLC
capacity boundaries aren't hand-confirmed the way L1 is (the capacity
section's ~20 MiB / ~150 MiB Sunbird values are still provisional, and
several other machines' non-L1 boundaries are flagged noisy/unresolved
above) — `run_associativity_full.sh` will auto-detect+round a stride from
an existing capacity summary if no override is given, but prints a loud
warning not to trust that for L1 specifically (confirmed off by ~9x on
Sunbird: detect_cache_hierarchy.py's coarse boundary is 285864B/~279 KiB
vs the hand-confirmed 32 KiB). Prefer an explicit
`cache_bytes_csv` override built from each machine's own confirmed
capacity numbers once available, e.g.
`./scripts/run_associativity_full.sh <machine> <core> <L1>,<L2>,<LLC>`.

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
