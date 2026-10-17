# Prior art (bounded competitor audit, checkpoint 1)

Depth labels: FULL_TEXT, ABSTRACT, REPOSITORY, CATALOGUE_ONLY, UNVERIFIED. Searches run 2026-10-17;
the audit is incomplete and must be extended before any manuscript.

| Work | Venue / ID | Relevance | Depth |
|---|---|---|---|
| WHO Global TB Report 2021, "COVID-19" section; Global TB Report 2022, "COVID-19 and TB" | who.int report pages | **Same source (closest head-to-head 1).** WHO describes collecting provisional monthly/quarterly notifications (initially 14 high-burden countries for Jan–Jun 2020, later >100 countries), published via TB Pronto dashboards, explicitly as provisional; used to measure drops vs 2019 | CATALOGUE_ONLY (via search summaries) |
| Falzon D, Zignol M, Bastard M, Floyd K, Kasaeva T. The impact of the COVID-19 pandemic on the global tuberculosis epidemic. *Front Immunol* 2023 | doi:10.3389/fimmu.2023.1234785 | WHO authors; notifications fell ~18% in 2020; uses notification shortfalls, not vintage reliability | ABSTRACT |
| Höhle M, an der Heiden M. Bayesian nowcasting during the STEC O104:H4 outbreak in Germany, 2011. *Biometrics* 2014 | doi:10.1111/biom.12194 | **Closest conceptual (head-to-head 2):** reporting-delay nowcasting from a reporting triangle. Needs line-list report dates we do not have | ABSTRACT |
| Vietnam TB notifications 2020 interrupted time series, *Emerg Infect Dis* 2022;28(3) | PMC8888245 | Country-level notification decline analysis; no vintage revision | CATALOGUE_ONLY |
| UKHSA / Public Health Scotland quarterly TB reports | gov.uk / publichealthscotland.scot | Official statements that provisional TB counts are revised (late notifications, culture results) | CATALOGUE_ONLY |

**Incremental question, if data permit:** not "provisional data are revised" (known), but how often
WHO-provisional H1 decline *alerts* reverse across public releases after same-definition matching,
and whether a precommitted defer rule pays off at explicit cost ratios.

**Falsifier:** reversal rates at operational thresholds near zero, or concentrated in a few
countries, in an uninspected later vintage. **Not yet established:** whether this is materially
beyond known provisional revisions — cannot be judged without a second vintage.
