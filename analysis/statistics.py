"""Explicit baselines, missingness accounting, and annual trend uncertainty."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import t


TEMP_ENTITIES = ("World", "Northern Hemisphere", "Southern Hemisphere")
CO2_ENTITIES = ("World", "United States", "China", "India", "United Kingdom", "Brazil", "South Africa")


def rebase_temperature(frame, start=1961, end=1990):
    """Shift central values and supplied bounds by each entity's baseline mean.

    Baseline is treated as fixed; its uncertainty is not propagated into bounds.
    """
    result = frame.copy()
    baselines = []
    for entity, group in frame.groupby("entity", sort=True):
        baseline = group[group.year.between(start, end)]
        if set(baseline.year) != set(range(start, end + 1)) or baseline.value.isna().any():
            raise ValueError(f"{entity}: incomplete {start}-{end} baseline; no imputation allowed")
        offset = float(baseline.value.mean())
        mask = result.entity == entity
        for column in ("value", "lower", "upper"):
            result.loc[mask, column] = result.loc[mask, column] - offset
        baselines.append({"entity": entity, "baseline_start": start, "baseline_end": end,
                          "baseline_n": len(baseline), "subtracted_mean_c": offset})
    return result, pd.DataFrame(baselines)


def coverage_audit(frame, start, end):
    """Audit the fixed calendar grid, distinguishing absent rows and null values."""
    if end < start:
        raise ValueError("End year must not precede start year")
    rows = []
    for (dataset, entity), group in frame.groupby(["dataset", "entity"], sort=True):
        series = group.set_index("year").value
        years = np.arange(start, end + 1)
        values = series.reindex(years)
        available = series.dropna()
        missing = years[values.isna()]
        first = int(available.index.min()) if len(available) else None
        last = int(available.index.max()) if len(available) else None
        rows.append({
            "dataset": dataset, "entity": entity, "start_year": start, "end_year": end,
            "expected_years": len(years), "observed_years": int(values.notna().sum()),
            "missing_years": len(missing), "coverage_pct": float(values.notna().mean()*100),
            "absent_rows": int((~np.isin(years, series.index)).sum()),
            "null_values": int(group[group.year.between(start, end)].value.isna().sum()),
            "before_first_observation": int((missing < first).sum()) if first is not None else 0,
            "internal_gaps": int(((missing >= first) & (missing <= last)).sum()) if first is not None else 0,
            "after_last_observation": int((missing > last).sum()) if last is not None else 0,
            "first_observed_year": first, "last_observed_year": last,
            "missing_year_list": ";".join(map(str, missing)),
        })
    return pd.DataFrame(rows)


def fit_trend(years, values, maxlags=3):
    """OLS slope per decade with Bartlett HAC covariance and t-based intervals.

    Require complete, equally spaced annual data: row-lag HAC would otherwise
    misinterpret gaps as adjacent years. This is a conditional linear trend,
    not a forecast, causal estimate, or total observational uncertainty.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    if years.ndim != 1 or values.shape != years.shape or len(years) < 20:
        raise ValueError("Trend requires at least 20 annual observations of equal shape")
    if not np.isfinite(years).all() or not np.isfinite(values).all():
        raise ValueError("Trend inputs must be finite; missing values are not imputed")
    if not np.all(years == np.floor(years)) or not np.all(np.diff(years) == 1):
        raise ValueError("Trend requires consecutive sorted calendar years without duplicates")
    if not isinstance(maxlags, int) or not 0 <= maxlags < len(years)-2:
        raise ValueError("HAC lag must be a nonnegative integer below n-2")
    x = sm.add_constant((years-years.mean()) / 10.0)
    fitted = sm.OLS(values, x).fit()
    robust = fitted.get_robustcov_results(cov_type="HAC", maxlags=maxlags,
                                        kernel="bartlett", use_correction=True, use_t=True)
    bounds = robust.conf_int(alpha=0.05)
    residual = fitted.resid
    lag1 = float(np.corrcoef(residual[:-1], residual[1:])[0, 1]) if np.std(residual) > 1e-12 else None
    result = {
        "n": len(years), "start_year": int(years[0]), "end_year": int(years[-1]),
        "hac_lags": maxlags, "slope_per_decade": float(robust.params[1]),
        "ci95_low": float(bounds[1, 0]), "ci95_high": float(bounds[1, 1]),
        "slope_standard_error": float(robust.bse[1]),
        "residual_lag1_correlation": lag1,
        "r_squared": float(fitted.rsquared),
    }
    # Pointwise uncertainty in the fitted mean, not a prediction interval.
    se = np.sqrt(np.maximum(0, np.einsum("ij,jk,ik->i", x, robust.cov_params(), x)))
    margin = t.ppf(0.975, robust.df_resid) * se
    predictions = pd.DataFrame({"year": years.astype(int), "fitted": fitted.fittedvalues,
                                "mean_ci95_low": fitted.fittedvalues-margin,
                                "mean_ci95_high": fitted.fittedvalues+margin})
    return result, predictions
