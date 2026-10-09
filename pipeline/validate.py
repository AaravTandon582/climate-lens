import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .clean import Observation
from .config import SOURCES


def validate(observations: list[Observation]) -> dict:
    checks: list[dict] = []
    specs = {spec.slug: spec for spec in SOURCES}

    def check(name: str, passed: bool, details: str) -> None:
        checks.append({"name": name, "passed": passed, "details": details})

    keys = [(o.dataset, o.entity, o.year) for o in observations]
    check("no_duplicate_entity_year", len(keys) == len(set(keys)), f"{len(keys) - len(set(keys))} duplicates")
    check("years_in_range", all(1750 <= o.year <= 2100 for o in observations), "accepted range: 1750..2100")
    check("values_in_contract", all(specs[o.dataset].min_value <= o.value <= specs[o.dataset].max_value for o in observations), "checked source-specific bounds")
    check("observations_present", bool(observations), f"{len(observations)} cleaned observations")
    return {"passed": all(item["passed"] for item in checks), "checks": checks, "rows": len(observations)}


def validate_database(connection: sqlite3.Connection) -> dict:
    row_count = connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    duplicates = connection.execute("SELECT dataset_id, entity, year, COUNT(*) FROM observations GROUP BY 1,2,3 HAVING COUNT(*) > 1").fetchall()
    checks = [{"name": "foreign_keys", "passed": not foreign, "details": f"{len(foreign)} violations"}, {"name": "database_duplicates", "passed": not duplicates, "details": f"{len(duplicates)} duplicate keys"}]
    return {"passed": all(item["passed"] for item in checks), "checks": checks, "rows": row_count}


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
