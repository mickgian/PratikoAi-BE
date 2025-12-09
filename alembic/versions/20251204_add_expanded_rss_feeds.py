"""Add expanded RSS feed configurations for DEV-BE-69

Revision ID: add_expanded_rss_feeds_20251204
Revises: 8f41bd3ce9fd
Create Date: 2025-12-04

This migration adds 10 new RSS feed configurations to expand knowledge base coverage:
- INPS: 5 feeds (news, circolari, messaggi, sentenze, comunicati)
- Ministero del Lavoro: 1 feed (news)
- MEF: 2 feeds (documenti, aggiornamenti)
- INAIL: 2 feeds (news, eventi)

It also ensures the existing feeds (Agenzia Entrate, Gazzetta Ufficiale) are present.
"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_expanded_rss_feeds_20251204"
down_revision = "8f41bd3ce9fd"
branch_labels = None
depends_on = None


def upgrade():
    """Insert expanded RSS feed configurations."""
    # Define all 13 feeds that should exist
    feeds = [
        # Agenzia delle Entrate (3 feeds) - use agenzia_normativa parser
        {
            "feed_url": "https://www.agenziaentrate.gov.it/portale/rss/circolari.xml",
            "source": "agenzia_entrate",
            "feed_type": "circolari",
            "parser": "agenzia_normativa",
        },
        {
            "feed_url": "https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml",
            "source": "agenzia_entrate",
            "feed_type": "risoluzioni",
            "parser": "agenzia_normativa",
        },
        {
            "feed_url": "https://www.agenziaentrate.gov.it/portale/rss/provvedimenti.xml",
            "source": "agenzia_entrate",
            "feed_type": "provvedimenti",
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
        # Gazzetta Ufficiale (1 feed) - use gazzetta_ufficiale parser
        {
            "feed_url": "https://www.gazzettaufficiale.it/rss/serie_generale.xml",
            "source": "gazzetta_ufficiale",
            "feed_type": "serie_generale",
            "parser": "gazzetta_ufficiale",
        },
    ]

    # Use upsert pattern to handle existing feeds
    for feed in feeds:
        op.execute(
            text(
                """
                INSERT INTO feed_status (
                    feed_url, source, feed_type, parser, status, enabled,
                    consecutive_errors, errors, check_interval_minutes
                )
                VALUES (
                    :feed_url, :source, :feed_type, :parser, 'pending', true,
                    0, 0, 240
                )
                ON CONFLICT (feed_url) DO UPDATE SET
                    source = EXCLUDED.source,
                    feed_type = EXCLUDED.feed_type,
                    parser = EXCLUDED.parser,
                    enabled = true,
                    check_interval_minutes = 240
                """
            ).bindparams(
                feed_url=feed["feed_url"],
                source=feed["source"],
                feed_type=feed["feed_type"],
                parser=feed["parser"],
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
