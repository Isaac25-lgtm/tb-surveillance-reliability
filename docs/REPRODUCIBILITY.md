# Reproducibility

Commands actually run in the checkpoint-1 cloud session (Linux, Python 3.13.16, 2 threads):

```bash
python3 -m venv .venv && .venv/bin/pip install pandas numpy matplotlib pytest streamlit pyyaml rdata
# acquisition (performed once, 2026-10-17; see data/manifest/source_attempts.csv)
curl -sS -L --max-time 90 -o provisional_notifications.csv \
  "https://extranet.who.int/tme/generateCSV.asp?ds=provisional_notifications"
sha256sum provisional_notifications.csv   # a4be40a0d977a47e7684aa8630d29e4c52afb35e6735a8b312032d4fb8cd684b
mkdir -p data/raw/who_provisional/2026-10-17 && mv provisional_notifications.csv data/raw/who_provisional/2026-10-17/
# official WHO archived vintages (metadata-only clones, then named blobs; see data/manifest/gtb_tme_snapshots.csv)
git clone --filter=blob:none --no-checkout --bare https://github.com/GTB-TME/gtbreport2024 gtbreport2024.git
git -C gtbreport2024.git log --format='%H %cI' --name-status -- 'data/gtb/snapshot_*/monthly.rda'
git -C gtbreport2024.git cat-file blob <commit>:<path> > data/raw/gtb_tme/gtbreport2024/<path>
#   (same for gtbreport2021, 2022, 2023, 2025; paths/commits in the manifest; .venv/bin/pip install rdata)
OMP_NUM_THREADS=1 .venv/bin/python scripts/run_pipeline.py     # writes results/ (3 min 33 s at c2004a9)
.venv/bin/python -m pytest -q                                  # 20 passed
.venv/bin/streamlit run dashboard/app.py                       # optional local explorer
```

`scripts/acquire.py` wraps the one-request download and prints a manifest entry. WHO overwrites
the CSV in place, so a re-download on another date is a **different vintage**: its hash will differ
and it must be registered separately; it cannot regenerate the 2026-10-17 bytes. The pipeline
refuses any configured vintage whose SHA-256 does not match.

Seed: 20261017 (bootstrap only). Outputs: `results/tables/*.csv`, `results/figures/*.png`,
`results/run_summary.json` (records the code commit used).
CI (`.github/workflows/ci.yml`) runs only the synthetic-fixture tests; it never downloads data.

Use `git cat-file -p` / `cat-file blob` only; avoid `git ls-tree -l` on blobless clones (it fetches every blob
lazily). Git blob ids in the manifest let anyone verify the bytes against the WHO repositories.
