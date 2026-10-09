import argparse
import sqlite3
from pathlib import Path

from .validate import validate_database, write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/climate.db"))
    args = parser.parse_args()
    connection = sqlite3.connect(args.db)
    report = validate_database(connection)
    connection.close()
    write_report(args.db.parent / "validation.json", report)
    print(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
