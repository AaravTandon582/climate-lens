"""Run the complete offline first analysis: python -m analysis.run."""

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path

import pandas as pd

from .charts import create_charts
from .inputs import load_inputs, sha256
from .report import write_report
from .statistics import CO2_ENTITIES, TEMP_ENTITIES, coverage_audit, fit_trend, rebase_temperature


HERE = Path(__file__).resolve().parent
START, END = 1960, 2024


def run(input_dir, output):
    if output.resolve() == input_dir.resolve() or input_dir.resolve() in output.resolve().parents:
        raise ValueError("Write analysis outputs outside the frozen input directory")
    frame, source_manifest, input_hashes = load_inputs(input_dir)
    coverage = coverage_audit(frame, START, END)
    temperature, baselines = rebase_temperature(frame[frame.dataset == "temperature_anomaly"])
    rebased = pd.concat([temperature, frame[frame.dataset == "co2_per_capita"]], ignore_index=True)
    selected_mask = ((rebased.dataset == "temperature_anomaly") & rebased.entity.isin(TEMP_ENTITIES)) | ((rebased.dataset == "co2_per_capita") & rebased.entity.isin(CO2_ENTITIES))
    selected_all_years = rebased[selected_mask]
    selected = selected_all_years[selected_all_years.year.between(START, END)].copy()
    expected_pairs = {(slug, entity) for slug, entities in (("temperature_anomaly", TEMP_ENTITIES), ("co2_per_capita", CO2_ENTITIES)) for entity in entities}
    actual_pairs = set(selected.groupby(["dataset", "entity"]).groups)
    if actual_pairs != expected_pairs:
        raise ValueError(f"Missing selected series: {sorted(expected_pairs-actual_pairs)}")
    summaries, trends, predictions, sensitivities = [], [], [], []
    for (dataset, entity), group in selected.groupby(["dataset", "entity"], sort=True):
        group = group.sort_values("year")
        if list(group.year) != list(range(START, END+1)) or group.value.isna().any():
            raise ValueError(f"{dataset}/{entity}: incomplete annual series; no automatic filling")
        values = group.value
        first, last = float(values.iloc[0]), float(values.iloc[-1])
        summaries.append({"dataset": dataset, "entity": entity, "n": len(group), "start_year": START, "end_year": END,
                          "mean": float(values.mean()), "median": float(values.median()), "interannual_sd": float(values.std(ddof=1)),
                          "minimum": float(values.min()), "maximum": float(values.max()), "first_value": first,
                          "last_value": last, "endpoint_change": last-first,
                          "endpoint_change_pct": (last/first-1)*100 if dataset == "co2_per_capita" and first != 0 else None})
        result, fitted = fit_trend(group.year, values, maxlags=3)
        trends.append({"dataset": dataset, "entity": entity, **result})
        fitted["dataset"], fitted["entity"] = dataset, entity
        predictions.append(fitted)
        for start in (1960, 1990):
            subset = group[group.year >= start]
            for lag in (1, 3, 5, 10):
                result, _ = fit_trend(subset.year, subset.value, maxlags=lag)
                sensitivities.append({"dataset": dataset, "entity": entity, **result})

    descriptive = pd.DataFrame(summaries)
    trends = pd.DataFrame(trends)
    sensitivity = pd.DataFrame(sensitivities)
    predictions = pd.concat(predictions, ignore_index=True)
    excluded = frame[frame.year > END].copy()
    excluded["exclusion_reason"] = "After fixed common end year 2024; 2026 is also an incomplete calendar year at retrieval"
    output.mkdir(parents=True, exist_ok=True)
    tables = {"coverage": coverage, "baseline_offsets": baselines, "descriptive_statistics": descriptive,
              "trends": trends, "sensitivity": sensitivity, "selected_annual": selected,
              "fitted_mean_intervals": predictions, "excluded_recent_rows": excluded}
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False, float_format="%.12g", na_rep="")
    create_charts(rebased, trends, predictions, coverage, output)
    write_report(output, descriptive, trends, sensitivity, coverage, baselines, source_manifest)
    produced = [output / f"{name}.csv" for name in tables] + [output / "REPORT.md"]
    produced += [output / f"{name}.{ext}" for name in ("01_temperature", "02_trends", "03_co2_per_person", "04_missing_data") for ext in ("png", "svg")]
    provenance = {
        "analysis_version": 1, "source_retrieved_at": source_manifest["retrieved_at"],
        "input_sha256": input_hashes,
        "code_sha256": {p.name: sha256(p) for p in sorted(HERE.glob("*.py"))},
        "requirements_sha256": sha256(HERE / "requirements.txt"),
        "sources_document_sha256": sha256(HERE / "SOURCES.md"),
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "matplotlib", "scipy", "statsmodels", "patsy", "pillow")},
        "settings": {"start_year": START, "end_year": END, "temperature_baseline": [1961, 1990],
                     "temperature_entities": TEMP_ENTITIES, "co2_entities": CO2_ENTITIES,
                     "hac_lags": 3, "hac_kernel": "bartlett", "small_sample_correction": True,
                     "confidence_level": 0.95, "reference_distribution": "t, n-2 degrees of freedom",
                     "sensitivity_start_years": [1960, 1990], "sensitivity_lags": [1, 3, 5, 10],
                     "missing_data": "no imputation; complete annual sequences required for modeling",
                     "random_seed": None, "randomness": "none"},
        "output_sha256": {p.name: sha256(p) for p in sorted(produced)},
    }
    (output / "run_manifest.json").write_text(json.dumps(provenance, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return {"selected_series": len(trends), "observations_analyzed": len(selected),
            "missing_co2_entity_years": int(coverage[coverage.dataset == "co2_per_capita"].missing_years.sum()),
            "figures": 4, "report": str(output / "REPORT.md")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=HERE / "inputs")
    parser.add_argument("--output-dir", type=Path, default=HERE / "output")
    args = parser.parse_args()
    try:
        result = run(args.input_dir, args.output_dir)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Analysis failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
