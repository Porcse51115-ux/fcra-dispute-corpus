# Schema Reference

Every file in `corpus/` conforms to the same top-level structure, and every document inside conforms to the same per-document schema. This file is the specification. For the controlled vocabulary that fills the `applies_to` field, see `TAG_VOCABULARY.md`.

## Top-level file structure

Each JSON file in `corpus/` is an object with three keys:

```json
{
  "$schema_version": "1.0.0",
  "$notes": "One-paragraph description of what this file contains and how it was curated.",
  "documents": [ ... ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `$schema_version` | string | yes | Semantic version. Bumps on breaking schema changes. Currently `1.0.0` across all files. |
| `$notes` | string | yes | Curator notes about the file's scope and sourcing approach. Human-readable, not machine-parsed. |
| `documents` | array | yes | The documents in this collection. Must be non-empty. |

The `$`-prefixed metadata keys are a convention borrowed from JSON Schema. They mark fields that describe the file itself rather than its content.

## Document schema

Each entry in `documents[]` is an object with nine fields:

```json
{
  "citation": "15 U.S.C. §1681c",
  "title": "Requirements relating to information contained in consumer reports",
  "source_type": "statute",
  "jurisdiction": "US-federal",
  "doc_date": "2003-12-04",
  "applies_to": ["obsolete", "accuracy_procedures"],
  "summary": "One or two paragraphs explaining what this document says and why it matters.",
  "source_url": "https://www.law.cornell.edu/uscode/text/15/1681c",
  "chunks": [ ... ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `citation` | string | yes | The canonical legal citation. Format depends on `source_type` — see "Citation format conventions" below. |
| `title` | string | yes | Human-readable title. Should match the source document's own title when one exists. |
| `source_type` | enum | yes | One of: `statute`, `case_law`, `cfpb_enforcement`, `cfpb_guidance`, `bureau_pattern`, `playbook`. Must match the containing file (see "File ↔ source_type mapping" below). |
| `jurisdiction` | string | yes | Jurisdiction code. Currently all entries are `US-federal`. |
| `doc_date` | ISO date | yes | For statutes: effective date of the current amendment. For cases: decision date. For enforcement actions: order date. For guidance: publication date. For patterns and playbooks: last update. |
| `applies_to` | array of strings | yes | Topic tags drawn from `TAG_VOCABULARY.md`. Non-empty. Documents may draw from both the classification and statute vocabularies when both apply. |
| `summary` | string | yes | A plain-language summary written for an AI agent to use as context when retrieving the chunk list. Should capture what the document says AND why it matters for dispute strategy. |
| `source_url` | string | yes | A URL where the primary source can be verified. Prefer stable government or academic archives (Cornell LII, govinfo.gov, consumerfinance.gov) over commercial databases. |
| `chunks` | array | yes | The retrievable content chunks for this document. Non-empty. |

## Chunk schema

Each entry in `chunks[]` is an object with five fields:

```json
{
  "chunk_type": "subsection",
  "position": 1,
  "citation_label": "§1681c(a)(4)",
  "applies_to": ["obsolete"],
  "content": "Except as authorized under subsection (b), no consumer reporting agency may make any consumer report containing any of the following items of information: ... (4) Accounts placed for collection or charged to profit and loss which antedate the report by more than seven years."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `chunk_type` | enum | yes | One of: `subsection`, `holding`, `finding`, `guidance`, `pattern`, `playbook`. Must be compatible with the parent document's `source_type` (see "Chunk type compatibility" below). |
| `position` | integer | yes | 1-indexed ordinal position of this chunk within the document. Positions must be exactly `1..N` with no gaps and no duplicates. |
| `citation_label` | string | yes | A specific sub-citation that identifies this chunk within the parent document. For statutes: the subsection letter/number (`§1681c(a)(4)`). For cases: the specific holding being quoted. For enforcement actions: the paragraph of the consent order. |
| `applies_to` | array of strings | yes | Topic tags drawn from `TAG_VOCABULARY.md`. Non-empty, 1-3 tags recommended, 4+ triggers a validator warning (per Rule 4). |
| `content` | string | yes | The actual text that gets embedded and retrieved. Should be self-contained — a reader looking at just this chunk should understand what it says without needing adjacent chunks. |

## File ↔ source_type mapping

Each file in `corpus/` holds documents of exactly one `source_type`:

| File | `source_type` |
|---|---|
| `statutes.json` | `statute` |
| `case_law.json` | `case_law` |
| `cfpb_enforcement.json` | `cfpb_enforcement` |
| `guidance.json` | `cfpb_guidance` |
| `bureau_patterns.json` | `bureau_pattern` |
| `playbooks.json` | `playbook` |

The validator enforces this mapping — a document in `statutes.json` cannot declare `source_type: "case_law"`.

## Chunk type compatibility

Each `source_type` permits a specific set of `chunk_type` values. Most source types permit exactly one chunk type; two of them permit a secondary type when documents mix content shapes:

| `source_type` | Allowed `chunk_type` values |
|---|---|
| `statute` | `subsection` |
| `case_law` | `holding` |
| `cfpb_enforcement` | `finding` |
| `cfpb_guidance` | `guidance`, `finding` |
| `bureau_pattern` | `pattern`, `finding` |
| `playbook` | `playbook` |

The `cfpb_guidance` and `bureau_pattern` exceptions reflect reality: CFPB Supervisory Highlights contain specific examination findings alongside policy guidance, and bureau pattern documents cite the enforcement findings that substantiate them.

## Chunk type semantics

| `chunk_type` | What it captures |
|---|---|
| `subsection` | One subsection or logically distinct provision of a statute. For FCRA §1681c, each lettered subsection becomes its own chunk. |
| `holding` | The legal holding or rule of law from a judicial decision. Facts and procedural history go in the document-level `summary`; chunks capture the binding legal pronouncement. |
| `finding` | A factual finding or legal conclusion from a CFPB consent order or supervisory examination. Supports factually-grounded dispute arguments. |
| `guidance` | A policy position or supervisory expectation articulated in an advisory opinion or bulletin. |
| `pattern` | A documented behavioral pattern of a specific credit bureau, derived from enforcement actions, published examination findings, or aggregated case data. |
| `playbook` | A strategic recommendation synthesizing statute, case law, and bureau patterns into actionable dispute guidance. Playbooks are opinionated derived content, not primary sources. |

## Citation format conventions

**Statutes** use the United States Code citation form:
`15 U.S.C. §1681b(a)(2)`

**Cases** use the standard reporter citation form:
`Boggio v. USAA Fed. Sav. Bank, 696 F.3d 611 (6th Cir. 2012)`

**CFPB enforcement actions** use the action number form:
`In re Equifax Information Services LLC, 2017-CFPB-0004`

**Guidance documents** use the publication identifier form, where one exists:
`CFPB Supervisory Highlights, Issue 27 (Spring 2022)`

**Bureau patterns and playbooks** use descriptive titles:
`Bureau Pattern — Automated e-OSCAR Dispute Handling`
`Playbook — When to Escalate to §1681n Willfulness`

## The `applies_to` vocabulary

The `applies_to` field drives filter-then-search retrieval and uses a strictly controlled two-vocabulary system. See `TAG_VOCABULARY.md` for the full lists and the rules for choosing tags. The high-level split:

- **Classification tags** describe credit-item conditions (`obsolete`, `collection`, `charge_off`, `identity_theft`, etc.).
- **Statute tags** describe legal concepts (`reinvestigation`, `permissible_purpose`, `furnisher_duty`, `willful_noncompliance`, etc.).

A single chunk often draws from both — a §605 obsolescence chunk might carry `["obsolete"]` (classification) alongside no statute tag, while a §611 reinvestigation chunk carries `["reinvestigation"]` (statute) alongside no classification tag. The vocabularies compose freely.

## What the schema does not enforce

Several properties are convention, not validation:

- **Chunk content length.** No minimum or maximum. In practice, chunks range from one sentence (for a tight statutory subsection) to several paragraphs (for a dense holding). The guiding question is: "Can this stand alone as a retrievable unit?"
- **Summary tone.** Summaries are written for agent context, not for lay readers. They assume FCRA/FDCPA domain knowledge.
- **Tag count per chunk.** The validator warns at 4+ tags per chunk (per `TAG_VOCABULARY.md` Rule 4) but does not reject. This is a smell, not a bug.

## Validation

The script at `scripts/validate.py` enforces the required fields, correct types, chunk_type ↔ source_type compatibility, and `applies_to` vocabulary compliance. Run it before committing any corpus change:

python scripts/validate.py corpus/


Exit code is `0` on success, `1` on any error. Warnings do not fail the validation but are printed for review.
