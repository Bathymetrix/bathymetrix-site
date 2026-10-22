"""Private, standard-library publication helpers; no scientific transformations."""

import csv
import hashlib
import itertools
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


def release_component(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z", value
    ):
        raise ValueError(f"invalid UTC release timestamp: {value!r}")
    datetime.fromisoformat(value[:19])  # Validate calendar/time, never round fractional identity.
    return quote(value, safe="")


def check_instrument(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(f"invalid instrument ID: {value!r}")
    return value


def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def fingerprint(path):
    checksum = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    return size, checksum.hexdigest()


def inspect_source_geocsv(path, instrument_id):
    """Read declarations and Station values; leave scientific parsing to the validator."""
    created = []
    station_index = None
    count = 0
    with Path(path).open(encoding="utf-8", newline="") as stream:
        lines = iter(stream)
        for line in lines:
            if line.startswith("#"):
                match = re.match(r"#\s*created\s*:\s*(.*?)\s*$", line)
                if match:
                    value = match.group(1)
                    release_component(value)
                    created.append(value)
                continue
            if not line.strip():
                raise ValueError(f"{path}: empty record")
            # csv.reader consumes any continuation lines in a quoted record.
            row = next(csv.reader(itertools.chain([line], lines), strict=True))
            if station_index is None:
                if row.count("Station") != 1:
                    raise ValueError(f"{path}: requires one Station column")
                width = len(row)
                station_index = row.index("Station")
            else:
                if len(row) != width or row[station_index] != instrument_id:
                    raise ValueError(f"{path}: ambiguous/mismatched Station; expected {instrument_id}")
                count += 1
    if len(created) != 1:
        raise ValueError(f"{path}: requires exactly one valid UTC #created, found {len(created)}")
    if station_index is None:
        raise ValueError(f"{path}: missing header")
    return created[0], count


def inspect_geocsv(path, instrument_id):
    created, count = inspect_source_geocsv(path, instrument_id)
    if not count:
        raise ValueError(f"{path}: no instrument records")
    return created


def check_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    release_component(manifest.get("release_id"))
    if manifest.get("testing_only") is not False:
        raise ValueError("production snapshot must have testing_only=false")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("snapshot requires a nonempty complete files inventory")
    instruments, filenames = set(), set()
    for entry in entries:
        instrument = check_instrument(entry.get("instrument_id"))
        filename = entry.get("filename")
        if filename != f"{instrument}.geocsv":
            raise ValueError(f"invalid production filename: {filename}")
        if instrument in instruments or filename in filenames:
            raise ValueError(f"duplicate instrument or filename: {instrument}")
        instruments.add(instrument)
        filenames.add(filename)
        if type(entry.get("size_bytes")) is not int or entry["size_bytes"] < 0:
            raise ValueError("invalid size_bytes")
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("invalid SHA-256")
        if not isinstance(entry.get("provenance"), dict):
            raise ValueError("missing provenance object")
    return entries


def verify_candidate(directory):
    directory = Path(directory).resolve()
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("candidate manifest cannot be a symlink")
    manifest = read_json(manifest_path)
    entries = check_manifest(manifest)
    if directory.name != release_component(manifest["release_id"]):
        raise ValueError("candidate directory must use the encoded release component")
    expected = {"manifest.json", *(entry["filename"] for entry in entries)}
    if {path.name for path in directory.iterdir()} != expected:
        raise ValueError("candidate inventory differs from frozen manifest")
    for entry in entries:
        path = directory / entry["filename"]
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"not a regular candidate file: {path}")
        if fingerprint(path) != (entry["size_bytes"], entry["sha256"]):
            raise ValueError(f"candidate bytes changed: {path}")
        if inspect_geocsv(path, entry["instrument_id"]) != manifest["release_id"]:
            raise ValueError(f"candidate #created differs from manifest: {path}")
    return manifest


def require_external_workspace(workspace, source_root):
    workspace, source_root = Path(workspace).resolve(), Path(source_root).resolve()
    if workspace == source_root or source_root in workspace.parents:
        raise ValueError("publication workspace must be outside the protected source tree")
    if workspace == source_root.parent or workspace in source_root.parents:
        raise ValueError("publication workspace must not contain the protected source tree")
    if any((parent / ".git").exists() for parent in (workspace, *workspace.parents)):
        raise ValueError("publication workspace must be outside Git checkouts")
    return workspace
