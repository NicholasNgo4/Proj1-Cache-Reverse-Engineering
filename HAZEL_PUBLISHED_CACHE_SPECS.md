# Hazel Published/Vendor-Spec Cache Organization (literature reference)

**Purpose.** Hazel has no PMU access (`README.md`'s Phase Discipline / `CLAUDE.md`'s
Hazel status both note PMU scripts were deliberately not ported there), so there is no
Phase-II hardware-counter step for any of the 9 Hazel generations the way there is for
the 8 lab machines (`data_processed/<machine>/PHASE2_VALIDATION_TABLE.md`). **This file
is the literature-only substitute**: published/vendor-documented cache organization for
each exact Hazel CPU SKU, gathered from Intel ARK/KB, AMD's own product pages, Intel/AMD
Hot Chips disclosures, 7-cpu.com's CPUID/timing measurements, Chips and Cheese, Wikipedia,
ServeTheHome, NextPlatform, Microway, and academic papers (Molka et al., ICPP 2015) —
**not** from `perf`/PMU/on-node system-reported cache info (`lscpu`, sysfs), since that's
still gated by the "no PMU access on Hazel" constraint the same way `perf` itself is.
`lscpu --caches` / `/sys/.../cache/index*/*` reading IS allowed under this project's own
Phase II discipline (system-reported cache info is not a PMU query) and would upgrade
several "INFERRED" cells below to directly-measured — **not done in this pass**, flagged
as a concrete follow-up per machine below.

**Confidence tags used throughout:**
- **EXACT-SKU-CONFIRMED** — a source names this exact CPU model/SKU.
- **FAMILY-LEVEL** — confirmed for the microarchitecture/die family this SKU belongs to,
  not independently re-verified for this exact part number (same caveat this project's
  own Phase II work raised repeatedly: don't assume one number holds for every SKU).
- **INFERRED** — computed (e.g. sets = capacity ÷ (ways × line size)) or reasoned by
  analogy to a same-microarchitecture sibling core (e.g. a client Sunny Cove chip standing
  in for the Ice Lake-SP server core), not directly quoted from a source that names the
  target part.

Sourcing note: WikiChip (en.wikichip.org) and legacy AnandTech
(at-web1.www.anandtech.com) and web.archive.org were **unreachable from every research
session this pass** (connection refused at the network layer, tried direct fetch and a
proxy) — despite being this project's usual go-to for per-level breakdowns (see
`PHASE2_VALIDATION_TABLE.md` citation conventions). 7-cpu.com (CPUID/timing-measured,
same methodology this project's own `cache_bench` uses) was substituted wherever a
directly-fetchable, quotable primary source was needed for associativity/line-size/sets.

---

## 1. Intel Xeon E5-2650 v3 (Haswell-EP, 10C/20T) — `haswell` constraint

| Level | Size | Ways | Line | Sets | Inclusivity | Confidence |
|---|---|---|---|---|---|---|
| L1D | 32 KiB/core | 8-way | 64 B | 64 | — | FAMILY-LEVEL (architecturally identical across all Haswell-EP die sizes; corroborated on real Haswell-EP silicon, Xeon E5-2680 v3, by Molka et al.) |
| L2 | 256 KiB/core | 8-way | 64 B | 512 | — | FAMILY-LEVEL, same corroboration |
| L3 (LLC) | **25 MiB total** (EXACT-SKU, Intel ARK) → 2.5 MiB/core slice (10 active cores) | **20-way** | 64 B | 2048/slice (derived) | **Inclusive of L1+L2** — directly quoted, measured on real dual-socket Haswell-EP hardware | Total size EXACT-SKU-CONFIRMED; 20-way cross-checked by 3 independent sources but not one clean primary quote; inclusivity is the one directly-quoted, primary-research-backed fact in this whole file |

- Interconnect: **partitioned dual bidirectional ring** (this 10-core SKU is a cut-down
  12-core die, 2 cores/slices fused off; in default non-Cluster-on-Die mode all cores see
  one unified 25 MiB LLC across both ring segments).
- Sources: Intel product page (`www.intel.com/.../sku/81705/...`, Cache=25,600 KB); Molka,
  Hackenberg, Schöne, Nagel, *"Cache Coherence Protocol and Memory Performance of the Intel
  Haswell-EP Architecture,"* ICPP 2015 (Table II, §III-B, §VI-A — direct inclusivity quote
  and ring-topology figure, measured on real E5-2680 v3 silicon); 7-cpu.com Haswell page.

---

## 2. Intel Xeon E5-2650 v4 (Broadwell-EP, 12C/24T) — `broadwell` constraint

| Level | Size | Ways | Line | Sets | Inclusivity | Confidence |
|---|---|---|---|---|---|---|
| L1D | 32 KiB/core | 8-way | 64 B | 64 | — | FAMILY-LEVEL, measured directly on real Broadwell-EP/desktop-Broadwell silicon by 7-cpu.com |
| L2 | 256 KiB/core | 8-way | 64 B | 512 | — | same |
| L3 (LLC) | **30 MiB total** (EXACT-SKU, Intel ARK) → 2.5 MiB/core slice (12 cores) | **20-way** | 64 B | 2048/slice | **Inclusive** (reasoned from Haswell-EP generational continuity + Tom's Hardware's "any core can address any part of the cache" description — NOT a direct quote for this generation) | Total size EXACT-SKU; per-slice ways measured on sibling SKU E5-2699 v4 (55 MiB/22 cores = same 2.5 MiB/core, 20-way ratio), not E5-2650 v4 itself — same-die-family cross-check, inclusivity is the weakest cell here |

- Interconnect: **symmetric dual bidirectional ring** (Broadwell-EP's high-core-count die
  made both rings symmetric, vs. Haswell-EP's asymmetric 8+4/8+10 split).
- Sources: Intel product page (`.../sku/91767/...`, Cache=30,720 KB); 7-cpu.com Broadwell
  page (tested on i7-6900K and **E5-2699 v4**); Tom's Hardware *"Intel Xeon E5-2600 v4
  Broadwell-EP Review."*

---

## 3. Intel Xeon Gold 6130 (Skylake-SP "Purley", 16C/32T) — `skylake` constraint

| Level | Size | Ways | Line | Sets | Inclusivity | Confidence |
|---|---|---|---|---|---|---|
| L1D | 32 KiB/core | 8-way | 64 B | 64 | — | FAMILY-LEVEL, measured on sibling Skylake-X (i7-7820X, same core design) by 7-cpu.com |
| L2 | **1 MiB/core** (up from prior-gen 256 KiB — the headline Skylake-SP change) | **16-way** | 64 B | 1024 | — | Size: ServeTheHome; ways/line: measured on Skylake-X sibling by 7-cpu.com |
| L3 (LLC) | **22 MiB total** (EXACT-SKU, Intel ARK) → 1.375 MiB/core slice (16 cores, exact) | **11-way** | 64 B | 2048/slice | **Non-inclusive / victim cache** (headline architecture change) — directly quoted from ServeTheHome | Total size EXACT-SKU; 11-way measured on Skylake-X sibling AND independently corroborated by ServeTheHome/WikiChip-adjacent sources — most solidly cross-confirmed ways figure in this file despite no source naming Gold 6130 by name |

- Interconnect: **mesh** (not ring) — headline change vs. Haswell/Broadwell-EP. Each
  core's L3 slice sits at its own mesh tile with a CHA (Caching/Home Agent); address hashed
  to exactly one slice, routed across the 2D mesh. All 16 cores/32 threads address the full
  22 MiB distributed LLC. A separate **snoop filter** (2048 sets, 12-way/tile, ~1.5 MiB
  coverage) tracks L2 contents for coherence — this is NOT the L3 itself.
- Sources: Intel product page (`.../sku/120492/...`, Cache=22 MB); 7-cpu.com Skylake_X page
  (measured on i7-7820X); ServeTheHome *"Intel Xeon Scalable Processor Family
  Microarchitecture Overview"* + its L3-inclusivity sub-article + *"Things are getting
  Meshy"* (title/existence confirmed via search, full text not fetched this session).

---

## 4. Intel Xeon Gold 6226R (Cascade Lake-SP Refresh, 16C/32T) — `cascadelake` constraint

| Level | Size | Ways | Line | Sets | Inclusivity | Confidence |
|---|---|---|---|---|---|---|
| L1D | 32 KiB/core | 8-way | 64 B | 64 | — | FAMILY-LEVEL (Cascade Lake reuses the Skylake-SP core unchanged for L1/L2; Wikipedia) |
| L2 | 1 MiB/core | 16-way | 64 B | 1024 | — | Size: EXACT-SKU (Wikipedia's 6226R row, Microway); ways: FAMILY-LEVEL |
| L3 (LLC) | **22 MiB total** (EXACT-SKU, Intel ARK) → 1.375 MiB/core slice | **11-way** | 64 B | 2048/slice | **Non-inclusive / victim cache** — explicitly stated by Microway | Total size EXACT-SKU; ways FAMILY-LEVEL (same Skylake-SP-inherited figure) |

- Interconnect: **mesh**, inherited unchanged from Skylake-SP. All 16 cores/32 threads
  share the 22 MiB distributed LLC; each socket has its own independent 22 MiB LLC.
- Sources: Intel ARK (`.../sku/199347/...`, Cache=22 MB); Wikipedia *Cascade Lake* article
  (SKU table); Microway *"Detailed Specifications of the Cascade Lake-SP..."*.

---

## 5. Intel Xeon Gold 6326 (Ice Lake-SP, 16C/32T) — `icelake_6326` constraint

**This is the key disambiguation this research pass was asked to resolve.**

| Level | Size | Ways | Line | Sets | Inclusivity | Confidence |
|---|---|---|---|---|---|---|
| L1D | **48 KiB/core — confirmed, NOT 32 KiB and NOT 64 KiB** | 12-way | 64 B | 64 | — | Size: EXACT-SKU-CONFIRMED via Intel's own support KB per-generation cache table (the Gold 6326 is a mainstream "1S/2S C620A" SKU); ways: INFERRED by analogy to client Sunny Cove (7-cpu.com i7-1065G7: 48 KB/12-way/64B) — no server-specific CPUID dump found |
| L2 | **1.25 MiB/core** (up from Cascade Lake's 1 MiB) | 20-way (weak) | 64 B | 1024 (if 20-way) | — | Size: EXACT-SKU (same Intel KB table + NextPlatform independently corroborates "25% bigger at 1.25 MB/core"); ways: weakly sourced by analogy to client Willow Cove (Tiger Lake), a different microarchitecture generation that happens to share the 1.25 MiB size |
| L3 (LLC) | **24 MiB total** (EXACT-SKU, Intel ARK) → **1.5 MiB/core slice** (exact, matches Intel KB table) | 12-way (pattern-inferred) | 64 B | 2048/slice | **Non-inclusive / victim cache** (FAMILY-LEVEL, Intel KB explicitly discusses this LLC design carried 2nd–5th Gen Xeon Scalable) | Total/per-core size EXACT-SKU; ways is circumstantial (pattern: constant 2048 sets/slice carried from Cascade Lake's 11-way/1.375 MiB → 12-way/1.5 MiB gives the same 2048), not a quoted value |

- **Resolves the CLAUDE.md open question directly**: `CAPACITY_RESULTS.md`/CLAUDE.md's own
  Phase-I best guess for this machine was **65,536 B (64 KiB)**, explicitly flagged
  "best-guess only, small-size region itself noisy." Published spec says the real L1D is
  **49,152 B (48 KiB)** — the 64 KiB guess was very likely noise (or a conflation with
  Sunny Cove's reported *80 KiB total* L1 = 32 KiB I + 48 KiB D), not a real alternate
  value. **Recommend correcting the Phase-I write-up's L1 line from 64 KiB to 48 KiB**, or
  at minimum flagging the discrepancy explicitly rather than leaving 64 KiB as the
  unqualified best guess.
- Important structural note from Intel's own KB table: Ice Lake-SP's **4S/8S** SKU class
  uses a *different*, Cascade-Lake-like L1D/L2/L3 config (32 KiB/1 MiB/1.375 MiB) — a real,
  documented split within "Ice Lake-SP," not measurement error. Gold 6326 and Platinum 8358
  are both mainstream 1S/2S parts, so the 48 KiB/1.25 MiB/1.5-MiB-per-core row applies to
  both — but this is worth remembering if a future Hazel generation turns out to be a 4S/8S
  Ice Lake-SP part.
- Interconnect: mesh (continued from Skylake-SP/Cascade Lake-SP). Ice Lake-SP also
  introduces up to 4-way Sub-NUMA Clustering (SNC4) — logically partitions cores/memory
  controllers for locality, does **not** physically repartition the LLC slices.
- Sources: Intel support KB *"Intel Xeon processors" cache-by-generation table*
  (`intel.com/.../000027820/...`); Intel ARK (`.../sku/215274/...`, Cache=24 MB);
  NextPlatform *"Deep Dive Into Intel's Ice Lake Xeon SP Architecture"*; 7-cpu.com Ice Lake
  page (client, analogy only); Chips and Cheese *"Sunny Cove: Intel's Lost Generation"*
  (Willow Cove L2 analogy).
- **Concrete follow-up, not done this pass**: `lscpu --caches` / sysfs
  `ways_of_associativity` on an actual `icelake_6326` Hazel node would directly measure
  L1D/L2/L3 ways and turn the two weakest cells above (L2/L3 ways) from inferred into
  system-reported — allowed under this project's Phase II discipline (not a PMU query).

---

## 6. Intel Xeon Platinum 8358 (Ice Lake-SP, 32C/64T) — `icelake_8358` constraint

Same per-core organization as Gold 6326 above (both are mainstream 1S/2S "C620A" Ice
Lake-SP SKUs per Intel's own KB table) — only core count/total LLC differs.

| Level | Size | Ways | Line | Sets | Inclusivity | Confidence |
|---|---|---|---|---|---|---|
| L1D | **48 KiB/core** (same correction as 6326 applies here) | 12-way | 64 B | 64 | — | Size EXACT-SKU via same Intel KB table row; ways INFERRED (client analogy) |
| L2 | 1.25 MiB/core | 20-way (weak) | 64 B | 1024 | — | same sourcing as 6326 |
| L3 (LLC) | **48 MiB total** (EXACT-SKU, Intel ARK) → **1.5 MiB/core slice** (exact, 32 cores) | 12-way (pattern-inferred) | 64 B | 2048/slice | Non-inclusive / victim cache (FAMILY-LEVEL) | same confidence structure as 6326 |

- Same 64 KiB→48 KiB L1D correction applies: `CAPACITY_RESULTS.md`'s best-guess 65,536 B
  for this machine should likewise be revisited against the published 49,152 B figure.
- Interconnect: mesh; SNC4 (4 domains of 8 cores) is a documented option on this larger
  32-core die per the same Hot Chips/Tom's Hardware coverage cited for Gold 6326.
- Sources: Intel ARK (`.../sku/212282/...`, Cache=48 MB); same Intel KB table as 6326.

---

## 7. Intel Xeon Platinum 8462Y+ (Sapphire Rapids, Golden Cove, 32C/64T) — `sapphirerapids` constraint

| Level | Size | Ways | Line | Sets | Inclusivity | Confidence |
|---|---|---|---|---|---|---|
| L1D | **48 KiB/core** | **12-way** | 64 B | 64 | — | Both size and ways EXACT-SKU/microarchitecture-confirmed via Chips and Cheese ("*Sapphire Rapids: Golden Cove Hits Servers*" + "*Going Armchair Quarterback on Golden Cove's Caches*" — explicit "Golden Cove's L1D is 12-way associative") |
| L2 | **2 MiB/core** (up from Golden Cove client's 1.25 MiB) | unconfirmed | 64 B | — | private, non-inclusive | Size: Chips and Cheese, explicit quote; ways: **not found in any source this session**, do not cite a specific number |
| L3 (LLC) | **60 MiB total** (EXACT-SKU — Intel product page AND independently: 32 cores × 1.875 MiB/slice = 60 MiB exact match) | unconfirmed | 64 B | — | Monolithic sliced mesh presented as **one logical LLC shared across the whole socket** (NOT CCX-partitioned like AMD) — Chips and Cheese: "the chip appears to be set up to expose all four chiplets/tiles as a monolithic entity, with a single large L3 instance" | Total size EXACT-SKU (two independent confirmations); ways **not found**, do not cite |

- **Directly confirms this project's own Phase-I best guess**: `CLAUDE.md`'s Hazel section
  already best-guessed 49,152 B (48 KiB) for this machine's L1 from "the flat baseline
  persists well past 32KiB" timing shape, and its associativity run independently got L1's
  own "12" passing the sets-must-be-integer check exactly (48 KiB/64 B/12-way = 64 sets).
  **Both numbers now match the published spec exactly** — a clean, citable Phase-I/
  literature agreement, unlike most of this project's L2/LLC associativity confounds.
- L3 latency noted by Chips and Cheese as "an extremely high L3 latency around 33 ns" —
  worth a direct comparison against this machine's own measured LLC hit latency once
  converted to ns (see `CLAUDE.md`'s sapphirerapids hit_latency numbers).
- Sources: Chips and Cheese, *"Sapphire Rapids: Golden Cove Hits Servers"*
  (chipsandcheese.com/p/a-peek-at-sapphire-rapids); Chips and Cheese, *"Going Armchair
  Quarterback on Golden Cove's Caches"*; Intel product specifications page
  (`.../sku/232383/...`, "60M Cache").
- **Follow-up**: L2/L3 ways unconfirmed — `lscpu --caches` on the `sapphirerapids` Hazel
  node would resolve this directly (Phase-II-safe, no PMU involved).

---

## 8. AMD EPYC 9654 "Genoa" (Zen 4, 96C/192T) — `genoa` constraint

| Level | Size | Ways | Line | Inclusivity/domain | Confidence |
|---|---|---|---|---|---|
| L1D | 32 KiB/core | 8-way | 64 B | — | FAMILY-LEVEL (standard Zen 4 core IP, not independently re-verified on an EPYC-specific source this session — client and server Zen 4 cores share the same core design) |
| L2 | **1 MiB/core** | 8-way | 64 B | — | Size: VideoCardz, explicit AMD quote ("Each 'Zen 4' CPU core includes 1 MB of dedicated L2 cache"); ways: WikiChip-derived (indirect, WikiChip itself unreachable this session) |
| L3 (LLC) | **384 MiB total** (EXACT-SKU, AMD's own product page) | 16-way (UNCONFIRMED for Zen 4 specifically — inherited assumption from Zen 2/3's own 16-way CCX L3) | 64 B | **NOT one shared 384 MiB pool** — see topology below | Total size EXACT-SKU (AMD's own page); topology independently corroborated by 2 sources + exact arithmetic |

- **Critical topology finding, confirms the project's own hypothesis exactly**: EPYC 9654
  has **12 CCDs, 8 cores per CCD, one CCX per CCD** (Zen 4 changed from Zen 3's
  2-CCX-per-CCD design to 1 CCX = 1 full CCD). Each CCD/CCX has its **own private 32 MiB L3
  slice** (384 MiB ÷ 12 = exactly 32 MiB/CCD). **The L3 is shared only among that CCD's own
  8 cores — never across the whole socket.**
  - Sources: AMD's own product page
    (`amd.com/.../amd-epyc-9654.html`, "L3 Cache: 384 MB"); Tom's Hardware *"AMD 4th-Gen
    EPYC Genoa 9654, 9554, and 9374F Review"* ("Genoa's larger chip package houses up to
    twelve 5nm Core Compute Dies (CCDs), each packing eight cores"); AMD Hot Chips 2023
    Zen4/EPYC presentation slides.
- **This directly explains a Phase-I finding already in `CLAUDE.md`**: Genoa's capacity
  sweep found "LLC confirmed 33,554,432B (exactly 32 MiB) via a clean acceleration matching
  Genoa's published per-CCD L3 spec almost too precisely to be coincidental." **It was not
  a coincidence — a single-core benchmark can only ever see its own CCD's 32 MiB slice,
  never the full 384 MiB total**, so 32 MiB is in fact the *correct* number for what
  Phase I's method measures, not an underestimate of a 384 MiB total. This should be stated
  explicitly in the report rather than left as "too precise to be coincidental."
- Line size: 64 B, no deviation found for Zen 4.
- **Follow-up**: L2/L3 ways not independently confirmed for Zen 4 EPYC specifically —
  `lscpu --caches` on the `genoa` Hazel node would resolve this directly.

---

## 9. AMD EPYC 9655 "Turin" (Zen 5, 96C/192T) — `turin` constraint

Newest chip in the set (launched ~Oct 2024) — extra care taken per the research brief.

| Level | Size | Ways | Line | Inclusivity/domain | Confidence |
|---|---|---|---|---|---|
| L1D | **48 KiB/core — confirmed increase from Zen 4's 32 KiB** (50% larger) | **12-way** | 64 B | — | Primary source: AMD's own Hot Chips 2024 presentation (Cohen & Subramony, *"Next Generation 'Zen 5' Core"*) — official AMD architectural disclosure, also states 4-cycle load-to-use latency maintained despite the size increase. Independently corroborated by Chips and Cheese ("Zen 5 increases L1 data cache capacity by 50%"). Applies to the standard/non-"c" Zen 5 core used in EPYC 9655 (NOT the denser Zen5c variant used in other "Turin Dense" SKUs) |
| L2 | 1 MiB/core (unchanged from Zen 4) | **16-way** (doubled from Zen 4's 8-way) | 64 B | — | Chips and Cheese *"Discussing AMD's Zen 5 at Hot Chips 2024"* + AMD's own Hot Chips slides; doubled L2 bandwidth (64B/clock to L1I+L1D) also noted |
| L3 (LLC) | **384 MiB total** (reseller-corroborated from AMD's spec sheet — CDW/Newegg/SHI all list "384MB"; a direct WebFetch of AMD's own EPYC 9655 page timed out this session) | 16-way (moderate confidence, not traced to one primary URL) | 64 B (confirmed unchanged — explicit quote found, no evidence of a Zen 5 line-size change) | **Same CCD-partitioned domain as Genoa**: 12 CCDs × 8 cores/CCD × 32 MiB L3/CCD, NOT socket-wide | Topology very-high-confidence (multiply corroborated + exact 384÷12=32 arithmetic) but not one single AMD-9655-specific verbatim quote |

- **Resolves the project's own open question**: `CLAUDE.md`'s turin section best-guessed
  49,152 B (48 KiB) L1D from the same "flat baseline past 32 KiB" timing shape used for
  Sapphire Rapids, but explicitly noted it was "NOT independently corroborated by
  associativity here" (that run showed the same arithmetically-invalid "13" at all 3
  levels — a confound, not a real associativity signal). **AMD's own Hot Chips 2024
  disclosure now independently confirms 48 KiB/12-way for Zen 5** — the Phase-I capacity
  guess was right even though its own associativity check couldn't corroborate it.
- Same CCD-slice implication as Genoa applies: any Phase-I LLC capacity finding on this
  machine reflects one CCD's 32 MiB slice, not the 384 MiB total, unless the benchmark
  specifically spans multiple CCDs' worth of physical memory with cross-CCD contention.
- Line size 64 B — the project's own concern about a possible Zen 5 line-size change
  appears unfounded; no source found suggests any deviation from 64 B.
- Sources: AMD Hot Chips 2024 (`hc2024.hotchips.org/.../24_HC2024.AMD.Cohen.Subramony.final.pdf`);
  Chips and Cheese *"AMD's Ryzen 9950X: Zen 5 on Desktop"* (explicit CCD/L3 quote, "Each CCD
  on the 9950X has eight Zen 5 cores and 32 MB of shared L3 cache, a baseline inherited from
  Zen 3" — same CCD design used in server Turin's standard/non-c SKUs); Chips and Cheese
  *"Zen 5's Leaked Slides"*; reseller listings (CDW/Newegg/SHI) citing AMD's 384 MB spec.
- **Follow-up, not done this pass**: no primary amd.com page render was obtained for the
  EPYC 9655 SKU specifically (WebFetch timed out) — worth a direct fetch/screenshot from a
  different network path if the report needs a first-party amd.com citation for this exact
  part, and `lscpu --caches` on the `turin` node would independently confirm L3 ways.

---

## Summary table

| Machine | L1D | L2 | L3 total | L3 domain | Line |
|---|---|---|---|---|---|
| Hazel-Haswell (E5-2650 v3) | 32 KiB, 8-way | 256 KiB, 8-way | 25 MiB, 20-way, **inclusive** | whole-socket (ring) | 64 B |
| Hazel-Broadwell (E5-2650 v4) | 32 KiB, 8-way | 256 KiB, 8-way | 30 MiB, 20-way, inclusive (reasoned) | whole-socket (symmetric ring) | 64 B |
| Hazel-Skylake (Gold 6130) | 32 KiB, 8-way | 1 MiB, 16-way | 22 MiB, 11-way, **non-inclusive** | whole-socket (mesh) | 64 B |
| Hazel-Cascadelake (Gold 6226R) | 32 KiB, 8-way | 1 MiB, 16-way | 22 MiB, 11-way, non-inclusive | whole-socket (mesh) | 64 B |
| Hazel-Icelake-6326 | **48 KiB**, 12-way | 1.25 MiB, 20-way | 24 MiB, 12-way, non-inclusive | whole-socket (mesh, SNC4-capable) | 64 B |
| Hazel-Icelake-8358 | **48 KiB**, 12-way | 1.25 MiB, 20-way | 48 MiB, 12-way, non-inclusive | whole-socket (mesh, SNC4-capable) | 64 B |
| Hazel-Sapphirerapids (8462Y+) | **48 KiB**, 12-way | 2 MiB, ways unconfirmed | 60 MiB, ways unconfirmed | whole-socket (monolithic sliced mesh) | 64 B |
| Hazel-Genoa (EPYC 9654) | 32 KiB, 8-way | 1 MiB, 8-way | 384 MiB total = **12 × 32 MiB/CCD** | **per-CCD (8 cores), not socket-wide** | 64 B |
| Hazel-Turin (EPYC 9655) | **48 KiB**, 12-way | 1 MiB, 16-way | 384 MiB total = **12 × 32 MiB/CCD** | **per-CCD (8 cores), not socket-wide** | 64 B |

## Three findings worth writing into the report directly

1. **The Ice Lake-SP L1D question is resolved**: 48 KiB, not the 64 KiB Phase I
   best-guessed for icelake_6326/icelake_8358 from noisy timing data — `CAPACITY_RESULTS.md`
   and `CLAUDE.md`'s per-machine capacity write-ups for these two machines should be
   corrected or at least flagged against this published figure.
2. **Sapphire Rapids and Turin's 48 KiB L1D guesses are independently confirmed** by
   vendor disclosures (Chips and Cheese for Golden Cove, AMD's own Hot Chips 2024 slides
   for Zen 5) — a clean win for the timing-only method on two different vendors' newest
   architectures.
3. **Genoa's and Turin's "32 MiB LLC" Phase-I capacity findings are not underestimates of
   the 384 MiB total — they are the correct answer for what a single-core benchmark can
   see.** AMD's chiplet design partitions the 384 MiB total into 12 independent 32 MiB
   CCD-private slices; no single core can ever observe more than its own CCD's 32 MiB.
   This reframes Genoa's own CLAUDE.md note ("matching Genoa's published per-CCD L3 spec
   almost too precisely to be coincidental") from a suspicious coincidence into an expected,
   now-explained result.

## Not done in this pass

- No `lscpu --caches`/sysfs system-reported cache info was collected on any Hazel node —
  this is Phase-II-safe (not a PMU query) and would resolve every "INFERRED"/"unconfirmed"
  ways cell above directly. Natural next step if these numbers need to be airtight rather
  than literature-inferred.
- No comparison against each machine's own Phase-I timing numbers beyond the three
  findings above — a full per-machine table (Phase I vs. published, mirroring the lab
  machines' `PHASE2_VALIDATION_TABLE.md` format) was out of scope for this pass but would
  be the natural next document to build from this one.
