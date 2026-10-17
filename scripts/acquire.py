"""Fetch the current WHO provisional TB notifications CSV once and print its manifest entry.

Usage: python scripts/acquire.py [--out data/raw/who_provisional]
Makes exactly one request (no retries). Append the printed entry to
data/manifest/source_attempts.csv and, if outcome=ok, add the vintage to configs/experiment.yaml.
Never run on CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tbvintage.acquire import WHO_PROVISIONAL_URL, download  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data/raw/who_provisional"))
    a = ap.parse_args()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dest = Path(a.out) / day / "provisional_notifications.csv"
    entry = download(WHO_PROVISIONAL_URL, dest, f"who_prov_{day}")
    if entry.local_path:
        entry.local_path = str(Path(entry.local_path).resolve().relative_to(ROOT))
    print(json.dumps(asdict(entry), indent=2))
