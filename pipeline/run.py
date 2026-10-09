import argparse
from pathlib import Path

from .clean import clean_all
from .ingest import fetch_sources, write_json
from .storage import open_database, replace_data
from .validate import validate, validate_database, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the CLIMATE/DATA SQLite database")
    parser.add_argument("--db", type=Path, default=Path("data/climate.db"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    tables, manifest = fetch_sources(args.raw_dir, offline=args.offline)
    observations = clean_all(tables)
    report = validate(observations)
    if not report["passed"]:
        raise SystemExit("Source validation failed: " + str(report))
    connection = open_database(args.db)
    replace_data(connection, observations, manifest["retrieved_at"], report)
    database_report = validate_database(connection)
    connection.close()
    report["database"] = database_report
    report["passed"] = report["passed"] and database_report["passed"]
    write_report(args.db.parent / "validation.json", report)
    manifest["validation"] = report
    write_json(args.db.parent / "manifest.json", manifest)
    if not report["passed"]:
        raise SystemExit("Database validation failed")
    print(f"Wrote {len(observations):,} observations to {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
