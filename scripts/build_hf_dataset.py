#!/usr/bin/env python3

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from killbench_collector.hf_dataset import main


if __name__ == "__main__":
    raise SystemExit(main())
