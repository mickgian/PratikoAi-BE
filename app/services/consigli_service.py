"""ConsigliService: on-demand AI insight report (ADR-038).

Generates a self-contained HTML report analyzing user interaction
patterns across 5 facet dimensions. No cost/pricing data exposed.
"""

import html as html_mod
import re
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.privacy.anonymizer import anonymizer
from app.models.data_export import QueryHistory
from app.services.cache import get_redis_client

MIN_QUERIES = 20
MIN_HISTORY_DAYS = 7
LOCK_TTL_SECONDS = 90


class ConsigliService:
    """Generates on-demand insight reports from user interaction history."""

    async def can_generate(self, user_id: int, db: AsyncSession) -> dict:
        """Check if enough data exists for meaningful analysis."""
        count_q = select(func.count(QueryHistory.id)).where(QueryHistory.user_id == user_id)
        count_result = await db.execute(count_q)
        query_count = count_result.scalar_one()

        if query_count < MIN_QUERIES:
            return {
                "can_generate": False,
                "query_count": query_count,
                "history_days": 0,
                "message_it": (
                    "Non ci sono ancora dati sufficienti per generare "
                    "un report significativo. Servono almeno "
                    f"{MIN_QUERIES} interazioni."
                ),
            }

        dates_q = select(
            func.min(QueryHistory.timestamp).label("min_ts"),
            func.max(QueryHistory.timestamp).label("max_ts"),
        ).where(QueryHistory.user_id == user_id)
        dates_result = await db.execute(dates_q)
        row = dates_result.one_or_none()

        history_days = 0
        if row and row.min_ts and row.max_ts:
            history_days = (row.max_ts - row.min_ts).days

        if history_days < MIN_HISTORY_DAYS:
            return {
                "can_generate": False,
                "query_count": query_count,
                "history_days": history_days,
                "message_it": (
                    "Non ci sono ancora dati sufficienti per generare "
                    "un report significativo. Continua a utilizzare "
                    "PratikoAI e riprova tra qualche giorno."
                ),
            }

        return {
            "can_generate": True,
            "query_count": query_count,
            "history_days": history_days,
            "message_it": "Dati sufficienti per la generazione del report.",
        }

    async def collect_stats(self, user_id: int, db: AsyncSession) -> dict:
        """Collect aggregated statistics (no cost data, no PII)."""
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        q = select(QueryHistory).where(
            QueryHistory.user_id == user_id,
            QueryHistory.timestamp >= ninety_days_ago,
        )
        result = await db.execute(q)
        rows = result.scalars().all()

        domain_counter: Counter = Counter()
        hourly_counter: Counter = Counter()
        sessions: set = set()
        cache_hits = 0
        kb_sources: set = set()
        dates_seen: set = set()

        for row in rows:
            domain_counter[row.query_type or "general"] += 1
            if row.timestamp:
                hourly_counter[str(row.timestamp.hour)] += 1
                dates_seen.add(row.timestamp.date())
            if row.session_id:
                sessions.add(row.session_id)
            if row.response_cached:
                cache_hits += 1
            if row.kb_sources_metadata:
                for src in row.kb_sources_metadata:
                    if isinstance(src, dict) and "source" in src:
                        kb_sources.add(src["source"])

        total = len(rows)
        min_ts = min((r.timestamp for r in rows if r.timestamp), default=None)
        max_ts = max((r.timestamp for r in rows if r.timestamp), default=None)
        history_days = (max_ts - min_ts).days if min_ts and max_ts else 0

        return {
            "total_queries": total,
            "domain_distribution": dict(domain_counter),
            "hourly_distribution": dict(hourly_counter),
            "session_count": len(sessions),
            "cache_hit_rate": cache_hits / total if total > 0 else 0,
            "kb_sources_used": sorted(kb_sources),
            "history_days": history_days,
            "active_days": len(dates_seen),
        }

    async def _call_llm_analysis(self, stats: dict) -> str:
        """Call production LLM to synthesize insights in Italian.

        Only aggregated stats are sent — no PII, no cost data.
        """
        from app.core.llm.model_registry import get_model_registry

        registry = get_model_registry()
        entry = registry.resolve_production_model()
        provider = entry.provider if entry else "mistral"
        model_name = entry.model_name if entry else "mistral-large-latest"

        system_prompt = (
            "Sei un analista esperto di PratikoAI, una piattaforma per "
            "consulenti fiscali e del lavoro italiani. Analizza le "
            "statistiche di utilizzo e genera consigli personalizzati. "
            "Non includere mai nomi, email, codici fiscali, o altri "
            "dati personali nel report. Rispondi in italiano."
        )

        user_prompt = (
            "Analizza queste statistiche di utilizzo e genera un report "
            "con 5 sezioni:\n"
            "1. Pattern comportamentali\n"
            "2. Competenza per dominio\n"
            "3. Qualità dell'interazione\n"
            "4. Lacune di conoscenza\n"
            "5. Ottimizzazione del workflow\n\n"
            f"Statistiche:\n"
            f"- Query totali: {stats['total_queries']}\n"
            f"- Giorni attivi: {stats['active_days']} su {stats['history_days']}\n"
            f"- Sessioni: {stats['session_count']}\n"
            f"- Distribuzione domini: {stats['domain_distribution']}\n"
            f"- Ore più attive: {stats['hourly_distribution']}\n"
            f"- Tasso cache: {stats['cache_hit_rate']:.0%}\n"
            f"- Fonti KB usate: {', '.join(stats['kb_sources_used']) or 'nessuna'}\n\n"
            "Per ogni sezione fornisci: osservazione + suggerimento concreto. "
            "Usa un tono professionale e diretto."
        )

        try:
            if provider == "mistral":
                from mistralai import Mistral

                from app.core.config import settings

                client = Mistral(api_key=settings.MISTRAL_API_KEY)
                response = await client.chat.complete_async(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
                return response.choices[0].message.content or ""
            else:
                logger.warning(
                    "consigli_unsupported_provider",
                    provider=provider,
                )
                return self._generate_fallback_analysis(stats)
        except Exception as e:
            logger.error(
                "consigli_llm_call_failed",
                error=str(e),
                provider=provider,
                model=model_name,
            )
            return self._generate_fallback_analysis(stats)

    def _generate_fallback_analysis(self, stats: dict) -> str:
        """Generate basic analysis without LLM (fallback)."""
        top_domain = max(
            stats["domain_distribution"],
            key=stats["domain_distribution"].get,
            default="general",
        )
        return (
            f"Hai effettuato {stats['total_queries']} interazioni in "
            f"{stats['history_days']} giorni, con {stats['active_days']} "
            f"giorni attivi. L'area tematica più frequente è "
            f"'{top_domain}'. Il tasso di cache è del "
            f"{stats['cache_hit_rate']:.0%}."
        )

    async def generate_report(self, user_id: int, db: AsyncSession) -> dict:
        """Generate the full insight report."""
        # RC-4: Concurrency guard
        redis = await get_redis_client()
        lock_key = f"consigli:generating:{user_id}"

        if redis:
            existing = await redis.get(lock_key)
            if existing:
                return {
                    "status": "generating",
                    "message_it": "Un report è in fase di generazione. Attendere il completamento.",
                    "html_report": None,
                }

        sufficiency = await self.can_generate(user_id, db)
        if not sufficiency["can_generate"]:
            return {
                "status": "insufficient_data",
                "message_it": sufficiency["message_it"],
                "html_report": None,
            }

        if redis:
            await redis.setex(lock_key, LOCK_TTL_SECONDS, "1")

        try:
            stats = await self.collect_stats(user_id, db)
            llm_text = await self._call_llm_analysis(stats)

            # R-4: Anonymize LLM output as safety net
            anon_result = anonymizer.anonymize_text(llm_text)
            safe_text = anon_result.anonymized_text

            html = render_report_html(stats, safe_text)

            logger.info(
                "consigli_report_generated",
                user_id=user_id,
                total_queries=stats["total_queries"],
                history_days=stats["history_days"],
            )

            return {
                "status": "success",
                "message_it": "Report generato con successo.",
                "html_report": html,
                "stats_summary": {
                    "total_queries": stats["total_queries"],
                    "active_days": stats["active_days"],
                    "session_count": stats["session_count"],
                },
            }
        except Exception as e:
            logger.error(
                "consigli_report_failed",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "status": "error",
                "message_it": "Errore nella generazione del report. Riprova più tardi.",
                "html_report": None,
            }
        finally:
            if redis:
                await redis.delete(lock_key)


# --- Module-level rendering helpers (extracted for code size compliance) ---


def _domain_label(domain: str) -> str:
    """Map internal domain keys to Italian labels."""
    labels = {
        "tax_calculation": "Calcolo fiscale",
        "document_analysis": "Analisi documenti",
        "labor_question": "Diritto del lavoro",
        "general": "Domande generali",
        "ccnl": "CCNL",
        "deadline": "Scadenze",
        "procedura": "Procedure",
    }
    return labels.get(domain, domain.replace("_", " ").title())


def _escape(text: str) -> str:
    """HTML-escape text to prevent XSS from LLM output."""
    return html_mod.escape(text, quote=True)


def _text_to_html(text: str) -> str:
    """Convert plain/markdown text to HTML paragraphs with XSS protection."""
    lines = text.strip().split("\n")
    html_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Escape first, then apply safe markdown transformations
        safe_line = _escape(line)
        # Bold **text** (applied on escaped text — safe)
        safe_line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_line)
        if safe_line.startswith("### "):
            html_parts.append(f"<h4>{safe_line[4:]}</h4>")
        elif safe_line.startswith("## "):
            html_parts.append(f"<h3>{safe_line[3:]}</h3>")
        elif safe_line.startswith("# "):
            html_parts.append(f"<h3>{safe_line[2:]}</h3>")
        elif safe_line.startswith("- ") or safe_line.startswith("* "):
            html_parts.append(f"<p>&bull; {safe_line[2:]}</p>")
        else:
            html_parts.append(f"<p>{safe_line}</p>")
    return "\n".join(html_parts)


def _prepare_domain_rows(stats: dict) -> str:
    """Build HTML table rows for domain distribution."""
    total_q = stats["total_queries"] or 1
    rows = ""
    for domain, count in sorted(
        stats["domain_distribution"].items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        pct = count / total_q * 100
        label = _escape(_domain_label(domain))
        rows += f"<tr><td>{label}</td><td>{count}</td><td>{pct:.0f}%</td></tr>\n"
    return rows


def _prepare_peak_hours(stats: dict) -> str:
    """Extract top 3 peak hours as a display string."""
    peak_hours = sorted(
        stats["hourly_distribution"].items(),
        key=lambda x: int(x[1]),
        reverse=True,
    )[:3]
    return ", ".join(f"{h}:00" for h, _ in peak_hours) or "N/D"


def render_report_html(stats: dict, llm_analysis: str) -> str:
    """Render self-contained HTML report from stats and LLM analysis."""
    now = datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    domain_rows = _prepare_domain_rows(stats)
    peak_str = _prepare_peak_hours(stats)
    analysis_html = _text_to_html(llm_analysis)
    kb_str = _escape(", ".join(stats["kb_sources_used"]) or "Nessuna specifica")

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PratikoAI — Consigli Personalizzati</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#F8F5F1;color:#2D2A26;line-height:1.6;padding:2rem}}
.container{{max-width:800px;margin:0 auto}}
header{{text-align:center;padding:2rem 0;border-bottom:2px solid #C4BDB4}}
header h1{{color:#8B7355;font-size:1.5rem;margin-bottom:.5rem}}
header p{{color:#6B6560;font-size:.9rem}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:1rem;margin:1.5rem 0}}
.stat-card{{background:white;border-radius:12px;padding:1.2rem;text-align:center;
border:1px solid #E8E2DB}}
.stat-card .value{{font-size:1.8rem;font-weight:700;color:#8B7355}}
.stat-card .label{{font-size:.8rem;color:#6B6560;margin-top:.3rem}}
section{{background:white;border-radius:12px;padding:1.5rem;margin:1.5rem 0;
border:1px solid #E8E2DB}}
section h2{{color:#8B7355;font-size:1.1rem;margin-bottom:1rem;
border-bottom:1px solid #E8E2DB;padding-bottom:.5rem}}
table{{width:100%;border-collapse:collapse;margin:.5rem 0}}
th,td{{padding:.5rem;text-align:left;border-bottom:1px solid #F0EBE5}}
th{{color:#6B6560;font-size:.8rem;text-transform:uppercase}}
.analysis p{{margin-bottom:.8rem}}
.analysis strong{{color:#8B7355}}
footer{{text-align:center;padding:1.5rem 0;color:#A09890;font-size:.8rem;
border-top:1px solid #E8E2DB;margin-top:2rem}}
@media print{{body{{padding:.5rem}}
.container{{max-width:100%}}}}
</style>
</head>
<body>
<div class="container">
<header>
<h1>PratikoAI — Report Consigli Personalizzati</h1>
<p>Analisi delle tue interazioni degli ultimi 90 giorni</p>
</header>

<div class="stats-grid">
<div class="stat-card">
<div class="value">{stats["total_queries"]}</div>
<div class="label">Interazioni totali</div>
</div>
<div class="stat-card">
<div class="value">{stats["active_days"]}</div>
<div class="label">Giorni attivi</div>
</div>
<div class="stat-card">
<div class="value">{stats["session_count"]}</div>
<div class="label">Sessioni</div>
</div>
<div class="stat-card">
<div class="value">{stats["cache_hit_rate"]:.0%}</div>
<div class="label">Risposte rapide</div>
</div>
</div>

<section>
<h2>Distribuzione per Area Tematica</h2>
<table>
<thead><tr><th>Area</th><th>Interazioni</th><th>%</th></tr></thead>
<tbody>{domain_rows}</tbody>
</table>
</section>

<section>
<h2>Orari di Maggiore Attivit&agrave;</h2>
<p>Le tue ore pi&ugrave; attive: <strong>{peak_str}</strong></p>
<p>Fonti di conoscenza utilizzate: <strong>{kb_str}</strong></p>
</section>

<section>
<h2>Analisi e Consigli Personalizzati</h2>
<div class="analysis">{analysis_html}</div>
</section>

<footer>
Generato il {now} &mdash; Dati degli ultimi 90 giorni<br>
PratikoAI &copy; 2026
</footer>
</div>
</body>
</html>"""


consigli_service = ConsigliService()
