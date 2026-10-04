# Tag Vocabulary

The `applies_to` array on every legal chunk drives filter-then-search retrieval. This document defines the two vocabularies chunks can draw from, and the rules for choosing tags.

## Two vocabularies, two questions

**Classification tags** answer *"what kind of problem does the consumer have?"* — the Classifier Agent emits one of these per credit item. They describe the *item*.

**Statute tags** answer *"what legal concept does this chunk cover?"* — they describe the *law*. Reserved primarily for statute, case law, and guidance sources.

Every chunk should draw from BOTH vocabularies where both apply. That way a Strategy Agent query like `applies_to=["obsolete", "reinvestigation"]` returns both the obsolescence rule (§605) AND the procedural remedy (§611) in a single call.

## Rules

**Rule 1** — Statute chunks primarily use statute tags. That's their "what am I about" tag.

**Rule 2** — Classification tags are added ONLY when the chunk directly speaks to that condition. §605's 7-year rule gets `obsolete` because it directly addresses obsolete items. §611(a)(1)(A) (the reinvestigation procedure) does NOT get `obsolete` even though obsolete items go through reinvestigation — the chunk isn't ABOUT obsolescence.

**Rule 3** — Never invent a new tag without adding it to this document first. Tag sprawl defeats filter-then-search.

**Rule 4** — Multiple tags per chunk are encouraged when both vocabularies genuinely apply. Aim for 1-3 tags per chunk; four or more is a smell that the chunk is too broad and should be split.

## Classification tags (from `ClassificationTag` enum)

Reserved for chunks about a specific credit-item condition.

- `obsolete` — item past its 7-year reporting window (or 10 years for bankruptcy)
- `collection` — collection account
- `charge_off` — charged-off tradeline
- `mixed_file` — someone else's data on the consumer's report
- `identity_theft` — item resulting from identity theft
- `duplicate` — same item reported multiple times
- `paid_reporting_open` — paid account still showing as open with a balance
- `authorized_user` — authorized-user tradeline dispute
- `zombie_debt` — resurrected time-barred debt
- `medical` — medical debt (subject to special rules under §1681c and CARES Act updates)
- `hard_inquiry_unauthorized` — inquiry without permissible purpose

## Statute tags

Reserved for legal-concept chunks (mainly statute, case law, guidance sources).

- `reinvestigation` — §611 procedure (30-day reinvestigation, notification to furnisher)
- `permissible_purpose` — §604 (who can pull a report and why)
- `furnisher_duty` — §623 duties on data furnishers
- `accuracy_procedures` — §607(b) reasonable procedures to assure maximum possible accuracy
- `willful_noncompliance` — §1681n statutory + punitive damages
- `negligent_noncompliance` — §1681o actual damages
- `disclosure_to_consumer` — §609 consumer's right to see the file
- `debt_validation` — FDCPA §809 debt validation procedure
- `false_representation` — FDCPA §807 prohibitions on false/misleading collection tactics
- `verification_failure` — chunk specifically addresses what happens when a furnisher cannot verify
- `definitions` — foundational definitional chunks (§603)

## Query patterns

The Strategy Agent will typically retrieve with a mixed-vocabulary query:

```python
# Obsolete collection item, round 1
retrieve_legal_context(
    query="Collection reporting past the 7-year window",
    applies_to=["obsolete", "collection", "reinvestigation"],
)

# Unauthorized hard inquiry
retrieve_legal_context(
    query="Hard inquiry made without permissible purpose",
    applies_to=["hard_inquiry_unauthorized", "permissible_purpose"],
)

# Furnisher refuses to correct after third round
retrieve_legal_context(
    query="Furnisher continues verifying incorrect balance after multiple disputes",
    applies_to=["furnisher_duty", "willful_noncompliance"],
)
```

## When to add a tag

Before adding a new tag to this vocabulary, check:

1. Would the tag be used by more than one chunk? (Single-use tags don't help retrieval.)
2. Does an existing tag cover 80%+ of what you'd use this for? (If yes, use the existing tag.)
3. Does the new tag come from one of the two vocabularies? (Classification tag → add to ClassificationTag enum first. Statute tag → add here.)

If all three checks pass, add it to this doc AND, for classification tags, to the `ClassificationTag` enum in `web/src/schemas/enums.ts` and `agents/src/schemas/enums.py`, then regenerate schemas.

## Vocabulary version

**v1.0.0** — initial vocabulary, established Session 4C.
