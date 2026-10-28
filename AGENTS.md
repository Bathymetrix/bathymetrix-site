# Repository instructions

## Shared coding instructions

For coding and engineering workflow only, read and follow these files in order:

1. `~/.codex/AGENTS.md`
2. `~/programs/AGENTS.md`

Repository-specific instructions supplement or override those references.

Non-coding decisions, including website visual design, presentation style,
branding, and editorial choices, are defined manually for this project. Do not
infer those choices from the referenced files.

## Public repository and private information

This repository is published publicly on GitHub. Treat committed files, history,
issues, pull requests and generated public artifacts as public disclosures.

Never place private personal information, passwords, API tokens, access keys,
private keys, authentication cookies or private account details in repository
content. This includes code, documentation, examples, fixtures, logs, generated
artifacts, screenshots, and untracked or Git-ignored files in the checkout.
Git-ignored status is not a privacy or credential-storage boundary.

Use credentials only for an authorized operation. Resolve them at runtime through
the existing SDK credential provider, externally supplied environment variables,
or an approved secret store configured outside this checkout. Never hard-code,
copy, print or commit credential values, including in errors, debug output,
command arguments, reports or conversation summaries. Routine inspections must
not read external credential files or dump the environment.

Use placeholders for private configuration and portable environment-based or
repository-relative paths instead of personal account names and home-directory
paths. Check embedded document/media metadata and archives as well as visible
text before publication. Deliberately published professional biography, approved
business contact details and scholarly attribution may remain; do not infer
permission to publish other personal information.

Review pending changes for these exposures before handoff. Report suspected
secrets by file and location without reproducing values. Cleanup of current files
does not remove historical copies; history rewrites and publication still require
explicit authorization under the inherited Git rules.

## Private website records

Never expose private website records in this repository. This includes DNS zone
exports, record inventories, DNS or account screenshots, private infrastructure
and deployment configuration, and other nonpublic website or service records.
Do not place them in repository files, documentation, examples, fixtures, logs,
issues, or pull requests, including untracked or Git-ignored files in the checkout.

Keep operational inventories and backups in an owner-approved private location
outside the repository. Use placeholders or redacted examples when documenting
procedures. Public DNS visibility does not authorize copying an operational
inventory or private account context into this repository.

## Documentation Voice

Write documentation in a direct, factual, statement-based voice. State the
configuration, decisions and requirements without conversational attribution
such as "the user reports", "you said" or "we agreed". Mark planned behavior,
unverified information and uncertainty explicitly rather than presenting them
as established facts. Omit personal account and billing details unless
explicitly requested for the document.

## GeoCSV testing-only publication phase

All hosted GeoCSV data remain explicitly testing only until production publication
is separately authorized. This includes synthetic fixtures and full-corpus upload,
download and scientific-validation tests. Public access, a complete corpus, a
passing acceptance report or a successful deployment does not establish a first
scientific release.

Label hosted data and public descriptions as testing only. Manifests and their
latest pointers must agree on `testing_only: true`. Keep testing objects and
pointers isolated from future production activation. Implement and verify these
safeguards before uploads if the current tools do not support them. Do not mutate
a frozen manifest or reuse its acceptance report merely to change the test flag.

Immutable timestamped snapshots and pinned downloads remain valid for test
reproducibility; `release_id` is a snapshot identifier, not authorization for a
formal release. Scientific checks, licensing/citation requirements and explicit
upload authorization still apply. Do not promote data to production, tag a first
data or software release, or claim production availability without explicit
authorization. Testing and infrastructure preparation do not grant it.

Initial workflow-testing snapshots may be retired through separately authorized
cleanup after verification. They are not permanent scientific releases and their
testing URLs do not promise indefinite availability. Preserve immutable bytes
until retirement; never reuse retired testing identities for different bytes.
Cleanup of hosted objects, caches, local artifacts or history still requires
explicit authorization. Production retention remains indefinite.

## Publication ownership

`mermaid-publisher` owns create, validate, gate, upload, latest activation and
local archive recording under `scripts/geocsv/`. Its `docs/geocsv/CONTRACT.md`
is the canonical download agreement. This website owns only its read-only
Worker, landing page and hosting infrastructure. Do not add publishing scripts,
scientific comparison code or report schemas here. Hosting must honor the
canonical contract; service changes do not redefine consumer behavior. The
2026-10-28 coordinated path review uses hyphenated creation-timestamp components
with consumer >= 0.26.0 and authorizes replacement of the initial testing set.
Its old encoded URLs may be retired; scientific release IDs remain unchanged.

Keep testing URLs/keys/pointers isolated from production and require matching
flags. Retain the Worker serving tests here; run publication/scientific tests in
the publisher. Private configuration and credentials remain outside checkouts.
