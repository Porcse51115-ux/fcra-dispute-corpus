"""Reproducible corpus statistics for fcra-dispute-corpus.

Prints document counts, chunk counts, chunk type distribution,
source type distribution, and tag frequency. Stdlib only.

Usage:
    python scripts/stats.py                      # defaults to corpus/
    python scripts/stats.py corpus/
    python scripts/stats.py --json               # machine-readable
    python scripts/stats.py --json > stats.json  # pipe to file
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


FILES = [
    "statutes.json",
    "case_law.json",
    "cfpb_enforcement.json",
    "guidance.json",
    "bureau_patterns.json",
    "playbooks.json",
]


def collect_stats(corpus_dir: Path) -> dict[str, Any]:
    """Walk the corpus and compute statistics.

    Returns a nested dict suitable for either human display or JSON output.
    """
    per_file: dict[str, dict[str, Any]] = {}
    all_chunk_types: Counter[str] = Counter()
    all_source_types: Counter[str] = Counter()
    all_tags: Counter[str] = Counter()
    all_jurisdictions: Counter[str] = Counter()

    total_docs = 0
    total_chunks = 0
    total_content_chars = 0

    for fname in FILES:
        path = corpus_dir / fname
        if not path.exists():
            per_file[fname] = {"error": f"file not found: {path}"}
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            per_file[fname] = {"error": f"JSON parse error: {e}"}
            continue

        docs = data.get("documents", [])
        file_chunks = 0
        file_content_chars = 0
        file_chunk_types: Counter[str] = Counter()
        file_tags: Counter[str] = Counter()
        file_source_types: Counter[str] = Counter()

        for doc in docs:
            if not isinstance(doc, dict):
                continue

            st = doc.get("source_type")
            if st:
                file_source_types[st] += 1
                all_source_types[st] += 1

            for tag in doc.get("applies_to", []) or []:
                all_tags[tag] += 1
                file_tags[tag] += 1

            for chunk in doc.get("chunks", []) or []:
                if not isinstance(chunk, dict):
                    continue

                file_chunks += 1
                total_chunks += 1

                ct = chunk.get("chunk_type")
                if ct:
                    file_chunk_types[ct] += 1
                    all_chunk_types[ct] += 1

                content = chunk.get("content", "")
                if isinstance(content, str):
                    file_content_chars += len(content)
                    total_content_chars += len(content)

                for tag in chunk.get("applies_to", []) or []:
                    all_tags[tag] += 1
                    file_tags[tag] += 1

            jurisdiction = doc.get("jurisdiction")
            if jurisdiction:
                all_jurisdictions[jurisdiction] += 1

        total_docs += len(docs)

        per_file[fname] = {
            "docs": len(docs),
            "chunks": file_chunks,
            "content_chars": file_content_chars,
            "avg_chars_per_chunk": round(file_content_chars / file_chunks, 1) if file_chunks else 0,
            "source_types": dict(file_source_types),
            "chunk_types": dict(file_chunk_types),
            "top_tags": dict(file_tags.most_common(5)),
        }

    return {
        "totals": {
            "files": len([f for f in FILES if (corpus_dir / f).exists()]),
            "documents": total_docs,
            "chunks": total_chunks,
            "content_chars": total_content_chars,
            "avg_chars_per_chunk": round(total_content_chars / total_chunks, 1) if total_chunks else 0,
        },
        "source_type_distribution": dict(all_source_types),
        "chunk_type_distribution": dict(all_chunk_types),
        "jurisdiction_distribution": dict(all_jurisdictions),
        "top_tags": dict(all_tags.most_common(20)),
        "tag_vocabulary_size": len(all_tags),
        "per_file": per_file,
    }


def _print_human(stats: dict[str, Any]) -> None:
    totals = stats["totals"]
    print(f"=== fcra-dispute-corpus statistics ===")
    print()
    print(f"Totals")
    print(f"  files:        {totals['files']}")
    print(f"  documents:    {totals['documents']}")
    print(f"  chunks:       {totals['chunks']}")
    print(f"  content:      {totals['content_chars']:,} chars")
    print(f"  avg chunk:    {totals['avg_chars_per_chunk']} chars")
    print()

    print("Source type distribution")
    for st, n in sorted(stats["source_type_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {st:<20} {n:>4} docs")
    print()

    print("Chunk type distribution")
    for ct, n in sorted(stats["chunk_type_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {ct:<20} {n:>4} chunks")
    print()

    print(f"Tag vocabulary size: {stats['tag_vocabulary_size']} distinct tags used")
    print("Top 20 most-used tags")
    for tag, n in stats["top_tags"].items():
        print(f"  {tag:<32} {n:>4}")
    print()

    print("Per-file breakdown")
    for fname, pf in stats["per_file"].items():
        if "error" in pf:
            print(f"  {fname}: ERROR — {pf['error']}")
            continue
        print(f"  {fname}")
        print(f"    docs: {pf['docs']}, chunks: {pf['chunks']}, "
              f"avg chunk: {pf['avg_chars_per_chunk']} chars")


def main(argv: list[str]) -> int:
    args = argv[1:]
    want_json = False
    corpus_dir = Path("corpus")

    for a in args:
        if a == "--json":
            want_json = True
        elif a.startswith("-"):
            print(f"usage: python scripts/stats.py [corpus_dir] [--json]", file=sys.stderr)
            return 2
        else:
            corpus_dir = Path(a)

    if not corpus_dir.exists():
        print(f"error: {corpus_dir} does not exist", file=sys.stderr)
        return 2

    stats = collect_stats(corpus_dir)

    if want_json:
        print(json.dumps(stats, indent=2))
    else:
        _print_human(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
