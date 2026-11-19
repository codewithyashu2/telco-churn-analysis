#!/usr/bin/env bash
# Reproduce the full analysis end to end.
set -euo pipefail
cd "$(dirname "$0")/python"
python 01_load_to_sqlite.py
python 02_run_sql_analysis.py
python 03_statistical_validation.py
python 04_make_charts.py
