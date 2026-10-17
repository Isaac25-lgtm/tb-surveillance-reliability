"""Write results/RESULTS_MANIFEST.csv: path, bytes and SHA-256 of every committed result file.

Usage: python scripts/make_results_manifest.py [--check]
--check exits non-zero if any file differs from the committed manifest (no file is written).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results" / "RESULTS_MANIFEST.csv"


def rows() -> list[dict]:
    out = []
    for p in sorted((ROOT / "results").rglob("*")):
        if p.is_file() and p.suffix in {".csv", ".png", ".json"} and p != MANIFEST:
            out.append({"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    current = rows()
    if ap.parse_args().check:
        with open(MANIFEST, newline="") as fh:
            committed = [{**r, "bytes": int(r["bytes"])} for r in csv.DictReader(fh)]
        sys.exit(0 if committed == current else 1)
    with open(MANIFEST, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"])
        w.writeheader()
        w.writerows(current)
    print(f"{len(current)} files")
