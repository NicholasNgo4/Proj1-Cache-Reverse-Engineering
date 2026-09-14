# Phase II Validation Table — Skylark (2026-09-14)

Per `PROJECT 1.pdf`'s Table 2 requirement: a compact post-Phase-I validation
table with measured size/ways/sets/line/latency/sharing-scope columns kept
**separate** from the cited reference/literature value and the Agreement
verdict. This file only exists because Phase I is now frozen and tagged
(`phase1-timing-only`, per `README.md`'s Phase Discipline) — nothing here
touches or overwrites `FINAL_CACHE_TABLE.md`, which remains the frozen,
timing-only Phase-I record. Produced with `scripts/run_pmu_verification.sh`
(the canonical pipeline settled after the Sunbird/Thunderbird divergence —
see `CLAUDE.md`), the same convention Sunbird and Thunderbird already use.

**Three independent sources feed this table, kept distinguishable in every
cell:**
1. **Phase I (timing-only)** — carried over read-only from
   `data_processed/skylark/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh skylark 5
   L1:32768,L2:524288,LLC:8388608`, core 5 — sampled idle via two `mpstat`
   windows a few seconds apart before starting, confirmed free of the other
   students' processes pinned to cores 0/2/3 at the time — base_seed=12345 +
   2 seeded repeats, 1,000,000 samples/run, timestamp `20260914T002932Z`).
   Raw: `data_raw/skylark/pmu/<level>/`. Summaries:
   `data_processed/skylark/pmu/<level>/pmu_summary_20260914T002932Z.csv`.
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/cpu5/cache/index*/*` (core 5, the core used for
   the PMU run above), saved verbatim in
   `data_raw/skylark/pmu/system_reported_cache_info.txt` (collected
   2026-09-14T00:2x:xxZ, same session).
4. **Reference (literature)** — Agner Fog, *The microarchitecture of Intel,
   AMD and VIA CPUs* (agner.org/optimize/microarchitecture.pdf, PDF fetched
   and converted to text this session), Chapter 22 "AMD Zen 1-2 pipeline",
   §22.16 "Cache and memory access", **Table 22.3 "Cache sizes on AMD Zen
   2"**, p. 237. Skylark is 2× AMD EPYC 7532, Zen 2 — covered by this table
   (not the Zen-1 Table 22.2 just above it on the same page). Supplemented
   by AMD's own published EPYC 7532 product specs (base/boost clock, total
   L3) via WikiChip/Tom's Hardware/vendor-reseller listings, cited inline
   where used, for the CCD/CCX chiplet layout Fog's per-generation table
   doesn't cover (SKU-specific, not microarchitecture-generic).

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **32,768 B (32 KiB)** — Phase I confirmed; Phase II system-reported (`lscpu --caches`, sysfs `index0`) identical: 32K | **8-way** — Phase I confirmed (clean knee); Phase II system-reported: 8-way | **64** — Phase I derived (S=C/(A·B)); Phase II system-reported: 64 sets | **64 B** — Phase I confirmed (2 methods); Phase II system-reported: 64 B | Phase I: ≈6.24 ticks/access. Phase II/PMU (same footprint, this run): median cycles/access ≈10.58, ns/access (wall-clock) ≈4.82 — **see caveat below, not a clean single-access number**. Phase II/PMU miss-rate corroboration: L1 miss rate 0.42% (median) — consistent with a fully L1-resident working set | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=5`** — private to this one logical core (SMT disabled machine-wide, `Thread(s) per core: 1`) — confirms the guess | 32 kB, 8-way, 64 sets, 64 B line, **latency 4 cycles**, per core (Fog Table 22.3) | Size/ways/sets/line/sharing: **exact match, all 3 sources.** Latency: measured (~6.24 ticks / ~10.58 cycles) reads **higher** than Fog's 4 cycles — attributed to this project's `-O0` dependent-chase loop overhead (stack spill/reload of the chase pointer sits in the true dependency chain every iteration), same explanation Sunbird's/Thunderbird's writeups already used, not a contradiction |
| L2 | **524,288 B (512 KiB)** per `CAPACITY_RESULTS.md` (hand-verified, taken as given — Phase I's own capacity sweep only resolved a broad candidate shelf, not a clean 512 KiB edge). **Phase II system-reported: 512K identical** | Phase I *best guess*: **8-way** (auto-detected "9" read as an L1-aliasing artifact — 524,288 B is an exact 16x multiple of L1's own stride — see `FINAL_CACHE_TABLE.md`'s reasoning). **Phase II system-reported: 8-way — independently confirms the best guess**, same pattern as Sunbird's own L2 row | **1,024** — Phase I derived; Phase II system-reported: 1,024 sets | **64 B** — Phase I "best available estimate, no counter-evidence" (this footprint's own line_size sweep found no elbow). Phase II system-reported: 64 B — confirms it wasn't just a placeholder guess | Phase I: ≈15.38 ticks/access. Phase II/PMU: median cycles/access ≈31.76, ns/access (wall-clock) ≈11.65 — same overhead caveat as L1. Miss-rate corroboration: L1 miss rate rises to 9.05% (footprint now exceeds L1, as expected) | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=5`** — private per core, same as L1 | 512 kB, 8-way, 1024 sets, 64 B line, **latency 12 cycles**, per core (Fog Table 22.3) | Size/ways/sets/line/sharing: **exact match, all 3 sources** — the confound-blocked Phase-I associativity best guess is now independently confirmed by direct OS/hardware self-report, same story as Sunbird's L2 row. Latency: measured (~15.38 ticks / ~31.76 cycles) **higher** than Fog's 12 cycles, same `-O0` loop-overhead explanation, inflation ratio (~2.6x) consistent with L1's |
| LLC | **8,388,608 B (8 MiB)** per `CAPACITY_RESULTS.md`, already **flagged in `FINAL_CACHE_TABLE.md` as a likely underestimate** (Skylark's own capacity data pointed to a real knee closer to ~16.8-21.8 MiB). **Phase II system-reported: 16,777,216 B (16 MiB) exactly** — this directly confirms the suspected underestimate (2x Phase I's chosen representative value) and lands almost exactly at the *bottom* of Phase I's own ~16.8-21.8 MiB re-look bracket (within ~0.2%) — a clean resolution, not a new mystery | Phase I: **best guess 8-way**, explicitly presented as an "effective estimate" — blocked by the same small-fixed-structure confound documented across 5+ team machines (`CLAUDE.md`'s running tally). **Phase II system-reported: 16-way — a real disagreement, resolved in favor of the system-reported value**, matching the same pattern as Sunbird's LLC row (9→20) and Thunderbird's L2 row (12→8) | Phase I: 8,192 (using the *wrong* 8 MiB/128 B/8-way combination — a clean integer by coincidence, not correctness). **Phase II system-reported: 16,384** (exact integer, S=16,777,216/(16·64)) | Phase I: **128 B**, confirmed at the LLC-region transition by 2 independent methods — notably 2x this machine's own L1/L2 line size. **Phase II system-reported: 64 B**, uniform across all 3 levels — a real disagreement (see Agreement) | Phase I: ≈27.26 ticks/access. Phase II/PMU: median cycles/access ≈230.03, ns/access (wall-clock) ≈73.97 — **not usable as an absolute latency number** at this footprint, same caveat as Sunbird's LLC row (warmup/permutation-construction dominates total process time here). Miss-rate corroboration is the reliable signal: generic `cache-references/cache-misses` miss rate jumps to 46.59% (vs. 19.34%/11.32% at the L1/L2 footprints) — the LLC footprint is unambiguously the highest of the three, though see the caveat below on why the L1/L2 footprint numbers for this *specific* metric shouldn't be read as a clean monotonic ramp on this machine | Phase I: shared across cores/socket (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=4-5`** — shared by only **2 logical cores**, not the whole socket (32 cores) — confirmed as a machine-wide pattern, not a quirk of core 5 specifically (spot-checked cores 0, 4, 6, 8, 12: each L3 instance's `shared_cpu_list` is consistently one adjacent core-pair, e.g. `0-1`, `6-7`, `8-9`, `12-13`). This directly explains why `lscpu --caches` shows 32 separate 16 MiB L3 "instances" for this 64-core-total machine (64÷32=2 cores/instance) rather than one large per-socket slice | 4-32 MB, 16-24 way, 64 B line, one L3 **per 4 cores**, latency 40 clocks (Fog Table 22.3, stated as a family-wide range for Zen 2, not per-SKU) | Size: **within Fog's 4-32 MB family range**, and see the underestimate-resolution note above. Ways: **Phase I (8, confound-blocked) vs. system-reported (16) — mismatch, resolved in favor of system-reported 16-way**, itself at the low end of Fog's quoted 16-24-way range (this exact SKU, not just "somewhere in the family"). Sets: only a clean integer at 16-way with the *correct* 64 B line — additional post-hoc evidence 8-way/128 B was the wrong combination, not merely an imprecise one. **Line size: a genuine, unresolved disagreement — Phase I's 128 B (2 independently-agreeing methods) vs. system-reported 64 B.** Leading hypothesis (plausible, NOT confirmed this phase, no dedicated follow-up run): Zen 2's documented hardware prefetchers (adjacent-line/stream prefetching, most active on L2↔L3 traffic per public microarchitecture writeups) could make a stride-based line-size probe see an *effective* 128 B granularity specifically once the working set spills past L2, without the physical line itself being any wider than the 64 B every level in Table 22.3 (and this machine's own sysfs) reports uniformly — flagged as an open question, not resolved by literature/system-report alone. **Sharing scope: also a genuine, informative disagreement.** Table 22.3 states one Zen 2 L3 "per 4 cores" as the microarchitecture-generic figure, but this specific SKU's L3 is shared by only **2** cores per instance — resolved by AMD's own published EPYC 7532 spec (232MB→256 MB L3, "double the L3 of other 32-core EPYC chips" per vendor/reseller listings): 8 CCDs × 2 CCX/CCD × 16 MiB/CCX = 256 MiB total, meaning this 32-core SKU runs only 2 (not the architecturally-typical 4) active cores per CCX while still granting each CCX its *full* 16 MiB L3 — a known AMD Rome "cache-doubled" binning strategy for this exact part number, not a measurement error or a contradiction of Fog's generic per-generation number. Latency: measured (~27.26 ticks) higher than Fog's 40 cycles at small `-O0` overhead ratios seen at L1/L2, plausibly because 40 cycles is itself already a fairly large number that the loop overhead is a smaller *relative* share of — same reasoning Sunbird's writeup used for its own LLC row |
| DRAM (reference floor, not a cache level) | — | — | — | — | Phase I: ≈274.87 ticks/access (from `data_processed/skylark/FINAL_CACHE_TABLE.md`) | — | — | — |

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **This machine's PMU reliably schedules the generic `cache-references`/
  `cache-misses`, `L1-dcache-loads`/`L1-dcache-load-misses`, and `cycles`/
  `instructions` 2-event groups at 100%** — spot-checked by hand before the
  full run (same reasoning as Sunbird's own pre-check: the script's 4-group
  design exists specifically because 3+ event groups don't reliably schedule
  everywhere).
- **`LLC-loads`/`LLC-load-misses` are unsupported on this AMD Zen 2 PMU for
  an unprivileged user — confirmed a real hardware/permission limitation,
  not counter contention.** Raw `perf stat -x,` output literally reports
  `<not supported>` (not `<not counted>`) for both events at every level —
  a stronger, more definitive failure than Thunderbird's ARM PMU (which
  also lacked an LLC-scoped alias) or a scheduling conflict. Also hand-
  checked this session: AMD's own raw uncore L3 events (`l3_accesses`,
  `l3_misses`, PMU unit `amd_l3`) fail identically even system-wide
  (`perf stat -a`), consistent with this session's `perf_event_paranoid=2`
  blocking unprivileged access to the socket-scoped uncore PMU entirely —
  no `sudo` available to test whether root access would resolve it. **Note
  on the summary CSV's `notes` column**: `scripts/summarize_pmu.py` (line
  47) only special-cases the literal string `<not counted>`; `<not
  supported>` falls through to the same generic exception handler and gets
  the same hardcoded "`<not counted>`" note text (see
  `pmu_summary_20260914T002932Z.csv`'s `notes` column for all 3 levels) —
  a cosmetic imprecision in the existing script (not touched this session,
  since Thunderbird's writeup already logged the identical mismatch
  without patching it), the true raw value is `<not supported>` as shown
  above.
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — same caveat as
  Sunbird's/Thunderbird's writeups: they include process fork/exec, the 3
  untimed warmup passes, and chase-buffer permutation construction. At the
  LLC footprint this inflation is large enough (median cycles/access ≈230
  vs. a ~27-tick Phase I number) that these two columns are only usable as
  an order-of-magnitude cross-check, not a real per-access latency, at that
  footprint. As a sanity check, `cycles ÷ duration_time` gives an implied
  clock speed of ≈2.19 GHz (L1), ≈2.73 GHz (L2), ≈3.11 GHz (LLC) — all
  within this CPU's published 2.4-3.3 GHz base/boost range (AMD EPYC 7532
  spec), with the L1 footprint's low-end reading consistent with fixed
  process-startup overhead being a larger relative share of a very short
  total run, same effect Sunbird's writeup flagged.
- **The generic `cache-references`/`cache-misses` group's miss rate is
  *not* a clean monotonic LLC-scope signal on this machine, unlike
  Sunbird's x86 run.** Values were 19.34% (L1 footprint) → 11.32% (L2
  footprint) → 46.59% (LLC footprint) — a dip-then-jump, not a steady
  climb. The LLC footprint's sharp jump is still a clean, trustworthy
  corroboration of the LLC boundary. But the L1-footprint's comparatively
  high 19.34% is very likely small-sample noise, not signal: the absolute
  `cache-references` count at the L1 footprint is only 69,146 (vs.
  7,613,735 `L1-dcache-loads` in the same run — roughly a 110x gap),
  suggesting this generic AMD PMU alias tracks something closer to L2
  request traffic than L1 or LLC traffic (AMD's generic-to-raw-event
  mapping differs from Intel's), so at a footprint that's supposed to stay
  entirely within L1, only a small, noisy trickle of L2-scope events occurs
  at all, and their miss-rate ratio is unstable at that low a count. Not
  investigated further at the raw-event level this session — flagged as an
  open, AMD-specific caveat on this one metric, not extended into a new
  claim about this machine's L2/L3 policy.
- `l1_miss_rate` shows the same known dilution/saturation effect already
  documented in Sunbird's writeup: it climbs cleanly across the L1→L2
  crossing (0.42% → 9.05%) but then does not climb further — it actually
  *dips slightly* at the LLC footprint (6.13%) rather than plateauing high.
  Same root cause already identified for Sunbird: `-O0`'s per-iteration
  stack spill/reload traffic contributes a large, constant share of
  guaranteed-L1-hit loads regardless of footprint, diluting the ratio once
  the chase load itself is already usually missing L1 — not treated as new
  evidence about L2/LLC boundaries.
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/skylark/pmu/<level>/pmu_summary_20260914T002932Z.csv` —
  the table above cites each metric's median-of-3 value.

## Where the underlying data lives

- Phase II PMU raw: `data_raw/skylark/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz`
  (perf stat output) and `*_bench_*.csv.gz` (cache_bench's own CSV from the
  same invocation).
- Phase II PMU processed: `data_processed/skylark/pmu/{L1,L2,LLC}/pmu_summary_20260914T002932Z.csv`.
- Phase II system-reported: `data_raw/skylark/pmu/system_reported_cache_info.txt`.
- Phase I (unchanged): `data_processed/skylark/FINAL_CACHE_TABLE.md`,
  `data_raw/skylark/README.md`.
- Literature: Agner Fog's manual, Ch. 22 §22.16, Table 22.3, p. 237 (see
  citation above) — a local copy of the fetched PDF is not committed to
  this repo (external reference only, per the citation, same convention as
  Sunbird's table).
- CPU/SKU-specific supplementary sourcing (CCD/CCX layout, total L3, base/
  boost clock): AMD EPYC 7532 public product specs, cited inline above —
  used only to explain the sharing-scope and clock-sanity-check findings,
  not as a substitute for Fog's microarchitecture-level cache table.
