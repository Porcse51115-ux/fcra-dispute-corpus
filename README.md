# fcra-dispute-corpus

A curated corpus of U.S. Fair Credit Reporting Act (FCRA) and Fair Debt Collection Practices Act (FDCPA) materials, structured for retrieval-augmented generation. 52 documents, 99 chunks, 18 topic tags. Includes federal statutes, landmark case law, CFPB enforcement actions, agency guidance, documented bureau behavior patterns, and strategic dispute playbooks. Each chunk carries a stable citation, topic tags, and context suitable for direct retrieval into a RAG pipeline.

This corpus powers the Strategy Agent in [Docket Strategist](https://github.com/Porcse51115-ux/docket-strategist), an AI-driven FCRA dispute system. It is published here as a standalone dataset so other projects can use it without pulling in a backend they do not need.

## Why this exists

Consumer credit disputes under the FCRA are won on specific statutory citations, case law precedent, and documented bureau behavior. A general-purpose language model can reason about this material but will cite incorrectly, invent precedent, or miss subsection-level nuance that matters for dispute strategy.

Grounding the model in a focused, well-structured corpus of primary sources changes that. The agent cites what the corpus says, not what the model remembers. The chunks are small enough to inject as context, specific enough to defend in writing, and tagged consistently enough to filter before similarity search.

This repository is the corpus itself, plus the tools to validate it and run a minimal demo against it.

## What's in the corpus

| File | Documents | Chunks | Content |
|---|---|---|---|
| `corpus/statutes.json` | 12 | 42 | FCRA and FDCPA statute sections |
| `corpus/case_law.json` | 15 | 18 | Federal appellate and Supreme Court decisions |
| `corpus/cfpb_enforcement.json` | 15 | 18 | CFPB consent orders against bureaus and furnishers |
| `corpus/guidance.json` | 5 | 7 | CFPB Supervisory Highlights and advisory opinions |
| `corpus/bureau_patterns.json` | 3 | 7 | Documented bureau behavior patterns |
| `corpus/playbooks.json` | 2 | 7 | Strategic dispute progression playbooks |

Every document carries a stable legal citation, source URL to a government or academic archive, publication date, jurisdiction, topic tags, and a plain-language summary. Every chunk carries a specific sub-citation (e.g. `§1681c(a)(4)`) and the retrievable text itself.

## Quick start

The corpus files are plain JSON — you can read them with any language. The included scripts are stdlib Python (no dependencies for validation and statistics):

```bash
# Validate the corpus structure
python scripts/validate.py corpus/

# Print corpus statistics (counts, distributions, tag frequencies)
python scripts/stats.py
```

For a minimal retrieval demo using voyage-3 embeddings and sqlite-vec:

```bash
pip install -e ".[rag]"
export VOYAGE_API_KEY=your_key_here
python scripts/example_rag.py "obsolete charge-off beyond seven year window"
```

The demo embeds every chunk once, stores them locally in a sqlite-vec database, and performs a filtered similarity search. It does not require a running backend, cloud database, or Docker — it's intended as a reference implementation you can lift into your own system.

## Document schema

Every corpus file follows the same shape:

```json
{
  "$schema_version": "1.0.0",
  "$notes": "What this file contains.",
  "documents": [
    {
      "citation": "15 U.S.C. §1681c",
      "title": "Requirements relating to information contained in consumer reports",
      "source_type": "statute",
      "jurisdiction": "US-federal",
      "doc_date": "2003-12-04",
      "applies_to": ["obsolete", "accuracy_procedures"],
      "summary": "...",
      "source_url": "https://www.law.cornell.edu/uscode/text/15/1681c",
      "chunks": [
        {
          "chunk_type": "subsection",
          "position": 1,
          "citation_label": "§1681c(a)(4)",
          "applies_to": ["obsolete"],
          "content": "..."
        }
      ]
    }
  ]
}
```

Full specification: [`docs/SCHEMA.md`](docs/SCHEMA.md). Tag vocabulary: [`docs/TAG_VOCABULARY.md`](docs/TAG_VOCABULARY.md). Curation approach: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## The tag vocabulary

The `applies_to` field drives filter-then-search retrieval. It uses two controlled vocabularies:

**Classification tags** describe credit item conditions: `obsolete`, `collection`, `charge_off`, `identity_theft`, `duplicate`, `hard_inquiry_unauthorized`, and others.

**Statute tags** describe legal concepts: `reinvestigation`, `permissible_purpose`, `furnisher_duty`, `accuracy_procedures`, `willful_noncompliance`, `debt_validation`, and others.

A single chunk can draw from both vocabularies. A §605 chunk about obsolete items carries `["obsolete"]`. A §611 chunk about the reinvestigation procedure carries `["reinvestigation"]`. A case-law holding addressing furnisher reinvestigation duties might carry both `["furnisher_duty", "reinvestigation"]`.

See [`docs/TAG_VOCABULARY.md`](docs/TAG_VOCABULARY.md) for the complete tag list and the rules governing tag choice.

## Current statistics

Generated from `scripts/stats.py` against the current state of `corpus/`:

- **52 documents, 99 chunks, 18 distinct tags in use**
- **~41,000 characters of curated content**, averaging 417 characters per chunk
- **Most-used tags**: `accuracy_procedures` (47 uses), `reinvestigation` (44), `furnisher_duty` (39), `collection` (27), `false_representation` (22)

Reproduce by running `python scripts/stats.py`.

## Honest limits

These are worth knowing before you use the corpus:

- **Snapshot, not live reference.** Statutes get amended; CFPB enforcement actions get added; case law evolves. This corpus reflects the state of U.S. consumer credit law as of its last update. Treat it as a research starting point, not an authoritative current reference.
- **U.S. federal only.** No state-level consumer protection laws, no Canadian or European equivalents.
- **Not legal advice.** This corpus is research material intended to ground AI-assisted dispute strategy. It does not substitute for consultation with a licensed attorney, and no attorney-client relationship is created by its use.
- **Chunking is opinionated.** The choice of what constitutes a chunk — subsection vs. full section, individual holding vs. combined rule — reflects judgment calls about retrieval granularity. The `chunk_type` field helps, but the opinion is baked in.
- **Playbooks are derived content.** The playbooks synthesize statute + case law + bureau patterns into strategic recommendations. They reflect one practitioner's view of effective dispute progression, not binding precedent.
- **Tag frequency is skewed.** Four tags account for the majority of uses (`accuracy_procedures`, `reinvestigation`, `furnisher_duty`, `collection`). Rarer tags like `duplicate` and `verification_failure` have one or two uses each — intentional, because they target specific niche scenarios.

## Provenance and attribution

The underlying legal texts referenced here — United States Code sections, federal court decisions, CFPB enforcement orders, and agency guidance — are works of the United States Government or quotations from public court records, and are themselves in the public domain or otherwise freely usable.

The original contributions in this repository — the selection of documents, the chunking strategy, the summaries, the tag vocabulary, the schema design, and the annotations — are licensed under CC-BY-4.0. The code under `scripts/` is MIT-licensed. See [`LICENSE`](LICENSE) for complete terms.

Attribution for derived works:

> This work includes material from fcra-dispute-corpus by Matthew Shea, licensed under CC-BY-4.0.
> Source: https://github.com/Porcse51115-ux/fcra-dispute-corpus

## Contributing

Pull requests welcome. Before opening one, read [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md). The short version: run `python scripts/validate.py corpus/` and `python scripts/stats.py` on your branch, cite primary sources with stable archive URLs, and respect the two-vocabulary tag system.

## Related projects

- [Docket Strategist](https://github.com/Porcse51115-ux/docket-strategist) — the multi-agent FCRA dispute strategist this corpus was built for. Uses pgvector + voyage-3 for retrieval; the structure here is identical to what the Strategy Agent sees at runtime.
- [Credit Docket](https://github.com/Porcse51115-ux/credit-docket) — the credit report monitoring and letter generation system Docket Strategist disputes through.

## License

Dual-licensed. Code under MIT, curated data under CC-BY-4.0. See [`LICENSE`](LICENSE) for complete terms.
