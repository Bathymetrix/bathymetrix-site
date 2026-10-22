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

## Scientific validation authority

For GeoCSV validation and scientific comparison decisions, consult the current
`~/programs/mermaid-geocsv/AGENTS.md`, `docs/HOSTING.md`, the relevant scientific
documentation/tutorials, and their verification tests before choosing a rule.
Use that package's public APIs for parsing, association and SAC projection.

When a discrepancy arises, first apply the relevant established package rule
for that field and context. Do not invent stricter equality requirements or
wider tolerances, or generalize one field's precision allowance to all fields.
Distinguish matching thresholds from independent representation comparisons.
If the package has no applicable rule, report the ambiguity and coordinate an
explicit decision before accepting production data. Record agreed comparison
changes in the versioned report contract and keep both hosting plans synchronized.

