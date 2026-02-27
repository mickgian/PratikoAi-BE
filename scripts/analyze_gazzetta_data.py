#!/usr/bin/env python3
"""Analyze Gazzetta Ufficiale data in knowledge base.

DEV-247: Script to classify existing Gazzetta documents and identify
irrelevant content (concorsi, nomine, graduatorie) for cleanup.

Usage:
    # Show analysis report
    python scripts/analyze_gazzetta_data.py

    # Export recommendations to CSV
    python scripts/analyze_gazzetta_data.py --export recommendations.csv

    # Show sample titles for each category
    python scripts/analyze_gazzetta_data.py --samples 10
"""

import argparse
import asyncio
import csv
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.ingest.rss_normativa import (  # noqa: E402
    BLACKLIST_KEYWORDS,
    WHITELIST_KEYWORDS,
    is_relevant_for_pratikoai,
)
from app.models.knowledge import KnowledgeItem  # noqa: E402


def classify_document(title: str, summary: str = "") -> str:
    """Classify a document into a category based on content.

    Args:
        title: Document title
        summary: Document summary (optional)

    Returns:
        Category string: 'relevant', 'concorso', 'nomina', 'graduatoria',
                        'bando', 'avviso', 'estratto', 'other_irrelevant'
    """
    combined = f"{title} {summary}".lower()

    # Check for specific irrelevant categories first
    if "concors" in combined:
        return "concorso"
    if "nomin" in combined:
        return "nomina"
    if "graduatoria" in combined:
        return "graduatoria"
    if "bando" in combined:
        return "bando"
    if "avviso" in combined:
        return "avviso"
    if "estratt" in combined:
        return "estratto"

    # Check if relevant
    if is_relevant_for_pratikoai(title, summary):
        return "relevant"

    return "other_irrelevant"


async def analyze_gazzetta_documents(
    session: AsyncSession,
    show_samples: int = 0,
) -> dict:
    """Analyze all Gazzetta documents in the knowledge base.

    Args:
        session: Database session
        show_samples: Number of sample titles to show per category

    Returns:
        Analysis statistics dictionary
    """
    print("\n" + "=" * 80)
    print("GAZZETTA UFFICIALE CONTENT ANALYSIS")
    print("=" * 80)
    print(f"Analysis started: {datetime.now(UTC).isoformat()}")
    print()

    # Query all Gazzetta documents
    query = select(KnowledgeItem).where(
        KnowledgeItem.source.like("%gazzetta%")  # type: ignore[union-attr]
        | KnowledgeItem.source_url.like("%gazzettaufficiale%")  # type: ignore[union-attr]
    )
    result = await session.execute(query)
    documents = result.scalars().all()

    print(f"Total Gazzetta documents found: {len(documents)}")
    print()

    # Classify documents
    categories: dict[str, list] = defaultdict(list)
    for doc in documents:
        category = classify_document(doc.title or "", "")
        categories[category].append(
            {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "source_url": doc.source_url,
                "created_at": doc.created_at,
            }
        )

    # Generate report
    print("=" * 80)
    print("CLASSIFICATION SUMMARY")
    print("=" * 80)
    print()

    total = len(documents)
    relevant_count = len(categories.get("relevant", []))
    irrelevant_count = total - relevant_count

    # Relevant documents
    print(f"{'RELEVANT (to keep):':<30} {relevant_count:>6} ({relevant_count / total * 100:.1f}%)")
    print()

    # Irrelevant categories
    print("IRRELEVANT (candidates for removal):")
    irrelevant_categories = [
        "concorso",
        "nomina",
        "graduatoria",
        "bando",
        "avviso",
        "estratto",
        "other_irrelevant",
    ]

    for cat in irrelevant_categories:
        count = len(categories.get(cat, []))
        if count > 0:
            print(f"  {cat:<26} {count:>6} ({count / total * 100:.1f}%)")

    print()
    print(f"{'Total irrelevant:':<30} {irrelevant_count:>6} ({irrelevant_count / total * 100:.1f}%)")
    print()

    # Show samples if requested
    if show_samples > 0:
        print("=" * 80)
        print(f"SAMPLE TITLES (up to {show_samples} per category)")
        print("=" * 80)

        for cat in ["relevant"] + irrelevant_categories:
            docs = categories.get(cat, [])
            if docs:
                print(f"\n--- {cat.upper()} ---")
                for doc in docs[:show_samples]:
                    title = doc["title"][:70] + "..." if len(doc["title"] or "") > 70 else doc["title"]
                    print(f"  [{doc['id']}] {title}")

    # Return statistics
    return {
        "total": total,
        "relevant": relevant_count,
        "irrelevant": irrelevant_count,
        "categories": {cat: len(docs) for cat, docs in categories.items()},
        "documents_by_category": categories,
    }


async def export_recommendations(
    session: AsyncSession,
    output_path: str,
) -> int:
    """Export document IDs recommended for deletion to CSV.

    Args:
        session: Database session
        output_path: Path to output CSV file

    Returns:
        Number of documents exported
    """
    stats = await analyze_gazzetta_documents(session, show_samples=0)

    # Collect all irrelevant documents
    irrelevant_docs = []
    for cat in [
        "concorso",
        "nomina",
        "graduatoria",
        "bando",
        "avviso",
        "estratto",
        "other_irrelevant",
    ]:
        irrelevant_docs.extend(stats["documents_by_category"].get(cat, []))

    # Write to CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "title", "source", "source_url", "created_at", "category"],
        )
        writer.writeheader()

        for doc in irrelevant_docs:
            category = classify_document(doc["title"] or "", "")
            writer.writerow(
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "source": doc["source"],
                    "source_url": doc["source_url"],
                    "created_at": doc["created_at"],
                    "category": category,
                }
            )

    print()
    print("=" * 80)
    print(f"EXPORTED {len(irrelevant_docs)} DOCUMENTS TO: {output_path}")
    print("=" * 80)

    return len(irrelevant_docs)


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Gazzetta Ufficiale documents in knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export recommendations to CSV file",
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of sample titles to show per category (default: 5)",
    )

    args = parser.parse_args()

    # Create async database session
    postgres_url = settings.POSTGRES_URL
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            if args.export:
                await export_recommendations(session, args.export)
            else:
                await analyze_gazzetta_documents(session, show_samples=args.samples)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
