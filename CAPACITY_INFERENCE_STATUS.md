# Per-Level Capacity Inference Status (gate for associativity L2/LLC work)

Consolidated from each machine's own `data_raw/<machine>/README.md` capacity
section. Purpose: `scripts/run_associativity_full.sh` needs one concrete
`cache_bytes` value per level to use as the node-to-node stride (see
`main_code/common/associativity.h`) — a wrong value either produces a
meaningless result or, worse, one that *looks* clean by accident. This table
says, per machine and level, whether a value exists and how much to trust
it. **Re-derive from the per-machine READMEs before trusting this after any
new capacity work lands — this file is a snapshot, not a live view.**

**2026-09-10 update:** this session (running on `sunbird.ece.ncsu.edu`) is
git-synced with every other machine's already-collected capacity data — the
raw/processed CSVs for all 8 machines are present in this checkout even
though this session cannot run new benchmarks anywhere except Sunbird
itself. A full pass through that already-committed data (no new benchmark
runs except where explicitly noted) turned up a major finding and two
corrections — see below.

## Headline finding: L1 = 32,768 bytes (32 KiB) on 6 of 7 x86 machines checked

Every x86 machine's coarse capacity sweep, re-examined from 1 KiB through at
least a few hundred KiB, shows the same signature: a flat random-pattern
plateau from 1,024 B through 27,552–30,048 B, a sharp ramp onset at
32,768 B, and a clearly-established climb by 35,728 B — with the
sequential-pattern control staying flat across that same pair of points
(ruling out a benchmark artifact). This was invisible to
`detect_cache_hierarchy.py`'s default thresholds on every machine except
Sunbird (where it was already hand-confirmed via a clean associativity
knee) — the same absolute-threshold blindness already documented on
Thunderbird (`--min-abs-ticks 3.0` requires a single adjacent-point jump
that large; a flat-then-ramp region can be genuine without any single step
being that big). Re-running the detector with `--min-abs-ticks 0.5
--rel-threshold 0.1` recovers it everywhere it was checked.

Confirmed this way (2026-09-10, from already-committed coarse data, no new
runs): **Crux, Skylark, Upgrade, Ookay, Charnwood** — all 32,768 B. Combined
with Sunbird's independently hand-confirmed 32,768 B, that's 6 of 7 x86
machines in agreement. (Thunderbird is AArch64/Neoverse-N1 and genuinely
shows a different, larger edge, ~64–75 KiB — already correctly documented,
unaffected. Artemisia's sub-48 KiB region is confounded by per-invocation
P-state/turbo bimodality — already correctly documented as unresolved,
unaffected by this pass.)

**Three corrections to prior work** (two from earlier sessions, one from
earlier in this same session), all now fixed in the respective
`data_raw/<machine>/README.md`:
- **Sunbird L2/L3**: this document originally said Sunbird's ~20 MiB
  boundary had been "upgraded to provisional-strong" from existing
  `denseB` data. That was itself wrong — the 21,757,352 B point that looked
  like a knee was an interference spike, not a real transition (this
  machine's coarse/dense sweeps are well-documented as noisy in this exact
  size range). A follow-up series of 200-400-points/octave sweeps (new
  data, run live on Sunbird this session — see that machine's README)
  computed a robust per-bin floor (minimum ticks/access, immune to
  upward-only spikes) and found the true plateau holds flat to ~26 MiB,
  with the floor itself only beginning a sustained climb after that.
  **Corrected: ~26-27 MiB**, not ~20 MiB.
- **Ookay**: previously reported "L1 = 285,864 B (279 KiB)" was wrong. The
  full ramp from 32,768 B to at least 961,544 B is one smooth continuous
  climb with no shelf anywhere in it — 285,864 B is just an ordinary point
  on that ramp. The locally-tight, low-noise measurement originally cited
  as evidence for a shelf there is consistent with either a genuine
  plateau *or* a precisely-measured point on a smooth ramp; only looking
  at the wider trend (not just the narrow dense window around the
  candidate boundary) distinguishes the two.
- **Charnwood**: same story, previously reported "L1 = 311,744 B
  (304 KiB)" was wrong for the same reason — one continuous ramp from
  32,768 B through at least 679,912 B, no shelf.

**Practical implication:** if `run_associativity_full.sh` is ever run on
Ookay or Charnwood, use **32,768**, not the old 279 KiB/304 KiB values, as
the L1 `cache_bytes` override — the old values were never real cache
boundaries and would not have produced a meaningful associativity result.

## Confidence tiers

- **HAND-CONFIRMED** — an independent downstream test validated the value
  (so far: only Sunbird L1, via a clean associativity knee).
- **PROVISIONAL** — a specific byte value is clearly supported by a
  flat-plateau-then-ramp signature in already-collected data (ideally with
  a sequential-pattern control check), but nothing downstream has
  cross-validated it yet.
- **PROVISIONAL-WEAK** — a candidate shelf is visible, but only in coarse
  (8-points/octave) data; needs a dedicated dense (48-ppo) sweep to confirm
  it's genuinely flat rather than a locally-slow stretch of one long ramp.
- **REGION-ONLY** — a flat/ramp region is identified but no single boundary
  byte value has been pinned down.
- **UNRESOLVED / CONTAMINATED** — auto-detected boundary(ies) exist but are
  flagged noisy, over-segmented, or interference-corrupted in that
  machine's own README. Do not use.
- **NOT YET COLLECTED** — no boundary-detection or region analysis has been
  done for this level at all.

## Summary table

| Machine | L1 | L2 | L3 / LLC |
|---|---|---|---|
| Sunbird | **32,768 B — HAND-CONFIRMED** (associativity knee, 0% spread, 8-way) | ~26-27 MiB — **PROVISIONAL** (robust per-bin floor, immune to this machine's known interference spikes, confirmed flat 8.4–26 MiB then a genuine sustained climb from ~26 MiB on, via 3 new 200-400-ppo sweeps run live this session; supersedes an earlier same-session ~20 MiB estimate that turned out to be measuring a single interference spike) | ~150 MiB onset — plateau itself (≥145 MiB, ~190-205 ticks/access) already confirmed genuine via multi-run repeats |
| Crux | **32,768 B — PROVISIONAL** (precise edge pinned 2026-09-10 from existing coarse data + sequential control) | UNRESOLVED (soft ramp ~64 KiB–4 MiB, no flat shelf) | UNRESOLVED discrete value (one dominant steep transition ~4–64 MiB); DRAM plateau ≥~100 MiB confirmed genuine (~245-250 ticks) |
| Skylark | **32,768 B — PROVISIONAL** (found 2026-09-10 from existing coarse data + sequential control; detector missed it, same threshold issue as Thunderbird) | ~4–16.8 MiB — **PROVISIONAL-WEAK** (new candidate shelf, 17 coarse points, 26.3-33.2 ticks, no trend; needs a 48-ppo dense sweep to confirm) | UNRESOLVED discrete value (3 close auto-boundaries 16.7-21.8 MiB, one ramp not 3 levels); DRAM plateau confirmed flat 512 MiB–2 GiB (~280 ticks) |
| Upgrade | **32,768 B — PROVISIONAL** (found 2026-09-10 from existing coarse data + sequential control) | UNRESOLVED (ramp 32 KiB–1.5 MiB); ~1.5–4.5 MiB soft near-plateau — **PROVISIONAL-WEAK**, needs a dense sweep | UNRESOLVED (noisy ~5–22 MiB transition, session-level interference between repeats, `rep2` systematically elevated at 60% of points); **DRAM region NOT flat at 256 MiB ceiling (+11.9%) — needs a genuinely new 256 MiB–1 GiB run on `upgrade` itself, not resolvable from existing data** |
| Charnwood | **32,768 B — PROVISIONAL** (corrected 2026-09-10 — old "304 KiB" value was wrong, see above) | UNRESOLVED / CONTAMINATED (1.83–11.31 MiB region, 4 boundaries, 12-157% spread from a confirmed concurrent interfering process; needs full re-run when quiet) | UNRESOLVED / CONTAMINATED (same interference); no DRAM plateau reached even by 1 GiB |
| Thunderbird | ~64-75 KiB — PROVISIONAL (eyeballed plateau edge, cross-checked against an independent timer sanity test; genuinely different from the x86 machines' 32 KiB, as expected for a different architecture) | UNRESOLVED (continuous ramp ~75 KiB–8 MiB, no flat shelf) | UNRESOLVED discrete value (dominant steep, noisy transition ~16-70 MiB); DRAM plateau confirmed flat 256 MiB–1 GiB (~2.3-2.4 ticks) |
| Ookay | **32,768 B — PROVISIONAL** (corrected 2026-09-10 — old "279 KiB" value was wrong, see above) | UNRESOLVED (the whole 32 KiB–~5.3 MiB span re-checked out to 961,544 B is one continuous ramp, no shelf; region beyond that not re-examined) | UNRESOLVED discrete value (5.3-11.9 MiB is one continuous over-segmented transition); DRAM plateau confirmed flat 256 MiB–1 GiB (~286-297 ticks, robust median-of-3) |
| Artemisia | UNRESOLVED (sub-48 KiB confounded by per-invocation P-state/turbo bimodality; re-checked 2026-09-10, unchanged — genuinely not a detector-threshold issue like the other machines) | none detected as a separate step (48–55 KiB onset through ~90 MiB is one continuous ramp on both core 20 and core 23) | ~90 MiB (94,371,840 B) plateau onset — PROVISIONAL, cross-validated between two independent cores agreeing within 0.4% |

## Bottom line / what to do next

**Settled from existing data alone (2026-09-10), no new benchmark runs:**
L1 is now PROVISIONAL-or-better on 7 of 8 machines (all x86 machines plus
Thunderbird's ARM-appropriate value); only Artemisia's L1 remains
genuinely unresolved, and that's a real hardware/measurement confound
(P-state bimodality), not a missing-data problem. Two prior L1
misidentifications (Ookay, Charnwood) were corrected.

**Settled with new live data on Sunbird (the one machine this session has
direct access to):** Sunbird's L2/L3 boundary was pinned at ~26-27 MiB via
a robust floor analysis across 3 new high-resolution sweeps, correcting
both the original ~20 MiB plot annotation and this document's own
initial (wrong) attempt to validate that annotation from existing sparse
data alone — a reminder that "locally clean-looking existing data" isn't
always enough; sometimes a targeted new sweep is what actually settles a
boundary, and re-analysis can itself need correcting.

**Still requires genuinely new data collection — cannot be resolved by
more analysis of what's already committed:**
- **Upgrade**: DRAM-region tail extension (256 MiB–1 GiB) — still climbing
  at the pipeline's default 256 MiB ceiling, exactly like every other
  machine needed before it flattened. This is the one unambiguous "go run
  the benchmark again" item.
- **Skylark**: a 48-ppo dense sweep across ~1–16 MiB to confirm or refute
  the new candidate L2/L3 shelf.
- **Upgrade** (optional): a dense sweep ~1–6 MiB to resolve its own softer
  candidate shelf, and a quiet-machine re-check of the noisy ~5–22 MiB
  region given the session-level (not per-point) interference signature
  found there.
- **Charnwood**: full re-run of the ~1.83–11.31 MiB region when the
  machine is quiet (already flagged before this pass, unchanged).

**This session can only act on Sunbird directly** (it's the machine this
checkout is running on) — collecting new data on any other machine needs a
session actually logged into that machine. Everything above this line was
achieved purely by re-analyzing already-committed CSVs.

**No level besides Sunbird L1 has an independent downstream
cross-validation yet** (e.g. a clean associativity knee matching the
assumed capacity). Before treating any PROVISIONAL/PROVISIONAL-STRONG
value as final, that kind of cross-check — or an explicit decision to
accept it as "provisional" in the report — is still needed.
