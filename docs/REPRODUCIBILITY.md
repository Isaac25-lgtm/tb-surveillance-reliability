# Reproducibility

Commands actually run in the checkpoint-1 cloud session (Linux, Python 3.13.16, 2 threads):

```bash
python3 -m venv .venv && .venv/bin/pip install pandas numpy matplotlib pytest streamlit pyyaml
# acquisition (performed once, 2026-10-17; see data/manifest/source_attempts.csv)
curl -sS -L --max-time 90 -o provisional_notifications.csv \
  "https://extranet.who.int/tme/generateCSV.asp?ds=provisional_notifications"
sha256sum provisional_notifications.csv   # a4be40a0d977a47e7684aa8630d29e4c52afb35e6735a8b312032d4fb8cd684b
mkdir -p data/raw/who_provisional/2026-10-17 && mv provisional_notifications.csv data/raw/who_provisional/2026-10-17/
OMP_NUM_THREADS=2 .venv/bin/python scripts/run_pipeline.py     # writes results/
.venv/bin/python -m pytest -q                                  # 12 passed
.venv/bin/streamlit run dashboard/app.py                       # optional local explorer
```

`scripts/acquire.py` wraps the one-request download and prints a manifest entry. WHO overwrites
the CSV in place, so a re-download on another date is a **different vintage**: its hash will differ
and it must be registered separately; it cannot regenerate the 2026-10-17 bytes. The pipeline
refuses any configured vintage whose SHA-256 does not match.

Seed: 20261017 (bootstrap only). Outputs: `results/tables/*.csv`, `results/figures/*.png`,
`results/run_summary.json` (records the code commit used).
CI (`.github/workflows/ci.yml`) runs only the synthetic-fixture tests; it never downloads data.
