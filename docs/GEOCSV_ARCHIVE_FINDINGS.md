# Full archive validation findings — 2026-10-22

Release ID: `2026-10-21T22:48:33.277Z`.

The complete available original MiniSEED/SAC archive was tested with strict
public `geocsv.read → associate → write_sac` calls. Report version 2 passed
all 43,365 pairs and the publisher's acceptance gate rechecked and accepted its
complete evidence. The independent-reference interval comparison permits one
float32 ULP; native interval preservation remains exact. No production release
or latest pointer has been published.

| Accounting | Result |
| --- | ---: |
| Source GeoCSV instruments accounted for | 112 |
| Nonempty GeoCSV files in the frozen candidate | 103 |
| Recordless GeoCSV files excluded locally | 9 |
| Original MiniSEED files | 43,365 |
| Independent SAC references | 43,365 |
| Pairs passing every scientific check | 43,365 |
| Failed pairs | 0 |
| Pairs with exactly equal independent-reference intervals | 32,400 |
| Pairs with a one-float32-ULP independent-reference interval difference | 10,965 |
| Missing / unsupported / wholly unexamined pairs | 0 / 0 / 0 |

The nine recordless IDs are R0060, S0081, S0082, S0085, S0086, S0087, S0090,
S0092, S0094. Their unchanged source files were not staged or published. A
complete deterministic local staging sidecar records the exclusions and reasons;
its hash is bound by the validation report. No original waveforms were hidden in
those excluded directories. `.mhpsd` spectra are outside scope and were not counted.

## Observations

The strict-equality diagnostic identified differences between exported and
independently read reference SAC `delta`. The version-2 rerun measured a
maximum distance of one float32 ULP and passed every interval comparison. Other
checks passed for every pair: strict original association, SNCL identity, sample counts, raw float32 samples, absolute first
sample times, geographic coordinates, depth/missingness and sea-level elevation.

Representative reproductions:

| Instrument / source row | Exported/native float32 delta (s) | Reference delta (s) | Difference (s) |
| --- | ---: | ---: | ---: |
| N0001 / 547 | 0.04998239502310753 | 0.04998239874839783 | 3.725290298461914e-9 |
| P0006 / 15825 | 0.09996487200260162 | 0.09996486455202103 | 7.450580596923828e-9 |

In both reproductions, export delta equals `float32(native MiniSEED delta)`
exactly, native/reference samples match, and the reference delta differs by one
float32 spacing. The maximum interval difference over the entire run was
7.450580596923828e-9 seconds. The maximum source/waveform rate difference was
3.4332129956737845e-6 Hz, within the package's documented rate agreement criterion.
The maximum exported/native start difference was zero; exported/reference start
difference was at most 1,000 ns.

The exporter preserves the documented native waveform interval at SAC float32
precision. The independent-reference verification permits one float32
representable step, following the package's established representation-check
pattern in `tests/test_earthscope_response.py`. Report version 2 records the
ULP distance and applies a fixed maximum of one; two-step differences fail.
This is a representation comparison, not a package defect or a relaxation of
association's time/rate matching thresholds. Separate format quantization is a
plausible cause of the numerical differences, not an established archive-wide
causal explanation.

Active imported code was `mermaid-geocsv` 0.24.0, ObsPy 1.5.1, NumPy 2.5.3,
pandas 3.0.6, Python 3.12.4. Installed distribution metadata for mermaid-geocsv
still reports 0.11.0 in this environment. Reports retain both the active module
version and distribution metadata, plus Python-source fingerprints. No environment
was modified to reconcile the metadata.

## Reproduce the examples

Source-relative pairs, both under the processed root:

- `452.112-N-01/0008_20190212-07h20m31s/20190214T200939.01_5C794146.MER.REQ.WLT5`
- `452.020-P-06/0290_20221112-10h19m09s/20221118T134758.06_64395124.MER.REQ.WLT4`

Use the `.mseed` and `.sac` suffixes for each pair and the frozen candidate's
`N0001.geocsv` or `P0006.geocsv`, respectively. A standalone public-API check:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import numpy as np
from obspy import read
from obspy.io.sac import SACTrace
from mermaid import geocsv

root = Path(os.environ["MERMAID"]) / "processed"
candidate = Path(os.environ["GEOCSV_CANDIDATE"])
stem = root / "452.112-N-01/0008_20190212-07h20m31s/20190214T200939.01_5C794146.MER.REQ.WLT5"
trace, = read(str(stem) + ".mseed", format="MSEED")
records = geocsv.read(candidate / "N0001.geocsv")
geocsv.associate(trace, records, allow_first_segment=False)
with TemporaryDirectory() as temporary:
    output = Path(temporary) / "associated.sac"
    geocsv.write_sac(trace, output)
    actual = SACTrace.read(str(output))
    reference = SACTrace.read(str(stem) + ".sac")
    print(trace.stats.sampling_rate, trace.stats.geocsv.SampleRate)
    print(actual.delta, float(np.float32(trace.stats.delta)), reference.delta)
    print(abs(actual.delta - reference.delta))
    assert actual.delta == np.float32(trace.stats.delta)
    assert actual.delta != reference.delta
    np.testing.assert_array_max_ulp(
        np.float32(actual.delta), np.float32(reference.delta), maxulp=1)
    np.testing.assert_array_equal(actual.data, reference.data)
```

Set temporary exports to an external workspace when running from a checkout.
Frozen candidate, full per-pair report, input fingerprints, exclusion sidecar and
run logs remain in the external publication workspace. The exploratory
exact-reference reports are retained separately as historical diagnostics.
The passing report is `validation-v2.json`, completed at
`2026-10-22T21:34:45.455696Z`. Publication acceptance rechecked the complete
candidate, source inventory, local exclusion sidecar and current code/dependencies
against that report. All scientific checks and coverage requirements passed.

Verification also passed 32 Python tests, including actual-client localhost
integration, and nine Worker tests. Focused interval tests accept one float32
ULP and reject two. Data licensing/citation, actual DNS/DNSSEC preparation,
deployment and live HTTPS verification remain pending. Follow the acceptance
protocol for any rerun; never edit a report's success fields or substitute
another candidate's evidence.
