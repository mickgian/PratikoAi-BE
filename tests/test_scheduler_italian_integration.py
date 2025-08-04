"""Tests for Italian document collection scheduler integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.scheduler_service import (
    SchedulerService, 
    ScheduledTask, 
    ScheduleInterval,
    setup_default_tasks,
    scheduler_service
)


class TestSchedulerItalianIntegration:
    """Test scheduler integration with Italian document collection."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler instance."""
        return SchedulerService()

    def test_schedule_interval_enum_has_4_hours(self):
        """Test that 4-hour interval is available."""
        assert ScheduleInterval.EVERY_4_HOURS == "4_hours"
        assert hasattr(ScheduleInterval, 'EVERY_4_HOURS')

    def test_calculate_next_run_4_hours(self, scheduler):
        """Test 4-hour interval calculation."""
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        next_run = scheduler._calculate_next_run(ScheduleInterval.EVERY_4_HOURS, base_time)
        
        expected = base_time + timedelta(hours=4)
        assert next_run == expected

    @patch('app.services.italian_document_collector.collect_italian_documents_task')
    def test_setup_default_tasks_includes_italian_collection(self, mock_collect_task):
        """Test that default tasks setup includes Italian document collection."""
        # Clear existing tasks
        scheduler_service.tasks.clear()
        
        setup_default_tasks()
        
        # Check that Italian document collection task was added
        assert "italian_documents_4h" in scheduler_service.tasks
        
        italian_task = scheduler_service.tasks["italian_documents_4h"]
        assert italian_task.name == "italian_documents_4h"
        assert italian_task.interval == ScheduleInterval.EVERY_4_HOURS
        assert italian_task.enabled is True
        assert italian_task.function == mock_collect_task

    def test_setup_default_tasks_includes_metrics_task(self):
        """Test that metrics task is still included alongside Italian collection."""
        # Clear existing tasks  
        scheduler_service.tasks.clear()
        
        setup_default_tasks()
        
        # Check both tasks are present
        assert "metrics_report_12h" in scheduler_service.tasks
        assert "italian_documents_4h" in scheduler_service.tasks
        
        # Verify metrics task configuration
        metrics_task = scheduler_service.tasks["metrics_report_12h"]
        assert metrics_task.interval == ScheduleInterval.EVERY_12_HOURS

    @patch('app.services.italian_document_collector.collect_italian_documents_task')
    async def test_italian_task_execution(self, mock_collect_task, scheduler):
        """Test execution of Italian document collection task."""
        mock_collect_task.return_value = None
        
        # Create and add Italian collection task
        italian_task = ScheduledTask(
            name="test_italian_collection",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=mock_collect_task,
            enabled=True
        )
        
        scheduler.add_task(italian_task)
        
        # Execute the task
        await scheduler._execute_task(italian_task)
        
        # Verify task was called
        mock_collect_task.assert_called_once()
        
        # Verify task timing was updated
        assert italian_task.last_run is not None
        assert italian_task.next_run is not None

    async def test_italian_task_error_handling(self, scheduler):
        """Test error handling during Italian collection task execution."""
        # Create task that raises exception
        def failing_task():
            raise Exception("Collection failed")
        
        italian_task = ScheduledTask(
            name="test_failing_italian_collection",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=failing_task,
            enabled=True
        )
        
        scheduler.add_task(italian_task)
        
        # Execute task - should handle error gracefully
        await scheduler._execute_task(italian_task)
        
        # Task timing should still be updated despite error
        assert italian_task.last_run is not None
        assert italian_task.next_run is not None

    def test_task_status_includes_italian_collection(self, scheduler):
        """Test that task status includes Italian collection task."""
        # Add Italian collection task
        italian_task = ScheduledTask(
            name="italian_documents_4h",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=lambda: None,
            enabled=True
        )
        
        scheduler.add_task(italian_task)
        
        status = scheduler.get_task_status()
        
        assert "italian_documents_4h" in status
        task_status = status["italian_documents_4h"]
        assert task_status["enabled"] is True
        assert task_status["interval"] == "4_hours"

    async def test_manual_italian_task_execution(self, scheduler):
        """Test manual execution of Italian collection task."""
        executed = False
        
        def mock_italian_task():
            nonlocal executed
            executed = True
        
        italian_task = ScheduledTask(
            name="italian_documents_4h",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=mock_italian_task,
            enabled=True
        )
        
        scheduler.add_task(italian_task)
        
        # Run task manually
        success = await scheduler.run_task_now("italian_documents_4h")
        
        assert success is True
        assert executed is True

    def test_enable_disable_italian_task(self, scheduler):
        """Test enabling and disabling Italian collection task."""
        italian_task = ScheduledTask(
            name="italian_documents_4h",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=lambda: None,
            enabled=True
        )
        
        scheduler.add_task(italian_task)
        
        # Disable task
        result = scheduler.disable_task("italian_documents_4h")
        assert result is True
        assert scheduler.tasks["italian_documents_4h"].enabled is False
        
        # Enable task
        result = scheduler.enable_task("italian_documents_4h")
        assert result is True
        assert scheduler.tasks["italian_documents_4h"].enabled is True

    def test_remove_italian_task(self, scheduler):
        """Test removing Italian collection task."""
        italian_task = ScheduledTask(
            name="italian_documents_4h",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=lambda: None,
            enabled=True
        )
        
        scheduler.add_task(italian_task)
        assert "italian_documents_4h" in scheduler.tasks
        
        # Remove task  
        result = scheduler.remove_task("italian_documents_4h")
        assert result is True
        assert "italian_documents_4h" not in scheduler.tasks

    @patch('app.services.scheduler_service.logger')
    def test_scheduler_logging_includes_italian_task(self, mock_logger, scheduler):
        """Test that scheduler logging includes Italian task information."""
        italian_task = ScheduledTask(
            name="italian_documents_4h",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=lambda: None,
            enabled=True
        )
        
        scheduler.add_task(italian_task)
        
        # Verify logging was called with Italian task info
        mock_logger.info.assert_called_with(
            "Added scheduled task: italian_documents_4h (4_hours)"
        )

    async def test_scheduler_loop_processes_italian_task(self, scheduler):
        """Test that scheduler loop processes Italian collection task when due."""
        executed = False
        
        def mock_italian_task():
            nonlocal executed
            executed = True
        
        # Create task that's due to run (past next_run time)
        past_time = datetime.utcnow() - timedelta(minutes=1)
        italian_task = ScheduledTask(
            name="italian_documents_4h",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=mock_italian_task,
            enabled=True,
            next_run=past_time
        )
        
        scheduler.add_task(italian_task)
        
        # Mock current time to be after next_run
        with patch('app.services.scheduler_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow()
            
            # Execute one iteration of scheduler loop logic
            current_time = datetime.utcnow()
            if current_time >= italian_task.next_run:
                await scheduler._execute_task(italian_task)
        
        assert executed is True

    def test_italian_task_configuration_consistency(self):
        """Test that Italian task configuration is consistent across setup."""
        # Clear tasks
        scheduler_service.tasks.clear()
        
        setup_default_tasks()
        
        italian_task = scheduler_service.tasks.get("italian_documents_4h")
        assert italian_task is not None
        
        # Verify task properties are consistent with requirements
        assert italian_task.interval == ScheduleInterval.EVERY_4_HOURS
        assert italian_task.enabled is True
        assert italian_task.args == ()
        assert italian_task.kwargs == {}
        
        # Verify next_run was calculated
        assert italian_task.next_run is not None
        assert italian_task.next_run > datetime.utcnow()

    @patch('app.services.italian_document_collector.collect_italian_documents_task')
    async def test_scheduler_integration_with_real_task_function(self, mock_collect_task):
        """Test scheduler integration with actual collection task function."""
        # Mock the actual collection task
        mock_collect_task.return_value = None
        
        # Clear and setup tasks
        scheduler_service.tasks.clear()
        setup_default_tasks()
        
        # Get the Italian task
        italian_task = scheduler_service.tasks["italian_documents_4h"]
        
        # Execute the task
        await scheduler_service._execute_task(italian_task)
        
        # Verify the real function was called
        mock_collect_task.assert_called_once()

    def test_scheduler_task_interval_ordering(self):
        """Test that task intervals are properly ordered by frequency."""
        intervals = [
            ScheduleInterval.MINUTES_30,
            ScheduleInterval.HOURLY,
            ScheduleInterval.EVERY_4_HOURS,
            ScheduleInterval.EVERY_12_HOURS,
            ScheduleInterval.DAILY,
            ScheduleInterval.WEEKLY
        ]
        
        # Calculate deltas for each interval
        base_time = datetime.utcnow()
        scheduler = SchedulerService()
        
        deltas = []
        for interval in intervals:
            next_time = scheduler._calculate_next_run(interval, base_time)
            delta = next_time - base_time
            deltas.append(delta.total_seconds())
        
        # Verify intervals are in ascending order
        assert deltas == sorted(deltas)
        
        # Verify 4-hour interval is between hourly and 12-hour
        four_hour_delta = deltas[2]  # EVERY_4_HOURS
        hourly_delta = deltas[1]     # HOURLY  
        twelve_hour_delta = deltas[3] # EVERY_12_HOURS
        
        assert hourly_delta < four_hour_delta < twelve_hour_delta
        assert four_hour_delta == 4 * 3600  # 4 hours in seconds