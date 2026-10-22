# Repository instructions

## Shared coding instructions

For coding and engineering workflow only, read and follow these files in order:

1. `~/.codex/AGENTS.md`
2. `~/programs/AGENTS.md`

Repository-specific instructions supplement or override those references.

Non-coding decisions, including website visual design, presentation style,
branding, and editorial choices, are defined manually for this project. Do not
infer those choices from the referenced files.

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

