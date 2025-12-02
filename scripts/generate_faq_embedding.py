"""Generate question embedding for existing FAQ entry in Golden Set.

This script generates the embedding vector for the FAQ entry created from expert feedback
so it can be retrieved via semantic search in Step 24.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.faq import FAQEntry
from app.services.llm_factory import LLMFactory


async def generate_embedding_for_faq(faq_id: str):
    """Generate and save embedding for a specific FAQ entry."""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aifinance:devpass@localhost:5433/aifinance")

    # Create async engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Fetch the FAQ entry
        result = await session.execute(select(FAQEntry).where(FAQEntry.id == faq_id))
        faq = result.scalar_one_or_none()

        if not faq:
            print(f"❌ FAQ entry {faq_id} not found")
            return False

        print("✅ Found FAQ entry:")
        print(f"   Question: {faq.question}")
        print(f"   Category: {faq.category}")
        print(f"   Version: {faq.version}")

        # Generate embedding using LLMFactory
        print("\n🔄 Generating embedding for question...")
        llm_factory = LLMFactory()
        embedding = await llm_factory.create_embedding(faq.question)

        if not embedding or len(embedding) != 1536:
            print(f"❌ Failed to generate valid embedding (length: {len(embedding) if embedding else 0})")
            return False

        print("✅ Generated embedding vector (1536 dimensions)")

        # Update the FAQ entry with the embedding
        print("\n🔄 Saving embedding to database...")
        await session.execute(update(FAQEntry).where(FAQEntry.id == faq_id).values(question_embedding=embedding))
        await session.commit()

        print(f"✅ Successfully saved embedding for FAQ {faq_id}")
        print("\n🎯 FAQ entry is now ready for semantic search retrieval!")

        return True


async def main():
    """Main function."""
    # The FAQ ID created from expert feedback
    faq_id = "3bd6945b-1813-4073-9bd3-d6a3154b8097"

    print("=" * 70)
    print("Generate FAQ Embedding for Golden Set")
    print("=" * 70)
    print(f"\nTarget FAQ ID: {faq_id}\n")

    success = await generate_embedding_for_faq(faq_id)

    if success:
        print("\n" + "=" * 70)
        print("✅ SUCCESS: FAQ embedding generated and saved")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌ FAILED: Could not generate embedding")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
