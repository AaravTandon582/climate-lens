import sqlite3
from pathlib import Path

from .clean import Observation
from .config import SCHEMA_VERSION, SOURCES


SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (dataset_id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, source_url TEXT NOT NULL, unit TEXT NOT NULL, schema_version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS observations (observation_id INTEGER PRIMARY KEY, dataset_id INTEGER NOT NULL REFERENCES datasets(dataset_id), entity TEXT NOT NULL, entity_code TEXT, year INTEGER NOT NULL CHECK(year BETWEEN 1750 AND 2100), value REAL NOT NULL, unit TEXT NOT NULL, UNIQUE(dataset_id, entity, year));
CREATE TABLE IF NOT EXISTS validation_results (validation_id INTEGER PRIMARY KEY, run_at TEXT NOT NULL, check_name TEXT NOT NULL, passed INTEGER NOT NULL, details TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_observations_dataset_year ON observations(dataset_id, year);
CREATE INDEX IF NOT EXISTS idx_observations_entity_year ON observations(entity, year);
"""


def open_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def replace_data(connection: sqlite3.Connection, observations: list[Observation], run_at: str, report: dict) -> None:
    with connection:
        connection.execute("DELETE FROM observations")
        connection.execute("DELETE FROM datasets")
        ids = {}
        for spec in SOURCES:
            cursor = connection.execute("INSERT INTO datasets(slug,name,source_url,unit,schema_version) VALUES (?,?,?,?,?)", (spec.slug, spec.name, spec.url, spec.unit, SCHEMA_VERSION))
            ids[spec.slug] = cursor.lastrowid
        connection.executemany("INSERT INTO observations(dataset_id,entity,entity_code,year,value,unit) VALUES (?,?,?,?,?,?)", [(ids[o.dataset], o.entity, o.code, o.year, o.value, o.unit) for o in observations])
        connection.execute("DELETE FROM validation_results")
        connection.executemany("INSERT INTO validation_results(run_at,check_name,passed,details) VALUES (?,?,?,?)", [(run_at, item["name"], int(item["passed"]), item["details"]) for item in report["checks"]])
