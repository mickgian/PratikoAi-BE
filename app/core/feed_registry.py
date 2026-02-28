"""Canonical RSS feed registry and startup seeding.

Single source of truth for the 16 RSS feeds monitored by PratikoAI.
Called on every app startup to guarantee feeds exist in feed_status,
regardless of Alembic migration state.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

# Canonical feed definitions — the authoritative list.
# Any changes to feeds should be made HERE, not in migrations or scripts.
CANONICAL_FEEDS: list[dict[str, str | int]] = [
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

_UPSERT_SQL = text("""
    INSERT INTO feed_status (
        feed_url, source, feed_type, parser, status, enabled,
        consecutive_errors, errors, check_interval_minutes
    )
    VALUES (
        :feed_url, :source, :feed_type, :parser, 'pending', true,
        0, 0, :check_interval_minutes
    )
    ON CONFLICT (feed_url) DO NOTHING
""")


async def ensure_feeds_seeded(session: AsyncSession) -> dict[str, int]:
    """Ensure all canonical feeds exist in feed_status.

    Idempotent: inserts only feeds whose feed_url is not already present.
    Does NOT overwrite existing feed state (status, errors, last_success, etc.).

    Called automatically on every app startup via start_scheduler().

    Args:
        session: Async database session.

    Returns:
        Dict with 'seeded' count (number of newly inserted feeds).
    """
    existing_urls_result = await session.execute(text("SELECT feed_url FROM feed_status"))
    existing_urls = {row[0] for row in existing_urls_result}

    seeded = 0
    for feed in CANONICAL_FEEDS:
        if feed["feed_url"] not in existing_urls:
            await session.execute(_UPSERT_SQL, feed)
            seeded += 1

    if seeded > 0:
        await session.commit()
        logger.info("feed_registry_seeded", seeded=seeded, total=len(CANONICAL_FEEDS))
    else:
        logger.debug("feed_registry_all_present", total=len(CANONICAL_FEEDS))

    return {"seeded": seeded}
