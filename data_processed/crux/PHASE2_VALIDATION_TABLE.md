# Phase II Validation Table — Crux (2026-09-14)

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
   `data_processed/crux/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh crux 1
   L1:32768,L2:262144,LLC:8388608`, core 1 — cores 0 and 2 were pinned by
   other students' jobs (`incl_pmu`, `cache_bench_x86`) at the time, confirmed
   fully busy via two independent `/proc/stat` idle-time-delta samples 4s
   apart; core 1 confirmed fully idle in both samples — base_seed=12345 + 2
   repeats, 1,000,000 samples/run, timestamp `20260914T003352Z`). Raw:
   `data_raw/crux/pmu/<level>/`. Summaries:
   `data_processed/crux/pmu/<level>/pmu_summary_20260914T003352Z.csv`.
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/cpu0/cache/index*/*`, saved verbatim in
   `data_raw/crux/pmu/system_reported_cache_info.txt` (collected
   2026-09-14T00:34:16Z).
4. **Reference (literature)** — Agner Fog, *The microarchitecture of Intel,
   AMD and VIA CPUs*, last updated 2026-05-23, §11.12 "Cache and memory
   access", Table 11.2 "Cache sizes on Skylake", p. 160 (canonical:
   `www.agner.org/optimize/microarchitecture.pdf`, fetched directly this
   session). Crux is an Intel Core i7-9700 (Coffee Lake) — Fog's manual
   groups Skylake/Kaby Lake/Coffee Lake as one client-core family for cache
   purposes (§11.15 is explicitly titled "Bottlenecks in Skylake, Kaby Lake,
   Cannon Lake, and Coffee Lake"; §11.12's own text notes "Different
   processors with Lake names are quite similar, but the sizes of level 2
   and 3 caches differ between different versions and models"), so Table
   11.2's Skylake-family ranges are the right reference row for this CPU —
   same grouping `CLAUDE.md`'s Phase II section already assigns to
   Crux/Ookay/Upgrade.

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **32,768 B (32 KiB)** — Phase I confirmed; Phase II system-reported (`lscpu --caches`, sysfs `index0`) identical: 32K | **8-way** — Phase I confirmed (clean knee, 0% repeat spread); Phase II system-reported: 8-way | **64** — Phase I derived (S=C/(A·B)); Phase II system-reported: 64 sets | **64 B** — Phase I confirmed (5 independent line_size runs); Phase II system-reported: 64 B | Phase I: ≈7.42 ticks/access. Phase II/PMU (same footprint, this run): median `bench_avg_ticks_per_access` ≈5.776, median cycles/access ≈13.19, ns/access (wall-clock) ≈3.40 — **see PMU caveat below, not a clean single-access number**. Miss-rate corroboration: L1 miss rate 1.07% (median) — consistent with a fully L1-resident working set | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=0`** — this CPU has no SMT (`Thread(s) per core: 1`), so "private per core" here also means private per logical CPU; confirms the guess | 32 kB, 8-way, 64 sets, 64 B line, **latency 4 cycles**, per core (Fog Table 11.2, "Level 1 data" row) | Size/ways/sets/line/sharing: **exact match, all 3 sources.** Latency: measured (~7.42 ticks Phase I / ~5.78 ticks this PMU run's own bench median) reads **higher** than Fog's 4 cycles — attributed to `-O0` dependent-chase loop overhead (stack spill/reload of the chase pointer sits in the true dependency chain; see Makefile's `-O0 -g` rationale), same explanation Sunbird's table used, not a contradiction |
| L2 | **262,144 B (256 KiB)** — Phase I ("hand-verified, take as given" per `CAPACITY_RESULTS.md`); Phase II system-reported: 256K identical | Phase I *best guess*: **8-way** (raw detector said 4-way with full 3/3 reproducibility, but Phase I's own `FINAL_CACHE_TABLE.md` set that aside as the cross-machine DTLB-scale confound and reasoned to 8 by anchoring to L1 plus an S=C/(A·B) clean-integer argument — see that file's "Associativity reasoning" section). **Phase II system-reported: 4-way — matches the raw/confound-flagged value, NOT Phase I's reasoned best guess. See Agreement.** | Phase I (at 8-way guess): 512. **Phase II system-reported (at real 4-way): 1024 sets** | **64 B** — Phase I confirmed (5 independent runs); Phase II system-reported: 64 B | Phase I: ≈14.30 ticks/access. Phase II/PMU: median `bench_avg_ticks_per_access` ≈14.92, median cycles/access ≈33.85, ns/access (wall-clock) ≈7.59 — same overhead caveat as L1. Miss-rate corroboration: L1-scope miss rate jumps to 12.1% (footprint now exceeds L1) while LLC-scope miss rate stays low (0.6-0.9%) — the signature of a footprint sized to fit L2/LLC but not L1 | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=0`** — private per logical CPU, same as L1 | 256 kB-1 MB, **4-16 ways**, 1024 sets, 64 B line, **latency 14 cycles**, per core (Fog Table 11.2, "Level 2" row) | Size/sets(at true ways)/line/sharing: **exact match, all 3 sources** (1024 sets at the system-reported 4-way exactly matches Fog's stated 1024-sets figure too). **Associativity: Phase I's reasoned override was wrong.** The raw, confound-flagged "4-way" reading Phase I explicitly set aside turns out to be the real answer — confirmed by both direct hardware self-report and by sitting exactly at the low end of Fog's quoted 4-16-way family range. Phase I's own stated reasons for preferring 8 (anchoring to L1, and a clean S=C/(A·B) integer check) were sound *arguments*, but this is a concrete case where the cross-machine confound heuristic overrode a correct raw measurement rather than correcting a confounded one — worth flagging plainly rather than smoothing over, per this table's own stated policy. Latency: measured (~14.30 ticks Phase I / ~14.92 this run) is **almost an exact match** to Fog's 12 kB... 14-cycle figure (ratio ~1.03-1.07x) — notably tighter than L1's own inflation ratio, though the underlying `-O0` loop-overhead mechanism should if anything affect L1/L2 similarly; not further explained this session |
| LLC | **~8 MiB (8,388,608 B)** — Phase I, from `CAPACITY_RESULTS.md` (rounded representative of a noisy, not-fully-resolved ~4-64 MiB transition; Phase I's own `FINAL_CACHE_TABLE.md` already flagged `lscpu`'s reported 12 MiB real L3 as a known, unresolved conflict). **Phase II system-reported: 12,582,912 B (12 MiB) exactly — confirms the conflict was real: Crux's actual LLC is 50% larger than the `CAPACITY_RESULTS.md` value used to pick this run's own footprint.** See Agreement | Phase I *best guess*: **8-way** (raw detector said 4-way, 3/3 reproducible — same confound signature as L2's, see `FINAL_CACHE_TABLE.md`). **Phase II system-reported: 12-way — matches neither Phase I's raw confound value (4) nor its reasoned best guess (8).** | Phase I (at 8-way guess, ~8 MiB): 16,384 (by design — Phase I picked 8-way partly *because* it made this come out to a clean integer). **Phase II system-reported (at real 12 MiB / 12-way): 16,384 — the exact same derived-set count, by coincidence of the two different (size, ways) pairs both dividing out to 16,384** | **64 B** — Phase I confirmed (tightest result on this machine); Phase II system-reported: 64 B | Phase I: ≈43.23 ticks/access. Phase II/PMU (at the 8 MiB footprint, which sits inside the real 12 MiB LLC, not at its edge): median `bench_avg_ticks_per_access` ≈59.32, median cycles/access ≈543.3, ns/access (wall-clock) ≈124.0 — **NOT usable as an absolute latency number, same reasoning as Sunbird's table** (whole-process-lifetime dilution from warmup passes/permutation construction dominates at this footprint scale — see caveats below). Miss-rate corroboration: LLC-scope miss rate jumps from 0.6-0.9% at the L2 footprint to 11.6% (median) at this footprint — an order-of-magnitude jump, though this is evidence of crossing the **L2** capacity boundary into LLC-resident territory (8 MiB fits inside the real 12 MiB LLC), not evidence of hitting the LLC's own capacity edge | Phase I: shared across cores/socket (architectural guess). **Phase II system-reported: `shared_cpu_list=0-7`** — all 8 physical cores (no SMT, no NUMA node splits — `Socket(s): 1`) share one LLC. Confirms + fully resolves the guess (simpler than Sunbird's own 2-socket case: here it's the whole machine, not one of several sockets) | 3-24 MB, 64 B line, **latency 34-85 cycles**, shared (Fog Table 11.2, "Level 3" row — no way-count given in this table at all for L3) | Size: **Phase I's rounded ~8 MiB estimate was measurably wrong; the real value (12 MiB) is now settled by system-report**, and comfortably inside Fog's 3-24 MB family range either way. **Ways: three-way disagreement, resolved in favor of system-reported 12-way** — Fog's table doesn't publish an L3 way-count for Skylake-family at all, so literature can't arbitrate this cell, but system-report is authoritative regardless. Sets: the two derived-set numbers coincidentally match (16,384) despite neither being computed from the true (size, ways) pair — flagged as a coincidence, not read as corroborating either wrong guess. Latency: measured (~43.23 ticks Phase I / ~59.32 this run) falls **inside** Fog's quoted 34-85 cycle range both times — the LLC row is the one place this machine's `-O0` inflation doesn't obviously exceed the literature range, plausibly because Fog's own range is wide enough to swallow it |

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **Unlike Sunbird, this machine's PMU reliably scheduled ALL 7 hardware
  events (`cache-references`, `cache-misses`, `L1-dcache-loads`,
  `L1-dcache-load-misses`, `LLC-loads`, `LLC-load-misses`, `cycles`,
  `instructions`) plus the software `duration_time` event simultaneously at
  100%**, confirmed by hand with a combined single-invocation test at the
  L1 footprint before running the pipeline (3 repeats, all 8 events showed
  `pct_running=100.00` every time; `nmi_watchdog=1` here too, same as
  Sunbird, but apparently doesn't force multiplexing on this CPU the way it
  did there). `run_pmu_verification.sh` still runs its fixed 4-separate-
  2-event-group design regardless (the settled cross-machine convention,
  not re-derived per machine) — this just means Crux's split into 4 groups
  was more conservative than strictly necessary, not that anything failed.
  No `<not counted>` entries appear anywhere in this machine's summaries
  (see the `notes` column of all three `pmu_summary_20260914T003352Z.csv`
  files — empty in every row).
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — same caveat as
  Sunbird's table: they also include process fork/exec, the 3 untimed
  warmup passes, and permutation construction, none of which
  `duration_time`/`cycles` separate out. At the LLC footprint this inflates
  `cycles_per_access` to ≈543 (vs. a ~59-tick bench-timer number) — **not a
  real per-access latency**, only the qualitative jump between footprints
  is meaningful from this column.
- **Sanity check that the counters themselves are being read correctly**
  (same check Sunbird's table ran): `cycles ÷ duration_time` implies
  ≈3.88 GHz at the L1 footprint, ≈4.46 GHz at L2, ≈4.38 GHz at LLC — all
  within this CPU's rated 3.0 GHz base / 4.7 GHz max-turbo range, confirming
  the hardware counters are being sampled correctly and aren't an artifact
  of measurement error.
- **The LLC-scope miss-rate ratio (`llc_miss_rate`) is the cleanest
  Phase-II corroboration signal on this machine**, same conclusion Sunbird's
  table reached: it cleanly separates L2-footprint (0.6-0.9%) from
  LLC-footprint (10.5-15%). The generic `cache_miss_rate` (from
  `cache-references`/`cache-misses`) shows the same L2→LLC jump (2.4-3.5% →
  10.9-14.8%) but **also carries an unexplained anomaly at the L1
  footprint** (12.6% median, higher than L2's own 2.4-3.5%, and much higher
  than Sunbird's equivalent L1-footprint value of <1.4%) — not traced to a
  specific cause this session; flagged as an open oddity rather than
  smoothed over. `l1_miss_rate` shows the same saturating-rather-than-
  climbing behavior at the LLC footprint (12.1% at L2 → 8.8% at LLC, i.e.
  going *down*) that Sunbird's table documented and attributed to guaranteed
  L1-hit stack loads at `-O0` diluting the ratio once the real chase load
  is already usually missing L1 — the same explanation applies here without
  further investigation.
- Absolute PMU event counts (e.g. `l1_dcache_loads` ≈88.7M at the LLC
  footprint, vs. 1,000,000 samples) are inflated far beyond a naive
  "1 load per chase step" expectation, for the same `-O0`/warmup/
  permutation-construction reasons Sunbird's table documented — not
  investigated further at the instruction level here either.
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/crux/pmu/<level>/pmu_summary_20260914T003352Z.csv` — the
  table above cites each metric's median-of-3 value.

## Where the underlying data lives

- Phase II PMU raw: `data_raw/crux/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz`
  (perf stat output) and `*_bench_*.csv.gz` (cache_bench's own CSV from the
  same invocation).
- Phase II PMU processed: `data_processed/crux/pmu/{L1,L2,LLC}/pmu_summary_20260914T003352Z.csv`.
- Phase II system-reported: `data_raw/crux/pmu/system_reported_cache_info.txt`.
- Phase I (unchanged): `data_processed/crux/FINAL_CACHE_TABLE.md`,
  `data_raw/crux/README.md`.
- Literature: Agner Fog's manual, §11.12/Table 11.2, p. 160 (see citation
  above) — a local copy of the fetched PDF is not committed to this repo
  (external reference only, per the citation).
