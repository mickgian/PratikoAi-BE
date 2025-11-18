"""Tests for scheduler service."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.scheduler_service import ScheduledTask, ScheduleInterval, SchedulerService


class TestScheduleInterval:
    """Test ScheduleInterval enum."""

    def test_interval_values(self):
        """Test that schedule intervals have correct values."""
        assert ScheduleInterval.MINUTES_30.value == "30_minutes"
        assert ScheduleInterval.HOURLY.value == "hourly"
        assert ScheduleInterval.EVERY_4_HOURS.value == "4_hours"
        assert ScheduleInterval.EVERY_12_HOURS.value == "12_hours"
        assert ScheduleInterval.DAILY.value == "daily"
        assert ScheduleInterval.WEEKLY.value == "weekly"


class TestScheduledTask:
    """Test ScheduledTask dataclass."""

    def test_create_task_minimal(self):
        """Test creating minimal scheduled task."""
        task = ScheduledTask(name="test_task", interval=ScheduleInterval.HOURLY, function=lambda: None)

        assert task.name == "test_task"
        assert task.interval == ScheduleInterval.HOURLY
        assert task.enabled is True
        assert task.run_immediately is False
        assert task.last_run is None
        assert task.next_run is None

    def test_create_task_full(self):
        """Test creating fully configured scheduled task."""
        func = lambda: "test"
        args = ("arg1", "arg2")
        kwargs = {"key": "value"}
        last_run = datetime.now(UTC)

        task = ScheduledTask(
            name="full_task",
            interval=ScheduleInterval.DAILY,
            function=func,
            args=args,
            kwargs=kwargs,
            enabled=False,
            run_immediately=True,
            last_run=last_run,
        )

        assert task.name == "full_task"
        assert task.args == args
        assert task.kwargs == kwargs
        assert task.enabled is False
        assert task.run_immediately is True
        assert task.last_run == last_run


class TestSchedulerService:
    """Test SchedulerService class."""

    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = SchedulerService()

        assert scheduler.tasks == {}
        assert scheduler.running is False
        assert scheduler._task_handle is None

    def test_add_task(self):
        """Test adding a scheduled task."""
        scheduler = SchedulerService()

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=lambda: None)

        scheduler.add_task(task)

        assert "test" in scheduler.tasks
        assert scheduler.tasks["test"] == task
        assert task.kwargs == {}  # Default empty dict
        assert task.next_run is not None  # Next run calculated

    def test_add_task_with_kwargs(self):
        """Test adding task with existing kwargs."""
        scheduler = SchedulerService()

        kwargs = {"key": "value"}
        task = ScheduledTask(name="test", interval=ScheduleInterval.DAILY, function=lambda: None, kwargs=kwargs)

        scheduler.add_task(task)

        assert scheduler.tasks["test"].kwargs == kwargs

    def test_remove_task_success(self):
        """Test removing existing task."""
        scheduler = SchedulerService()

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=lambda: None)
        scheduler.add_task(task)

        result = scheduler.remove_task("test")

        assert result is True
        assert "test" not in scheduler.tasks

    def test_remove_task_not_found(self):
        """Test removing non-existent task."""
        scheduler = SchedulerService()

        result = scheduler.remove_task("nonexistent")

        assert result is False

    def test_enable_task_success(self):
        """Test enabling a disabled task."""
        scheduler = SchedulerService()

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=lambda: None, enabled=False)
        scheduler.add_task(task)

        result = scheduler.enable_task("test")

        assert result is True
        assert scheduler.tasks["test"].enabled is True

    def test_enable_task_not_found(self):
        """Test enabling non-existent task."""
        scheduler = SchedulerService()

        result = scheduler.enable_task("nonexistent")

        assert result is False

    def test_disable_task_success(self):
        """Test disabling an enabled task."""
        scheduler = SchedulerService()

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=lambda: None, enabled=True)
        scheduler.add_task(task)

        result = scheduler.disable_task("test")

        assert result is True
        assert scheduler.tasks["test"].enabled is False

    def test_disable_task_not_found(self):
        """Test disabling non-existent task."""
        scheduler = SchedulerService()

        result = scheduler.disable_task("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_start_scheduler(self):
        """Test starting the scheduler."""
        scheduler = SchedulerService()

        await scheduler.start()

        assert scheduler.running is True
        assert scheduler._task_handle is not None

        # Cleanup
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self):
        """Test starting scheduler when already running."""
        scheduler = SchedulerService()

        await scheduler.start()
        await scheduler.start()  # Second start should be no-op

        assert scheduler.running is True

        # Cleanup
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        scheduler = SchedulerService()

        await scheduler.start()
        await scheduler.stop()

        assert scheduler.running is False

    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self):
        """Test stopping scheduler when not running."""
        scheduler = SchedulerService()

        await scheduler.stop()  # Should not raise error

        assert scheduler.running is False

    def test_calculate_next_run_30_minutes(self):
        """Test calculating next run for 30 minutes interval."""
        scheduler = SchedulerService()
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        next_run = scheduler._calculate_next_run(ScheduleInterval.MINUTES_30, base_time)

        expected = base_time + timedelta(minutes=30)
        assert next_run == expected

    def test_calculate_next_run_hourly(self):
        """Test calculating next run for hourly interval."""
        scheduler = SchedulerService()
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        next_run = scheduler._calculate_next_run(ScheduleInterval.HOURLY, base_time)

        expected = base_time + timedelta(hours=1)
        assert next_run == expected

    def test_calculate_next_run_4_hours(self):
        """Test calculating next run for 4 hours interval."""
        scheduler = SchedulerService()
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        next_run = scheduler._calculate_next_run(ScheduleInterval.EVERY_4_HOURS, base_time)

        expected = base_time + timedelta(hours=4)
        assert next_run == expected

    def test_calculate_next_run_12_hours(self):
        """Test calculating next run for 12 hours interval."""
        scheduler = SchedulerService()
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        next_run = scheduler._calculate_next_run(ScheduleInterval.EVERY_12_HOURS, base_time)

        expected = base_time + timedelta(hours=12)
        assert next_run == expected

    def test_calculate_next_run_daily(self):
        """Test calculating next run for daily interval."""
        scheduler = SchedulerService()
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        next_run = scheduler._calculate_next_run(ScheduleInterval.DAILY, base_time)

        expected = base_time + timedelta(days=1)
        assert next_run == expected

    def test_calculate_next_run_weekly(self):
        """Test calculating next run for weekly interval."""
        scheduler = SchedulerService()
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        next_run = scheduler._calculate_next_run(ScheduleInterval.WEEKLY, base_time)

        expected = base_time + timedelta(weeks=1)
        assert next_run == expected

    def test_calculate_next_run_default_time(self):
        """Test calculating next run with default time (now)."""
        scheduler = SchedulerService()

        next_run = scheduler._calculate_next_run(ScheduleInterval.HOURLY)

        assert next_run > datetime.now(UTC)
        assert next_run < datetime.now(UTC) + timedelta(hours=2)

    @pytest.mark.asyncio
    async def test_execute_task_sync_function(self):
        """Test executing synchronous task function."""
        scheduler = SchedulerService()

        executed = []

        def sync_func(value):
            executed.append(value)

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=sync_func, args=("test_value",))
        scheduler.add_task(task)

        await scheduler._execute_task(task)

        assert executed == ["test_value"]
        assert task.last_run is not None
        assert task.next_run is not None

    @pytest.mark.asyncio
    async def test_execute_task_async_function(self):
        """Test executing asynchronous task function."""
        scheduler = SchedulerService()

        executed = []

        async def async_func(value):
            executed.append(value)

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=async_func, args=("test_value",))
        scheduler.add_task(task)

        await scheduler._execute_task(task)

        assert executed == ["test_value"]
        assert task.last_run is not None

    @pytest.mark.asyncio
    async def test_execute_task_with_kwargs(self):
        """Test executing task with keyword arguments."""
        scheduler = SchedulerService()

        executed = []

        def func_with_kwargs(value, **kwargs):
            executed.append((value, kwargs))

        task = ScheduledTask(
            name="test",
            interval=ScheduleInterval.HOURLY,
            function=func_with_kwargs,
            args=("test",),
            kwargs={"key": "value"},
        )
        scheduler.add_task(task)

        await scheduler._execute_task(task)

        assert executed == [("test", {"key": "value"})]

    @pytest.mark.asyncio
    async def test_execute_task_with_error(self):
        """Test executing task that raises error."""
        scheduler = SchedulerService()

        def failing_func():
            raise ValueError("Test error")

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=failing_func)
        scheduler.add_task(task)

        # Should not raise, just log error
        await scheduler._execute_task(task)

        # Task timing should still be updated
        assert task.last_run is not None
        assert task.next_run is not None

    def test_get_task_status_empty(self):
        """Test getting task status with no tasks."""
        scheduler = SchedulerService()

        status = scheduler.get_task_status()

        assert status == {}

    def test_get_task_status_multiple_tasks(self):
        """Test getting status of multiple tasks."""
        scheduler = SchedulerService()

        task1 = ScheduledTask(name="task1", interval=ScheduleInterval.HOURLY, function=lambda: None)
        task2 = ScheduledTask(name="task2", interval=ScheduleInterval.DAILY, function=lambda: None, enabled=False)

        scheduler.add_task(task1)
        scheduler.add_task(task2)

        status = scheduler.get_task_status()

        assert "task1" in status
        assert "task2" in status
        assert status["task1"]["enabled"] is True
        assert status["task1"]["interval"] == "hourly"
        assert status["task2"]["enabled"] is False
        assert status["task2"]["interval"] == "daily"

    def test_get_task_status_with_last_run(self):
        """Test task status includes last run time."""
        scheduler = SchedulerService()

        last_run = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=lambda: None, last_run=last_run)

        scheduler.add_task(task)

        status = scheduler.get_task_status()

        assert status["test"]["last_run"] == last_run.isoformat()

    def test_get_task_status_overdue(self):
        """Test task status shows overdue status."""
        scheduler = SchedulerService()

        # Create task with next run in the past
        past_time = datetime.now(UTC) - timedelta(hours=1)
        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=lambda: None)
        scheduler.add_task(task)
        task.next_run = past_time

        status = scheduler.get_task_status()

        assert status["test"]["overdue"] is True

    @pytest.mark.asyncio
    async def test_run_task_now_success(self):
        """Test manually running a task."""
        scheduler = SchedulerService()

        executed = []

        def test_func():
            executed.append("ran")

        task = ScheduledTask(name="test", interval=ScheduleInterval.HOURLY, function=test_func)
        scheduler.add_task(task)

        result = await scheduler.run_task_now("test")

        assert result is True
        assert executed == ["ran"]

    @pytest.mark.asyncio
    async def test_run_task_now_not_found(self):
        """Test manually running non-existent task."""
        scheduler = SchedulerService()

        result = await scheduler.run_task_now("nonexistent")

        assert result is False

    def test_global_instance_exists(self):
        """Test that global scheduler_service instance exists."""
        from app.services.scheduler_service import scheduler_service

        assert scheduler_service is not None
        assert isinstance(scheduler_service, SchedulerService)
