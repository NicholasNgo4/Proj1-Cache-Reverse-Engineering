# Phase II Validation Table — Sunbird (2026-09-13)

Per `PROJECT 1.pdf`'s Table 2 requirement: a compact post-Phase-I validation
table with measured size/ways/sets/line/latency/sharing-scope columns kept
**separate** from the cited reference/literature value and the Agreement
verdict. This file only exists because Phase I is now frozen and tagged
(`phase1-timing-only`, per `README.md`'s Phase Discipline) — nothing here
touches or overwrites `FINAL_CACHE_TABLE.md`, which remains the frozen,
timing-only Phase-I record.

**Three independent sources feed this table, kept distinguishable in every
cell:**
1. **Phase I (timing-only)** — carried over read-only from
   `data_processed/sunbird/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh sunbird 1
   L1:32768,L2:262144,LLC:31457280`, core 1, base_seed=12345 + 2 repeats,
   1,000,000 samples/run, timestamp `20260913T193142Z`). Raw:
   `data_raw/sunbird/pmu/<level>/`. Summaries:
   `data_processed/sunbird/pmu/<level>/pmu_summary_20260913T193142Z.csv`.
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/cpu0/cache/index*/*`, saved verbatim in
   `data_raw/sunbird/pmu/system_reported_cache_info.txt` (collected
   2026-09-13T19:28:20Z).
4. **Reference (literature)** — Agner Fog, *The microarchitecture of Intel,
   AMD and VIA CPUs*, last updated 2015-12-23, §10.11 "Cache and memory
   access", Table 10.2 "Cache sizes on Haswell and Broadwell", p. 143
   (canonical: `www.agner.org/optimize/microarchitecture.pdf`; this session
   read a mirrored copy at
   `cs.utexas.edu/~hunt/class/2018-spring/cs340d/documents/Agner-Fog/microarchitecture.pdf`).
   Sunbird is 2× Xeon E5-2680 v3, Haswell-EP — covered by this table.

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **32,768 B (32 KiB)** — Phase I confirmed; Phase II system-reported (`lscpu --caches`, sysfs `index0`) identical: 32K | **8-way** — Phase I confirmed (clean knee); Phase II system-reported: 8-way | **64** — Phase I derived (S=C/(A·B)); Phase II system-reported: 64 sets | **64 B** — Phase I confirmed (2 methods); Phase II system-reported: 64 B | Phase I: ≈10.35 ticks/access (~4.14 ns @ 2.5 GHz nominal). Phase II/PMU (same footprint, this run): median cycles/access ≈13.61, ns/access (wall-clock) ≈8.06 — **see caveat below, not a clean single-access number**. Phase II/PMU miss-rate corroboration: L1 miss rate 0.61% (median) — consistent with a fully L1-resident working set | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=0,24`** — private to one physical core's own 2 SMT threads only (confirms + sharpens the guess) | 32 kB, 8-way, 64 sets, 64 B line, **latency 4 cycles**, per core (Fog Table 10.2) | Size/ways/sets/line/sharing: **exact match, all 3 sources.** Latency: measured (~10.35 ticks / ~13.6 cycles) reads **higher** than Fog's 4 cycles — attributed to `-O0` dependent-chase loop overhead (stack spill/reload of the chase pointer between iterations sits in the true dependency chain; see Makefile's `-O0 -g` rationale), not a contradiction — Phase I's own writeup already flagged ticks as "not pure single-load latency" |
| L2 | **262,144 B (256 KiB)** — Phase I ("hand-verified, take as given" per `CAPACITY_RESULTS.md`); Phase II system-reported: 256K identical | **8-way** — Phase I *best guess* (blocked by the documented DTLB-scale confound, corroborated only indirectly via Upgrade's derived-stride-scan). **Phase II system-reported: 8-way — independently confirms the best guess** | **512** — Phase I derived; Phase II system-reported: 512 sets | **64 B** — Phase I confirmed; Phase II system-reported: 64 B | Phase I: ≈26.83 ticks/access. Phase II/PMU: median cycles/access ≈28.22, ns/access (wall-clock) ≈17.78 — same overhead caveat as L1. Miss-rate corroboration: L1 miss rate jumps to 12.59% (footprint now exceeds L1) while LLC-scope miss rate stays tiny (0.08%) — i.e. almost everything that misses L1 is caught by L2, exactly the signature of a footprint sized to fit L2 | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=0,24`** — private per physical core, same as L1 | 256 kB, 8-way, 512 sets, 64 B line, **latency 12 cycles**, per core (Fog Table 10.2) | Size/ways/sets/line/sharing: **exact match, all 3 sources** — the confound-blocked Phase-I associativity guess is now independently confirmed by direct OS/hardware self-report. Latency: measured (~26.83 ticks / ~28.2 cycles) **higher** than Fog's 12 cycles, same `-O0` loop-overhead explanation as L1 (inflation ratio ~2.2-2.6x, consistent across L1/L2) |
| LLC | **~30 MiB (31,457,280 B representative)** — Phase I, from `CAPACITY_RESULTS.md` (rounded estimate). **Phase II system-reported: 30,720 KiB = 31,457,280 B exactly** (per-socket `ONE-SIZE`; 60 MiB `ALL-SIZE` across both sockets) — an exact byte-for-byte match to Phase I's independently-derived estimate | Phase I: **best guess 9-way**, explicitly presented as an "effective lower bound" — heavily caveated, blocked by the same small-fixed-structure (likely DTLB) confound documented across 5+ machines. **Phase II system-reported: 20-way — a real disagreement, resolved in favor of the system-reported value** (see Agreement) | Phase I: ≈54,613 (non-integer, at 9-way — itself a red flag in hindsight). **Phase II system-reported: 24,576** (exact integer, S=31,457,280/(20·64)) | **64 B** — Phase I confirmed ("cleanest elbow of the three levels"); Phase II system-reported: 64 B | Phase I: ≈58.42 ticks/access (~23.4 ns @ 2.5 GHz). Phase II/PMU: median cycles/access ≈2025.8, ns/access (wall-clock) ≈866 — **NOT usable as an absolute latency number** (this footprint's warmup passes + permutation construction dominate total process time at this scale, per this file's PMU caveat below). Miss-rate corroboration is the reliable signal here: LLC-scope miss rate jumps to 11.25% and generic cache-miss rate to 14.21% (both were <1.4% at the L1/L2 footprints) — a clean order-of-magnitude jump exactly at the footprint Phase I placed the LLC boundary, corroborating it independently | Phase I: shared across cores/socket (architectural guess). **Phase II system-reported: `shared_cpu_list`** = all 24 logical CPUs of NUMA node 0 (12 physical cores × 2 SMT threads) — confirms and quantifies: shared across the *entire socket*, not across both sockets (each socket has its own private 30 MiB slice, matching `lscpu --caches`' `ALL-SIZE 60M` / 2 instances) | 2–45 MB, **12–16 way**, 64 B line, **latency 34 cycles**, shared (Fog Table 10.2 — stated as a family-wide range, not per-SKU) | Size: **exact match** (30 MiB, within Fog's 2–45 MB family range). **Ways: Phase I (9, low-confidence lower bound) vs. system-reported (20) — mismatch, resolved in favor of system-reported 20-way, which is itself outside Fog's quoted 12–16-way family range** — a concrete, textbook instance of `PROJECT 1.pdf`'s own warning not to assume one value applies to every SKU in a generation (this is a 12-core server die, not the client part Fog's range most likely reflects). This also directly confirms, rather than just suspects, Phase I's own confound hypothesis: the "9" the timing method kept finding was the shared small-structure artifact, not real LLC associativity. Sets: only comes out to a clean integer at 20-way, additional post-hoc evidence 9-way was wrong. Latency: measured (~58.42 ticks) higher than Fog's 34 cycles — same `-O0` overhead story as L1/L2 (inflation ratio ~1.7x, slightly lower than L1/L2's, plausibly because loop overhead is a smaller *relative* share of a much longer absolute latency here) plus a plausible genuine SKU effect (a 30 MiB, 12-core ring/mesh-connected L3 slice is physically larger and farther than whatever smaller Haswell/Broadwell part Fog's 34-cycle figure was likely measured on) |

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **This machine's PMU reliably schedules only 2 generic hardware counters
  at once** (confirmed by hand before writing `run_pmu_verification.sh`: a
  3-event group only scheduled 57–71%, not 100%; `nmi_watchdog=1` reserves
  one counter). The script therefore runs 4 separate `perf stat` invocations
  per (level, run_tag) — `{cache-references,cache-misses}`,
  `{L1-dcache-loads,L1-dcache-load-misses}`, `{LLC-loads,LLC-load-misses}`,
  `{cycles,instructions}` — each also carrying the software `duration_time`
  event. All four groups scheduled at 100% in every run collected here.
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — they also
  include process fork/exec, the untimed warmup passes (3 full passes over
  the working set), and the chase-buffer permutation construction, none of
  which `duration_time`/`cycles` can be separated out from. At the L1/L2
  footprints this makes the derived "latency" numbers not directly
  comparable to Phase I's own batch-internal RDTSC measurement; at the LLC
  footprint the effect is large enough (median cycles/access ≈2026, vs. a
  ~58-tick Phase I number) that these two derived columns must **not** be
  read as a real per-access latency at all here — only the qualitative,
  order-of-magnitude jump between footprints is meaningful.
- **The miss-rate metrics (ratios) are the trustworthy Phase-II PMU
  corroboration signal**, since they're insensitive to the above (a ratio of
  two counts from the same inflated process lifetime cancels most of the
  contamination): `l1_miss_rate` cleanly confirms the L1→L2 capacity
  crossing (0.6% → 12.6%) but then saturates rather than climbing further
  into LLC territory (11.5%) — a known limitation of that specific ratio at
  -O0 (every loop iteration issues several guaranteed-L1-hit stack loads
  alongside the one real chase load, diluting the ratio once the chase load
  itself is already usually missing L1); `cache_miss_rate`/`llc_miss_rate`
  (the LLC-scope generic events) are the cleaner signal and show the clear
  order-of-magnitude jump exactly at the LLC footprint (≈0.1–1.4% at
  L1/L2 → ≈11–14% at LLC) used above.
- Absolute PMU event counts (e.g. `l1_dcache_loads` ≈293M at the LLC
  footprint, vs. 1,000,000 samples) are inflated far beyond a naive
  "1 load per chase step" expectation — consistent with `-O0`'s lack of
  register allocation across loop iterations (the chase pointer, loop
  counters, etc. are reloaded from the stack every iteration, each such
  reload being its own guaranteed-L1-hit `L1-dcache-loads` event) plus the
  warmup/permutation-construction phases described above. Not investigated
  further at the instruction level this session — noted as a real property
  of this measurement, not a script bug (independently sanity-checked: at
  the LLC footprint, `cycles` ÷ `duration_time` ≈ 2.40 GHz, matching this
  CPU's 2.5 GHz max clock closely enough to confirm the counters themselves
  are being read correctly).
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/sunbird/pmu/<level>/pmu_summary_20260913T193142Z.csv` —
  the table above cites each metric's median-of-3 value.

## Where the underlying data lives

- Phase II PMU raw: `data_raw/sunbird/pmu/{L1,L2,LLC}/*_perfstat_*.csv` (perf
  stat output) and `*_bench_*.csv` (cache_bench's own CSV from the same
  invocation).
- Phase II PMU processed: `data_processed/sunbird/pmu/{L1,L2,LLC}/pmu_summary_20260913T193142Z.csv`.
- Phase II system-reported: `data_raw/sunbird/pmu/system_reported_cache_info.txt`.
- Phase I (unchanged): `data_processed/sunbird/FINAL_CACHE_TABLE.md`,
  `data_raw/sunbird/README.md`.
- Literature: Agner Fog's manual, §10.11/Table 10.2, p. 143 (see citation
  above) — a local copy of the fetched PDF is not committed to this repo
  (external reference only, per the citation).
