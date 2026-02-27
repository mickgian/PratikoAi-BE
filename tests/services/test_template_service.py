"""DEV-336: Tests for TemplateService — Communication template management.

Tests cover:
- Template CRUD (create, get_by_id, list, update, delete)
- Studio-isolated template listing
- Template rendering with variable substitution
- Not found handling
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.communication import CanaleInvio
from app.models.communication_template import CommunicationTemplate
from app.services.template_service import TemplateService


@pytest.fixture
def template_service() -> TemplateService:
    return TemplateService()


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def studio_id():
    return uuid4()


@pytest.fixture
def sample_template(studio_id) -> CommunicationTemplate:
    return CommunicationTemplate(
        id=uuid4(),
        studio_id=studio_id,
        name="Scadenza IVA",
        subject_template="Promemoria: scadenza IVA {{trimestre}}",
        content_template=(
            "Gentile {{nome}},\n\n"
            "Le ricordiamo che la scadenza per il versamento IVA "
            "del {{trimestre}} è il {{data_scadenza}}.\n\n"
            "Cordiali saluti,\n{{studio_nome}}"
        ),
        channel=CanaleInvio.EMAIL,
        category="scadenza",
        is_active=True,
    )


class TestTemplateServiceCreate:
    """Test TemplateService.create()."""

    @pytest.mark.asyncio
    async def test_create_template(
        self,
        template_service: TemplateService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Happy path: create a new communication template."""
        result = await template_service.create(
            db=mock_db,
            studio_id=studio_id,
            name="Scadenza IVA",
            subject_template="Promemoria: scadenza IVA {{trimestre}}",
            content_template="Gentile {{nome}}, la scadenza IVA è il {{data_scadenza}}.",
            channel=CanaleInvio.EMAIL,
        )

        assert result.name == "Scadenza IVA"
        assert result.studio_id == studio_id
        assert result.channel == CanaleInvio.EMAIL
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()


class TestTemplateServiceGetById:
    """Test TemplateService.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_template_by_id(
        self,
        template_service: TemplateService,
        mock_db: AsyncMock,
        sample_template: CommunicationTemplate,
    ) -> None:
        """Happy path: retrieve template by ID."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_template)))

        result = await template_service.get_by_id(
            db=mock_db,
            template_id=sample_template.id,
            studio_id=sample_template.studio_id,
        )

        assert result is not None
        assert result.id == sample_template.id
        assert result.name == "Scadenza IVA"

    @pytest.mark.asyncio
    async def test_get_template_not_found(
        self,
        template_service: TemplateService,
        mock_db: AsyncMock,
        studio_id,
    ) -> None:
        """Error: non-existent template returns None."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await template_service.get_by_id(
            db=mock_db,
            template_id=uuid4(),
            studio_id=studio_id,
        )

        assert result is None


class TestTemplateServiceList:
    """Test TemplateService.list_by_studio()."""

    @pytest.mark.asyncio
    async def test_list_templates_by_studio(
        self,
        template_service: TemplateService,
        mock_db: AsyncMock,
        studio_id,
        sample_template: CommunicationTemplate,
    ) -> None:
        """Happy path: list templates with studio isolation."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_template])))
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await template_service.list_by_studio(
            db=mock_db,
            studio_id=studio_id,
        )

        assert len(result) == 1
        assert result[0].studio_id == studio_id
        assert result[0].name == "Scadenza IVA"


class TestTemplateServiceRender:
    """Test TemplateService.render()."""

    def test_render_template(
        self,
        template_service: TemplateService,
        sample_template: CommunicationTemplate,
    ) -> None:
        """Happy path: render template with variable substitution."""
        variables = {
            "nome": "Mario Rossi",
            "trimestre": "Q1 2026",
            "data_scadenza": "16/03/2026",
            "studio_nome": "Studio Bianchi",
        }

        subject, content = template_service.render(
            template=sample_template,
            variables=variables,
        )

        assert "Q1 2026" in subject
        assert "Mario Rossi" in content
        assert "16/03/2026" in content
        assert "Studio Bianchi" in content

    def test_render_template_missing_variable(
        self,
        template_service: TemplateService,
        sample_template: CommunicationTemplate,
    ) -> None:
        """Missing variables remain as {{placeholder}}."""
        variables = {"nome": "Mario Rossi"}

        subject, content = template_service.render(
            template=sample_template,
            variables=variables,
        )

        assert "Mario Rossi" in content
        # Unresolved variables stay as placeholders
        assert "{{trimestre}}" in subject
        assert "{{data_scadenza}}" in content


class TestTemplateServiceUpdate:
    """Test TemplateService.update()."""

    @pytest.mark.asyncio
    async def test_update_template(
        self,
        template_service: TemplateService,
        mock_db: AsyncMock,
        sample_template: CommunicationTemplate,
    ) -> None:
        """Happy path: update template name and content."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_template)))

        result = await template_service.update(
            db=mock_db,
            template_id=sample_template.id,
            studio_id=sample_template.studio_id,
            name="Scadenza IVA Aggiornata",
            content_template="Gentile {{nome}}, nuova scadenza il {{data_scadenza}}.",
        )

        assert result is not None


class TestTemplateServiceDelete:
    """Test TemplateService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_template(
        self,
        template_service: TemplateService,
        mock_db: AsyncMock,
        sample_template: CommunicationTemplate,
    ) -> None:
        """Happy path: soft-delete (deactivate) a template."""
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=sample_template)))

        result = await template_service.delete(
            db=mock_db,
            template_id=sample_template.id,
            studio_id=sample_template.studio_id,
        )

        assert result is True
        # Template is soft-deleted (deactivated), not hard-deleted
        assert sample_template.is_active is False
