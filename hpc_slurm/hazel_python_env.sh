#!/bin/bash
#
# hazel_python_env.sh -- source this before running any of this repo's
# scripts/*.py tools (summarize_raw.py, detect_*.py, plot_*.py) on Hazel.
#
# Hazel's default python3 (3.9.25) has numpy/scipy but not matplotlib, and
# `pip install --user` fails outright (home directory quota is exceeded --
# confirmed via `quota -s` / a failed install into /home/krchen/.local).
# matplotlib+numpy were instead installed once into GPFS project storage:
#   python3 -m pip install \
#     --target=/gpfs_common/share01/titan/krchen/pylibs matplotlib numpy
# (this pulled in numpy 2.0.2, ahead of the system scipy 1.9.3's own pinned
# numpy<1.26 requirement -- irrelevant here since no script in this repo
# imports scipy, only numpy/matplotlib.) Do not re-run that install without
# checking whether pylibs/ is already populated first.
#
export PYTHONPATH="/gpfs_common/share01/titan/krchen/pylibs:${PYTHONPATH:-}"
export MPLCONFIGDIR="/gpfs_common/share01/titan/krchen/.mplconfig"
mkdir -p "$MPLCONFIGDIR"
