#!/usr/bin/env python3
"""Freeze a complete GeoCSV snapshot outside Git; never edit processed sources."""

import argparse
import csv
import os
import shutil
import tempfile
from pathlib import Path

from snapshot import (
    check_instrument, check_manifest, fingerprint, inspect_geocsv, json_bytes,
    read_json, release_component, require_external_workspace, verify_candidate,
)


def read_inventory(path):
    """Require an explicit reviewed serial-to-instrument mapping, without guessing."""
    mapping = {}
    instruments = set()
    with Path(path).open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["instrument_serial", "instrument_id"]:
            raise ValueError("inventory columns must be instrument_serial,instrument_id")
        for row in rows:
            serial = row["instrument_serial"]
            instrument = check_instrument(row["instrument_id"])
            check_instrument(serial)
            if serial in mapping or instrument in instruments:
                raise ValueError(f"duplicate serial or instrument: {serial}, {instrument}")
            mapping[serial] = instrument
            instruments.add(instrument)
    if not mapping:
        raise ValueError("empty instrument inventory")
    return mapping


def create_snapshot(source_root, workspace, inventory_path, previous_manifest=None):
    source_root = Path(source_root).resolve(strict=True)
    workspace = require_external_workspace(workspace, source_root)
    mapping = read_inventory(inventory_path)
    discovered = {path.parent.name for path in source_root.glob("*/geo_DET_REQ.csv")}
    missing = set(mapping) - discovered
    unlisted = discovered - set(mapping)
    if missing or unlisted:
        raise ValueError(f"incomplete inventory: missing sources={sorted(missing)}, unlisted serials={sorted(unlisted)}")
    if previous_manifest:
        previous = check_manifest(read_json(previous_manifest))
        missing_ids = {entry["instrument_id"] for entry in previous} - set(mapping.values())
        if missing_ids:
            raise ValueError(f"previously published instruments missing: {sorted(missing_ids)}")
    snapshots = workspace / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".candidate-", dir=snapshots) as temporary:
        candidate = Path(temporary)
        entries = []
        release = None
        for serial, instrument in sorted(mapping.items(), key=lambda pair: pair[1]):
            source = source_root / serial / "geo_DET_REQ.csv"
            resolved = source.resolve(strict=True)
            if source.is_symlink() or source_root not in resolved.parents:
                raise ValueError(f"source escapes processed root: {source}")
            before = source.stat()
            target = candidate / f"{instrument}.geocsv"
            with source.open("rb") as reader, target.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
            after = source.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError(f"source changed during staging: {source}")
            created = inspect_geocsv(target, instrument)
            if release is not None and created != release:
                raise ValueError(f"mixed #created timestamps: {release!r} and {created!r}")
            release = created
            size, checksum = fingerprint(target)
            entries.append({
                "instrument_id": instrument, "filename": target.name,
                "size_bytes": size, "sha256": checksum,
                "provenance": {"source_path": f"{serial}/geo_DET_REQ.csv", "manual_edits": False},
            })
        manifest = {"release_id": release, "testing_only": False, "files": entries}
        payload = json_bytes(manifest)
        (candidate / "manifest.json").write_bytes(payload)
        destination = snapshots / release_component(release)
        if destination.exists():
            verify_candidate(destination)
            if (destination / "manifest.json").read_bytes() != payload:
                raise FileExistsError(f"conflicting immutable snapshot: {destination}")
            return destination
        # Rename the whole candidate only when complete. No partial frozen release.
        # A concurrent creator cannot replace an existing nonempty directory.
        os.rename(candidate, destination)
    verify_candidate(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path,
                        help="reviewed CSV mapping: instrument_serial,instrument_id")
    parser.add_argument("--previous-manifest", type=Path,
                        help="required operationally after first publication to detect missing instruments")
    args = parser.parse_args()
    try:
        print(create_snapshot(args.source_root, args.workspace, args.inventory, args.previous_manifest))
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(1, f"Snapshot not created: {exc}\n")


if __name__ == "__main__":
    main()
