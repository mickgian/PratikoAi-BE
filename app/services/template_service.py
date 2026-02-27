"""DEV-336: Template Service — Reusable communication template management.

CRUD for templates with variable rendering support.
"""

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.communication import CanaleInvio
from app.models.communication_template import CommunicationTemplate


class TemplateService:
    """Service for communication template management."""

    async def create(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        name: str,
        subject_template: str,
        content_template: str,
        channel: CanaleInvio,
        category: str = "generale",
    ) -> CommunicationTemplate:
        """Create a new communication template."""
        template = CommunicationTemplate(
            studio_id=studio_id,
            name=name,
            subject_template=subject_template,
            content_template=content_template,
            channel=channel,
            category=category,
        )
        db.add(template)
        await db.flush()

        logger.info(
            "template_created",
            template_id=str(template.id),
            studio_id=str(studio_id),
        )
        return template

    async def get_by_id(self, db: AsyncSession, *, template_id: UUID, studio_id: UUID) -> CommunicationTemplate | None:
        """Get template by ID within studio."""
        result = await db.execute(
            select(CommunicationTemplate).where(
                and_(
                    CommunicationTemplate.id == template_id,
                    CommunicationTemplate.studio_id == studio_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_studio(
        self,
        db: AsyncSession,
        *,
        studio_id: UUID,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[CommunicationTemplate]:
        """List templates for a studio."""
        query = select(CommunicationTemplate).where(CommunicationTemplate.studio_id == studio_id)
        if active_only:
            query = query.where(CommunicationTemplate.is_active.is_(True))
        if category is not None:
            query = query.where(CommunicationTemplate.category == category)
        query = query.order_by(CommunicationTemplate.name)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        *,
        template_id: UUID,
        studio_id: UUID,
        **fields: object,
    ) -> CommunicationTemplate | None:
        """Update template fields."""
        template = await self.get_by_id(db, template_id=template_id, studio_id=studio_id)
        if template is None:
            return None

        for key, value in fields.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        template.updated_at = datetime.now(UTC)
        await db.flush()

        logger.info("template_updated", template_id=str(template_id))
        return template

    async def delete(
        self,
        db: AsyncSession,
        *,
        template_id: UUID,
        studio_id: UUID,
    ) -> bool:
        """Soft-delete a template (set inactive). Returns True if found."""
        template = await self.get_by_id(db, template_id=template_id, studio_id=studio_id)
        if template is None:
            return False

        template.is_active = False
        template.updated_at = datetime.now(UTC)
        await db.flush()

        logger.info("template_deactivated", template_id=str(template_id))
        return True

    @staticmethod
    def render(
        template: CommunicationTemplate,
        variables: dict[str, str],
    ) -> tuple[str, str]:
        """Render a template with variable substitution.

        Returns (rendered_subject, rendered_content).
        Variables use {{variable_name}} syntax.
        """
        subject = _substitute(template.subject_template, variables)
        content = _substitute(template.content_template, variables)
        return subject, content


def _substitute(text: str, variables: dict[str, str]) -> str:
    """Replace {{key}} placeholders with values."""

    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        return variables.get(key, match.group(0))

    return re.sub(r"\{\{(\w+)\}\}", replacer, text)


template_service = TemplateService()
