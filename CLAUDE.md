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

**Capacity experiment: done on Sunbird, not yet started on the other 7
machines.** Sunbird's results (`data_raw/sunbird/capacity/`,
`data_processed/sunbird/capacity/`, including `plots/capacity_curve.png`
and `capacity_boxplots.png`) found three flat/ramp transitions across
1 KiB-256 MiB, confirmed via independent repeat runs (see
`data_raw/sunbird/README.md` for the full methodology notes, including a
documented multi-tenant-interference finding and a plotting-script bug
that was found and fixed along the way — read that file before trusting
any plateau/boundary number at face value).

**`scripts/run_capacity_full.sh <machine> <core> [coarse_max_bytes]` is
the one-command pipeline for running the capacity experiment on each
remaining machine** (Thunderbird, Skylark, Artemisia, Charnwood, Crux,
Ookay, Upgrade): coarse sweep -> automatic boundary detection -> dense
sweep per boundary -> reproducibility repeats on the deepest boundary ->
tail-extension sweep to check for a further plateau -> plots. It is
deliberately non-adaptive (see the script's own header comment for why).
After it finishes on a machine, fill in that machine's
`data_raw/<machine>/README.md` using the core/seed/timestamp/boundaries
it prints at the end.

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
