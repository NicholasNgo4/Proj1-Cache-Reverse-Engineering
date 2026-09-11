#!/usr/bin/env python3
"""Plot the required "family of curves" line-size evidence (homework
PROJECT 1.pdf, Figure 3 / "Example B") from one or more processed summary
CSVs produced by summarize_raw.py on --experiment line_size_family raw data.

Each input summary holds one (candidate stride, pattern) sweep of median
ticks/access vs. working-set footprint (see
main_code/common/line_size.h for why footprint is the swept axis
here, not stride). This script overlays all candidate strides' curves
together -- that overlay IS the family of curves -- and applies a simple
elbow detector to each curve to turn the overlay into a concrete line-size
inference instead of leaving it to eyeballing:

  1. line_size_family_curve.{pdf,png} -- median ticks/access vs. footprint,
     one line per candidate stride (random pattern; sequential drawn faint/
     dashed alongside as the prefetcher-sanity control), with an IQR band.
     Each curve's detected elbow (smallest footprint after which the curve
     never again drops below its own final, settled plateau -- see
     detect_elbow's docstring for why this is anchored to the END of the
     curve rather than a fragile early baseline) is marked. Curves
     for strides <= the true line size should share essentially the same
     elbow (multiple nodes legitimately pack into one line, so real cache
     pressure only depends on total footprint, independent of stride);
     curves for strides > the true line size have their elbow pushed out to
     a larger footprint, because each node then occupies its own line. The
     smallest candidate stride whose elbow separates from the shared
     baseline is reported as the line-size estimate.
  2. line_size_family_boxplots.{pdf,png} -- box-and-whisker evidence at
     representative footprints (immediately below/at/above the smallest
     stride's detected elbow), one box per candidate stride at each
     footprint, so the distribution behind the family-of-curves inference
     is visible, not just medians.

Usage:
    python3 scripts/plot_line_size_family.py \\
        data_processed/sunbird/line_size/family_8_random_summary.csv \\
        data_processed/sunbird/line_size/family_8_sequential_summary.csv \\
        data_processed/sunbird/line_size/family_16_random_summary.csv \\
        ... \\
        -o data_processed/sunbird/line_size/plots --machine sunbird
"""
import argparse
import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

REQUIRED_COLS = {"footprint_bytes", "stride_bytes", "pattern", "median", "q1", "q3",
                  "p5", "p95", "n", "n_outliers"}


def load_summaries(paths, want_offset=0):
    """Returns {pattern: {stride_bytes: {footprint_bytes: row_dict}}}, restricted
    to rows whose offset_bytes == want_offset.

    Older summaries (from before offset_bytes existed) have no such column --
    those are treated as offset_bytes=0, matching the default baseline. This
    filter exists so summaries from run_line_size.sh (which
    deliberately mixes several offsets in one directory) can't get silently
    merged into one curve here: two rows sharing (pattern, stride, footprint)
    but differing only in offset_bytes describe genuinely different node
    layouts, and letting one clobber the other in the dict below would produce
    a plot that looks clean while quietly hiding an alignment effect. Use
    plot_line_size_offset.py for the cross-offset comparison instead.
    """
    out = {}
    for path in paths:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or not REQUIRED_COLS.issubset(reader.fieldnames):
                missing = REQUIRED_COLS - set(reader.fieldnames or [])
                raise ValueError(f"{path}: missing expected column(s) {missing} -- "
                                 f"is this a line_size_family summary from summarize_raw.py?")
            has_offset_col = "offset_bytes" in reader.fieldnames
            for row in reader:
                offset = int(float(row["offset_bytes"])) if has_offset_col else 0
                if offset != want_offset:
                    continue
                pattern = row["pattern"]
                stride = int(float(row["stride_bytes"]))
                footprint = int(float(row["footprint_bytes"]))
                out.setdefault(pattern, {}).setdefault(stride, {})[footprint] = row
    if not out:
        raise ValueError(f"no rows with offset_bytes={want_offset} found across "
                          f"{len(paths)} summary file(s) -- pass --offset to select "
                          f"a different one")
    return out


def human_bytes(n):
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):g} MiB"
    if n >= 1024:
        return f"{n / 1024:g} KiB"
    return f"{n} B"


def style_axes(ax):
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(1.2)
        ax.spines[side].set_color("black")
    ax.tick_params(width=1.1, labelsize=10)


def detect_elbow(points, plateau_frac=0.85, plateau_n=3, min_rise_ratio=1.15):
    """points: sorted list of (footprint_bytes, median). Returns the smallest
    footprint_bytes after which the curve NEVER AGAIN drops below plateau_frac
    times the curve's own FINAL plateau (median of its last plateau_n points),
    or None if the curve never meaningfully rises above its own starting level.

    This replaces an earlier version that anchored to a 2-point LOW-footprint
    baseline and returned the first point to cross rise_ratio*baseline,
    confirmed by only the next 2 points. That was fragile in two ways this
    project hit in practice (see data_raw/<machine>/README.md line_size/
    section): (1) a single noisy early point could throw off the 2-point
    baseline itself, and (2) a transient spike/dip anywhere in the middle of
    a curve could satisfy "confirmed by the next 2 points" without the curve
    having actually settled -- both produced elbow estimates that visually
    contradicted the plotted curves (e.g. picking up a residual artifact from
    an adjacent cache level's own boundary bleeding into this level's window,
    or a stride's slow continuous ramp crossing the threshold at an
    essentially arbitrary point rather than at a genuine step).

    Anchoring to the curve's OWN final, best-established plateau instead is
    far more robust: any single noisy point earlier in the curve (a spike OR
    a dip) cannot fool this, because the returned footprint must hold for
    EVERY remaining point through the end of the sweep, not just a couple
    immediately following it. min_rise_ratio guards against reporting an
    "elbow" for a curve that is essentially flat throughout (no real
    transition to detect)."""
    if len(points) < plateau_n + 2:
        return None
    tail_vals = sorted(m for _, m in points[-plateau_n:])
    plateau = tail_vals[len(tail_vals) // 2]
    if plateau <= 0:
        return None
    head = points[0][1]
    if plateau < head * min_rise_ratio:
        return None
    threshold = plateau * plateau_frac
    for i in range(len(points)):
        if all(m >= threshold for _, m in points[i:]):
            return points[i][0]
    return None


STRIDE_MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]


def plot_curve(by_pattern, machine, out_prefix, title_suffix):
    if "random" not in by_pattern:
        raise ValueError("no 'random' pattern rows found -- line_size_family always "
                          "needs the randomized curve; sequential alone cannot show a "
                          "real line-size effect (a stride prefetcher hides it)")

    strides = sorted(by_pattern["random"].keys())
    cmap = cm.get_cmap("viridis", max(len(strides), 2))

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    elbows = {}
    for i, stride in enumerate(strides):
        color = cmap(i)
        marker = STRIDE_MARKERS[i % len(STRIDE_MARKERS)]

        rows = by_pattern["random"][stride]
        pts = sorted((fp, float(r["median"]), float(r["q1"]), float(r["q3"]))
                     for fp, r in rows.items())
        xs = [p[0] for p in pts]
        med = [p[1] for p in pts]
        q1 = [p[2] for p in pts]
        q3 = [p[3] for p in pts]
        ax.fill_between(xs, q1, q3, color=color, alpha=0.12, linewidth=0)
        ax.plot(xs, med, color=color, marker=marker, markersize=4, linewidth=1.8,
                 label=f"{human_bytes(stride)} stride (random)")

        elbow = detect_elbow([(p[0], p[1]) for p in pts])
        elbows[stride] = elbow
        if elbow is not None:
            elbow_med = dict(zip(xs, med))[elbow]
            ax.scatter([elbow], [elbow_med], s=110, facecolors="none",
                       edgecolors=color, linewidths=2.0, zorder=5)

        if stride in by_pattern.get("sequential", {}):
            srows = by_pattern["sequential"][stride]
            spts = sorted((fp, float(r["median"])) for fp, r in srows.items())
            ax.plot([p[0] for p in spts], [p[1] for p in spts], color=color,
                     linestyle=":", linewidth=1.0, alpha=0.6)

    ax.set_xscale("log", base=2)
    ax.set_xlabel("Working-set footprint (bytes, log scale)")
    ax.set_ylabel("Median latency (timer ticks / access)")
    title = f"{machine}: line-size family of curves (dependent pointer chase)"
    if title_suffix:
        title += f"\n{title_suffix}"
    ax.set_title(title, fontsize=11)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)

    return elbows


def infer_line_size(elbows, separation_ratio=1.2):
    """elbows: {stride_bytes: elbow_footprint_or_None}, strides ascending.
    Reference = the LARGEST tested stride's own elbow. The largest stride is
    the one structurally least likely to still share a physical line with
    its neighbors, so its elbow is the most reliable single anchor for
    "definitely at or above the true line size" behavior -- unlike the
    smallest stride (used as the anchor in an earlier version of this
    function), which can itself legitimately BE at or above the true line
    size, making it an unreliable reference.

    Returns the smallest stride whose own elbow agrees with that reference
    within separation_ratio: per this module's docstring, every stride at or
    above the true line size should settle at essentially the same footprint
    (real cache pressure then depends only on total footprint, not stride),
    while strides below the true line size pack multiple nodes per line and
    settle at a durably different footprint. separation_ratio=1.2 is
    deliberately set above the coarse candidate-stride grid's own log
    spacing (points_per_octave step ratio here is much larger than 1.2, but
    two elbows that are merely one measurement apart on a similarly-spaced
    footprint grid should NOT by themselves count as "separated" -- see
    data_raw/<machine>/README.md's line_size/ section for a worked example
    of two candidate strides landing within one grid step of each other by
    coincidence, which an earlier, tighter-seeming ratio treated as
    agreement when it should not have)."""
    strides = sorted(k for k, v in elbows.items() if v is not None)
    if not strides:
        return None, None, None
    reference_stride = strides[-1]
    reference_elbow = elbows[reference_stride]
    for s in strides:
        ratio = elbows[s] / reference_elbow
        if 1.0 / separation_ratio <= ratio <= separation_ratio:
            return s, reference_elbow, "agrees with largest tested stride"
    return None, reference_elbow, None


def pick_box_footprints(all_footprints, elbow):
    sorted_fps = sorted(all_footprints)
    if elbow is None:
        n = len(sorted_fps)
        step = max(1, n // 3)
        return sorted_fps[::step][:3]
    idx = min(range(len(sorted_fps)), key=lambda i: abs(sorted_fps[i] - elbow))
    picks = [sorted_fps[j] for j in (idx - 1, idx, idx + 1) if 0 <= j < len(sorted_fps)]
    seen = set()
    return [p for p in picks if not (p in seen or seen.add(p))]


def plot_boxplots(by_pattern, machine, out_prefix, title_suffix, elbow):
    if "random" not in by_pattern:
        return
    strides = sorted(by_pattern["random"].keys())
    all_footprints = sorted({fp for s in strides for fp in by_pattern["random"][s]})
    footprints = pick_box_footprints(all_footprints, elbow)
    if not footprints:
        print("No box-plot footprints selected; skipping.", file=sys.stderr)
        return

    fig, axes = plt.subplots(1, len(footprints), figsize=(3.2 * len(footprints), 4.5),
                              sharey=True)
    if len(footprints) == 1:
        axes = [axes]

    cmap = cm.get_cmap("viridis", max(len(strides), 2))
    for ax, fp in zip(axes, footprints):
        box_data, labels, colors = [], [], []
        for i, stride in enumerate(strides):
            row = by_pattern["random"][stride].get(fp)
            if row is None:
                continue
            q1, med, q3 = float(row["q1"]), float(row["median"]), float(row["q3"])
            p5, p95 = float(row["p5"]), float(row["p95"])
            box_data.append(dict(med=med, q1=q1, q3=q3, whislo=p5, whishi=p95))
            labels.append(human_bytes(stride))
            colors.append(cmap(i))

        bp = ax.bxp(box_data, showfliers=False, patch_artist=True)
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.5)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        tag = ""
        if elbow is not None:
            if fp < elbow:
                tag = " (below baseline elbow)"
            elif fp == elbow:
                tag = " (at baseline elbow)"
            else:
                tag = " (above baseline elbow)"
        ax.set_title(f"{human_bytes(fp)}{tag}", fontsize=9)
        style_axes(ax)

    axes[0].set_ylabel("Latency (timer ticks / access)")
    title = f"{machine}: line-size family box plots by candidate stride"
    if title_suffix:
        title += f"\n{title_suffix}"
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(f"{out_prefix}.pdf")
    fig.savefig(f"{out_prefix}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_prefix}.pdf and .png", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summaries", nargs="+")
    ap.add_argument("-o", "--output-dir", required=True)
    ap.add_argument("--machine", required=True)
    ap.add_argument("--title-suffix", default="")
    ap.add_argument("--offset", type=int, default=0,
                     help="offset_bytes to plot when summaries contain more than one "
                          "(default 0, the baseline alignment)")
    ap.add_argument("--estimate-out", default=None,
                     help="if given, write the inferred line-size estimate (an integer, "
                          "or the literal 'none' if no stride separated) to this file -- "
                          "lets a driving shell script consume the estimate without "
                          "parsing stderr diagnostics")
    args = ap.parse_args()

    by_pattern = load_summaries(args.summaries, want_offset=args.offset)
    elbows = plot_curve(by_pattern, args.machine,
                         f"{args.output_dir}/line_size_family_curve", args.title_suffix)

    est_stride, reference_elbow, note = infer_line_size(elbows)
    print(f"-- per-stride elbow (bytes): "
          f"{{{', '.join(f'{s}B: {e}' for s, e in sorted(elbows.items()))}}}",
          file=sys.stderr)
    if est_stride is not None:
        print(f"-- line-size estimate: smallest candidate stride whose elbow "
              f"{note} (~{reference_elbow} bytes) is {est_stride}B -- see "
              f"infer_line_size's docstring caveat on the fixed grid resolution "
              f"before citing this as a clean line-size number on its own",
              file=sys.stderr)
    else:
        print("-- no candidate stride's elbow agreed with the largest tested "
              "stride's within the swept footprint range -- either every tested "
              "stride is below the true line size, or the footprint ceiling "
              "needs raising", file=sys.stderr)

    plot_boxplots(by_pattern, args.machine,
                  f"{args.output_dir}/line_size_family_boxplots", args.title_suffix,
                  est_stride and elbows[est_stride])

    if args.estimate_out:
        with open(args.estimate_out, "w") as f:
            f.write(str(est_stride) if est_stride is not None else "none")


if __name__ == "__main__":
    main()
