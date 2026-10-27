"""Export standalone PNG and SVG figures; no GUI or network required."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

from .statistics import CO2_ENTITIES, TEMP_ENTITIES


COLORS = ["#202f48", "#167d9a", "#d55e00", "#009e73", "#9a599a", "#bd8500", "#5879bc"]


def save(fig, output, name, footer):
    fig.text(0.02, 0.015, footer, ha="left", va="bottom", fontsize=8, color="#455366")
    fig.savefig(output / f"{name}.png", dpi=180, facecolor="white")
    fig.savefig(output / f"{name}.svg", metadata={"Date": None}, facecolor="white")
    plt.close(fig)


def create_charts(frame, trends, predictions, coverage, output):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold", "axes.labelcolor": "#263449",
                         "svg.hashsalt": "climatelens-first-analysis"})
    temp = frame[(frame.dataset == "temperature_anomaly") & (frame.entity == "World")].set_index("year")
    temp = temp.reindex(range(1850, 2025))
    fit = predictions[(predictions.dataset == "temperature_anomaly") & (predictions.entity == "World")]
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), gridspec_kw={"height_ratios": [1.15, 1]})
    axes[0].fill_between(temp.index, temp.lower, temp.upper, color="#bed9e2", label="Supplied source bounds (level unverified for snapshot)")
    axes[0].plot(temp.index, temp.value, color=COLORS[1], lw=1.5, label="Annual estimate")
    axes[0].axhline(0, color="#83909d", lw=0.7)
    axes[0].set(title="Global temperature: saved observations, 1850–2024", ylabel="°C relative to 1961–1990")
    axes[0].legend(loc="upper left", fontsize=8)
    modern = temp.loc[1960:2024]
    axes[1].plot(modern.index, modern.value, color=COLORS[1], lw=1, marker=".", ms=4, label="Annual estimate")
    axes[1].fill_between(fit.year, fit.mean_ci95_low, fit.mean_ci95_high, color="#eed0b6", label="95% pointwise HAC interval for fitted mean")
    axes[1].plot(fit.year, fit.fitted, color=COLORS[2], lw=2, label="Linear fit, 1960–2024")
    axes[1].set(title="Modern trend and model uncertainty", xlabel="Year", ylabel="°C relative to 1961–1990")
    axes[1].legend(loc="upper left", fontsize=8)
    for ax in axes:
        ax.grid(axis="y", alpha=0.18)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, output, "01_temperature", "Source: saved OWID snapshot, 2026-10-09. Baseline shift is fixed; source and model uncertainty are not combined.\nModel intervals: Bartlett HAC, 3 annual lags, t reference; not forecast intervals. 2025–2026 excluded from comparison.")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    for ax, dataset, entities, unit, title in (
        (axes[0], "temperature_anomaly", TEMP_ENTITIES, "°C per decade", "Temperature trends"),
        (axes[1], "co2_per_capita", CO2_ENTITIES, "Tonnes CO₂/person per decade", "Emissions-per-person trends"),
    ):
        table = trends[trends.dataset == dataset].set_index("entity").reindex(entities)
        y = np.arange(len(table))
        ax.errorbar(table.slope_per_decade, y,
                    xerr=[table.slope_per_decade-table.ci95_low, table.ci95_high-table.slope_per_decade],
                    fmt="o", capsize=4, color=COLORS[1] if dataset == "temperature_anomaly" else COLORS[2])
        ax.axvline(0, color="#83909d", lw=0.8)
        ax.set(yticks=y, yticklabels=entities, xlabel=unit, title=title)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.18)
    fig.suptitle("1960–2024 linear trends with 95% confidence intervals", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=(0, 0.12, 1, 0.94))
    save(fig, output, "02_trends", "OLS slopes with Bartlett HAC covariance (3 lags, small-sample correction, t reference). All series: 65 annual observations.\nIntervals describe model uncertainty, not total measurement uncertainty. Separate units; no causal or between-series significance claim.")

    co2 = frame[(frame.dataset == "co2_per_capita") & frame.entity.isin(CO2_ENTITIES)]
    fig, axes = plt.subplots(2, 4, figsize=(13, 7), sharex=True, sharey=True)
    shared_upper = float(co2[co2.year.between(1960, 2024)].value.max()) * 1.16
    for ax, entity, color in zip(axes.flat, CO2_ENTITIES, COLORS):
        group = co2[co2.entity == entity].set_index("year").reindex(range(1960, 2025))
        ax.plot(group.index, group.value, color=color, lw=2)
        ax.set_title(entity)
        ax.set_ylim(0, shared_upper)
        ax.grid(axis="y", alpha=0.18)
        last = group.loc[2024, "value"]
        ax.text(0.96, 0.93, f"2024: {last:.2f}", transform=ax.transAxes, ha="right", fontsize=10)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(0, 0.85, "Same axes in each panel\n\nUnits: tonnes CO₂/person/year\n\nTerritorial fossil + industrial CO₂\nLand-use change excluded\n\nNo emissions uncertainty bounds\nprovided in this snapshot", va="top", linespacing=1.6, fontsize=9, transform=axes.flat[-1].transAxes)
    fig.suptitle("Emissions per person: selected examples, 1960–2024", fontsize=16, fontweight="bold")
    fig.supxlabel("Year", y=0.07)
    fig.supylabel("Tonnes CO₂ per person per year", x=0.01)
    fig.tight_layout(rect=(0.02, 0.10, 1, 0.94))
    save(fig, output, "03_co2_per_person", "Source: Global Carbon Project / OWID saved snapshot. Selection is illustrative, not representative of all countries.\nWorld is the supplied global aggregate, not an unweighted average of the selected countries. Gaps are never interpolated.")

    data = frame[frame.dataset == "co2_per_capita"]
    entities = sorted(data.entity.unique())
    matrix = data.pivot(index="entity", columns="year", values="value").reindex(index=entities, columns=range(1960, 2025))
    available = matrix.notna()
    gaps = coverage[(coverage.dataset == "co2_per_capita") & (coverage.missing_years > 0)].sort_values(["missing_years", "entity"], ascending=[False, True])
    fig, axes = plt.subplots(2, 1, figsize=(12, 11), gridspec_kw={"height_ratios": [1, 3]})
    axes[0].plot(available.columns, available.sum()/len(entities)*100, color=COLORS[1], lw=2)
    axes[0].set(title=f"CO₂ coverage across all {len(entities)} entities in the saved file", ylabel="Entities with a value (%)", ylim=(0, 105))
    axes[0].grid(axis="y", alpha=0.18)
    if len(gaps):
        shown = available.loc[gaps.entity]
        axes[1].imshow(shown.astype(int), aspect="auto", interpolation="nearest", cmap=ListedColormap(["#efc18c", "#215b70"]), vmin=0, vmax=1,
                       extent=(1959.5, 2024.5, len(shown)-0.5, -0.5))
        axes[1].set(yticks=range(len(shown)), yticklabels=shown.index, xlabel="Year",
                    title="Entities with gaps: orange = no value; blue = observed")
        axes[1].tick_params(axis="y", labelsize=8)
    else:
        axes[1].text(0.5, 0.5, "No missing entity-years in this interval", ha="center")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, output, "04_missing_data", "Fixed 1960–2024 grid. Denominator includes countries, territories, and aggregates; it is not a population coverage measure.\nAbsence before a series starts can reflect entity history or reporting scope. No values are filled. All selected analysis series are complete.")
