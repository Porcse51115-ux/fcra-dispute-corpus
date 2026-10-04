"""Schema validator for fcra-dispute-corpus.

Enforces the schema documented in docs/SCHEMA.md and the controlled
`applies_to` vocabulary documented in docs/TAG_VOCABULARY.md.

Exit code is 0 on success, 1 on any validation failure. Stdlib only
— no external deps.

Usage:
    python scripts/validate.py corpus/
    python scripts/validate.py corpus/statutes.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# ─── Schema constants (mirror docs/SCHEMA.md and docs/TAG_VOCABULARY.md) ──

REQUIRED_TOP_FIELDS = {"$schema_version", "$notes", "documents"}

REQUIRED_DOC_FIELDS = {
    "citation",
    "title",
    "source_type",
    "jurisdiction",
    "doc_date",
    "applies_to",
    "summary",
    "source_url",
    "chunks",
}

REQUIRED_CHUNK_FIELDS = {
    "chunk_type",
    "position",
    "citation_label",
    "applies_to",
    "content",
}

VALID_SOURCE_TYPES = {
    "statute",
    "case_law",
    "cfpb_enforcement",
    "cfpb_guidance",
    "bureau_pattern",
    "playbook",
}

VALID_CHUNK_TYPES = {
    "subsection",
    "holding",
    "finding",
    "guidance",
    "pattern",
    "playbook",
}

# ─── Two-vocabulary tag system (per docs/TAG_VOCABULARY.md v1.0.0) ────────

CLASSIFICATION_TAGS = {
    "obsolete",
    "collection",
    "charge_off",
    "mixed_file",
    "identity_theft",
    "duplicate",
    "paid_reporting_open",
    "authorized_user",
    "zombie_debt",
    "medical",
    "hard_inquiry_unauthorized",
}

STATUTE_TAGS = {
    "reinvestigation",
    "permissible_purpose",
    "furnisher_duty",
    "accuracy_procedures",
    "willful_noncompliance",
    "negligent_noncompliance",
    "disclosure_to_consumer",
    "debt_validation",
    "false_representation",
    "verification_failure",
    "definitions",
}

VALID_APPLIES_TO = CLASSIFICATION_TAGS | STATUTE_TAGS

# A file name maps to the source_type its documents must declare.
FILE_TO_SOURCE_TYPE = {
    "statutes.json": "statute",
    "case_law.json": "case_law",
    "cfpb_enforcement.json": "cfpb_enforcement",
    "guidance.json": "cfpb_guidance",
    "bureau_patterns.json": "bureau_pattern",
    "playbooks.json": "playbook",
}

# A source_type permits certain chunk_types. Some source_types permit
# more than one (e.g. a bureau_patterns doc could have both `pattern`
# and `finding` chunks if a pattern is substantiated by a cited finding).
SOURCE_TYPE_TO_ALLOWED_CHUNK_TYPES = {
    "statute": {"subsection"},
    "case_law": {"holding"},
    "cfpb_enforcement": {"finding"},
    "cfpb_guidance": {"guidance", "finding"},
    "bureau_pattern": {"pattern", "finding"},
    "playbook": {"playbook"},
}

# docs/TAG_VOCABULARY.md Rule 4: "Aim for 1-3 tags per chunk; four or more
# is a smell that the chunk is too broad and should be split." We warn
# rather than error so this stays advisory.
TAGS_PER_CHUNK_WARN_THRESHOLD = 4


# ─── Validation errors ──────────────────────────────────────────────────


class ValidationIssue:
    """One validation issue — may be an error or warning."""

    def __init__(self, path: str, message: str, severity: str = "error"):
        self.path = path
        self.message = message
        self.severity = severity  # "error" or "warning"

    def __str__(self) -> str:
        tag = "WARN " if self.severity == "warning" else "ERROR"
        return f"  [{tag}] {self.path}: {self.message}"


# ─── Validators ─────────────────────────────────────────────────────────


def _validate_applies_to(
    value: Any,
    ctx: str,
    is_chunk: bool,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if value is None:
        return [ValidationIssue(ctx, "applies_to is required")]

    if not isinstance(value, list):
        return [ValidationIssue(ctx, f"applies_to must be an array, got {type(value).__name__}")]

    if not value:
        return [ValidationIssue(ctx, "applies_to must be a non-empty array")]

    bad = [v for v in value if v not in VALID_APPLIES_TO]
    if bad:
        issues.append(
            ValidationIssue(
                ctx,
                f"applies_to values not in TAG_VOCABULARY.md: {bad} "
                f"(classification tags: {sorted(CLASSIFICATION_TAGS)[:4]}... "
                f"statute tags: {sorted(STATUTE_TAGS)[:4]}...)",
            )
        )

    if is_chunk and len(value) >= TAGS_PER_CHUNK_WARN_THRESHOLD:
        issues.append(
            ValidationIssue(
                ctx,
                f"chunk has {len(value)} tags — Rule 4 of TAG_VOCABULARY.md "
                f"suggests splitting chunks with 4+ tags",
                severity="warning",
            )
        )

    return issues


def _validate_chunk(
    chunk: Any,
    doc_source_type: str,
    doc_citation: str,
    chunk_idx: int,
    file_name: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    ctx = f"{file_name}::{doc_citation}::chunk[{chunk_idx}]"

    if not isinstance(chunk, dict):
        return [ValidationIssue(ctx, f"chunk must be an object, got {type(chunk).__name__}")]

    missing = REQUIRED_CHUNK_FIELDS - chunk.keys()
    if missing:
        issues.append(ValidationIssue(ctx, f"missing required fields: {sorted(missing)}"))

    chunk_type = chunk.get("chunk_type")
    if chunk_type is not None and chunk_type not in VALID_CHUNK_TYPES:
        issues.append(
            ValidationIssue(
                ctx,
                f"chunk_type {chunk_type!r} is not in VALID_CHUNK_TYPES {sorted(VALID_CHUNK_TYPES)}",
            )
        )
    elif chunk_type is not None:
        allowed = SOURCE_TYPE_TO_ALLOWED_CHUNK_TYPES.get(doc_source_type, set())
        if allowed and chunk_type not in allowed:
            issues.append(
                ValidationIssue(
                    ctx,
                    f"chunk_type {chunk_type!r} not permitted for source_type "
                    f"{doc_source_type!r} (allowed: {sorted(allowed)})",
                )
            )

    pos = chunk.get("position")
    if pos is not None and (not isinstance(pos, int) or pos < 1):
        issues.append(ValidationIssue(ctx, f"position must be a positive integer, got {pos!r}"))

    issues.extend(_validate_applies_to(chunk.get("applies_to"), ctx, is_chunk=True))

    content = chunk.get("content")
    if content is not None and (not isinstance(content, str) or not content.strip()):
        issues.append(ValidationIssue(ctx, "content must be a non-empty string"))

    citation_label = chunk.get("citation_label")
    if citation_label is not None and (not isinstance(citation_label, str) or not citation_label.strip()):
        issues.append(ValidationIssue(ctx, "citation_label must be a non-empty string"))

    return issues


def _validate_document(
    doc: Any,
    doc_idx: int,
    file_name: str,
    expected_source_type: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    ctx = f"{file_name}::doc[{doc_idx}]"

    if not isinstance(doc, dict):
        return [ValidationIssue(ctx, f"document must be an object, got {type(doc).__name__}")]

    missing = REQUIRED_DOC_FIELDS - doc.keys()
    if missing:
        issues.append(ValidationIssue(ctx, f"missing required fields: {sorted(missing)}"))

    citation = doc.get("citation", f"<doc[{doc_idx}] no-citation>")

    source_type = doc.get("source_type")
    if source_type is not None:
        if source_type not in VALID_SOURCE_TYPES:
            issues.append(
                ValidationIssue(
                    ctx,
                    f"source_type {source_type!r} is not in VALID_SOURCE_TYPES {sorted(VALID_SOURCE_TYPES)}",
                )
            )
        elif source_type != expected_source_type:
            issues.append(
                ValidationIssue(
                    ctx,
                    f"source_type {source_type!r} does not match expected "
                    f"{expected_source_type!r} for file {file_name}",
                )
            )

    for field in ("citation", "title", "summary", "source_url", "jurisdiction", "doc_date"):
        v = doc.get(field)
        if v is not None and (not isinstance(v, str) or not v.strip()):
            issues.append(ValidationIssue(ctx, f"{field} must be a non-empty string"))

    issues.extend(_validate_applies_to(doc.get("applies_to"), ctx, is_chunk=False))

    chunks = doc.get("chunks")
    if chunks is not None:
        if not isinstance(chunks, list) or not chunks:
            issues.append(ValidationIssue(ctx, "chunks must be a non-empty array"))
        else:
            # Validate position monotonicity: positions should be exactly 1..N.
            positions = [c.get("position") for c in chunks if isinstance(c, dict)]
            if positions and all(isinstance(p, int) for p in positions):
                expected_positions = set(range(1, len(chunks) + 1))
                if set(positions) != expected_positions:
                    issues.append(
                        ValidationIssue(
                            ctx,
                            f"chunk positions must be exactly 1..{len(chunks)}; "
                            f"got {sorted(positions)}",
                        )
                    )

            # Validate each chunk
            for i, chunk in enumerate(chunks):
                issues.extend(
                    _validate_chunk(
                        chunk,
                        doc_source_type=source_type or expected_source_type,
                        doc_citation=citation,
                        chunk_idx=i,
                        file_name=file_name,
                    )
                )

    return issues


def _validate_file(path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    file_name = path.name

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [ValidationIssue(file_name, f"JSON parse error: {e}")]
    except OSError as e:
        return [ValidationIssue(file_name, f"file read error: {e}")]

    if not isinstance(data, dict):
        return [ValidationIssue(file_name, f"top-level must be an object, got {type(data).__name__}")]

    missing = REQUIRED_TOP_FIELDS - data.keys()
    if missing:
        issues.append(ValidationIssue(file_name, f"missing top-level fields: {sorted(missing)}"))

    schema_version = data.get("$schema_version")
    if schema_version != "1.0.0":
        issues.append(
            ValidationIssue(
                file_name,
                f"$schema_version must be '1.0.0', got {schema_version!r}",
            )
        )

    notes = data.get("$notes")
    if notes is not None and (not isinstance(notes, str) or not notes.strip()):
        issues.append(ValidationIssue(file_name, "$notes must be a non-empty string"))

    expected_source_type = FILE_TO_SOURCE_TYPE.get(file_name)
    if expected_source_type is None:
        # Unknown file — still validate the structure, but can't check source_type consistency.
        docs = data.get("documents", [])
        if docs and isinstance(docs, list) and isinstance(docs[0], dict):
            expected_source_type = docs[0].get("source_type", "")

    documents = data.get("documents")
    if documents is not None:
        if not isinstance(documents, list):
            issues.append(ValidationIssue(file_name, "documents must be an array"))
        else:
            for i, doc in enumerate(documents):
                issues.extend(
                    _validate_document(
                        doc,
                        doc_idx=i,
                        file_name=file_name,
                        expected_source_type=expected_source_type or "",
                    )
                )

    return issues


# ─── Main ────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python scripts/validate.py <path>")
        print("  <path> may be a corpus/ directory or a single .json file.")
        return 2

    target = Path(argv[1])
    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 2

    if target.is_dir():
        files = sorted(target.glob("*.json"))
        if not files:
            print(f"error: no .json files in {target}/", file=sys.stderr)
            return 2
    else:
        files = [target]

    all_errors: list[ValidationIssue] = []
    all_warnings: list[ValidationIssue] = []
    for f in files:
        print(f"validating {f}...")
        issues = _validate_file(f)
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        if issues:
            if errors:
                print(f"  {len(errors)} error(s):")
                for e in errors:
                    print(e)
            if warnings:
                print(f"  {len(warnings)} warning(s):")
                for w in warnings:
                    print(w)
            if not errors:
                print("  OK (with warnings)")
            all_errors.extend(errors)
            all_warnings.extend(warnings)
        else:
            print("  OK")

    print()
    if all_errors:
        print(f"FAIL: {len(all_errors)} error(s), {len(all_warnings)} warning(s) across {len(files)} file(s)")
        return 1
    if all_warnings:
        print(f"PASS: {len(files)} file(s) validated clean ({len(all_warnings)} warning(s))")
    else:
        print(f"PASS: {len(files)} file(s) validated clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
