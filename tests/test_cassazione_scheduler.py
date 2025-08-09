"""
Test suite for Cassazione scraper scheduler integration.

This module tests the integration between the Cassazione scraper
and the job scheduling system for automated updates.
"""

import pytest
from datetime import datetime, date, timedelta, time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from app.services.scrapers.cassazione_scheduler import (
    CassazioneScheduler,
    ScheduledScrapingJob,
    ScheduleFrequency,
    JobStatus,
    SchedulingError
)
# Mock scheduler_service import to avoid async loop issues during testing
class MockSchedulerService:
    def add_job(self, *args, **kwargs):
        return "mock_job_id"
    def remove_job(self, job_id):
        pass
    def pause_job(self, job_id):
        pass
    def resume_job(self, job_id):
        pass

scheduler_service = MockSchedulerService()
from app.services.scrapers.cassazione_scraper import CassazioneScraper, ScrapingResult, CourtSection


class TestScheduleFrequencyEnum:
    """Test scheduling frequency enumeration."""
    
    def test_frequency_values(self):
        """Test that all frequency values are defined."""
        assert ScheduleFrequency.DAILY.value == "daily"
        assert ScheduleFrequency.WEEKLY.value == "weekly"
        assert ScheduleFrequency.MONTHLY.value == "monthly"
        assert ScheduleFrequency.HOURLY.value == "hourly"
    
    def test_frequency_cron_expressions(self):
        """Test getting cron expressions for frequencies."""
        assert ScheduleFrequency.DAILY.cron_expression() == "0 2 * * *"  # 2 AM daily
        assert ScheduleFrequency.WEEKLY.cron_expression() == "0 2 * * 0"  # 2 AM Sunday
        assert ScheduleFrequency.MONTHLY.cron_expression() == "0 2 1 * *"  # 2 AM 1st of month
        assert ScheduleFrequency.HOURLY.cron_expression() == "0 * * * *"  # Every hour


class TestJobStatusEnum:
    """Test job status enumeration."""
    
    def test_status_values(self):
        """Test that all status values are defined."""
        assert JobStatus.SCHEDULED.value == "scheduled"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.PAUSED.value == "paused"
        assert JobStatus.CANCELLED.value == "cancelled"
    
    def test_status_transitions(self):
        """Test valid status transitions."""
        # Scheduled can go to running or cancelled
        assert JobStatus.SCHEDULED.can_transition_to(JobStatus.RUNNING) is True
        assert JobStatus.SCHEDULED.can_transition_to(JobStatus.CANCELLED) is True
        assert JobStatus.SCHEDULED.can_transition_to(JobStatus.COMPLETED) is False
        
        # Running can go to completed, failed, or paused
        assert JobStatus.RUNNING.can_transition_to(JobStatus.COMPLETED) is True
        assert JobStatus.RUNNING.can_transition_to(JobStatus.FAILED) is True
        assert JobStatus.RUNNING.can_transition_to(JobStatus.PAUSED) is True
        assert JobStatus.RUNNING.can_transition_to(JobStatus.SCHEDULED) is False


class TestScheduledScrapingJobModel:
    """Test the scheduled scraping job model."""
    
    def test_create_basic_job(self):
        """Test creating a basic scheduled job."""
        job = ScheduledScrapingJob(
            job_id="weekly_civil_updates",
            name="Weekly Civil Section Updates",
            frequency=ScheduleFrequency.WEEKLY,
            court_sections=[CourtSection.CIVILE],
            days_back=7
        )
        
        assert job.job_id == "weekly_civil_updates"
        assert job.frequency == ScheduleFrequency.WEEKLY
        assert CourtSection.CIVILE in job.court_sections
        assert job.status == JobStatus.SCHEDULED  # Default
        assert job.days_back == 7
    
    def test_create_job_with_full_config(self):
        """Test creating job with complete configuration."""
        next_run = datetime.now() + timedelta(days=1)
        
        job = ScheduledScrapingJob(
            job_id="comprehensive_updates",
            name="Comprehensive Daily Updates",
            description="Daily updates for all court sections",
            frequency=ScheduleFrequency.DAILY,
            court_sections=[CourtSection.CIVILE, CourtSection.TRIBUTARIA, CourtSection.LAVORO],
            days_back=1,
            max_decisions_per_run=1000,
            enabled=True,
            next_run_time=next_run,
            retry_on_failure=True,
            max_retries=3,
            notification_emails=["admin@pratiko.ai"],
            scraping_config={
                "rate_limit_delay": 2.0,
                "timeout_seconds": 30,
                "respect_robots_txt": True
            }
        )
        
        assert len(job.court_sections) == 3
        assert job.max_decisions_per_run == 1000
        assert job.enabled is True
        assert job.retry_on_failure is True
        assert job.max_retries == 3
        assert len(job.notification_emails) == 1
        assert job.scraping_config["rate_limit_delay"] == 2.0
    
    def test_job_validation_invalid_frequency(self):
        """Test validation with invalid frequency configuration."""
        with pytest.raises(ValueError, match="Days back must be positive"):
            ScheduledScrapingJob(
                job_id="test_job",
                name="Test Job",
                frequency=ScheduleFrequency.WEEKLY,
                days_back=-1  # Invalid
            )
    
    def test_job_validation_empty_sections(self):
        """Test validation with empty court sections."""
        with pytest.raises(ValueError, match="At least one court section must be specified"):
            ScheduledScrapingJob(
                job_id="test_job",
                name="Test Job",
                frequency=ScheduleFrequency.WEEKLY,
                court_sections=[]  # Invalid
            )
    
    def test_calculate_next_run_time(self):
        """Test calculating next run time based on frequency."""
        daily_job = ScheduledScrapingJob(
            job_id="daily_job",
            name="Daily Job",
            frequency=ScheduleFrequency.DAILY
        )
        
        next_run = daily_job.calculate_next_run_time()
        
        # Should be tomorrow at 2 AM
        tomorrow = (datetime.now() + timedelta(days=1)).replace(
            hour=2, minute=0, second=0, microsecond=0
        )
        assert next_run.date() == tomorrow.date()
        assert next_run.hour == 2
    
    def test_update_job_status(self):
        """Test updating job status with validation."""
        job = ScheduledScrapingJob(
            job_id="test_job",
            name="Test Job",
            frequency=ScheduleFrequency.WEEKLY
        )
        
        # Valid transition
        job.update_status(JobStatus.RUNNING)
        assert job.status == JobStatus.RUNNING
        assert job.status_updated_at is not None
        
        # Valid completion
        job.update_status(JobStatus.COMPLETED, "Successfully processed 50 decisions")
        assert job.status == JobStatus.COMPLETED
        assert "50 decisions" in job.status_message
        
        # Invalid transition should raise error
        with pytest.raises(ValueError, match="Invalid status transition"):
            job.update_status(JobStatus.SCHEDULED)  # Can't go back to scheduled from completed


class TestCassazioneScheduler:
    """Test the main Cassazione scheduler."""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance for testing."""
        return CassazioneScheduler()
    
    @pytest.fixture
    def sample_job(self):
        """Create sample job for testing."""
        return ScheduledScrapingJob(
            job_id="test_civil_weekly",
            name="Weekly Civil Updates",
            frequency=ScheduleFrequency.WEEKLY,
            court_sections=[CourtSection.CIVILE],
            days_back=7
        )
    
    def test_register_job(self, scheduler, sample_job):
        """Test registering a new scheduled job."""
        with patch.object(scheduler_service, 'add_job') as mock_add_job:
            mock_add_job.return_value = "scheduler_job_id_123"
            
            result = scheduler.register_job(sample_job)
            
            assert result is True
            mock_add_job.assert_called_once()
            
            # Check that the job was called with correct parameters
            call_args = mock_add_job.call_args
            assert call_args[1]['trigger'] == 'cron'
            assert call_args[1]['day_of_week'] == '0'  # Sunday for weekly
    
    def test_register_job_duplicate_id(self, scheduler, sample_job):
        """Test registering job with duplicate ID."""
        scheduler._registered_jobs[sample_job.job_id] = sample_job
        
        with pytest.raises(SchedulingError, match="Job with ID .* already exists"):
            scheduler.register_job(sample_job)
    
    def test_unregister_job(self, scheduler, sample_job):
        """Test unregistering an existing job."""
        # First register the job
        sample_job.scheduler_job_id = "scheduler_job_123"
        scheduler._registered_jobs[sample_job.job_id] = sample_job
        
        with patch.object(scheduler_service, 'remove_job') as mock_remove_job:
            result = scheduler.unregister_job(sample_job.job_id)
            
            assert result is True
            mock_remove_job.assert_called_once_with("scheduler_job_123")
            assert sample_job.job_id not in scheduler._registered_jobs
    
    def test_unregister_nonexistent_job(self, scheduler):
        """Test unregistering job that doesn't exist."""
        with pytest.raises(SchedulingError, match="Job with ID .* not found"):
            scheduler.unregister_job("nonexistent_job")
    
    def test_pause_job(self, scheduler, sample_job):
        """Test pausing an active job."""
        sample_job.scheduler_job_id = "scheduler_job_123"
        sample_job.status = JobStatus.SCHEDULED
        scheduler._registered_jobs[sample_job.job_id] = sample_job
        
        with patch.object(scheduler_service, 'pause_job') as mock_pause_job:
            result = scheduler.pause_job(sample_job.job_id)
            
            assert result is True
            mock_pause_job.assert_called_once_with("scheduler_job_123")
            assert sample_job.status == JobStatus.PAUSED
    
    def test_resume_job(self, scheduler, sample_job):
        """Test resuming a paused job."""
        sample_job.scheduler_job_id = "scheduler_job_123"
        sample_job.status = JobStatus.PAUSED
        scheduler._registered_jobs[sample_job.job_id] = sample_job
        
        with patch.object(scheduler_service, 'resume_job') as mock_resume_job:
            result = scheduler.resume_job(sample_job.job_id)
            
            assert result is True
            mock_resume_job.assert_called_once_with("scheduler_job_123")
            assert sample_job.status == JobStatus.SCHEDULED
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job(self, scheduler, sample_job):
        """Test executing a scraping job."""
        scheduler._registered_jobs[sample_job.job_id] = sample_job
        
        mock_scraping_result = ScrapingResult(
            decisions_found=25,
            decisions_processed=24,
            decisions_saved=23,
            errors=1,
            duration_seconds=180
        )
        
        with patch('app.services.scrapers.cassazione_scraper.CassazioneScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_recent_decisions.return_value = mock_scraping_result
            mock_scraper_class.return_value = mock_scraper
            
            result = await scheduler.execute_scraping_job(sample_job.job_id)
            
            assert result is not None
            assert result.decisions_found == 25
            assert result.decisions_saved == 23
            
            # Check that job status was updated
            assert sample_job.status == JobStatus.COMPLETED
            assert sample_job.last_run_time is not None
            assert sample_job.last_run_result is not None
    
    @pytest.mark.asyncio
    async def test_execute_scraping_job_with_failure(self, scheduler, sample_job):
        """Test executing scraping job that fails."""
        sample_job.retry_on_failure = True
        sample_job.max_retries = 2
        scheduler._registered_jobs[sample_job.job_id] = sample_job
        
        with patch('app.services.scrapers.cassazione_scraper.CassazioneScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_recent_decisions.side_effect = Exception("Network error")
            mock_scraper_class.return_value = mock_scraper
            
            result = await scheduler.execute_scraping_job(sample_job.job_id)
            
            assert result is None
            assert sample_job.status == JobStatus.FAILED
            assert "Network error" in sample_job.status_message
            assert sample_job.retry_count > 0
    
    def test_get_job_status(self, scheduler, sample_job):
        """Test getting job status information."""
        sample_job.status = JobStatus.RUNNING
        sample_job.last_run_time = datetime.now() - timedelta(minutes=30)
        scheduler._registered_jobs[sample_job.job_id] = sample_job
        
        status = scheduler.get_job_status(sample_job.job_id)
        
        assert status["job_id"] == sample_job.job_id
        assert status["status"] == "running"
        assert status["last_run_time"] is not None
        assert "next_run_time" in status
    
    def test_get_all_jobs(self, scheduler):
        """Test getting all registered jobs."""
        job1 = ScheduledScrapingJob(
            job_id="job1",
            name="Job 1",
            frequency=ScheduleFrequency.DAILY
        )
        job2 = ScheduledScrapingJob(
            job_id="job2", 
            name="Job 2",
            frequency=ScheduleFrequency.WEEKLY
        )
        
        scheduler._registered_jobs["job1"] = job1
        scheduler._registered_jobs["job2"] = job2
        
        all_jobs = scheduler.get_all_jobs()
        
        assert len(all_jobs) == 2
        assert any(job["job_id"] == "job1" for job in all_jobs)
        assert any(job["job_id"] == "job2" for job in all_jobs)
    
    def test_get_jobs_by_status(self, scheduler):
        """Test filtering jobs by status."""
        running_job = ScheduledScrapingJob(
            job_id="running_job",
            name="Running Job",
            frequency=ScheduleFrequency.DAILY
        )
        running_job.status = JobStatus.RUNNING
        
        completed_job = ScheduledScrapingJob(
            job_id="completed_job",
            name="Completed Job", 
            frequency=ScheduleFrequency.WEEKLY
        )
        completed_job.status = JobStatus.COMPLETED
        
        scheduler._registered_jobs["running_job"] = running_job
        scheduler._registered_jobs["completed_job"] = completed_job
        
        running_jobs = scheduler.get_jobs_by_status(JobStatus.RUNNING)
        completed_jobs = scheduler.get_jobs_by_status(JobStatus.COMPLETED)
        
        assert len(running_jobs) == 1
        assert len(completed_jobs) == 1
        assert running_jobs[0]["job_id"] == "running_job"
        assert completed_jobs[0]["job_id"] == "completed_job"


class TestSchedulerNotifications:
    """Test notification system for scheduled jobs."""
    
    @pytest.fixture
    def scheduler_with_notifications(self):
        """Create scheduler with notification system."""
        scheduler = CassazioneScheduler()
        scheduler.enable_notifications = True
        return scheduler
    
    @pytest.mark.asyncio
    async def test_send_job_completion_notification(self, scheduler_with_notifications):
        """Test sending notification on job completion."""
        job = ScheduledScrapingJob(
            job_id="test_job",
            name="Test Job",
            frequency=ScheduleFrequency.WEEKLY,
            notification_emails=["admin@pratiko.ai", "legal@pratiko.ai"]
        )
        
        result = ScrapingResult(
            decisions_found=50,
            decisions_saved=48,
            errors=2,
            duration_seconds=300
        )
        
        with patch('app.services.email_service.send_email') as mock_send_email:
            await scheduler_with_notifications._send_job_notification(
                job, JobStatus.COMPLETED, result
            )
            
            assert mock_send_email.call_count == 2  # Two email recipients
            
            # Check email content
            call_args = mock_send_email.call_args_list[0]
            assert "Test Job" in call_args[1]["subject"]
            assert "completed successfully" in call_args[1]["subject"].lower()
            assert "48 decisions saved" in call_args[1]["body"]
    
    @pytest.mark.asyncio
    async def test_send_job_failure_notification(self, scheduler_with_notifications):
        """Test sending notification on job failure."""
        job = ScheduledScrapingJob(
            job_id="failing_job",
            name="Failing Job", 
            frequency=ScheduleFrequency.DAILY,
            notification_emails=["admin@pratiko.ai"]
        )
        
        error_message = "Network timeout during scraping"
        
        with patch('app.services.email_service.send_email') as mock_send_email:
            await scheduler_with_notifications._send_job_notification(
                job, JobStatus.FAILED, error_message=error_message
            )
            
            assert mock_send_email.call_count == 1
            
            # Check email content for failure
            call_args = mock_send_email.call_args
            assert "failed" in call_args[1]["subject"].lower()
            assert error_message in call_args[1]["body"]
    
    def test_notification_throttling(self, scheduler_with_notifications):
        """Test that notifications are throttled to prevent spam."""
        job = ScheduledScrapingJob(
            job_id="throttled_job",
            name="Throttled Job",
            frequency=ScheduleFrequency.HOURLY,  # High frequency
            notification_emails=["admin@pratiko.ai"]
        )
        
        # Set last notification time to recent
        scheduler_with_notifications._last_notification_times[job.job_id] = datetime.now()
        
        # Should not send notification due to throttling
        should_send = scheduler_with_notifications._should_send_notification(
            job, JobStatus.COMPLETED
        )
        
        assert should_send is False
        
        # But should send for failures even if throttled
        should_send_failure = scheduler_with_notifications._should_send_notification(
            job, JobStatus.FAILED
        )
        
        assert should_send_failure is True


class TestSchedulerPersistence:
    """Test persistence of scheduling configuration."""
    
    @pytest.fixture
    def scheduler_with_persistence(self):
        """Create scheduler with persistence enabled."""
        scheduler = CassazioneScheduler()
        scheduler.persistence_enabled = True
        return scheduler
    
    @pytest.mark.asyncio
    async def test_save_job_configuration(self, scheduler_with_persistence):
        """Test saving job configuration to database."""
        job = ScheduledScrapingJob(
            job_id="persistent_job",
            name="Persistent Job",
            frequency=ScheduleFrequency.WEEKLY,
            court_sections=[CourtSection.CIVILE, CourtSection.TRIBUTARIA]
        )
        
        with patch('app.services.database.database_service') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            await scheduler_with_persistence.save_job_configuration(job)
            
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_job_configurations(self, scheduler_with_persistence):
        """Test loading job configurations from database."""
        with patch('app.services.database.database_service') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock database results
            mock_job_records = [
                Mock(
                    job_id="job1",
                    name="Job 1",
                    frequency="weekly",
                    court_sections=["civile"],
                    enabled=True
                ),
                Mock(
                    job_id="job2",
                    name="Job 2", 
                    frequency="daily",
                    court_sections=["tributaria", "lavoro"],
                    enabled=False
                )
            ]
            mock_session.exec.return_value = mock_job_records
            
            loaded_jobs = await scheduler_with_persistence.load_job_configurations()
            
            assert len(loaded_jobs) == 2
            assert loaded_jobs[0].job_id == "job1"
            assert loaded_jobs[1].job_id == "job2"
    
    @pytest.mark.asyncio
    async def test_update_job_execution_history(self, scheduler_with_persistence):
        """Test updating job execution history."""
        job = ScheduledScrapingJob(
            job_id="history_job",
            name="History Job",
            frequency=ScheduleFrequency.DAILY
        )
        
        result = ScrapingResult(
            decisions_found=30,
            decisions_saved=28,
            errors=2,
            duration_seconds=240
        )
        
        with patch('app.services.database.database_service') as mock_db:
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            await scheduler_with_persistence.update_job_execution_history(job, result)
            
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()


class TestSchedulerIntegrationScenarios:
    """Test real-world scheduling scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_weekly_update_scenario(self):
        """Test complete weekly update scenario."""
        scheduler = CassazioneScheduler()
        
        # Create weekly job for multiple sections
        weekly_job = ScheduledScrapingJob(
            job_id="comprehensive_weekly",
            name="Comprehensive Weekly Updates",
            frequency=ScheduleFrequency.WEEKLY,
            court_sections=[CourtSection.CIVILE, CourtSection.TRIBUTARIA],
            days_back=7,
            max_decisions_per_run=500,
            notification_emails=["admin@pratiko.ai"]
        )
        
        # Register the job
        with patch.object(scheduler_service, 'add_job') as mock_add_job:
            mock_add_job.return_value = "scheduler_job_456"
            scheduler.register_job(weekly_job)
        
        # Simulate job execution
        mock_result = ScrapingResult(
            decisions_found=150,
            decisions_processed=148,
            decisions_saved=145,
            errors=3,
            duration_seconds=600
        )
        
        with patch('app.services.scrapers.cassazione_scraper.CassazioneScraper') as mock_scraper_class:
            mock_scraper = AsyncMock()
            mock_scraper.scrape_recent_decisions.return_value = mock_result
            mock_scraper_class.return_value = mock_scraper
            
            # Execute the job
            result = await scheduler.execute_scraping_job(weekly_job.job_id)
            
            assert result.decisions_found == 150
            assert result.decisions_saved == 145
            assert weekly_job.status == JobStatus.COMPLETED
            assert weekly_job.last_run_result is not None
    
    def test_multiple_jobs_with_different_schedules(self):
        """Test managing multiple jobs with different schedules."""
        scheduler = CassazioneScheduler()
        
        jobs = [
            ScheduledScrapingJob(
                job_id="daily_civil",
                name="Daily Civil Updates",
                frequency=ScheduleFrequency.DAILY,
                court_sections=[CourtSection.CIVILE],
                days_back=1
            ),
            ScheduledScrapingJob(
                job_id="weekly_tax", 
                name="Weekly Tax Updates",
                frequency=ScheduleFrequency.WEEKLY,
                court_sections=[CourtSection.TRIBUTARIA],
                days_back=7
            ),
            ScheduledScrapingJob(
                job_id="monthly_comprehensive",
                name="Monthly Comprehensive Update",
                frequency=ScheduleFrequency.MONTHLY,
                court_sections=[CourtSection.CIVILE, CourtSection.TRIBUTARIA, CourtSection.LAVORO],
                days_back=30
            )
        ]
        
        with patch.object(scheduler_service, 'add_job') as mock_add_job:
            mock_add_job.return_value = "mock_scheduler_id"
            
            # Register all jobs
            for job in jobs:
                scheduler.register_job(job)
            
            assert len(scheduler._registered_jobs) == 3
            
            # Verify different cron expressions
            assert mock_add_job.call_count == 3
            call_args_list = mock_add_job.call_args_list
            
            # Daily job should run at 2 AM every day
            daily_call = call_args_list[0]
            assert daily_call[1]['hour'] == 2
            assert 'day_of_week' not in daily_call[1]
            
            # Weekly job should run on Sundays
            weekly_call = call_args_list[1]
            assert weekly_call[1]['day_of_week'] == '0'  # Sunday
            
            # Monthly job should run on 1st of month
            monthly_call = call_args_list[2]
            assert monthly_call[1]['day'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.scrapers.cassazione_scheduler"])