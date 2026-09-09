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

**Capacity experiment: done (with caveats, see below) on Sunbird, Crux,
Skylark, Upgrade, and Charnwood — not yet started on Thunderbird,
Artemisia, or Ookay.** Five different sessions ran this in parallel on
different machines; this section was consolidated from all of their
commits/READMEs during a merge, so re-check each machine's own
`data_raw/<machine>/README.md` before citing a number — summaries below
are necessarily compressed.

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

**`scripts/run_capacity_full.sh <machine> <core> [coarse_max_bytes]` is
the one-command pipeline for running the capacity experiment on each
remaining machine** (Thunderbird, Artemisia, Ookay — and Charnwood again
once quiet, and Upgrade needs its README backfilled + a plateau check):
coarse sweep -> automatic boundary detection -> dense sweep per boundary
-> reproducibility repeats on the deepest boundary -> tail-extension
sweep to check for a further plateau -> plots -> gzips its own raw CSVs
(commit the `.csv.gz`, not a decompressed copy — see `.gitignore`; the
repo was already at ~291MB for just 2 machines/1 experiment type before
this convention). It is deliberately non-adaptive (see the script's own
header comment for why). After it finishes on a machine, fill in that
machine's `data_raw/<machine>/README.md` using the core/seed/timestamp/
boundaries it prints at the end, and — as done for Sunbird/Crux/Skylark/
Charnwood — manually extend the tail further (with 1-2 repeats, gzip any
ad hoc raw CSVs by hand before committing) if the topmost region is still
climbing rather than flat at the script's default ceiling.

**Before running it on Thunderbird (the one ARM/AArch64 machine):**
`main_code/aarch64/timer_arm.h` has never been validated on real hardware.
Do a small standalone sanity check first (a handful of timed loads,
confirm `CNTVCT_EL0` is readable unprivileged and has usable resolution)
before trusting a full sweep's numbers there.

**Not yet started:** line size, associativity, hit/miss latency,
inclusion/exclusion experiments (only `--experiment capacity` exists in
`cache_bench` so far — see `main_code/common/main.c` usage text). PMU
verification (Phase II) and Hazel (Phase III) have not started; Phase I
must be frozen/tagged first per `README.md`.

## Known constraints from prior sessions

- Compile baseline is `-O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer`
  (see `Makefile`) — do not add optimization or drop `-g`/frame-pointer
  without updating the disassembly-inspection evidence too.
- Every `cache_bench` run must be pinned with `taskset -c <core>` (or
  `srun --cpu-bind=cores` on Hazel) — check `Cpus_allowed_list` and
  `lscpu -e=CPU,CORE,SOCKET,NODE` first to pick a full physical core (both
  SMT siblings) actually available to your session, and check `who`/`ps`
  for other students' active processes on this shared machine before
  assuming a core is quiet.
- `scripts/plot_capacity.py` combines overlapping (pattern, size) rows
  across input summary CSVs by averaging rather than letting the last
  file win — this matters because dense/repeat sweeps sharing a log-spaced
  grid will legitimately collide on many exact sizes.
