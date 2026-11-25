#!/usr/bin/env bash
# Convenience wrapper for macOS / Linux. Just calls the cross-platform installer.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt
python3 install/install.py "$@"
