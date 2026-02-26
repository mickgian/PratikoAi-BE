"""DEV-388: Shared PDF Export Service.

Generates PDFs for procedures, tax calculations, dashboard reports,
and communication archives using ReportLab.
"""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.logging import logger

# Branding constants
_BRAND = "PratikoAI"
_BRAND_COLOR = colors.HexColor("#1E3A5F")


class PDFExportService:
    """Shared PDF generation service.

    All public methods return ``bytes`` (the raw PDF).
    """

    def __init__(self) -> None:
        self._styles = getSampleStyleSheet()
        self._register_custom_styles()

    # ------------------------------------------------------------------
    # Custom styles
    # ------------------------------------------------------------------

    def _register_custom_styles(self) -> None:
        self._styles.add(
            ParagraphStyle(
                "BrandTitle",
                parent=self._styles["Title"],
                textColor=_BRAND_COLOR,
                fontSize=18,
                spaceAfter=12,
            )
        )
        self._styles.add(
            ParagraphStyle(
                "SectionHeader",
                parent=self._styles["Heading2"],
                textColor=_BRAND_COLOR,
                fontSize=13,
                spaceBefore=14,
                spaceAfter=6,
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_pdf(
        self,
        title: str,
        content: str,
        *,
        sections: list[dict[str, str]] | None = None,
        template: str | None = None,
        author: str = _BRAND,
        subject: str = "",
    ) -> bytes:
        """Generate a generic PDF document.

        Args:
            title: Document title.
            content: Body text (may be empty).
            sections: Optional list of ``{"title": …, "content": …}`` dicts.
            template: Template name (ignored if unknown — falls back to default).
            author: PDF metadata author.
            subject: PDF metadata subject.

        Returns:
            Raw PDF bytes.
        """
        if template and template != "default":
            logger.warning("pdf_unknown_template", template=template, fallback="default")

        buf = BytesIO()
        doc = self._make_doc(buf, title=title, author=author, subject=subject)

        story: list[Any] = []
        story.append(Paragraph(title, self._styles["BrandTitle"]))

        if content:
            story.append(Paragraph(content, self._styles["BodyText"]))

        for sec in sections or []:
            story.append(Spacer(1, 6 * mm))
            story.append(Paragraph(sec.get("title", ""), self._styles["SectionHeader"]))
            story.append(Paragraph(sec.get("content", ""), self._styles["BodyText"]))

        if not story or (len(story) == 1 and not content):
            story.append(Spacer(1, 1 * cm))

        doc.build(story)
        return buf.getvalue()

    def export_procedura(
        self,
        procedura: dict[str, Any],
        progress: dict[str, Any] | None = None,
    ) -> bytes:
        """Export a procedura with optional step progress.

        Args:
            procedura: Dict with ``code``, ``title``, ``steps``.
            progress: Optional dict with ``current_step``, ``completed_steps``.

        Returns:
            Raw PDF bytes.
        """
        completed = set(progress.get("completed_steps", [])) if progress else set()

        buf = BytesIO()
        doc = self._make_doc(buf, title=procedura.get("title", "Procedura"))

        story: list[Any] = []
        story.append(Paragraph(procedura.get("title", ""), self._styles["BrandTitle"]))
        story.append(Paragraph(f"Codice: {procedura.get('code', '')}", self._styles["BodyText"]))
        story.append(Spacer(1, 6 * mm))

        for step in procedura.get("steps", []):
            step_num = step.get("step", 0)
            status = "[completato]" if step_num in completed else "[da fare]"
            story.append(
                Paragraph(
                    f"<b>Step {step_num}</b> — {step.get('title', '')} {status}",
                    self._styles["SectionHeader"],
                )
            )
            for item in step.get("checklist", []):
                story.append(Paragraph(f"&bull; {item}", self._styles["BodyText"]))

        doc.build(story)
        return buf.getvalue()

    def export_calculation(self, calculation: dict[str, Any]) -> bytes:
        """Export a tax calculation result.

        Args:
            calculation: Dict with calculation details.

        Returns:
            Raw PDF bytes.
        """
        buf = BytesIO()
        title = calculation.get("tipo", "Calcolo Fiscale")
        doc = self._make_doc(buf, title=title)

        story: list[Any] = []
        story.append(Paragraph(title, self._styles["BrandTitle"]))

        # Build a summary table
        data = []
        for key, value in calculation.items():
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    data.append([f"{key} — {sub_key}", self._fmt(sub_val)])
            else:
                data.append([str(key), self._fmt(value)])

        if data:
            tbl = Table(data, colWidths=[10 * cm, 6 * cm])
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), _BRAND_COLOR),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(tbl)

        doc.build(story)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _make_doc(buf: BytesIO, *, title: str = "", author: str = _BRAND, subject: str = "") -> SimpleDocTemplate:
        return SimpleDocTemplate(
            buf,
            pagesize=A4,
            title=title,
            author=author,
            subject=subject,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

    @staticmethod
    def _fmt(value: Any) -> str:
        """Format a value for display in the PDF."""
        if isinstance(value, float):
            return f"€ {value:,.2f}"
        return str(value)
