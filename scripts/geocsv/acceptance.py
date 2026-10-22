"""Version 2 full-archive evidence and acceptance rules owned by bathymetrix-site."""

import importlib.metadata
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys

from snapshot import check_instrument, fingerprint, inspect_source_geocsv, read_json, verify_candidate

SCHEMA = "bathymetrix-geocsv-archive-validation"
VERSION = 2
CHECKS = (
    "strict_association", "identity", "sample_count", "samples_native",
    "samples_reference", "sample_interval", "start_native", "start_reference",
    "latitude", "longitude", "depth", "elevation",
)
LIMITS = {
    "association_time_seconds": 0.001,
    "association_rate_hz": 0.00001,
    "allow_first_segment": False,
    "coordinate_decimal_half_unit_degrees": 0.5e-6,
    "coordinate_reference_float32_spacings": 1,
    "sac_start_comparison_ns": 1000,
    "sample_comparison": "exact float32 arrays",
    "interval_comparison": "exact float32 native delta; reference within one float32 ULP",
    "interval_reference_max_ulps": 1,
    "depth_comparison": "exact SAC float32 or both undefined",
    "elevation_metres": 0,
}
SCOPE = "original MiniSEED and paired SAC; spectra excluded without counting"
MEASUREMENTS = {
    "association_offset_seconds", "association_rate_error_hz", "sample_count_error",
    "sample_error_native_counts", "sample_error_reference_counts", "interval_error_seconds",
    "interval_native_error_seconds", "interval_reference_ulps",
    "start_native_ns", "start_reference_ns", "latitude_error_deg", "latitude_limit_deg",
    "longitude_error_deg", "longitude_limit_deg", "depth_error_m", "elevation_error_m",
}


class AcceptanceError(ValueError):
    """Evidence is incomplete, failing, stale, or bound to different inputs."""


def software_versions():
    if sys.version_info < (3, 11):
        raise RuntimeError("archive validation and acceptance require Python 3.11+")
    from mermaid import geocsv
    versions = {name: importlib.metadata.version(name)
                for name in ("numpy", "pandas", "obspy", "mermaid-geocsv")}
    versions["mermaid-geocsv_distribution"] = versions["mermaid-geocsv"]
    versions["mermaid-geocsv"] = geocsv.__version__
    versions["python"] = ".".join(map(str, sys.version_info[:3]))
    versions["website_code_sha256"] = {
        name: fingerprint(Path(__file__).parent / name)[1] for name in (
            "snapshot.py", "create_snapshot.py", "validate_snapshot.py",
            "acceptance.py", "publish_snapshot.py")}
    versions["package_code_sha256"] = {
        path.name: fingerprint(path)[1]
        for path in sorted(Path(geocsv.__file__).parent.glob("*.py"))}
    return versions


def source_directories(manifest, source_root):
    root = Path(source_root).resolve(strict=True)
    sources = {}
    for entry in manifest["files"]:
        source = entry["provenance"].get("source_path")
        relative = PurePosixPath(source) if isinstance(source, str) else None
        if (relative is None or relative.is_absolute() or len(relative.parts) != 2
                or relative.parts[-1] != "geo_DET_REQ.csv" or ".." in relative.parts):
            raise AcceptanceError("production source_path must be <serial>/geo_DET_REQ.csv")
        path = root / str(relative)
        if root not in path.resolve(strict=True).parents:
            raise AcceptanceError("source escapes processed root")
        serial = path.parent
        if serial in sources.values():
            raise AcceptanceError("duplicate instrument source directory")
        sources[entry["instrument_id"]] = serial
    return root, sources


def inventory_sources(manifest, source_root):
    """Fingerprint all waveform inputs; do not open or count spectra/other products."""
    root, directories = source_directories(manifest, source_root)
    files = []
    for instrument, directory in sorted(directories.items()):
        paths = [(directory / "geo_DET_REQ.csv", "geocsv")]
        for parent, dirs, names in os.walk(directory, followlinks=False):
            # Source metadata and credentials are not validation inputs.
            dirs[:] = [name for name in dirs if name != ".git"]
            for name in names:
                lower = name.lower()
                if lower.endswith(".mseed"):
                    kind = "mseed"
                elif lower.endswith(".sac"):
                    kind = "sac"
                elif lower.endswith((".seed", ".miniseed", ".ms", ".mseed.gz", ".sac.gz", ".seed.gz")):
                    kind = "unsupported"
                else:
                    continue
                paths.append((Path(parent) / name, kind))
        for path, kind in paths:
            if path.is_symlink() or root not in path.resolve(strict=True).parents or not path.is_file():
                raise AcceptanceError(f"not a regular contained source input: {path.relative_to(root)}")
            size, checksum = fingerprint(path)
            files.append({"instrument_id": instrument, "path": path.relative_to(root).as_posix(),
                          "kind": kind, "size_bytes": size, "sha256": checksum})
    return sorted(files, key=lambda entry: (entry["instrument_id"], entry["path"]))


def check_staging_inventory(candidate, manifest, source_root):
    """Verify local recordless exclusions without adding them to the public inventory."""
    candidate, root = Path(candidate), Path(source_root).resolve(strict=True)
    path = candidate.parent.parent / "staging" / candidate.name / "inventory.json"
    sidecar = read_json(path)
    if sidecar.get("schema_version") != 1 or sidecar.get("release_id") != manifest["release_id"]:
        raise AcceptanceError("invalid local staging inventory")
    entries = sidecar.get("instruments")
    if not isinstance(entries, list):
        raise AcceptanceError("missing complete local staging inventory")
    published = {item["instrument_id"]: item for item in manifest["files"]}
    included, paths, ids = set(), set(), set()
    excluded = 0
    for item in entries:
        instrument = check_instrument(item.get("instrument_id"))
        relative = PurePosixPath(item.get("source_path", ""))
        if relative.is_absolute() or len(relative.parts) != 2 or ".." in relative.parts or relative.name != "geo_DET_REQ.csv":
            raise AcceptanceError("invalid staging source path")
        source = root / str(relative)
        if instrument in ids or str(relative) in paths or root not in source.resolve(strict=True).parents:
            raise AcceptanceError("duplicate or escaped staging source")
        ids.add(instrument)
        paths.add(str(relative))
        if item.get("status") == "included":
            expected = published.get(instrument)
            if expected is None or item["source_path"] != expected["provenance"]["source_path"] or (item.get("size_bytes"), item.get("sha256")) != (expected["size_bytes"], expected["sha256"]):
                raise AcceptanceError("staging included inventory differs from candidate")
            included.add(instrument)
        elif item.get("status") == "excluded_recordless":
            created, count = inspect_source_geocsv(source, instrument)
            if count or created != item.get("created") or fingerprint(source) != (item.get("size_bytes"), item.get("sha256")):
                raise AcceptanceError("recordless exclusion changed or has data records")
            for parent, _, names in os.walk(source.parent):
                if any(name.lower().endswith((".mseed", ".sac", ".seed", ".miniseed", ".ms", ".mseed.gz", ".sac.gz")) for name in names):
                    raise AcceptanceError(f"excluded recordless instrument has unexamined waveforms: {instrument}")
            excluded += 1
        else:
            raise AcceptanceError("unexplained staging exclusion")
    actual = {file.relative_to(root).as_posix() for file in root.glob("*/geo_DET_REQ.csv")}
    if paths != actual or included != set(published):
        raise AcceptanceError("local staging inventory omits source instruments")
    return {"inventory_sha256": fingerprint(path)[1], "excluded_recordless": excluded}


def pair_inventory(source_files):
    pairs = {}
    for entry in source_files:
        if entry["kind"] not in {"mseed", "sac"}:
            continue
        path = PurePosixPath(entry["path"])
        key = (entry["instrument_id"], str(path.with_suffix("")))
        pair = pairs.setdefault(key, {"instrument_id": key[0], "pair_id": key[1], "mseed": None, "sac": None})
        if pair[entry["kind"]] is not None:
            raise AcceptanceError(f"duplicate format for waveform pair: {key}")
        pair[entry["kind"]] = entry["path"]
    return [pairs[key] for key in sorted(pairs)]


def supported_product(pair):
    # Product identity is only a scope check, never an association/matching hint.
    return re.search(r"\.MER[0-9]*\.(DET|REQ)\.(WLT[1-5]|RAW)$", pair["pair_id"]) is not None


def summary(pairs, source_files):
    return {
        "source_files": len(source_files),
        "mseed_files": sum(item["kind"] == "mseed" for item in source_files),
        "sac_files": sum(item["kind"] == "sac" for item in source_files),
        "unsupported_files": sum(item["kind"] == "unsupported" for item in source_files),
        "pairs": len(pairs),
        **{status: sum(pair["status"] == status for pair in pairs)
           for status in ("passed", "failed", "missing", "unsupported", "unexamined")},
    }


def measured_maxima(pairs):
    maxima = {}
    for pair in pairs:
        for name, value in pair.get("measurements", {}).items():
            if value is None:
                continue
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise AcceptanceError(f"invalid measured value: {name}")
            maxima[name] = max(maxima.get(name, 0), value)
    return maxima


def check_measurements(pair):
    values = pair.get("measurements")
    if not isinstance(values, dict) or set(values) != MEASUREMENTS:
        raise AcceptanceError("incomplete scientific measurements")
    for name, value in values.items():
        if name == "depth_error_m" and value is None:
            continue  # Both undefined is checked by the independent SAC comparison.
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise AcceptanceError(f"invalid scientific measurement: {name}")
    for name in ("sample_count_error", "sample_error_native_counts", "sample_error_reference_counts",
                 "interval_native_error_seconds", "elevation_error_m"):
        if values[name] != 0:
            raise AcceptanceError(f"nonzero exact-comparison error: {name}")
    if values["depth_error_m"] not in (None, 0):
        raise AcceptanceError("depth differs at SAC float32 precision")
    if values["interval_reference_ulps"] > LIMITS["interval_reference_max_ulps"]:
        raise AcceptanceError("independent SAC interval differs by more than one float32 ULP")
    for name in ("start_native_ns", "start_reference_ns"):
        if values[name] > LIMITS["sac_start_comparison_ns"]:
            raise AcceptanceError("SAC timing comparison failed")
    for field in ("latitude", "longitude"):
        if values[f"{field}_error_deg"] > values[f"{field}_limit_deg"]:
            raise AcceptanceError("geographic comparison failed")
        # Maximum one float32 spacing anywhere in the allowed coordinate domain.
        maximum_spacing = 2 ** (-17 if field == "latitude" else -16)
        if not LIMITS["coordinate_decimal_half_unit_degrees"] <= values[f"{field}_limit_deg"] <= LIMITS["coordinate_decimal_half_unit_degrees"] + maximum_spacing:
            raise AcceptanceError("invalid geographic precision limit")
    if values["association_offset_seconds"] > LIMITS["association_time_seconds"]:
        raise AcceptanceError("strict association diagnostic exceeds its documented limit")


def require_acceptance(candidate, report_path, source_root):
    """Recompute coverage and fingerprints instead of trusting a success flag."""
    if report_path is None or source_root is None:
        raise AcceptanceError("a validation report and explicit --source-root are required")
    manifest = verify_candidate(candidate)
    report = read_json(report_path)
    if not isinstance(report, dict) or report.get("schema") != SCHEMA or type(report.get("schema_version")) is not int or report["schema_version"] != VERSION:
        raise AcceptanceError("unsupported full-archive validation report schema")
    if report.get("release_id") != manifest["release_id"]:
        raise AcceptanceError("validation release ID does not match candidate")
    expected = {"manifest_sha256": fingerprint(Path(candidate) / "manifest.json")[1], "files": manifest["files"]}
    if report.get("candidate") != expected:
        raise AcceptanceError("validation is bound to different manifest or staged files")
    if report.get("scope") != SCOPE or report.get("limits") != LIMITS:
        raise AcceptanceError("validation scope or scientific limits differ")
    if report.get("software") != software_versions():
        raise AcceptanceError("validation code or dependency versions differ; rerun validation")
    if report.get("staging") != check_staging_inventory(candidate, manifest, source_root):
        raise AcceptanceError("local staging exclusions changed or incomplete")
    sources = inventory_sources(manifest, source_root)
    if report.get("source_files") != sources:
        raise AcceptanceError("source waveform inventory/fingerprints changed or incomplete")
    geo_by_id = {entry["instrument_id"]: entry for entry in manifest["files"]}
    for source in sources:
        if source["kind"] == "geocsv":
            entry = geo_by_id[source["instrument_id"]]
            if (source["size_bytes"], source["sha256"]) != (entry["size_bytes"], entry["sha256"]):
                raise AcceptanceError("processed GeoCSV and frozen candidate differ")
    expected_pairs = pair_inventory(sources)
    pairs = report.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != len(expected_pairs):
        raise AcceptanceError("pair accounting is incomplete")
    for expected_pair, pair in zip(expected_pairs, pairs):
        if not isinstance(pair, dict) or any(pair.get(key) != value for key, value in expected_pair.items()):
            raise AcceptanceError("pair inventory differs or has omissions/duplicates")
        if not pair["mseed"] or not pair["sac"] or not supported_product(pair):
            raise AcceptanceError("missing pair or unsupported waveform product")
        checks = pair.get("checks")
        if (pair.get("status") != "passed" or not isinstance(checks, dict)
                or set(checks) != set(CHECKS) or any(value is not True for value in checks.values())):
            raise AcceptanceError(f"scientific checks failed or unexamined: {pair['pair_id']}")
        check_measurements(pair)
        if not isinstance(pair.get("association"), dict) or pair["association"].get("type") != "single_segment":
            raise AcceptanceError("missing strict association evidence")
    if report.get("failures") != []:
        raise AcceptanceError("scientific validation contains failures")
    if any(source["kind"] == "unsupported" for source in sources):
        raise AcceptanceError("unsupported waveform inputs remain")
    counts = report.get("summary")
    if (not isinstance(counts, dict) or any(type(value) is not int for value in counts.values())
            or counts != summary(pairs, sources) or report.get("maxima") != measured_maxima(pairs)):
        raise AcceptanceError("validation counts or maxima are inconsistent")
    instruments = report.get("instruments")
    expected_instruments = sorted(geo_by_id)
    if not isinstance(instruments, list) or [item.get("instrument_id") for item in instruments] != expected_instruments:
        raise AcceptanceError("instrument accounting is incomplete")
    for item in instruments:
        count = sum(pair["instrument_id"] == item["instrument_id"] for pair in pairs)
        if item.get("pairs") != count or item.get("status") != "complete":
            raise AcceptanceError("instrument coverage is incomplete")
    if report.get("status") != "passed":
        raise AcceptanceError("validation did not pass")
    return report
