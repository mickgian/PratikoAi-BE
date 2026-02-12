#!/usr/bin/env python3
"""Data Quality Repair Script (DEV-258).

Repairs existing data quality issues identified by audit_data_quality.py:
  A. Broken hyphenation in chunks and items
  B. Incorrect token counts (word count instead of char//4)
  C. Duplicate documents (by source_url)
  D. Missing embeddings
  E. Navigation-contaminated chunks

Usage:
    # Dry run (default) — reports what would change
    python scripts/repair_data_quality.py --dry-run

    # Execute repairs
    python scripts/repair_data_quality.py --execute

    # Run a single step
    python scripts/repair_data_quality.py --execute --step hyphenation
    python scripts/repair_data_quality.py --execute --step tokens
    python scripts/repair_data_quality.py --execute --step dedup
    python scripts/repair_data_quality.py --execute --step embeddings
    python scripts/repair_data_quality.py --execute --step navigation

Environment variables:
    DATABASE_URL: PostgreSQL connection string (or uses docker default)
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

BATCH_SIZE = 500


async def get_db_session() -> AsyncSession:
    """Create async database session."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aifinance:devpass@localhost:5433/aifinance",  # pragma: allowlist secret
    )
    # Normalize sync driver URL (set for alembic) to async driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


def print_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


# -------------------------------------------------------------------------
# Step A: Fix broken hyphenation
# -------------------------------------------------------------------------
async def repair_hyphenation(db: AsyncSession, dry_run: bool) -> None:
    """Repair broken hyphenation in chunks and items."""
    from app.core.text.hyphenation import repair_broken_hyphenation

    print_section("Step A: Repair broken hyphenation")

    # Count affected chunks
    result = await db.execute(
        text("SELECT COUNT(*) FROM knowledge_chunks WHERE chunk_text ~ '[a-zàèéìòù]- [a-zàèéìòù]'")
    )
    chunk_count = result.scalar() or 0
    print(f"  Affected chunks: {chunk_count}")

    # Count affected items
    result = await db.execute(text("SELECT COUNT(*) FROM knowledge_items WHERE content ~ '[a-zàèéìòù]- [a-zàèéìòù]'"))
    item_count = result.scalar() or 0
    print(f"  Affected items:  {item_count}")

    if dry_run:
        print("  [DRY RUN] No changes made.")
        return

    # Repair chunks in batches
    repaired_chunks = 0
    while True:
        result = await db.execute(
            text(
                "SELECT id, chunk_text FROM knowledge_chunks "
                "WHERE chunk_text ~ '[a-zàèéìòù]- [a-zàèéìòù]' "
                "ORDER BY id LIMIT :limit"
            ),
            {"limit": BATCH_SIZE},
        )
        rows = result.fetchall()
        if not rows:
            break

        for row in rows:
            chunk_id, chunk_text = row[0], row[1]
            repaired = repair_broken_hyphenation(chunk_text)
            if repaired != chunk_text:
                await db.execute(
                    text("UPDATE knowledge_chunks SET chunk_text = :text WHERE id = :id"),
                    {"text": repaired, "id": chunk_id},
                )
                repaired_chunks += 1

        await db.commit()
        print(f"    Repaired batch of {len(rows)} chunks...")

    # Repair items in batches
    repaired_items = 0
    while True:
        result = await db.execute(
            text(
                "SELECT id, content FROM knowledge_items "
                "WHERE content ~ '[a-zàèéìòù]- [a-zàèéìòù]' "
                "ORDER BY id LIMIT :limit"
            ),
            {"limit": BATCH_SIZE},
        )
        rows = result.fetchall()
        if not rows:
            break

        for row in rows:
            item_id, content = row[0], row[1]
            repaired = repair_broken_hyphenation(content)
            if repaired != content:
                await db.execute(
                    text("UPDATE knowledge_items SET content = :text WHERE id = :id"),
                    {"text": repaired, "id": item_id},
                )
                repaired_items += 1

        await db.commit()
        print(f"    Repaired batch of {len(rows)} items...")

    print(f"  Repaired {repaired_chunks} chunks, {repaired_items} items.")


# -------------------------------------------------------------------------
# Step B: Recalculate token counts
# -------------------------------------------------------------------------
async def repair_token_counts(db: AsyncSession, dry_run: bool) -> None:
    """Recalculate token counts using len(text)//4 instead of word count."""
    print_section("Step B: Recalculate token counts")

    result = await db.execute(text("SELECT COUNT(*) FROM knowledge_chunks"))
    total = result.scalar() or 0
    print(f"  Total chunks to check: {total}")

    if dry_run:
        # Sample to show the problem
        result = await db.execute(
            text(
                "SELECT id, token_count, LENGTH(chunk_text) / 4 as expected "
                "FROM knowledge_chunks "
                "WHERE token_count != LENGTH(chunk_text) / 4 "
                "LIMIT 5"
            )
        )
        samples = result.fetchall()
        mismatch_result = await db.execute(
            text("SELECT COUNT(*) FROM knowledge_chunks WHERE token_count != LENGTH(chunk_text) / 4")
        )
        mismatch_count = mismatch_result.scalar() or 0
        print(f"  Chunks with wrong token_count: {mismatch_count}")
        if samples:
            print("  Samples (id, current, expected):")
            for row in samples:
                print(f"    id={row[0]}: current={row[1]}, expected={row[2]}")
        print("  [DRY RUN] No changes made.")
        return

    # Batch update using SQL (much faster than Python loop)
    result = await db.execute(
        text(
            "UPDATE knowledge_chunks "
            "SET token_count = LENGTH(chunk_text) / 4 "
            "WHERE token_count != LENGTH(chunk_text) / 4"
        )
    )
    updated = result.rowcount
    await db.commit()
    print(f"  Updated {updated} chunks.")


# -------------------------------------------------------------------------
# Step C: Deduplicate documents
# -------------------------------------------------------------------------
async def repair_dedup(db: AsyncSession, dry_run: bool) -> None:
    """Remove duplicate documents by source_url."""
    print_section("Step C: Deduplicate documents (by source_url)")

    result = await db.execute(
        text(
            "SELECT source_url, COUNT(*) as cnt "
            "FROM knowledge_items "
            "WHERE source_url IS NOT NULL AND status = 'active' "
            "GROUP BY source_url "
            "HAVING COUNT(*) > 1 "
            "ORDER BY cnt DESC"
        )
    )
    dupe_groups = result.fetchall()
    print(f"  Duplicate URL groups: {len(dupe_groups)}")

    total_to_delete = 0

    for url, count in dupe_groups:
        print(f"    {url}: {count} copies")

        # Keep the one with best text_quality, or most recent
        result = await db.execute(
            text(
                "SELECT id, title, text_quality, created_at "
                "FROM knowledge_items "
                "WHERE source_url = :url AND status = 'active' "
                "ORDER BY COALESCE(text_quality, 0) DESC, created_at DESC"
            ),
            {"url": url},
        )
        rows = result.fetchall()

        keep_id = rows[0][0]
        delete_ids = [row[0] for row in rows[1:]]
        total_to_delete += len(delete_ids)

        print(f"      Keep: id={keep_id} (quality={rows[0][2]}, created={rows[0][3]})")
        for row in rows[1:]:
            print(f"      Delete: id={row[0]} (quality={row[2]}, created={row[3]})")

        if not dry_run:
            # Delete chunks first (FK safety)
            for del_id in delete_ids:
                await db.execute(
                    text("DELETE FROM knowledge_chunks WHERE knowledge_item_id = :id"),
                    {"id": del_id},
                )
            # Delete items
            for del_id in delete_ids:
                await db.execute(
                    text("DELETE FROM knowledge_items WHERE id = :id"),
                    {"id": del_id},
                )
            await db.commit()

    if dry_run:
        print(f"  [DRY RUN] Would delete {total_to_delete} duplicate items.")
    else:
        print(f"  Deleted {total_to_delete} duplicate items.")


# -------------------------------------------------------------------------
# Step D: Re-embed missing items/chunks
# -------------------------------------------------------------------------
async def repair_embeddings(db: AsyncSession, dry_run: bool) -> None:
    """Re-embed items and chunks with missing embeddings."""
    from app.core.embed import generate_embedding, generate_embeddings_batch

    print_section("Step D: Re-embed missing items/chunks")

    # Count missing
    result = await db.execute(
        text("SELECT COUNT(*) FROM knowledge_items WHERE embedding IS NULL AND status = 'active'")
    )
    items_missing = result.scalar() or 0

    result = await db.execute(text("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NULL"))
    chunks_missing = result.scalar() or 0

    print(f"  Items missing embeddings:  {items_missing}")
    print(f"  Chunks missing embeddings: {chunks_missing}")

    if dry_run:
        batches_needed = (items_missing + chunks_missing + 19) // 20
        print(f"  Estimated API calls: {batches_needed}")
        print("  [DRY RUN] No changes made.")
        return

    # Re-embed items
    embedded_items = 0
    result = await db.execute(
        text("SELECT id, content FROM knowledge_items WHERE embedding IS NULL AND status = 'active' ORDER BY id")
    )
    rows = result.fetchall()

    for i in range(0, len(rows), 20):
        batch = rows[i : i + 20]
        texts = [row[1] if row[1] else "" for row in batch]
        embeddings = await generate_embeddings_batch(texts, batch_size=20)

        for (item_id, _), emb in zip(batch, embeddings, strict=False):
            if emb is not None:
                await db.execute(
                    text("UPDATE knowledge_items SET embedding = :emb WHERE id = :id"),
                    {"emb": str(emb), "id": item_id},
                )
                embedded_items += 1

        await db.commit()
        print(f"    Embedded {min(i + 20, len(rows))}/{len(rows)} items...")
        await asyncio.sleep(0.5)

    # Re-embed chunks
    embedded_chunks = 0
    result = await db.execute(text("SELECT id, chunk_text FROM knowledge_chunks WHERE embedding IS NULL ORDER BY id"))
    rows = result.fetchall()

    for i in range(0, len(rows), 20):
        batch = rows[i : i + 20]
        texts = [row[1] if row[1] else "" for row in batch]
        embeddings = await generate_embeddings_batch(texts, batch_size=20)

        for (chunk_id, _), emb in zip(batch, embeddings, strict=False):
            if emb is not None:
                await db.execute(
                    text("UPDATE knowledge_chunks SET embedding = :emb WHERE id = :id"),
                    {"emb": str(emb), "id": chunk_id},
                )
                embedded_chunks += 1

        await db.commit()
        print(f"    Embedded {min(i + 20, len(rows))}/{len(rows)} chunks...")
        await asyncio.sleep(0.5)

    print(f"  Embedded {embedded_items} items, {embedded_chunks} chunks.")


# -------------------------------------------------------------------------
# Step E: Delete navigation-contaminated chunks
# -------------------------------------------------------------------------
async def repair_navigation(db: AsyncSession, dry_run: bool) -> None:
    """Delete chunks contaminated with navigation boilerplate text."""
    from app.core.text.clean import NAVIGATION_PATTERNS

    print_section("Step E: Delete navigation-contaminated chunks")

    # Build a SQL condition that counts how many patterns match per chunk
    # Use LOWER() + LIKE for each pattern
    like_conditions = [f"LOWER(chunk_text) LIKE '%{p}%'" for p in NAVIGATION_PATTERNS]
    count_expr = " + ".join(f"CASE WHEN {c} THEN 1 ELSE 0 END" for c in like_conditions)
    any_condition = " OR ".join(like_conditions)

    # Count affected chunks (2+ patterns, or 1 pattern and short)
    count_sql = (
        f"SELECT COUNT(*) FROM knowledge_chunks "
        f"WHERE ({any_condition}) "
        f"AND (({count_expr}) >= 2 OR (({count_expr}) >= 1 AND LENGTH(chunk_text) < 300))"
    )
    result = await db.execute(text(count_sql))
    affected = result.scalar() or 0
    print(f"  Navigation-contaminated chunks: {affected}")

    if dry_run:
        # Show samples
        sample_sql = (
            f"SELECT id, LEFT(chunk_text, 150), ({count_expr}) as nav_count, LENGTH(chunk_text) as len "
            f"FROM knowledge_chunks "
            f"WHERE ({any_condition}) "
            f"AND (({count_expr}) >= 2 OR (({count_expr}) >= 1 AND LENGTH(chunk_text) < 300)) "
            f"LIMIT 5"
        )
        result = await db.execute(text(sample_sql))
        samples = result.fetchall()
        if samples:
            print("  Samples:")
            for row in samples:
                print(f"    id={row[0]} nav_count={row[2]} len={row[3]}")
                print(f"      text: {row[1][:120]}...")
        print("  [DRY RUN] No changes made.")
        return

    # Delete in batches
    total_deleted = 0
    while True:
        select_sql = (
            f"SELECT id FROM knowledge_chunks "
            f"WHERE ({any_condition}) "
            f"AND (({count_expr}) >= 2 OR (({count_expr}) >= 1 AND LENGTH(chunk_text) < 300)) "
            f"LIMIT :limit"
        )
        result = await db.execute(text(select_sql), {"limit": BATCH_SIZE})
        rows = result.fetchall()
        if not rows:
            break

        ids = [row[0] for row in rows]
        await db.execute(
            text("DELETE FROM knowledge_chunks WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
        await db.commit()
        total_deleted += len(ids)
        print(f"    Deleted batch of {len(ids)} chunks...")

    print(f"  Deleted {total_deleted} navigation-contaminated chunks.")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
STEPS = {
    "hyphenation": repair_hyphenation,
    "tokens": repair_token_counts,
    "dedup": repair_dedup,
    "embeddings": repair_embeddings,
    "navigation": repair_navigation,
}


async def run_repairs(dry_run: bool, step: str) -> None:
    """Run repair operations."""
    db = await get_db_session()

    try:
        if step == "all":
            steps_to_run = list(STEPS.values())
        else:
            if step not in STEPS:
                print(f"Unknown step: {step}. Choose from: {', '.join(STEPS.keys())}, all")
                return
            steps_to_run = [STEPS[step]]

        start = time.time()
        for repair_fn in steps_to_run:
            await repair_fn(db, dry_run)
        elapsed = time.time() - start

        print_section("COMPLETE")
        mode = "DRY RUN" if dry_run else "EXECUTED"
        print(f"  Mode: {mode}")
        print(f"  Time: {elapsed:.1f}s")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="PratikoAI Data Quality Repair (DEV-258)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report what would change (no modifications)")
    mode.add_argument("--execute", action="store_true", help="Apply repairs to the database")
    parser.add_argument(
        "--step",
        default="all",
        choices=["hyphenation", "tokens", "dedup", "embeddings", "navigation", "all"],
        help="Run a specific repair step (default: all)",
    )
    args = parser.parse_args()

    dry_run = args.dry_run
    print("=" * 70)
    print("  PratikoAI Data Quality Repair (DEV-258)")
    print(f"  Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"  Step: {args.step}")
    print("=" * 70)

    asyncio.run(run_repairs(dry_run=dry_run, step=args.step))


if __name__ == "__main__":
    main()
