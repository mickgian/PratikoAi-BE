"""Slack Notification Service for PratikoAI Subagent System.

This service handles all Slack notifications for the multi-agent system:
- Architect veto alerts (immediate, high priority)
- Scrum Master progress updates (every 2 hours)
- Task completion notifications
- Blocker alerts and escalations
- Sprint summaries

Adapted from deployment-orchestration/notification_system.py
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NotificationSeverity(Enum):
    """Notification severity levels with Slack color mappings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SlackNotificationService:
    """Service for sending Slack notifications for subagent activities."""

    def __init__(
        self,
        architect_webhook_url: str,
        scrum_webhook_url: str,
        enabled: bool = True,
    ):
        """Initialize Slack notification service.

        Modern Slack app webhooks require separate webhooks for each channel.
        The "channel" parameter in payloads is ignored by modern webhooks.

        Args:
            architect_webhook_url: Webhook URL for #architect-alerts channel
            scrum_webhook_url: Webhook URL for #scrum-updates channel
            enabled: Whether notifications are enabled (default: True)
        """
        self.architect_webhook_url = architect_webhook_url
        self.scrum_webhook_url = scrum_webhook_url
        self.enabled = enabled

        # Severity color mapping
        self.color_map = {
            NotificationSeverity.INFO: "#36a64f",  # Green
            NotificationSeverity.WARNING: "#ff9900",  # Orange
            NotificationSeverity.ERROR: "#ff0000",  # Red
            NotificationSeverity.CRITICAL: "#8b0000",  # Dark Red
        }

    async def _send_slack_message(self, payload: dict[str, Any], webhook_url: str) -> bool:
        """Send message to Slack via webhook.

        Args:
            payload: Slack message payload
            webhook_url: Specific webhook URL to use for this message

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.info("Slack notifications disabled, skipping send")
            return False

        if not webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=30)

                if response.status_code == 200:
                    logger.info("Slack notification sent successfully")
                    return True
                else:
                    logger.error(f"Slack notification failed: HTTP {response.status_code}")
                    return False

        except httpx.TimeoutException:
            logger.error("Slack notification timeout after 30s")
            return False
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False

    async def send_architect_veto(
        self,
        task_id: str,
        task_description: str,
        proposed_by: str,
        veto_reason: str,
        violated_principle: str,
        risk_introduced: str,
        alternative_approach: str | None = None,
    ) -> bool:
        """Send Architect veto alert to Slack.

        Args:
            task_id: Task identifier (e.g., DEV-BE-67)
            task_description: Brief task description
            proposed_by: Who proposed the approach (subagent name)
            veto_reason: Detailed technical rationale for veto
            violated_principle: Which ADR or principle was violated
            risk_introduced: Performance/security/maintainability concerns
            alternative_approach: Recommended solution (optional)

        Returns:
            True if notification sent successfully
        """
        fields = [
            {"title": "Task", "value": f"{task_id}: {task_description}", "short": False},
            {"title": "Proposed By", "value": proposed_by, "short": True},
            {"title": "Veto Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M CET"), "short": True},
            {"title": "Veto Reason", "value": veto_reason, "short": False},
            {"title": "Violated Principle", "value": violated_principle, "short": True},
            {"title": "Risk Introduced", "value": risk_introduced, "short": True},
        ]

        if alternative_approach:
            fields.append({"title": "Alternative Approach", "value": alternative_approach, "short": False})

        payload = {
            "text": "🛑 *ARCHITECT VETO EXERCISED*",
            "attachments": [
                {
                    "color": self.color_map[NotificationSeverity.CRITICAL],
                    "fields": fields,
                    "footer": "PratikoAI Architect Subagent",
                    "footer_icon": "https://github.com/anthropics/claude-code/raw/main/assets/claude-icon.png",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
            "username": "PratikoAI Architect",
            "icon_emoji": ":no_entry:",
        }

        return await self._send_slack_message(payload, self.architect_webhook_url)

    async def send_scrum_progress_update(
        self,
        sprint_name: str,
        sprint_progress: str,
        tasks_in_progress: list[dict[str, str]],
        tasks_completed_today: list[str],
        tasks_next_up: list[str],
        blockers: list[str] | None = None,
        velocity: str | None = None,
        sprint_status: str = "ON TRACK",
    ) -> bool:
        """Send Scrum Master progress update to Slack (every 2 hours).

        Args:
            sprint_name: Sprint identifier (e.g., "Sprint 1")
            sprint_progress: Progress summary (e.g., "5/12 tasks (42%)")
            tasks_in_progress: List of active tasks with details
            tasks_completed_today: List of completed task IDs
            tasks_next_up: List of queued task IDs
            blockers: List of current blockers (optional)
            velocity: Velocity metric (e.g., "2.5 points/day") (optional)
            sprint_status: Sprint health status (default: "ON TRACK")

        Returns:
            True if notification sent successfully
        """
        # Determine status emoji
        status_emoji = {"ON TRACK": "✅", "AT RISK": "🟡", "DELAYED": "🔴"}.get(sprint_status, "⚪")

        # Determine severity based on status
        severity = {
            "ON TRACK": NotificationSeverity.INFO,
            "AT RISK": NotificationSeverity.WARNING,
            "DELAYED": NotificationSeverity.ERROR,
        }.get(sprint_status, NotificationSeverity.INFO)

        # Build mobile-friendly Block Kit format
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 PROGRESS UPDATE - {datetime.now().strftime('%H:%M CET')}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Sprint:*\n{sprint_name}"},
                    {"type": "mrkdwn", "text": f"*Progress:*\n{sprint_progress}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{status_emoji} {sprint_status}"},
                ]
            },
            {"type": "divider"}
        ]

        # Add in-progress tasks
        if tasks_in_progress:
            in_progress_text = "\n".join([
                f"• *{task['id']}*: {task['description']}\n  _{task['assignee']}_ - {task['progress']}"
                for task in tasks_in_progress
            ])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*🔄 In Progress:*\n{in_progress_text}"}
            })

        # Add completed tasks
        if tasks_completed_today:
            completed_text = "\n".join([f"• {task}" for task in tasks_completed_today])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*✅ Completed Today:*\n{completed_text}"}
            })

        # Add next up tasks
        if tasks_next_up:
            next_up_text = "\n".join([f"• {task}" for task in tasks_next_up])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*⏳ Next Up:*\n{next_up_text}"}
            })

        # Add blockers if present
        if blockers:
            blockers_text = "\n".join([f"• {blocker}" for blocker in blockers])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*⚠️ Blockers:*\n{blockers_text}"}
            })

        # Add velocity if provided
        if velocity:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📈 Velocity: *{velocity}*"}
                ]
            })

        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "🤖 PratikoAI Scrum Master Subagent"}
            ]
        })

        payload = {
            "text": f"📊 PROGRESS UPDATE - {datetime.now().strftime('%H:%M CET')}",
            "blocks": blocks,
            "username": "PratikoAI Scrum Master",
            "icon_emoji": ":clipboard:",
        }

        return await self._send_slack_message(payload, self.scrum_webhook_url)

    async def send_task_completion(self, task_id: str, task_description: str, assigned_to: str, duration: str) -> bool:
        """Send task completion notification to Slack.

        Args:
            task_id: Task identifier (e.g., DEV-BE-67)
            task_description: Task description
            assigned_to: Subagent that completed the task
            duration: Actual task duration (e.g., "3 days")

        Returns:
            True if notification sent successfully
        """
        payload = {
            "text": "✅ *TASK COMPLETED*",
            "attachments": [
                {
                    "color": self.color_map[NotificationSeverity.INFO],
                    "fields": [
                        {"title": "Task", "value": f"{task_id}: {task_description}", "short": False},
                        {"title": "Completed By", "value": assigned_to, "short": True},
                        {"title": "Duration", "value": duration, "short": True},
                        {
                            "title": "Completed At",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M CET"),
                            "short": True,
                        },
                    ],
                    "footer": "PratikoAI Scrum Master Subagent",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
            "username": "PratikoAI Scrum Master",
            "icon_emoji": ":white_check_mark:",
        }

        return await self._send_slack_message(payload, self.scrum_webhook_url)

    async def send_blocker_alert(self, task_id: str, blocker_description: str, escalated_to: str, impact: str) -> bool:
        """Send blocker alert to Slack.

        Args:
            task_id: Blocked task identifier
            blocker_description: Description of the blocker
            escalated_to: Who the blocker is escalated to (Architect/Stakeholder)
            impact: Impact description (e.g., "Blocks Sprint 1 completion")

        Returns:
            True if notification sent successfully
        """
        payload = {
            "text": "⚠️ *BLOCKER DETECTED*",
            "attachments": [
                {
                    "color": self.color_map[NotificationSeverity.WARNING],
                    "fields": [
                        {"title": "Task", "value": task_id, "short": True},
                        {"title": "Escalated To", "value": escalated_to, "short": True},
                        {"title": "Blocker Description", "value": blocker_description, "short": False},
                        {"title": "Impact", "value": impact, "short": False},
                        {
                            "title": "Detected At",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M CET"),
                            "short": True,
                        },
                    ],
                    "footer": "PratikoAI Scrum Master Subagent",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
            "username": "PratikoAI Scrum Master",
            "icon_emoji": ":warning:",
        }

        return await self._send_slack_message(payload, self.scrum_webhook_url)

    async def send_sprint_summary(
        self,
        sprint_name: str,
        sprint_dates: str,
        tasks_completed: int,
        tasks_total: int,
        velocity: str,
        completed_tasks_list: list[str],
        incomplete_tasks_list: list[str],
        blockers_encountered: list[str],
        lessons_learned: list[str],
    ) -> bool:
        """Send weekly sprint summary to Slack.

        Args:
            sprint_name: Sprint identifier
            sprint_dates: Sprint duration (e.g., "2025-11-15 to 2025-11-21")
            tasks_completed: Number of completed tasks
            tasks_total: Total committed tasks
            velocity: Sprint velocity metric
            completed_tasks_list: List of completed task IDs
            incomplete_tasks_list: List of incomplete task IDs
            blockers_encountered: List of blockers that occurred
            lessons_learned: List of retrospective insights

        Returns:
            True if notification sent successfully
        """
        completion_rate = int((tasks_completed / tasks_total) * 100) if tasks_total > 0 else 0

        fields = [
            {"title": "Sprint", "value": sprint_name, "short": True},
            {"title": "Duration", "value": sprint_dates, "short": True},
            {
                "title": "Completion Rate",
                "value": f"{tasks_completed}/{tasks_total} ({completion_rate}%)",
                "short": True,
            },
            {"title": "Velocity", "value": velocity, "short": True},
            {
                "title": "✅ Completed Tasks",
                "value": "\n".join(completed_tasks_list) if completed_tasks_list else "None",
                "short": False,
            },
            {
                "title": "⏳ Incomplete Tasks",
                "value": "\n".join(incomplete_tasks_list) if incomplete_tasks_list else "None",
                "short": False,
            },
            {
                "title": "⚠️ Blockers Encountered",
                "value": "\n".join(blockers_encountered) if blockers_encountered else "None",
                "short": False,
            },
            {
                "title": "💡 Lessons Learned",
                "value": "\n".join(lessons_learned) if lessons_learned else "None",
                "short": False,
            },
        ]

        # Determine severity based on completion rate
        if completion_rate >= 90:
            severity = NotificationSeverity.INFO
        elif completion_rate >= 70:
            severity = NotificationSeverity.WARNING
        else:
            severity = NotificationSeverity.ERROR

        payload = {
            "text": f"📈 *SPRINT {sprint_name} SUMMARY*",
            "attachments": [
                {
                    "color": self.color_map[severity],
                    "fields": fields,
                    "footer": "PratikoAI Scrum Master Subagent",
                    "footer_icon": "https://github.com/anthropics/claude-code/raw/main/assets/claude-icon.png",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
            "username": "PratikoAI Scrum Master",
            "icon_emoji": ":bar_chart:",
        }

        return await self._send_slack_message(payload, self.scrum_webhook_url)

    async def send_daily_standup(
        self,
        sprint_name: str,
        yesterday_completed: list[str],
        today_active: list[str],
        next_up: list[str],
        blockers: list[str] | None = None,
        sprint_day: int = 1,
        sprint_progress: str = "0%",
    ) -> bool:
        """Send daily standup summary to Slack (every morning at 08:00).

        Args:
            sprint_name: Sprint identifier
            yesterday_completed: Tasks completed yesterday
            today_active: Tasks being worked on today
            next_up: Queued tasks
            blockers: Current blockers (optional)
            sprint_day: Day number in sprint (e.g., Day 3/7)
            sprint_progress: Overall sprint progress percentage

        Returns:
            True if notification sent successfully
        """
        payload = {
            "text": f"🌅 *DAILY STANDUP* - {datetime.now().strftime('%Y-%m-%d')}",
            "attachments": [
                {
                    "color": self.color_map[NotificationSeverity.INFO],
                    "fields": [
                        {"title": "Sprint", "value": f"{sprint_name} (Day {sprint_day})", "short": True},
                        {"title": "Progress", "value": sprint_progress, "short": True},
                        {
                            "title": "✅ Yesterday",
                            "value": "\n".join(yesterday_completed) if yesterday_completed else "None",
                            "short": False,
                        },
                        {
                            "title": "🔄 Today",
                            "value": "\n".join(today_active) if today_active else "None",
                            "short": False,
                        },
                        {
                            "title": "⏳ Next",
                            "value": "\n".join(next_up) if next_up else "None",
                            "short": False,
                        },
                        {
                            "title": "⚠️ Blockers",
                            "value": "\n".join(blockers) if blockers else "None",
                            "short": False,
                        },
                    ],
                    "footer": "PratikoAI Scrum Master Subagent",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
            "username": "PratikoAI Scrum Master",
            "icon_emoji": ":sunrise:",
        }

        return await self._send_slack_message(payload, self.scrum_webhook_url)
