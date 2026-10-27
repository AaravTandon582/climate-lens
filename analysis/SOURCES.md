# Source and method audit

Checked 2026-10-17. The analysis preserves the exact raw CSV bytes ingested on 2026-10-09, along with the original manifest. It does not fetch updated observations. Both CSV hashes were verified, and every central value was compared with the existing SQLite database.

## Temperature provenance limitation

The original README's Berkeley Earth / 1850–1900 description is not supported by archived metadata in this repository. The saved file contains `Average`, `Lower bound`, and `Upper bound` for World and two hemispheres. The [current OWID temperature page](https://ourworldindata.org/grapher/temperature-anomaly) identifies HadCRUT5 and an 1861–1890 reference. Its [current metadata](https://ourworldindata.org/grapher/temperature-anomaly.metadata.json) names 95% bounds, but reports an update on 2026-10-12, after the local snapshot was retrieved. These later metadata cannot conclusively authenticate the older CSV's producer version, interval level, or original baseline.

Accordingly, figures label the preserved bounds as source-supplied bounds with an unverified nominal level. A separate, explicit 1961–1990 baseline is calculated from each saved series. The mean and both bounds receive the same shift. Baseline uncertainty is not propagated, and these bounds are not combined with regression confidence intervals. Linear slopes are invariant to the constant shift. No threshold claim relative to the original pre-industrial baseline is made.

The original temperature file contains 2026 rows even though retrieval occurred during 2026. These are not treated as completed full-year values. Both 2025 and 2026 are excluded from the fixed 1960–2024 comparison because the emissions snapshot ends in 2024.

## CO₂ scope

The [OWID CO₂-per-capita documentation](https://ourworldindata.org/grapher/co-emissions-per-capita) identifies territorial fossil-fuel and industrial emissions divided by population, excluding land-use change. Country emissions exclude international aviation/shipping, while the global total includes them. The source is Global Carbon Project, with population estimates used by OWID. The saved CSV supplies no measurement-error intervals. World is retained as provided rather than calculated from unweighted country averages.

## Statistical method

[statsmodels robust covariance documentation](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_robustcov_results.html) describes HAC covariance and its lag, Bartlett-kernel, small-sample correction, and reference-distribution options. This analysis uses installed statsmodels 0.14.4 and records package versions. Three annual lags are the primary choice; 1, 3, 5, and 10 lags and two start years are sensitivity checks. Inference is conditional on a linear mean model and sufficiently weak residual dependence; it is not causal or a guarantee against all model misspecification.

See `output/run_manifest.json` for exact input and code hashes. Links above provide context, not live dependencies of the reproducible script. Data attribution and source-provider terms continue to apply to the preserved inputs and derived figures.
