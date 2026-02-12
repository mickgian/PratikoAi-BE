#!/usr/bin/env python3
"""Data Quality Diagnostic Script for DATA_CLEANING_AUDIT.md verification.

Runs SQL queries against the knowledge base to confirm or refute audit findings.
Produces a summary report with counts and sample data.

Usage:
    # Full diagnostic (default database)
    python scripts/audit_data_quality.py

    # With custom database URL
    DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" python scripts/audit_data_quality.py  # pragma: allowlist secret

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

from app.services.data_quality_audit_service import DataQualityAuditService, DataQualitySummary


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


def print_summary_from_service(s: DataQualitySummary) -> None:
    """Print the SUMMARY section using DataQualitySummary fields."""
    print_section("SUMMARY")
    print(f"""
  Total documents:          {s.total_items}
  Total chunks:             {s.total_chunks}
  URL duplicates:           {s.url_duplicate_groups} groups
  Title duplicates:         {s.title_duplicate_groups} groups
  Navigation-contaminated:  {s.navigation_contaminated_chunks}
  RSS fallback docs:        {s.rss_fallback_docs}
  Broken hyphenation:       {s.broken_hyphenation_chunks}
  Junk chunks stored:       {s.junk_chunks_stored}
  Low quality chunks:       {s.low_quality_chunks}
  Missing embeddings:       {s.items_missing_embedding} items, {s.chunks_missing_embedding} chunks
  NULL text_quality:        {s.null_text_quality}
  No publication_date:      {s.no_publication_date}
  Old active (>1yr):        {s.old_active_documents}
  NFD Unicode:              {s.nfd_unicode_chunks}
""")


async def run_diagnostics(samples: int = 5) -> None:
    """Run all diagnostic queries."""
    db = await get_db_session()

    try:
        # --- Use service for all COUNT metrics ---
        audit_service = DataQualityAuditService(db)
        s = await audit_service.run_summary()

        # =====================================================================
        print_section("1. KNOWLEDGE BASE OVERVIEW")
        # =====================================================================

        print(f"  Total knowledge_items: {s.total_items}")
        print(f"  Total knowledge_chunks: {s.total_chunks}")

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

        # URL-based duplicates — count from service, samples from DB
        print_finding("Exact URL duplicates (same URL, multiple records)", s.url_duplicate_groups)
        if samples > 0:
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
            for row in result.fetchall():
                print(f"    URL: {row[0][:80]}... ({row[1]} copies)")

        # Content-based near-duplicates (same title, different URL)
        print_finding("Same title, different URLs (potential content dupes)", s.title_duplicate_groups)
        if samples > 0:
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
            for row in result.fetchall():
                print(f"    Title: {row[0][:70]}... ({row[1]} copies)")

        # =====================================================================
        print_section("3. NAVIGATION TEXT IN CHUNKS (Finding E.6)")
        # =====================================================================

        print_finding("Navigation-contaminated chunks (repair criteria)", s.navigation_contaminated_chunks)

        # --- Informational: per-pattern occurrence breakdown ---
        from app.core.text.clean import NAVIGATION_PATTERNS

        nav_patterns = list(NAVIGATION_PATTERNS)
        print("\n  Per-pattern occurrence counts (informational, may overlap):")
        total_pattern_hits = 0
        for pattern in nav_patterns:
            result = await db.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE LOWER(chunk_text) LIKE :pattern"),
                {"pattern": f"%{pattern}%"},
            )
            count = result.scalar() or 0
            if count > 0:
                total_pattern_hits += count
                print(f"    '{pattern}': {count} chunks")
        print(f"  Total pattern occurrences (summed, with overlap): {total_pattern_hits}")

        if s.navigation_contaminated_chunks > 0 and samples > 0:
            from app.services.data_quality_audit_service import _build_navigation_contamination_sql

            # Re-build the expressions for sample query
            like_conditions = [f"LOWER(chunk_text) LIKE '%{p}%'" for p in nav_patterns]
            count_expr = " + ".join(f"CASE WHEN {c} THEN 1 ELSE 0 END" for c in like_conditions)
            any_condition = " OR ".join(like_conditions)

            sample_sql = (
                f"SELECT LEFT(chunk_text, 200), document_title, source_url, "
                f"({count_expr}) as nav_count, LENGTH(chunk_text) as len "
                f"FROM knowledge_chunks "
                f"WHERE ({any_condition}) "
                f"AND (({count_expr}) >= 2 OR (({count_expr}) >= 1 AND LENGTH(chunk_text) < 300)) "
                f"LIMIT :limit"
            )
            result = await db.execute(text(sample_sql), {"limit": samples})
            nav_samples = result.fetchall()
            print("\n  Sample contaminated chunks:")
            for row in nav_samples:
                print(f"    Doc: {row[1]} (nav_count={row[3]}, len={row[4]})")
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
            result = await db.execute(
                text("SELECT COUNT(*) FROM knowledge_items WHERE content LIKE :pattern"), {"pattern": f"%{pattern}%"}
            )
            items_count = result.scalar() or 0

            result = await db.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE chunk_text LIKE :pattern"),
                {"pattern": f"%{pattern}%"},
            )
            chunks_count = result.scalar() or 0

            if items_count > 0 or chunks_count > 0:
                print(f"    {label}: {items_count} items, {chunks_count} chunks")

        print_finding("Documents using RSS summary fallback", s.rss_fallback_docs)

        if s.rss_fallback_docs > 0 and samples > 0:
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

        print_finding("Chunks with broken hyphenation (word- fragment)", s.broken_hyphenation_chunks)

        if s.broken_hyphenation_chunks > 0 and samples > 0:
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

        if s.chunk_stats:
            cs = s.chunk_stats
            print("  Token count distribution:")
            print(f"    Min:    {cs.get('min')}")
            print(f"    Max:    {cs.get('max')}")
            print(f"    Avg:    {cs.get('avg')}")
            print(f"    Median: {cs.get('median')}")
            print(f"    P95:    {cs.get('p95')}")

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

        print_finding("Chunks flagged as junk (stored despite JUNK_DROP_CHUNK)", s.junk_chunks_stored)
        print_finding("Low quality chunks (quality_score < 0.5)", s.low_quality_chunks)
        print_finding("Chunks with NULL quality_score", s.null_quality_chunks)

        # =====================================================================
        print_section("8. MISSING EMBEDDINGS (Finding E.9)")
        # =====================================================================

        print_finding("Knowledge items without embedding", s.items_missing_embedding)
        print_finding("Knowledge chunks without embedding", s.chunks_missing_embedding)

        # =====================================================================
        print_section("9. STALENESS / SUPERSEDED DOCUMENTS (Finding E.3)")
        # =====================================================================

        print("  Document status distribution:")
        for status_name, count in s.status_distribution.items():
            print(f"    {str(status_name):20s} {count:>5d}")

        print_finding("Active documents older than 1 year", s.old_active_documents)
        print_finding("Documents without publication_date", s.no_publication_date)

        # =====================================================================
        print_section("10. TEXT QUALITY FOR HTML DOCUMENTS (Backfill check)")
        # =====================================================================

        print_finding("Documents with NULL text_quality", s.null_text_quality)

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

        print_finding("Chunks with combining Unicode marks (NFD)", s.nfd_unicode_chunks)

        # =====================================================================
        # SUMMARY — uses service dataclass
        # =====================================================================

        print_summary_from_service(s)

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
