# The mechanical gate

A known credential format or private name should not survive because a model had an unhelpful response. The gate is a deterministic backstop, with a list whose incompleteness remains explicit.

## What to scan

The original state-only, case-sensitive check missed capitalized names and private free-text options. The later gate scanned state, all options and label case-insensitively. The adapter begins with that broader check. `scrub_failed` rows remain available for local diagnosis but cannot enter the usable file or audit sample.

The outbound sample includes question and sample identifier as well. The review wrapper scans the entire serialized sample, not merely the decision fields. Neither `extra` nor `provenance` nor the entity map belongs in that sample. The map and private configuration must stay local.

## Patterns and tokens

`configs/patterns.example.txt` is a synthetic starting point, not the private rule list. Its identifier alternatives cover the fixture entities; other lines cover private-range address shapes, home-directory shapes and common credential formats. Literal non-loopback addresses are not needed in a public example. Credential prefixes use a character class for their first character so source scanners do not mistake a regex for an actual key.

`common.load_patterns` ignores blank lines and comments, compiles case-insensitively, and rejects missing, malformed or empty rule files. This strict loading is an adapter hardening change. The original scrubber could skip malformed patterns with a warning; that behavior was incompatible with a fail-closed public runner.

A token table is `token<TAB>class`. `postscrub.py` looks up or allocates a class placeholder in the shared map. It then strips day residue using the recorded month/day pattern, replaces the complete ROUTE Goal value, and rescans. The Goal regex is configurable and captures a prefix and the entire value, including spaces. A public keep-list belongs to map validation, not to an exemption from all downstream scanning.

The original regex file stayed at 4 lines while token entries grew from 9 to 29; the private keep-list had 28 entries. The public lists contain synthetic examples only and do not claim those historical sizes.

## Failures are local artifacts

A matching row carries `scrub_failed` and a pattern index or failure reason. Logs report counts and indices, not matching private text. A row failing before later repairs remains failed; a repair pass does not silently resurrect it. Model/parse failures, including failed option rewrites, also fail closed in the adapter.

Mechanical failures at different stages are not additive. The original first ARCH scrub had 5 failures out of 157; the guarded extraction then supplied a different 131-row set. A case-insensitive pass subsequently found 4 more in the 128 surviving rows. [The results table](results.md#mechanical-gate) preserves those populations separately.

## Enumeration has a ceiling

The final v7 rescan found no hits in the 679 REVIEW and 32 ARCH rows, but hit 4 ROUTE rows. The final hosted ROUTE audit found more shorthand too. Passing a growing list only shows absence of listed strings, not anonymity or immunity to outside linkage.

Mixed-language records require language-aware private lists. The source record says some routing fragments in another language survived. The public repository itself contains only English text; it does not ship those fragments or a private language-specific name list.

**Rule:** fail closed, scan the actual outbound artifact, and keep extending known patterns without treating enumeration as complete.
