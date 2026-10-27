import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.inputs import load_inputs
from analysis.run import run
from analysis.statistics import coverage_audit, fit_trend, rebase_temperature


INPUTS = Path(__file__).resolve().parents[1] / "analysis" / "inputs"


def test_known_slope_units_and_constant_shift_invariance():
    years = np.arange(1960, 2025)
    values = 2 + 0.3 * (years - 1960) / 10
    result, predictions = fit_trend(years, values)
    shifted, _ = fit_trend(years, values + 17)
    assert result["slope_per_decade"] == pytest.approx(0.3)
    assert shifted["slope_per_decade"] == pytest.approx(0.3)
    assert result["ci95_low"] == pytest.approx(0.3)
    assert result["ci95_high"] == pytest.approx(0.3)
    np.testing.assert_allclose(predictions.fitted, values)


def test_hac_reflects_correlated_residuals():
    years = np.arange(1960, 2025)
    values = 0.02 * (years-1960) + 0.2 * np.sin(np.arange(len(years)) / 3)
    independent, _ = fit_trend(years, values, maxlags=0)
    correlated, predictions = fit_trend(years, values, maxlags=3)
    assert correlated["slope_per_decade"] == pytest.approx(independent["slope_per_decade"])
    assert correlated["slope_standard_error"] > independent["slope_standard_error"]
    assert correlated["residual_lag1_correlation"] > 0.8
    assert (predictions.mean_ci95_low <= predictions.fitted).all()
    assert (predictions.mean_ci95_high >= predictions.fitted).all()


@pytest.mark.parametrize("defect", ["gap", "duplicate", "nan", "infinite", "short", "fractional", "reversed"])
def test_bad_time_series_is_not_silently_compressed_or_filled(defect):
    years = np.arange(1960, 2025, dtype=float)
    values = np.arange(len(years), dtype=float)
    if defect == "gap":
        years, values = np.delete(years, 10), np.delete(values, 10)
    elif defect == "duplicate":
        years[10] = years[9]
    elif defect == "nan":
        values[10] = np.nan
    elif defect == "infinite":
        values[10] = np.inf
    elif defect == "short":
        years, values = years[:10], values[:10]
    elif defect == "fractional":
        years += 0.5
    else:
        years, values = years[::-1], values[::-1]
    with pytest.raises(ValueError):
        fit_trend(years, values)


def test_rebasing_preserves_source_bounds_and_rejects_missing_baseline():
    years = np.arange(1960, 2025)
    value = np.arange(len(years)) * 0.02
    raw = pd.DataFrame({"entity": "World", "year": years, "value": value, "lower": value-0.1, "upper": value+0.2})
    result, baselines = rebase_temperature(raw)
    assert result[result.year.between(1961, 1990)].value.mean() == pytest.approx(0, abs=1e-12)
    np.testing.assert_allclose(result.upper-result.lower, raw.upper-raw.lower)
    assert baselines.iloc[0].baseline_n == 30
    np.testing.assert_allclose(raw.value, value)  # input not mutated
    with pytest.raises(ValueError, match="incomplete"):
        rebase_temperature(raw[raw.year != 1970])


def test_missingness_distinguishes_absent_null_and_structural_edges():
    frame = pd.DataFrame({"dataset": "co2_per_capita", "entity": ["A", "A", "A", "A", "B"],
                          "year": [1959, 1961, 1963, 1965, 1962], "value": [1, np.nan, 2, 3, 0]})
    audit = coverage_audit(frame, 1960, 1964).set_index("entity")
    assert audit.loc["A", "missing_years"] == 4
    assert audit.loc["A", "absent_rows"] == 3
    assert audit.loc["A", "null_values"] == 1
    assert audit.loc["A", "internal_gaps"] == 4
    assert audit.loc["B", "observed_years"] == 1  # an actual zero is observed
    assert audit.loc["B", "before_first_observation"] == 2
    assert audit.loc["B", "after_last_observation"] == 2


def test_snapshot_hash_mismatch_fails_before_analysis(tmp_path):
    for path in INPUTS.iterdir():
        if path.is_file():
            shutil.copyfile(path, tmp_path / path.name)
    with (tmp_path / "temperature_anomaly.csv").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="Hash mismatch"):
        load_inputs(tmp_path)


def test_full_analysis_is_reproducible_and_reports_only_completed_common_years(tmp_path, monkeypatch):
    from analysis import charts

    original_save = charts.save

    def check_and_save(fig, output, name, footer):
        if name == "03_co2_per_person":
            panels = [axis for axis in fig.axes if axis.lines]
            assert len(panels) == 7
            assert len({axis.get_ylim() for axis in panels}) == 1
            for axis in panels:
                lower, upper = axis.get_ylim()
                for line in axis.lines:
                    values = np.asarray(line.get_ydata(), dtype=float)
                    assert np.nanmin(values) >= lower
                    assert np.nanmax(values) <= upper
        original_save(fig, output, name, footer)

    monkeypatch.setattr(charts, "save", check_and_save)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS.iterdir() if p.is_file()}
    first, second = tmp_path / "first", tmp_path / "second"
    summary = run(INPUTS, first)
    run(INPUTS, second)
    assert summary["selected_series"] == 10
    assert summary["observations_analyzed"] == 650
    assert summary["missing_co2_entity_years"] == 499
    manifest = json.loads((first / "run_manifest.json").read_text())
    assert manifest == json.loads((second / "run_manifest.json").read_text())
    for name, expected_hash in manifest["output_sha256"].items():
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == expected_hash
        assert (first / name).read_bytes() == (second / name).read_bytes()
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUTS.iterdir() if p.is_file()}
    selected = pd.read_csv(first / "selected_annual.csv")
    assert selected.year.min() == 1960
    assert selected.year.max() == 2024
    excluded = pd.read_csv(first / "excluded_recent_rows.csv")
    assert len(excluded) == 6
    assert set(excluded.year) == {2025, 2026}
    trends = pd.read_csv(first / "trends.csv")
    assert (trends.n == 65).all()
    assert (trends.ci95_low <= trends.slope_per_decade).all()
    assert (trends.ci95_high >= trends.slope_per_decade).all()
    assert len(pd.read_csv(first / "sensitivity.csv")) == 80
    assert len(list(first.glob("*.png"))) == len(list(first.glob("*.svg"))) == 4
