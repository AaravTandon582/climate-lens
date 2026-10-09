import math
from dataclasses import dataclass

from .config import DatasetSpec, SOURCES


@dataclass(frozen=True)
class Observation:
    dataset: str
    entity: str
    code: str | None
    year: int
    value: float
    unit: str


def clean(spec: DatasetSpec, rows: list[dict[str, str]]) -> list[Observation]:
    required = {"Entity", "Code", "Year", spec.value_column}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"{spec.slug}: missing columns {sorted(missing)}")
    output: list[Observation] = []
    for number, row in enumerate(rows, start=2):
        entity = row["Entity"].strip()
        try:
            year = int(row["Year"])
            value = float(row[spec.value_column])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{spec.slug}: invalid row {number}") from exc
        if not entity or not math.isfinite(value):
            raise ValueError(f"{spec.slug}: blank entity or non-finite value at row {number}")
        output.append(Observation(spec.slug, entity, row.get("Code") or None, year, value, spec.unit))
    return output


def clean_all(tables: dict[str, list[dict[str, str]]]) -> list[Observation]:
    specs = {spec.slug: spec for spec in SOURCES}
    return [observation for slug, rows in tables.items() for observation in clean(specs[slug], rows)]
