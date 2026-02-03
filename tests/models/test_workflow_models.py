"""Tests for workflow models.

DEV-260: Workflow Data Layer
TDD: RED phase - tests written before implementation
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlmodel import Session as DBSession

# Skip entire module if workflow models not yet implemented
pytest.importorskip("app.models.workflow", reason="DEV-260: Workflow models not yet implemented")

from app.models.workflow import (  # noqa: E402
    CheckpointStatus,
    CheckpointType,
    Project,
    ProjectDocument,
    ProjectStatus,
    SupervisionMode,
    SyncStatus,
    WorkflowAuditLog,
    WorkflowStatus,
    WorkflowTask,
    WorkflowType,
)


class TestWorkflowEnums:
    """Test enum definitions."""

    def test_workflow_type_values(self):
        """Test WorkflowType enum values match ADR-024."""
        assert WorkflowType.DICHIARAZIONE_REDDITI == "dichiarazione_redditi"
        assert WorkflowType.ADEMPIMENTI_PERIODICI == "adempimenti_periodici"
        assert WorkflowType.APERTURA_CHIUSURA == "apertura_chiusura"
        assert WorkflowType.PENSIONAMENTO == "pensionamento"

    def test_project_status_values(self):
        """Test ProjectStatus enum values."""
        assert ProjectStatus.ACTIVE == "active"
        assert ProjectStatus.ARCHIVED == "archived"
        assert ProjectStatus.DELETED == "deleted"

    def test_workflow_status_values(self):
        """Test WorkflowStatus enum values."""
        assert WorkflowStatus.PENDING == "pending"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.PAUSED == "paused"
        assert WorkflowStatus.WAITING_APPROVAL == "waiting_approval"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"
        assert WorkflowStatus.CANCELLED == "cancelled"

    def test_sync_status_values(self):
        """Test SyncStatus enum values."""
        assert SyncStatus.SYNCED == "synced"
        assert SyncStatus.PENDING_UPLOAD == "pending_upload"
        assert SyncStatus.PENDING_DOWNLOAD == "pending_download"
        assert SyncStatus.CONFLICT == "conflict"
        assert SyncStatus.ERROR == "error"

    def test_supervision_mode_values(self):
        """Test SupervisionMode enum values match ADR-024."""
        assert SupervisionMode.FULL_SUPERVISION == "full_supervision"
        assert SupervisionMode.APPROVAL_REQUIRED == "approval_required"
        assert SupervisionMode.CONFIDENCE_BASED == "confidence_based"
        assert SupervisionMode.REVIEW_CHECKPOINTS == "review_checkpoints"

    def test_checkpoint_type_values(self):
        """Test CheckpointType enum values match ADR-024."""
        assert CheckpointType.DOCUMENT_VALIDATION == "document_validation"
        assert CheckpointType.CALCULATION_REVIEW == "calculation_review"
        assert CheckpointType.DATA_CONFIRMATION == "data_confirmation"
        assert CheckpointType.FINAL_REVIEW == "final_review"
        assert CheckpointType.SUBMISSION_APPROVAL == "submission_approval"

    def test_checkpoint_status_values(self):
        """Test CheckpointStatus enum values."""
        assert CheckpointStatus.PENDING == "pending"
        assert CheckpointStatus.APPROVED == "approved"
        assert CheckpointStatus.REJECTED == "rejected"
        assert CheckpointStatus.SKIPPED == "skipped"


class TestProjectModel:
    """Test Project model."""

    def test_project_creation_minimal(self):
        """Test creating a project with minimal required fields."""
        project = Project(
            name="Mario Rossi - 730/2026",
            user_id=1,
            workflow_type=WorkflowType.DICHIARAZIONE_REDDITI,
        )
        assert project.name == "Mario Rossi - 730/2026"
        assert project.user_id == 1
        assert project.workflow_type == WorkflowType.DICHIARAZIONE_REDDITI
        assert project.status == ProjectStatus.ACTIVE
        assert project.id is not None
        assert project.created_at is not None

    def test_project_creation_full(self):
        """Test creating a project with all fields."""
        settings = {"supervision_mode": "full_supervision", "notifications": True}
        project = Project(
            name="Test Project",
            user_id=1,
            workflow_type=WorkflowType.ADEMPIMENTI_PERIODICI,
            client_id=uuid4(),
            status=ProjectStatus.ARCHIVED,
            settings=settings,
        )
        assert project.settings == settings
        assert project.status == ProjectStatus.ARCHIVED
        assert project.client_id is not None

    def test_project_default_values(self):
        """Test project default values."""
        project = Project(
            name="Test",
            user_id=1,
            workflow_type=WorkflowType.PENSIONAMENTO,
        )
        assert project.status == ProjectStatus.ACTIVE
        assert project.settings == {}
        assert project.client_id is None

    def test_project_updated_at(self):
        """Test project updated_at field."""
        project = Project(
            name="Test",
            user_id=1,
            workflow_type=WorkflowType.APERTURA_CHIUSURA,
        )
        assert project.updated_at is not None
        assert project.updated_at >= project.created_at


class TestProjectDocumentModel:
    """Test ProjectDocument model."""

    def test_document_creation_minimal(self):
        """Test creating a document with minimal required fields."""
        project_id = uuid4()
        doc = ProjectDocument(
            project_id=project_id,
            filename="fattura_001.pdf",
            cloud_path="projects/123/fattura_001.pdf",
        )
        assert doc.project_id == project_id
        assert doc.filename == "fattura_001.pdf"
        assert doc.cloud_path == "projects/123/fattura_001.pdf"
        assert doc.sync_status == SyncStatus.SYNCED
        assert doc.id is not None

    def test_document_creation_full(self):
        """Test creating a document with all fields."""
        project_id = uuid4()
        doc = ProjectDocument(
            project_id=project_id,
            filename="cu_2025.pdf",
            cloud_path="projects/123/cu_2025.pdf",
            local_path="/Users/mario/Documents/cu_2025.pdf",
            sync_status=SyncStatus.PENDING_UPLOAD,
            checksum="sha256:abc123...",
            document_type="certificazione_unica",
            file_size=1024 * 500,
            mime_type="application/pdf",
        )
        assert doc.local_path == "/Users/mario/Documents/cu_2025.pdf"
        assert doc.sync_status == SyncStatus.PENDING_UPLOAD
        assert doc.checksum == "sha256:abc123..."
        assert doc.document_type == "certificazione_unica"
        assert doc.file_size == 1024 * 500
        assert doc.mime_type == "application/pdf"

    def test_document_default_values(self):
        """Test document default values."""
        doc = ProjectDocument(
            project_id=uuid4(),
            filename="test.pdf",
            cloud_path="test/test.pdf",
        )
        assert doc.sync_status == SyncStatus.SYNCED
        assert doc.local_path is None
        assert doc.checksum is None
        assert doc.document_type is None


class TestWorkflowTaskModel:
    """Test WorkflowTask model."""

    def test_task_creation_minimal(self):
        """Test creating a workflow task with minimal fields."""
        project_id = uuid4()
        task = WorkflowTask(
            project_id=project_id,
            workflow_definition_id="dichiarazione_redditi_v1",
        )
        assert task.project_id == project_id
        assert task.workflow_definition_id == "dichiarazione_redditi_v1"
        assert task.status == WorkflowStatus.PENDING
        assert task.current_step is None
        assert task.state == {}
        assert task.checkpoints == []

    def test_task_creation_full(self):
        """Test creating a workflow task with all fields."""
        project_id = uuid4()
        state = {"documents_collected": True, "irpef_calculated": False}
        checkpoints = [
            {
                "type": "document_validation",
                "status": "approved",
                "approved_at": "2026-01-30T10:00:00",
            }
        ]
        task = WorkflowTask(
            project_id=project_id,
            workflow_definition_id="dichiarazione_redditi_v1",
            status=WorkflowStatus.RUNNING,
            current_step="calculate_irpef",
            state=state,
            checkpoints=checkpoints,
            supervision_mode=SupervisionMode.APPROVAL_REQUIRED,
            started_at=datetime.utcnow(),
        )
        assert task.status == WorkflowStatus.RUNNING
        assert task.current_step == "calculate_irpef"
        assert task.state == state
        assert task.checkpoints == checkpoints
        assert task.supervision_mode == SupervisionMode.APPROVAL_REQUIRED
        assert task.started_at is not None

    def test_task_default_supervision_mode(self):
        """Test task default supervision mode is FULL_SUPERVISION."""
        task = WorkflowTask(
            project_id=uuid4(),
            workflow_definition_id="test_v1",
        )
        assert task.supervision_mode == SupervisionMode.FULL_SUPERVISION


class TestWorkflowAuditLogModel:
    """Test WorkflowAuditLog model."""

    def test_audit_log_creation_system(self):
        """Test creating an audit log entry from system."""
        task_id = uuid4()
        log = WorkflowAuditLog(
            workflow_task_id=task_id,
            action="workflow_started",
            actor_type="system",
            details={"workflow_definition": "dichiarazione_redditi_v1"},
        )
        assert log.workflow_task_id == task_id
        assert log.action == "workflow_started"
        assert log.actor_type == "system"
        assert log.actor_id is None
        assert log.details == {"workflow_definition": "dichiarazione_redditi_v1"}

    def test_audit_log_creation_user(self):
        """Test creating an audit log entry from user."""
        task_id = uuid4()
        log = WorkflowAuditLog(
            workflow_task_id=task_id,
            action="checkpoint_approved",
            actor_type="user",
            actor_id=1,
            details={
                "checkpoint_type": "document_validation",
                "comment": "Documenti verificati",
            },
        )
        assert log.actor_type == "user"
        assert log.actor_id == 1

    def test_audit_log_default_values(self):
        """Test audit log default values."""
        log = WorkflowAuditLog(
            workflow_task_id=uuid4(),
            action="test_action",
            actor_type="system",
        )
        assert log.details == {}
        assert log.actor_id is None
        assert log.created_at is not None

    def test_audit_log_gdpr_fields(self):
        """Test audit log has GDPR-required fields."""
        log = WorkflowAuditLog(
            workflow_task_id=uuid4(),
            action="data_processed",
            actor_type="system",
            details={
                "data_category": "financial",
                "processing_purpose": "tax_calculation",
                "legal_basis": "contract",
            },
        )
        # GDPR requires tracking what, who, when, and why
        assert log.action is not None  # what
        assert log.actor_type is not None  # who (type)
        assert log.created_at is not None  # when
        assert log.details.get("processing_purpose") is not None  # why


class TestModelRelationships:
    """Test model relationships (integration tests requiring DB)."""

    @pytest.fixture
    def db_session(self, test_db_session):
        """Get database session from fixture."""
        return test_db_session

    @pytest.mark.skip(reason="Requires database setup - will run in integration tests")
    def test_project_documents_relationship(self, db_session: DBSession):
        """Test Project -> ProjectDocument relationship."""
        project = Project(
            name="Test Project",
            user_id=1,
            workflow_type=WorkflowType.DICHIARAZIONE_REDDITI,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        doc = ProjectDocument(
            project_id=project.id,
            filename="test.pdf",
            cloud_path="test/test.pdf",
        )
        db_session.add(doc)
        db_session.commit()

        # Verify relationship
        db_session.refresh(project)
        assert len(project.documents) == 1
        assert project.documents[0].filename == "test.pdf"

    @pytest.mark.skip(reason="Requires database setup - will run in integration tests")
    def test_project_workflow_tasks_relationship(self, db_session: DBSession):
        """Test Project -> WorkflowTask relationship."""
        project = Project(
            name="Test Project",
            user_id=1,
            workflow_type=WorkflowType.ADEMPIMENTI_PERIODICI,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        task = WorkflowTask(
            project_id=project.id,
            workflow_definition_id="f24_v1",
        )
        db_session.add(task)
        db_session.commit()

        # Verify relationship
        db_session.refresh(project)
        assert len(project.workflow_tasks) == 1
        assert project.workflow_tasks[0].workflow_definition_id == "f24_v1"

    @pytest.mark.skip(reason="Requires database setup - will run in integration tests")
    def test_workflow_task_audit_log_relationship(self, db_session: DBSession):
        """Test WorkflowTask -> WorkflowAuditLog relationship."""
        project = Project(
            name="Test Project",
            user_id=1,
            workflow_type=WorkflowType.PENSIONAMENTO,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        task = WorkflowTask(
            project_id=project.id,
            workflow_definition_id="pensionamento_v1",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        log = WorkflowAuditLog(
            workflow_task_id=task.id,
            action="task_created",
            actor_type="system",
        )
        db_session.add(log)
        db_session.commit()

        # Verify relationship
        db_session.refresh(task)
        assert len(task.audit_logs) == 1
        assert task.audit_logs[0].action == "task_created"
