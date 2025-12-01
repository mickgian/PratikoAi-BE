"""Task Generator Service for Expert Feedback System.

Automatically generates quality issue tasks in QUERY_ISSUES_ROADMAP.md when experts
mark responses as 'Incomplete' or 'Incorrect' and provide additional details.

These tasks track AI response quality issues, NOT development process issues.

Features:
- Async task creation (fire and forget, doesn't block feedback submission)
- Scans QUERY_ISSUES_ROADMAP.md to find max QUERY-XXX number
- Generates task ID by incrementing max number (QUERY-01, QUERY-02, etc.)
- Creates markdown task with proper format
- Appends to QUERY_ISSUES_ROADMAP.md (creates file if doesn't exist)
- Stores record in expert_generated_tasks table
- Logs success/failure (doesn't raise exceptions to avoid blocking feedback)
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import AsyncSessionLocal
from app.models.quality_analysis import ExpertFeedback, ExpertGeneratedTask, ExpertProfile


class TaskGeneratorService:
    """Service for automatically generating quality issue tasks from expert feedback.

    This service is called asynchronously (fire and forget) after expert feedback
    is submitted. It creates tasks in QUERY_ISSUES_ROADMAP.md and tracks them in the
    expert_generated_tasks database table.

    Note: These tasks track AI response quality issues, NOT development process issues.
    """

    def __init__(self):
        """Initialize task generator service.

        Note: This service creates its own database session for background tasks.
        """
        self.project_root = Path(__file__).parent.parent.parent

    async def generate_task_from_feedback(self, feedback_id: UUID, expert_id: UUID) -> str | None:
        """Generate development task from expert feedback.

        This method is called asynchronously and should not raise exceptions
        to avoid blocking the feedback submission flow.

        Creates its own database session since it runs as a background task.

        Args:
            feedback_id: UUID of ExpertFeedback record with additional_details
            expert_id: UUID of ExpertProfile of the expert who submitted feedback

        Returns:
            str: Task ID (e.g., "QUERY-08") if successful, None if failed
        """
        # Create new session for background task (request session will be closed)
        async with AsyncSessionLocal() as db:
            try:
                # Load feedback and expert from database
                feedback = await db.get(ExpertFeedback, feedback_id)
                expert = await db.get(ExpertProfile, expert_id)

                if not feedback or not expert:
                    logger.error(f"Failed to load feedback {feedback_id} or expert {expert_id}")
                    return None

                # Only create tasks for incomplete/incorrect feedback with additional_details
                if feedback.feedback_type.value not in ["incomplete", "incorrect"]:
                    logger.info(
                        f"Skipping task generation for feedback {feedback.id} - "
                        f"feedback_type is {feedback.feedback_type.value}"
                    )
                    return None

                if not feedback.additional_details:
                    logger.info(
                        f"Skipping task generation for feedback {feedback.id} - no additional_details provided"
                    )
                    return None

                logger.info(f"Starting task generation for feedback {feedback.id}")

                # Generate task ID by scanning existing files
                task_id = await self._generate_task_id()
                logger.info(f"Generated task ID: {task_id}")

                # Generate task name from question
                task_name = self._generate_task_name(feedback.query_text)
                logger.info(f"Generated task name: {task_name}")

                # Create markdown content
                markdown = self._create_task_markdown(task_id, task_name, feedback, expert)

                # Append to QUERY_ISSUES_ROADMAP.md
                await self._append_to_file(markdown)
                logger.info(f"Appended task {task_id} to QUERY_ISSUES_ROADMAP.md")

                # Store in database
                await self._store_task_record(task_id, task_name, feedback, expert, db)
                logger.info(f"Stored task {task_id} in database")

                # Update feedback record with task info
                feedback.generated_task_id = task_id
                feedback.task_creation_success = True
                await db.commit()

                logger.info(f"Task {task_id} created successfully from feedback {feedback.id}")
                return task_id

            except Exception as e:
                logger.error(f"Failed to create task from feedback {feedback_id}: {e}", exc_info=True)

                # Update feedback record with error (but don't fail the request)
                try:
                    if feedback:
                        feedback.task_creation_success = False
                        feedback.task_creation_error = str(e)[:500]  # Truncate error to fit in column
                        await db.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update feedback record with error: {db_error}", exc_info=True)

                return None

    async def _generate_task_id(self) -> str:
        """Generate next task ID by scanning QUERY_ISSUES_ROADMAP.md.

        Scans QUERY_ISSUES_ROADMAP.md to find the highest QUERY-XXX number and increments it.
        Note: Task IDs start from QUERY-08 since QUERY-01 through QUERY-07 are reserved for
        development process issues.

        Returns:
            str: Next task ID (e.g., "QUERY-08", "QUERY-09", etc.)
        """
        roadmap_max = await self._scan_file_for_max_task_number(
            self.project_root / "QUERY_ISSUES_ROADMAP.md", pattern=r"QUERY-(\d+)"
        )
        logger.debug(f"Max task number in QUERY_ISSUES_ROADMAP.md: {roadmap_max}")

        # Start from QUERY-08 (QUERY-01 to QUERY-07 are reserved for process issues)
        next_num = max(roadmap_max, 7) + 1
        return f"QUERY-{next_num:02d}"  # Zero-pad to 2 digits (QUERY-08, QUERY-09, ...)

    async def _scan_file_for_max_task_number(self, filepath: Path, pattern: str) -> int:
        r"""Scan file for task ID pattern and return highest number found.

        Args:
            filepath: Path to file to scan
            pattern: Regex pattern to match task IDs (e.g., r"DEV-BE-(\d+)")

        Returns:
            int: Highest task number found, or 0 if file doesn't exist or no matches
        """
        if not filepath.exists():
            logger.debug(f"File {filepath} does not exist, returning 0")
            return 0

        try:
            content = filepath.read_text()
            matches = re.findall(pattern, content)

            if matches:
                max_num = max(int(m) for m in matches)
                logger.debug(f"Found {len(matches)} task IDs in {filepath.name}, max: {max_num}")
                return max_num

            logger.debug(f"No task IDs found in {filepath.name}")
            return 0

        except Exception as e:
            logger.warning(f"Error scanning {filepath}: {e}", exc_info=True)
            return 0

    def _generate_task_name(self, question: str) -> str:
        """Generate task name from question (max 30 chars, uppercase, underscores).

        Args:
            question: Original question text

        Returns:
            str: Task name (e.g., "CALCOLO_IVA_REGIME_FORFETTA")
        """
        # Truncate to 30 chars
        name = question.strip()[:30]

        # Convert to uppercase
        name = name.upper()

        # Keep only alphanumeric characters and spaces
        name = re.sub(r"[^A-Z0-9\s]", "", name)

        # Replace spaces with underscores
        name = name.replace(" ", "_")

        # Remove multiple consecutive underscores
        name = re.sub(r"_+", "_", name)

        # Strip leading/trailing underscores
        name = name.strip("_")

        # Ensure we have a valid name
        if not name:
            name = "EXPERT_FEEDBACK_TASK"

        return name

    def _create_task_markdown(
        self, task_id: str, task_name: str, feedback: ExpertFeedback, expert: ExpertProfile
    ) -> str:
        """Create markdown task format for QUERY_ISSUES_ROADMAP.md.

        Args:
            task_id: Task ID (e.g., "QUERY-08")
            task_name: Task name (e.g., "CALCOLO_IVA")
            feedback: ExpertFeedback record
            expert: ExpertProfile of the expert

        Returns:
            str: Formatted markdown task
        """
        # Map feedback type to Italian
        feedback_type_it = {"incomplete": "Incompleta", "incorrect": "Errata"}.get(
            feedback.feedback_type.value, feedback.feedback_type.value
        )

        # Format category if present
        category_str = f"- Categoria: {feedback.category.value}\n" if feedback.category else ""

        # Format regulatory references if present
        regulatory_refs_str = ""
        if feedback.regulatory_references:
            regulatory_refs_str = "\n**Riferimenti normativi citati dall'esperto:**\n"
            for ref in feedback.regulatory_references:
                regulatory_refs_str += f"- {ref}\n"

        # Format improvement suggestions if present
        suggestions_str = ""
        if feedback.improvement_suggestions:
            suggestions_str = "\n**Suggerimenti per il miglioramento:**\n"
            for suggestion in feedback.improvement_suggestions:
                suggestions_str += f"- {suggestion}\n"

        markdown = f"""
---

### {task_id}: {task_name}

**Priority:** HIGH | **Effort:** TBD | **Dependencies:** None
**Created:** {datetime.now().strftime('%Y-%m-%d')}
**Source:** Expert Feedback (ID: {feedback.id})
**Expert:** User {expert.user_id} (Trust Score: {expert.trust_score:.2f})

**Problema rilevato dall'esperto:**

La risposta fornita dal sistema è stata marcata come **{feedback_type_it}** dall'esperto.

**Domanda originale:**
```
{feedback.query_text}
```

**Risposta fornita (incompleta/errata):**
```
{feedback.original_answer}
```

**Dettagli aggiuntivi dall'esperto:**
```
{feedback.additional_details}
```

**Feedback dell'esperto:**
- Tipo di feedback: {feedback.feedback_type.value}
{category_str}- Confidence score: {feedback.confidence_score:.2f}
- Tempo impiegato: {feedback.time_spent_seconds}s
{regulatory_refs_str}{suggestions_str}
**Implementazione richiesta:**
[Da definire dal team di sviluppo in base ai dettagli forniti dall'esperto]

**Acceptance Criteria:**
- [ ] Verificare che la risposta copra tutti i casi sollevati dall'esperto
- [ ] Aggiungere riferimenti normativi se mancanti
- [ ] Testare la risposta con domande simili
- [ ] Far validare la correzione da un esperto fiscale

**Status:** 🔴 TODO

**Note:**
Questo task è stato generato automaticamente dal sistema di feedback esperti.
Per maggiori dettagli sul feedback originale, consultare il database con `feedback_id: {feedback.id}`

"""

        return markdown

    async def _append_to_file(self, markdown: str) -> None:
        """Append task to QUERY_ISSUES_ROADMAP.md.

        Note: This method ONLY appends to the existing file. It does NOT create the file
        if it doesn't exist, because QUERY_ISSUES_ROADMAP.md should be manually created
        with proper structure (including QUERY-01 through QUERY-07 development process issues).

        Args:
            markdown: Formatted markdown task content

        Raises:
            FileNotFoundError: If QUERY_ISSUES_ROADMAP.md doesn't exist
        """
        filepath = self.project_root / "QUERY_ISSUES_ROADMAP.md"

        if not filepath.exists():
            error_msg = (
                f"QUERY_ISSUES_ROADMAP.md not found at {filepath}. "
                "This file must be manually created with proper structure."
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Append task to the end of the file
        with filepath.open("a") as f:
            f.write(markdown)

        logger.info(f"Appended task to {filepath}")

    async def _store_task_record(
        self, task_id: str, task_name: str, feedback: ExpertFeedback, expert: ExpertProfile, db: AsyncSession
    ) -> None:
        """Store task record in expert_generated_tasks table.

        Args:
            task_id: Task ID (e.g., "QUERY-08")
            task_name: Task name
            feedback: ExpertFeedback record
            expert: ExpertProfile of the expert
            db: Database session to use
        """
        task = ExpertGeneratedTask(
            task_id=task_id,
            task_name=task_name,
            feedback_id=feedback.id,
            expert_id=expert.id,
            question=feedback.query_text,
            answer=feedback.original_answer,
            additional_details=feedback.additional_details,
            file_path="QUERY_ISSUES_ROADMAP.md",
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        logger.info(f"Stored task record in database: {task.id}")
