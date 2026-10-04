# Methodology

This document explains how the corpus was built — the sourcing criteria, chunking approach, tag strategy, and the judgment calls behind them. It is intentionally honest about tradeoffs and limits.

## Sourcing criteria

Every document in the corpus had to meet all four of these criteria before inclusion:

**1. Primary source.** Statutes come from the United States Code via Cornell LII. Cases come from federal court opinions (preference for appellate and Supreme Court decisions over district court orders). CFPB enforcement actions come from the agency's own published consent orders. Guidance documents come from CFPB Supervisory Highlights, advisory opinions, and bulletins published by the agency itself. No commercial databases, no secondary summaries, no blog posts.

**2. Stable archive URL.** Every document's `source_url` points to a location where the primary source can still be verified. Cornell LII for statutes. CourtListener or official court websites for cases. consumerfinance.gov for CFPB material. This matters because a corpus whose sources go dark is a corpus that can't be audited.

**3. Dispute-relevance.** This isn't a general FCRA/FDCPA reference. Documents were selected because they bear on specific decisions a dispute strategist has to make: whether an item is reportable, whether a dispute will be treated as frivolous, what the bureau's reinvestigation obligations are, when willfulness damages become available. If a statute or case doesn't change what a strategist does, it was left out even when relevant to the broader body of law.

**4. Verifiable claims only.** Summaries and playbooks make assertions about law and bureau behavior. Every assertion traces back to the primary sources in the corpus itself. Bureau pattern documents in particular cite specific CFPB enforcement actions as substantiation — the pattern "bureaus often verify furnisher claims without independent investigation" is backed by the Wells Fargo and Hyundai Capital consent orders, not inferred from aggregate consumer complaints.

## What's deliberately missing

Several things are not in this corpus by design:

- **State-level consumer protection law.** California's CCRAA, New York's FCRA analogue, and other state statutes often exceed federal protections. They're out of scope here. A production system would layer state law on top of this federal baseline.
- **District court decisions.** With rare exceptions, this corpus prefers appellate rulings. District court orders can establish facts but rarely create binding precedent that would survive appeal. Including every district court dispute case would multiply the corpus size without proportionally improving retrieval quality.
- **Credit scoring regulation.** FICO scoring methodology, VantageScore specifics, and the regulation of credit scoring under ECOA (Regulation B) are out of scope. The corpus addresses the reporting layer, not the scoring layer.
- **Industry trade publications.** Trade press often reflects what the industry believes about the law, which is not always what the law actually says. Primary sources only.
- **Historical versions.** Statutes evolve. This corpus holds the current effective version of each section, not amendment history. A researcher comparing a 1996 version to a 2024 version would need external resources.

## Chunking strategy

Chunks are the unit of retrieval. The chunking approach differs by `source_type`:

**Statute chunks are usually one subsection each.** FCRA §1681c has eight chunks because it has eight functionally distinct subsections. A single statute section would be too coarse (the embedding would be a blurry average of several unrelated rules), and chunking below the subsection level would lose the semantic unit that attorneys actually cite. Where a subsection is tightly bound to another by cross-reference, they stay together as one chunk.

**Case chunks capture the holding, not the opinion.** A federal appellate opinion is 20-40 pages, most of which is procedural history, facts, and reasoning. The retrievable value is the rule of law — the one or two paragraphs that bind future courts. Case chunks capture that rule verbatim where possible, with surrounding context sufficient to understand what the rule applies to. The full procedural and factual background goes in the document-level `summary`.

**CFPB enforcement chunks capture findings.** A CFPB consent order includes background, legal conclusions, and ordered remedies. The retrievable value for dispute strategy is the findings — the specific violations the CFPB documented. A chunk from the Wells Fargo consent order captures what Wells Fargo did wrong according to the CFPB, not the agreed-upon settlement amount.

**Guidance chunks capture positions.** CFPB Supervisory Highlights and advisory opinions articulate policy positions. A guidance chunk captures the position itself (what the CFPB expects of bureaus or furnishers), with enough surrounding text to make the position's scope clear. Supervisory Highlights sometimes include specific examination findings — those are chunked as `finding`, not `guidance`, because they're factual rather than normative.

**Bureau pattern chunks capture one documented behavior each.** Patterns are the most inferential content in the corpus. Each pattern chunk corresponds to a specific behavioral tendency (e.g. e-OSCAR dispute handling, verification rates) and cites the enforcement actions or examination findings that substantiate it.

**Playbook chunks capture one strategic decision each.** The playbook on §1681n willfulness escalation has four chunks because there are four distinct decision points in that escalation. Each chunk is self-contained — a strategist reading just one chunk should be able to make the specific decision it addresses.

## The two-vocabulary tag system

Tag design was the hardest part of the corpus. An uncontrolled vocabulary leads to tag sprawl, inconsistent retrieval, and arguments over whether "furnisher_accuracy_duty" and "accuracy_procedures" mean the same thing. The two-vocabulary approach constrains that:

**Classification tags describe credit items.** These are the categories a credit report item might fall into: `obsolete`, `collection`, `charge_off`, `duplicate`, `identity_theft`, and so on. A Classifier agent sees a credit item and assigns one or more classification tags based on what the item looks like.

**Statute tags describe legal concepts.** These are the concepts in the law itself: `reinvestigation` (what §611 requires), `permissible_purpose` (what §604 requires), `furnisher_duty` (what §623 requires), `willful_noncompliance` (what §1681n enables), and so on. A Strategy agent sees a classified item and needs legal concepts that apply to it.

The vocabularies compose. A §605 chunk about obsolete items carries `["obsolete"]` because that's what the chunk is about. A §611 chunk about the reinvestigation procedure carries `["reinvestigation"]` because that's what *that* chunk is about. A case-law holding addressing a furnisher's duty to reinvestigate after notice carries both: `["furnisher_duty", "reinvestigation"]`.

Filter-then-search is the retrieval pattern this enables. A query like "obsolete charge-off past the seven-year window" filters first on `applies_to=["obsolete"]`, then runs similarity search over the filtered set. Compared to pure similarity search, this halves retrieval noise and makes the surfaced chunks directly relevant to the dispute at hand.

Four rules govern tag choice. See [`TAG_VOCABULARY.md`](TAG_VOCABULARY.md) for the full statement; summary here:

1. Statute chunks primarily use statute tags.
2. Classification tags are added only when the chunk directly speaks to that condition.
3. New tags require updating `TAG_VOCABULARY.md` first — no silent additions.
4. 1-3 tags per chunk is the target; 4+ is a smell. The validator warns at 4+.

## Judgment calls worth naming

Several decisions could have gone differently. Being explicit about them helps anyone extending the corpus:

**Chunk size granularity.** A §611 reinvestigation chunk could have been split further into "what the bureau must do" vs. "what the furnisher must do" sub-chunks. It wasn't, because the current chunking (one subsection = one chunk) produced retrieval quality that didn't justify the complexity cost of finer-grained chunks. If a future retrieval use case needed more granular surfacing, splitting is additive — existing chunks stay, new ones get added with higher position numbers.

**Case selection.** Fifteen appellate cases is not fifteen *randomly selected* appellate cases. The selection privileges cases that establish rules strategists rely on in Round 2+ disputes: Boggio on furnisher reinvestigation duties, Spokeo on standing for FCRA claims, TransUnion v. Ramirez on class standing, Cortez on CRA reasonable procedures. A different curator might have included more early-FCRA cases or more state-court analogues. This curator didn't.

**Playbook inclusion.** Playbooks are inherently opinionated — they synthesize statute, case law, and bureau patterns into one practitioner's view of what works. They're included because an agent reasoning without strategic context tends to produce legally correct but tactically weak disputes. A reader who disagrees with a playbook's strategy can ignore the two playbook chunks (they're clearly tagged `source_type: "playbook"`) and retrieve from the primary sources alone.

**Bureau pattern inclusion.** The three bureau pattern documents are the most inferential content. They describe tendencies — "bureaus often rely on furnisher verification without independent investigation" — rather than binding rules. They're included because strategic choice-making depends on predicting bureau behavior, not just citing law. Every pattern cites specific enforcement actions as substantiation, but a reader who prefers rules-only retrieval can filter them out by `source_type`.

**Vocabulary conservatism.** 18 tags for 99 chunks is deliberately low tag density. A richer vocabulary could support more precise filtering, but every additional tag increases the chance of inconsistent application across documents. Starting with a conservative vocabulary and extending it as patterns emerge is more sustainable than starting broad and consolidating later.

## Reproducibility

The corpus can be regenerated from its primary sources. Every document has a `source_url`. Every citation is in a canonical format a researcher could re-retrieve. Chunking decisions are documented above. Tag assignments are reviewable per-chunk against the rules in `TAG_VOCABULARY.md`.

The scripts in this repository make the corpus's current state verifiable:

- `scripts/validate.py` enforces the schema and the controlled vocabulary.
- `scripts/stats.py` produces the statistics that back up any numeric claim in the README.
- `scripts/example_rag.py` runs an end-to-end retrieval demo without requiring the production backend.

Running all three on a clone of this repository is the fastest way to confirm the corpus holds together.

## What this corpus isn't

A reader seeing "FCRA corpus" might expect any of several things that this specifically is not:

- **Not a complete reference.** 12 statute sections is nowhere near the full FCRA. The 15 cases are nowhere near every important FCRA decision. The corpus is deliberately focused on dispute strategy, not on being an encyclopedia.
- **Not an automated extraction.** Every document was selected, chunked, summarized, and tagged by hand. There is no scraper. There is no LLM-generated summary. The curation effort is the point.
- **Not a benchmark.** No gold-standard query/answer pairs are included. If you need evaluation data for a RAG system, you'd need to build it on top of this corpus — the corpus itself doesn't ship with labeled queries.
- **Not maintenance-free.** CFPB enforcement actions get added regularly. Case law evolves. Statute amendments happen. A corpus that doesn't get maintained goes stale.

## Attribution

The curation effort — document selection, chunking strategy, summaries, tag vocabulary, schema design — is the original work in this repository and is licensed under CC-BY-4.0. The underlying legal texts are in the public domain. See [`LICENSE`](../LICENSE) for complete terms.
