# Data dictionary (observed in vintage who_prov_2026-10-17)

| Variable | Type | Meaning (WHO dictionary) | Observed audit |
|---|---|---|---|
| country, iso2, iso3, iso_numeric | text | Country identifiers | 142 iso3 codes; `iso3`+`year` unique |
| g_whoregion | text | WHO region | |
| year | int | Calendar year | 2020–2026 |
| report_frequency | int | 70 = Monthly; 71 = Quarterly | never missing; monthly rows never carry quarters and vice versa |
| report_coverage | int | 34 = All units; 35 = Some units | missing in 98 of 647 rows |
| m_01..m_12 | count | Provisional notifications for month 1..12 | no negatives; zeros mainly in small-count countries |
| q_1..q_4 | count | Provisional notifications for quarter 1..4 | as above |

Derived (in `tbvintage.preprocess` / `evaluate`): `h1_total`, `h1_complete`, `h1_missing_cells`,
`h1_has_zero`, `ratio`, `strict`, `relaxed`, `exclusion_reason`, cross-vintage `ratio_revision`,
`h1_revision_rel`, `changed_k`, `false_early_alarm_k`, `early_miss_k`. Definitions in
`docs/SCIENTIFIC_PROTOCOL.md`.
