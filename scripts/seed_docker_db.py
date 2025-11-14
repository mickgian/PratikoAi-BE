#!/usr/bin/env python3
"""
Seed Docker database with essential data from host database.
Imports user accounts and Risoluzione 56 knowledge base content.
"""
import asyncio
import json
import sys
from decimal import Decimal

from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

# Database URLs
HOST_DB_URL = "postgresql://aifinance:devpass@localhost:5432/aifinance"  # pragma: allowlist secret
DOCKER_DB_URL = "postgresql://aifinance:devpass@localhost:5433/aifinance"  # pragma: allowlist secret


def prepare_row_data(row_dict):
    """Convert row data to handle JSON and special types."""
    result = {}
    for key, value in row_dict.items():
        if value is None:
            result[key] = None
        elif isinstance(value, (dict, list)):
            result[key] = json.dumps(value)
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result


async def seed_data():
    """Copy essential data from host DB to Docker DB."""

    # Create sync engines for simpler data copy
    host_engine = create_engine(HOST_DB_URL)
    docker_engine = create_engine(DOCKER_DB_URL)

    print("🌱 Starting database seeding...")

    # 1. Copy user accounts
    print("\n📋 Copying user accounts...")
    with host_engine.connect() as host_conn:
        users = host_conn.execute(text('SELECT * FROM "user" LIMIT 5')).fetchall()
        print(f"   Found {len(users)} users in host DB")

        if users:
            # Get column names
            columns = host_conn.execute(text('SELECT * FROM "user" LIMIT 0')).keys()
            cols_str = ", ".join([f'"{col}"' for col in columns])
            placeholders = ", ".join([f":{col}" for col in columns])

            with docker_engine.connect() as docker_conn:
                # Clear existing users
                docker_conn.execute(text('TRUNCATE TABLE "user" CASCADE'))
                docker_conn.commit()

                # Insert users
                for user in users:
                    user_dict = prepare_row_data(dict(zip(columns, user)))
                    insert_sql = f'INSERT INTO "user" ({cols_str}) VALUES ({placeholders})'
                    docker_conn.execute(text(insert_sql), user_dict)
                docker_conn.commit()
                print(f"   ✅ Copied {len(users)} users")

    # 2. Copy Risoluzione 56 knowledge items
    print("\n📚 Copying Risoluzione 56 knowledge items...")
    with host_engine.connect() as host_conn:
        # Find items related to Risoluzione 56
        items_query = text(
            """
            SELECT * FROM knowledge_items
            WHERE title ILIKE '%risoluzione%56%'
               OR content ILIKE '%risoluzione%56%'
               OR source_url ILIKE '%risoluzione%56%'
            LIMIT 10
        """
        )
        items = host_conn.execute(items_query).fetchall()
        print(f"   Found {len(items)} knowledge items")

        if items:
            columns = host_conn.execute(text("SELECT * FROM knowledge_items LIMIT 0")).keys()
            cols_str = ", ".join([f'"{col}"' for col in columns])
            placeholders = ", ".join([f":{col}" for col in columns])

            with docker_engine.connect() as docker_conn:
                # Clear existing knowledge items
                docker_conn.execute(text("TRUNCATE TABLE knowledge_items CASCADE"))
                docker_conn.commit()

                # Insert knowledge items
                item_ids = []
                for item in items:
                    item_dict = prepare_row_data(dict(zip(columns, item)))
                    item_ids.append(item_dict["id"])
                    insert_sql = f"INSERT INTO knowledge_items ({cols_str}) VALUES ({placeholders})"
                    docker_conn.execute(text(insert_sql), item_dict)
                docker_conn.commit()
                print(f"   ✅ Copied {len(items)} knowledge items")

                # 3. Copy related knowledge chunks
                if item_ids:
                    print("\n📝 Copying knowledge chunks...")
                    with host_engine.connect() as host_conn2:
                        ids_str = ",".join(map(str, item_ids))
                        chunks_query = text(
                            f"""
                            SELECT * FROM knowledge_chunks
                            WHERE knowledge_item_id IN ({ids_str})
                            ORDER BY knowledge_item_id, chunk_index
                        """
                        )
                        chunks = host_conn2.execute(chunks_query).fetchall()
                        print(f"   Found {len(chunks)} chunks")

                        if chunks:
                            chunk_columns = host_conn2.execute(text("SELECT * FROM knowledge_chunks LIMIT 0")).keys()
                            chunk_cols_str = ", ".join([f'"{col}"' for col in chunk_columns])
                            chunk_placeholders = ", ".join([f":{col}" for col in chunk_columns])

                            # Clear existing chunks
                            docker_conn.execute(text("TRUNCATE TABLE knowledge_chunks CASCADE"))
                            docker_conn.commit()

                            # Insert chunks
                            for chunk in chunks:
                                chunk_dict = prepare_row_data(dict(zip(chunk_columns, chunk)))
                                insert_sql = (
                                    f"INSERT INTO knowledge_chunks ({chunk_cols_str}) VALUES ({chunk_placeholders})"
                                )
                                docker_conn.execute(text(insert_sql), chunk_dict)
                            docker_conn.commit()
                            print(f"   ✅ Copied {len(chunks)} chunks")

    print("\n✅ Seeding complete!")
    print("\n📊 Summary:")
    with docker_engine.connect() as conn:
        user_count = conn.execute(text('SELECT COUNT(*) FROM "user"')).scalar()
        item_count = conn.execute(text("SELECT COUNT(*) FROM knowledge_items")).scalar()
        chunk_count = conn.execute(text("SELECT COUNT(*) FROM knowledge_chunks")).scalar()
        print(f"   - Users: {user_count}")
        print(f"   - Knowledge Items: {item_count}")
        print(f"   - Knowledge Chunks: {chunk_count}")

    host_engine.dispose()
    docker_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
