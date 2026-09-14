# Phase II Validation Table — Artemisia (2026-09-14)

Per `PROJECT 1.pdf`'s Table 2 requirement: a compact post-Phase-I validation
table with measured size/ways/sets/line/latency/sharing-scope columns kept
**separate** from the cited reference/literature value and the Agreement
verdict. This file only exists because Phase I is now frozen and tagged
(`phase1-timing-only`, per `README.md`'s Phase Discipline) — nothing here
touches or overwrites `FINAL_CACHE_TABLE.md`, which remains the frozen,
timing-only Phase-I record. Uses the same canonical pipeline and table
format Sunbird's session established and Thunderbird's session standardized
on (see `CLAUDE.md`'s "Phase II" subsection) — no format deviations.

**Four independent sources feed this table, kept distinguishable in every
cell:**
1. **Phase I (timing-only)** — carried over read-only from
   `data_processed/artemisia/FINAL_CACHE_TABLE.md`.
2. **Phase II / PMU** — this session's own `perf stat` hardware-counter
   measurements (`scripts/run_pmu_verification.sh artemisia 1
   L1:49152,L2:2097152,LLC:31457280`, core 1, base_seed=12345 + 2 repeats,
   1,000,000 samples/run, timestamp `20260914T003056Z`). Raw:
   `data_raw/artemisia/pmu/<level>/`. Summaries:
   `data_processed/artemisia/pmu/<level>/pmu_summary_20260914T003056Z.csv`.
3. **Phase II / system-reported** — `lscpu --caches`/`lscpu` and
   `/sys/devices/system/cpu/{cpu0,cpu1}/cache/index*/*`, saved verbatim in
   `data_raw/artemisia/pmu/system_reported_cache_info.txt` (collected
   2026-09-14T00:31:34Z).
4. **Reference (vendor spec + literature)** — this CPU (Sapphire Rapids,
   Golden Cove cores) postdates Agner Fog's published microarchitecture
   table, so per `CLAUDE.md`'s Phase II guidance this uses vendor docs
   supplemented by Chips and Cheese where a field isn't published in the
   vendor spec, each cited by exact URL:
   - **Intel ARK** — [Intel® Xeon® Gold 5420+ Processor (52.5M Cache, 2.00
     GHz) — Product Specifications](https://www.intel.com/content/www/us/en/products/sku/232381/intel-xeon-gold-5420-processor-52-5m-cache-2-00-ghz/specifications.html)
     (SKU 232381, this exact CPU model) — states L1 Data Cache "28 x 48 KB",
     L2 Cache "28 x 2 MB", L3 Cache "52.5 MB". No associativity, latency, or
     line-size fields (Intel ARK never publishes those).
   - **Chips and Cheese, "Sapphire Rapids: Golden Cove Hits Servers"**,
     Chester Lam, published 2023-03-12
     (https://chipsandcheese.com/p/a-peek-at-sapphire-rapids) — states a
     "16-cycle L2 latency" for Sapphire Rapids (one cycle more than client
     Golden Cove's 15, per the companion article below) and an L3 latency of
     "around 125 cycles" (Intel DevCloud config) / "88 cycles" (Google Cloud
     config) / "~33 ns" / "48.5 ns effective" depending on measurement
     config and page-size — explicitly a **measured, config-dependent range
     for the Sapphire Rapids family, not a single per-SKU number** (same
     caveat Sunbird's own Agner Fog LLC citation carried). Also states a
     1.875 MB per-core L3 slice for the SPR configuration tested.
   - **Chips and Cheese, "Going Armchair Quarterback on Golden Cove's
     Caches"**, Chester Lam, published 2022-02-11
     (https://chipsandcheese.com/2022/02/11/going-armchair-quarterback-on-golden-coves-caches)
     — states "latency for this 1.2 MB cache [client Golden Cove's L2] is
     about 15 cycles", used only as corroboration for the SPR L2 number
     above (same core microarchitecture, client SKU).
   - **No literature source found with a directly-quotable L1D latency in
     cycles for Golden Cove/Sapphire Rapids** (checked 3 Chips and Cheese
     articles specifically about this microarchitecture's cache subsystem —
     each covers L1D size but only L2/L3 latency numerically in the article
     text; L1D latency appears only in unquotable chart form). Left blank
     rather than guessed — flagged as a genuine literature gap, not an
     oversight.

## Table 2

| Level | Measured size | Measured ways | Derived sets | Line | Measured latency | Sharing scope | Reference value | Agreement |
|---|---|---|---|---|---|---|---|---|
| L1D | **49,152 B (48 KiB)** — Phase I (`CAPACITY_RESULTS.md`, this machine's own capacity data has no clean plateau here but agrees the ramp starts at this size). Phase II system-reported (`lscpu --caches`, sysfs `cpu0`+`cpu1` index0, identical): 48K. **Intel ARK: "28 x 48 KB" — exact match, all 3 sources** | Phase I: **best guess 12-way**, explicitly flagged LOW confidence in `FINAL_CACHE_TABLE.md` (confound-blocked, corroborated only by a clean-but-unconfirmed transition shelf, not a hand-verified knee the way Sunbird/Upgrade/Charnwood's L1=8-way was). **Phase II system-reported: 12-way — an EXACT match to the low-confidence guess** | **64** — Phase I derived; Phase II system-reported: 64 sets, exact match | **64 B** — Phase I confirmed (2 methods, 3 reproductions, offset-invariance-confirmed); Phase II system-reported: 64 B | Phase I (original latency run, 2026-09-13, core 4): ≈9.87 ticks/access. **This session's own PMU run (core 1, same footprint): bench median 5.742 ticks/access — notably lower than the original run**, not fully explained (see caveats below; L2's own re-measurement agreed far more closely with its original number, so this isn't simply "PMU wrapper overhead" acting uniformly). Phase II/PMU: median cycles/access ≈10.42, ns/access (wall-clock) ≈6.08 — same whole-process-lifetime caveat as every other machine's PMU numbers (see caveats below). Miss-rate corroboration: L1 miss rate 0.60% (median) — consistent with a fully L1-resident working set. No literature cycle-latency number available for comparison (see sourcing note above) | Phase I: private per core (architectural guess, untested). **Phase II system-reported: `shared_cpu_list=1,57`** — private to this physical core's own 2 SMT threads only (confirms the guess, same pattern as Sunbird's L1/L2) | Intel ARK: 48 KB per core (no ways/latency/line published). No literature associativity or L1D-latency-in-cycles source found (see sourcing note) | Size/sets/line/sharing: **exact match, all sources that publish the field.** **Associativity: exact match (12-way) between Phase I's own low-confidence guess and Phase II system-report** — a genuine confirmation of a guess this team's own FINAL_CACHE_TABLE.md explicitly did not trust going in. Latency: no literature cycle-count exists to compare against; the two Phase-I-adjacent timing numbers (9.87 vs. this session's 5.74 ticks) disagree with each other more than either disagrees with anything else on this row — flagged as unresolved session-to-session noise, not a Phase-II-vs-Phase-I disagreement |
| L2 | **2,097,152 B (2 MiB)** — Phase I (`CAPACITY_RESULTS.md`), **flagged by this machine's own capacity data as NOT a confirmed boundary** (a waypoint inside one continuous ramp, not a discrete plateau — see `data_raw/artemisia/README.md`'s capacity/ section). Phase II system-reported: 2048K, exact byte match regardless. **Intel ARK: "28 x 2 MB" — exact match** | Phase I: **best guess 16-way**, explicitly flagged LOW confidence in `FINAL_CACHE_TABLE.md` (a purely structural argument — "smallest power of two at or above the L1 floor" — since the confound blocks direct measurement and no stride-scan/falsification test was run on this machine). **Phase II system-reported: 16-way — again an EXACT match to the low-confidence guess** | **2,048** — Phase I derived (matches exactly, since the guess was reverse-derived from wanting a clean set count); Phase II system-reported: 2,048 sets, exact match | **64 B** — Phase I "best-supported candidate" (offset-invariance check came back genuinely mixed, unlike L1's clean confirmation); Phase II system-reported: 64 B | Phase I (original run): ≈28.05 ticks/access. **This session's own PMU run: bench median 27.625 ticks/access — closely agrees with the original** (unlike L1 and LLC below), suggesting this level's measurement is comparatively insensitive to today's session-specific noise. Phase II/PMU: median cycles/access ≈72.17, ns/access ≈36.19 — same overhead caveat as L1. Miss-rate corroboration: L1 miss rate jumps to 7.62% (footprint now exceeds L1, as expected) while LLC-scope miss rate stays low (3.97%) — the same "everything that misses L1 is caught by L2" signature Sunbird's own L2 row showed | Phase I: private per core (guess). **Phase II system-reported: `shared_cpu_list=1,57`** — private per physical core, same as L1 | Intel ARK: 2 MB per core (no ways/latency/line published). **Chips and Cheese ("A Peek at Sapphire Rapids"): "16-cycle L2 latency"** for Sapphire Rapids specifically (this exact microarchitecture family, not a different generation the way Sunbird's Fog citation was) | Size/sets/line/sharing: **exact match, all sources that publish the field — including a byte-for-byte match to Intel's own SKU-specific spec sheet, despite Phase I's own capacity data never confirming this footprint as a genuine boundary.** **Associativity: exact match (16-way) between Phase I's own low-confidence, purely-structural guess and Phase II system-report** — striking given the guess had no direct measurement behind it at all, only "must be a power of two dividing the candidate capacity evenly." Latency: measured (~28 ticks Phase I / ~27.6 this session / ~72.2 cycles PMU-derived) reads **higher** than the literature's 16 cycles — ratio ~1.7-1.9x on the two directly-comparable RDTSC-tick numbers, consistent with the same `-O0` dependent-chase loop-overhead explanation Sunbird's and Thunderbird's sessions already documented (stack spill/reload of the chase pointer sits in the true dependency chain each iteration) |
| LLC | **~30 MiB (31,457,280 B representative)** — Phase I (`CAPACITY_RESULTS.md`), **explicitly not a confirmed boundary**: this machine's own capacity data found no discrete L2/L3 plateau at all, only one continuous ramp from ~48 KiB through ~90 MiB (see capacity/ section). **Phase II system-reported: 55,050,240 B exactly (57,344 sets × 15 ways × 64 B = 52.5 MiB `ONE-SIZE` per socket; 105 MiB `ALL-SIZE` across both sockets). Intel ARK independently states "52.5 MB" for this exact SKU — both agree, and both disagree with Phase I's representative value by a factor of ~1.75x** | Phase I: **best guess 16-way** presented as a point estimate with an explicitly "equally plausible" 8-way alternative — the weakest-evidenced associativity guess on this machine's whole Phase I table (LOW confidence, no discriminating evidence between the two candidates). **Phase II system-reported: 15-way — matches neither guess exactly, but sits far closer to 16 than to 8** | Phase I: 30,720 (at the guessed 16-way, on the guessed ~30 MiB capacity — internally consistent but resting on two unconfirmed numbers). **Phase II system-reported: 57,344** (exact integer, from the real 52.5 MiB capacity and real 15-way) | **64 B** — Phase I carried over as a default (this machine's own line_size/ section found no line-size-detectable signal at all at this footprint, after 11 independent attempts — not a machine-specific measurement at this level). Phase II system-reported: 64 B, matches the carried-over default | Phase I (original latency run, 2026-09-13, core 4): ≈94.38 ticks/access. **This session's own PMU run (core 1): bench median 237.724 ticks/access — ~2.5x the original number**, the largest session-to-session discrepancy on this table (see caveats below — most likely explained by a concurrent same-socket process, not a Phase-I-vs-Phase-II disagreement). Phase II/PMU: median cycles/access ≈3142.6, ns/access ≈1575.5 — **NOT usable as an absolute latency number**, same whole-process-lifetime caveat as Sunbird's own LLC row, amplified further here by this run's own contention (see below). Miss-rate corroboration: `cache_miss_rate` jumps from ~0.13-0.16% at the L1/L2 footprints to **53.96%** here — a much larger jump than Sunbird's equivalent (~11-14%), plausibly inflated by real contention on top of a genuine LLC-crossing signal (see caveats) | Phase I: shared across cores/socket (architectural guess). **Phase II system-reported: `shared_cpu_list=0-27,56-83`** — confirms and quantifies: shared across the entire socket (28 physical cores × 2 SMT threads = 56 logical CPUs), same pattern as Sunbird's own LLC | Intel ARK: 52.5 MB total, matching system-report exactly (independent triple-source agreement on size). **Chips and Cheese ("A Peek at Sapphire Rapids"): per-core L3 slice "1.875 MB" for the tested SPR configuration** — this machine's own 52.5 MiB / 28 cores = 1.875 MiB per core, an exact match; latency "around 125 cycles" (DevCloud config) / "88 cycles" (Google Cloud config) / "~33-48.5 ns", explicitly config-dependent, not one canonical number, same "family-wide range" caveat as Sunbird's Fog citation | **Size: a real, informative disagreement, resolved in favor of Phase II** (system-report + Intel ARK, both 52.5 MiB, vs. Phase I's admittedly-unconfirmed ~30 MiB representative value) — this is the first machine in this project where the LLC *size* itself, not just associativity, disagrees between Phase I and Phase II; it directly explains why this machine's own capacity sweep never found a clean plateau near 30 MiB (that footprint is only ~60% of the real cache, deep inside the ramp, not at an edge), and is consistent with the ~90 MiB plateau onset the capacity data did find (a real ~52.5 MiB cache plausibly needs some headroom past its nominal size before a random-probe pattern reliably evicts everything). **Ways: Phase I's 16-way point estimate is closer to system-reported 15-way than the alternative 8-way guess was** — a partial, not exact, validation. Latency: Phase I's original number (~94.38 ticks) falls inside or near the literature's cited cycle range (~88-125) for the first time on this project's Phase II tables without needing the usual `-O0`-overhead inflation explanation — worth noting as an open observation, not a settled finding, since it may just be a coincidence of an already-heavily-caveated footprint that also isn't purely LLC-resident (running below the machine's true LLC size). This session's own PMU-run measurement (237.7 ticks) is far above both Phase I's number and the literature range — attributed to this run's specific same-socket contention (see below), not a new disagreement to reconcile against literature |

## PMU measurement caveats (read before citing the "Measured latency" cells above)

- **This machine schedules all 8 requested hardware events in a single `perf
  stat` group at 100%** — confirmed by hand before running the full
  pipeline (unlike Sunbird/Thunderbird, which topped out at 2 events per
  group). The script's existing 4-separate-group design was still used
  as-is, for cross-machine file-layout and command-structure consistency
  with the already-collected Sunbird/Thunderbird data, not because this
  machine needed it.
- **`ns_per_access_perf`/`cycles_per_access` are whole-process-lifetime
  numbers divided only by the 1,000,000 *timed* samples** — same limitation
  documented in Sunbird's and Thunderbird's own validation tables: they also
  include process fork/exec, the 3 untimed warmup passes, and permutation
  construction, none of which `duration_time`/`cycles` can be separated out
  from. This makes them not directly comparable to the RDTSC-based
  `bench_avg_ticks_per_access_median` column at the L1/L2 footprints, and
  not usable as an absolute latency number at all at the LLC footprint
  (median cycles/access ≈3143 vs. a ~238-tick RDTSC-based number from the
  exact same run).
- **This run's LLC-footprint numbers (both the bench-median tick count and
  the PMU miss rate) are very likely inflated by real, concurrent
  contention, not just this project's usual measurement-overhead
  caveats.** At the time of this run, another student's own `incl_pmu`
  benchmark was actively running (~200% CPU, confirmed via `ps`/`taskset`)
  pinned to CPU 0 — a different physical core than this run's core 1, but
  the **same NUMA node/socket/LLC domain** (`shared_cpu_list=0-27,56-83`
  covers both). This machine's real LLC (52.5 MiB, confirmed independently
  by system-report and Intel's own spec sheet) is large enough that this
  run's 31.46 MiB footprint should mostly fit on its own — the observed
  53.96% generic cache-miss rate and the ~2.5x latency gap versus Phase I's
  original (presumably quieter) session at the identical footprint are both
  more consistent with active LLC pressure from that other job than with a
  clean single-tenant measurement. Not re-run at a quieter time this
  session — flagged honestly rather than either silently accepted or
  discarded, consistent with this project's established handling of
  shared-machine noise elsewhere (see this machine's own P-state/turbo
  anomaly writeups, and Charnwood's/Ookay's/Sunbird's contention writeups,
  in `data_raw/artemisia/README.md` and `CLAUDE.md`).
- **The miss-rate metrics (ratios) remain the more trustworthy Phase-II PMU
  corroboration signal** for the same reason Sunbird's table gives: a ratio
  of two counts from the same inflated process lifetime cancels most of
  that contamination. `l1_miss_rate` cleanly confirms the L1→L2 capacity
  crossing (0.60% → 7.62%) but — like Sunbird's — then plateaus rather than
  climbing further at the LLC footprint (8.79%), the same `-O0`
  stack-load-dilution effect documented there. `cache_miss_rate` (the
  LLC-scope generic event) is the cleaner signal and shows a very large
  jump exactly at the LLC footprint (~0.13-0.16% → ~54%), though per the
  caveat above this magnitude is likely contention-inflated on top of the
  genuine underlying signal.
- Raw per-run-tag numbers (base/rep1/rep2) are in
  `data_processed/artemisia/pmu/<level>/pmu_summary_20260914T003056Z.csv` —
  the table above cites each metric's median-of-3 value.

## Where the underlying data lives

- Phase II PMU raw: `data_raw/artemisia/pmu/{L1,L2,LLC}/*_perfstat_*.csv.gz`
  (perf stat output) and `*_bench_*.csv.gz` (cache_bench's own CSV from the
  same invocation).
- Phase II PMU processed:
  `data_processed/artemisia/pmu/{L1,L2,LLC}/pmu_summary_20260914T003056Z.csv`.
- Phase II system-reported: `data_raw/artemisia/pmu/system_reported_cache_info.txt`.
- Phase I (unchanged): `data_processed/artemisia/FINAL_CACHE_TABLE.md`,
  `data_raw/artemisia/README.md`.
- Vendor spec: Intel ARK SKU 232381 (URL above; no local copy committed).
- Literature: Chips and Cheese, two Chester Lam articles (URLs above; no
  local copy committed).
