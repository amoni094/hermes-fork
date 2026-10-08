#!/usr/bin/env python3
"""
hindsight-reembed.py — Batch re-embed all NULL-embedding rows in Hindsight DB
using OpenAI text-embedding-3-small (1536d).

Safe to run while the daemon is running — only touches rows with NULL embeddings.
Uses psycopg2 to connect directly to the pg0 postgres instance.

Usage:
  python3 hindsight-reembed.py [--batch-size 100] [--dry-run]
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

# Load OPENAI_API_KEY from .hermes/.env if not in environment
def load_env():
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists() and not os.environ.get("OPENAI_API_KEY"):
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY=") and "=" in line:
                os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip()
                break

load_env()

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2
    import psycopg2.extras

try:
    import openai
except ImportError:
    print("Installing openai...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "-q"])
    import openai

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMS = 1536
PG_CONN = "host=127.0.0.1 port=5433 dbname=hindsight user=hindsight password=hindsight"


def get_embeddings(texts: list[str], client) -> list[list[float]]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
        dimensions=EMBED_DIMS,
    )
    return [d.embedding for d in sorted(response.data, key=lambda x: x.index)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)
    conn = psycopg2.connect(PG_CONN)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM memory_units WHERE embedding IS NULL")
        row = cur.fetchone()
        total_pending = row[0] if row else 0

    print(f"Pending rows: {total_pending}")
    if args.dry_run:
        print("Dry run — exiting")
        return

    processed = 0
    errors = 0
    start = time.time()

    while True:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, text FROM memory_units WHERE embedding IS NULL LIMIT %s",
                (args.batch_size,),
            )
            rows = cur.fetchall()

        if not rows:
            break

        ids = [r["id"] for r in rows]
        texts = [r["text"] or "" for r in rows]

        try:
            embeddings = get_embeddings(texts, client)
        except Exception as e:
            print(f"  ERROR embedding batch: {e}")
            errors += 1
            time.sleep(5)
            continue

        with conn.cursor() as cur:
            for row_id, emb in zip(ids, embeddings):
                vec_str = "[" + ",".join(str(x) for x in emb) + "]"
                cur.execute(
                    "UPDATE memory_units SET embedding = %s::vector WHERE id = %s",
                    (vec_str, row_id),
                )
        conn.commit()

        processed += len(rows)
        elapsed = time.time() - start
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = total_pending - processed
        eta = remaining / rate if rate > 0 else 0
        print(
            f"  {processed}/{total_pending} ({100*processed/total_pending:.1f}%) "
            f"| {rate:.1f} rows/s | ETA {eta/60:.1f}min",
            flush=True,
        )

    conn.close()
    elapsed = time.time() - start
    print(f"\nDone. {processed} rows embedded in {elapsed:.1f}s. Errors: {errors}")


if __name__ == "__main__":
    main()
