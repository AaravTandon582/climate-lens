# First analysis

Open [the generated findings report](output/REPORT.md) for results, four figures, uncertainty, and missing-data treatment. [SOURCES.md](SOURCES.md) records a source-metadata discrepancy in the original project description and how the analysis avoids relying on it.

## Reproduce offline

From the ClimateLens project root, using Python 3.11–3.13 (recorded run: 3.13.9):

```bash
python3 -m venv .venv-analysis
source .venv-analysis/bin/activate
python -m pip install -r analysis/requirements.txt
python -m analysis.run
python -m pytest -q
```

Dependency installation needs package access once. The analysis itself makes no network requests. It reads the bundled `analysis/inputs/` snapshot, verifies its hashes, and writes `analysis/output/`. It does not update raw data or the existing SQLite database. Inputs are preserved byte-for-byte from the prior ingestion; the original manifest retains its original paths and timestamp.

On the machine where these outputs were created, the available scientific Python environment can run the same commands without installation:

```bash
/opt/anaconda3/bin/python -m analysis.run
/opt/anaconda3/bin/python -m pytest -q
```

Custom locations are supported:

```bash
python -m analysis.run --input-dir analysis/inputs --output-dir /tmp/climatelens-analysis
```

The input directory must contain both CSVs and `ingest_manifest.json`, with matching hashes. Output paths must be outside the input directory. Existing generated files at the output location are replaced; unrelated files are not removed. For a different snapshot, preserve it with a matching ingestion manifest and review the fixed date interval and entity selections before comparing results.

## Outputs

| Artifact | Contents |
|---|---|
| `REPORT.md` | Questions, computed findings, methods, caveats, and all figures |
| `01_temperature.png` / `.svg` | Global history with source bounds; modern fit with pointwise HAC interval |
| `02_trends.png` / `.svg` | Global/hemispheric temperature and selected CO₂ trend intervals |
| `03_co2_per_person.png` / `.svg` | Seven CO₂ trajectories on common axes |
| `04_missing_data.png` / `.svg` | Full-file CO₂ coverage and missing entity-year matrix |
| `selected_annual.csv` | The 650 observations used for primary analyses; temperatures rebased to 1961–1990 |
| `descriptive_statistics.csv` | Means, medians, interannual standard deviations, ranges, and endpoints |
| `trends.csv` | Ten OLS trends with 95% HAC intervals and residual diagnostics |
| `sensitivity.csv` | 80 fits: two start years × four lag settings × ten series |
| `coverage.csv` | All 234 saved dataset/entity pairs, missing counts, types, and exact year lists |
| `baseline_offsets.csv` | Exact means subtracted from each temperature series |
| `fitted_mean_intervals.csv` | Pointwise model intervals, distinct from source bounds |
| `excluded_recent_rows.csv` | Six recent temperature rows outside the comparison window |
| `run_manifest.json` | Settings, versions, input/code hashes, output hashes |

`statistics.py` contains reusable calculations; `inputs.py` verifies the snapshot; `charts.py` renders static figures; `report.py` writes results directly from computed tables; `run.py` orchestrates the analysis. No notebook execution order or manually copied statistics are required.

## Interpretation

The main period is 1960–2024. Temperature is explicitly relative to each saved series' 1961–1990 mean. CO₂ values are annual tonnes per person. The World aggregate comes from the source; selected countries are illustrative, not a representative sample.

Missing values are never filled. The fixed annual grid reveals absent rows as well as explicit nulls. Models require complete consecutive annual series; irregular sequences fail rather than compressing calendar gaps into HAC lags. All ten selected series are complete in this snapshot, but the full CO₂ file has gaps.

Trend intervals use Bartlett HAC covariance with three annual lags, a finite-sample correction, and a t reference. Sensitivity checks use lags 1/3/5/10 and starts 1960/1990. These exploratory model intervals are not measurement-error bounds, causal effects, predictions, or multiple-comparison-adjusted tests. No uncertainty values are invented for the CO₂ source.

The procedure is deterministic: no random seed is required. Tests include known slopes, baseline invariance, gap rejection, missingness accounting, snapshot integrity, and byte-for-byte repeated output generation in the recorded environment.

## Recorded validation

On 2026-10-17, `/opt/anaconda3/bin/python -m pytest -q -W error` completed with **15 passed in 8.57 seconds**, including the existing pipeline tests. Two independent analysis runs produced identical report, table, PNG, SVG, and manifest bytes in the recorded environment. The final output/code hashes and report links were checked, and all four figures were visually inspected. The CO₂ plot has a regression check ensuring all seven series fit inside their shared axes.

Passing tests verifies the calculations and reproducibility exercised here, not the adequacy of every statistical assumption. In particular, persistent CO₂ residuals limit interpretation of the simple trend intervals; the report discusses this explicitly.
