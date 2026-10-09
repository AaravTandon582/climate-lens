import csv
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import certifi

from .config import DatasetSpec, SOURCES


def _download(url: str, destination: Path) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "CLIMATE-DATA/1.0"})
    context = __import__("ssl").create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        data = response.read()
    destination.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def fetch_sources(raw_dir: Path, *, offline: bool = False) -> tuple[dict[str, list[dict[str, str]]], dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[dict[str, str]]] = {}
    manifest = {"retrieved_at": datetime.now(UTC).isoformat(), "sources": {}}
    for spec in SOURCES:
        path = raw_dir / f"{spec.slug}.csv"
        if not offline:
            digest = _download(spec.url, path)
        elif not path.exists():
            raise FileNotFoundError(f"Offline mode requires {path}")
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError(f"{spec.slug}: source contains no rows")
        tables[spec.slug] = rows
        manifest["sources"][spec.slug] = {"url": spec.url, "sha256": digest, "rows": len(rows), "file": str(path)}
    return tables, manifest


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
