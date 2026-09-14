# Phase II Validation Table — Charnwood (2026-09-14)

Per `PROJECT 1.pdf`'s Table 2 requirement: a compact post-Phase-I validation
table with measured size/ways/sets/line/latency/sharing-scope columns kept
**separate** from the cited reference/literature value and the Agreement
verdict. This file only exists because Phase I is now frozen and tagged
(`phase1-timing-only`, per `README.md`'s Phase Discipline) — nothing here
touches or overwrites `FINAL_CACHE_TABLE.md`, which remains the frozen,
timing-only Phase-I record. Built following the canonical convention
`scripts/run_pmu_verification.sh` established on Sunbird/Thunderbird (see
`CLAUDE.md`'s Phase II section) — same pipeline, same table shape, so all
three (and future machines) can be read side by side.

**Three independent sources feed this table, kept distinguishable in every
cell:**
1. **Phase I (timing-only)** — carried over read-only from
   `data_processed/charnwood/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh charnwood 3
   L1:32768,L2:262144,LLC:8388608`, core 3, base_seed=12345 + 2 repeats,
   1,000,000 samples/run, timestamp `20260914T003212Z`). Raw:
   `data_raw/charnwood/pmu/<level>/`. Summaries:
   `data_processed/charnwood/pmu/<level>/pmu_summary_20260914T003212Z.csv`.
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/cpu{0,1,2,3}/cache/index*/*`, saved verbatim in
   `data_raw/charnwood/pmu/system_reported_cache_info.txt` (collected
   2026-09-14T00:33:11Z).
4. **Reference (literature)** — Agner Fog, *The microarchitecture of Intel,
   AMD and VIA CPUs*, last updated 2026-05-23, §11.12 "Cache and memory
   access", Table 11.2 "Cache sizes on Skylake", p. 160 (canonical:
   `www.agner.org/optimize/microarchitecture.pdf`). Charnwood is an
   Intel Core i7-6700 (Skylake client, 6th-gen desktop) — the exact
   microarchitecture this table covers, unlike Sunbird's Haswell-EP
   Xeon needing the earlier Table 10.2.

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **32,768 B (32 KiB)** — Phase I confirmed; Phase II system-reported (`lscpu --caches`, sysfs `index0` on cpu3) identical: 32K | **8-way** — Phase I confirmed (clean single knee, 0 disagreement across base+2 repeats); Phase II system-reported: 8-way | **64** — Phase I derived (S=C/(A·B)); Phase II system-reported: 64 sets | **64 B** — Phase I confirmed (family-of-curves + step-4 offset check); Phase II system-reported: 64 B | Phase I: ≈7.98 ticks/access (rep1+rep2 average, base-run P-state-elevated). Phase II/PMU (same footprint, this run): median cycles/access ≈14.73, wall-clock ≈6.13 ns/access — **reads noticeably higher than even Phase I's own number; see the contention/turbo caveat below, not a clean single-access figure**. Phase II/PMU miss-rate corroboration: L1 miss rate 1.13% (median) — low, consistent with a fully L1-resident working set | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=3,7`** — private to physical core 3's own 2 SMT threads only (confirms + sharpens the guess) | 32 kB, 8-way, 64 sets, 64 B line, **latency 4 cycles**, per core (Fog Table 11.2) | Size/ways/sets/line/sharing: **exact match, all 3 sources.** Latency: measured (~7.98 ticks Phase I / ~14.73 cycles this PMU run) reads **higher** than Fog's 4 cycles — the same `-O0` dependent-chase loop-overhead attribution Sunbird's/Thunderbird's tables already used (stack spill/reload of the chase pointer sits in the true dependency chain every iteration) applies here too, compounded this run by the contention/turbo effect documented below |
| L2 | **262,144 B (256 KiB)** — Phase I ("hand-verified, take as given" per `CAPACITY_RESULTS.md`); Phase II system-reported: 256K identical | Phase I: **best guess 8-way** (confound-blocked — see `FINAL_CACHE_TABLE.md`'s reasoning). **Phase II system-reported: 4-way — a real disagreement, resolved in favor of the system-reported value** (see Agreement) | Phase I: 512 (at the wrong guessed 8-way). **Phase II system-reported: 1,024** (S=262,144/(4·64), exact integer) | **64 B** — Phase I best-available (no counter-evidence at this footprint); Phase II system-reported: 64 B | Phase I: ≈17.27 ticks/access. Phase II/PMU: median cycles/access ≈32.51, wall-clock ≈12.03 ns/access — same overhead+contention caveat as L1. Miss-rate corroboration: L1-scope miss rate jumps to 12.22% (footprint now exceeds L1) while LLC-scope miss rate stays low (1.51%), generic cache-miss rate 4.04% — the expected signature of a footprint sized to fit L2 | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=3,7`** — private per physical core, same as L1 | 256 kB – 1 MB, 4–16 way, 1,024 sets, 64 B line, **latency 14 cycles**, per core (Fog Table 11.2) | Size/sets/line/sharing: **exact match, all 3 sources** (256 KiB and 1,024 sets sit exactly at the low end of Fog's own quoted ranges, since this particular Skylake SKU is a 4-core client part rather than a larger die). **Ways: Phase I's confound-blocked best guess (8-way) was wrong — system-reported 4-way, which is also literature's own quoted low end of "4–16 way" for this family, a 2-source agreement against the 1 confound-limited Phase I guess.** Latency: measured (~17.27 ticks / ~32.5 cycles) higher than Fog's 14 cycles, same `-O0`+contention story as L1 |
| LLC | **8,388,608 B (8 MiB)** — Phase I, from `CAPACITY_RESULTS.md` (rounded team estimate, "take as given"). **Phase II system-reported: 8,388,608 B exactly** (`lscpu --caches` ONE-SIZE/ALL-SIZE both 8M, single LLC instance for the whole socket) — an exact byte-for-byte match to Phase I's estimate | Phase I: **best guess 8-way** (explicitly presented as an effective point estimate, blocked by the same small-fixed-structure/DTLB-scale confound documented across 5+ team machines — see `FINAL_CACHE_TABLE.md`). **Phase II system-reported: 16-way — a real disagreement, resolved in favor of the system-reported value** (see Agreement) | Phase I: 16,384 (at the wrong guessed 8-way, though it happened to come out as a clean integer). **Phase II system-reported: 8,192** (S=8,388,608/(16·64), also a clean integer) | **64 B** — Phase I leaning/best-available (75% offset-agreement, not fully confirmed); Phase II system-reported: 64 B | Phase I: ≈108 ticks/access (all 3 runs agree within ~107-109). Phase II/PMU: median cycles/access ≈631.1, wall-clock ≈244.1 ns/access — **NOT usable as an absolute latency number** (whole-process-lifetime contamination at this footprint scale, same caveat Sunbird's own LLC row required — see caveats below). Miss-rate corroboration is the reliable signal here: LLC-scope miss rate jumps to 31.37% and generic cache-miss rate to 33.56% (both were ≤4.04% at the L1/L2 footprints) — a clean order-of-magnitude jump exactly at the footprint Phase I placed the LLC boundary, independently corroborating it | Phase I: shared across cores/socket (architectural guess). **Phase II system-reported: `shared_cpu_list=0-7`** — confirms and quantifies: shared across the *entire socket* (all 4 cores / 8 logical CPUs), not just a subset | 3–24 MB, 64 B line, **latency 34–85 cycles**, shared (Fog Table 11.2 — **no ways figure given for L3 in this table**, unlike Fog's own Haswell/Broadwell Table 10.2, which did quote a 12–16-way range; this is an honest gap in the literature source, not an omission on this session's part) | Size: **exact match** (8 MiB, comfortably inside Fog's 3–24 MB family range). **Ways: Phase I (8, confound-blocked point estimate) vs. system-reported (16) — mismatch, resolved in favor of system-reported 16-way; no literature value exists to arbitrate a 3rd time here** (see the reference-value note). This is now the **third** team machine (after Sunbird's LLC and Thunderbird's L2) where a confound-blocked Phase I associativity guess disagreed with the system-reported ground truth once Phase II unlocked it — direction varies (Sunbird guessed too low, Charnwood also guessed too low here, at exactly half the true 16-way), but the pattern that no machine's guess has yet landed exactly right is now well-established. Sets: only comes out as the historically load-bearing integer at 16-way (8,192, matching Fog's implied structure); the guessed-8-way's own 16,384 was a coincidental clean integer too, so unlike Sunbird's table, integrality alone couldn't have flagged the wrong guess here — only the direct system-report could. Latency: Phase I's ~108 ticks is not directly convertible to Fog's 34–85 *cycle* range without a documented ticks→cycles factor (RDTSC-based "ticks" run at a fixed reference rate, not this core's dynamic/turbo frequency) — same caution Sunbird's/Thunderbird's tables already applied; qualitatively, 108 sits above even the top of Fog's range the way L1/L2 did, consistent with the same `-O0` overhead (now also compounded by this run's contention/turbo suppression, see below) |

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **This machine's PMU reliably scheduled all 4 two-event groups at 100% for
  every (level, run_tag) this run** — no `<not counted>` anywhere in any of
  the 9 (level × run_tag) result sets, unlike the possibility flagged in
  `run_pmu_verification.sh`'s own header comment. `nmi_watchdog=1` is still
  set on this machine (same as Sunbird), consistent with the "2 generic
  counters reliably schedulable" design the script assumes.
- **Confirmed real-time contention from two other logged-in users' processes
  during this entire PMU run — the likely cause of a fairly uniform ~30-36%
  inflation in `bench_avg_ticks_per_access_median` at all three levels
  relative to Phase I's own (quieter-session) hit_latency numbers**
  (L1: 10.53 vs. 7.98; L2: 23.57 vs. 17.27; LLC: 141.2 vs. 108 — each
  roughly 30-36% higher). Directly observed via `ps`/`mpstat` throughout:
  `dsengup2`'s `incl_pmu` process pinned at ~100-133% CPU on physical core 0
  (PID 1812516, elapsed ~51 min at run time) and `msabap`'s `cache_bench_x86`
  process pinned at ~100% CPU on physical core 2 (PID 1807870, elapsed
  ~1h09m at run time) — **neither shares a physical core with this run's
  pinned core 3** (confirmed via `taskset -cp` on both PIDs and `mpstat -P
  3,7` showing 98-100% idle across 3 sampling windows immediately before and
  during the run), so this is not the classic same-core interference
  documented elsewhere in this project. Instead, the mechanism is most
  likely **package-level turbo-budget suppression**: `scaling_governor` is
  `powersave` and `intel_pstate/no_turbo` is `0` (turbo available in
  principle), but core 3's `scaling_cur_freq` measured ~2.70 GHz while cores
  0/2 were both near 100% busy — well below this CPU's 3.4 GHz base and
  4.0 GHz max turbo. `cycles/duration_time_ns` computed directly from this
  run's own PMU counters independently corroborates a suppressed clock:
  ~2.40 GHz (L1), ~2.70 GHz (L2), ~2.59 GHz (LLC) — all in the same
  ~2.4-2.7 GHz band, well under base clock, at a physical core that was
  itself otherwise idle. Intel's per-package turbo bin allocation depends on
  the total number of active cores and the package's shared power/thermal
  budget, so two other physical cores sustained near 100% for the run's
  entire duration plausibly capped how high core 3 could turbo even though
  it had no direct resource conflict with either contending process. This is
  a real, plausible architectural explanation for the observed inflation,
  not proven via direct thermal/power telemetry — flagged as the leading
  hypothesis, not a certainty.
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — same caveat
  Sunbird's table already documented: they also include process fork/exec,
  3 untimed warmup passes, and chase-buffer permutation construction. At the
  LLC footprint this dominates enough (median cycles/access ≈631, vs. a
  ~108-tick Phase I number) that this derived column must **not** be read as
  a real per-access latency at all — only the qualitative, order-of-magnitude
  jump between footprints (see miss-rate discussion below) is meaningful.
- **The miss-rate metrics are the trustworthy Phase-II PMU corroboration
  signal**, for the same reason Sunbird's table gives (a ratio of two counts
  from the same inflated process lifetime cancels most of the contamination
  AND is insensitive to the turbo-suppression effect above, since both
  numerator and denominator scale together): `l1_miss_rate` cleanly confirms
  the L1→L2 capacity crossing (1.13% → 12.22%) but then only modestly rises
  further at the LLC footprint (8.87%, i.e. essentially flat vs. L2) — the
  same `-O0` stack-load dilution effect Sunbird's writeup already documented
  for this exact ratio; `cache_miss_rate`/`llc_miss_rate` (the LLC-scope
  generic events) are the cleaner signal and show the expected
  order-of-magnitude jump exactly at the LLC footprint (≈1.5-4.0% at
  L1/L2 → ≈31-34% at LLC).
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/charnwood/pmu/<level>/pmu_summary_20260914T003212Z.csv` —
  the table above cites each metric's median-of-3 value.

## Where the underlying data lives

- Phase II PMU raw: `data_raw/charnwood/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz`
  (perf stat output) and `*_bench_*.csv.gz` (cache_bench's own CSV from the
  same invocation) — gzipped by hand per `.gitignore`'s `data_raw/**/*.csv`
  rule.
- Phase II PMU processed: `data_processed/charnwood/pmu/{L1,L2,LLC}/pmu_summary_20260914T003212Z.csv`.
- Phase II system-reported: `data_raw/charnwood/pmu/system_reported_cache_info.txt`.
- Phase I (unchanged): `data_processed/charnwood/FINAL_CACHE_TABLE.md`,
  `data_raw/charnwood/README.md`.
- Literature: Agner Fog's manual, §11.12/Table 11.2, p. 160 (see citation
  above) — a local copy of the fetched PDF is not committed to this repo
  (external reference only, per the citation convention Sunbird's/
  Thunderbird's tables already established).
- Full run transcript: `data_raw/charnwood/pmu/run_pmu_verification_20260914T003212Z.log`.
