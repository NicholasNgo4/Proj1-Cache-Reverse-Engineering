#!/usr/bin/env python3
"""Plot the required Moore-style chronological cross-generation figures
(PROJECT 1.pdf Section 9, Figures 4-7 / plot list items 1-15) from the
consolidated `data_processed/master/chronological_master_table.csv`.

Every column's PRIMARY plotted value is the Phase I timing-only inferred
number -- never silently replaced by a Phase II/vendor value. Where Phase II
(PMU/system-report/literature) resolved a real disagreement, an open/hollow
marker for the Phase-II value is drawn at the same x (year) position and
tied to the solid Phase-I marker with a thin vertical connector, so the
correction is visible without overwriting the observed series feeding the
report's Moore-style trend fit and frozen Hazel prediction.

Usage:
    python3 scripts/plot_chronological_master.py \\
        data_processed/master/chronological_master_table.csv \\
        -o plots
"""
import argparse
import csv
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

VENDOR_STYLE = {
    "Intel": dict(marker="o", label="Intel x86-64"),
    "AMD": dict(marker="s", label="AMD x86-64"),
    "Ampere": dict(marker="^", label="Arm / AArch64"),
}


def load_rows(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["year"] = int(r["year"])
    rows.sort(key=lambda r: r["year"])
    return rows


def fnum(v):
    """Parses a CSV field to float, returning None for blank/NA cells
    (e.g. Thunderbird's missing LLC system-report columns) rather than
    raising or silently coercing to 0."""
    if v is None or v.strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def style_axes(ax):
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(1.2)
        ax.spines[side].set_color("black")
    ax.tick_params(width=1.1, labelsize=11)


def human_bytes(n):
    if n is None:
        return ""
    n = float(n)
    if n >= 1024 * 1024 * 1024:
        return f"{n / (1024 ** 3):g} GiB"
    if n >= 1024 * 1024:
        return f"{n / (1024 ** 2):g} MiB"
    if n >= 1024:
        return f"{n / 1024:g} KiB"
    return f"{n:g} B"


def short_label(row):
    return row["microarch"]


def annotate_points(ax, pts_with_rows):
    """Labels each (x, y, row) point with its microarchitecture, alternating
    the vertical offset for points that share an x (year) -- e.g. Ookay/
    Upgrade both 2017, Crux/Skylark both 2019 -- so the text doesn't overlap
    into an unreadable stack."""
    seen_at_year = {}
    for x, y, row in pts_with_rows:
        k = seen_at_year.get(x, 0)
        seen_at_year[x] = k + 1
        dy = 6 + 15 * k
        ax.annotate(short_label(row), (x, y), textcoords="offset points",
                    xytext=(6, dy), fontsize=7.5, color="0.25")


def base_plot(figsize=(8.5, 5.5)):
    fig, ax = plt.subplots(figsize=figsize)
    style_axes(ax)
    return fig, ax


def plot_series(rows, field_phase1, out_path, ylabel, title, log_y=False,
                 field_phase2=None, annotate=True, y_is_bytes=False):
    """Generic scalar-metric-vs-year plot. field_phase1 is always drawn as
    the solid, vendor-shaped marker series (the observed/primary value).
    If field_phase2 is given and differs from field_phase1 at a point, an
    open marker + thin connector is added at that same year to show the
    Phase-II-resolved value without replacing the Phase-I point."""
    fig, ax = base_plot()

    by_vendor = {}
    for r in rows:
        y1 = fnum(r[field_phase1])
        if y1 is None:
            continue
        by_vendor.setdefault(r["vendor"], []).append(r)

    all_pts_for_annotation = []
    for vendor, vrows in by_vendor.items():
        vrows = sorted(vrows, key=lambda r: r["year"])
        style = VENDOR_STYLE.get(vendor, dict(marker="D", label=vendor))
        xs = [r["year"] for r in vrows]
        ys = [fnum(r[field_phase1]) for r in vrows]
        ax.plot(xs, ys, color="black", marker=style["marker"], markersize=8,
                 markerfacecolor="black", linewidth=1.4, linestyle="-",
                 label=style["label"])
        all_pts_for_annotation.extend(zip(xs, ys, vrows))
    if annotate:
        all_pts_for_annotation.sort(key=lambda t: t[0])
        annotate_points(ax, all_pts_for_annotation)

    if field_phase2:
        drew_p2_label = False
        for r in rows:
            y1 = fnum(r[field_phase1])
            y2 = fnum(r[field_phase2])
            if y1 is None or y2 is None:
                continue
            if abs(y1 - y2) < 1e-9:
                continue
            ax.plot([r["year"], r["year"]], [y1, y2], color="0.4", linewidth=1.0,
                     linestyle=":", zorder=1)
            ax.plot(r["year"], y2, marker="o", markersize=8, markerfacecolor="white",
                     markeredgecolor="black", markeredgewidth=1.3, linestyle="none",
                     label="Phase II (PMU/system-report/literature) resolved value"
                           if not drew_p2_label else None, zorder=3)
            drew_p2_label = True

    if log_y:
        ax.set_yscale("log", base=2)
        if y_is_bytes:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(v)))
            distinct_vals = sorted({fnum(r[field_phase1]) for r in rows if fnum(r[field_phase1])})
            if field_phase2:
                distinct_vals = sorted(set(distinct_vals) |
                                        {fnum(r[field_phase2]) for r in rows if fnum(r[field_phase2])})
            ax.set_yticks(distinct_vals)
            ax.set_yticks([], minor=True)

    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=9, loc="best")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def plot_dual_series(rows, field_a, label_a, field_b, label_b, out_path, ylabel, title):
    """Two metrics vs year on the same axes with different markers, same
    color scheme (used for LLC hit-latency + LLC-to-memory miss penalty,
    and for the two PMU-derived normalized metrics)."""
    fig, ax = base_plot()
    for field, label, marker, ls in ((field_a, label_a, "o", "-"), (field_b, label_b, "s", "--")):
        pts = [(r["year"], fnum(r[field])) for r in rows if fnum(r[field]) is not None]
        pts.sort()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color="black" if ls == "-" else "0.45", marker=marker, markersize=8,
                 markerfacecolor="black" if ls == "-" else "0.45", linewidth=1.4,
                 linestyle=ls, label=label)
    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=9, loc="best")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def plot_law_heldout(rows, field, out_path, ylabel, title, model_fn,
                      last_lab_year, future_year, hazel_year, hazel_value,
                      hazel_label, future_uncertainty=None, log_y=False,
                      y_is_bytes=False, hazel_jitter_years=0.0,
                      hazel_text_xy=(0.40, 0.62)):
    """Moore-style frozen-prediction / held-out-reveal figure (PROJECT 1.pdf
    Section 9's required visual logic): lab observations solid, the frozen
    model's own extrapolation dashed starting at the last measured lab
    point and extending only into future/unmeasured years, and the
    held-out Hazel reveal as a star (real measurement) or an open/gray
    diamond (untestable this pass -- never a fabricated measured point).
    The dashed line and its future-year value are computed purely from the
    frozen model; no Hazel point is ever used to refit it."""
    fig, ax = base_plot()

    by_vendor = {}
    for r in rows:
        y1 = fnum(r[field])
        if y1 is None:
            continue
        by_vendor.setdefault(r["vendor"], []).append(r)

    all_pts_for_annotation = []
    for vendor, vrows in by_vendor.items():
        vrows = sorted(vrows, key=lambda r: r["year"])
        style = VENDOR_STYLE.get(vendor, dict(marker="D", label=vendor))
        xs = [r["year"] for r in vrows]
        ys = [fnum(r[field]) for r in vrows]
        ax.plot(xs, ys, color="black", marker=style["marker"], markersize=8,
                 markerfacecolor="black", linewidth=1.4, linestyle="-",
                 label=style["label"], zorder=2)
        all_pts_for_annotation.extend(zip(xs, ys, vrows))
    all_pts_for_annotation.sort(key=lambda t: t[0])
    annotate_points(ax, all_pts_for_annotation)

    dash_xs = [last_lab_year, future_year]
    dash_ys = [model_fn(last_lab_year), model_fn(future_year)]
    ax.plot(dash_xs, dash_ys, color="black", linestyle="--", linewidth=1.6,
             marker="x", markersize=8, markeredgewidth=1.6, zorder=2,
             label=f"Frozen model, dashed extrapolation to {future_year}")

    if future_uncertainty is not None:
        lo, hi = future_uncertainty
        yv = model_fn(future_year)
        ax.errorbar([future_year], [yv], yerr=[[yv - lo], [hi - yv]],
                     color="0.35", capsize=5, linewidth=1.6, zorder=2)

    hx = hazel_year + hazel_jitter_years
    if hazel_value is not None:
        ax.plot([hx], [hazel_value], marker="*", markersize=20, color="#B8860B",
                 markeredgecolor="black", markeredgewidth=1.0, linestyle="none",
                 zorder=5, label="Hazel-Haswell (held-out reveal)")
        ax.annotate(hazel_label, xy=(hx, hazel_value), xycoords="data",
                    xytext=hazel_text_xy, textcoords="axes fraction",
                    fontsize=8, color="#7a5c00",
                    arrowprops=dict(arrowstyle="->", color="#B8860B", linewidth=1.1),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor="#B8860B", linewidth=0.8))
    else:
        hy = model_fn(hazel_year)
        ax.plot([hx], [hy], marker="D", markersize=12, markerfacecolor="none",
                 markeredgecolor="0.4", markeredgewidth=1.8, linestyle="none",
                 zorder=5, label="Hazel-Haswell (untestable this pass)")
        ax.annotate(hazel_label, xy=(hx, hy), xycoords="data",
                    xytext=hazel_text_xy, textcoords="axes fraction",
                    fontsize=8, color="0.3",
                    arrowprops=dict(arrowstyle="->", color="0.4", linewidth=1.1),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor="0.4", linewidth=0.8))

    if log_y:
        ax.set_yscale("log", base=2)
        if y_is_bytes:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(v)))
            distinct_vals = {fnum(r[field]) for r in rows if fnum(r[field]) is not None}
            distinct_vals |= {model_fn(last_lab_year), model_fn(future_year)}
            if hazel_value is not None:
                distinct_vals.add(hazel_value)
            if future_uncertainty is not None:
                distinct_vals |= set(future_uncertainty)
            ax.set_yticks(sorted(distinct_vals))
            ax.set_yticks([], minor=True)

    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in rows] + [future_year, hazel_year]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=7.5, loc="best")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def plot_final_combined(lab_rows, hazel_rows, field, out_path, ylabel, title,
                         log_y=False, y_is_bytes=False, untestable_years=None):
    """Final post-validation historical-comparison figure: combines every
    successfully measured system -- the 8 lab machines (solid, vendor-shaped,
    connected line, exactly as fit) plus any already-validated Hazel
    generation (drawn as an unconnected filled star, never blended into the
    lab trend line) -- sorted by year, in the same empirical spirit as
    Moore's original plot. `untestable_years` optionally lists Hazel years
    whose value for this specific field was never resolved (shown as an
    open gray diamond + annotation instead of a fabricated star)."""
    fig, ax = base_plot()

    by_vendor = {}
    for r in lab_rows:
        if fnum(r[field]) is None:
            continue
        by_vendor.setdefault(r["vendor"], []).append(r)

    all_pts_for_annotation = []
    for vendor, vrows in by_vendor.items():
        vrows = sorted(vrows, key=lambda r: r["year"])
        style = VENDOR_STYLE.get(vendor, dict(marker="D", label=vendor))
        xs = [r["year"] for r in vrows]
        ys = [fnum(r[field]) for r in vrows]
        ax.plot(xs, ys, color="black", marker=style["marker"], markersize=8,
                 markerfacecolor="black", linewidth=1.4, linestyle="-",
                 label=style["label"], zorder=2)
        all_pts_for_annotation.extend(zip(xs, ys, vrows))
    all_pts_for_annotation.sort(key=lambda t: t[0])
    annotate_points(ax, all_pts_for_annotation)

    untestable_years = untestable_years or set()
    drew_star_label = drew_diamond_label = False
    fig.canvas.draw()  # force autoscale from lab data before placing Hazel markers
    for r in hazel_rows:
        y = fnum(r[field])
        hx = r["year"] + 0.3
        if r["year"] in untestable_years or y is None:
            ylo, yhi = ax.get_ylim()
            hy = (ylo * yhi) ** 0.5 if log_y else (ylo + yhi) / 2.0
            ax.plot([hx], [hy], marker="D", markersize=11, markerfacecolor="none",
                     markeredgecolor="0.4", markeredgewidth=1.6, linestyle="none",
                     zorder=5,
                     label="Hazel (untestable this field)" if not drew_diamond_label else None)
            ax.annotate(f"{short_label(r)} (untestable)", (hx, hy),
                        textcoords="offset points", xytext=(6, 6), fontsize=7.5, color="0.3")
            drew_diamond_label = True
        else:
            ax.plot([hx], [y], marker="*", markersize=18, color="#B8860B",
                     markeredgecolor="black", markeredgewidth=1.0, linestyle="none",
                     zorder=5,
                     label="Hazel (validated, held-out)" if not drew_star_label else None)
            ax.annotate(short_label(r), (hx, y), textcoords="offset points",
                        xytext=(6, -16), fontsize=7.5, color="#7a5c00")
            drew_star_label = True

    if log_y:
        ax.set_yscale("log", base=2)
        if y_is_bytes:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: human_bytes(v)))
            distinct_vals = {fnum(r[field]) for r in lab_rows if fnum(r[field]) is not None}
            distinct_vals |= {fnum(r[field]) for r in hazel_rows if fnum(r[field]) is not None}
            ax.set_yticks(sorted(distinct_vals))
            ax.set_yticks([], minor=True)

    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in lab_rows] + [r["year"] + 0.3 for r in hazel_rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=7.5, loc="best")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def plot_hit_rate(rows, field, field_lo, field_hi, out_path, ylabel, title):
    """Plot #14: the software-only timing-derived hit-rate estimator (Hhat,
    PROJECT 1.pdf Sec. 8.5) vs. year, evaluated at ONE identical standardized
    workload size across every machine (262,144 B / 256 KiB -- the largest
    common footprint tested on every machine's sweep that still shows real
    cross-machine variation rather than having already collapsed near 0 or
    1; see CHRONOLOGICAL_MASTER_TABLE.md for the size-selection rationale).
    Bootstrap 95% CI error bars come directly from the estimator's own
    output, not fabricated."""
    fig, ax = base_plot()
    by_vendor = {}
    for r in rows:
        y = fnum(r[field])
        if y is None:
            continue
        by_vendor.setdefault(r["vendor"], []).append(r)

    all_pts_for_annotation = []
    for vendor, vrows in by_vendor.items():
        vrows = sorted(vrows, key=lambda r: r["year"])
        style = VENDOR_STYLE.get(vendor, dict(marker="D", label=vendor))
        xs = [r["year"] for r in vrows]
        ys = [fnum(r[field]) for r in vrows]
        lo = [fnum(r[field]) - fnum(r[field_lo]) for r in vrows]
        hi = [fnum(r[field_hi]) - fnum(r[field]) for r in vrows]
        ax.errorbar(xs, ys, yerr=[lo, hi], color="black", marker=style["marker"],
                     markersize=8, markerfacecolor="black", linewidth=1.4,
                     linestyle="-", capsize=4, elinewidth=1.0, label=style["label"])
        all_pts_for_annotation.extend(zip(xs, ys, vrows))
    all_pts_for_annotation.sort(key=lambda t: t[0])
    annotate_points(ax, all_pts_for_annotation)

    ax.set_ylim(0.65, 1.05)
    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12)
    all_years = [r["year"] for r in rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


INCL_ORDER = ["NON-INCLUSIVE", "UNCERTAIN", "INCLUSIVE"]


def incl_category(cell):
    c = cell.upper()
    if c.startswith("NON-INCLUSIVE"):
        return "NON-INCLUSIVE"
    if c.startswith("UNCERTAIN"):
        return "UNCERTAIN"
    if c.startswith("INCLUSIVE"):
        return "INCLUSIVE"
    return "UNCERTAIN"


def plot_inclusion(rows, out_path):
    fig, ax = base_plot(figsize=(9.5, 5))
    # A small fixed x-jitter per pairing keeps all three pairings visible
    # side-by-side even when two land on the identical (year, category) cell
    # -- e.g. Crux and Skylark both reading L2-vs-LLC as NON-INCLUSIVE in
    # 2019 -- rather than one marker silently occluding another.
    pairings = [("incl_l1_l2", "L1 vs L2", "o", -0.10), ("incl_l2_llc", "L2 vs LLC", "s", 0.0),
                ("incl_l1_llc", "L1 vs LLC (skip-level)", "^", 0.10)]
    y_of = {cat: i for i, cat in enumerate(INCL_ORDER)}
    for field, label, marker, jitter in pairings:
        pts = [(r["year"] + jitter, y_of[incl_category(r[field])]) for r in rows]
        pts.sort()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color="black", marker=marker, markersize=9,
                 markerfacecolor="black", linewidth=0, label=label)
    ax.set_yticks(range(len(INCL_ORDER)))
    ax.set_yticklabels(INCL_ORDER)
    ax.set_ylim(-0.5, len(INCL_ORDER) - 0.5)
    ax.set_xlabel("Year (processor generation / microarchitecture introduction)")
    ax.set_ylabel("Inclusion / exclusion behavior (categorical)")
    ax.set_title("Inclusion/exclusion behavior vs. year, per cache-level pairing", fontsize=12)
    all_years = [r["year"] for r in rows]
    ax.set_xlim(min(all_years) - 1, max(all_years) + 1)
    ax.legend(frameon=False, fontsize=9, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {out_path}.pdf/.png", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path")
    ap.add_argument("-o", "--out-dir", required=True)
    ap.add_argument("--final-csv",
                     help="Post-validation combined dataset (8 lab rows + any "
                          "already-validated Hazel row(s), e.g. "
                          "chronological_master_table_with_hazel_haswell.csv) "
                          "for the final historical-comparison plots.")
    args = ap.parse_args()

    import os
    os.makedirs(args.out_dir, exist_ok=True)
    rows = load_rows(args.csv_path)

    def p(name):
        return os.path.join(args.out_dir, name)

    # 1. L1D capacity vs year
    plot_series(rows, "l1_size_b", p("chrono_01_l1_capacity"),
                "L1D capacity (bytes, log2)", "L1D capacity vs. year",
                log_y=True, y_is_bytes=True)
    # 2. L1D associativity vs year
    plot_series(rows, "l1_assoc_phase1", p("chrono_02_l1_associativity"),
                "L1D associativity (ways)", "L1D associativity vs. year",
                field_phase2="l1_assoc_pmu")
    # 3. L1D hit latency vs year (ns/access)
    plot_series(rows, "l1_hit_ns", p("chrono_03_l1_hit_latency"),
                "L1D hit latency (ns/access)", "L1D hit latency vs. year")
    # 4. L1 miss penalty vs year
    plot_series(rows, "l1_missp_ns", p("chrono_04_l1_miss_penalty"),
                "L1 miss penalty, L1→L2 (ns/access)", "L1 miss penalty vs. year")
    # 5. L2 capacity per core vs year
    plot_series(rows, "l2_size_b", p("chrono_05_l2_capacity"),
                "L2 capacity per core (bytes, log2)", "L2 capacity per core vs. year",
                log_y=True, y_is_bytes=True)
    # 6. L2 associativity vs year
    plot_series(rows, "l2_assoc_phase1", p("chrono_06_l2_associativity"),
                "L2 associativity (ways)", "L2 associativity vs. year",
                field_phase2="l2_assoc_pmu")
    # 7. L2 hit latency vs year
    plot_series(rows, "l2_hit_ns", p("chrono_07_l2_hit_latency"),
                "L2 hit latency (ns/access)", "L2 hit latency vs. year")
    # 8. L2 miss penalty vs year
    plot_series(rows, "l2_missp_ns", p("chrono_08_l2_miss_penalty"),
                "L2 miss penalty, L2→LLC (ns/access)", "L2 miss penalty vs. year")
    # 9. LLC capacity vs year (sharing domain) + normalized MiB/core
    plot_series(rows, "llc_size_phase1_b", p("chrono_09a_llc_capacity_domain"),
                "LLC capacity, sharing domain (bytes, log2)",
                "LLC capacity (sharing domain) vs. year",
                log_y=True, y_is_bytes=True, field_phase2="llc_size_pmu_b")
    plot_series(rows, "llc_mib_per_core", p("chrono_09b_llc_capacity_per_core"),
                "LLC capacity per core within its sharing domain (MiB)",
                "LLC capacity per core (normalized) vs. year")
    # 10. LLC associativity/effective vs year
    plot_series(rows, "llc_assoc_phase1", p("chrono_10_llc_associativity"),
                "LLC associativity (ways, effective)", "LLC associativity vs. year",
                field_phase2="llc_assoc_pmu")
    # 11. LLC hit latency and LLC-to-memory miss penalty vs year
    plot_dual_series(rows, "llc_hit_ns", "LLC hit latency",
                      "llc_missp_ns", "LLC→DRAM miss penalty",
                      p("chrono_11_llc_latency_and_miss_penalty"),
                      "Latency (ns/access)",
                      "LLC hit latency and LLC→DRAM miss penalty vs. year")
    # 12. Cache line/block size vs year
    plot_series(rows, "l1_line_b", p("chrono_12_line_size"),
                "Cache line size (bytes)", "L1D line size vs. year (LLC line size noted per-machine "
                "in CHRONOLOGICAL_MASTER_TABLE.md where it differs)")
    # 13. Inclusion/exclusion behavior vs year (categorical)
    plot_inclusion(rows, p("chrono_13_inclusion_exclusion"))
    # 14. Timing-derived hit-rate/residency metric vs year, one identical
    # standardized workload (262,144 B / 256 KiB) across all 8 machines
    plot_hit_rate(rows, "hhat_256kib", "hhat_256kib_ci_lower", "hhat_256kib_ci_upper",
                  p("chrono_14_software_hit_rate"),
                  "Estimated hit rate, Ĥ (256 KiB workload, bootstrap 95% CI)",
                  "Software-only timing-derived hit rate vs. year\n"
                  "(identical 262,144 B standardized workload, every machine)")
    # 15. At least 2 PMU-derived normalized metrics vs year
    plot_dual_series(rows, "pmu_l1missrate_at_l1fp_pct", "L1 miss rate @ L1 footprint (sanity check)",
                      "pmu_cachemissrate_at_llcfp_pct", "Generic cache-miss rate @ LLC footprint",
                      p("chrono_15_pmu_normalized_metrics"),
                      "Miss rate (%)",
                      "PMU-derived normalized metrics vs. year")

    # Law 1 (Chen-Ngo Cache Capacity Doubling Law): frozen model
    # C(t) = 256 KiB * 2^((t-2014)/3), dashed extrapolation 2023->2028,
    # Hazel-Haswell's own L2 boundary was never cleanly resolved this pass
    # (Section "Hazel-Haswell: Timing-Only Results") -- shown as an open,
    # explicitly-labeled "untestable" diamond at the model's own predicted
    # value, never a fabricated measured point.
    def law1_model(t):
        return 256 * 1024 * (2 ** ((t - 2014) / 3.0))
    plot_law_heldout(
        rows, "l2_size_b", p("law1_l2_capacity_heldout"),
        "L2 capacity per core (bytes, log2)",
        "Law 1 (Chen–Ngo Capacity Doubling): frozen prediction and held-out reveal",
        model_fn=law1_model, last_lab_year=2023, future_year=2028,
        hazel_year=2014, hazel_value=None,
        hazel_label="Hazel-Haswell target (2014):\nL2 UNTESTABLE this pass\n(no resolved capacity boundary)",
        future_uncertainty=(law1_model(2023), 2 * law1_model(2028)),
        log_y=True, y_is_bytes=True, hazel_text_xy=(0.30, 0.72),
    )

    # Law 2 (Chen-Ngo Cache Invariance Law): frozen model is the constant
    # 6-of-8 majority baseline (32,768 B), not a per-machine curve fit --
    # Hazel-Haswell's own L1D (32,768 B, 8-way, fully reproducible) is a
    # real, resolved measurement, so it is drawn as a filled star, jittered
    # slightly in x so it does not fully occlude Sunbird's own 2014 point.
    def law2_model(_t):
        return 32768
    plot_law_heldout(
        rows, "l1_size_b", p("law2_l1d_invariance_heldout"),
        "L1D capacity (bytes, log2)",
        "Law 2 (Chen–Ngo Invariance): frozen prediction and held-out reveal",
        model_fn=law2_model, last_lab_year=2023, future_year=2028,
        hazel_year=2014, hazel_value=32768,
        hazel_label="Hazel-Haswell (2014): 32,768 B,\n8-way, 64 B line — exact match",
        future_uncertainty=(32768, 65536),
        log_y=True, y_is_bytes=True, hazel_jitter_years=0.35,
        hazel_text_xy=(0.32, 0.55),
    )

    # Final post-validation historical comparison: now that the frozen
    # lab-only prediction has been checked against Hazel-Haswell
    # (Section "Held-Out Prediction Evaluation"), combine every
    # successfully measured system -- 8 lab machines + the validated
    # Hazel-Haswell generation -- into one chronological dataset, sorted
    # oldest to newest, in the same empirical spirit as Moore's own plot.
    if args.final_csv:
        final_rows = load_rows(args.final_csv)
        lab_machines = {r["machine"] for r in rows}
        lab_rows = [r for r in final_rows if r["machine"] in lab_machines]
        hazel_rows = [r for r in final_rows if r["machine"] not in lab_machines]

        plot_final_combined(
            lab_rows, hazel_rows, "l1_size_b", p("final_01_l1_capacity_with_hazel"),
            "L1D capacity (bytes, log2)",
            "Final combined comparison: L1D capacity vs. year (lab + validated Hazel)",
            log_y=True, y_is_bytes=True,
        )
        plot_final_combined(
            lab_rows, hazel_rows, "l2_size_b", p("final_02_l2_capacity_with_hazel"),
            "L2 capacity per core (bytes, log2)",
            "Final combined comparison: L2 capacity per core vs. year (lab + validated Hazel)",
            log_y=True, y_is_bytes=True,
            untestable_years={r["year"] for r in hazel_rows if fnum(r["l2_size_b"]) is None},
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
