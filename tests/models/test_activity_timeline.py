"""Tests for DEV-357: Activity Timeline Model."""

from uuid import uuid4

from app.models.activity_timeline import ActivityTimeline, ActivityType


class TestActivityType:
    """Tests for ActivityType enum."""

    def test_all_values_exist(self):
        assert ActivityType.COMMUNICATION_SENT == "communication_sent"
        assert ActivityType.COMMUNICATION_DRAFT == "communication_draft"
        assert ActivityType.PROCEDURA_STARTED == "procedura_started"
        assert ActivityType.PROCEDURA_COMPLETED == "procedura_completed"
        assert ActivityType.MATCH_FOUND == "match_found"
        assert ActivityType.CLIENT_CREATED == "client_created"
        assert ActivityType.CLIENT_UPDATED == "client_updated"
        assert ActivityType.DOCUMENT_UPLOADED == "document_uploaded"

    def test_enum_count(self):
        assert len(ActivityType) == 8


class TestActivityTimeline:
    """Tests for ActivityTimeline model."""

    def test_create_minimal(self):
        studio_id = uuid4()
        activity = ActivityTimeline(
            studio_id=studio_id,
            user_id=1,
            activity_type=ActivityType.CLIENT_CREATED,
            title="Nuovo cliente creato",
        )
        assert activity.studio_id == studio_id
        assert activity.user_id == 1
        assert activity.activity_type == ActivityType.CLIENT_CREATED
        assert activity.title == "Nuovo cliente creato"
        assert activity.description is None
        assert activity.reference_id is None
        assert activity.metadata_json is None

    def test_create_with_all_fields(self):
        studio_id = uuid4()
        ref_id = uuid4()
        activity = ActivityTimeline(
            studio_id=studio_id,
            user_id=2,
            activity_type=ActivityType.COMMUNICATION_SENT,
            title="Comunicazione inviata",
            description="Inviata comunicazione a Mario Rossi",
            reference_id=ref_id,
            reference_type="communication",
            metadata_json={"channel": "email"},
        )
        assert activity.reference_id == ref_id
        assert activity.reference_type == "communication"
        assert activity.metadata_json == {"channel": "email"}

    def test_repr(self):
        activity = ActivityTimeline(
            studio_id=uuid4(),
            user_id=1,
            activity_type=ActivityType.MATCH_FOUND,
            title="Match trovato",
        )
        repr_str = repr(activity)
        assert "match_found" in repr_str
        assert "Match trovato" in repr_str

    def test_tablename(self):
        assert ActivityTimeline.__tablename__ == "activity_timeline"

    def test_default_id_generated(self):
        a = ActivityTimeline(
            studio_id=uuid4(),
            user_id=1,
            activity_type=ActivityType.DOCUMENT_UPLOADED,
            title="Doc uploaded",
        )
        assert a.id is not None
