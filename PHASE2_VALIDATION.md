# Phase II — Counter- and Literature-Based Validation (Table 2, per processor)

**Started 2026-09-13, after tagging `phase1-timing-only` at commit `7be6dac`.**
This file holds each machine's required post-Phase-I validation table (PROJECT 1.pdf
§Phase II, Table 2). Per the assignment: "Keep your measured values and the
published/reference values in separate columns" and "The reference value validates
your experiment; it does not replace it." Columns:

- **Measured** (size/ways/latency) = the frozen Phase-I timing-only number, unchanged
  from `CAPACITY_RESULTS.md`/that machine's `data_raw/<machine>/README.md`. Never
  edited in light of Phase II evidence — if Phase II contradicts it, that goes in the
  Agreement column, not a rewrite of the Measured column.
- **PMU** (this file's own addition, beyond the assignment's minimum 8 columns) =
  hardware-counter evidence collected this phase, kept visually separate from both
  Measured and Reference.
- **Reference value** = published (vendor datasheet / architectural TRM) or
  system-reported (`lscpu`/sysfs) value, cited with exact source + section/page.
  System-reported topology counts as Phase-II-permitted evidence per the assignment
  ("you may now inspect ... system-reported cache information") but is kept distinct
  from vendor-published numbers since the OS's report itself isn't a citation trail
  back to silicon.
- **Agreement** = how Measured compares to Reference, with PMU noted as
  corroborating/not corroborating where it's able to speak to that row at all.

---

## Thunderbird — Ampere Altra Q80-30 (Arm Neoverse N1), aarch64, 2020, 7 nm

Machine identification, timer method, and all Phase-I run commands/seeds:
`data_raw/thunderbird/README.md`. Phase-I timing values below are unchanged from
that file and from `CAPACITY_RESULTS.md`.

### Sources used this phase
1. **Ampere® Altra® 64-Bit Multi-Core Processor Datasheet**, Rev A1, Document Issue
   1.30, 2022-07-28 (Ampere Computing). §2.3.1 "L1 Data Cache" (p.9), §2.3.2 "L1
   Instruction Cache" (p.9), §2.4 "L2 Cache Features" (p.9), §2.5 "System Level Cache
   (SLC) Features" (p.9), §2.1 "Processor Complex (PCP)". SKU-specific — describes
   Ampere's actual configuration choices, not just the architected options.
2. **Arm® Neoverse™ N1 Core Technical Reference Manual**, revision r3p1, document
   100616_0301_01_en (Arm Limited). §A2.1.2 "L1 data memory system" / "L2 memory
   system" (p.A2-36), §A6.4 "L1 data memory system" (p.A6-78), §A7.1 "About the L2
   memory system" (p.A7-102). Architectural — describes what the core IP supports
   (including L2's 256/512/1024 KiB configurability); confirms Ampere's SKU choices
   sit inside the documented envelope. **Does not cover the SLC** — the SLC is a
   mesh/DSU-level component outside this per-core manual's scope, so the SLC row
   below is corroborated by source 1 only, not independently cross-checked by 2.
3. **System-reported** (Phase II only): `lscpu -C`, `/sys/devices/system/cpu/cpu3/cache/index*/*`
   — captured 2026-09-13, saved at `data_raw/thunderbird/pmu/sysfs_cache_topology_20260913.txt`.
4. **PMU counters** (Phase II): `perf stat` with raw `armv8_pmuv3_0` events
   (`l1d_cache[_refill]`, `l2d_cache[_refill]`, `l3d_cache[_refill]`, generic
   `cache-references`/`cache-misses`), swept across the same working-set sizes as
   Phase I's capacity experiment. Full methodology below the table.

### Table 2

| Level | Measured size (Phase I) | Measured ways (Phase I) | Derived sets | Line | Measured latency (Phase I) | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| **L1D** | ~64–75 KiB (eyeballed plateau edge, no automatic detector — see caveat in `data_raw/thunderbird/README.md`) | **4-way**, clean single knee, reproducible across base + 2 repeat seeds | 256 sets (65,536 / (4×64)) — using reference line size, not independently measured | **not measured** — `line_size/` experiment never run on this machine (Phase I gap, left blank per team decision rather than invented); system-reported + literature both give 64 B | 0.085 ticks/access median (1 KiB–57 KiB flat region) = **3.4 ns/access** (CNTFRQ_EL0=25 MHz → 40 ns/tick) | Private per core (`shared_cpu_list`=single CPU) | **64 KiB, 4-way, 64 B line** — Ampere datasheet §2.3.1 p.9; independently corroborated by Arm TRM §A2.1.2/A6.4 (PIPT, 4-way, 64 B lines) | **Size: exact** — PMU knee below lands the boundary precisely at 64 KiB (see PMU section). **Ways: exact** (4 = 4). **Line/sets: not Phase-I-measured**, but system-reported (sysfs) and both literature sources agree at 64 B — 2-way corroborated, not 3-way. **Latency: no published reference exists** (neither source states load-use cycles) — Phase-I number stands uncorroborated by literature, only by the machine's own repeat sanity-check already in the README. |
| **L2** | **No confirmed boundary** — continuous ramp ~75 KiB–8 MiB, no flat shelf (Phase I's own documented finding); ~1 MiB used only as an *assumed* associativity stride, never independently confirmed as a real boundary | Phase I associativity at 1,048,576 B reports **11-way (base) / 12-way (both repeats)** — flagged in `data_raw/thunderbird/README.md` and `CLAUDE.md` as confound-suspected (same universal ~10–12-way wall recurring across every large-stride candidate on 5 machines / 2 architectures) | 2048 sets (1,048,576 / (8×64)) — using reference values; matches sysfs `number_of_sets`=2048 exactly | not measured; system-reported + literature = 64 B | **Not available** — Phase I explicitly found "a long, shallow, continuous ramp... no flat shelf" through this region, so no clean latency number exists to report (left blank rather than invented, per team decision) | Private per core (`shared_cpu_list`=single CPU; datasheet: "dedicated low-latency per-core 1 MB L2 cache") | **1024 KiB (1 MiB), 8-way, 64 B line, 2048 sets, private per-core** — Ampere datasheet §2.4 p.9 (Ampere's configuration choice); Arm TRM §A2.1.2 confirms L2 is architecturally configurable at 256/512/1024 KiB, 8-way — Ampere selected the 1 MiB option | **Size: unconfirmed by either phase** — the 1 MiB figure matches the reference only because it was borrowed FROM the reference (`CAPACITY_RESULTS.md`), not derived independently; Phase-II PMU shows a smooth, knee-free miss-rate ramp through this region (0.3% at 128–256 KiB rising to ~44% by 4–8 MiB, no elbow at/near 1 MiB — see PMU plot), i.e. **PMU corroborates the Phase-I "no discrete boundary" finding itself**, not the specific 1 MiB number. **Ways: disagree** (measured 11–12 vs. reference 8) — Phase II literature (two independent sources agreeing on 8-way, plus sysfs's `ways_of_associativity`×`number_of_sets`×64 B = 8×2048×64 = 1,048,576 B, an internally self-consistent check) gives strong grounds to treat the Phase-I 11–12-way figure as the already-documented confound artifact, not a corrected measurement — **do not replace the Phase-I number; the disagreement itself is the Phase-II finding.** |
| **LLC (SLC)** | ~30 MiB (picked by eye from a documented **noisy, 20–65% run-to-run-spread** transition region, not a flat shelf) | Phase I associativity at 31,457,280 B reports **10-way**, reproducible across base + both repeats — but flagged (same confound signature) | 32,768 sets (33,554,432 / (16×64)) — reference-derived only; SLC has no sysfs presence to check against | not measured; not exposed in sysfs at all (see Sharing scope); no source states an SLC line size distinct from 64 B, but this is not independently confirmed | **Not available as an LLC-specific number.** The only confirmed flat plateau above the ramp region is DRAM: 2.388 ticks/access median (256 MiB–1 GiB, 3 independent runs, ~2% spread) = **95.5 ns/access** — this is DRAM latency reached *past* the SLC, not SLC hit latency, and should not be read as the LLC row's own number | **Shared across all 80 cores** (one distributed on-chip cache) — Ampere datasheet §2.5: "A 32 MB distributed on-chip cache shared between all processors." **This is a real, load-bearing correction to how Phase-I's per-core `taskset` pinning should be read for this level** — every other cache row on this machine is private-per-core, so pinning to one idle core isolates it from other users' activity; the SLC is architecturally shared machine-wide, so it *cannot* be isolated that way. This plausibly explains why Phase I's own README flags exactly this size region (not L1, not L2) as showing 20–65% run-to-run interference on a shared, multi-user machine — the noise isn't just "bad luck," it's the expected consequence of probing the one cache level this pinning strategy structurally cannot protect. | **32 MiB, 16-way, shared/distributed, "mostly exclusive with L2"** — Ampere datasheet §2.5 p.9. **Not covered by the Arm Neoverse N1 core TRM** (SLC is outside a per-core manual's scope) — this reference is SKU-specific only, one source, not cross-corroborated the way L1/L2 were. | **Size: suggestively close (~30 MiB measured vs. 32 MiB reference, ~94%)** but this is the *weakest-supported* row on the table: the Measured number came from a non-plateau, high-noise region to begin with, and Phase-II PMU **could not independently corroborate it** — the `l3d_cache`/`l3d_cache_refill` raw PMU events show **no capacity-dependent miss-rate structure at all** across the entire swept range (flat/noisy ~50–65% from a 4 KiB working set — which trivially fits in L1 alone — all the way to 512 MiB; see PMU section). That is itself informative (see below) but it means the ~30 MiB↔32 MiB agreement rests on the timing estimate and the datasheet alone, not on a 3-way check like L1's. **Ways: disagree** (10 vs. 16), same confound caveat as L2. **Sharing scope: Phase I never tested this** (single-core pinned for every run) — Phase II literature reveals the assumption implicit in that design (that pinning isolates the level under test) does not hold for this specific level. |

### PMU sweep — methodology and full results

**Script:** `data_raw/thunderbird/pmu/run_pmu_sweep.sh 3 data_raw/thunderbird/pmu/pmu_sweep_raw.csv`
(core 3, same core as every Phase-I Thunderbird run; idle-checked via `/proc/stat`
over a 2 s window before running — 96.5% idle, consistent with the Phase-I session's
own idle-core discipline). Wraps the **same Phase-I `cache_bench --experiment
capacity` binary** (one working-set size per invocation, `--min-bytes N --max-bytes N
--points-per-octave 1`, `--samples 1000000 --pattern random --seed 12345`, matching
Phase-I's own capacity-sweep parameters) under `perf stat`, sweeping 23 sizes from
4 KiB to 512 MiB — this deliberately reuses the Phase-I access pattern so the PMU
counts and the Phase-I timing numbers describe the *same* memory-access sequence,
just measured two different ways (event counts vs. latency).

**Events, split into 3 `perf stat` groups per size** (6 general-purpose PMUv3
counters on this core; 4 events per group avoids multiplexing):
- Group A: `armv8_pmuv3_0/l1d_cache/`, `.../l1d_cache_refill/`, `.../l2d_cache/`, `.../l2d_cache_refill/`
- Group B: `.../l3d_cache/`, `.../l3d_cache_refill/`, `.../mem_access/`, `.../bus_access/`
- Group C: generic `cache-references`, `cache-misses` (perf's own event mapping, as a cross-check)

Exact semantics (from `/sys/bus/event_source/devices/armv8_pmuv3_0/events/`, saved
at `data_raw/thunderbird/pmu/perf_list_20260913.txt`): these are the architected
ARMv8 PMUv3 cache events — `l{1,2,3}d_cache` counts attributable L1D/L2D/L3D cache
accesses, `l{1,2,3}d_cache_refill` counts linefills (i.e. misses) at that level. Raw
data: `data_raw/thunderbird/pmu/pmu_sweep_raw.csv`; processed miss-rate summary:
`data_processed/thunderbird/pmu/pmu_sweep_summary.csv`; plot:
`data_processed/thunderbird/pmu/plots/pmu_miss_rate_sweep.{png,pdf}`.

**Findings:**
1. **L1D miss rate gives an exact, sharp knee between 65,536 B (0.18% miss) and
   81,920 B (2.81% miss)** — i.e. right at 64 KiB, matching the reference size
   exactly and landing precisely where Phase I's own eyeballed "64–75 KiB" edge
   said it would. This is the cleanest 3-way agreement on the table (Phase-I timing,
   Phase-II PMU, and literature/system-reported all converge on 64 KiB).
2. **L2D miss rate is a smooth, knee-free ramp** from ~0.3% (128–256 KiB) through
   ~44% (4–8 MiB and beyond) — no elbow anywhere near the reference's 1 MiB size.
   This matches Phase I's own "no flat shelf, continuous ramp" finding via a
   completely independent measurement (event counts, not latency) — strong
   corroboration of *that* qualitative finding, even though it doesn't pin down a
   number.
3. **L3D miss rate shows no capacity-dependent structure whatsoever** — it sits at
   50–65% (noisily) across the *entire* swept range, including a 4 KiB working set
   that fits trivially inside L1 alone, where a real cache level's miss rate should
   read near 0%. Combined with the SLC not being exposed anywhere in the OS-reported
   cache topology (§ below), this is reasonably strong evidence that the `l3d_cache`/
   `l3d_cache_refill` raw PMU events on this SoC either aren't wired to the actual
   SLC the way `l1d_cache`/`l2d_cache` are wired to the real L1/L2, or count
   something else entirely (e.g. a fixed-ratio proxy unrelated to real hit/miss
   outcomes) — **not proof of which, just proof these specific counters cannot be
   used to validate the ~30 MiB SLC boundary on this machine.** Flagged as an open
   question, not resolved further this session.
4. **System-reported cache topology (`lscpu -C`, sysfs) lists only L1d/L1i/L2 —
   no L3 appears at all**, even though the SLC demonstrably exists per the Ampere
   datasheet. This is architecturally expected for Ampere Altra (the SLC is a
   distributed mesh-level structure, not one of the per-core cache instances the
   Linux cache-topology sysfs interface enumerates) and is itself corroborating
   context for finding 3 above — if the kernel's own topology view doesn't resolve
   the SLC as a normal cache level, it's plausible the core PMU's L3 events don't
   either.

### Known limitations of this pass (flagged, not resolved)
- No PMU-based line-size measurement was attempted (would require a stride sweep
  analogous to `line_size/`, not attempted this session — the team decided to leave
  Phase-I's own line-size gap unfilled rather than invent a number, and that
  decision carries over to Phase II: line size here rests on system-reported +
  literature agreement only, never cross-checked against this machine's own timing
  or counter data).
- The L2/LLC associativity disagreement (11–12/10 measured vs. 8/16 reference) is
  documented here, not re-investigated — `CLAUDE.md`'s associativity section already
  has an extensive, unresolved root-cause discussion (DTLB aliasing vs. TLB/
  page-walk-cache hypotheses) that this Phase-II pass does not settle. What Phase II
  *does* add: independent literature confirmation of what the correct L2 answer
  almost certainly is (8-way), strengthening the case that the confound hypothesis
  is right rather than merely plausible.
- Only Thunderbird has a Phase II table so far — this file is structured to have a
  new `## <Machine>` section appended per machine as Phase II proceeds elsewhere,
  mirroring `CAPACITY_RESULTS.md`'s per-machine section convention.
