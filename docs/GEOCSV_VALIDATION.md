# Full-archive GeoCSV validation and report version 2

`bathymetrix-site/scripts/geocsv/validate_snapshot.py` orchestrates the public
`mermaid-geocsv` read → associate → write_sac APIs. It requires Python 3.11+,
`mermaid-geocsv` with its ObsPy extra, and original local MiniSEED/SAC inputs.
The source tree is read-only. Temporary exports, frozen candidates and reports
are outside Git. The publisher consumes this repository's report protocol.

## Scope and complete accounting

Every included instrument is resolved from the frozen manifest's explicit
processed-root-relative `provenance.source_path`. Every original `.mseed` and
`.sac` underneath its serial directory is fingerprinted and paired by identical
relative stem. Pairing does not provide association hints: the package matches
native MiniSEED identity, start, count and rate to the frozen GeoCSV.

Original products follow `.MER[digits].DET|REQ.WLT1..5|RAW`. Other waveform
products, multitrace files, unsupported `.seed`, `.miniseed`, `.ms` and compressed
waveform formats are reported explicitly. Missing counterparts, unreadable inputs,
failed associations/exports/comparisons, and unexamined pairs block acceptance.
No missing waveform is silently replaced or reconstructed. Every available pair
must be examined; not every GeoCSV metadata row necessarily denotes a separate
available waveform file. Instruments with no original pairs remain explicit in
the instrument accounting.

`.mhpsd` spectra are outside scope and are neither opened nor counted. Other
non-waveform products and source-control metadata are not validation inputs.

Process one instrument at a time and bounded batches of original loaded traces.
Association is transactional: when a batch fails, all pairs in that batch are
reported failed with the public exception and unperformed comparisons left null.
No part of the failed batch is claimed to have passed. Read each paired SAC
independently after association/export. SAC headers never supply source defaults,
matching hints, missing positions or missing pressure.

Recordless GeoCSV sources are excluded before payload staging and documented
in the creator's local-only `staging/<encoded release>/inventory.json`. That
sidecar covers every source instrument, including explicit exclusion reasons.
The validator and publisher verify its exact hash, recordless status, and complete
source accounting; any original waveforms in an excluded directory block the
run rather than being silently omitted. Empty GeoCSV files and the staging
sidecar are never uploaded. The public report records only the sidecar hash and
recordless-exclusion count, not the excluded payloads.

## Scientific checks and limits

The fixed limits reproduce the package's documented original-segment contract
and `docs/tutorials/WRITE_SAC.md` comparisons. Limits are recorded in every report
and are not configurable from the CLI. Failures do not trigger wider tolerances.
The one-ULP representation-check pattern is established in the package's
`tests/test_earthscope_response.py` and its association fixture documentation.
Version 2 applies that pattern to the independent SAC interval comparison;
it does not change the package's strict association time/rate thresholds.
Version 1's exact independent-reference interval criterion is not reused.

| Check | Rule |
| --- | --- |
| Strict association | `associate(..., time_tolerance=0.001, allow_first_segment=False)`; require `single_segment` |
| Rate association | Package's documented floating endpoint test within 0.00001 Hz; measured absolute difference retained diagnostically |
| Identity | Exported, native MiniSEED and independently read reference SNCL agree |
| Count | Exported/reference `npts` equal native loaded count exactly |
| Samples | Exported data exactly equals native data cast to float32 and independently read reference data; no scaling |
| Interval | Exported `delta` exactly equals float32(native delta); independent reference differs by at most one float32 ULP |
| First sample time | Exported absolute UTC first-sample time is within 1,000 ns of native and independently read reference |
| Latitude/longitude | Error at most `0.5e-6 + abs(spacing(float32(reference_coordinate)))` degrees |
| Depth | Exact SAC float32 equality, or both SAC undefined (`None` through SACTrace) |
| Elevation | Exported and reference STEL equal zero metres exactly |

The 1 microsecond timing criterion is a conservative fixture comparison limit,
not a general claim about SAC accuracy or MERMAID physical clock resolution.
GeoCSV coordinate precision is six decimal places for the current producer.
Sample intervals/rates remain scientifically meaningful independently of coarser
absolute clock accuracy. Absolute start times are compared, not a particular
split between SAC reference time and `b`.

The package owns the geographic projection: latitude in degrees_north, longitude
in degrees_east, sea-level STEL=0 metres, and approximate depth from WaterPressure
in mbar divided by 100. This reproduces the producer's convention, not a physical
pressure-to-depth model. REQ source quality D may omit pressure; depth remains
undefined, without borrowing another record's value. Missing DET pressure fails
through the public exporter. All coordinate/unit validation stays in the package.

No whole-SAC-header or byte equivalence is asserted. Calibration, instrument,
orientation and producer-specific trigger headers are outside comparison scope.
SAC raw waveform values are subject to float32 storage, without response removal
or counts-to-pressure conversion.

## Report schema

A UTF-8 JSON object has `schema: "bathymetrix-geocsv-archive-validation"` and integer
`schema_version: 2`. Unknown versions are rejected. JSON creation rejects NaN and
infinity. Reports are created exclusively, retained separately from the frozen
manifest, and use source-relative identifiers without machine-specific roots.

| Field | Meaning |
| --- | --- |
| `release_id` | Literal upstream timestamp, exactly matching the frozen manifest |
| `candidate.manifest_sha256` | SHA-256 of exact manifest bytes, not normalized JSON |
| `candidate.files` | Complete frozen manifest file entries, including sizes, hashes and provenance |
| `staging` | SHA-256 of the local complete staging inventory and recordless-exclusion count |
| `scope` | Fixed original-waveform scope, excluding spectra without counting |
| `limits` | Exact versioned scientific rule values and comparison descriptions |
| `software` | Python, mermaid-geocsv, NumPy, pandas and ObsPy versions; website workflow code and package Python source hashes |
| `source_files` | Complete sorted included-input inventory: instrument ID, source-relative path, kind, byte count and SHA-256 |
| `instruments` | Every included instrument, pair count, parsed event-row count when available, and completion status |
| `pairs` | Every expected pair, paths, outcome, per-check results, measurements and strict association source-row evidence |
| `failures` | Instrument, pair ID, stage and diagnostic for every reported failure |
| `summary` | Recomputable input/pair counts and passed/failed/missing/unsupported/unexamined counts |
| `maxima` | Recomputable maxima of nonnegative finite per-pair measurements |
| `started_utc`, `finished_utc` | Run times, distinct from upstream release identity |
| `status` | Derived `passed` or `failed`; never sufficient by itself for acceptance |

Source kinds are `geocsv`, `mseed`, `sac` and `unsupported`. Source GeoCSV
fingerprints must equal their frozen staged files. The source inventory is
recreated and fingerprinted again at run completion to detect changes during
validation; the publisher recreates it again before publication.

Pair statuses are `passed`, `failed`, `missing`, `unsupported`, and `unexamined`.
The exact per-pair check names are `strict_association`, `identity`, `sample_count`,
`samples_native`, `samples_reference`, `sample_interval`, `start_native`,
`start_reference`, `latitude`, `longitude`, `depth`, `elevation`. Every value must
be the boolean `true` for acceptance; null explicitly means unperformed.

Measurements retain absolute association time/rate differences, native/reference
sample errors, count/interval errors, exact native-interval error, independent-reference
float32 ULP distance, first-sample time differences in ns,
coordinate errors and their limits in degrees, and depth/elevation errors in
metres. Undefined depth has a null depth error after a successful both-undefined
comparison. Association evidence records `single_segment`, dataset index and
source record index, as supplied by the public package.

## Acceptance

`publish_snapshot.py` requires `--report` and explicit `--source-root` for
publication. `require_scientific_acceptance` calls this repository's versioned
acceptance rules, which:

1. Recheck the complete candidate inventory, exact bytes and literal timestamp.
2. Require matching report identity, exact manifest hash/file list, scope, limits,
   current workflow/package code hashes and dependency versions.
3. Reinventory/fingerprint all source inputs and reconstruct pair coverage.
4. Require every expected original pair exactly once, both formats, supported
   product, strict association evidence, all checks passed, and measurements
   consistent with the versioned limits.
5. Recompute counts/maxima, require every instrument complete, and reject any
   failures, unsupported/unexamined inputs or incomplete evidence.
6. Bind acceptance to the report bytes and candidate manifest passed to transfer;
   recheck them before activation. Uploads and public checks precede latest.

These are evidence/consistency checks for a locally produced report, not a digital
signature or independent re-execution of all scientific comparisons by the
publisher. Treat local reports as controlled publication artifacts. A bare
success flag cannot satisfy the protocol. Code/dependency changes require rerun.
The report binds the manifest; the manifest contains no report hash.

## Verification

Focused tests build synthetic original MiniSEED with independent SAC references,
exercise the real public APIs, and check success plus missing pairs, association,
sample/coordinate mismatches, one-ULP interval acceptance and two-ULP rejection,
unexamined inputs, unsupported products, missing REQ
pressure and post-validation candidate/source tampering. Publisher transfer tests
continue to exercise immutable retries/conflicts, interrupted uploads, verification
failure and concurrent latest changes with transport-only synthetic evidence.

Full archive results are recorded separately, with the frozen candidate and
report retained outside Git. Failures must be resolved or explicitly reported;
a failed full run does not authorize a production candidate. Package defects
need source-relative reproductions using public APIs and the exact candidate,
file fingerprints, versions, affected pair and comparison measurements.
