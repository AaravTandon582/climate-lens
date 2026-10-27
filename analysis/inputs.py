"""Read the pinned raw CSVs, verifying their original ingestion hashes."""

import hashlib
import json

import numpy as np
import pandas as pd


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(directory):
    manifest_path = directory / "ingest_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = []
    hashes = {manifest_path.name: sha256(manifest_path)}
    for slug, column in (("temperature_anomaly", "Average"), ("co2_per_capita", "CO₂ emissions per capita")):
        path = directory / f"{slug}.csv"
        hashes[path.name] = sha256(path)
        if hashes[path.name] != manifest["sources"][slug]["sha256"]:
            raise ValueError(f"Hash mismatch for {path}; input snapshot changed")
        frame = pd.read_csv(path)
        required = {"Entity", "Code", "Year", column}
        if slug == "temperature_anomaly":
            required |= {"Lower bound", "Upper bound"}
        if not required.issubset(frame.columns):
            raise ValueError(f"{slug}: missing columns {sorted(required-set(frame.columns))}")
        if len(frame) != manifest["sources"][slug]["rows"]:
            raise ValueError(f"{slug}: row count differs from ingestion manifest")
        frame = frame.rename(columns={"Entity": "entity", "Code": "code", "Year": "year", column: "value",
                                      "Lower bound": "lower", "Upper bound": "upper"})
        if frame.entity.isna().any() or frame.entity.str.strip().eq("").any():
            raise ValueError(f"{slug}: blank entity")
        frame["year"] = pd.to_numeric(frame.year, errors="raise")
        if not np.isfinite(frame.year).all() or not (frame.year == frame.year.round()).all():
            raise ValueError(f"{slug}: invalid year")
        frame["year"] = frame.year.astype(int)
        if frame.duplicated(["entity", "year"]).any():
            raise ValueError(f"{slug}: duplicate entity/year")
        for field in (["value", "lower", "upper"] if slug == "temperature_anomaly" else ["value"]):
            frame[field] = pd.to_numeric(frame[field], errors="raise")
            if np.isinf(frame[field]).any():
                raise ValueError(f"{slug}: infinite {field}")
        if slug == "temperature_anomaly":
            complete = frame[["lower", "value", "upper"]].dropna()
            if ((complete.lower > complete.value) | (complete.value > complete.upper)).any():
                raise ValueError("Temperature estimate outside supplied uncertainty bounds")
        elif (frame.value.dropna() < 0).any():
            raise ValueError("Negative CO2 emissions per person")
        frame["dataset"] = slug
        frames.append(frame)
    return pd.concat(frames, ignore_index=True).sort_values(["dataset", "entity", "year"]), manifest, hashes
