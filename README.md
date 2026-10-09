# CLIMATE/DATA

Reproducible climate and environmental data pipeline. It downloads two public Our World in Data grapher datasets, cleans them into a common long format, validates the records, and writes a portable SQLite database.

## Data sources

- Global temperature anomaly: [OWID grapher](https://ourworldindata.org/grapher/temperature-anomaly.csv), sourced by OWID from Berkeley Earth. Values are degrees Celsius relative to the 1850–1900 baseline.
- CO₂ emissions per person: [OWID grapher](https://ourworldindata.org/grapher/co-emissions-per-capita.csv), sourced from the Global Carbon Project. Values are tonnes per person.

The URLs and expected columns are pinned in `pipeline/config.py`. The raw downloads are never edited; a SHA-256 manifest records exactly what was ingested.

## Reproduce

```bash
cd CLIMATE-DATA
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.run --db data/climate.db
python -m pipeline.validate_cli --db data/climate.db
```

The pipeline is idempotent: rerunning it replaces the two source tables and rebuilds the validation report. Use `--offline --raw-dir data/raw` to rebuild from already downloaded CSVs without network access.

## Outputs

- `data/raw/`: downloaded source CSVs (ignored by Git; regenerate with the command above)
- `data/climate.db`: SQLite database (ignored by Git)
- `data/manifest.json`: source URLs, download times, hashes, row counts, and validation results
- `data/validation.json`: machine-readable validation report

## Database design

`datasets` identifies each source and stores provenance. `observations` is a tidy fact table with one measurement per dataset, country/region, and year. Its uniqueness constraint prevents duplicate observations. `validation_results` stores check name, status, and details so a downstream consumer can audit a run. Foreign keys are enabled, and indexes support country/year and dataset/year queries.

Example query:

```sql
SELECT year, value AS temperature_anomaly_c
FROM observations JOIN datasets USING (dataset_id)
WHERE slug = 'temperature_anomaly' AND entity = 'United States';
```

## Validation checks

The run fails before publishing a database if a source is missing required columns, has duplicate entity/year rows, invalid years, non-numeric measurements, or impossible values. It also checks that every observation references a known dataset and that the SQLite uniqueness constraint holds.

## Project layout

```text
pipeline/config.py       source contracts and URLs
pipeline/ingest.py       download/read raw CSVs and compute hashes
pipeline/clean.py        normalize source-specific columns
pipeline/validate.py     data-quality checks and report writer
pipeline/storage.py      SQLite schema and atomic replacement
pipeline/run.py           command-line orchestration
tests/                    deterministic unit tests with fixture data
```

## License and attribution

The code in this repository is MIT licensed. Data remains under the licenses and terms of the [Our World in Data grapher catalog](https://ourworldindata.org/grapher). Keep the source URLs and attribution when redistributing derived data.
