"""Rename golden_set intent label to normative_reference.

Renames the intent classification label in labeled_queries table:
- predicted_intent column: 'golden_set' → 'normative_reference'
- expert_intent column: 'golden_set' → 'normative_reference'
- all_scores JSON column: rename key 'golden_set' → 'normative_reference'

The golden set FAQ pipeline (response metadata, orchestrators) is NOT affected.

Revision ID: rename_golden_set_20260220
Revises: add_exported_at_20260220
Create Date: 2026-02-20 14:00:00.000000

"""

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = "rename_golden_set_20260220"
down_revision = "add_exported_at_20260220"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE labeled_queries SET predicted_intent = 'normative_reference' WHERE predicted_intent = 'golden_set'"
        )
    )
    op.execute(
        sa.text("UPDATE labeled_queries SET expert_intent = 'normative_reference' WHERE expert_intent = 'golden_set'")
    )
    # Rename JSON key in all_scores: move 'golden_set' value to 'normative_reference'
    # Column is json (not jsonb), so cast to jsonb for key operations, then back to json
    op.execute(
        sa.text(
            "UPDATE labeled_queries "
            "SET all_scores = ("
            "(all_scores::jsonb - 'golden_set') "
            "|| jsonb_build_object('normative_reference', all_scores::jsonb->'golden_set')"
            ")::json "
            "WHERE all_scores::jsonb ? 'golden_set'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE labeled_queries SET predicted_intent = 'golden_set' WHERE predicted_intent = 'normative_reference'"
        )
    )
    op.execute(
        sa.text("UPDATE labeled_queries SET expert_intent = 'golden_set' WHERE expert_intent = 'normative_reference'")
    )
    # Cast to jsonb for key operations, then back to json
    op.execute(
        sa.text(
            "UPDATE labeled_queries "
            "SET all_scores = ("
            "(all_scores::jsonb - 'normative_reference') "
            "|| jsonb_build_object('golden_set', all_scores::jsonb->'normative_reference')"
            ")::json "
            "WHERE all_scores::jsonb ? 'normative_reference'"
        )
    )
