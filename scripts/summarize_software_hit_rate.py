#!/usr/bin/env python3
"""Summarizes one or more raw `--experiment hit_rate` output files (Problem
8.5's software-only cache hit-rate estimator, main_code/software_hit_rate/)
into a single CSV: one row per input file, parsed directly from that file's
own "# experiment=hit_rate ..." metadata line and "# result ..." line -- no
recomputation, this script trusts the numbers cache_bench itself already
computed and reported (tau, sensitivity/specificity, Hhat, bootstrap CI).

Usage:
    python3 scripts/summarize_software_hit_rate.py \\
        data_raw/sunbird/software_hit_rate/raw/hit_rate_*.csv \\
        -o data_raw/sunbird/software_hit_rate/hit_rate_sweep_<ts>.csv
"""
import argparse
import csv
import gzip
import re
import sys

KV_RE = re.compile(r"(\w+)=([^\s]+)")


def parse_kv_line(line, prefix_tokens):
    """Strips a fixed number of leading non-key=value tokens (e.g. "#",
    "result") then parses the rest as space-separated key=value pairs."""
    parts = line.strip().split(maxsplit=prefix_tokens)
    rest = parts[-1] if len(parts) > prefix_tokens else ""
    return dict(KV_RE.findall(rest))


def open_maybe_gzip(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt")
    return open(path, "r")


def parse_file(path):
    meta = {}
    result = {}
    with open_maybe_gzip(path) as f:
        for line in f:
            if line.startswith("# experiment=hit_rate"):
                meta = parse_kv_line(line, 1)  # drop "#"
            elif line.startswith("# result"):
                result = parse_kv_line(line, 2)  # drop "#" "result"
    if not meta or not result:
        raise ValueError(f"{path}: missing metadata or result line -- not a valid "
                          f"hit_rate raw output file")
    row = {
        "source_file": path,
        "test_bytes": meta.get("test_bytes"),
        "resident_bytes": meta.get("resident_bytes"),
        "nonresident_bytes": meta.get("nonresident_bytes"),
        "calib_samples": meta.get("calib_samples"),
        "test_samples": meta.get("test_samples"),
        "seed": meta.get("seed"),
        "pattern": meta.get("pattern"),
        "tau_ticks": result.get("tau_ticks"),
        "sensitivity": result.get("sensitivity"),
        "specificity": result.get("specificity"),
        "p_obs": result.get("p_obs"),
        "Hhat": result.get("Hhat"),
        "ci_lower": result.get("ci_lower"),
        "ci_upper": result.get("ci_upper"),
        "bootstrap_mean": result.get("bootstrap_mean"),
        "bootstrap_std": result.get("bootstrap_std"),
        "bootstrap_reps": result.get("bootstrap_reps"),
    }
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="raw hit_rate output file(s), .csv or .csv.gz")
    ap.add_argument("-o", "--output", required=True, help="output summary CSV path")
    args = ap.parse_args()

    rows = [parse_file(p) for p in args.inputs]
    rows.sort(key=lambda r: int(r["test_bytes"]))

    fieldnames = list(rows[0].keys())
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"wrote {len(rows)} rows -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
