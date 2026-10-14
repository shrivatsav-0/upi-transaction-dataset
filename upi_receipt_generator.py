#!/usr/bin/env python3
"""Convenience entry point: `python upi_receipt_generator.py`.

The generator itself lives in the `upi_ss_gen` package (src/upi_ss_gen). This
script just forwards to the CLI so the historical command keeps working.

Run:
    python upi_receipt_generator.py
    python upi_receipt_generator.py -n 1000 --seed 7 -o ./mydata
    python upi_receipt_generator.py --no-augment --quiet
"""

from __future__ import annotations

import os
import sys

try:
    from upi_ss_gen.cli import main
except ModuleNotFoundError:  # running from a checkout without `uv sync`
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "src"))
    from upi_ss_gen.cli import main


if __name__ == "__main__":
    raise SystemExit(main())