"""Test that SQLAlchemy mapper initializes without errors.

This test validates that the FAQ automation models can initialize their
mappers without cross-metadata registry issues.

Bug: GeneratedFAQ, RSSFAQImpact, and FAQGenerationJob use relationship("User")
where User is in SQLModel.metadata but these models are in Base.metadata.
String-based relationships cannot resolve across metadata boundaries.

Fix: Use lambda: UserModel to delay reference resolution until after
both metadata registries are initialized.
"""

import pytest
from sqlalchemy.orm import configure_mappers


def test_mapper_configuration_succeeds():
    """Verify all models initialize without mapper errors.

    This test triggers mapper configuration for all models in the application.
    Before the lambda fix, this would raise InvalidRequestError because
    GeneratedFAQ.approver relationship("User") cannot find User across
    different metadata registries.

    After the fix, mapper configuration should succeed without errors.
    """
    # Import all models to ensure they're registered
    from app.models.faq_automation import (  # noqa: F401
        FAQGenerationJob,
        GeneratedFAQ,
        RSSFAQImpact,
    )
    from app.models.user import User  # noqa: F401

    # This should NOT raise InvalidRequestError
    configure_mappers()


def test_generated_faq_approver_relationship_exists():
    """Verify GeneratedFAQ.approver relationship is defined."""
    from app.models.faq_automation import GeneratedFAQ

    assert hasattr(GeneratedFAQ, "approver"), "GeneratedFAQ must have 'approver' relationship"
    assert GeneratedFAQ.approver is not None, "approver relationship must not be None"


def test_rss_faq_impact_action_user_relationship_exists():
    """Verify RSSFAQImpact.action_user relationship is defined."""
    from app.models.faq_automation import RSSFAQImpact

    assert hasattr(RSSFAQImpact, "action_user"), "RSSFAQImpact must have 'action_user' relationship"
    assert RSSFAQImpact.action_user is not None, "action_user relationship must not be None"


def test_faq_generation_job_creator_relationship_exists():
    """Verify FAQGenerationJob.creator relationship is defined."""
    from app.models.faq_automation import FAQGenerationJob

    assert hasattr(FAQGenerationJob, "creator"), "FAQGenerationJob must have 'creator' relationship"
    assert FAQGenerationJob.creator is not None, "creator relationship must not be None"


def test_all_user_relationships_point_to_user_model():
    """Verify that all User relationships resolve to the correct User class.

    This test ensures the lambda relationships correctly resolve to the
    User model from app.models.user, not some other User class.
    """
    from app.models.faq_automation import FAQGenerationJob, GeneratedFAQ, RSSFAQImpact
    from app.models.user import User

    # Trigger mapper configuration
    configure_mappers()

    # Check GeneratedFAQ.approver points to User
    approver_mapper = GeneratedFAQ.approver.property.mapper
    assert approver_mapper.class_ == User, "GeneratedFAQ.approver must point to User model"

    # Check RSSFAQImpact.action_user points to User
    action_user_mapper = RSSFAQImpact.action_user.property.mapper
    assert action_user_mapper.class_ == User, "RSSFAQImpact.action_user must point to User model"

    # Check FAQGenerationJob.creator points to User
    creator_mapper = FAQGenerationJob.creator.property.mapper
    assert creator_mapper.class_ == User, "FAQGenerationJob.creator must point to User model"
