"""DEV-431: Tests for Formulario SQLModel."""

from uuid import UUID

from app.models.formulario import Formulario, FormularioCategory


class TestFormularioCreation:
    """Test Formulario model creation and field defaults."""

    def test_formulario_valid_creation(self) -> None:
        """Valid formulario with all required fields."""
        formulario = Formulario(
            code="F24",
            name="Modello F24",
            description="Modello di pagamento unificato per imposte, contributi e premi",
            category=FormularioCategory.VERSAMENTI,
            issuing_authority="Agenzia delle Entrate",
        )

        assert formulario.code == "F24"
        assert formulario.name == "Modello F24"
        assert formulario.description == "Modello di pagamento unificato per imposte, contributi e premi"
        assert formulario.category == FormularioCategory.VERSAMENTI
        assert formulario.issuing_authority == "Agenzia delle Entrate"

    def test_formulario_uuid_auto_generated(self) -> None:
        """UUID id is auto-generated on creation."""
        formulario = Formulario(
            code="CU",
            name="Certificazione Unica",
            description="Certificazione dei redditi di lavoro dipendente",
            category=FormularioCategory.DICHIARAZIONI,
            issuing_authority="Agenzia delle Entrate",
        )

        assert formulario.id is not None
        assert isinstance(formulario.id, UUID)

    def test_formulario_code_uniqueness_attr(self) -> None:
        """Two formulari can have different codes (uniqueness enforced at DB)."""
        f1 = Formulario(
            code="F24",
            name="Modello F24",
            description="Pagamento imposte",
            category=FormularioCategory.VERSAMENTI,
            issuing_authority="Agenzia delle Entrate",
        )
        f2 = Formulario(
            code="CU",
            name="Certificazione Unica",
            description="Certificazione redditi",
            category=FormularioCategory.DICHIARAZIONI,
            issuing_authority="Agenzia delle Entrate",
        )

        assert f1.code != f2.code

    def test_formulario_category_enum(self) -> None:
        """All FormularioCategory enum values are valid."""
        assert FormularioCategory.APERTURA == "apertura"
        assert FormularioCategory.DICHIARAZIONI == "dichiarazioni"
        assert FormularioCategory.VERSAMENTI == "versamenti"
        assert FormularioCategory.LAVORO == "lavoro"
        assert FormularioCategory.PREVIDENZA == "previdenza"
        assert FormularioCategory.ALTRO == "altro"

    def test_formulario_all_categories(self) -> None:
        """FormularioCategory has exactly 6 categories."""
        categories = list(FormularioCategory)
        assert len(categories) == 6

    def test_formulario_nullable_external_url(self) -> None:
        """external_url defaults to None and can be set."""
        formulario_no_url = Formulario(
            code="AA9-12",
            name="Modello AA9/12",
            description="Dichiarazione di inizio attività",
            category=FormularioCategory.APERTURA,
            issuing_authority="Agenzia delle Entrate",
        )
        assert formulario_no_url.external_url is None

        formulario_with_url = Formulario(
            code="F24-URL",
            name="Modello F24",
            description="Pagamento imposte",
            category=FormularioCategory.VERSAMENTI,
            issuing_authority="Agenzia delle Entrate",
            external_url="https://www.agenziaentrate.gov.it/f24",
        )
        assert formulario_with_url.external_url == "https://www.agenziaentrate.gov.it/f24"

    def test_formulario_default_active(self) -> None:
        """is_active defaults to True."""
        formulario = Formulario(
            code="770",
            name="Modello 770",
            description="Dichiarazione dei sostituti d'imposta",
            category=FormularioCategory.DICHIARAZIONI,
            issuing_authority="Agenzia delle Entrate",
        )

        assert formulario.is_active is True

    def test_formulario_repr(self) -> None:
        """__repr__ includes code and name."""
        formulario = Formulario(
            code="UNILAV",
            name="Comunicazione UniLav",
            description="Comunicazione obbligatoria",
            category=FormularioCategory.LAVORO,
            issuing_authority="Ministero del Lavoro",
        )

        assert "UNILAV" in repr(formulario)
        assert "Comunicazione UniLav" in repr(formulario)
