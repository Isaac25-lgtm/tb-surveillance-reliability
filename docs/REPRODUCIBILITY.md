# Reproducibility

## What was actually re-run (17 October 2026, branch `research/presentation-repro-2026-10-17`)

**Source-to-output re-run, done once.**
- **Code:** commit `e59d998` (main after PR 1; the same tree as `dabf6df`).
- **Inputs:** 16 cached vintages. Before the run, all 16 matched the SHA-256 values in
  `configs/experiment.yaml` (16/16).
- **Environment:** Linux, Python 3.13.16, pandas 3.0.6, numpy 2.5.4, matplotlib 3.11.2, PyYAML 6.0.3,
  rdata 1.1.0, one thread.
- **Command:** `OMP_NUM_THREADS=1 python scripts/run_pipeline.py --out <scratch dir>`
- **Runtime:** 20:31:09Z to 20:35:01Z (3 min 52 s); exit code 0; 16 vintages loaded; 0 blocked.

**Comparison with the committed `results/`, byte for byte:**
- All **13 tables** were identical.
- All **5 figures** were identical.
- `run_summary.json` was identical except for its `code_commit` field. The committed copy keeps
  `c2004a9`, the commit that produced the committed outputs.

So committed raw inputs → committed code → committed outputs reproduced exactly. **No input was
re-acquired.** The cache came from the 17 October acquisition session. Re-downloading on another date
produces a different vintage; see "Re-acquisition" below.

**Earlier evidence (same day).** The pre-optimisation bootstrap at `c7b76f1`'s parent and the
optimised one at `c2004a9` produced byte-identical tables. A dedicated test checks that the faster
resampler matches the concat implementation exactly.

**Output hashes.** `results/RESULTS_MANIFEST.csv` lists bytes and SHA-256 for all 19 result files. The
manifest's own SHA-256 is `243db8df…cb0cfa01`.
- `python scripts/make_results_manifest.py --check` verifies the manifest.
- `tests/test_results_integrity.py` checks the hashes, the headline numbers (89/52/3, 86 stable, 8/125,
  CI upper bound 7.6%, 14 deferred / 3 avoided), cross-table consistency, and the absence of free text
  and email addresses.

**Tests run on this branch:**
- `pytest -q` → **29 passed**, on Python 3.13.16 and on a clean Python 3.11.17 venv with the deployment
  pins.
- The one warning is a matplotlib `tight_layout` notice in the synthetic end-to-end test: its single-year
  fixture places a threshold label outside the axes. The real figures render unclipped. Figure code was
  not changed, so no numeric output changed.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[test,dashboard,archives]"
# 1. current public vintage (one request; a new date is a NEW vintage with a new hash)
.venv/bin/python scripts/acquire.py
# 2. official WHO archived vintages: metadata-only clones, then the named blobs in data/manifest/gtb_tme_snapshots.csv
git clone --filter=blob:none --no-checkout --bare https://github.com/GTB-TME/gtbreport2024 gtbreport2024.git
git -C gtbreport2024.git cat-file blob <commit>:<path> > data/raw/gtb_tme/gtbreport2024/<path>
#    (same for gtbreport2021, 2022, 2023, 2025; each blob id is in the manifest; avoid `git ls-tree -l`)
# 3. pipeline (refuses any vintage whose SHA-256 differs from configs/experiment.yaml)
OMP_NUM_THREADS=1 .venv/bin/python scripts/run_pipeline.py          # about 4 min on one CPU
.venv/bin/python scripts/make_results_manifest.py --check
.venv/bin/python -m pytest -q
.venv/bin/streamlit run dashboard/app.py                             # default scope
R02_SHOW_ARCHIVE_DERIVED=1 .venv/bin/streamlit run dashboard/app.py  # full scope (local research use)
```

## Limits

- **Re-acquisition.** The WHO public CSV is overwritten in place, so the 2026-10-17 bytes cannot be
  re-downloaded. Without that cached file, the primary C1 analysis, S1, S4 and the within-file audit cannot
  be reproduced, because that file is their reference. Only the archive-to-archive comparisons (S3) can. The GTB-TME
  blobs are content-addressed: their git blob ids in the manifest pin the exact bytes, provided WHO keeps
  the repositories.
- **Raw inputs are not committed** (`.gitignore`), and their redistribution terms are unclear (see
  `docs/DEPLOYMENT.md`).
- **Seed and versions.** The bootstrap seed is 20261017. Library versions were recorded only for this
  re-run (above). Other pandas/numpy versions could change the last floating-point digits, which would
  show up as byte differences.
- **CI** runs only synthetic-fixture tests and committed-aggregate checks. It never downloads data or
  re-runs the pipeline.
