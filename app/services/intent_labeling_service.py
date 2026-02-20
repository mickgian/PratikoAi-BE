"""Intent Labeling Service for Expert Training Data Collection.

DEV-253: Service layer for the expert labeling UI. Captures low-confidence
HF classifications for expert review and exports labeled data for model training.

Usage:
    from app.services.intent_labeling_service import intent_labeling_service

    # Capture a low-confidence prediction
    await intent_labeling_service.capture_prediction(
        query="Come si calcola l'IVA?",
        predicted_intent="technical_research",
        confidence=0.45,
        all_scores={...},
        source_query_id=uuid,
        db=session,
    )

    # Get labeling queue
    queue = await intent_labeling_service.get_queue(page=1, page_size=50, db=session)

    # Submit expert label
    labeled = await intent_labeling_service.submit_label(
        query_id=uuid,
        expert_intent=IntentLabel.CALCULATOR,
        labeled_by=user_id,
        notes="Richiesta di calcolo",
        db=session,
    )
"""

import csv
import io
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.intent_labeling import IntentLabel, LabeledQuery
from app.schemas.intent_labeling import (
    LabeledQueryResponse,
    LabelingStatsResponse,
    QueueItem,
    QueueResponse,
)


class IntentLabelingService:
    """Service for managing intent labeling workflow.

    Captures low-confidence HF classifications, provides a labeling queue,
    and exports labeled data for classifier training.

    Attributes:
        LABELING_CONFIDENCE_THRESHOLD: Predictions below this threshold
            are captured for expert review. Default 0.7 matches HF classifier.
    """

    LABELING_CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, labeling_threshold: float | None = None):
        """Initialize the labeling service.

        Args:
            labeling_threshold: Custom confidence threshold for capturing predictions.
                               Defaults to LABELING_CONFIDENCE_THRESHOLD (0.7).
        """
        if labeling_threshold is not None:
            self.LABELING_CONFIDENCE_THRESHOLD = labeling_threshold

    async def capture_prediction(
        self,
        query: str,
        predicted_intent: str,
        confidence: float,
        all_scores: dict[str, Any],
        source_query_id: UUID | None,
        db: AsyncSession,
    ) -> UUID | None:
        """Capture a low-confidence prediction for expert labeling.

        Only captures predictions below the confidence threshold.
        High-confidence predictions don't need expert review.

        Args:
            query: The user query text
            predicted_intent: HF classifier's prediction
            confidence: HF classifier's confidence score (0.0-1.0)
            all_scores: Full score distribution from HF classifier
            source_query_id: UUID of the original query for traceability
            db: Database session

        Returns:
            UUID of the captured record, or None if not captured (high confidence)
        """
        # Only capture low-confidence predictions
        if confidence >= self.LABELING_CONFIDENCE_THRESHOLD:
            logger.debug(
                "intent_labeling_skip_high_confidence",
                confidence=confidence,
                threshold=self.LABELING_CONFIDENCE_THRESHOLD,
                predicted_intent=predicted_intent,
            )
            return None

        try:
            labeled_query = LabeledQuery(
                query=query,
                predicted_intent=predicted_intent,
                confidence=confidence,
                all_scores=all_scores,
                source_query_id=source_query_id,
            )

            db.add(labeled_query)
            await db.commit()
            await db.refresh(labeled_query)

            logger.info(
                "intent_labeling_captured",
                query_id=str(labeled_query.id),
                predicted_intent=predicted_intent,
                confidence=confidence,
            )

            return labeled_query.id

        except Exception as e:
            logger.error(
                "intent_labeling_capture_failed",
                error_type=type(e).__name__,
                error_message=str(e),
                query_length=len(query),
            )
            await db.rollback()
            raise

    async def get_queue(
        self,
        page: int,
        page_size: int,
        db: AsyncSession,
    ) -> QueueResponse:
        """Get the labeling queue of unlabeled queries.

        Returns queries ordered by confidence (lowest first) so experts
        can focus on the most uncertain classifications.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            db: Database session

        Returns:
            QueueResponse with paginated unlabeled queries
        """
        # Count total unlabeled queries
        count_query = (
            select(func.count())
            .select_from(LabeledQuery)
            .where(
                LabeledQuery.is_deleted == False,  # noqa: E712
                LabeledQuery.expert_intent.is_(None),  # type: ignore[union-attr]
            )
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get paginated results ordered by confidence ASC
        offset = (page - 1) * page_size
        query = (
            select(LabeledQuery)
            .where(
                LabeledQuery.is_deleted == False,  # noqa: E712
                LabeledQuery.expert_intent.is_(None),  # type: ignore[union-attr]
            )
            .order_by(LabeledQuery.confidence.asc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(query)
        queries = result.scalars().all()

        items = [
            QueueItem(
                id=q.id,
                query=q.query,
                predicted_intent=q.predicted_intent,
                confidence=q.confidence,
                all_scores=q.all_scores or {},
                expert_intent=q.expert_intent,
                skip_count=q.skip_count,
                created_at=q.created_at,
            )
            for q in queries
        ]

        return QueueResponse(
            total_count=total_count,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def submit_label(
        self,
        query_id: UUID,
        expert_intent: str | IntentLabel,
        labeled_by: int,
        notes: str | None,
        db: AsyncSession,
    ) -> LabeledQueryResponse:
        """Submit an expert label for a query.

        Args:
            query_id: UUID of the query to label
            expert_intent: Expert-assigned intent (string or IntentLabel enum)
            labeled_by: User ID of the expert
            notes: Optional notes explaining the label
            db: Database session

        Returns:
            LabeledQueryResponse with updated query data

        Raises:
            ValueError: If query not found or intent is invalid
        """
        # Validate intent
        if isinstance(expert_intent, IntentLabel):
            intent_value = expert_intent.value
        else:
            # Validate string is a valid IntentLabel
            try:
                IntentLabel(expert_intent)
                intent_value = expert_intent
            except ValueError as e:
                raise ValueError("Intento non valido") from e

        # Find the query
        query = select(LabeledQuery).where(LabeledQuery.id == query_id)
        result = await db.execute(query)
        labeled_query = result.scalar_one_or_none()

        if labeled_query is None:
            raise ValueError("Query non trovata")

        # Update the query with expert label
        labeled_query.expert_intent = intent_value
        labeled_query.labeled_by = labeled_by
        labeled_query.labeled_at = datetime.utcnow()
        labeled_query.labeling_notes = notes

        await db.commit()
        await db.refresh(labeled_query)

        logger.info(
            "intent_labeling_submitted",
            query_id=str(query_id),
            expert_intent=intent_value,
            labeled_by=labeled_by,
        )

        return LabeledQueryResponse(
            id=labeled_query.id,
            query=labeled_query.query,
            predicted_intent=labeled_query.predicted_intent,
            expert_intent=labeled_query.expert_intent,
            labeled_by=labeled_query.labeled_by,
            labeled_at=labeled_query.labeled_at,
            labeling_notes=labeled_query.labeling_notes,
        )

    async def get_stats(self, db: AsyncSession) -> LabelingStatsResponse:
        """Get labeling progress statistics.

        Args:
            db: Database session

        Returns:
            LabelingStatsResponse with progress metrics
        """
        # Total queries
        total_query = (
            select(func.count())
            .select_from(LabeledQuery)
            .where(
                LabeledQuery.is_deleted == False,  # noqa: E712
            )
        )
        total_result = await db.execute(total_query)
        total_queries = total_result.scalar() or 0

        # Labeled queries
        labeled_query = (
            select(func.count())
            .select_from(LabeledQuery)
            .where(
                LabeledQuery.is_deleted == False,  # noqa: E712
                LabeledQuery.expert_intent.is_not(None),  # type: ignore[union-attr]
            )
        )
        labeled_result = await db.execute(labeled_query)
        labeled_queries = labeled_result.scalar() or 0

        pending_queries = total_queries - labeled_queries
        completion_percentage = (labeled_queries / total_queries * 100) if total_queries > 0 else 0.0

        # New since last export (labeled but not yet exported)
        new_since_export_query = (
            select(func.count())
            .select_from(LabeledQuery)
            .where(
                LabeledQuery.is_deleted == False,  # noqa: E712
                LabeledQuery.expert_intent.is_not(None),  # type: ignore[union-attr]
                LabeledQuery.exported_at.is_(None),  # type: ignore[union-attr]
            )
        )
        new_since_export_result = await db.execute(new_since_export_query)
        new_since_export = new_since_export_result.scalar() or 0

        # Labels by intent (count for each intent)
        labels_by_intent: dict[str, int] = {}
        for intent in IntentLabel:
            count_query = (
                select(func.count())
                .select_from(LabeledQuery)
                .where(
                    LabeledQuery.is_deleted == False,  # noqa: E712
                    LabeledQuery.expert_intent == intent.value,
                )
            )
            count_result = await db.execute(count_query)
            count = count_result.scalar() or 0
            if count > 0:
                labels_by_intent[intent.value] = count

        return LabelingStatsResponse(
            total_queries=total_queries,
            labeled_queries=labeled_queries,
            pending_queries=pending_queries,
            completion_percentage=round(completion_percentage, 2),
            labels_by_intent=labels_by_intent,
            new_since_export=new_since_export,
        )

    async def export_training_data(
        self,
        format: str,
        db: AsyncSession,
    ) -> tuple[str, int]:
        """Export labeled data for HuggingFace training.

        Args:
            format: Export format ("jsonl" or "csv")
            db: Database session

        Returns:
            Tuple of (content string, count of exported records)
        """
        # Get all labeled queries
        query = select(LabeledQuery).where(
            LabeledQuery.is_deleted == False,  # noqa: E712
            LabeledQuery.expert_intent.is_not(None),  # type: ignore[union-attr]
        )
        result = await db.execute(query)
        queries = result.scalars().all()

        if not queries:
            return "", 0

        if format == "jsonl":
            lines = []
            for q in queries:
                record = {
                    "text": q.query,
                    "label": q.expert_intent,
                }
                lines.append(json.dumps(record, ensure_ascii=False))
            content = "\n".join(lines)

        elif format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["text", "label"])
            for q in queries:
                writer.writerow([q.query, q.expert_intent])
            content = output.getvalue()

        else:
            raise ValueError(f"Formato non supportato: {format}")

        # Stamp exported_at on all exported records
        query_ids = [q.id for q in queries]
        await db.execute(
            update(LabeledQuery).where(LabeledQuery.id.in_(query_ids)).values(exported_at=datetime.utcnow())  # type: ignore[attr-defined]  # type: ignore[union-attr]
        )
        await db.commit()

        logger.info(
            "intent_labeling_export",
            format=format,
            count=len(queries),
        )

        return content, len(queries)

    async def skip_query(self, query_id: UUID, db: AsyncSession) -> int:
        """Skip a query in the labeling queue.

        Increments the skip count for tracking difficult queries.

        Args:
            query_id: UUID of the query to skip
            db: Database session

        Returns:
            Updated skip count

        Raises:
            ValueError: If query not found
        """
        query = select(LabeledQuery).where(LabeledQuery.id == query_id)
        result = await db.execute(query)
        labeled_query = result.scalar_one_or_none()

        if labeled_query is None:
            raise ValueError("Query non trovata")

        labeled_query.skip_count += 1
        await db.commit()

        logger.info(
            "intent_labeling_skipped",
            query_id=str(query_id),
            skip_count=labeled_query.skip_count,
        )

        return labeled_query.skip_count


# Singleton instance
intent_labeling_service = IntentLabelingService()
