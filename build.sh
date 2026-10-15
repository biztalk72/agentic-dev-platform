#!/usr/bin/env bash
set -euo pipefail

# MVP bootstrap: checks Python, installs deps, runs a dry-run demo.
python3 --version
pip3 install -r requirements.txt
python3 -m src.main --demo
echo "MVP dry-run complete. Check output/ for PRD draft and dashboard snapshot."
