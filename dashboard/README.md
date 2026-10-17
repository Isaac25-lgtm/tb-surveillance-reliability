# R02 vintage explorer (local only)

`streamlit run dashboard/app.py` — reads only committed aggregate files in `results/` and
`data/manifest/`; no raw data, no network calls, no model fitting. Tabs: overview/coverage,
provenance (all attempts incl. blocked), within-vintage pairs with country filter, cross-vintage status,
limitations. Smoke-tested with Streamlit `AppTest` in `tests/test_dashboard.py`.
**Not deployed.** Any public deployment needs separate investigator approval.
