"""Wave 4: API Layer + Advanced Services.

DEV-315: Add studio_id to user table
DEV-336: Communication templates table
DEV-376: Processing register table
DEV-341: Seed 10 pre-configured procedures (P001-P010)

Revision ID: wave4_20260227
Revises: (previous migration)
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from alembic import op

revision = "wave4_20260227"
down_revision = "add_wave3_20260226"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # DEV-315: Add studio_id to user table
    user_columns = [c["name"] for c in inspector.get_columns("user")]
    if "studio_id" not in user_columns:
        op.add_column("user", sa.Column("studio_id", sa.String(36), nullable=True))
        op.create_index("ix_user_studio_id", "user", ["studio_id"])

    # DEV-336: Communication templates
    if not inspector.has_table("communication_templates"):
        op.create_table(
            "communication_templates",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("studio_id", sa.Uuid(), sa.ForeignKey("studios.id"), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("subject_template", sa.String(300), nullable=False),
            sa.Column("content_template", sa.Text(), nullable=False),
            sa.Column("channel", sa.String(15), nullable=False),
            sa.Column("category", sa.String(50), nullable=False, server_default="generale"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_comm_templates_studio_active", "communication_templates", ["studio_id", "is_active"])
        op.create_index("ix_comm_templates_category", "communication_templates", ["category"])

    # DEV-376: Processing register
    if not inspector.has_table("processing_register"):
        op.create_table(
            "processing_register",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("studio_id", sa.Uuid(), sa.ForeignKey("studios.id"), nullable=False),
            sa.Column("activity_name", sa.String(300), nullable=False),
            sa.Column("purpose", sa.Text(), nullable=False),
            sa.Column("legal_basis", sa.String(100), nullable=False),
            sa.Column("data_categories", ARRAY(sa.String(100)), nullable=False),
            sa.Column("data_subjects", sa.String(200), nullable=False),
            sa.Column("retention_period", sa.String(100), nullable=False),
            sa.Column("recipients", ARRAY(sa.String(200)), nullable=True),
            sa.Column("third_country_transfers", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_processing_register_studio", "processing_register", ["studio_id"])
        op.create_index("ix_processing_register_legal_basis", "processing_register", ["legal_basis"])

    # DEV-343/DEV-344: Add checklist_state and document_status to procedura_progress
    pp_columns = [c["name"] for c in inspector.get_columns("procedura_progress")]
    if "checklist_state" not in pp_columns:
        op.add_column(
            "procedura_progress",
            sa.Column("checklist_state", JSONB, nullable=False, server_default="{}"),
        )
    if "document_status" not in pp_columns:
        op.add_column(
            "procedura_progress",
            sa.Column("document_status", JSONB, nullable=False, server_default="{}"),
        )

    _seed_procedures(conn)


def _seed_procedures(conn) -> None:
    import json

    result = conn.execute(sa.text("SELECT code FROM procedure WHERE code LIKE 'P0%' LIMIT 1"))
    if result.fetchone() is not None:
        return

    procedures = [
        {
            "code": "P001",
            "title": "Apertura attivit\u00e0 artigiano",
            "description": "Procedura per apertura attivit\u00e0 artigianale (AdE, CCIAA, INPS, INAIL, ISTAT).",
            "category": "fiscale",
            "estimated_time_minutes": 180,
            "steps": json.dumps(
                [
                    {
                        "title": "Apertura Partita IVA",
                        "description": "Modello AA9/12 all'AdE",
                        "checklist": ["Compilare AA9/12", "Codice ATECO", "Regime fiscale"],
                        "documents": ["Documento identit\u00e0", "Codice fiscale"],
                    },
                    {
                        "title": "Iscrizione CCIAA",
                        "description": "Camera di Commercio via ComUnica",
                        "checklist": ["Pratica ComUnica", "Diritti camerali"],
                        "documents": ["Pratica ComUnica"],
                    },
                    {
                        "title": "Iscrizione INPS Artigiani",
                        "description": "Gestione artigiani INPS",
                        "checklist": ["Modulo iscrizione", "Contributi minimi"],
                        "documents": ["Modulo INPS"],
                    },
                    {
                        "title": "Iscrizione INAIL",
                        "description": "Denuncia esercizio INAIL",
                        "checklist": ["Denuncia esercizio", "Premio assicurativo"],
                        "documents": ["Denuncia INAIL"],
                    },
                    {
                        "title": "Comunicazione ISTAT",
                        "description": "Comunicazione statistica",
                        "checklist": ["Verifica obbligo"],
                        "documents": ["Modulo ISTAT"],
                    },
                ]
            ),
        },
        {
            "code": "P002",
            "title": "Apertura attivit\u00e0 commerciale",
            "description": "Procedura per apertura commerciale (AdE, CCIAA, INPS, SCIA Comune).",
            "category": "fiscale",
            "estimated_time_minutes": 180,
            "steps": json.dumps(
                [
                    {
                        "title": "Apertura Partita IVA",
                        "description": "AA9/12 all'AdE",
                        "checklist": ["Compilare AA9/12", "ATECO commerciale"],
                        "documents": ["Documento identit\u00e0"],
                    },
                    {
                        "title": "SCIA al Comune",
                        "description": "Segnalazione Certificata Inizio Attivit\u00e0",
                        "checklist": ["Modulo SCIA", "Requisiti urbanistici", "Presentare al SUAP"],
                        "documents": ["Modulo SCIA", "Planimetria"],
                    },
                    {
                        "title": "Iscrizione CCIAA",
                        "description": "Registro Imprese",
                        "checklist": ["ComUnica", "Diritti camerali"],
                        "documents": ["ComUnica"],
                    },
                    {
                        "title": "Iscrizione INPS Commercianti",
                        "description": "Gestione commercianti",
                        "checklist": ["Modulo iscrizione"],
                        "documents": ["Modulo INPS"],
                    },
                ]
            ),
        },
        {
            "code": "P003",
            "title": "Apertura studio professionale",
            "description": "Apertura studio professionale (AdE, Ordine, INPS GS).",
            "category": "fiscale",
            "estimated_time_minutes": 120,
            "steps": json.dumps(
                [
                    {
                        "title": "Apertura Partita IVA",
                        "description": "AA9/12 professionale",
                        "checklist": ["AA9/12", "Regime fiscale"],
                        "documents": ["Documento identit\u00e0"],
                    },
                    {
                        "title": "Iscrizione Ordine",
                        "description": "Albo professionale",
                        "checklist": ["Domanda Ordine", "Quota iscrizione"],
                        "documents": ["Titolo studio"],
                    },
                    {
                        "title": "INPS Gestione Separata",
                        "description": "Gestione separata professionisti",
                        "checklist": ["Modulo GS", "Aliquota contributiva"],
                        "documents": ["Modulo GS"],
                    },
                ]
            ),
        },
        {
            "code": "P004",
            "title": "Domanda pensione vecchiaia",
            "description": "Domanda pensione vecchiaia INPS.",
            "category": "previdenza",
            "estimated_time_minutes": 90,
            "steps": json.dumps(
                [
                    {
                        "title": "Verifica requisiti",
                        "description": "Et\u00e0 e contributi",
                        "checklist": ["Et\u00e0 67 anni", "20 anni contributi", "Estratto conto"],
                        "documents": ["Estratto conto INPS"],
                    },
                    {
                        "title": "Documentazione",
                        "description": "Raccolta documenti",
                        "checklist": ["Documento identit\u00e0", "Codice fiscale", "CUD"],
                        "documents": ["Documento identit\u00e0", "CUD"],
                    },
                    {
                        "title": "Presentazione domanda",
                        "description": "Invio telematico INPS",
                        "checklist": ["Domanda online", "Allegare documenti", "Conservare ricevuta"],
                        "documents": ["Domanda pensione"],
                    },
                ]
            ),
        },
        {
            "code": "P005",
            "title": "Domanda pensione anticipata",
            "description": "Pensione anticipata con requisito contributivo.",
            "category": "previdenza",
            "estimated_time_minutes": 90,
            "steps": json.dumps(
                [
                    {
                        "title": "Verifica contributi",
                        "description": "42a 10m uomini / 41a 10m donne",
                        "checklist": ["Estratto conto", "Anni contribuzione", "Riscatti"],
                        "documents": ["Estratto conto"],
                    },
                    {
                        "title": "Documentazione",
                        "description": "Preparazione documenti",
                        "checklist": ["Documento identit\u00e0", "Documentazione contributiva"],
                        "documents": ["Documento identit\u00e0"],
                    },
                    {
                        "title": "Presentazione domanda",
                        "description": "Invio INPS",
                        "checklist": ["Domanda portale", "Finestra decorrenza", "Ricevuta"],
                        "documents": ["Domanda pensione anticipata"],
                    },
                ]
            ),
        },
        {
            "code": "P006",
            "title": "Assunzione dipendente",
            "description": "Assunzione nuovo dipendente (INPS, INAIL, Centro Impiego).",
            "category": "lavoro",
            "estimated_time_minutes": 120,
            "steps": json.dumps(
                [
                    {
                        "title": "Comunicazione Unilav",
                        "description": "Centro Impiego entro giorno precedente",
                        "checklist": ["Modello Unilav", "Tipo contratto/CCNL", "Invio tempestivo"],
                        "documents": ["Unilav", "Contratto"],
                    },
                    {
                        "title": "Registrazione INPS",
                        "description": "Posizione contributiva",
                        "checklist": ["Posizione INPS", "Registrare dipendente"],
                        "documents": ["Dati dipendente"],
                    },
                    {
                        "title": "Registrazione INAIL",
                        "description": "Variazione rischio",
                        "checklist": ["Classificazione rischio", "Aggiornare INAIL"],
                        "documents": ["Denuncia INAIL"],
                    },
                    {
                        "title": "Adempimenti aziendali",
                        "description": "LUL e documenti",
                        "checklist": ["Aggiornare LUL", "Copia contratto", "Privacy GDPR"],
                        "documents": ["Contratto firmato", "Informativa privacy"],
                    },
                ]
            ),
        },
        {
            "code": "P007",
            "title": "Trasformazione regime fiscale",
            "description": "Cambio regime fiscale (forfettario/ordinario).",
            "category": "fiscale",
            "estimated_time_minutes": 60,
            "steps": json.dumps(
                [
                    {
                        "title": "Verifica requisiti",
                        "description": "Requisiti nuovo regime",
                        "checklist": ["Limiti fatturato", "Requisiti soggettivi", "Convenienza economica"],
                        "documents": ["Dichiarazione redditi"],
                    },
                    {
                        "title": "Comunicazione AdE",
                        "description": "Variazione dati",
                        "checklist": ["AA9/12 variazione", "Invio telematico"],
                        "documents": ["AA9/12 variazione"],
                    },
                    {
                        "title": "Aggiornamento contabilit\u00e0",
                        "description": "Adeguare sistema contabile",
                        "checklist": ["Software contabile", "Obblighi IVA"],
                        "documents": [],
                    },
                ]
            ),
        },
        {
            "code": "P008",
            "title": "Chiusura attivit\u00e0",
            "description": "Chiusura completa attivit\u00e0 (AdE, CCIAA, INPS, INAIL).",
            "category": "fiscale",
            "estimated_time_minutes": 180,
            "steps": json.dumps(
                [
                    {
                        "title": "Chiusura P.IVA",
                        "description": "Cessazione AdE",
                        "checklist": ["AA9/12 cessazione", "IVA finale"],
                        "documents": ["AA9/12 cessazione"],
                    },
                    {
                        "title": "Cancellazione CCIAA",
                        "description": "Registro Imprese",
                        "checklist": ["Pratica cancellazione", "Diritti segreteria"],
                        "documents": ["Pratica cancellazione"],
                    },
                    {
                        "title": "Chiusura INPS",
                        "description": "Cessazione gestioni",
                        "checklist": ["Comunicazione cessazione", "Contributi residui"],
                        "documents": ["Comunicazione INPS"],
                    },
                    {
                        "title": "Chiusura INAIL",
                        "description": "Cessazione INAIL",
                        "checklist": ["Denuncia cessazione", "Regolazione premio"],
                        "documents": ["Denuncia cessazione"],
                    },
                    {
                        "title": "Adempimenti finali",
                        "description": "Dichiarazioni finali",
                        "checklist": ["IVA finale", "Redditi cessazione", "Conservazione 10 anni"],
                        "documents": [],
                    },
                ]
            ),
        },
        {
            "code": "P009",
            "title": "Variazione dati azienda",
            "description": "Variazione dati aziendali (sede, denominazione) presso AdE e CCIAA.",
            "category": "fiscale",
            "estimated_time_minutes": 60,
            "steps": json.dumps(
                [
                    {
                        "title": "Variazione AdE",
                        "description": "Comunicazione variazione",
                        "checklist": ["AA9/12 variazione", "Dati modificati"],
                        "documents": ["AA9/12 variazione"],
                    },
                    {
                        "title": "Variazione CCIAA",
                        "description": "Aggiornamento RI",
                        "checklist": ["Pratica variazione", "ComUnica"],
                        "documents": ["ComUnica variazione"],
                    },
                ]
            ),
        },
        {
            "code": "P010",
            "title": "Iscrizione gestione separata INPS",
            "description": "Iscrizione GS INPS per collaboratori/professionisti senza cassa.",
            "category": "previdenza",
            "estimated_time_minutes": 45,
            "steps": json.dumps(
                [
                    {
                        "title": "Verifica obbligo",
                        "description": "Obbligo iscrizione GS",
                        "checklist": ["Assenza cassa professionale", "Tipo rapporto"],
                        "documents": ["Documentazione attivit\u00e0"],
                    },
                    {
                        "title": "Iscrizione online",
                        "description": "Portale INPS",
                        "checklist": ["SPID/CIE", "Domanda iscrizione", "Data inizio"],
                        "documents": ["Credenziali SPID"],
                    },
                    {
                        "title": "Verifica",
                        "description": "Conferma iscrizione",
                        "checklist": ["Ricevuta iscrizione", "Aliquota applicata"],
                        "documents": ["Ricevuta"],
                    },
                ]
            ),
        },
    ]

    for proc in procedures:
        # Check if this specific code already exists (safe for partial re-runs)
        exists = conn.execute(
            sa.text("SELECT 1 FROM procedure WHERE code = :code"),
            {"code": proc["code"]},
        ).fetchone()
        if exists:
            continue

        conn.execute(
            sa.text(
                "INSERT INTO procedure (id, code, title, description, category, steps, estimated_time_minutes, version, is_active) "
                "VALUES (:id, :code, :title, :description, :category, :steps::jsonb, :estimated_time_minutes, 1, true)"
            ),
            {
                "id": str(uuid.uuid4()),
                "code": proc["code"],
                "title": proc["title"],
                "description": proc["description"],
                "category": proc["category"],
                "steps": proc["steps"],
                "estimated_time_minutes": proc["estimated_time_minutes"],
            },
        )


def downgrade() -> None:
    op.drop_index("ix_processing_register_legal_basis", table_name="processing_register")
    op.drop_index("ix_processing_register_studio", table_name="processing_register")
    op.drop_table("processing_register")
    op.drop_index("ix_comm_templates_category", table_name="communication_templates")
    op.drop_index("ix_comm_templates_studio_active", table_name="communication_templates")
    op.drop_table("communication_templates")
    op.drop_index("ix_user_studio_id", table_name="user")
    op.drop_column("user", "studio_id")
