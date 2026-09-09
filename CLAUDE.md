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
Skylark, Upgrade, Charnwood, Thunderbird, and Ookay — not yet started on
Artemisia.** Several sessions ran this in parallel on different machines;
this section was consolidated from all of their commits/READMEs during a
merge, so re-check each machine's own `data_raw/<machine>/README.md`
before citing a number — summaries below are necessarily compressed.

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

**`scripts/run_capacity_full.sh <machine> <core> [coarse_max_bytes]` is
the one-command pipeline for running the capacity experiment on each
remaining machine** (Artemisia — and Charnwood again once quiet, and
Upgrade needs its README backfilled + a plateau check): coarse sweep
-> automatic boundary detection -> dense sweep per boundary ->
reproducibility repeats on the deepest boundary -> tail-extension sweep
to check for a further plateau -> plots -> gzips its own raw CSVs (commit
the `.csv.gz`, not a decompressed copy — see `.gitignore`; the repo was
already at ~291MB for just 2 machines/1 experiment type before this
convention). It is deliberately non-adaptive (see the script's own header
comment for why). After it finishes on a machine, fill in that machine's
`data_raw/<machine>/README.md` using the core/seed/timestamp/boundaries
it prints at the end, and — as done for Sunbird/Crux/Skylark/Charnwood/
Thunderbird — manually extend the tail further (with 1-2 repeats, gzip
any ad hoc raw CSVs by hand before committing) if the topmost region is
still climbing rather than flat at the script's default ceiling. Check
early whether `python3 -c "import matplotlib"` works on the new machine
(this bit both Skylark and Thunderbird) — and if the machine is ARM,
expect to redo boundary detection by hand as described in Thunderbird's
bullet above (no other ARM machines remain in the team's list per
`MACHINE_RESEARCH.md`, but the same coarse-counter-resolution issue could
recur on any low-frequency architected timer).

**Not yet started (data collection):** line size, associativity, hit/miss
latency, inclusion/exclusion experiments — no machine has run any of
these yet (every `data_raw/<machine>/line_size/` etc. is still just a
`.gitkeep`). Code-wise, `--experiment line_size` now exists in
`cache_bench` (added by @krchen1, commit `5aaa83f`, with its own
`scripts/{run_line_size_full.sh,run_line_size_sweep.sh,detect_line_size.py,
plot_line_size.py}` pipeline — check that script's own header/`--help`
before using it, this session hasn't read it yet); `--experiment capacity`
remains the only one with real per-machine results. PMU verification
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
  assuming a core is quiet.
- `scripts/plot_capacity.py` combines overlapping (pattern, size) rows
  across input summary CSVs by averaging rather than letting the last
  file win — this matters because dense/repeat sweeps sharing a log-spaced
  grid will legitimately collide on many exact sizes.
