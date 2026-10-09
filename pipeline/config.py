from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetSpec:
    slug: str
    name: str
    url: str
    value_column: str
    unit: str
    min_value: float
    max_value: float


SOURCES = (
    DatasetSpec(
        "temperature_anomaly", "Global temperature anomaly", "https://ourworldindata.org/grapher/temperature-anomaly.csv", "Average", "degrees_celsius", -10.0, 10.0
    ),
    DatasetSpec(
        "co2_per_capita", "CO₂ emissions per person", "https://ourworldindata.org/grapher/co-emissions-per-capita.csv", "CO₂ emissions per capita", "tonnes_per_person", 0.0, 1000.0
    ),
)

SCHEMA_VERSION = 1
