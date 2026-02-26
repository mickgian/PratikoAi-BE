"""DEV-305: Tests for Procedura SQLModel."""

from datetime import date

from app.models.procedura import Procedura, ProceduraCategory


class TestProceduraCreation:
    """Test Procedura model creation and field defaults."""

    def test_procedura_creation(self) -> None:
        """Valid procedura with all required fields."""
        procedura = Procedura(
            code="APERTURA_PIVA",
            title="Apertura Partita IVA",
            description="Procedura per apertura di nuova partita IVA",
            category=ProceduraCategory.FISCALE,
            steps=[
                {"step": 1, "title": "Raccolta documenti", "checklist": ["CI", "CF"]},
                {"step": 2, "title": "Invio telematico", "checklist": ["Modello AA9/12"]},
            ],
            estimated_time_minutes=120,
        )

        assert procedura.code == "APERTURA_PIVA"
        assert procedura.title == "Apertura Partita IVA"
        assert procedura.id is not None

    def test_procedura_category_enum(self) -> None:
        """All ProceduraCategory enum values are valid."""
        assert ProceduraCategory.FISCALE == "fiscale"
        assert ProceduraCategory.LAVORO == "lavoro"
        assert ProceduraCategory.SOCIETARIO == "societario"
        assert ProceduraCategory.PREVIDENZA == "previdenza"

    def test_procedura_steps_jsonb(self) -> None:
        """JSONB steps field stores structured step data."""
        steps = [
            {
                "step": 1,
                "title": "Verifica requisiti",
                "checklist": ["Età >= 18", "Residenza italiana"],
                "documents": ["CI", "CF"],
                "notes": "Verificare residenza",
            },
            {
                "step": 2,
                "title": "Compilazione modello",
                "checklist": ["AA9/12 compilato"],
                "documents": ["Modello AA9/12"],
                "notes": None,
            },
        ]
        procedura = Procedura(
            code="TEST_STEPS",
            title="Test",
            description="d",
            category=ProceduraCategory.FISCALE,
            steps=steps,
            estimated_time_minutes=60,
        )
        assert len(procedura.steps) == 2
        assert procedura.steps[0]["title"] == "Verifica requisiti"
        assert "CI" in procedura.steps[0]["documents"]

    def test_procedura_versioning(self) -> None:
        """Version defaults to 1 and can be incremented."""
        procedura = Procedura(
            code="VER",
            title="Versioned",
            description="d",
            category=ProceduraCategory.LAVORO,
            steps=[],
            estimated_time_minutes=30,
        )
        assert procedura.version == 1

        procedura.version = 2
        assert procedura.version == 2

    def test_procedura_is_active_default(self) -> None:
        """is_active defaults to True."""
        procedura = Procedura(
            code="ACTIVE",
            title="Active",
            description="d",
            category=ProceduraCategory.FISCALE,
            steps=[],
            estimated_time_minutes=10,
        )
        assert procedura.is_active is True

    def test_procedura_last_updated(self) -> None:
        """last_updated can be set."""
        procedura = Procedura(
            code="DATED",
            title="Dated",
            description="d",
            category=ProceduraCategory.PREVIDENZA,
            steps=[],
            estimated_time_minutes=10,
            last_updated=date(2026, 2, 1),
        )
        assert procedura.last_updated == date(2026, 2, 1)

    def test_procedura_code_uniqueness_attr(self) -> None:
        """Two proceduras can have different codes (uniqueness enforced at DB)."""
        p1 = Procedura(
            code="A",
            title="A",
            description="d",
            category=ProceduraCategory.FISCALE,
            steps=[],
            estimated_time_minutes=10,
        )
        p2 = Procedura(
            code="B",
            title="B",
            description="d",
            category=ProceduraCategory.FISCALE,
            steps=[],
            estimated_time_minutes=10,
        )
        assert p1.code != p2.code

    def test_procedura_repr(self) -> None:
        """__repr__ includes code and title."""
        procedura = Procedura(
            code="REPR",
            title="Repr Test",
            description="d",
            category=ProceduraCategory.FISCALE,
            steps=[],
            estimated_time_minutes=10,
        )
        assert "REPR" in repr(procedura)
        assert "Repr Test" in repr(procedura)
