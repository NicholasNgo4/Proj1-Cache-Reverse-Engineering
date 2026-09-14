# Phase II Validation Table — Upgrade (2026-09-14)

Per `PROJECT 1.pdf`'s Table 2 requirement: a compact post-Phase-I validation
table with measured size/ways/sets/line/latency/sharing-scope columns kept
**separate** from the cited reference/literature value and the Agreement
verdict. This file only exists because Phase I is frozen and tagged
(`phase1-timing-only`, per `README.md`'s Phase Discipline) — nothing here
touches or overwrites `FINAL_CACHE_TABLE.md`, which remains the frozen,
timing-only Phase-I record. Uses `scripts/run_pmu_verification.sh` (the
settled convention per `CLAUDE.md`'s cross-session divergence note), same
format as Sunbird's/Thunderbird's tables.

**Three independent sources feed this table, kept distinguishable in every
cell:**
1. **Phase I (timing-only)** — carried over read-only from
   `data_processed/upgrade/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh upgrade 5
   L1:32768,L2:262144,LLC:12582912`, core 5, base_seed=12345 + 2 repeats,
   1,000,000 samples/run, timestamp `20260914T003134Z`). Footprint bytes
   are the same hand-confirmed values Upgrade's own Phase-I `hit_latency`
   run used (`CAPACITY_RESULTS.md`'s L1/L2 values plus the exact 12 MiB
   LLC candidate, not a rounded power of two — `--cache-bytes`'s
   power-of-two requirement was relaxed for the associativity experiment
   only, and `hit_latency`/this PMU pipeline never had that restriction).
   Raw: `data_raw/upgrade/pmu/<level>/`. Summaries:
   `data_processed/upgrade/pmu/<level>/pmu_summary_20260914T003134Z.csv`.
   All 4 perf event groups scheduled at 100% in every run collected here —
   no `<not counted>`/`<not supported>` events, unlike Thunderbird's ARM
   run (see below).
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/cpu0/cache/index*/*`, saved verbatim in
   `data_raw/upgrade/pmu/sysfs_cache_topology_20260913.txt` (collected
   2026-09-14, filename dated the day the session started).
4. **Reference (literature)** — Agner Fog, *The microarchitecture of Intel,
   AMD and VIA CPUs*, last updated 2026-05-23, §11.12 "Cache and memory
   access", Table 11.2 "Cache sizes on Skylake", p. 160 (canonical:
   `www.agner.org/optimize/microarchitecture.pdf`). Upgrade is a Core
   i7-8700 (Coffee Lake) — §11 states explicitly that Kaby Lake, Cannon
   Lake, and Coffee Lake "are based on the same design" as Skylake and
   differ mainly in process node, core count, and cache size, so this
   table is the correct family-level reference (also see §11.15
   "Bottlenecks in Skylake, Kaby Lake, Cannon Lake, and Coffee Lake",
   p. 161, which names Coffee Lake explicitly). **Table 11.2 gives L1/L2 as
   exact per-core numbers but L3 only as a family-wide range (3–24 MB,
   64 B line, latency 34–85 cycles, shared) with no associativity figure
   at all** — weaker than the Haswell/Broadwell table Sunbird's session
   used (which did give a 12–16-way L3 range). To resolve L3 ways for this
   specific SKU, supplemented with **uops.info's per-microarchitecture
   cache table** (`https://uops.info/cache.html`), which lists Coffee Lake
   (Core i7-8700K — same 6-core Coffee Lake die as Upgrade's i7-8700, only
   differing in default clock/multiplier) as L1D 32 kB/8-way/4 cycles, L2
   256 kB/4-way/12 cycles, L3 12 MB/16-way/41 cycles — a second,
   independent literature source, not just a fallback guess.

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **32,768 B (32 KiB)** — Phase I confirmed; Phase II system-reported (`lscpu --caches`, sysfs `index0`) identical: 32K | **8-way** — Phase I confirmed (clean knee); Phase II system-reported: 8-way | **64** — Phase I derived (S=C/(A·B)); Phase II system-reported: 64 sets | **64 B** — Phase I confirmed; Phase II system-reported: 64 B | Phase I: ≈6.17 ticks/access. Phase II/PMU (same footprint, this run): median `bench_avg_ticks_per_access` ≈6.43 (+4% vs. Phase I, within normal run-to-run noise), median cycles/access ≈13.78, ns/access (wall-clock) ≈3.76 — see PMU caveats below, not a clean single-access number. Miss-rate corroboration: `l1_miss_rate` 1.13% (median) — low, consistent with a working set sized almost exactly at L1 capacity (some conflict-miss residue expected right at the boundary, not a clean 0%) | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=0,6`** — private to one physical core's own 2 SMT threads only (confirms + sharpens the guess) | 32 kB, 8-way, 64 sets, 64 B line, **latency 4 cycles**, per core (Fog Table 11.2, p.160); uops.info independently agrees: 32 kB/8-way/4 cycles | Size/ways/sets/line/sharing: **exact match, all 3 sources, both literature sources.** Latency: measured (~6.17 ticks / ~13.8 cycles) reads **higher** than the literature's 4 cycles — same `-O0` dependent-chase loop-overhead explanation Sunbird's/Thunderbird's writeups already used (stack spill/reload of the chase pointer sits in the true dependency chain at `-O0`), not a contradiction |
| L2 | **262,144 B (256 KiB)** — Phase I (`CAPACITY_RESULTS.md`, hand-verified); Phase II system-reported: 256K identical | **Best guess: 8-way (Phase I, confound-blocked)** — Phase I's own writeup already flagged this as the least-independent of its associativity guesses. **Phase II system-reported: 4-way — a real disagreement, resolved in favor of system-reported (see Agreement)** | Phase I (at 8-way, now superseded): 512. **Phase II system-reported (at 4-way): 1,024 sets** | **64 B** — Phase I best-available estimate; Phase II system-reported: 64 B | Phase I: ≈16.12 ticks/access. Phase II/PMU: median `bench_avg_ticks_per_access` ≈15.84 (−1.7% vs. Phase I, closest agreement of the three levels), median cycles/access ≈33.28, ns/access ≈8.01. Miss-rate corroboration: `l1_miss_rate` jumps to 12.07% (footprint now exceeds L1) while `llc_miss_rate` stays tiny (0.95%) — almost everything that misses L1 is caught by L2, the same signature Sunbird's own L2 row used to corroborate a footprint sized to fit L2 | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=0,6`** — private per physical core, same as L1 | 256 kB, **4-way**, 1,024 sets, 64 B line, **latency 12 cycles**, per core (Fog Table 11.2 — states L2 ranges "4–16 ways" across the Skylake/Kaby Lake/Coffee Lake family, with 1,024 sets fixed regardless of size/ways, so 256 KiB at 4-way sitting at the low end of that range is expected, not a family-range mismatch); uops.info agrees exactly: 256 kB/4-way/12 cycles | Size/sets/line/sharing: **exact match, all 3 sources.** **Ways: Phase I (8, confound-blocked best guess) vs. system-reported AND both literature sources (4) — mismatch, resolved in favor of the 3-way-converging value, 4-way.** This directly confirms Phase I's own confound hypothesis for this machine (the "8" the associativity method kept finding at L2/LLC-scale strides was the shared small-structure artifact, not real L2 associativity) rather than contradicting it — same resolution pattern as Sunbird's LLC row. Latency: measured (~16.12 ticks / ~33.3 cycles) higher than literature's 12 cycles, same `-O0` overhead story as L1 (inflation ratio ~2.6-2.8x, consistent with L1's own ~3.3-3.5x) |
| LLC | **12,582,912 B (12 MiB)** — Phase I, from `CAPACITY_RESULTS.md` (this machine's own capacity sweep never independently resolved a clean LLC edge — see caveat below). **Phase II system-reported: 12,288K = 12,582,912 B exactly** — an exact byte-for-byte match to the Phase-I candidate used | Phase I: **best guess 8-way**, explicitly presented by `FINAL_CACHE_TABLE.md` as a confound-limited "effective point estimate," the least independent of Upgrade's associativity results. **Phase II system-reported: 16-way — a real disagreement, resolved in favor of the system-reported value** (see Agreement) | Phase I (at 8-way, superseded): 24,576. **Phase II system-reported (at 16-way): 12,288 sets** (exact integer, S=12,582,912/(16·64)) | **64 B** — Phase I best-available estimate; Phase II system-reported: 64 B | Phase I: ≈155.05 ticks/access. Phase II/PMU: median `bench_avg_ticks_per_access` ≈121.47 (**−21.6% vs. Phase I** — the largest gap of the three levels, see caveat below), median cycles/access ≈1183.05, ns/access ≈297.00 — **not usable as an absolute latency number** (same whole-process-lifetime contamination Sunbird's LLC row already documented: warmup passes + permutation construction dominate total time at this footprint scale). Miss-rate corroboration is the reliable signal here: `llc_miss_rate` jumps to 35.6% (median) and generic `cache_miss_rate` to 39.7% (median) — both were ≤2.7% at the L1/L2 footprints, a clean order-of-magnitude jump right at the footprint Phase I placed the LLC candidate, independently corroborating it. **Notably high run-to-run spread in the miss-rate metrics themselves** (base/rep1/rep2 `llc_miss_rate`: 35.6% / 57.8% / 32.7%; `cache_miss_rate`: 53.9% / 33.0% / 39.7%) — this directly corroborates, rather than contradicts, Phase I's own finding for this machine: `CAPACITY_RESULTS.md`'s own bullet already flags Upgrade's ~5–22 MiB region as "a noisy transition... needing a dedicated dense sweep to resolve," and this run's own core-5 idle-core check found cores 0 and 2 pinned at 100% by another student's job (`incl_pmu`/`cache_bench_x86`) for the whole session — plausible shared-LLC interference from a *different* core on the same socket, since the L3 is shared across all 12 logical CPUs on this single-socket part (see Sharing scope column) | Phase I: shared across cores/socket (architectural guess). **Phase II system-reported: `shared_cpu_list=0-11`** — all 12 logical CPUs (6 cores × 2 SMT threads), i.e. the entire chip, confirming + sharpening the guess. (Unlike Sunbird's 2-socket Xeon, Upgrade is a single-socket desktop part, so there is only one LLC instance total, not one per socket — `lscpu --caches`' `ONE-SIZE`/`ALL-SIZE` are identical, 12M, confirming this) | 3–24 MB, 64 B line, **latency 34–85 cycles**, shared (Fog Table 11.2 — states a family-wide range with **no associativity figure at all** for L3, unlike the Haswell/Broadwell table Sunbird's session used). **Supplementary source (uops.info, Coffee Lake i7-8700K): 12 MB, 16-way, latency 41 cycles** — same die as Upgrade's i7-8700, differing only in stock clock/multiplier | Size: **exact match** (12 MiB, within Fog's 3–24 MB family range; uops.info's 12 MB figure for the sibling i7-8700K SKU matches exactly). **Ways: Phase I (8, confound-limited best guess) vs. system-reported AND uops.info (both 16) — mismatch, resolved in favor of the 2-way-converging value, 16-way** — Fog's own family table has no L3-ways figure to arbitrate with, so uops.info is the deciding literature vote here, not a fallback of last resort. This is the same textbook confirmation of Phase I's confound hypothesis as Sunbird's/Thunderbird's LLC rows: the "8" this machine's associativity method kept reporting at large strides was the shared small-structure (DTLB-scale) artifact, not real LLC associativity. Sets: unlike Sunbird's LLC row, the set-count cross-check is **not** a useful disambiguator here — both 8-way (Phase I's guess, S=24,576) and 16-way (system/literature, S=12,288) come out to clean integers at this machine's power-of-two-adjacent 12 MiB candidate, so this ways disagreement is resolved purely by the 2-source system-reported/uops.info convergence against Phase I's own confound caveat (see the note below), not by set-count cleanliness. Latency: measured (~155.05 ticks) higher than literature's 34–85 cycle range/uops.info's 41 cycles — same `-O0` overhead story as L1/L2, though the gap is smaller in relative terms here (inflation ratio ~1.8-2.0x vs. literature's midpoint) since loop overhead is a smaller *relative* share of a much longer absolute latency |

**Note on the LLC "Sets" cleanliness claim above:** unlike Sunbird's ~30 MiB
*rounded* LLC estimate (where only one of the two candidate ways gave a
clean integer set count), Upgrade's 12,582,912 B candidate is already
`24,576 x 512` = a multiple of many small factors, so **both** 8-way
(S=24,576) and 16-way (S=12,288) come out to clean integers — the
set-count cross-check that helped disambiguate Sunbird's LLC row is not
useful here, and the ways disagreement is resolved purely by the
system-reported + uops.info convergence against Phase I's own confound
caveat, not by an S=C/(A×B) integer test.

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **This run never hit the 2-generic-counter scheduling limit Sunbird's
  session found on its own machine** — all 4 perf event groups
  (`cache-references,cache-misses` / `L1-dcache-loads,L1-dcache-load-misses`
  / `LLC-loads,LLC-load-misses` / `cycles,instructions`, each alongside the
  software `duration_time` event) scheduled at 100% in every one of the 9
  runs (3 levels × 3 run_tags) collected here — verified by grepping every
  raw `*_perfstat_*.csv.gz` for `<not counted>`/`<not supported>`, no hits.
  A real, machine-specific difference from Sunbird's own PMU, not assumed.
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — same caveat as
  Sunbird's/Thunderbird's tables: they also include process fork/exec, the
  3 untimed warmup passes, and chase-buffer permutation construction, none
  of which `duration_time`/`cycles` can be separated out from. At the
  L1/L2 footprints this makes the derived numbers not directly comparable
  to Phase I's own batch-internal RDTSC measurement; at the LLC footprint
  the effect is large enough (median cycles/access ≈1,183 vs. a ~155-tick
  Phase I number) that these two derived columns must **not** be read as a
  real per-access latency at all — only the qualitative, order-of-magnitude
  jump between footprints, and the miss-rate ratios, are meaningful there.
- **A sanity cross-check (cycles ÷ duration_time) gives ≈3.66 GHz at L1 and
  ≈3.98 GHz at LLC** — both plausible for this CPU's 3.2 GHz base / 4.6 GHz
  max-turbo range, confirming the counters are being read correctly (same
  check Sunbird's writeup used).
- **This machine had confirmed contention on 2 of its other 11 logical
  CPUs during the run** (see the LLC row's spread discussion above) —
  core 5 (the pinned `taskset` core, verified idle via 3 independent
  `/proc/stat` sampling windows before the run, per this project's
  established idle-core-check discipline) itself stayed idle throughout,
  but cores 0 and 2 were pinned at 100% by another student's `incl_pmu`/
  `cache_bench_x86` processes the whole session, and this machine's LLC is
  shared across the entire chip (`shared_cpu_list=0-11`) — plausible
  explanation for the LLC-footprint miss-rate spread and for the ~22%
  Phase-I-vs-PMU latency gap at that level specifically (L1/L2, both
  private per-core, showed no comparable gap: +4% and −1.7%
  respectively).
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/upgrade/pmu/<level>/pmu_summary_20260914T003134Z.csv` —
  the table above cites each metric's median-of-3 value.

## Where the underlying data lives

- Phase II PMU raw: `data_raw/upgrade/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz`
  (perf stat output) and `*_bench_*.csv.gz` (cache_bench's own CSV from the
  same invocation).
- Phase II PMU processed: `data_processed/upgrade/pmu/{L1,L2,LLC}/pmu_summary_20260914T003134Z.csv`.
- Phase II system-reported: `data_raw/upgrade/pmu/sysfs_cache_topology_20260913.txt`.
- Phase I (unchanged): `data_processed/upgrade/FINAL_CACHE_TABLE.md`,
  `data_raw/upgrade/README.md`.
- Literature: Agner Fog's manual, §11.12/Table 11.2, p. 160 (see citation
  above); uops.info's Coffee Lake cache table
  (`https://uops.info/cache.html`) — neither is committed to this repo
  (external references only, per the citations above).
