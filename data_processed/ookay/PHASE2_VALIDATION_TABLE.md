# Phase II Validation Table — Ookay (2026-09-14)

Per `PROJECT 1.pdf`'s Table 2 requirement: a compact post-Phase-I validation
table with measured size/ways/sets/line/latency/sharing-scope columns kept
**separate** from the cited reference/literature value and the Agreement
verdict. This file only exists because Phase I is now frozen and tagged
(`phase1-timing-only`, per `README.md`'s Phase Discipline) — nothing here
touches or overwrites `FINAL_CACHE_TABLE.md`, which remains the frozen,
timing-only Phase-I record. Built with `scripts/run_pmu_verification.sh` +
`scripts/summarize_pmu.py`, the same pipeline used for Sunbird and
Thunderbird (see `CLAUDE.md`'s Phase II subsection) — no script changes were
needed for this machine.

**Four independent sources feed this table, kept distinguishable in every
cell:**
1. **Phase I (timing-only)** — carried over read-only from
   `data_processed/ookay/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh ookay 3
   L1:32768,L2:262144,LLC:8388608`, core 3, base_seed=12345 + 2 repeats
   (seeds 12346/12347), 1,000,000 samples/run, timestamp
   `20260914T003308Z`). Raw: `data_raw/ookay/pmu/<level>/`. Summaries:
   `data_processed/ookay/pmu/<level>/pmu_summary_20260914T003308Z.csv`.
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/cpu0/cache/index*/*`, saved verbatim in
   `data_raw/ookay/pmu/system_reported_cache_info.txt` (collected
   2026-09-14T00:33:33Z).
4. **Reference (literature)** — Agner Fog, *The microarchitecture of Intel,
   AMD and VIA CPUs*, last updated 2015-12-23, §11.12 "Cache and memory
   access", Table 11.2 "Cache sizes on Skylake", p. 160 (canonical:
   `www.agner.org/optimize/microarchitecture.pdf`). Fog's own text groups
   Skylake/Kaby Lake/Coffee Lake as "quite similar" in cache architecture,
   differing mainly in L2/L3 capacity by SKU — Ookay is a Core i7-7700
   (Kaby Lake), covered by this table per `CLAUDE.md`'s Phase II literature
   plan (grouped with Crux/Upgrade as "Skylake-family").

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **32,768 B (32 KiB)** — Phase I confirmed; Phase II system-reported (`lscpu --caches`, sysfs `index0`) identical: 32K | **8-way** — Phase I confirmed (clean knee); Phase II system-reported: 8-way | **64** — Phase I derived (S=C/(A·B)); Phase II system-reported: 64 sets | **64 B** — Phase I confirmed; Phase II system-reported: 64 B | Phase I: ≈7.49 ticks/access. Phase II/PMU (same footprint, this run): bench median ≈7.618 ticks/access (closely reproduces Phase I), median cycles/access ≈13.73, ns/access (wall-clock) ≈3.79 — **see caveat below, not a clean single-access number**. Miss-rate corroboration: L1-dcache miss rate 0.97% (median) — consistent with a fully L1-resident working set | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=0,4`** — private to one physical core's own 2 SMT threads only (confirms + sharpens the guess) | 32 kB, 8-way, 64 sets, 64 B line, **latency 4 cycles**, per core (Fog Table 11.2) | Size/ways/sets/line/sharing: **exact match, all 3 sources.** Latency: measured (~13.73 cycles/access) reads **higher** than Fog's 4 cycles (ratio ≈3.43x) — attributed to `-O0` dependent-chase loop overhead (stack spill/reload of the chase pointer sits in the true dependency chain every iteration), same explanation already used for Sunbird's table, and notably the **same ratio order** as Sunbird's own L1 inflation (≈3.40x) despite a different CPU generation |
| L2 | **262,144 B (256 KiB)** — Phase I ("hand-verified, take as given" per `CAPACITY_RESULTS.md`); Phase II system-reported: 256K identical | Phase I: **best guess 8-way** (blocked by the documented DTLB-scale confound — see `data_raw/ookay/README.md`'s associativity/ section). **Phase II system-reported: 4-way — a real disagreement, resolved in favor of the system-reported value** (see Agreement) | Phase I (at its own 8-way guess): 512 (internally consistent but built on the wrong ways value). **Phase II system-reported (at the correct 4-way): 1,024 sets** — S=C/(A·B) = 262,144/(4×64) | **64 B** — Phase I weak/uncontradicted evidence only; Phase II system-reported: 64 B | Phase I: ≈18.53 ticks/access. Phase II/PMU: bench median ≈19.192 ticks/access (closely reproduces Phase I, +3.6%), median cycles/access ≈33.68, ns/access (wall-clock) ≈7.94 — same overhead caveat as L1. Miss-rate corroboration: L1-dcache miss rate jumps to 12.14% (footprint now exceeds L1) while LLC-scope-specific miss rate stays low (1.38%) — i.e. almost everything that misses L1 is caught by L2, the expected signature of a footprint sized to fit L2 | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=0,4`** — private per physical core, same as L1 | 256 kB – 1 MB, **4–16 ways**, 1024 sets, 64 B line, **latency 14 cycles**, per core (Fog Table 11.2 — stated as a family-wide range, not per-SKU) | Size/sets/line/sharing: **exact match, all 3 sources** (1,024 sets only resolves once the associativity disagreement below is settled). **Ways: Phase I confound-blocked guess (8) vs. system-reported (4) — a real disagreement, resolved in favor of system-reported 4-way, which sits at the low end of Fog's own quoted 4–16-way family range** — this directly confirms Phase I's own associativity investigation's confound hypothesis: the "8" the timing method kept finding at this level was the shared small-structure artifact (matching L1's own value), not L2's real associativity. Latency: measured (~33.68 cycles/access) higher than Fog's 14 cycles (ratio ≈2.41x), a somewhat smaller inflation than L1's, consistent with the same `-O0` loop-overhead story being a smaller *relative* share of a longer absolute latency |
| LLC | **8,388,608 B (8 MiB)** — Phase I, from `CAPACITY_RESULTS.md`. **Phase II system-reported: 8,388,608 B exactly** (`lscpu --caches` ONE-SIZE/ALL-SIZE both 8M — single-socket, 1 LLC instance) — an exact byte-for-byte match to Phase I's estimate | Phase I: **best guess 8-way** (explicitly presented as an effective point estimate, blocked by the same small-fixed-structure confound documented across 6+ machines — see `data_processed/ookay/FINAL_CACHE_TABLE.md`'s reasoning). **Phase II system-reported: 16-way — a real disagreement, resolved in favor of the system-reported value** (see Agreement) | Phase I (at its own 8-way guess): 16,384 (also a clean integer — see the caveat in `FINAL_CACHE_TABLE.md` about why this check is weaker evidence here than on Sunbird). **Phase II system-reported (at the correct 16-way): 8,192 sets** — S=C/(A·B) = 8,388,608/(16×64), also a clean integer | **64 B** — Phase I unresolved/inconclusive at this level; Phase II system-reported: 64 B | Phase I: ≈74.78 ticks/access. Phase II/PMU: bench median ≈128.42 ticks/access (**+71.7% vs. Phase I — a real divergence, see caveat below, not silently averaged away**), median cycles/access ≈736.89, ns/access (wall-clock) ≈265.36 — **NOT usable as an absolute latency number**, same process-lifetime-contamination effect documented for Sunbird's LLC row, amplified here (see caveats). Miss-rate corroboration is the reliable signal: LLC-scope-specific miss rate jumps to 32.39% and generic cache-miss rate to 61.50% (both were ≤12.14%, mostly single digits, at the L1/L2 footprints) — a clean order-of-magnitude jump exactly at the footprint Phase I placed the LLC boundary, corroborating it independently despite the latency-number divergence | Phase I: shared across cores/socket (architectural guess). **Phase II system-reported: `shared_cpu_list=0-7`** — all 8 logical CPUs of this machine's single socket/4 physical cores (unlike Sunbird's 2-socket NUMA design, Ookay's LLC is shared across the *entire chip*, not just one socket's worth) — confirms and simplifies the architectural guess | 3–24 MB, 64 B line, **latency 34–85 cycles**, shared (Fog Table 11.2 — no ways/sets figure published for L3 at all, only size/line/latency/sharing) | Size: **exact match** (8 MiB, within Fog's 3–24 MB family range). **Ways: Phase I (8, confound-caveated) vs. system-reported (16) — mismatch, resolved in favor of system-reported 16-way**, the same resolution pattern as Sunbird's LLC row and this table's own L2 row — concrete, repeated evidence that Phase I's confound-driven "8" (recurring at both L2 and LLC here) was never real associativity. Fog gives no specific ways figure to cross-check against, unlike L1/L2. Sets: only a clean integer either way here (8 MiB and 64 B are both powers of two — see `FINAL_CACHE_TABLE.md`'s own caveat that this internal-consistency check is weaker evidence on this machine than on Sunbird). Latency: measured (~74.78 Phase I ticks) is inside Fog's 34–85 cycle range at face value, but the Phase II PMU cycles/access number (~737) is not a like-for-like comparison — see caveats |

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **This machine's PMU reliably schedules all 4 two-hardware-event groups at
  100%** (same design as Sunbird's/Thunderbird's pipeline run — `nmi_watchdog=1`
  is set here too, so the script's 2-event-per-group split was used as-is,
  not re-derived from scratch). No `<not counted>` flags anywhere in this
  run's raw data, and (unlike Thunderbird's ARM PMU) `LLC-loads`/
  `LLC-load-misses` scheduled and counted normally at every footprint.
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — same caveat as
  Sunbird's table: they also include process fork/exec, the 3 untimed
  warmup passes, and chase-buffer permutation construction. At the L1/L2
  footprints this makes the derived numbers not directly comparable to
  Phase I's own batch-internal RDTSC measurement; at the LLC footprint the
  effect is large enough (median cycles/access ≈737, vs. a ~75-tick Phase I
  number) that these two derived columns must **not** be read as a real
  per-access latency at all — only the qualitative, order-of-magnitude jump
  between footprints is meaningful.
- **New finding on this machine, not seen on Sunbird/Thunderbird: the
  generic `cache-references`/`cache-misses` ratio and the `LLC-loads`-
  specific ratio are BOTH non-monotonic across footprints** — higher at the
  small L1 footprint (18.54% / 17.34%) than at the L2 footprint (3.33% /
  1.38%), before climbing again at the LLC footprint (61.50% / 32.39%),
  reproducibly across all 3 runs at each level (not a one-off spike). Most
  likely explanation: at the L1 footprint the timed loop itself finishes in
  only ~3.3–4.6 ms, so the fixed one-time cost (process fork/exec, warmup
  passes, permutation construction) is a much larger share of the whole
  measured window than at the larger footprints, and that one-time setup
  phase plausibly generates its own LLC-scope references unrelated to the
  steady-state per-access signal — diluting/inflating the ratio in a way
  that shrinks (rather than grows) once the timed loop's own duration
  dominates more of the total at L2, then genuinely climbs again at LLC.
  The **L1-dcache-specific** miss rate does NOT show this artifact and
  climbs monotonically (0.97% → 12.14% → 8.79%, the last value saturating
  rather than climbing further, same `-O0` stack-load dilution effect
  documented on Sunbird) — treated as the more trustworthy per-level
  indicator for this reason, alongside the two LLC-scope ratios' clean jump
  specifically between L2 and LLC.
- **New finding, this machine only: the LLC-footprint run's own bench
  latency (≈128.42 ticks median) diverges substantially from Phase I's
  original hit_latency result (≈74.78 ticks, +71.7%), unlike L1/L2 which
  reproduced Phase I closely (+1.7%/+3.6%).** Investigated rather than
  averaged away: this session's per-run `cycles ÷ duration_time` implied
  clock frequency was unstable and inconsistent with a quiet chip — 2.99,
  3.62, 4.17 GHz across the 3 L1 runs; 4.24, 4.43, 4.41 GHz at L2; and
  **2.32–4.80 GHz at LLC (a run exceeding this CPU's own reported 4.2 GHz
  max turbo)** — all measured while `mpstat`/`ps` confirmed two other
  students' processes (`incl_pmu`, `cache_bench_x86`) pinned at 100% CPU on
  cores 0 and 2 for this session's entire duration, even though core 3
  (this run's core, both SMT threads) was independently verified idle
  before, during, and after via 3 separate `mpstat` samples a few seconds
  apart. Leading hypothesis: shared-LLC/memory-bandwidth contention and
  per-package Turbo Boost power-budget sharing across all 4 physical cores
  can measurably affect a nominally-idle core's own achieved frequency and
  effective LLC access latency — a genuinely idle *core* does not fully
  insulate a benchmark from *chip-shared* resource contention the way it
  does for L1/L2 (which are private per core). Not resolved further this
  session (would need a re-run once the machine is fully quiet to confirm);
  flagged plainly rather than silently reconciled, consistent with this
  project's established practice of documenting rather than smoothing over
  shared-machine noise.
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/ookay/pmu/<level>/pmu_summary_20260914T003308Z.csv` — the
  table above cites each metric's median-of-3 value.

## Where the underlying data lives

- Phase II PMU raw: `data_raw/ookay/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz`
  (perf stat output) and `*_bench_*.csv.gz` (cache_bench's own CSV from the
  same invocation).
- Phase II PMU processed: `data_processed/ookay/pmu/{L1,L2,LLC}/pmu_summary_20260914T003308Z.csv`.
- Phase II system-reported: `data_raw/ookay/pmu/system_reported_cache_info.txt`.
- Phase I (unchanged): `data_processed/ookay/FINAL_CACHE_TABLE.md`,
  `data_raw/ookay/README.md`.
- Literature: Agner Fog's manual, §11.12/Table 11.2, p. 160 (see citation
  above) — a local copy of the fetched PDF is not committed to this repo
  (external reference only, per the citation).
