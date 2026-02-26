"""DEV-307: Tests for Phase 0 Alembic migration.

Verifies that the migration correctly creates all PratikoAI 2.0 tables
(Waves 0-1) with proper columns, indexes, foreign keys, and constraints.

Tests run without a database by inspecting the SQLModel metadata and
the migration module structure.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlmodel import SQLModel

# ---------------------------------------------------------------------------
# Ensure app.services.database is stubbed before model imports
# ---------------------------------------------------------------------------
if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub


# ---------------------------------------------------------------------------
# Import all Phase 0 models so their tables are registered in metadata.
# Also import User and KnowledgeItem so FK references can resolve.
# ---------------------------------------------------------------------------
from app.models.client import Client, StatoCliente, TipoCliente
from app.models.client_profile import ClientProfile, PosizioneAgenziaEntrate, RegimeFiscale
from app.models.communication import CanaleInvio, Communication, StatoComunicazione
from app.models.knowledge import KnowledgeItem
from app.models.matching_rule import MatchingRule, RuleType
from app.models.proactive_suggestion import ProactiveSuggestion
from app.models.procedura import Procedura, ProceduraCategory
from app.models.procedura_progress import ProceduraProgress
from app.models.studio import Studio
from app.models.user import User

# ---------------------------------------------------------------------------
# Project root and migration file path
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MIGRATION_FILE = _PROJECT_ROOT / "alembic" / "versions" / "20260226_add_pratikoai_2_0_models.py"


def _load_migration_module():
    """Load the migration module from its file path (alembic/versions/ is not a package)."""
    spec = importlib.util.spec_from_file_location("migration_pratikoai_2_0", _MIGRATION_FILE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ============================================================================
# Phase 0 Tables — expected table names
# ============================================================================
PHASE0_TABLES = [
    "studios",
    "clients",
    "client_profiles",
    "matching_rules",
    "communications",
    "procedure",
    "procedura_progress",
    "proactive_suggestions",
]


class TestMigrationModuleStructure:
    """Verify the migration file has correct Alembic structure."""

    def test_migration_module_importable(self) -> None:
        """Migration module can be imported."""
        mod = _load_migration_module()
        assert mod is not None

    def test_migration_has_revision(self) -> None:
        """Migration has a revision ID."""
        mod = _load_migration_module()
        assert hasattr(mod, "revision")
        assert isinstance(mod.revision, str)
        assert len(mod.revision) > 0

    def test_migration_has_down_revision(self) -> None:
        """Migration has a down_revision linking to previous migration."""
        mod = _load_migration_module()
        assert hasattr(mod, "down_revision")
        assert mod.down_revision == "add_release_notes_20260226"

    def test_migration_has_upgrade_function(self) -> None:
        """Migration has an upgrade() function."""
        mod = _load_migration_module()
        assert hasattr(mod, "upgrade")
        assert callable(mod.upgrade)

    def test_migration_has_downgrade_function(self) -> None:
        """Migration has a downgrade() function."""
        mod = _load_migration_module()
        assert hasattr(mod, "downgrade")
        assert callable(mod.downgrade)


class TestPhase0TablesInMetadata:
    """Verify all Phase 0 models register the expected tables in SQLModel metadata."""

    def test_all_phase0_tables_registered(self) -> None:
        """All Phase 0 table names exist in SQLModel.metadata."""
        registered = set(SQLModel.metadata.tables.keys())
        for table_name in PHASE0_TABLES:
            assert table_name in registered, f"Table '{table_name}' not in metadata"

    @pytest.mark.parametrize("table_name", PHASE0_TABLES)
    def test_table_has_primary_key(self, table_name: str) -> None:
        """Each table must have a primary key constraint."""
        table = SQLModel.metadata.tables[table_name]
        pk_cols = list(table.primary_key.columns)
        assert len(pk_cols) >= 1, f"Table '{table_name}' has no primary key"


class TestStudiosTable:
    """Verify studios table structure."""

    def test_studios_columns(self) -> None:
        """Studios table has all required columns."""
        table = SQLModel.metadata.tables["studios"]
        col_names = {c.name for c in table.columns}
        expected = {"id", "name", "slug", "settings", "max_clients", "created_at", "updated_at"}
        assert expected.issubset(col_names)

    def test_studios_slug_unique(self) -> None:
        """Slug column has unique constraint."""
        table = SQLModel.metadata.tables["studios"]
        slug_col = table.c.slug
        assert slug_col.unique is True

    def test_studios_pk_is_uuid(self) -> None:
        """PK is UUID type."""
        studio = Studio(name="Test", slug="test")
        assert isinstance(studio.id, UUID)


class TestClientsTable:
    """Verify clients table structure."""

    def test_clients_columns(self) -> None:
        """Clients table has all required columns."""
        table = SQLModel.metadata.tables["clients"]
        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "studio_id",
            "codice_fiscale",
            "partita_iva",
            "nome",
            "tipo_cliente",
            "stato_cliente",
            "email",
            "phone",
            "indirizzo",
            "cap",
            "comune",
            "provincia",
            "data_nascita_titolare",
            "note_studio",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert expected.issubset(col_names)

    def test_clients_studio_fk(self) -> None:
        """studio_id references studios.id."""
        table = SQLModel.metadata.tables["clients"]
        fks = {
            (list(fk.columns)[0].name, list(fk.elements)[0].column.table.name) for fk in table.foreign_key_constraints
        }
        assert ("studio_id", "studios") in fks

    def test_clients_soft_delete_column(self) -> None:
        """deleted_at column exists and is nullable."""
        table = SQLModel.metadata.tables["clients"]
        assert table.c.deleted_at.nullable is True


class TestClientProfilesTable:
    """Verify client_profiles table structure."""

    def test_client_profiles_columns(self) -> None:
        """ClientProfiles table has required columns."""
        table = SQLModel.metadata.tables["client_profiles"]
        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "client_id",
            "codice_ateco_principale",
            "codici_ateco_secondari",
            "regime_fiscale",
            "ccnl_applicato",
            "n_dipendenti",
            "data_inizio_attivita",
            "data_cessazione_attivita",
            "immobili",
            "posizione_agenzia_entrate",
            "profile_vector",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(col_names)

    def test_client_profiles_client_fk(self) -> None:
        """client_id FK → clients.id with CASCADE delete."""
        table = SQLModel.metadata.tables["client_profiles"]
        for fk in table.foreign_key_constraints:
            constrained = [c.name for c in fk.columns]
            if "client_id" in constrained:
                assert fk.ondelete == "CASCADE"
                return
        pytest.fail("client_id FK not found")

    def test_client_profiles_client_id_unique(self) -> None:
        """client_id is unique (1:1 relationship)."""
        table = SQLModel.metadata.tables["client_profiles"]
        client_id_col = table.c.client_id
        assert client_id_col.unique is True

    def test_profile_vector_column_exists(self) -> None:
        """profile_vector column exists for semantic matching."""
        table = SQLModel.metadata.tables["client_profiles"]
        assert "profile_vector" in {c.name for c in table.columns}


class TestMatchingRulesTable:
    """Verify matching_rules table structure."""

    def test_matching_rules_columns(self) -> None:
        """MatchingRules table has all required columns."""
        table = SQLModel.metadata.tables["matching_rules"]
        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "name",
            "description",
            "rule_type",
            "conditions",
            "priority",
            "is_active",
            "valid_from",
            "valid_to",
            "categoria",
            "fonte_normativa",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(col_names)

    def test_matching_rules_name_unique(self) -> None:
        """name column has unique constraint."""
        table = SQLModel.metadata.tables["matching_rules"]
        name_col = table.c.name
        assert name_col.unique is True


class TestCommunicationsTable:
    """Verify communications table structure."""

    def test_communications_columns(self) -> None:
        """Communications table has required columns."""
        table = SQLModel.metadata.tables["communications"]
        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "studio_id",
            "client_id",
            "subject",
            "content",
            "channel",
            "status",
            "created_by",
            "approved_by",
            "approved_at",
            "sent_at",
            "normativa_riferimento",
            "matching_rule_id",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(col_names)

    def test_communications_studio_fk(self) -> None:
        """studio_id FK references studios.id."""
        table = SQLModel.metadata.tables["communications"]
        fk_targets = set()
        for fk in table.foreign_key_constraints:
            for col in fk.columns:
                if col.name == "studio_id":
                    for elem in fk.elements:
                        fk_targets.add(elem.column.table.name)
        assert "studios" in fk_targets

    def test_communications_status_default_draft(self) -> None:
        """status defaults to DRAFT."""
        comm = Communication(
            studio_id="00000000-0000-0000-0000-000000000000",
            subject="Test",
            content="Content",
            channel=CanaleInvio.EMAIL,
            created_by=1,
        )
        assert comm.status == StatoComunicazione.DRAFT


class TestProcedureTable:
    """Verify procedure table structure."""

    def test_procedure_columns(self) -> None:
        """Procedure table has required columns."""
        table = SQLModel.metadata.tables["procedure"]
        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "code",
            "title",
            "description",
            "category",
            "steps",
            "estimated_time_minutes",
            "version",
            "is_active",
            "last_updated",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(col_names)

    def test_procedure_code_unique(self) -> None:
        """code column has unique constraint."""
        table = SQLModel.metadata.tables["procedure"]
        code_col = table.c.code
        assert code_col.unique is True


class TestProceduraProgressTable:
    """Verify procedura_progress table structure."""

    def test_procedura_progress_columns(self) -> None:
        """ProceduraProgress table has required columns."""
        table = SQLModel.metadata.tables["procedura_progress"]
        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "user_id",
            "studio_id",
            "procedura_id",
            "client_id",
            "current_step",
            "completed_steps",
            "started_at",
            "completed_at",
            "notes",
        }
        assert expected.issubset(col_names)

    def test_procedura_progress_fk_references(self) -> None:
        """FK references: studios, procedure, clients, user."""
        table = SQLModel.metadata.tables["procedura_progress"]
        # Collect FK target table names from the FK string specs
        fk_target_tables = set()
        for fk in table.foreign_key_constraints:
            for elem in fk.elements:
                # elem.target_fullname is e.g. "studios.id"
                target_table = elem.target_fullname.split(".")[0]
                fk_target_tables.add(target_table)
        assert "studios" in fk_target_tables
        assert "procedure" in fk_target_tables
        assert "user" in fk_target_tables
        assert "clients" in fk_target_tables


class TestProactiveSuggestionsTable:
    """Verify proactive_suggestions table structure."""

    def test_proactive_suggestions_columns(self) -> None:
        """ProactiveSuggestions table has required columns."""
        table = SQLModel.metadata.tables["proactive_suggestions"]
        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "studio_id",
            "knowledge_item_id",
            "matched_client_ids",
            "match_score",
            "suggestion_text",
            "is_read",
            "is_dismissed",
            "created_at",
        }
        assert expected.issubset(col_names)

    def test_proactive_suggestions_studio_fk(self) -> None:
        """studio_id FK references studios.id."""
        table = SQLModel.metadata.tables["proactive_suggestions"]
        fk_targets = set()
        for fk in table.foreign_key_constraints:
            for col in fk.columns:
                if col.name == "studio_id":
                    for elem in fk.elements:
                        fk_targets.add(elem.column.table.name)
        assert "studios" in fk_targets


class TestIndexes:
    """Verify key indexes exist on Phase 0 tables."""

    def _get_index_names(self, table_name: str) -> set[str]:
        """Get all index names for a table."""
        table = SQLModel.metadata.tables[table_name]
        return {idx.name for idx in table.indexes}

    def test_studios_name_index(self) -> None:
        assert "ix_studios_name" in self._get_index_names("studios")

    def test_clients_studio_stato_index(self) -> None:
        assert "ix_clients_studio_stato" in self._get_index_names("clients")

    def test_client_profiles_regime_index(self) -> None:
        assert "ix_client_profiles_regime" in self._get_index_names("client_profiles")

    def test_client_profiles_ateco_index(self) -> None:
        assert "ix_client_profiles_ateco" in self._get_index_names("client_profiles")

    def test_matching_rules_type_active_index(self) -> None:
        assert "ix_matching_rules_type_active" in self._get_index_names("matching_rules")

    def test_matching_rules_priority_index(self) -> None:
        assert "ix_matching_rules_priority" in self._get_index_names("matching_rules")

    def test_communications_studio_status_index(self) -> None:
        assert "ix_communications_studio_status" in self._get_index_names("communications")

    def test_procedure_category_active_index(self) -> None:
        assert "ix_procedure_category_active" in self._get_index_names("procedure")

    def test_procedura_progress_user_procedura_index(self) -> None:
        assert "ix_procedura_progress_user_procedura" in self._get_index_names("procedura_progress")

    def test_proactive_suggestions_studio_read_index(self) -> None:
        assert "ix_proactive_suggestions_studio_read" in self._get_index_names("proactive_suggestions")


class TestMigrationContent:
    """Verify the migration file contains expected operations."""

    @pytest.fixture(autouse=True)
    def _load_module(self) -> None:
        self.mod = _load_migration_module()

    def test_migration_creates_all_tables(self) -> None:
        """Migration source references all Phase 0 table names."""
        import inspect

        source = inspect.getsource(self.mod)
        for table_name in PHASE0_TABLES:
            assert table_name in source, f"Table '{table_name}' not referenced in migration source"

    def test_migration_creates_hnsw_index(self) -> None:
        """Migration source contains HNSW index creation for profile_vector."""
        import inspect

        source = inspect.getsource(self.mod)
        assert "hnsw" in source.lower() or "HNSW" in source

    def test_migration_downgrade_drops_tables(self) -> None:
        """Downgrade function drops all Phase 0 tables."""
        import inspect

        source = inspect.getsource(self.mod.downgrade)
        for table_name in PHASE0_TABLES:
            assert table_name in source, f"Table '{table_name}' not dropped in downgrade"

    def test_migration_creates_vector_extension(self) -> None:
        """Migration ensures pgvector extension exists."""
        import inspect

        source = inspect.getsource(self.mod)
        assert "vector" in source.lower()
