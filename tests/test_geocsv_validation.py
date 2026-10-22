"""Full public-API round trips and candidate-bound acceptance, using synthetic originals."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/geocsv"))
from acceptance import AcceptanceError, LIMITS, require_acceptance
from create_snapshot import create_snapshot
from snapshot import json_bytes
from validate_snapshot import validate_snapshot
from publish_snapshot import require_scientific_acceptance

try:
    import numpy as np
    from obspy import Trace, UTCDateTime, read
    from obspy.io.sac import SACTrace
    from mermaid import geocsv
except ImportError:
    geocsv = None


@unittest.skipIf(geocsv is None, "requires mermaid-geocsv with the ObsPy extra")
class ArchiveValidation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "processed"
        self.serial = self.source / "serial"
        self.cycle = self.serial / "0001_cycle"
        self.cycle.mkdir(parents=True)
        self.mseed = self.cycle / "20200101T000000.serial.MER.DET.WLT5.mseed"
        self.sac = self.mseed.with_suffix(".sac")
        self.trace = Trace(np.array([1, -2, 3, 5], dtype=np.int32), header={
            "network": "MH", "station": "P0006", "location": "00", "channel": "BDH",
            "starttime": UTCDateTime("2020-01-01T00:00:00Z"), "sampling_rate": 20.0,
        })
        self.trace.write(str(self.mseed), format="MSEED")
        reference = SACTrace.from_obspy_trace(self.trace, keep_sac_header=False)
        reference.stla = 12.345678
        reference.stlo = -150.123456
        reference.stdp = 100
        reference.stel = 0
        reference.write(str(self.sac))
        self.geo = self.serial / "geo_DET_REQ.csv"
        self.geo.write_text(
            "#dataset: GeoCSV\n#created: 2026-10-21T22:48:33.277Z\n"
            "#field_type: string,datetime,string,string,string,string,string,float,float,float,float,string,float,integer,float,float\n"
            "#field_unit: unitless,iso8601,unitless,unitless,unitless,unitless,unitless,degrees_north,degrees_east,meters,mbar,unitless,hertz,unitless,seconds,seconds\n"
            "MethodIdentifier,StartTime,Network,Station,Location,Channel,DataQuality,Latitude,Longitude,Elevation,WaterPressure,InstrumentDescription,SampleRate,SampleCount,TimeDelay,TimeCorrection\n"
            "Algorithm(event):test,2020-01-01T00:00:00.000Z,MH,P0006,00,BDH,Q,12.345678,-150.123456,nan,10000,test,20,4,nan,nan\n")
        self.inventory = self.root / "instruments.csv"
        self.inventory.write_text("instrument_serial,instrument_id\nserial,P0006\n")
        self.work = self.root / "publication"
        self.candidate = create_snapshot(self.source, self.work, self.inventory)
        self.report_path = self.work / "validation/validation.json"

    def validate(self):
        return validate_snapshot(self.candidate, self.source, self.report_path, batch_size=2)

    def test_complete_public_api_validation_and_acceptance(self):
        before = {p: p.read_bytes() for p in (self.geo, self.mseed, self.sac)}
        report = self.validate()
        self.assertEqual(report["status"], "passed", report["failures"])
        self.assertEqual(report["summary"]["passed"], 1)
        accepted = require_scientific_acceptance(self.candidate, self.report_path, self.source)
        self.assertEqual(accepted, report)
        self.assertEqual(report["pairs"][0]["association"]["type"], "single_segment")
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse(list(self.report_path.parent.glob("sac-exports-*")))
        self.assertNotIn(str(self.root), self.report_path.read_text())

    def test_arbitrary_success_flag_and_unsupported_version_rejected(self):
        self.report_path.parent.mkdir(parents=True)
        for report in ({"passed": True}, {"schema": "bathymetrix-geocsv-archive-validation", "schema_version": 999}):
            self.report_path.write_bytes(json_bytes(report))
            with self.assertRaises(AcceptanceError):
                require_acceptance(self.candidate, self.report_path, self.source)

    def test_mutated_evidence_rejected_without_trusting_passed_flag(self):
        valid = self.validate()
        variants = []
        def change(path, value):
            variant = deepcopy(valid)
            target = variant
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            variants.append(variant)
        change(["candidate", "manifest_sha256"], "0" * 64)
        change(["release_id"], "different")
        change(["pairs"], [])
        change(["pairs", 0, "checks", "latitude"], False)
        change(["pairs", 0, "checks", "latitude"], 1)
        change(["pairs", 0, "measurements", "start_reference_ns"], 1001)
        change(["pairs", 0, "measurements", "interval_reference_ulps"], 2)
        change(["pairs", 0, "measurements"], {})
        change(["summary", "passed"], 100)
        change(["maxima"], {})
        change(["limits", "sac_start_comparison_ns"], 1000000)
        change(["software", "obspy"], "other")
        change(["source_files"], [])
        change(["instruments"], [])
        change(["failures"], [{"detail": "failed"}])
        for variant in variants:
            self.report_path.write_bytes(json_bytes(variant))
            with self.subTest(variant=len(variant)), self.assertRaises(AcceptanceError):
                require_acceptance(self.candidate, self.report_path, self.source)

    def test_changed_candidate_or_source_after_validation_blocks_publication(self):
        self.validate()
        content = self.mseed.read_bytes()
        self.mseed.write_bytes(content + b"changed")
        with self.assertRaisesRegex(AcceptanceError, "fingerprints"):
            require_acceptance(self.candidate, self.report_path, self.source)
        self.mseed.write_bytes(content)
        candidate_file = self.candidate / "P0006.geocsv"
        candidate_file.write_bytes(candidate_file.read_bytes() + b"#comment edit\n")
        with self.assertRaises(ValueError):
            require_acceptance(self.candidate, self.report_path, self.source)

    def test_missing_pair_reports_and_blocks(self):
        self.sac.unlink()
        report = self.validate()
        self.assertEqual(report["summary"]["missing"], 1)
        self.assertEqual(report["status"], "failed")
        with self.assertRaises(AcceptanceError):
            require_acceptance(self.candidate, self.report_path, self.source)

    def test_reference_interval_one_ulp_passes_two_ulps_fail(self):
        original = SACTrace.read(str(self.sac))
        for steps in (1, 2):
            reference = original.copy()
            value = np.float32(original.delta)
            for _ in range(steps):
                value = np.nextafter(value, np.float32(np.inf))
            reference.delta = value
            reference.write(str(self.sac))
            report = self.validate()
            self.assertEqual(report["pairs"][0]["measurements"]["interval_reference_ulps"], steps)
            self.assertEqual(report["pairs"][0]["measurements"]["interval_native_error_seconds"], 0)
            self.assertTrue(report["pairs"][0]["checks"]["samples_reference"])
            if steps == 1:
                self.assertEqual(report["status"], "passed", report["failures"])
                require_acceptance(self.candidate, self.report_path, self.source)
            else:
                self.assertEqual(report["status"], "failed")
                with self.assertRaises(AcceptanceError):
                    require_acceptance(self.candidate, self.report_path, self.source)
            self.report_path.unlink()

    def test_association_sample_and_coordinate_failures_are_not_widened(self):
        original = self.sac.read_bytes()
        for field in ("data", "stla"):
            reference = SACTrace.read(str(self.sac))
            if field == "data":
                reference.data = reference.data + 1
            else:
                reference.stla = reference.stla + 1
            reference.write(str(self.sac))
            report = self.validate()
            self.assertEqual(report["status"], "failed")
            expected = "samples_reference" if field == "data" else "latitude"
            self.assertFalse(report["pairs"][0]["checks"][expected])
            self.assertEqual(report["limits"], LIMITS)
            self.report_path.unlink()
            self.sac.write_bytes(original)
        trace = read(str(self.mseed))[0]
        trace.stats.starttime += 1
        trace.write(str(self.mseed), format="MSEED")
        report = self.validate()
        self.assertFalse(report["pairs"][0]["checks"]["strict_association"])
        self.assertEqual(report["status"], "failed")

    def test_unsupported_waveforms_are_reported_spectra_not_counted(self):
        (self.cycle / "outside_scope.mhpsd").write_bytes(b"not a waveform input")
        (self.cycle / "unknown.seed").write_bytes(b"unsupported waveform")
        report = self.validate()
        self.assertEqual(report["summary"]["unsupported_files"], 1)
        self.assertEqual(report["status"], "failed")
        self.assertFalse(any("mhpsd" in item["path"] for item in report["source_files"]))

    def test_recordless_instrument_is_accounted_locally_and_not_staged(self):
        empty = self.source / "empty"
        empty.mkdir()
        (empty / "geo_DET_REQ.csv").write_text(
            "#dataset: GeoCSV\n#created: 2026-10-21T22:48:33.277Z\nStation\n")
        self.inventory.write_text(self.inventory.read_text() + "empty,R0060\n")
        self.candidate = create_snapshot(self.source, self.root / "empty-work", self.inventory)
        self.assertFalse((self.candidate / "R0060.geocsv").exists())
        local = self.candidate.parent.parent / "staging" / self.candidate.name / "inventory.json"
        sidecar = json.loads(local.read_text())
        self.assertEqual(next(item for item in sidecar["instruments"] if item["instrument_id"] == "R0060")["reason"], "no data records")
        report = self.validate()
        self.assertEqual(report["staging"]["excluded_recordless"], 1)
        self.assertEqual(report["status"], "passed", report["failures"])
        require_acceptance(self.candidate, self.report_path, self.source)
        (empty / "hidden.mseed").write_bytes(self.mseed.read_bytes())
        with self.assertRaisesRegex(AcceptanceError, "unexamined waveforms"):
            require_acceptance(self.candidate, self.report_path, self.source)

    def test_geo_read_failure_keeps_waveforms_explicitly_unexamined(self):
        with patch.object(geocsv, "read", side_effect=ValueError("invalid GeoCSV")):
            report = self.validate()
        self.assertEqual(report["summary"]["unexamined"], 1)
        self.assertEqual(report["status"], "failed")
        with self.assertRaises(AcceptanceError):
            require_acceptance(self.candidate, self.report_path, self.source)

    def test_req_missing_pressure_remains_undefined(self):
        self.geo.write_text(self.geo.read_text().replace(",Q,12.345678,-150.123456,nan,10000,", ",D,12.345678,-150.123456,nan,nan,"))
        reference = SACTrace.read(str(self.sac))
        reference.stdp = None
        reference.write(str(self.sac))
        # Rebuild in a separate workspace because the timestamp identity is unchanged.
        self.candidate = create_snapshot(self.source, self.root / "req-work", self.inventory)
        report = self.validate()
        self.assertEqual(report["status"], "passed", report["failures"])
        self.assertIsNone(report["pairs"][0]["measurements"]["depth_error_m"])
        require_acceptance(self.candidate, self.report_path, self.source)


if __name__ == "__main__":
    unittest.main()
