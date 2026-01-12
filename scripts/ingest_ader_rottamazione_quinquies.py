#!/usr/bin/env python3
"""Ingest AdER official rules for Rottamazione Quinquies.

This script ingests the official rules published by Agenzia delle Entrate-Riscossione
for the Rottamazione Quinquies (Definizione Agevolata 2026).

DEV-242 Phase 29A: This content is NOT in Gazzetta Ufficiale and provides critical
operational details like the 5-day grace period rule.

Usage:
    python scripts/ingest_ader_rottamazione_quinquies.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.document_ingestion import ingest_document_with_chunks
from app.models.knowledge import KnowledgeItem

# Official AdER content for Rottamazione Quinquies
# Source: https://www.agenziaentrateriscossione.gov.it/it/il-gruppo/lagenzia-comunica/novita/Legge-di-Bilancio-2026-in-arrivo-la-Rottamazione-quinquies/
ADER_ROTTAMAZIONE_QUINQUIES_CONTENT = """
ROTTAMAZIONE QUINQUIES - REGOLE UFFICIALI ADER
Agenzia delle Entrate-Riscossione - Definizione Agevolata 2026

NORMATIVA DI RIFERIMENTO
La Rottamazione Quinquies è disciplinata dalla Legge n. 199/2025 (Legge di Bilancio 2026),
pubblicata sul supplemento ordinario n. 42 alla Gazzetta Ufficiale n. 301 del 30 dicembre 2025.

AMBITO DI APPLICAZIONE
La Rottamazione Quinquies riguarda i debiti risultanti dai carichi affidati agli agenti
della riscossione nel periodo dal 1° gennaio 2000 al 31 dicembre 2023, derivanti da:
- Omesso versamento di imposte e tributi
- Omesso versamento di contributi previdenziali INPS
- Altre somme affidate all'Agenzia delle Entrate-Riscossione

BENEFICI PER IL CONTRIBUENTE
Chi aderisce alla Rottamazione Quinquies può estinguere il proprio debito versando:
- Capitale originario dovuto
- Rimborso spese per procedure esecutive e notificazione cartelle

SENZA corrispondere:
- Sanzioni
- Interessi di mora
- Aggio di riscossione

TASSI DI INTERESSE PER IL PAGAMENTO RATEALE
In caso di pagamento rateale, sono dovuti interessi al tasso del 3 per cento annuo
(3% annuo), a decorrere dal 1° agosto 2026. Per il pagamento in unica soluzione
entro il 31 luglio 2026, NON sono dovuti interessi.

MODALITÀ DI PAGAMENTO
1) PAGAMENTO IN UNICA SOLUZIONE
   - Scadenza: entro il 31 luglio 2026
   - Nessun interesse applicato

2) PAGAMENTO RATEALE
   - Massimo 54 rate bimestrali di pari importo (9 anni)
   - Importo minimo per rata: 100 euro
   - Interessi: 3% annuo dal 1° agosto 2026

SCADENZE RATE (pagamento rateale):
- 1ª rata: 31 luglio 2026
- 2ª rata: 30 settembre 2026
- 3ª rata: 30 novembre 2026
- Rate successive: 31 gennaio, 31 marzo, 31 maggio, 31 luglio, 30 settembre, 30 novembre di ogni anno
- Ultime rate 2035: 31 gennaio 2035, 31 marzo 2035, 31 maggio 2035

PRESENTAZIONE DELLA DOMANDA
- Scadenza: entro il 30 aprile 2026
- Modalità: esclusivamente telematica sul sito dell'Agenzia delle Entrate-Riscossione
- Comunicazione importi: entro il 30 giugno 2026, l'AdER comunica l'ammontare delle somme dovute

DECADENZA DAL BENEFICIO
La Rottamazione Quinquies risulterà inefficace (decadenza) in caso di:

a) Mancato o insufficiente versamento dell'UNICA RATA scelta per il pagamento in soluzione unica
   (scadenza 31 luglio 2026)

b) Per il pagamento RATEALE, mancato o insufficiente versamento di:
   - DUE RATE, anche non consecutive
   - L'ULTIMA RATA del piano di pagamento

IMPORTANTE: In caso di decadenza, i versamenti già effettuati sono acquisiti a titolo di
ACCONTO sulle somme complessivamente dovute, senza estinzione del debito residuo.

GIORNI DI TOLLERANZA
ATTENZIONE: Per la Rottamazione Quinquies NON sono previsti i 5 giorni di tolleranza
che erano concessi nelle precedenti definizioni agevolate (Rottamazione-ter e Rottamazione-quater).
I pagamenti devono essere effettuati ESATTAMENTE entro le scadenze indicate, senza alcun
margine di tolleranza.

CHI PUÒ ADERIRE
Possono aderire alla Rottamazione Quinquies:
- Contribuenti con debiti nel periodo 1/1/2000 - 31/12/2023
- Contribuenti decaduti da precedenti rottamazioni (ter, quater) purché i carichi rientrino
  nell'ambito applicativo della quinquies

ESCLUSIONI
NON possono aderire alla Rottamazione Quinquies:
- Debiti già inclusi in piani di Rottamazione-quater in regola al 30 settembre 2025
  (ossia con tutte le rate scadute regolarmente versate)

SOSPENSIONE ATTIVITÀ DI RISCOSSIONE
Dalla presentazione della domanda fino alla scadenza della prima/unica rata:
- Sono sospesi i termini di prescrizione e decadenza
- Sono sospese le procedure esecutive già avviate
- È sospeso l'obbligo di versamento delle rate di dilazioni in corso

FONTE: Agenzia delle Entrate-Riscossione
URL: https://www.agenziaentrateriscossione.gov.it/it/il-gruppo/lagenzia-comunica/novita/Legge-di-Bilancio-2026-in-arrivo-la-Rottamazione-quinquies/
Data pubblicazione: Gennaio 2026
"""


async def check_existing(session: AsyncSession, url: str) -> bool:
    """Check if document already exists."""
    result = await session.execute(select(KnowledgeItem).where(KnowledgeItem.source_url == url))
    return result.scalar_one_or_none() is not None


async def ingest_ader_content(session: AsyncSession) -> bool:
    """Ingest AdER official rules content."""
    url = "https://www.agenziaentrateriscossione.gov.it/it/il-gruppo/lagenzia-comunica/novita/Legge-di-Bilancio-2026-in-arrivo-la-Rottamazione-quinquies/"
    title = "Rottamazione Quinquies - Regole Ufficiali AdER (Agenzia Entrate-Riscossione)"

    # Check if already exists
    if await check_existing(session, url):
        print(f"⚠️  Document already exists: {url}")
        print("   Skipping ingestion. Delete first if you want to re-ingest.")
        return False

    print("📝 Ingesting AdER Rottamazione Quinquies rules...")
    print(f"   Title: {title}")
    print(f"   Content length: {len(ADER_ROTTAMAZIONE_QUINQUIES_CONTENT):,} characters")

    result = await ingest_document_with_chunks(
        session=session,
        title=title,
        url=url,
        content=ADER_ROTTAMAZIONE_QUINQUIES_CONTENT,
        extraction_method="manual_ader_rules",
        text_quality=1.0,  # High quality manual content
        ocr_pages=[],
        source="agenzia_entrate_riscossione",
        category="regulatory_documents",
        subcategory="definizione_agevolata",
    )

    if result:
        print(f"✅ Successfully ingested with ID: {result}")
        return True
    else:
        print("❌ Failed to ingest document")
        return False


async def main():
    """Main function."""
    # Convert sync URL to async URL
    postgres_url = settings.POSTGRES_URL
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            print("=" * 80)
            print("AdER Rottamazione Quinquies Rules Ingestion")
            print("DEV-242 Phase 29A")
            print("=" * 80)

            success = await ingest_ader_content(session)

            print()
            print("=" * 80)
            if success:
                print("✅ Ingestion completed successfully!")
                print("   The 5-day grace period rule and 3% interest rate info is now in KB.")
            else:
                print("⚠️  Ingestion skipped or failed.")
            print("=" * 80)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
