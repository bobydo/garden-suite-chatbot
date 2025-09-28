#!/usr/bin/env python3
"""Peek at embeddings stored in Qdrant.

Shows a few points from a collection with:
- point id
- vector length (dimension)
- first N values
- select payload fields (url/source/title)

Usage examples:
  python database_tools/peek_embeddings.py --collection website_index --limit 3
  python database_tools/peek_embeddings.py --collection pdf_index --limit 2

Relies on Qdrant host/port and collection names from config.py
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple, Optional, Any, Dict

from qdrant_client import QdrantClient
# No extra HTTP model imports needed for simple scroll

# Ensure project root is on sys.path for `import config`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def extract_vector(record) -> Tuple[Optional[List[float]], Optional[str]]:
    """Return (vector, name) from a Qdrant Record supporting single or named vectors.

    - Single-vector collections expose `record.vector` as List[float].
    - Named-vector collections may expose `record.vector` as Dict[str, List[float]]
      or `record.vectors` depending on client version. We pick the first entry.
    """
    # Prefer attribute 'vector' when present
    vec = getattr(record, "vector", None)
    name = None

    if vec is None:
        # Some client versions use 'vectors' for named vectors
        vec = getattr(record, "vectors", None)

    if vec is None:
        return None, None

    if isinstance(vec, list):
        # Single vector
        return vec, None

    if isinstance(vec, dict):
        # Named vectors dict
        if not vec:
            return None, None
        name, arr = next(iter(vec.items()))
        return arr, name

    # Fallback: try to coerce unknown vector container types
    try:
        # Some SDKs wrap named vectors in a model with a .values or .vectors dict
        values = getattr(vec, "values", None) or getattr(vec, "vectors", None)
        if isinstance(values, dict) and values:
            name, arr = next(iter(values.items()))
            return arr, name
    except Exception:
        pass

    return None, None


def _get_meta_value(meta: Dict[str, Any], key: str) -> Optional[Any]:
    """Return a value from payload at top-level or inside nested 'metadata'."""
    if key in meta:
        return meta.get(key)
    nested = meta.get("metadata")
    if isinstance(nested, dict) and key in nested:
        return nested.get(key)
    return None


def main():
    parser = argparse.ArgumentParser(description="Peek embeddings from a Qdrant collection")
    parser.add_argument("--collection", default=config.WEBSITE_COLLECTION, help="Qdrant collection name")
    parser.add_argument("--host", default=getattr(config, "QDRANT_HOST", "localhost"), help="Qdrant host")
    parser.add_argument("--port", type=int, default=getattr(config, "QDRANT_PORT", 6333), help="Qdrant port")
    parser.add_argument("--limit", type=int, default=3, help="Number of points to show")
    parser.add_argument("--offset", default=None, help="Optional page offset (opaque)")
    parser.add_argument("--values", type=int, default=8, help="How many initial vector values to display")
    args = parser.parse_args()

    client = QdrantClient(host=args.host, port=args.port)

    try:
        records, next_offset = client.scroll(
            collection_name=args.collection,
            scroll_filter=None,
            limit=args.limit,
            with_payload=True,
            with_vectors=True,
            offset=args.offset,
        )
    except Exception as e:
        print(
            "Error: Unable to connect to Qdrant. "
            f"Tried http://{args.host}:{args.port}.\n"
            "- Is Qdrant running?\n"
            "- If using a different host/port, pass --host/--port or set env QDRANT_HOST/QDRANT_PORT.\n"
            f"Details: {e}"
        )
        return

    if not records:
        print("No records returned. Check that the collection exists and contains points.")
        return

    for i, rec in enumerate(records, 1):
        vec, name = extract_vector(rec)
        meta = rec.payload or {}
        # Pull from top-level or nested 'metadata'
        title = (
            _get_meta_value(meta, "title")
            or _get_meta_value(meta, "page_title")
            or ""
        )
        url = (
            _get_meta_value(meta, "url")
            or _get_meta_value(meta, "source")
            or _get_meta_value(meta, "source_url")
            or ""
        )

        if vec is None:
            print(f"[{i}] id={rec.id}  (no vector returned)  title={str(title)[:60]}  url={str(url)[:80]}")
            if not title and not url and meta:
                print(f"     payload_keys={list(meta.keys())}")
            continue

        dim = len(vec)
        sample = ", ".join(f"{x:.5f}" for x in vec[: args.values])
        vname = f" name={name}" if name else ""
        print(f"[{i}] id={rec.id}{vname}  dim={dim}  title={str(title)[:60]}")
        print(f"     url={str(url)[:120]}")
        if not title and not url and meta:
            print(f"     payload_keys={list(meta.keys())}")
        print(f"     head=[{sample}{'...' if dim > args.values else ''}]")

    if next_offset is not None:
        print(f"- Next offset available: {next_offset}")


if __name__ == "__main__":
    main()
