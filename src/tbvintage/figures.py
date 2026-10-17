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
