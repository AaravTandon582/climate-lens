import sqlite3

import pytest

from pipeline.clean import Observation
from pipeline.storage import open_database, replace_data
from pipeline.validate import validate, validate_database


def test_validation_rejects_duplicate_keys() -> None:
    rows = [Observation("temperature_anomaly", "X", "X", 2000, 1.0, "degrees_celsius")] * 2
    report = validate(rows)
    assert not report["passed"]
    assert report["checks"][0]["name"] == "no_duplicate_entity_year"


def test_storage_enforces_referential_integrity(tmp_path) -> None:
    connection = open_database(tmp_path / "climate.db")
    report = validate([Observation("temperature_anomaly", "X", "X", 2000, 1.0, "degrees_celsius"), Observation("co2_per_capita", "X", "X", 2000, 2.0, "tonnes_per_person")])
    replace_data(connection, [Observation("temperature_anomaly", "X", "X", 2000, 1.0, "degrees_celsius"), Observation("co2_per_capita", "X", "X", 2000, 2.0, "tonnes_per_person")], "now", report)
    assert validate_database(connection)["passed"]
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO observations(dataset_id,entity,year,value,unit) VALUES (1,'X',2000,1,'degrees_celsius')")

