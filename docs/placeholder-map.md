# Shared placeholders and deterministic repair

The intended contract was useful: the same private entity should get the same neutral placeholder across rows, preserving relationships without preserving identity. The model and the shared map violated that contract in several ways.

## Historical rewrite algorithm

Before a call, apply map entries longest-original-first with plain `str.replace`. Ask the local model for `{"text": ..., "entities": [{"original": ..., "placeholder": ...}]}`. Class placeholders cover project, bot, persona, node, person, vendor and opaque identifiers; dates become month placeholders. Merge new originals with first-come numbering and rewrite the model's placeholder numbers to match the shared map.

When options are free text, rewrite each option separately. The label is the rewritten text at the original chosen option's index. Fixed lane and APPLY/REJECT vocabularies do not need semantic rewriting. Parse/model failure is a row failure. Dry-run mode processes the first 5 rows against copied maps and writes nothing; the public adapter suppresses before/after text in that log.

The model sees already-replaced placeholders. Of 523 map entries at repair time, 116 originals were numbered placeholders, all renumbered to different placeholders. The merge did not reject them. This explains a plausible poisoning mechanism, inferred from code and counts rather than isolated in an experiment.

## Repair policy

`mapclean.py` retains only numbered class placeholders or valid month forms, with original length at least 4, excluding the public keep-list and class/placeholder-shaped originals. A dropped mapping can be reversed only if its target placeholder is not retained for another entity. Literal unnumbered placeholders become the explicit unknown bucket `class_0`. Labels must remain in options.

The historical repair kept 243 and dropped 280 entries: 88 malformed, 40 short originals, 10 public names, 142 class/placeholder originals. It reversed 192 replacements and changed 611 of 1,014 rows. The recorded class breakdown is reproduced in [results](results.md#shared-map-repair), with its unresolved mismatch to the retained total.

This repair is not a complete prevention mechanism. The scrub adapter still retains the original substring replacement and permissive entity merge so the failure mechanism is inspectable. It must be followed by validation, repair and gates. Longer originals inside other words remain a risk. A synthetic illustration is replacing `cat` inside `category`; neither string comes from a private record.

## Distinct codes and neutral names

The first deterministic code pass replaced every work-item-shaped string with one literal. That made distinct targets identical. The next version kept distinct values but used `code_N`; a later reader drifted toward a lane associated with that word. Neutral `ref_N` preserves distinctions without that particular cue. The original runs mapped 91 codes at v5 and 93 at v6/v7.

`postscrub2.py` recognizes configured code patterns and assigns distinct references, normalizes nested/doubled/plural/trailing-letter placeholders, replaces a configured alias with “the local model”, removes line references and rejects duplicate options. The published config uses only synthetic identifiers and public severity forms.

## Recovering erased decision signals

The scrubber replaced a review severity tag with an unknown project. Align raw and scrubbed token streams using `difflib.SequenceMatcher(autojunk=False)`. For a replacement span containing `project_0`, restore a configured severity token, restore the exact generic word `project`, or map a raw slug to a proper placeholder. Unresolved cases remain unknown rather than guessed.

The final recorded alignment restored 126 severity tags, 4 generic words and 17 slugs; 12 rows remained in the unknown bucket. The source comment said 127 restored tags, but the recorded output said 126. The public adapter tokenizes trailing punctuation separately so a synthetic severity tag followed by a colon can be restored; its regression test covers that case.

## Rerun discipline

Restart repairs from the last model-scrubbed file, not the previous repaired version. Inspect many-to-one mappings, option uniqueness and label membership; then repeat the mechanical, label-leak, decidability and audit checks. Model-free repairs can still destroy meaning.

**Rule:** map validation and collision checks are part of the data transformation, and a map is never a publishable artifact.
