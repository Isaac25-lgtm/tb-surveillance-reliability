"""Lawful acquisition of WHO provisional TB notification releases with a hash manifest.

Only official WHO endpoints or archived copies whose capture time can be proven
are registered. A vintage's ``public_by`` date is the earliest time we can
*prove* the file existed publicly (our own access time, or an archive capture
time); it is not the date WHO first disseminated it.
"""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

WHO_PROVISIONAL_URL = "https://extranet.who.int/tme/generateCSV.asp?ds=provisional_notifications"
WHO_DICTIONARY_URL = "https://extranet.who.int/tme/generateCSV.asp?ds=dictionary"

# Ordinary attempts allowed per host in one bounded session (investigator rule).
MAX_ATTEMPTS_PER_HOST = 3


@dataclass
class ManifestEntry:
    vintage_id: str
    source_url: str
    access_utc: str
    public_by_utc: str
    public_by_basis: str
    http_status: str
    bytes: int
    sha256: str
    server_filename: str
    local_path: str
    outcome: str
    note: str = ""


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _filename_from_headers(header_text: str) -> str:
    m = re.search(r"filename=([^\s;]+)", header_text, flags=re.I)
    return m.group(1).strip('"') if m else ""


def download(url: str, dest: str | Path, vintage_id: str, timeout: int = 90) -> ManifestEntry:
    """Fetch ``url`` once with curl (honours the environment proxy/CA settings).

    Records failures as manifest entries instead of raising, so blocked or empty
    responses are preserved as evidence.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    header_path = dest.with_suffix(dest.suffix + ".headers")
    access = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    proc = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", str(timeout), "-o", str(dest), "-D", str(header_path),
         "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    status = proc.stdout.strip() or "000"
    headers = header_path.read_text(errors="replace") if header_path.exists() else ""
    size = dest.stat().st_size if dest.exists() else 0
    ok = proc.returncode == 0 and status == "200" and size > 0
    return ManifestEntry(
        vintage_id=vintage_id,
        source_url=url,
        access_utc=access,
        public_by_utc=access if ok else "",
        public_by_basis="own_access_time" if ok else "",
        http_status=status,
        bytes=size,
        sha256=sha256_file(dest) if size else "",
        server_filename=_filename_from_headers(headers),
        local_path=str(dest) if ok else "",
        outcome="ok" if ok else ("empty_response" if status == "200" else "failed"),
        note=proc.stderr.strip()[:200],
    )


def read_manifest(path: str | Path) -> list[ManifestEntry]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [ManifestEntry(**{**r, "bytes": int(r["bytes"] or 0)}) for r in rows]


def write_manifest(entries: list[ManifestEntry], path: str | Path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[f.name for f in fields(ManifestEntry)])
        w.writeheader()
        for e in entries:
            w.writerow(asdict(e))


def usable_vintages(entries: list[ManifestEntry], root: str | Path = ".") -> list[ManifestEntry]:
    """Successful entries whose local file exists and still matches the recorded hash."""
    out = []
    for e in entries:
        if e.outcome != "ok" or not e.local_path:
            continue
        p = Path(root) / e.local_path
        if p.exists() and sha256_file(p) == e.sha256:
            out.append(e)
    return out
