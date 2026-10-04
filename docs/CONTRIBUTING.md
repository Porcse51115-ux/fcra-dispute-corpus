# Contributing

Pull requests and issues welcome. The guidance below keeps the corpus's quality bar consistent across contributors.

## Before opening a PR

Run both scripts locally and confirm they pass:

```bash
python scripts/validate.py corpus/
python scripts/stats.py
```

`validate.py` must exit 0. `stats.py` can't fail, but review its output to confirm the new document(s) show up in the counts and tag frequencies you expect.

## Adding a document

Every added document must meet the sourcing criteria in [`METHODOLOGY.md`](METHODOLOGY.md):

1. **Primary source.** No commercial databases, no secondary summaries.
2. **Stable archive URL.** Cornell LII for statutes. CourtListener or official court sites for cases. consumerfinance.gov for CFPB material.
3. **Dispute-relevance.** The document should bear on a decision a strategist actually has to make.
4. **Verifiable claims only.** Summaries assert what primary sources say — no inferences without substantiation.

Place the document in the file matching its `source_type`:

| `source_type` | File |
|---|---|
| `statute` | `corpus/statutes.json` |
| `case_law` | `corpus/case_law.json` |
| `cfpb_enforcement` | `corpus/cfpb_enforcement.json` |
| `cfpb_guidance` | `corpus/guidance.json` |
| `bureau_pattern` | `corpus/bureau_patterns.json` |
| `playbook` | `corpus/playbooks.json` |

Follow the citation format conventions in [`SCHEMA.md`](SCHEMA.md).

## Chunking a document

Read [`METHODOLOGY.md`](METHODOLOGY.md) first — the chunking approach differs by source type, and it's deliberate. Short version:

- **Statutes**: one subsection per chunk (merge tightly cross-referenced subsections).
- **Cases**: capture the holding, not the full opinion. Context goes in the document-level `summary`.
- **CFPB enforcement**: capture findings, not settlement terms.
- **Guidance**: capture the policy position with enough context to make its scope clear.
- **Bureau patterns**: one documented behavior per chunk, with specific enforcement actions cited.
- **Playbooks**: one strategic decision per chunk, self-contained.

Chunk `position` must be `1..N` with no gaps.

## Choosing `applies_to` tags

Tag choice follows the four rules in [`TAG_VOCABULARY.md`](TAG_VOCABULARY.md):

1. Statute chunks primarily use statute tags.
2. Classification tags are added only when the chunk directly speaks to that condition.
3. **Never add a tag that isn't already in `TAG_VOCABULARY.md`.** If you need a new one, propose it in a separate PR that updates `TAG_VOCABULARY.md` AND the validator's `CLASSIFICATION_TAGS` or `STATUTE_TAGS` sets in `scripts/validate.py`. Don't silently extend the vocabulary.
4. 1-3 tags per chunk is the target. The validator warns at 4+; take warnings seriously.

## Writing a summary

Document-level summaries get injected into agent context when the full chunk list is retrieved. Write for an AI agent that knows FCRA/FDCPA domain basics but doesn't know this specific document.

Good summary:

> "Establishes the §611 reinvestigation procedure: when a consumer disputes an item, the CRA must conduct a reasonable reinvestigation within 30 days (45 if additional information is submitted). The CRA must notify the furnisher, consider all relevant information provided by the consumer, and either verify, modify, or delete the disputed item. Deletions must be permanent unless specific procedural requirements for reinsertion are met."

Not a good summary:

> "This is 15 U.S.C. §1681i, a very important FCRA statute that governs reinvestigations. It is used in many dispute cases."

## PR checklist

- [ ] Validator passes: `python scripts/validate.py corpus/`
- [ ] Stats run cleanly and show your additions: `python scripts/stats.py`
- [ ] New documents cite stable primary-source URLs
- [ ] Chunks follow the type-specific chunking approach from `METHODOLOGY.md`
- [ ] All tags are already in `TAG_VOCABULARY.md` (or your PR adds them properly)
- [ ] Document-level `summary` is written for agent context, not lay readers

## What won't be merged

PRs that fail validation. PRs adding tags without updating the vocabulary. PRs sourcing from commercial databases, blog posts, or secondary summaries. PRs that duplicate existing documents without adding genuinely new content. PRs that make claims unsupported by their cited primary sources.

## Issues

For documents that should be added but you don't have time to prepare a PR: open an issue with the citation and a brief note on why it belongs. For validator improvements or schema gaps: open an issue describing the specific case the current spec doesn't handle.

## License for contributions

By submitting a pull request, you agree that your contribution is licensed under the same dual license as the repository: CC-BY-4.0 for corpus content, MIT for code.
