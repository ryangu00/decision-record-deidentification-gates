# Label leaks are a separate gate

A row can contain no recognized private identifiers and still give away its answer. Name removal and answer removal are different transformations with different failure modes.

## The five observed routes

ARCH contexts directly restated chosen decisions. Other ARCH contexts eliminated the rejected option, which reveals the answer in a 2-option record. ROUTE task text sometimes named the chosen execution lane. REVIEW extraction sometimes read a current file that had already incorporated the verdict's repair. The REVIEW change column directly described that repair and was excluded from the start.

The final controls were a guarded ARCH prompt and overlap filter, a semantic ARCH leak checker, a ROUTE label-in-state rejection, and removal of all REVIEW file context. The raw side of the decidability comparison needs the same deliberate context removal; otherwise the comparison measures that policy change alongside scrubbing.

## Semantic request and score

`leakcheck.py` asks: “Does the CONTEXT reveal, state, or strongly imply which option was chosen, adopted, approved, or which options were rejected?” The system asks for exactly Yes or No. Options are included because elimination can be a leak even without repeating the chosen text.

Read the first-token logprobs of Yes and No, retaining the best observed score for each token spelling. A missing side gets minimum observed logprob minus 3. Convert to p(yes) with a softmax, repeat 3 times, and use the median. Drop rows at median p(yes) >= 0.5. Fixed-vocabulary rows pass through without this model check.

The public adapter uses numerically stable softmax arithmetic and fails closed when the read is missing or incomplete. Already failed scrub rows go to the dropped output. These are implementation hardening changes; no new real-data recall measurement is claimed.

## What the original filter did

The guarded extractor supplied 131 ARCH rows. Mechanical stages removed 3 plus 4, leaving 124. The semantic gate dropped 92 (74 %) and kept 32, for a final 32 of 157 source records (20 %). The dropped-row score bands were 11 at 0.5 to 0.6, 38 at 0.6 to 0.8, and 43 at 0.8 to 1.0. Nine dropped rows straddled 0.5 across their reads.

Kept rows had maximum score 0.469. This separation says only that a handful lie close to the policy threshold; it says nothing about rows misjudged by the model. No labelled leak set existed and no calibration was performed, so recall is unknown. The complete distributions are in [results](results.md#semantic-leak-filter).

All 499 resolved REVIEW contexts were dropped. All 679 extracted REVIEW rows survived as rows, with 622 APPLY and 57 REJECT labels. Some finding text still contained verdict-like words; the reviewers did not count those as leaks and they were not removed. A constant “Reviewer finding” prefix is not itself evidence of label leakage.

## Sampling consequences

An early audit's REVIEW sample had 16 of 16 APPLY labels against a corpus with 91.6 % APPLY. Later samples deliberately included 8 APPLY and 8 REJECT. Balancing audit coverage is separate from rebalancing data for training, which was not performed here.

The synthetic mock only recognizes a planted word indicating a decision. That is enough to exercise the threshold/drop path, but cannot reproduce a real semantic auditor or estimate its recall. Tests label that distinction explicitly.

**Rule:** construct state blind to outcomes where possible, then independently test answer exposure. Record the loss at every stage.
