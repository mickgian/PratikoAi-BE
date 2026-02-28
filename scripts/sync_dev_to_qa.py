#!/usr/bin/env python3
"""Sync knowledge data from dev DB to QA DB (one-time alignment).

Copies knowledge_items, knowledge_chunks, regulatory_documents, and feed_status
from the dev database to QA so both environments have identical ingested content.
After this one-time sync, QA maintains itself via daily RSS ingestion + web scrapers.

Usage:
    # Default: dev (localhost:5432) -> QA (from env var QA_DATABASE_URL)
    python scripts/sync_dev_to_qa.py

    # Explicit connection strings
    python scripts/sync_dev_to_qa.py \
        --source "postgresql://aifinance:devpass@localhost:5432/aifinance" \
        --target "postgresql://aifinance:password@qa-host:5432/aifinance"

    # Dry run (show counts only, no writes)
    python scripts/sync_dev_to_qa.py --dry-run

    # Via SSH tunnel to QA (run in another terminal first):
    #   ssh -L 15432:localhost:5432 user@qa-server
    # Then:
    python scripts/sync_dev_to_qa.py \
        --target "postgresql://aifinance:password@localhost:15432/aifinance"
"""

import argparse
import json
import os
import sys
import time
from decimal import Decimal

from sqlalchemy import create_engine, text

# Default dev DB (local Docker, port 5432)
DEFAULT_SOURCE_URL = os.getenv(
    "DEV_DATABASE_URL",
    "postgresql://aifinance:devpass@localhost:5432/aifinance",  # pragma: allowlist secret
)
DEFAULT_TARGET_URL = os.getenv("QA_DATABASE_URL", "")


# Tables to sync, in dependency order (parents first).
# search_vector columns are auto-maintained by DB triggers on INSERT,
# so we exclude them from the copy — the trigger recreates them.
SYNC_TABLES = [
    {
        "name": "feed_status",
        "label": "RSS Feed Status",
        "skip_columns": {"search_vector"},
        "conflict_column": "feed_url",
        "conflict_action": "DO NOTHING",
    },
    {
        "name": "knowledge_items",
        "label": "Knowledge Items",
        "skip_columns": {"search_vector"},
        "conflict_column": "id",
        "conflict_action": "DO NOTHING",
    },
    {
        "name": "knowledge_chunks",
        "label": "Knowledge Chunks",
        "skip_columns": {"search_vector"},
        "conflict_column": "id",
        "conflict_action": "DO NOTHING",
    },
    {
        "name": "regulatory_documents",
        "label": "Regulatory Documents",
        "skip_columns": set(),
        "conflict_column": "id",
        "conflict_action": "DO NOTHING",
    },
]


def prepare_row_data(row_dict: dict) -> dict:
    """Convert row data to handle JSON and special types.

    Same pattern as seed_docker_db.py — handles dict/list -> JSON string,
    Decimal -> float, and preserves None values.
    """
    result = {}
    for key, value in row_dict.items():
        if value is None:
            result[key] = None
        elif isinstance(value, dict | list):
            result[key] = json.dumps(value)
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result


def get_table_columns(conn, table_name: str, skip_columns: set[str]) -> list[str]:
    """Get column names for a table, excluding skipped columns."""
    result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 0"))  # noqa: S608
    return [col for col in result.keys() if col not in skip_columns]


def count_rows(conn, table_name: str) -> int:
    """Count rows in a table."""
    return conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()  # noqa: S608


def sync_table(
    source_engine,
    target_engine,
    table_config: dict,
    *,
    dry_run: bool = False,
    batch_size: int = 500,
) -> dict:
    """Sync a single table from source to target DB.

    Uses ON CONFLICT DO NOTHING to safely merge data without overwriting
    existing records in QA. This means QA-specific state (e.g., feed health
    metrics, processing status) is preserved.

    Returns dict with sync stats.
    """
    table_name = table_config["name"]
    skip_columns = table_config["skip_columns"]
    conflict_col = table_config["conflict_column"]

    stats = {"table": table_name, "source_count": 0, "target_before": 0, "inserted": 0, "target_after": 0}

    with source_engine.connect() as source_conn:
        stats["source_count"] = count_rows(source_conn, table_name)
        columns = get_table_columns(source_conn, table_name, skip_columns)

        if stats["source_count"] == 0:
            print(f"  {table_config['label']}: source is empty, skipping")
            return stats

        # Fetch all source rows
        cols_select = ", ".join([f'"{col}"' for col in columns])
        rows = source_conn.execute(text(f"SELECT {cols_select} FROM {table_name}")).fetchall()  # noqa: S608

    with target_engine.connect() as target_conn:
        stats["target_before"] = count_rows(target_conn, table_name)

        if dry_run:
            print(
                f"  {table_config['label']}: "
                f"source={stats['source_count']}, "
                f"target={stats['target_before']} (dry run, no changes)"
            )
            return stats

        # Build INSERT ... ON CONFLICT DO NOTHING
        cols_str = ", ".join([f'"{col}"' for col in columns])
        placeholders = ", ".join([f":{col}" for col in columns])
        insert_sql = (
            f"INSERT INTO {table_name} ({cols_str}) "  # noqa: S608
            f"VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_col}) {table_config['conflict_action']}"
        )

        inserted = 0
        for i, row in enumerate(rows):
            row_dict = prepare_row_data(dict(zip(columns, row, strict=False)))
            result = target_conn.execute(text(insert_sql), row_dict)
            if result.rowcount > 0:
                inserted += 1

            # Progress indicator for large tables
            if (i + 1) % batch_size == 0:
                target_conn.commit()
                print(f"    ... processed {i + 1}/{len(rows)} rows ({inserted} new)")

        target_conn.commit()
        stats["inserted"] = inserted
        stats["target_after"] = count_rows(target_conn, table_name)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Sync knowledge data from dev DB to QA DB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE_URL,
        help="Source (dev) database URL (default: DEV_DATABASE_URL env var or localhost:5432)",
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET_URL,
        help="Target (QA) database URL (default: QA_DATABASE_URL env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show row counts only, do not write to target",
    )
    args = parser.parse_args()

    if not args.target:
        print(
            "Error: target DB URL required. Use --target or set QA_DATABASE_URL env var.\n"
            "\n"
            "Example with SSH tunnel:\n"
            "  1. Open tunnel: ssh -L 15432:localhost:5432 user@qa-server\n"
            '  2. Run sync:  python scripts/sync_dev_to_qa.py --target "postgresql://aifinance:pass@localhost:15432/aifinance"\n',
            file=sys.stderr,
        )
        sys.exit(1)

    # Mask password in display
    def mask_url(url: str) -> str:
        if "://" in url and "@" in url:
            pre = url.split("://")[0] + "://"
            post = url.split("@")[1]
            return f"{pre}***@{post}"
        return url

    print("=" * 60)
    print("PratikoAI Dev -> QA Knowledge Data Sync")
    print("=" * 60)
    print(f"Source: {mask_url(args.source)}")
    print(f"Target: {mask_url(args.target)}")
    if args.dry_run:
        print("Mode:   DRY RUN (no writes)")
    print()

    source_engine = create_engine(args.source)
    target_engine = create_engine(args.target)

    # Verify connectivity
    try:
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Source DB: connected")
    except Exception as e:
        print(f"Error: cannot connect to source DB: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Target DB: connected")
    except Exception as e:
        print(f"Error: cannot connect to target DB: {e}", file=sys.stderr)
        sys.exit(1)

    print()

    all_stats = []
    start_time = time.time()

    for table_config in SYNC_TABLES:
        print(f"Syncing {table_config['label']}...")
        stats = sync_table(
            source_engine,
            target_engine,
            table_config,
            dry_run=args.dry_run,
        )
        all_stats.append(stats)
        print(
            f"  Done: {stats['inserted']} new rows inserted "
            f"(source={stats['source_count']}, "
            f"target: {stats['target_before']} -> {stats['target_after']})"
        )
        print()

    elapsed = time.time() - start_time

    # Summary
    print("=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    print(f"{'Table':<30} {'Source':>8} {'Before':>8} {'New':>8} {'After':>8}")
    print("-" * 60)
    for s in all_stats:
        print(
            f"{s['table']:<30} {s['source_count']:>8} "
            f"{s['target_before']:>8} {s['inserted']:>8} {s['target_after']:>8}"
        )
    print("-" * 60)
    total_inserted = sum(s["inserted"] for s in all_stats)
    print(f"{'Total new rows:':<30} {' ':>8} {' ':>8} {total_inserted:>8}")
    print(f"\nCompleted in {elapsed:.1f}s")

    source_engine.dispose()
    target_engine.dispose()

    if total_inserted > 0:
        print("\nQA database aligned with dev. Daily RSS ingestion and web scrapers will keep QA updated from here.")
    else:
        print("\nQA database already aligned — no new data to sync.")


if __name__ == "__main__":
    main()
