#!/usr/bin/env python3
"""Seed RSS feed configurations into feed_status table.

Idempotent script that ensures all 16 RSS feed configurations exist.
Uses ON CONFLICT (feed_url) DO UPDATE so it's safe to run multiple times.

Usage (inside QA container):
    docker exec -it pratikoai-app python scripts/seed_rss_feeds.py

Usage (locally):
    POSTGRES_URL=postgresql://... uv run python scripts/seed_rss_feeds.py
"""

import os
import sys

from sqlalchemy import create_engine, text

# All 16 RSS feeds — must match alembic/versions/20251204_add_expanded_rss_feeds.py
FEEDS = [
    # Agenzia delle Entrate (2 feeds)
    {
        "feed_url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4",
        "source": "agenzia_entrate",
        "feed_type": "normativa_prassi",
        "parser": "agenzia_normativa",
        "check_interval_minutes": 240,
    },
    {
        "feed_url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9",
        "source": "agenzia_entrate",
        "feed_type": "news",
        "parser": "agenzia_normativa",
        "check_interval_minutes": 240,
    },
    # INPS (5 feeds)
    {
        "feed_url": "https://www.inps.it/it/it.rss.news.xml",
        "source": "inps",
        "feed_type": "news",
        "parser": "inps",
        "check_interval_minutes": 240,
    },
    {
        "feed_url": "https://www.inps.it/it/it.rss.circolari.xml",
        "source": "inps",
        "feed_type": "circolari",
        "parser": "inps",
        "check_interval_minutes": 240,
    },
    {
        "feed_url": "https://www.inps.it/it/it.rss.messaggi.xml",
        "source": "inps",
        "feed_type": "messaggi",
        "parser": "inps",
        "check_interval_minutes": 240,
    },
    {
        "feed_url": "https://www.inps.it/it/it.rss.sentenze.xml",
        "source": "inps",
        "feed_type": "sentenze",
        "parser": "inps",
        "check_interval_minutes": 240,
    },
    {
        "feed_url": "https://www.inps.it/it/it.rss.comunicati.xml",
        "source": "inps",
        "feed_type": "comunicati",
        "parser": "inps",
        "check_interval_minutes": 240,
    },
    # Ministero del Lavoro (1 feed)
    {
        "feed_url": "https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS",
        "source": "ministero_lavoro",
        "feed_type": "news",
        "parser": "generic",
        "check_interval_minutes": 240,
    },
    # MEF (2 feeds)
    {
        "feed_url": "https://www.mef.gov.it/rss/rss.asp?t=5",
        "source": "ministero_economia",
        "feed_type": "documenti",
        "parser": "generic",
        "check_interval_minutes": 240,
    },
    {
        "feed_url": "https://www.finanze.gov.it/it/rss.xml",
        "source": "ministero_economia",
        "feed_type": "aggiornamenti",
        "parser": "generic",
        "check_interval_minutes": 240,
    },
    # INAIL (2 feeds)
    {
        "feed_url": "https://www.inail.it/portale/it.rss.news.xml",
        "source": "inail",
        "feed_type": "news",
        "parser": "generic",
        "check_interval_minutes": 240,
    },
    {
        "feed_url": "https://www.inail.it/portale/it.rss.eventi.xml",
        "source": "inail",
        "feed_type": "eventi",
        "parser": "generic",
        "check_interval_minutes": 240,
    },
    # Gazzetta Ufficiale (4 feeds) — daily publication
    {
        "feed_url": "https://www.gazzettaufficiale.it/rss/SG",
        "source": "gazzetta_ufficiale",
        "feed_type": "serie_generale",
        "parser": "gazzetta_ufficiale",
        "check_interval_minutes": 1440,
    },
    {
        "feed_url": "https://www.gazzettaufficiale.it/rss/S1",
        "source": "gazzetta_ufficiale",
        "feed_type": "corte_costituzionale",
        "parser": "gazzetta_ufficiale",
        "check_interval_minutes": 1440,
    },
    {
        "feed_url": "https://www.gazzettaufficiale.it/rss/S2",
        "source": "gazzetta_ufficiale",
        "feed_type": "unione_europea",
        "parser": "gazzetta_ufficiale",
        "check_interval_minutes": 1440,
    },
    {
        "feed_url": "https://www.gazzettaufficiale.it/rss/S3",
        "source": "gazzetta_ufficiale",
        "feed_type": "regioni",
        "parser": "gazzetta_ufficiale",
        "check_interval_minutes": 1440,
    },
]

UPSERT_SQL = text("""
    INSERT INTO feed_status (
        feed_url, source, feed_type, parser, status, enabled,
        consecutive_errors, errors, check_interval_minutes
    )
    VALUES (
        :feed_url, :source, :feed_type, :parser, 'pending', true,
        0, 0, :check_interval_minutes
    )
    ON CONFLICT (feed_url) DO UPDATE SET
        source = EXCLUDED.source,
        feed_type = EXCLUDED.feed_type,
        parser = EXCLUDED.parser,
        enabled = true,
        check_interval_minutes = EXCLUDED.check_interval_minutes
""")


def main() -> None:
    db_url = os.environ.get("POSTGRES_URL")
    if not db_url:
        print("ERROR: POSTGRES_URL environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Ensure sync driver (not asyncpg)
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Show current state
        count_before = conn.execute(text("SELECT COUNT(*) FROM feed_status")).scalar()
        print(f"Current feed_status rows: {count_before}")

        # Upsert all feeds
        for feed in FEEDS:
            conn.execute(UPSERT_SQL, feed)
            print(f"  Upserted: {feed['source']}/{feed['feed_type']}")

        conn.commit()

        # Show final state
        count_after = conn.execute(text("SELECT COUNT(*) FROM feed_status")).scalar()
        enabled = conn.execute(text("SELECT COUNT(*) FROM feed_status WHERE enabled = true")).scalar()
        print(f"\nDone. feed_status rows: {count_after} ({enabled} enabled)")

    engine.dispose()


if __name__ == "__main__":
    main()
