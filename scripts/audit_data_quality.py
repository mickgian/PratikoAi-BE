#!/usr/bin/env python3
"""Data Quality Diagnostic Script for DATA_CLEANING_AUDIT.md verification.

Runs SQL queries against the knowledge base to confirm or refute audit findings.
Produces a summary report with counts and sample data.

Usage:
    # Full diagnostic (default database)
    python scripts/audit_data_quality.py

    # With custom database URL
    DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" python scripts/audit_data_quality.py

    # Limit samples per query
    python scripts/audit_data_quality.py --samples 3

Environment variables:
    DATABASE_URL: PostgreSQL connection string (or uses docker default)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def get_db_session() -> AsyncSession:
    """Create async database session."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aifinance:devpass@localhost:5433/aifinance",  # pragma: allowlist secret
    )
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_finding(label: str, count: int, status: str = "") -> None:
    """Print a finding line."""
    icon = "CONFIRMED" if count > 0 else "NOT FOUND"
    if status:
        icon = status
    print(f"  [{icon:>12}] {label}: {count}")


async def run_diagnostics(samples: int = 5) -> None:
    """Run all diagnostic queries."""
    db = await get_db_session()

    try:
        # =====================================================================
        print_section("1. KNOWLEDGE BASE OVERVIEW")
        # =====================================================================

        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_items"))
        total_items = result.scalar() or 0
        print(f"  Total knowledge_items: {total_items}")

        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_chunks"))
        total_chunks = result.scalar() or 0
        print(f"  Total knowledge_chunks: {total_chunks}")

        result = await db.execute(
            text("SELECT source, COUNT(*) as cnt FROM knowledge_items GROUP BY source ORDER BY cnt DESC")
        )
        rows = result.fetchall()
        print("\n  Documents by source:")
        for row in rows:
            print(f"    {row[0]:45s} {row[1]:>5d}")

        result = await db.execute(
            text(
                "SELECT extraction_method, COUNT(*) as cnt FROM knowledge_items "
                "GROUP BY extraction_method ORDER BY cnt DESC"
            )
        )
        rows = result.fetchall()
        print("\n  Documents by extraction method:")
        for row in rows:
            print(f"    {str(row[0] or 'NULL'):30s} {row[1]:>5d}")

        # =====================================================================
        print_section("2. DUPLICATE DOCUMENTS (Finding E.2)")
        # =====================================================================

        # URL-based duplicates (same URL stored multiple times)
        result = await db.execute(
            text(
                "SELECT source_url, COUNT(*) as cnt "
                "FROM knowledge_items "
                "WHERE source_url IS NOT NULL "
                "GROUP BY source_url HAVING COUNT(*) > 1 "
                "ORDER BY cnt DESC LIMIT :limit"
            ),
            {"limit": samples},
        )
        url_dupes = result.fetchall()
        print_finding("Exact URL duplicates (same URL, multiple records)", len(url_dupes))
        for row in url_dupes[:samples]:
            print(f"    URL: {row[0][:80]}... ({row[1]} copies)")

        # Content-based near-duplicates (same title, different URL)
        result = await db.execute(
            text(
                "SELECT title, COUNT(*) as cnt, "
                "array_agg(DISTINCT source_url) as urls "
                "FROM knowledge_items "
                "WHERE title IS NOT NULL AND title != '' "
                "GROUP BY title HAVING COUNT(*) > 1 "
                "ORDER BY cnt DESC LIMIT :limit"
            ),
            {"limit": samples},
        )
        title_dupes = result.fetchall()
        print_finding("Same title, different URLs (potential content dupes)", len(title_dupes))
        for row in title_dupes[:samples]:
            print(f"    Title: {row[0][:70]}... ({row[1]} copies)")

        # =====================================================================
        print_section("3. NAVIGATION TEXT IN CHUNKS (Finding E.6)")
        # =====================================================================

        nav_patterns = [
            "vai al menu",
            "vai al contenuto",
            "cookie policy",
            "accedi a myinps",
            "cedolino pensione",
            "mappa del sito",
            "privacy policy",
            "seguici su",
            "menu principale",
            "skip to content",
            "area riservata",
        ]

        total_nav = 0
        for pattern in nav_patterns:
            result = await db.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE LOWER(chunk_text) LIKE :pattern"),
                {"pattern": f"%{pattern}%"},
            )
            count = result.scalar() or 0
            if count > 0:
                total_nav += count
                print(f"    '{pattern}': {count} chunks")

        print_finding("Chunks containing navigation text", total_nav)

        if total_nav > 0:
            # Show a sample
            result = await db.execute(
                text(
                    "SELECT LEFT(chunk_text, 200), document_title, source_url "
                    "FROM knowledge_chunks "
                    "WHERE LOWER(chunk_text) LIKE '%vai al menu%' "
                    "   OR LOWER(chunk_text) LIKE '%cookie policy%' "
                    "LIMIT :limit"
                ),
                {"limit": samples},
            )
            nav_samples = result.fetchall()
            print("\n  Sample chunks with navigation text:")
            for row in nav_samples:
                print(f"    Doc: {row[1]}")
                print(f"    Text: {row[0][:150]}...")
                print()

        # =====================================================================
        print_section("4. HTML ARTIFACTS IN CONTENT (Findings E.5)")
        # =====================================================================

        html_patterns = [
            ("<p>", "HTML <p> tags"),
            ("<strong>", "HTML <strong> tags"),
            ("<a ", "HTML <a> links"),
            ("&amp;", "HTML &amp; entities"),
            ("&quot;", "HTML &quot; entities"),
            ("&#8217;", "HTML &#8217; entities"),
            ("&agrave;", "HTML &agrave; entities"),
            ("&egrave;", "HTML &egrave; entities"),
        ]

        for pattern, label in html_patterns:
            # Check in knowledge_items.content
            result = await db.execute(
                text("SELECT COUNT(*) FROM knowledge_items WHERE content LIKE :pattern"), {"pattern": f"%{pattern}%"}
            )
            items_count = result.scalar() or 0

            # Check in knowledge_chunks.chunk_text
            result = await db.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE chunk_text LIKE :pattern"),
                {"pattern": f"%{pattern}%"},
            )
            chunks_count = result.scalar() or 0

            if items_count > 0 or chunks_count > 0:
                print(f"    {label}: {items_count} items, {chunks_count} chunks")

        # Check RSS summary fallback specifically
        result = await db.execute(
            text("SELECT COUNT(*) FROM knowledge_items WHERE extraction_method = 'rss_summary_fallback'")
        )
        rss_fallback_count = result.scalar() or 0
        print_finding("Documents using RSS summary fallback", rss_fallback_count)

        if rss_fallback_count > 0:
            result = await db.execute(
                text(
                    "SELECT title, LEFT(content, 200) "
                    "FROM knowledge_items "
                    "WHERE extraction_method = 'rss_summary_fallback' "
                    "LIMIT :limit"
                ),
                {"limit": samples},
            )
            rss_samples = result.fetchall()
            print("\n  Sample RSS summary fallback content:")
            for row in rss_samples:
                print(f"    Title: {row[0]}")
                print(f"    Content: {row[1][:150]}...")
                has_html = any(tag in (row[1] or "") for tag in ["<p>", "<strong>", "<a ", "&amp;"])
                print(f"    Contains HTML: {'YES' if has_html else 'No'}")
                print()

        # =====================================================================
        print_section("5. BROKEN HYPHENATION IN CHUNKS (Finding E.1)")
        # =====================================================================

        # Pattern: word fragment + hyphen + space (PDF line-break artifact)
        result = await db.execute(
            text("SELECT COUNT(*) FROM knowledge_chunks WHERE chunk_text ~ '[a-zàèéìòù]- [a-zàèéìòù]'")
        )
        hyphen_break_count = result.scalar() or 0
        print_finding("Chunks with broken hyphenation (word- fragment)", hyphen_break_count)

        if hyphen_break_count > 0:
            result = await db.execute(
                text(
                    "SELECT document_title, "
                    "  substring(chunk_text from '[A-Za-zÀ-ÿ]{2,}- [A-Za-zÀ-ÿ]{2,}') as broken_word, "
                    "  source_url "
                    "FROM knowledge_chunks "
                    "WHERE chunk_text ~ '[a-zàèéìòù]- [a-zàèéìòù]' "
                    "LIMIT :limit"
                ),
                {"limit": samples},
            )
            hyph_samples = result.fetchall()
            print("\n  Sample broken words:")
            for row in hyph_samples:
                print(f"    Doc: {row[0]}")
                print(f"    Broken: '{row[1]}'")
                print()

        # =====================================================================
        print_section("6. CHUNK SIZE DISTRIBUTION (Finding E.9)")
        # =====================================================================

        result = await db.execute(
            text(
                "SELECT "
                "  MIN(token_count) as min_tokens, "
                "  MAX(token_count) as max_tokens, "
                "  AVG(token_count)::int as avg_tokens, "
                "  percentile_cont(0.5) WITHIN GROUP (ORDER BY token_count)::int as median_tokens, "
                "  percentile_cont(0.95) WITHIN GROUP (ORDER BY token_count)::int as p95_tokens "
                "FROM knowledge_chunks"
            )
        )
        row = result.fetchone()
        if row:
            print("  Token count distribution:")
            print(f"    Min:    {row[0]}")
            print(f"    Max:    {row[1]}")
            print(f"    Avg:    {row[2]}")
            print(f"    Median: {row[3]}")
            print(f"    P95:    {row[4]}")

            config_tokens = 900
            hardcoded_tokens = 512
            over_512 = 0
            over_900 = 0

            result = await db.execute(
                text(
                    "SELECT "
                    "  SUM(CASE WHEN token_count > 512 THEN 1 ELSE 0 END) as over_512, "
                    "  SUM(CASE WHEN token_count > 900 THEN 1 ELSE 0 END) as over_900 "
                    "FROM knowledge_chunks"
                )
            )
            size_row = result.fetchone()
            if size_row:
                print(f"    Chunks > 512 tokens (hardcoded limit): {size_row[0] or 0}")
                print(f"    Chunks > 900 tokens (config limit):    {size_row[1] or 0}")
                print("    NOTE: CHUNK_TOKENS=900 in config, but max_tokens=512 hardcoded in ingestion")

        # =====================================================================
        print_section("7. QUALITY SCORES & JUNK CHUNKS (Quality Gates)")
        # =====================================================================

        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_chunks WHERE junk = TRUE"))
        junk_stored = result.scalar() or 0

        result = await db.execute(
            text("SELECT COUNT(*) FROM knowledge_chunks WHERE quality_score IS NOT NULL AND quality_score < 0.5")
        )
        low_quality = result.scalar() or 0

        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_chunks WHERE quality_score IS NULL"))
        null_quality = result.scalar() or 0

        print_finding("Chunks flagged as junk (stored despite JUNK_DROP_CHUNK)", junk_stored)
        print_finding("Low quality chunks (quality_score < 0.5)", low_quality)
        print_finding("Chunks with NULL quality_score", null_quality)

        # =====================================================================
        print_section("8. MISSING EMBEDDINGS (Finding E.9)")
        # =====================================================================

        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_items WHERE embedding IS NULL"))
        items_no_embed = result.scalar() or 0

        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NULL"))
        chunks_no_embed = result.scalar() or 0

        print_finding("Knowledge items without embedding", items_no_embed)
        print_finding("Knowledge chunks without embedding", chunks_no_embed)

        # =====================================================================
        print_section("9. STALENESS / SUPERSEDED DOCUMENTS (Finding E.3)")
        # =====================================================================

        result = await db.execute(
            text("SELECT status, COUNT(*) FROM knowledge_items GROUP BY status ORDER BY COUNT(*) DESC")
        )
        rows = result.fetchall()
        print("  Document status distribution:")
        for row in rows:
            print(f"    {str(row[0] or 'NULL'):20s} {row[1]:>5d}")

        # Check for old documents still active
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_items "
                "WHERE status = 'active' "
                "AND created_at < NOW() - INTERVAL '365 days'"
            )
        )
        old_active = result.scalar() or 0
        print_finding("Active documents older than 1 year", old_active)

        # Check for documents without publication_date
        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_items WHERE publication_date IS NULL"))
        no_pub_date = result.scalar() or 0
        print_finding("Documents without publication_date", no_pub_date)

        # =====================================================================
        print_section("10. TEXT QUALITY FOR HTML DOCUMENTS (Backfill check)")
        # =====================================================================

        result = await db.execute(text("SELECT COUNT(*) FROM knowledge_items WHERE text_quality IS NULL"))
        null_tq = result.scalar() or 0
        print_finding("Documents with NULL text_quality", null_tq)

        result = await db.execute(
            text(
                "SELECT extraction_method, COUNT(*), "
                "  AVG(text_quality)::numeric(4,2) as avg_quality "
                "FROM knowledge_items "
                "WHERE text_quality IS NOT NULL "
                "GROUP BY extraction_method "
                "ORDER BY avg_quality"
            )
        )
        rows = result.fetchall()
        if rows:
            print("\n  Average quality by extraction method:")
            for row in rows:
                print(f"    {str(row[0] or 'NULL'):25s} count={row[1]:>4d}  avg_quality={row[2]}")

        # =====================================================================
        print_section("11. LEGAL PREAMBLE / BOILERPLATE (Finding E.7)")
        # =====================================================================

        preamble_patterns = [
            ("IL DIRETTORE DELL'AGENZIA", "Agenzia Entrate preamble"),
            ("IL DIRETTORE GENERALE", "Generic director preamble"),
            ("In base alle attribuzioni", "Attribution clause"),
            ("Gazzetta Ufficiale della Repubblica", "GU running header"),
            ("Pagina 1 di", "Page number artifact"),
        ]

        for pattern, label in preamble_patterns:
            result = await db.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE chunk_text LIKE :pattern"),
                {"pattern": f"%{pattern}%"},
            )
            count = result.scalar() or 0
            if count > 0:
                print(f"    {label}: {count} chunks")

        # =====================================================================
        print_section("12. UNICODE NORMALIZATION CHECK (Finding E.8)")
        # =====================================================================

        # Check for common NFD sequences (combining accents)
        # e + combining grave = è in NFD
        result = await db.execute(
            text(
                r"SELECT COUNT(*) FROM knowledge_chunks "
                r"WHERE chunk_text ~ E'[\u0300-\u036f]'"
            )
        )
        nfd_count = result.scalar() or 0
        print_finding("Chunks with combining Unicode marks (NFD)", nfd_count)

        # =====================================================================
        print_section("SUMMARY")
        # =====================================================================

        print(f"""
  Total documents:          {total_items}
  Total chunks:             {total_chunks}
  URL duplicates:           {len(url_dupes)} groups
  Title duplicates:         {len(title_dupes)} groups
  Navigation in chunks:     {total_nav}
  RSS fallback docs:        {rss_fallback_count}
  Broken hyphenation:       {hyphen_break_count}
  Junk chunks stored:       {junk_stored}
  Low quality chunks:       {low_quality}
  Missing embeddings:       {items_no_embed} items, {chunks_no_embed} chunks
  NULL text_quality:        {null_tq}
  No publication_date:      {no_pub_date}
  Old active (>1yr):        {old_active}
  NFD Unicode:              {nfd_count}
""")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(description="Data Quality Diagnostic for PratikoAI Knowledge Base")
    parser.add_argument("--samples", type=int, default=5, help="Number of samples per query (default: 5)")
    args = parser.parse_args()

    print("=" * 70)
    print("  PratikoAI Data Quality Diagnostic")
    print("  Based on DATA_CLEANING_AUDIT.md findings")
    print("=" * 70)

    asyncio.run(run_diagnostics(samples=args.samples))


if __name__ == "__main__":
    main()
