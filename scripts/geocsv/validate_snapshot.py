#!/usr/bin/env python3
"""Validate every original MiniSEED/SAC pair against a frozen GeoCSV snapshot."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

from acceptance import (
    CHECKS, LIMITS, SCHEMA, SCOPE, VERSION, check_staging_inventory, inventory_sources, measured_maxima,
    pair_inventory, software_versions, source_directories, summary, supported_product,
)
from snapshot import fingerprint, json_bytes, require_external_workspace, verify_candidate


def compare_pair(trace, reference_path, output_path):
    """Call the public exporter; compare only the documented scientific surfaces."""
    import numpy as np
    from mermaid import geocsv
    from obspy.io.sac import SACTrace

    checks = dict.fromkeys(CHECKS, False)
    checks["strict_association"] = trace.stats.geocsv.association.type == "single_segment"
    geocsv.write_sac(trace, output_path)
    actual = SACTrace.read(str(output_path))
    # Read the independent SAC only AFTER association/export; never supply it upstream.
    reference = SACTrace.read(str(reference_path))
    written_trace = actual.to_obspy_trace(round_sampling_interval=False)
    reference_trace = reference.to_obspy_trace(round_sampling_interval=False)
    checks["identity"] = written_trace.id == trace.id == reference_trace.id
    checks["sample_count"] = actual.npts == trace.stats.npts == reference.npts
    native = trace.data.astype(np.float32)
    checks["samples_native"] = np.array_equal(actual.data, native)
    checks["samples_reference"] = np.array_equal(actual.data, reference.data)
    native_interval_error = abs(actual.delta - float(np.float32(trace.stats.delta)))
    # Mirror mermaid-geocsv's public-NumPy one-ULP verification pattern.
    # maxulp=inf requests diagnostic distance even for failures; the acceptance
    # bound below remains exactly one. This does not relax association matching.
    interval_ulps = (float(np.testing.assert_array_max_ulp(
        np.float32(actual.delta), np.float32(reference.delta), maxulp=np.inf).max())
        if np.isfinite([actual.delta, reference.delta]).all() and min(actual.delta, reference.delta) > 0 else None)
    checks["sample_interval"] = native_interval_error == 0 and interval_ulps is not None and interval_ulps <= LIMITS["interval_reference_max_ulps"]
    measurements = {
        "association_offset_seconds": abs(float(trace.stats.geocsv.association.waveform_start_offset_seconds)),
        "association_rate_error_hz": abs(float(trace.stats.geocsv.SampleRate) - trace.stats.sampling_rate),
        "start_native_ns": abs(written_trace.stats.starttime.ns - trace.stats.starttime.ns),
        "start_reference_ns": abs(written_trace.stats.starttime.ns - reference_trace.stats.starttime.ns),
        "interval_error_seconds": max(abs(actual.delta - float(np.float32(trace.stats.delta))), abs(actual.delta - reference.delta)),
        "interval_native_error_seconds": native_interval_error,
        "interval_reference_ulps": interval_ulps,
    }
    for label, comparison in (("native", native), ("reference", reference.data)):
        measurements[f"sample_error_{label}_counts"] = (
            float(np.max(np.abs(actual.data.astype(np.float64) - comparison.astype(np.float64))))
            if len(actual.data) == len(comparison) and len(comparison) else None)
    measurements["sample_count_error"] = max(abs(actual.npts - trace.stats.npts), abs(actual.npts - reference.npts))
    checks["start_native"] = measurements["start_native_ns"] <= LIMITS["sac_start_comparison_ns"]
    checks["start_reference"] = measurements["start_reference_ns"] <= LIMITS["sac_start_comparison_ns"]
    for field, key in (("latitude", "stla"), ("longitude", "stlo")):
        value, expected = getattr(actual, key), getattr(reference, key)
        if value is None or expected is None or not np.isfinite([value, expected]).all():
            measurements[f"{field}_error_deg"] = None
            measurements[f"{field}_limit_deg"] = None
            checks[field] = False
        else:
            tolerance = LIMITS["coordinate_decimal_half_unit_degrees"] + abs(float(np.spacing(np.float32(expected))))
            error = abs(value - expected)
            measurements[f"{field}_error_deg"] = error
            measurements[f"{field}_limit_deg"] = tolerance
            checks[field] = error <= tolerance
    checks["depth"] = actual.stdp == reference.stdp
    measurements["depth_error_m"] = abs(actual.stdp - reference.stdp) if actual.stdp is not None and reference.stdp is not None else None
    checks["elevation"] = actual.stel == reference.stel == LIMITS["elevation_metres"]
    measurements["elevation_error_m"] = max(abs(actual.stel), abs(reference.stel)) if actual.stel is not None and reference.stel is not None else None
    source = trace.stats.geocsv
    association = {"type": source.association.type, "dataset_index": int(source.dataset_index),
                   "source_record_index": int(source.source_record_index)}
    checks = {key: bool(value) for key, value in checks.items()}
    measurements = {key: (None if value is None or not np.isfinite(value) else float(value))
                    for key, value in measurements.items()}
    return checks, measurements, association


def validate_snapshot(candidate, source_root, report_path, *, batch_size=128, progress=None):
    if sys.version_info < (3, 11):
        raise RuntimeError("full-archive validation requires Python 3.11+")
    from mermaid import geocsv
    from obspy import Stream, read as read_waveforms

    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    candidate, source_root = Path(candidate).resolve(), Path(source_root).resolve(strict=True)
    report_path = Path(report_path).resolve()
    require_external_workspace(report_path.parent, source_root)
    if any((parent / ".git").exists() for parent in (candidate, *candidate.parents)):
        raise ValueError("candidate must be outside Git")
    if report_path == candidate or candidate in report_path.parents:
        raise ValueError("validation report must remain separate from the frozen candidate")
    manifest = verify_candidate(candidate)
    frozen_manifest = fingerprint(candidate / "manifest.json")[1]
    software = software_versions()
    staging = check_staging_inventory(candidate, manifest, source_root)
    source_files = inventory_sources(manifest, source_root)
    pairs = [{**pair, "status": "unexamined", "checks": dict.fromkeys(CHECKS), "measurements": {}}
             for pair in pair_inventory(source_files)]
    report = {
        "schema": SCHEMA, "schema_version": VERSION,
        "release_id": manifest["release_id"], "scope": SCOPE, "limits": LIMITS,
        "candidate": {"manifest_sha256": frozen_manifest, "files": manifest["files"]},
        "software": software, "staging": staging, "source_files": source_files, "pairs": pairs,
        "instruments": [], "failures": [],
        "started_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    def fail(instrument, pair, stage, detail):
        # Public reports use source-relative IDs, never machine-specific paths.
        detail = str(detail).replace(str(source_root) + "/", "").replace(str(candidate) + "/", "")
        if pair is not None:
            detail = detail.replace(str(scratch) + "/", "scratch/")
        report["failures"].append({"instrument_id": instrument,
                                   "pair_id": pair["pair_id"] if pair else None,
                                   "stage": stage, "detail": detail})

    # Only original waveform formats enter this inventory. Spectra are neither read nor counted.
    for source in source_files:
        if source["kind"] == "unsupported":
            fail(source["instrument_id"], None, "unsupported_format", source["path"])
        elif source["kind"] == "geocsv":
            entry = next(item for item in manifest["files"] if item["instrument_id"] == source["instrument_id"])
            if (source["size_bytes"], source["sha256"]) != (entry["size_bytes"], entry["sha256"]):
                fail(source["instrument_id"], None, "source_geocsv", "processed GeoCSV differs from frozen candidate")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sac-exports-", dir=report_path.parent) as temporary:
        scratch = Path(temporary)
        for entry in manifest["files"]:
            instrument = entry["instrument_id"]
            selected = [pair for pair in pairs if pair["instrument_id"] == instrument]
            before_failures = len(report["failures"])
            item = {"instrument_id": instrument, "pairs": len(selected), "status": "unexamined"}
            report["instruments"].append(item)
            if progress:
                progress(f"{instrument}: {len(selected)} original waveform pairs")
            try:
                tables = geocsv.read(candidate / entry["filename"])
                item["event_records"] = sum(int(table["MethodIdentifier"].str.startswith("Algorithm(event)", na=False).sum()) for table in tables)
            except Exception as exc:
                fail(instrument, None, "read_geocsv", exc)
                item["status"] = "failed"
                continue
            for start in range(0, len(selected), batch_size):
                batch = selected[start:start + batch_size]
                loaded = []
                for pair in batch:
                    if pair["mseed"] is None or pair["sac"] is None:
                        pair["status"] = "missing"
                        fail(instrument, pair, "missing_pair", "original MiniSEED and independently read paired SAC are both required")
                        continue
                    if not supported_product(pair):
                        pair["status"] = "unsupported"
                        fail(instrument, pair, "unsupported_product", "unsupported original waveform product")
                        continue
                    try:
                        stream = read_waveforms(str(source_root / pair["mseed"]), format="MSEED")
                        if len(stream) != 1:
                            pair["status"] = "unsupported"
                            fail(instrument, pair, "waveform_layout", f"expected one original contiguous Trace, got {len(stream)}")
                            continue
                        trace = stream[0]
                        if "sac" in trace.stats or "geocsv" in trace.stats:
                            raise ValueError("original MiniSEED must not supply inherited association or SAC headers")
                        if trace.stats.station != instrument:
                            raise ValueError(f"waveform Station {trace.stats.station} differs from inventory {instrument}")
                        loaded.append((pair, trace))
                    except Exception as exc:
                        pair["status"] = "failed"
                        fail(instrument, pair, "read_mseed", exc)
                if loaded:
                    try:
                        geocsv.associate(Stream([trace for _, trace in loaded]), tables,
                                         time_tolerance=LIMITS["association_time_seconds"], allow_first_segment=False)
                    except Exception as exc:
                        # The public API is transactional. A failed batch has no accepted associations.
                        for pair, _ in loaded:
                            pair["status"] = "failed"
                            pair["checks"]["strict_association"] = False
                            fail(instrument, pair, "associate_batch", exc)
                        loaded = []
                for index, (pair, trace) in enumerate(loaded):
                    output = scratch / f"{index}.sac"
                    try:
                        checks, measurements, association = compare_pair(trace, source_root / pair["sac"], output)
                        pair.update(checks=checks, measurements=measurements, association=association)
                        pair["status"] = "passed" if all(checks.values()) else "failed"
                        for name, passed in checks.items():
                            if not passed:
                                fail(instrument, pair, name, "documented scientific comparison failed")
                    except Exception as exc:
                        pair["status"] = "failed"
                        fail(instrument, pair, "export_or_compare", exc)
                    finally:
                        output.unlink(missing_ok=True)
                if progress and len(selected) > batch_size:
                    progress(f"{instrument}: examined {min(start + batch_size, len(selected))}/{len(selected)}")
            item["status"] = "complete" if all(pair["status"] == "passed" for pair in selected) and len(report["failures"]) == before_failures else "failed"

    # Bind the evidence to files stable throughout the complete run.
    try:
        verify_candidate(candidate)
        if fingerprint(candidate / "manifest.json")[1] != frozen_manifest:
            fail(None, None, "candidate_changed", "frozen manifest changed during validation")
        if inventory_sources(manifest, source_root) != source_files:
            fail(None, None, "sources_changed", "source inventory/fingerprints changed during validation")
        if software_versions() != software:
            fail(None, None, "code_changed", "validation code/dependencies changed during validation")
        if check_staging_inventory(candidate, manifest, source_root) != staging:
            fail(None, None, "staging_changed", "local staging exclusions changed during validation")
    except Exception as exc:
        fail(None, None, "final_recheck", exc)
    report["summary"] = summary(pairs, source_files)
    try:
        report["maxima"] = measured_maxima(pairs)
    except ValueError as exc:
        report["maxima"] = {}
        fail(None, None, "nonfinite_measurements", exc)
    report["status"] = "passed" if not report["failures"] and all(pair["status"] == "passed" for pair in pairs) else "failed"
    report["finished_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    # Exclusive creation preserves previous evidence; use a new output path for a rerun.
    with report_path.open("xb") as output:
        output.write((json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    try:
        report = validate_snapshot(args.candidate, args.source_root, args.report,
                                   batch_size=args.batch_size, progress=lambda message: print(message, flush=True))
        print(json.dumps({"status": report["status"], "summary": report["summary"],
                          "failures": len(report["failures"]), "report": str(args.report)}, indent=2))
        if report["status"] != "passed":
            raise SystemExit(1)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Validation not accepted: {exc}\n")


if __name__ == "__main__":
    main()
