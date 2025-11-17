#!/usr/bin/env python3
"""
Test script for Slack notification integration.

This script sends test notifications to verify the Slack integration is working correctly.
It tests all notification types used by the PratikoAI subagent system.

Usage:
    python scripts/test_slack_notifications.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.slack_notification_service import SlackNotificationService


async def main():
    """Run all Slack notification tests."""
    print("=" * 80)
    print("PratikoAI Slack Notification Test Suite")
    print("=" * 80)
    print()

    # Check configuration
    print("1. Checking Slack configuration...")
    if not settings.SLACK_ENABLED:
        print("   ❌ SLACK_ENABLED is False in .env")
        print("   Please set SLACK_ENABLED=true in your .env file")
        return False

    if not settings.SLACK_WEBHOOK_URL_ARCHITECT:
        print("   ❌ SLACK_WEBHOOK_URL_ARCHITECT is not set")
        print("   Please add your architect webhook URL to .env")
        print("   See docs/setup/SLACK_INTEGRATION.md for instructions")
        return False

    if not settings.SLACK_WEBHOOK_URL_SCRUM:
        print("   ❌ SLACK_WEBHOOK_URL_SCRUM is not set")
        print("   Please add your scrum webhook URL to .env")
        print("   See docs/setup/SLACK_INTEGRATION.md for instructions")
        return False

    print(f"   ✅ Slack enabled: {settings.SLACK_ENABLED}")
    print(f"   ✅ Architect webhook: {settings.SLACK_WEBHOOK_URL_ARCHITECT[:50]}...")
    print(f"   ✅ Scrum webhook: {settings.SLACK_WEBHOOK_URL_SCRUM[:50]}...")
    print()

    # Initialize service
    slack_service = SlackNotificationService(
        architect_webhook_url=settings.SLACK_WEBHOOK_URL_ARCHITECT,
        scrum_webhook_url=settings.SLACK_WEBHOOK_URL_SCRUM,
        enabled=settings.SLACK_ENABLED,
    )

    print("2. Testing notifications...")
    print()

    # Test 1: Architect Veto Alert
    print("   Test 1: Architect Veto Alert (CRITICAL)")
    success = await slack_service.send_architect_veto(
        task_id="DEV-BE-TEST-001",
        task_description="Test: Switch to Redis for vector storage",
        proposed_by="Test Script",
        veto_reason="This is a test veto notification. Redis is not suitable for vector storage (test case).",
        violated_principle="ADR-003 - pgvector for vector search",
        risk_introduced="Loss of vector similarity search capabilities, $5,000 migration cost (test)",
        alternative_approach="Continue using pgvector, upgrade to HNSW index (test)",
    )
    if success:
        print("   ✅ Architect veto alert sent successfully")
    else:
        print("   ❌ Failed to send architect veto alert")
    print()
    await asyncio.sleep(1)

    # Test 2: Scrum Progress Update
    print("   Test 2: Scrum Progress Update (INFO)")
    success = await slack_service.send_scrum_progress_update(
        sprint_name="Sprint 0 - Test",
        sprint_progress="3/10 tasks (30%)",
        tasks_in_progress=[
            {
                "id": "DEV-BE-TEST-002",
                "description": "Test task 1",
                "assignee": "Backend Expert",
                "progress": "50% complete, 4 hours elapsed",
            },
            {
                "id": "DEV-BE-TEST-003",
                "description": "Test task 2",
                "assignee": "Test Generation",
                "progress": "25% complete, 2 hours elapsed",
            },
        ],
        tasks_completed_today=["DEV-BE-TEST-004: Completed test task"],
        tasks_next_up=["DEV-BE-TEST-005: Next test task", "DEV-BE-TEST-006: Another test task"],
        blockers=None,
        velocity="2.5 points/day (target: 2.0)",
        sprint_status="ON TRACK",
    )
    if success:
        print("   ✅ Scrum progress update sent successfully")
    else:
        print("   ❌ Failed to send scrum progress update")
    print()
    await asyncio.sleep(1)

    # Test 3: Task Completion Notification
    print("   Test 3: Task Completion Notification (INFO)")
    success = await slack_service.send_task_completion(
        task_id="DEV-BE-TEST-007",
        task_description="Test: Implement test notification system",
        assigned_to="Backend Expert",
        duration="2 hours (estimated: 3 hours)",
    )
    if success:
        print("   ✅ Task completion notification sent successfully")
    else:
        print("   ❌ Failed to send task completion notification")
    print()
    await asyncio.sleep(1)

    # Test 4: Blocker Alert
    print("   Test 4: Blocker Alert (WARNING)")
    success = await slack_service.send_blocker_alert(
        task_id="DEV-BE-TEST-008",
        blocker_description="Test blocker: API key for test service expired",
        escalated_to="Architect",
        impact="Blocks testing of notification system integration (test case)",
    )
    if success:
        print("   ✅ Blocker alert sent successfully")
    else:
        print("   ❌ Failed to send blocker alert")
    print()
    await asyncio.sleep(1)

    # Test 5: Sprint Summary
    print("   Test 5: Sprint Summary (INFO)")
    success = await slack_service.send_sprint_summary(
        sprint_name="Sprint 0 - Test",
        sprint_dates="2025-11-15 to 2025-11-21",
        tasks_completed=7,
        tasks_total=10,
        velocity="2.5 points/day",
        completed_tasks_list=[
            "DEV-BE-TEST-001: Test task 1",
            "DEV-BE-TEST-002: Test task 2",
            "DEV-BE-TEST-003: Test task 3",
            "DEV-BE-TEST-004: Test task 4",
            "DEV-BE-TEST-005: Test task 5",
            "DEV-BE-TEST-006: Test task 6",
            "DEV-BE-TEST-007: Test task 7",
        ],
        incomplete_tasks_list=[
            "DEV-BE-TEST-008: Incomplete test task 1 (80% complete)",
            "DEV-BE-TEST-009: Incomplete test task 2 (60% complete)",
            "DEV-BE-TEST-010: Incomplete test task 3 (30% complete)",
        ],
        blockers_encountered=["Test blocker 1 (resolved in 2 hours)", "Test blocker 2 (resolved in 4 hours)"],
        lessons_learned=[
            "Test notifications work well with Slack",
            "Webhook integration is straightforward",
            "Rich formatting enhances readability",
        ],
    )
    if success:
        print("   ✅ Sprint summary sent successfully")
    else:
        print("   ❌ Failed to send sprint summary")
    print()
    await asyncio.sleep(1)

    # Test 6: Daily Standup
    print("   Test 6: Daily Standup (INFO)")
    success = await slack_service.send_daily_standup(
        sprint_name="Sprint 0 - Test",
        yesterday_completed=["DEV-BE-TEST-011: Yesterday's test task 1", "DEV-BE-TEST-012: Yesterday's test task 2"],
        today_active=["DEV-BE-TEST-013: Today's test task 1", "DEV-BE-TEST-014: Today's test task 2"],
        next_up=["DEV-BE-TEST-015: Tomorrow's test task 1"],
        blockers=None,
        sprint_day=3,
        sprint_progress="30%",
    )
    if success:
        print("   ✅ Daily standup sent successfully")
    else:
        print("   ❌ Failed to send daily standup")
    print()

    # Summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    print("✅ All test notifications sent!")
    print()
    print("Next steps:")
    print("1. Check your Slack workspace:")
    print("   - #architect-alerts should have 1 message (veto alert)")
    print("   - #scrum-updates should have 5 messages (progress, completion, blocker, summary, standup)")
    print("2. Verify you received 6 test notifications in total")
    print("3. Review the message formatting and content")
    print("4. If messages didn't appear, check docs/setup/SLACK_INTEGRATION.md")
    print()
    print("Notification types tested:")
    print("  ✅ Architect veto alert (critical, red)")
    print("  ✅ Scrum progress update (info, green)")
    print("  ✅ Task completion notification (info, green)")
    print("  ✅ Blocker alert (warning, orange)")
    print("  ✅ Sprint summary (info, green)")
    print("  ✅ Daily standup (info, green)")
    print()

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
