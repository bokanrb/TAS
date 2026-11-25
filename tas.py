#!/usr/bin/env python3
"""TAS, Target Attack Surface. Thin, cross platform recon orchestrator.

Entry point. Run `python tas.py --help`, or on *nix `./tas.py --help`.
Works the same on macOS, Linux and Windows.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tas.cli import main

if __name__ == "__main__":
    sys.exit(main())
