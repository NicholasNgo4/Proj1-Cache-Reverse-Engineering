# Phase II Validation Table — Thunderbird (2026-09-13)

Per `PROJECT 1.pdf`'s Table 2 requirement: a compact post-Phase-I validation
table with measured size/ways/sets/line/latency/sharing-scope columns kept
**separate** from the cited reference/literature value and the Agreement
verdict. This file only exists because Phase I is now frozen and tagged
(`phase1-timing-only`, per `README.md`'s Phase Discipline) — nothing here
touches or overwrites `FINAL_CACHE_TABLE.md`, which remains the frozen,
timing-only Phase-I record.

**Uses the same reusable pipeline as Sunbird's table** (`scripts/
run_pmu_verification.sh` + `scripts/summarize_pmu.py`) — an earlier pass on
this machine used a different, ad hoc script; that pass's findings are folded
in as supplementary evidence (§ below) rather than discarded, since it swept
a full range of working-set sizes the 3-point pipeline here does not, but
this file and its pipeline outputs are now the canonical Phase II deliverable
for this machine, matching every other machine's format.

**Four sources feed this table, kept distinguishable in every cell:**
1. **Phase I (timing-only)** — carried over read-only from
   `data_processed/thunderbird/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh thunderbird 3
   L1:65536,L2:1048576,LLC:31457280`, core 3, base_seed=12345 + 2 repeats,
   1,000,000 samples/run, timestamp `20260913T203354Z`). Raw:
   `data_raw/thunderbird/pmu/<level>/`. Summaries:
   `data_processed/thunderbird/pmu/<level>/pmu_summary_20260913T203354Z.csv`.
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/cpu3/cache/index*/*` (core 3, the core used for
   every Thunderbird run), saved verbatim in
   `data_raw/thunderbird/pmu/system_reported_cache_info.txt` (collected
   2026-09-13).
4. **Reference (literature)** — two independent sources, since Agner Fog's
   manual does not cover ARM:
   - **Ampere® Altra® 64-Bit Multi-Core Processor Datasheet**, Rev A1,
     Document Issue 1.30, 2022-07-28 (Ampere Computing). §2.3.1/2.3.2/2.4/2.5,
     p. 9. SKU-specific (Thunderbird is an Ampere Q80-30, i.e. Altra).
   - **Arm® Neoverse™ N1 Core Technical Reference Manual**, revision r3p1,
     document 100616_0301_01_en (Arm Limited). §A2.1.2 (p. A2-36), §A6.4
     (p. A6-78), §A7.1 (p. A7-102). Architectural — confirms Ampere's SKU
     choices sit inside the IP's documented configuration envelope. **Does
     not cover the SLC** (a mesh/DSU-level component outside a per-core
     manual's scope) — the LLC row below is corroborated by the Ampere
     datasheet alone, not cross-checked by this second source.

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **65,536 B (64 KiB)** — Phase I confirmed (`CAPACITY_RESULTS.md`, hand-verified). **Phase II system-reported (`lscpu --caches`, sysfs `cpu3/index0`) identical: 64K** | **4-way** — Phase I confirmed (clean knee, identical across base + both repeats, both patterns). **Phase II system-reported: 4-way — exact match** | **256** — Phase I derived (S=C/(A·B)); Phase II system-reported: 256 sets — exact match | **64 B** — Phase I confirmed (offset-independent elbow at 8/8 tested offsets); Phase II system-reported: 64 B — exact match | Phase I: ≈0.124–0.136 ticks/access (~5.0 ns @ 25 MHz). Phase II/PMU (same footprint, this run): median cycles/access ≈12.86, ns/access (wall-clock) ≈5.67 — broadly consistent with Phase I's ~5.0 ns given the same overhead caveats as Sunbird's table (see below). Miss-rate corroboration: L1 miss rate 0.20% (median) — consistent with a fully L1-resident working set | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=3`** — private to this one logical core (this CPU has no SMT — `Thread(s) per core: 1` — so unlike Sunbird's `0,24` pair, a single-entry list here already means "fully private," not just "private to one core's SMT siblings") | 64 KiB, 4-way, 64 B line — Ampere Altra Datasheet §2.3.1 p. 9; independently corroborated by Arm Neoverse N1 TRM §A2.1.2/A6.4 (PIPT, 4-way, 64 B lines) | Size/ways/sets/line/sharing: **exact match, all 3 sources — the cleanest row on this table**, matching Sunbird's own L1D result pattern. Latency: no published load-use-cycle figure exists in either literature source (neither vendor publishes it) — measured value (Phase I timing + Phase II PMU, mutually consistent) stands alone, uncorroborated by literature, same situation Sunbird's L1 row was in |
| L2 | **No confirmed Phase-I boundary** — continuous ramp in the raw capacity sweep, no flat shelf; Phase I's `FINAL_CACHE_TABLE.md` uses `CAPACITY_RESULTS.md`'s 1,048,576 B (1 MiB) as a hand-verified **take-as-given** value, not an independently confirmed one. **Phase II system-reported: 1024K (1 MiB) — identical to the assumed value** | Phase I: **best guess 12-way** (2-of-3 majority across base+repeats; explicitly flagged as confound-suspected — see `CLAUDE.md`'s associativity section). **Phase II system-reported: 8-way — a real disagreement, resolved in favor of the system-reported value** (see Agreement) | Phase I: 1,365 (non-integer at 12-way — itself a flag in hindsight, and explicitly noted in `FINAL_CACHE_TABLE.md` as not discriminating between candidates since both 1,048,576's power-of-two structure and the LLC's highly composite byte count are divisible by nearly every plausible way-count). **Phase II system-reported: 2048** (exact integer, S=1,048,576/(8×64)) | **64 B** — Phase I confirmed (offset-independent elbow at 6/8 tested offsets); Phase II system-reported: 64 B — exact match | Phase I: ≈0.2975 ticks/access (~11.9 ns). Phase II/PMU: median cycles/access ≈66.21, ns/access (wall-clock) ≈24.37 — same overhead caveat as L1/Sunbird's table. Miss-rate corroboration: `l1_miss_rate` jumps to 7.72% (footprint now well past L1) — consistent with a footprint sized for L2, though (see caveats below) this machine's generic `cache_miss_rate` tracks `l1_miss_rate` almost exactly rather than acting as a distinct LLC-scope signal the way it did on Sunbird | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=3`** — private per core, same pattern as L1 | 1024 KiB, 8-way, 64 B line, 2048 sets, private per-core — Ampere datasheet §2.4 p. 9 (Ampere's configuration choice; the Neoverse N1 IP is architecturally configurable at 256/512/1024 KiB, per Arm TRM §A2.1.2 — Ampere selected 1 MiB) | Size/line/sharing: **exact match, all 3 sources** (though the size match is partly circular — Phase I borrowed 1 MiB FROM `CAPACITY_RESULTS.md` rather than deriving it independently; Phase II system-report is the first source here to confirm it from something other than the same assumption). **Ways: Phase I (12, confound-suspected) vs. system-reported (8) — mismatch, resolved in favor of system-reported 8-way**, which is also the exact value the independent Arm/Ampere literature gives — **three-way convergence (system-report, Ampere datasheet, Arm TRM) against one confound-blocked Phase-I guess.** This directly confirms, rather than merely suspects, that the "10–12" the timing method kept finding across every large-stride candidate on this machine (documented at length in `CLAUDE.md`) was the shared small-structure confound, not real L2 associativity. Sets: only comes out to a clean integer at 8-way, additional post-hoc evidence 12-way was wrong |
| LLC | **~30 MiB (31,457,280 B representative)** — Phase I, from `CAPACITY_RESULTS.md` (rounded estimate, picked by eye from a documented noisy, non-plateau transition region — not a flat shelf). **Phase II system-reported: no L3/SLC entry exists in `lscpu --caches`/sysfs at all** (only `index0`/`index1`/`index2` = L1D/L1I/L2 are enumerated on this core) — system-reported evidence is silent on this row, a genuinely different situation from Sunbird's L3, which sysfs *did* expose directly | Phase I: **best guess 10-way**, fully reproducible across base + both repeats, presented as an "effective lower bound" per the same cross-machine DTLB/page-count confound documented in `CLAUDE.md`. **Phase II system-reported: N/A (no SLC entry to read)** — unlike Sunbird, this row cannot be resolved or even directly checked by system-report; only literature speaks to it, and only partially (see Reference) | Phase I: 24,576 (clean integer at 10-way — but `FINAL_CACHE_TABLE.md` itself flags this as weak evidence given the LLC's highly composite byte count divides cleanly under almost any candidate way-count). **Phase II: cannot derive independently** (no system-reported ways or line size for this level) | Phase I: **128 B — the one level on this machine that does NOT share the 64 B line size found at L1/L2** (majority elbow agreement at 7/8 tested offsets, reproduced across 2 seeds). **Phase II system-reported: N/A** (no SLC entry) | Phase I: ≈0.907 ticks/access (~36.3 ns, rep1/rep2 median — base run's 1.642 excluded as a single-run interference spike). Phase II/PMU (this run, base+rep1+rep2 median): ≈1.012 ticks (~40.5 ns) — same order of magnitude, base run here (0.925) did NOT show the same spike Phase I's base run did, so this run's 3-way median is used unfiltered; cycles/access ≈2096 (median) is **NOT usable as an absolute latency number**, same whole-process-lifetime dilution caveat as Sunbird's LLC row. Miss-rate corroboration: `l1_miss_rate`/`cache_miss_rate` read ≈5.50% here — **lower than the L2 footprint's ≈7.72%, the wrong direction for a real capacity-scoped miss-rate signal** (see caveats below for why this specific ratio isn't trustworthy as LLC-scope evidence on this machine) | Phase I: shared across cores/socket (architectural guess, untested). **Phase II literature: shared across ALL 80 cores** (Ampere datasheet §2.5: "a 32 MB distributed on-chip cache shared between all processors") — a real, load-bearing sharpening of the Phase-I guess, and a structural difference from every other cache row on this machine (L1/L2 are private-per-core; the SLC is not) | 32 MiB, 16-way, shared/distributed, "mostly exclusive with L2" — Ampere datasheet §2.5 p. 9. **Not covered by the Arm Neoverse N1 core TRM** (SLC is outside a per-core manual's scope) — single-source only, unlike L1D/L2 | **The weakest-supported row on the table, by a wide margin.** Size: suggestively close (~30 MiB measured vs. 32 MiB reference, ~94%) but resting on Phase I timing and the datasheet alone — Phase II system-report has nothing to say here (no SLC entry in sysfs), a direct contrast with Sunbird's LLC row, where system-report gave an exact byte-for-byte size match AND resolved the associativity disagreement outright. Ways: Phase I's 10-way vs. reference 16-way disagree, but **this disagreement cannot be independently arbitrated the way L2's was** — there is no system-reported number to break the tie, only the same confound-suspected Phase-I guess against a single literature source. Sharing scope is the one genuinely new, confident Phase-II finding at this level (see that column) |

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **Two real ARM-PMU limitations showed up on this machine that Sunbird's
  x86 run never hit — both honestly documented, not worked around:**
  1. **`LLC-loads`/`LLC-load-misses` (the `llc` event group) report
     `<not supported>` at every level, every run** — confirmed directly with
     a standalone `perf stat` check before concluding this was a pipeline
     bug: this armv8_pmuv3 PMU's architected event list
     (`/sys/bus/event_source/devices/armv8_pmuv3_0/events/`) has no
     LLC-scoped event, generic or raw, that perf's `LLC-loads` alias can map
     to (it does expose raw `l3d_cache`/`l3d_cache_refill` events, but perf
     does not alias those to the generic `LLC-loads` name on this PMU driver).
     `summarize_pmu.py` records this via the `notes` column exactly as
     designed — a real, machine-specific limitation, not a script defect.
  2. **The generic `cache-references`/`cache-misses` group IS counted, but
     tracks `L1-dcache-loads`/`L1-dcache-load-misses` almost exactly at every
     footprint tested** (`cache_miss_rate` vs. `l1_miss_rate`: 0.218%/0.203%
     at L1, 7.713%/7.716% at L2, 5.497%/5.504% at LLC — agreeing to within
     0.01–0.02 percentage points every time) — i.e. on this PMU, "generic
     cache events" are not a distinct LLC-scope signal the way they
     functioned on Sunbird's table (where `cache_miss_rate`/`llc_miss_rate`
     were explicitly used as "the cleaner LLC-scope signal"). This is why
     the LLC row's miss-rate corroboration reads *lower* than L2's — a
     genuine capacity-scoped metric should climb, not fall, between those
     two footprints; here it can't, because the metric being read is
     effectively still an L1 signal. **Do not read this machine's
     `cache_miss_rate` column as evidence about LLC behavior specifically.**
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — same caveat as
  Sunbird's table: they also include process fork/exec, warmup passes, and
  buffer-permutation construction. At the L1/L2 footprints this stays
  roughly comparable to Phase I's own number; at the LLC footprint
  (median cycles/access ≈2096, vs. a ~1-tick/~40 ns Phase I number) it is
  **not usable as a real per-access latency**, same conclusion Sunbird's
  table reached for its own LLC row, for the same reason.
- **Sanity check (counters reading correctly):** at the LLC footprint,
  `cycles ÷ duration_time` ≈ 2.90 GHz — close to this SKU's rated 3.0 GHz
  (Ampere datasheet: "Consistent Frequency 3.0 GHz"), confirming the PMU
  counters themselves are being read correctly despite the two limitations
  above.
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/thunderbird/pmu/<level>/pmu_summary_20260913T203354Z.csv` —
  the table above cites each metric's median-of-3 value.

## Supplementary PMU evidence (earlier ad hoc pass, kept for what it adds)

Before this machine was migrated to the shared `run_pmu_verification.sh`
pipeline, an earlier session ran a **from-scratch raw-`armv8_pmuv3_0`-event
sweep across 23 working-set sizes (4 KiB–512 MiB)**, wrapping the Phase-I
`capacity` binary directly under `perf stat` with raw `l1d_cache`,
`l2d_cache`, and `l3d_cache` (+ `_refill`) events — a genuinely different
measurement from the 3-fixed-footprint pipeline above, and one that fills a
real gap the two limitations noted above leave in the table (a full sweep
doesn't depend on the generic `cache-references` alias behaving correctly,
and the raw `l3d_cache` events at least attempt to speak to LLC-scope
behavior, even though the pipeline's `LLC-loads` alias cannot). Kept as
supplementary evidence, not superseded:
- **L1D miss rate gives an exact, sharp knee between 65,536 B (0.18% miss)
  and 81,920 B (2.81% miss)** — right at 64 KiB, matching both this table's
  L1D row and the literature value.
- **L2D miss rate is a smooth, knee-free ramp** from ~0.3% (128–256 KiB)
  through ~44% (4–8 MiB) — no elbow anywhere near the reference 1 MiB size,
  independently corroborating Phase I's own "no flat L2 shelf" finding via a
  completely different measurement (full-sweep event counts, not a single
  fixed-footprint latency number).
- **L3D miss rate shows no capacity-dependent structure at all** — flat/noisy
  ~50–65% across the *entire* range, including a 4 KiB working set that
  trivially fits inside L1 alone. Combined with this table's own finding
  that the SLC doesn't appear in sysfs cache topology (§ Table 2, LLC row)
  and that perf has no `LLC-loads` alias on this PMU at all, this is now
  **three independent pieces of evidence** (raw sweep, sysfs topology, and
  this table's own generic-event aliasing finding) all pointing the same
  way: this SoC's core PMU and the OS's cache-topology reporting both treat
  the SLC as effectively invisible at the per-core level, even though it
  demonstrably exists (Ampere datasheet §2.5).
- Full detail, methodology, and plot: `data_raw/thunderbird/pmu/run_pmu_sweep.sh`,
  `data_raw/thunderbird/pmu/pmu_sweep_raw.csv.gz`,
  `data_processed/thunderbird/pmu/pmu_sweep_summary.csv`,
  `data_processed/thunderbird/pmu/plots/pmu_miss_rate_sweep.{png,pdf}`.

## Where the underlying data lives

- Phase II PMU raw (canonical pipeline): `data_raw/thunderbird/pmu/{L1,L2,LLC}/*_perfstat_*.csv`
  (perf stat output) and `*_bench_*.csv` (cache_bench's own CSV from the same
  invocation).
- Phase II PMU processed (canonical pipeline): `data_processed/thunderbird/pmu/{L1,L2,LLC}/pmu_summary_20260913T203354Z.csv`.
- Phase II system-reported: `data_raw/thunderbird/pmu/system_reported_cache_info.txt`.
- Phase II supplementary sweep: see § above.
- Phase I (unchanged): `data_processed/thunderbird/FINAL_CACHE_TABLE.md`,
  `data_raw/thunderbird/README.md`.
- Literature: Ampere Altra Datasheet Rev A1 v1.30 §2.3–2.5 p. 9; Arm Neoverse
  N1 Core TRM r3p1 §A2.1.2/A6.4/A7.1 (see citations above) — local copies of
  the fetched PDFs are not committed to this repo (external references only).
