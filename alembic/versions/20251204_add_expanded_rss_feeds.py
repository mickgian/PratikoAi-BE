"""Add expanded RSS feed configurations for DEV-BE-69

Revision ID: add_expanded_rss_feeds_20251204
Revises: 8f41bd3ce9fd
Create Date: 2025-12-04

This migration adds RSS feed configurations to expand knowledge base coverage (16 total):
- Agenzia Entrate: 2 feeds (legacy idrss URLs: normativa_prassi, news)
- INPS: 5 feeds (news, circolari, messaggi, sentenze, comunicati)
- Ministero del Lavoro: 1 feed (news)
- MEF: 2 feeds (documenti, aggiornamenti)
- INAIL: 2 feeds (news, eventi)
- Gazzetta Ufficiale: 4 feeds (SG serie_generale, S1 corte_costituzionale, S2 unione_europea, S3 regioni)
"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_expanded_rss_feeds_20251204"
down_revision = "8f41bd3ce9fd"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade():
    """Insert expanded RSS feed configurations."""
    # First, delete old semantic Agenzia Entrate URLs (keep only legacy idrss URLs)
    op.execute(
        text(
            """
            DELETE FROM feed_status
            WHERE source = 'agenzia_entrate'
              AND feed_url LIKE 'https://www.agenziaentrate.gov.it/portale/rss/%';
            """
        )
    )

    # Define all 16 feeds that should exist
    feeds = [
        # Agenzia delle Entrate (2 legacy feeds) - use agenzia_normativa parser
        {
            "feed_url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4",
            "source": "agenzia_entrate",
            "feed_type": "normativa_prassi",
            "parser": "agenzia_normativa",
        },
        {
            "feed_url": "https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9",
            "source": "agenzia_entrate",
            "feed_type": "news",
            "parser": "agenzia_normativa",
        },
        # INPS (5 feeds) - use inps parser
        {
            "feed_url": "https://www.inps.it/it/it.rss.news.xml",
            "source": "inps",
            "feed_type": "news",
            "parser": "inps",
        },
        {
            "feed_url": "https://www.inps.it/it/it.rss.circolari.xml",
            "source": "inps",
            "feed_type": "circolari",
            "parser": "inps",
        },
        {
            "feed_url": "https://www.inps.it/it/it.rss.messaggi.xml",
            "source": "inps",
            "feed_type": "messaggi",
            "parser": "inps",
        },
        {
            "feed_url": "https://www.inps.it/it/it.rss.sentenze.xml",
            "source": "inps",
            "feed_type": "sentenze",
            "parser": "inps",
        },
        {
            "feed_url": "https://www.inps.it/it/it.rss.comunicati.xml",
            "source": "inps",
            "feed_type": "comunicati",
            "parser": "inps",
        },
        # Ministero del Lavoro (1 feed) - use generic parser
        {
            "feed_url": "https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS",
            "source": "ministero_lavoro",
            "feed_type": "news",
            "parser": "generic",
        },
        # MEF - Ministero dell'Economia e delle Finanze (2 feeds) - use generic parser
        {
            "feed_url": "https://www.mef.gov.it/rss/rss.asp?t=5",
            "source": "ministero_economia",
            "feed_type": "documenti",
            "parser": "generic",
        },
        {
            "feed_url": "https://www.finanze.gov.it/it/rss.xml",
            "source": "ministero_economia",
            "feed_type": "aggiornamenti",
            "parser": "generic",
        },
        # INAIL (2 feeds) - use generic parser
        {
            "feed_url": "https://www.inail.it/portale/it.rss.news.xml",
            "source": "inail",
            "feed_type": "news",
            "parser": "generic",
        },
        {
            "feed_url": "https://www.inail.it/portale/it.rss.eventi.xml",
            "source": "inail",
            "feed_type": "eventi",
            "parser": "generic",
        },
        # Gazzetta Ufficiale (4 feeds) - use gazzetta_ufficiale parser
        # Note: Old URL /rss/serie_generale.xml returns 404 since 2025.
        # New URL format is /rss/{code} where code is SG, S1, S2, S3, etc.
        # Check interval: 24 hours (1440 min) - publishes once daily
        {
            "feed_url": "https://www.gazzettaufficiale.it/rss/SG",
            "source": "gazzetta_ufficiale",
            "feed_type": "serie_generale",
            "parser": "gazzetta_ufficiale",
            "check_interval_minutes": 1440,  # 24 hours - daily publication
        },
        {
            "feed_url": "https://www.gazzettaufficiale.it/rss/S1",
            "source": "gazzetta_ufficiale",
            "feed_type": "corte_costituzionale",
            "parser": "gazzetta_ufficiale",
            "check_interval_minutes": 1440,  # 24 hours - daily publication
        },
        {
            "feed_url": "https://www.gazzettaufficiale.it/rss/S2",
            "source": "gazzetta_ufficiale",
            "feed_type": "unione_europea",
            "parser": "gazzetta_ufficiale",
            "check_interval_minutes": 1440,  # 24 hours - daily publication
        },
        {
            "feed_url": "https://www.gazzettaufficiale.it/rss/S3",
            "source": "gazzetta_ufficiale",
            "feed_type": "regioni",
            "parser": "gazzetta_ufficiale",
            "check_interval_minutes": 1440,  # 24 hours - daily publication
        },
    ]

    # Use upsert pattern to handle existing feeds
    for feed in feeds:
        # Use per-feed check interval if specified, otherwise default to 240 min (4 hours)
        check_interval = feed.get("check_interval_minutes", 240)
        op.execute(
            text(
                """
                INSERT INTO feed_status (
                    feed_url, source, feed_type, parser, status, enabled,
                    consecutive_errors, errors, check_interval_minutes
                )
                VALUES (
                    :feed_url, :source, :feed_type, :parser, 'pending', true,
                    0, 0, :check_interval
                )
                ON CONFLICT (feed_url) DO UPDATE SET
                    source = EXCLUDED.source,
                    feed_type = EXCLUDED.feed_type,
                    parser = EXCLUDED.parser,
                    enabled = true,
                    check_interval_minutes = :check_interval
                """
            ).bindparams(
                feed_url=feed["feed_url"],
                source=feed["source"],
                feed_type=feed["feed_type"],
                parser=feed["parser"],
                check_interval=check_interval,
            )
        )


def downgrade():
    """Remove newly added RSS feeds (keep Agenzia Entrate and Gazzetta Ufficiale)."""
    # Remove INPS feeds
    op.execute(
        """
        DELETE FROM feed_status
        WHERE source = 'inps'
          AND feed_url LIKE 'https://www.inps.it/%';
        """
    )

    # Remove Ministero del Lavoro feed
    op.execute(
        """
        DELETE FROM feed_status
        WHERE source = 'ministero_lavoro';
        """
    )

    # Remove MEF feeds
    op.execute(
        """
        DELETE FROM feed_status
        WHERE source = 'ministero_economia';
        """
    )

    # Remove INAIL feeds
    op.execute(
        """
        DELETE FROM feed_status
        WHERE source = 'inail';
        """
    )
