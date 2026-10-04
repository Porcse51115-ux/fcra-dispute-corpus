"""Minimal end-to-end RAG demo over the fcra-dispute-corpus.

Embeds every chunk once using voyage-3, stores them in a local sqlite-vec
database, and performs filter-then-search retrieval. No backend required.

Setup:
    pip install -e ".[rag]"
    export VOYAGE_API_KEY=your_key_here

Usage:
    python scripts/example_rag.py "obsolete charge-off beyond seven year window"
    python scripts/example_rag.py --tags obsolete,reinvestigation "disputing an old collection"
    python scripts/example_rag.py --rebuild "unauthorized hard inquiry"

The first run embeds the corpus (~5-10 seconds + API cost — voyage-3 is
cheap, under a cent for the full corpus). Subsequent runs reuse the
cached embeddings in corpus_demo.db unless --rebuild is passed.

This script is intentionally minimal — it mirrors what a Strategy agent
would do at runtime, in about 300 lines of standalone code. For a
production deployment, see Docket Strategist for the full pgvector +
async orchestration setup.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


# ─── Config ─────────────────────────────────────────────────────────────

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"
DB_PATH = Path(__file__).resolve().parent.parent / "corpus_demo.db"
EMBED_MODEL = "voyage-3"
EMBED_DIM = 1024
DEFAULT_TOP_K = 5


# ─── Chunk loader ───────────────────────────────────────────────────────


def load_all_chunks() -> list[dict[str, Any]]:
    """Walk corpus/ and return a flat list of chunks with document context attached."""
    chunks: list[dict[str, Any]] = []
    for json_path in sorted(CORPUS_DIR.glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        for doc in data.get("documents", []):
            doc_citation = doc.get("citation", "")
            doc_title = doc.get("title", "")
            doc_source_type = doc.get("source_type", "")
            for chunk in doc.get("chunks", []):
                chunks.append({
                    "file": json_path.name,
                    "doc_citation": doc_citation,
                    "doc_title": doc_title,
                    "source_type": doc_source_type,
                    "chunk_type": chunk.get("chunk_type", ""),
                    "position": chunk.get("position", 0),
                    "citation_label": chunk.get("citation_label", ""),
                    # Merge doc + chunk tags for filterable retrieval.
                    "tags": list(set(
                        (doc.get("applies_to") or []) + (chunk.get("applies_to") or [])
                    )),
                    "content": chunk.get("content", ""),
                })
    return chunks


# ─── Embedding ──────────────────────────────────────────────────────────


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts with voyage-3.

    Uses the voyageai client. Reads VOYAGE_API_KEY from env. Batches up to
    128 texts per request (voyage-3's max batch size).
    """
    try:
        import voyageai
    except ImportError:
        print("error: voyageai not installed. Run: pip install -e '.[rag]'", file=sys.stderr)
        sys.exit(2)

    if not os.environ.get("VOYAGE_API_KEY"):
        print("error: VOYAGE_API_KEY not set in environment", file=sys.stderr)
        sys.exit(2)

    client = voyageai.Client()
    all_embeddings: list[list[float]] = []
    batch_size = 128

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = client.embed(batch, model=EMBED_MODEL, input_type="document")
        all_embeddings.extend(result.embeddings)

    return all_embeddings


def embed_query(query: str) -> list[float]:
    """Embed a single query (uses input_type='query' per voyage-3 best practices)."""
    import voyageai

    client = voyageai.Client()
    result = client.embed([query], model=EMBED_MODEL, input_type="query")
    return result.embeddings[0]


# ─── Database ───────────────────────────────────────────────────────────


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a sqlite connection with sqlite-vec loaded as an extension."""
    try:
        import sqlite_vec
    except ImportError:
        print("error: sqlite-vec not installed. Run: pip install -e '.[rag]'", file=sys.stderr)
        sys.exit(2)

    conn = sqlite3.connect(str(db_path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def build_index(rebuild: bool = False) -> int:
    """Build the local index from the corpus. Returns number of chunks indexed."""
    if DB_PATH.exists() and not rebuild:
        print(f"index already exists at {DB_PATH} — use --rebuild to regenerate")
        return 0

    if DB_PATH.exists() and rebuild:
        DB_PATH.unlink()
        print(f"removed existing {DB_PATH}")

    print(f"loading chunks from {CORPUS_DIR}/ ...")
    chunks = load_all_chunks()
    print(f"loaded {len(chunks)} chunks")

    print(f"embedding with {EMBED_MODEL} (this calls the voyage API)...")
    t0 = time.time()
    embeddings = embed_texts([c["content"] for c in chunks])
    t1 = time.time()
    print(f"embedded {len(embeddings)} chunks in {t1 - t0:.1f}s")

    print(f"writing to {DB_PATH} ...")
    conn = _connect(DB_PATH)
    cur = conn.cursor()

    # Metadata table — one row per chunk with the content and tags.
    cur.execute("""
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            file TEXT NOT NULL,
            doc_citation TEXT NOT NULL,
            doc_title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            chunk_type TEXT NOT NULL,
            citation_label TEXT NOT NULL,
            position INTEGER NOT NULL,
            tags TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    # Vector table — sqlite-vec virtual table holding the embeddings.
    cur.execute(f"""
        CREATE VIRTUAL TABLE chunk_vectors USING vec0(
            embedding float[{EMBED_DIM}]
        )
    """)

    import struct
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
        cur.execute(
            """INSERT INTO chunks
               (id, file, doc_citation, doc_title, source_type, chunk_type,
                citation_label, position, tags, content)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                i,
                chunk["file"],
                chunk["doc_citation"],
                chunk["doc_title"],
                chunk["source_type"],
                chunk["chunk_type"],
                chunk["citation_label"],
                chunk["position"],
                json.dumps(chunk["tags"]),
                chunk["content"],
            ),
        )
        # Pack embedding as float32 blob for sqlite-vec.
        embedding_blob = struct.pack(f"{EMBED_DIM}f", *embedding)
        cur.execute(
            "INSERT INTO chunk_vectors(rowid, embedding) VALUES (?, ?)",
            (i, embedding_blob),
        )

    conn.commit()
    conn.close()
    print(f"indexed {len(chunks)} chunks")
    return len(chunks)


def search(query: str, tags: list[str] | None = None, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    """Filter-then-search: optional tag filter, then similarity on the filtered set."""
    if not DB_PATH.exists():
        print(f"error: no index at {DB_PATH}. Run with --rebuild first.", file=sys.stderr)
        sys.exit(2)

    print(f"embedding query: {query!r}")
    query_embedding = embed_query(query)

    import struct
    query_blob = struct.pack(f"{EMBED_DIM}f", *query_embedding)

    conn = _connect(DB_PATH)
    cur = conn.cursor()

    # First pass: tag filter if given. Returns ids of chunks matching any provided tag.
    if tags:
        filter_sql = " OR ".join(["chunks.tags LIKE ?"] * len(tags))
        filter_params = [f'%"{t}"%' for t in tags]
        cur.execute(
            f"SELECT id FROM chunks WHERE {filter_sql}",
            filter_params,
        )
        allowed_ids = {row[0] for row in cur.fetchall()}
        if not allowed_ids:
            print(f"no chunks match tag filter: {tags}")
            return []
        print(f"tag filter {tags} matched {len(allowed_ids)} chunks")
    else:
        allowed_ids = None

    # Second pass: vector similarity. sqlite-vec's KNN syntax.
    cur.execute(
        """
        SELECT rowid, distance
        FROM chunk_vectors
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
        """,
        (query_blob, top_k * 4 if allowed_ids else top_k),
    )
    ranked = cur.fetchall()

    # Filter the ranked results by allowed_ids and take top_k.
    results: list[dict[str, Any]] = []
    for rowid, distance in ranked:
        if allowed_ids is not None and rowid not in allowed_ids:
            continue
        cur.execute(
            """SELECT doc_citation, doc_title, source_type, chunk_type,
                      citation_label, tags, content
               FROM chunks WHERE id = ?""",
            (rowid,),
        )
        row = cur.fetchone()
        if row:
            results.append({
                "doc_citation": row[0],
                "doc_title": row[1],
                "source_type": row[2],
                "chunk_type": row[3],
                "citation_label": row[4],
                "tags": json.loads(row[5]),
                "content": row[6],
                "distance": distance,
            })
        if len(results) >= top_k:
            break

    conn.close()
    return results


# ─── CLI ────────────────────────────────────────────────────────────────


def _print_results(query: str, results: list[dict[str, Any]]) -> None:
    print()
    print(f"=== top {len(results)} results for: {query!r} ===")
    print()
    for i, r in enumerate(results, start=1):
        print(f"[{i}] distance={r['distance']:.4f}  {r['doc_citation']}  ({r['chunk_type']})")
        print(f"    {r['citation_label']}  tags={r['tags']}")
        content_preview = r["content"][:300] + ("..." if len(r["content"]) > 300 else "")
        # Indent content for readability.
        for line in content_preview.split("\n"):
            print(f"    {line}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else None)
    parser.add_argument("query", nargs="?", help="natural-language query")
    parser.add_argument("--tags", type=str, default="",
                        help="comma-separated applies_to tags to filter on (e.g. obsolete,reinvestigation)")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help=f"number of results to return (default {DEFAULT_TOP_K})")
    parser.add_argument("--rebuild", action="store_true",
                        help="rebuild the index from corpus/ (re-embeds all chunks)")
    args = parser.parse_args()

    # If rebuild requested, build then exit if no query provided.
    if args.rebuild:
        build_index(rebuild=True)
        if not args.query:
            return 0

    # If no index exists and no rebuild requested, build it (first-run convenience).
    if not DB_PATH.exists():
        print("no index found — building one (first-run only)...")
        build_index(rebuild=False)

    if not args.query:
        parser.print_help()
        return 2

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
    results = search(args.query, tags=tags, top_k=args.top_k)
    _print_results(args.query, results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
