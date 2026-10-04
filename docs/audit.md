# Independent audit: write the ruler before counting

A regex list cannot list unknown identifiers. A consistency gate cannot judge re-identification. The independent review asked an attacker-like question about a small sample, under a written acceptance rule whose scope must remain explicit.

## Inputs and projection

The historical reviewer read a 50-row JSONL file containing id, class, state, question, options and label. The public sampler selects usable rows only, stratifies ROUTE and ARCH separately, and divides REVIEW into APPLY and REJECT strata. It excludes extra and provenance. Sample identifiers are newly assigned so original row identifiers do not become an egress path.

Historical mixed-sample targets were 17 ROUTE, 8 APPLY, 8 REJECT and 17 ARCH. The synthetic fixture cannot satisfy that exact composition: it has fewer architecture records and rejected findings. The sampler fills missing quotas from remaining usable rows without replacement, reports actual class counts, and never invents records to reach the requested total. Insufficient total rows is an error.

## Acceptance rule

Hard leaks include real person/organization identity or evidence revealing the producer, private endpoints/credentials, internal system/project names and task slugs, dates finer than a month, malformed placeholders, a placeholder meaning different things within the same record, and a state exposing its label.

Allowed items include public products, libraries, models, datasets, benchmarks, third-party upstream accounts/repositories, generic public-repository relative paths, public domains, image tags and commit hashes. `project_0` is an explicit unknown bucket. Opaque `ref_N` codes distinguish things within a record without a cross-record consistency requirement.

The output is a hard-leak table with record id, quoted string, category and explanation. It answers whether the producer can be inferred, whether internal names can be recovered, and which rows expose their labels. Optional notes are separate and do not count. The last line must be exactly `AUDIT: CLEAN` or `AUDIT: LEAKS (n)`.

`configs/p-audit-scrub.txt` is the before example. It lacks the final written acceptance boundary and is not the runner default. `configs/p-audit-scrub-v2.txt` is the final-rule prompt. Neither file contains private rule lists.

## Chronology and two rulers

The rule was written after round 3 and before round 4. Round 4 still used the old prompt, so its findings were re-tallied manually. Round 5 finally inserted the rule into the prompt. Reviewer counts were 52, 28, 27, 28, 1, 0, 6. The retrospective final-rule counts were 34, 17, 7, 9, 1, 0, 6, with uncertainties reported separately in rounds 2 and 3.

Round 4's 9 comprise 4 hard findings plus 5 collisions introduced by collapsing codes. The older “24 of 28 allowed” note is inconsistent with the final tally: 19 allowed, 5 self-inflicted and 4 hard. The complete [round table](results.md#independent-audit-record) preserves findings, sample conditions and next changes.

Producer identity was not reliably inferred. Internal names were partly recoverable until round 5. Label leaks appeared in rounds 1 and 2 and only rarely afterwards. Those are descriptions of the recorded audits, not a guarantee against other reviewers or outside linkage data.

## What CLEAN means

For zero affected rows among 50 independent random rows, `1 - 0.05^(1/50)` gives an upper row-level rate of about 5.8 % at 95 % confidence. The actual mixed sample was stratified, so the simple calculation is illustrative and not a per-class certificate. Round 6 included 17 ROUTE rows; round 7 then found 6 hard findings in 3 of 50 ROUTE rows (6 % of rows).

Different samples and data versions were used each time. No sample was reviewed twice, so reviewer variance was not measured. One reviewer family was used. Allowed paths, exact benchmark figures and commit fingerprints can still form a source fingerprint; outside linkage attacks were not tested.

## Egress was real

The reviewer was a hosted model. It received 350 row-views across the 7 calls. Early samples contained private identifiers, so the claim that nothing left the machine was wrong for this stage. The old pre-check scanned the prompt file only, not the sample the reviewer read. Instructions forbidding network use inside the reviewer session did not eliminate the hosted model's own input egress.

The public review wrapper reads and scans both files before invoking a command. It stages exactly the scanned contents in a local temporary review directory, passes filenames as arguments without shell interpolation, and checks the final verdict. A successful no-op command is an invalid audit response. With no command it records `AUDIT: NOT RUN`.

The supplied reviewer command must provide read-only sandboxing. This portable wrapper is not an OS sandbox and does not turn arbitrary commands into read-only reviewers. No external review is performed by the tests.

**Rule:** scan the material that leaves, write the counting rule before the first round, and treat CLEAN as sample evidence with a stated threat model.
