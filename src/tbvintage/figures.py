"""Source-grounded aggregate figures (no row-level restricted data; WHO national aggregates only)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

INK, MUTED, BLUE, ORANGE, GRID = "#1f2328", "#59636e", "#2f6db5", "#c4621d", "#e4e7eb"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def coverage_figure(cov: pd.DataFrame, pairs_by_year: pd.DataFrame, vintage: str, path: str):
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    _style(ax)
    ax.plot(cov["year"], cov["country_years"], color=MUTED, marker="o", lw=1.5,
            label="Countries with any provisional row")
    ax.plot(cov["year"], cov["h1_complete"], color=BLUE, marker="o", lw=2,
            label="Complete H1 (6 months or 2 quarters)")
    py = pairs_by_year.set_index("year")
    ax.plot(py.index, py["strict"], color=ORANGE, marker="o", lw=2,
            label="Strict same-definition pair with year t-1")
    ax.set_xlabel("Year t", color=INK)
    ax.set_ylabel("Countries", color=INK)
    ax.set_ylim(bottom=0)
    ax.set_title(f"WHO provisional TB notifications, vintage {vintage}: coverage thins in recent years",
                 loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.text(0.01, 0.01, "Source: WHO Global TB Programme provisional notifications CSV. "
             "Notifications are not incidence.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def ratio_figure(pairs: pd.DataFrame, vintage: str, path: str, thresholds=(0.05, 0.10, 0.15, 0.20)):
    sub = pairs[pairs["strict"]]
    years = sorted(sub["year"].unique())
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    _style(ax)
    for i, y in enumerate(years):
        r = sub.loc[sub["year"] == y, "ratio"].clip(0.4, 1.8)
        x = i + (pd.Series(range(len(r))) % 7 - 3) * 0.035
        ax.scatter(x, r.values, s=10, color=BLUE, alpha=0.55, linewidths=0)
    for k in thresholds:
        ax.axhline(1 - k, color=ORANGE if k == 0.10 else GRID, lw=1.2 if k == 0.10 else 0.9,
                   ls="--" if k == 0.10 else "-")
        ax.text(len(years) - 0.45, 1 - k, f"-{int(k * 100)}%", va="center", fontsize=7, color=MUTED)
    ax.axhline(1.0, color=MUTED, lw=0.8)
    ax.set_xticks(range(len(years)), [f"{y - 1}->{y}" for y in years])
    ax.set_ylabel("H1 ratio (year t / year t-1), clipped 0.4-1.8", color=INK)
    ax.set_title(f"Strict same-definition H1 ratios within vintage {vintage} (one point per country)",
                 loc="left", fontsize=10, color=INK)
    fig.text(0.01, 0.01, "Within-vintage year-on-year change, not a revision between releases.",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def revision_scatter(units: pd.DataFrame, k: float, path: str):
    """Early-vintage vs reference H1 ratio for each (country, year) unit, alert quadrants marked."""
    fig, ax = plt.subplots(figsize=(6.4, 6), dpi=150)
    _style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    cut = 1 - k
    changed = units[f"changed_{int(round(k * 100))}"].astype(bool)
    x, y = units["ratio_a"].clip(0.4, 1.8), units["ratio_b"].clip(0.4, 1.8)
    ax.scatter(x[~changed], y[~changed], s=14, color=BLUE, alpha=0.55, linewidths=0,
               label=f"Same alert status (n={int((~changed).sum())})")
    ax.scatter(x[changed], y[changed], s=34, color=ORANGE, edgecolor=INK, linewidths=0.6,
               label=f"Alert status changed (n={int(changed.sum())})")
    ax.plot([0.4, 1.8], [0.4, 1.8], color=MUTED, lw=0.8)
    ax.axvline(cut, color=ORANGE, ls="--", lw=1)
    ax.axhline(cut, color=ORANGE, ls="--", lw=1)
    ax.set_xlim(0.4, 1.8)
    ax.set_ylim(0.4, 1.8)
    ax.set_xlabel("H1 ratio in report-season snapshot (early)", color=INK)
    ax.set_ylabel("H1 ratio in 2026-10-17 public file (reference)", color=INK)
    ax.set_title(f"C1: same (country, year) H1 ratio across vintages; dashed = -{int(k * 100)}% alert",
                 loc="left", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.text(0.01, 0.01, "Strict same-definition units, years 2021/2023/2024/2025; clipped 0.4-1.8. "
             "Reference is a later file, not truth.", fontsize=6.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def maturity_curve(s4: pd.DataFrame, k: float, path: str):
    """H1 2021 units available and changed vs the reference, by nominal 2021 snapshot date."""
    tag = int(round(k * 100))
    d = s4.assign(nominal=pd.to_datetime(s4["early"].str[-10:])).sort_values("nominal")
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    _style(ax)
    ax.plot(d["nominal"], d["n_units"], color=BLUE, marker="o", lw=2, label="Strict units comparable to reference")
    ax.plot(d["nominal"], d[f"changed_{tag}"], color=ORANGE, marker="o", lw=2,
            label=f"... of which -{tag}% alert status differs from reference")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Country H1 2020->2021 pairs", color=INK)
    ax.set_xlabel("Nominal WHO snapshot date in 2021 (all made public by commit 2021-10-13)", color=INK)
    ax.set_title("S4: H1 2021 becomes comparable only as snapshots mature", loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def defer_tradeoff(d: pd.DataFrame, path: str):
    """Deferrals vs remaining reversals for each buffer at the primary threshold (C1)."""
    g = d.drop_duplicates("buffer").sort_values("buffer")
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    _style(ax)
    ax.plot(g["buffer"], g["n_deferred"], color=BLUE, marker="o", lw=2, label="Decisions deferred")
    ax.plot(g["buffer"], g["errors_after_defer_rule"], color=ORANGE, marker="o", lw=2,
            label="Reversals among acted decisions")
    ax.axhline(g["errors_if_trust_early"].iloc[0], color=MUTED, ls=":", lw=1,
               label="Reversals if early vintage trusted")
    ax.set_xlabel("Defer buffer around the -10% cut-off (0.03 predeclared)", color=INK)
    ax.set_ylabel("Count of country-year units", color=INK)
    ax.set_ylim(bottom=0)
    ax.set_title(f"C1 defer rule trade-off (n={int(g['n_decisions'].iloc[0])} units); retrospective, not validation",
                 loc="left", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
