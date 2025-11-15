"""CCNL Notification Service.

This service manages notifications for CCNL updates, including
user targeting, notification generation, and delivery.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


@dataclass
class NotificationTemplate:
    """Notification template structure."""

    template_id: str
    title_template: str
    message_template: str
    priority: NotificationPriority
    channels: list[NotificationChannel]


@dataclass
class UserNotificationPreferences:
    """User notification preferences."""

    user_id: str
    sectors_of_interest: list[str]
    preferred_channels: list[NotificationChannel]
    minimum_priority: NotificationPriority
    frequency_limit: dict[str, int]  # e.g., {"daily": 5, "weekly": 20}


class CCNLNotificationService:
    """CCNL notification service."""

    def __init__(self):
        self.notification_templates = self._initialize_templates()
        self.user_preferences = {}  # In real implementation, would load from database

    def _initialize_templates(self) -> dict[str, NotificationTemplate]:
        """Initialize notification templates."""
        templates = {
            "ccnl_update": NotificationTemplate(
                template_id="ccnl_update",
                title_template="CCNL {ccnl_name} Updated",
                message_template="The {ccnl_name} has been updated with important changes. "
                "Effective date: {effective_date}. Key changes: {changes_summary}",
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
            ),
            "ccnl_renewal": NotificationTemplate(
                template_id="ccnl_renewal",
                title_template="CCNL {ccnl_name} Renewed",
                message_template="The {ccnl_name} has been successfully renewed. "
                "New contract period: {effective_date} to {expiry_date}. "
                "Major changes include: {changes_summary}",
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
            ),
            "salary_increase": NotificationTemplate(
                template_id="salary_increase",
                title_template="Salary Increases in {ccnl_name}",
                message_template="New salary increases have been approved for {ccnl_name}. "
                "Average increase: {avg_increase}%. Effective: {effective_date}",
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
            ),
            "expiry_warning": NotificationTemplate(
                template_id="expiry_warning",
                title_template="CCNL {ccnl_name} Expiring Soon",
                message_template="The {ccnl_name} will expire on {expiry_date}. Monitor for renewal negotiations.",
                priority=NotificationPriority.MEDIUM,
                channels=[NotificationChannel.EMAIL],
            ),
        }

        return templates

    def generate_update_notification(self, update_data: dict[str, Any]) -> dict[str, Any]:
        """Generate notification for CCNL update."""
        try:
            ccnl_name = update_data.get("ccnl_name", "Unknown CCNL")
            changes = update_data.get("changes", {})
            effective_date = update_data.get("effective_date", date.today())

            # Determine notification type and template
            if "salary_increases" in changes:
                template_id = "salary_increase"
                template_vars = {
                    "ccnl_name": ccnl_name,
                    "avg_increase": self._calculate_average_increase(changes["salary_increases"]),
                    "effective_date": effective_date.strftime("%d/%m/%Y"),
                }
            else:
                template_id = "ccnl_update"
                template_vars = {
                    "ccnl_name": ccnl_name,
                    "effective_date": effective_date.strftime("%d/%m/%Y"),
                    "changes_summary": self._generate_changes_summary(changes),
                }

            template = self.notification_templates[template_id]

            notification = {
                "id": f"notification_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "template_id": template_id,
                "title": template.title_template.format(**template_vars),
                "message": template.message_template.format(**template_vars),
                "priority": template.priority.value,
                "channels": [channel.value for channel in template.channels],
                "created_at": datetime.utcnow(),
                "affected_users": self._find_affected_users(ccnl_name),
                "metadata": {
                    "ccnl_name": ccnl_name,
                    "effective_date": effective_date,
                    "changes_count": len(changes),
                    "template_vars": template_vars,
                },
            }

            logger.info(f"Generated notification for {ccnl_name}: {notification['title']}")

            return notification

        except Exception as e:
            logger.error(f"Error generating update notification: {str(e)}")
            return {
                "id": "error_notification",
                "title": "Notification Generation Error",
                "message": f"Failed to generate notification: {str(e)}",
                "priority": "low",
                "channels": ["in_app"],
                "affected_users": [],
            }

    def _calculate_average_increase(self, salary_increases: dict[str, Any]) -> float:
        """Calculate average salary increase percentage."""
        try:
            if not salary_increases:
                return 0.0

            total_increase = 0.0
            count = 0

            for level_data in salary_increases.values():
                if isinstance(level_data, dict) and "percentage" in level_data:
                    total_increase += level_data["percentage"]
                    count += 1

            return total_increase / count if count > 0 else 0.0

        except Exception as e:
            logger.error(f"Error calculating average increase: {str(e)}")
            return 0.0

    def _generate_changes_summary(self, changes: dict[str, Any]) -> str:
        """Generate a brief summary of changes."""
        summary_parts = []

        try:
            if "salary_increases" in changes:
                summary_parts.append("salary adjustments")

            if "working_hours" in changes:
                old_hours = changes["working_hours"].get("old", 40)
                new_hours = changes["working_hours"].get("new", 40)
                if new_hours != old_hours:
                    summary_parts.append(f"working hours changed from {old_hours} to {new_hours}")

            if "new_benefits" in changes:
                benefits = changes["new_benefits"]
                if benefits:
                    summary_parts.append(f"new benefits added ({len(benefits)})")

            return "; ".join(summary_parts) if summary_parts else "various updates"

        except Exception as e:
            logger.error(f"Error generating changes summary: {str(e)}")
            return "updates applied"

    def _find_affected_users(self, ccnl_name: str) -> list[str]:
        """Find users who should be notified about this CCNL update."""
        try:
            # In real implementation, this would query user preferences database
            # For now, return mock user list

            # Extract sector from CCNL name for matching
            ccnl_lower = ccnl_name.lower()
            relevant_sectors = []

            if "metalmeccanic" in ccnl_lower:
                relevant_sectors = ["metalmeccanici", "industria"]
            elif "commercio" in ccnl_lower:
                relevant_sectors = ["commercio", "terziario"]
            elif "edilizia" in ccnl_lower:
                relevant_sectors = ["edilizia", "costruzioni"]
            elif "sanità" in ccnl_lower or "sanita" in ccnl_lower:
                relevant_sectors = ["sanita", "sanitario"]
            else:
                relevant_sectors = ["generale"]

            # Mock affected users based on sector
            mock_users = {
                "metalmeccanici": ["user_001", "user_015", "user_028"],
                "commercio": ["user_002", "user_016", "user_029"],
                "edilizia": ["user_003", "user_017", "user_030"],
                "sanita": ["user_004", "user_018", "user_031"],
                "generale": ["user_admin", "user_hr_001"],
            }

            affected_users = []
            for sector in relevant_sectors:
                if sector in mock_users:
                    affected_users.extend(mock_users[sector])

            # Remove duplicates and add admin users for high-priority updates
            affected_users = list(set(affected_users))
            affected_users.extend(["admin_001", "system_monitor"])

            return list(set(affected_users))  # Remove duplicates again

        except Exception as e:
            logger.error(f"Error finding affected users: {str(e)}")
            return ["admin_001"]  # Fallback to admin

    def send_notification(self, notification: dict[str, Any]) -> dict[str, Any]:
        """Send notification through specified channels."""
        try:
            notification_id = notification.get("id")
            channels = notification.get("channels", [])
            affected_users = notification.get("affected_users", [])

            delivery_results = {}
            total_sent = 0
            total_failed = 0

            for channel in channels:
                channel_results = self._send_via_channel(notification, channel, affected_users)
                delivery_results[channel] = channel_results
                total_sent += channel_results.get("sent", 0)
                total_failed += channel_results.get("failed", 0)

            delivery_summary = {
                "notification_id": notification_id,
                "total_recipients": len(affected_users),
                "total_sent": total_sent,
                "total_failed": total_failed,
                "channels_used": len(channels),
                "delivery_results": delivery_results,
                "sent_at": datetime.utcnow(),
                "success_rate": total_sent / (total_sent + total_failed) if (total_sent + total_failed) > 0 else 0.0,
            }

            logger.info(f"Sent notification {notification_id} to {total_sent} recipients via {len(channels)} channels")

            return delivery_summary

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return {
                "notification_id": notification.get("id", "unknown"),
                "total_sent": 0,
                "total_failed": len(notification.get("affected_users", [])),
                "error": str(e),
            }

    def _send_via_channel(self, notification: dict[str, Any], channel: str, users: list[str]) -> dict[str, Any]:
        """Send notification via specific channel (mock implementation)."""
        try:
            # Mock delivery implementation
            # In real implementation, would integrate with email service, SMS provider, etc.

            sent_count = len(users)  # Assume all successful for testing
            failed_count = 0

            # Simulate some failures for certain channels
            if channel == "sms" and len(users) > 10:
                # SMS might fail for large groups
                failed_count = 1
                sent_count -= 1

            result = {
                "channel": channel,
                "sent": sent_count,
                "failed": failed_count,
                "delivery_time": datetime.utcnow(),
                "details": f"Mock delivery via {channel}",
            }

            logger.debug(f"Mock sent via {channel}: {sent_count} sent, {failed_count} failed")

            return result

        except Exception as e:
            logger.error(f"Error sending via {channel}: {str(e)}")
            return {"channel": channel, "sent": 0, "failed": len(users), "error": str(e)}

    def get_notification_history(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get notification history for a user."""
        try:
            # Mock notification history
            history = [
                {
                    "id": "notif_001",
                    "title": "CCNL Metalmeccanici Updated",
                    "message": "Salary increases of 3.2% approved",
                    "priority": "high",
                    "sent_at": datetime.utcnow() - timedelta(days=1),
                    "read": True,
                    "channel": "email",
                },
                {
                    "id": "notif_002",
                    "title": "CCNL Commercio Expiring Soon",
                    "message": "Contract expires in 30 days",
                    "priority": "medium",
                    "sent_at": datetime.utcnow() - timedelta(days=7),
                    "read": False,
                    "channel": "in_app",
                },
            ]

            return history[:limit]

        except Exception as e:
            logger.error(f"Error getting notification history for {user_id}: {str(e)}")
            return []


# Global instance
ccnl_notification_service = CCNLNotificationService()
