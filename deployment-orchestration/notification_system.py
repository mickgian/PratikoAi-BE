#!/usr/bin/env python3
"""
PratikoAI Cross-Repository Notification System

Advanced notification system for deployment orchestration with multiple
channels, actionable alerts, and comprehensive status reporting.

Features:
- Multi-channel notifications (Slack, email, webhook, GitHub)
- Rich formatting with deployment context
- Actionable notifications with resolution guidance
- Escalation rules for critical failures
- Status dashboards and reporting
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
import httpx
from github import Github
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import jinja2

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_SUCCESS = "deployment_success"
    DEPLOYMENT_FAILED = "deployment_failed"
    DEPLOYMENT_PARTIAL = "deployment_partial"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_SUCCESS = "rollback_success"
    ROLLBACK_FAILED = "rollback_failed"
    COMPATIBILITY_WARNING = "compatibility_warning"
    HEALTH_CHECK_FAILED = "health_check_failed"
    MANUAL_INTERVENTION_REQUIRED = "manual_intervention_required"


class Severity(Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Available notification channels."""
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    GITHUB_ISSUE = "github_issue"
    SMS = "sms"
    TEAMS = "teams"


@dataclass
class NotificationRecipient:
    """Represents a notification recipient."""
    name: str
    channel: NotificationChannel
    address: str  # email, slack user ID, phone number, etc.
    preferences: Dict[str, Any] = field(default_factory=dict)
    escalation_level: int = 1  # 1=normal, 2=escalated, 3=critical


@dataclass
class NotificationRule:
    """Rules for when and how to send notifications."""
    event_types: List[NotificationType]
    severity_levels: List[Severity]
    channels: List[NotificationChannel]
    recipients: List[NotificationRecipient]
    conditions: Dict[str, Any] = field(default_factory=dict)
    cooldown_minutes: int = 0  # Prevent spam
    escalation_delay_minutes: int = 15


@dataclass
class DeploymentContext:
    """Context information for deployment notifications."""
    deployment_id: str
    environment: str
    services: Dict[str, str]  # service -> version
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    workflow_urls: Dict[str, str] = field(default_factory=dict)
    health_urls: Dict[str, str] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    previous_versions: Dict[str, str] = field(default_factory=dict)
    rollback_available: bool = True


@dataclass
class NotificationMessage:
    """A formatted notification message."""
    title: str
    body: str
    severity: Severity
    context: DeploymentContext
    actions: List[Dict[str, str]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationFormatter:
    """Formats notifications for different channels."""
    
    def __init__(self):
        # Setup Jinja2 templates
        self.template_env = jinja2.Environment(
            loader=jinja2.DictLoader({
                'slack': self._get_slack_template(),
                'email_html': self._get_email_html_template(),
                'email_text': self._get_email_text_template(),
                'webhook': self._get_webhook_template(),
                'github_issue': self._get_github_issue_template()
            })
        )
    
    def format_for_slack(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Format notification for Slack."""
        
        color_map = {
            Severity.INFO: "#36a64f",
            Severity.WARNING: "#ffaa00", 
            Severity.ERROR: "#ff0000",
            Severity.CRITICAL: "#ff0000"
        }
        
        # Generate action buttons
        actions = []
        for action in notification.actions:
            actions.append({
                "type": "button",
                "text": action["text"],
                "url": action["url"],
                "style": action.get("style", "default")
            })
        
        # Create attachment fields
        fields = [
            {"title": "Deployment ID", "value": notification.context.deployment_id, "short": True},
            {"title": "Environment", "value": notification.context.environment, "short": True},
            {"title": "Status", "value": notification.context.status, "short": True}
        ]
        
        # Add service versions
        if notification.context.services:
            service_list = []
            for service, version in notification.context.services.items():
                service_list.append(f"{service}: {version}")
            fields.append({
                "title": "Services", 
                "value": "\n".join(service_list[:5]),  # Limit to 5 services
                "short": False
            })
        
        # Add error message if present
        if notification.context.error_message:
            fields.append({
                "title": "Error",
                "value": notification.context.error_message[:500] + "..." if len(notification.context.error_message) > 500 else notification.context.error_message,
                "short": False
            })
        
        # Calculate duration
        duration = "Unknown"
        if notification.context.started_at:
            end_time = notification.context.completed_at or datetime.now(timezone.utc)
            total_seconds = (end_time - notification.context.started_at).total_seconds()
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            duration = f"{minutes}m {seconds}s"
        
        fields.append({"title": "Duration", "value": duration, "short": True})
        
        attachment = {
            "color": color_map[notification.severity],
            "title": notification.title,
            "text": notification.body,
            "fields": fields,
            "footer": "PratikoAI Deployment Orchestrator",
            "ts": int(datetime.now().timestamp())
        }
        
        if actions:
            attachment["actions"] = actions
        
        return {
            "attachments": [attachment],
            "username": "PratikoAI Deploy Bot",
            "icon_emoji": ":rocket:"
        }
    
    def format_for_email(self, notification: NotificationMessage, html: bool = True) -> Dict[str, str]:
        """Format notification for email."""
        
        template_name = 'email_html' if html else 'email_text'
        template = self.template_env.get_template(template_name)
        
        # Prepare template variables
        variables = {
            'notification': notification,
            'context': notification.context,
            'severity_emoji': {
                Severity.INFO: "ℹ️",
                Severity.WARNING: "⚠️",
                Severity.ERROR: "❌",
                Severity.CRITICAL: "🚨"
            },
            'environment_emoji': {
                'production': "🟢",
                'staging': "🟡", 
                'development': "🔵"
            }
        }
        
        subject = f"[{notification.context.environment.upper()}] {notification.title}"
        body = template.render(**variables)
        
        return {
            'subject': subject,
            'body': body,
            'content_type': 'text/html' if html else 'text/plain'
        }
    
    def format_for_webhook(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Format notification for generic webhook."""
        
        return {
            "event_type": "deployment_notification",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": notification.severity.value,
            "title": notification.title,
            "body": notification.body,
            "context": {
                "deployment_id": notification.context.deployment_id,
                "environment": notification.context.environment,
                "services": notification.context.services,
                "status": notification.context.status,
                "started_at": notification.context.started_at.isoformat(),
                "completed_at": notification.context.completed_at.isoformat() if notification.context.completed_at else None,
                "error_message": notification.context.error_message,
                "workflow_urls": notification.context.workflow_urls,
                "health_urls": notification.context.health_urls
            },
            "actions": notification.actions,
            "metadata": notification.metadata
        }
    
    def format_for_github_issue(self, notification: NotificationMessage) -> Dict[str, str]:
        """Format notification for GitHub issue creation."""
        
        template = self.template_env.get_template('github_issue')
        
        variables = {
            'notification': notification,
            'context': notification.context,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        title = f"🚨 {notification.title}"
        body = template.render(**variables)
        
        # Determine labels based on context
        labels = ['deployment', notification.context.environment]
        if notification.severity in [Severity.ERROR, Severity.CRITICAL]:
            labels.append('deployment-failure')
        if notification.context.status == 'rollback':
            labels.append('rollback')
        
        return {
            'title': title,
            'body': body,
            'labels': labels
        }
    
    def _get_slack_template(self) -> str:
        """Get Slack message template."""
        return """
{# This is handled in format_for_slack method directly #}
"""
    
    def _get_email_html_template(self) -> str:
        """Get HTML email template."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ notification.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background: #f4f4f4; padding: 20px; border-left: 5px solid {% if notification.severity.value == 'critical' %}#ff0000{% elif notification.severity.value == 'error' %}#ff6600{% elif notification.severity.value == 'warning' %}#ffaa00{% else %}#36a64f{% endif %}; }
        .content { padding: 20px; }
        .footer { background: #f4f4f4; padding: 10px; font-size: 12px; }
        .info-table { width: 100%; border-collapse: collapse; }
        .info-table th, .info-table td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        .info-table th { background-color: #f2f2f2; }
        .action-button { display: inline-block; padding: 10px 20px; background: #007cba; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
        .error-box { background: #ffe6e6; border: 1px solid #ff9999; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ severity_emoji[notification.severity] }} {{ notification.title }}</h1>
    </div>
    
    <div class="content">
        <p>{{ notification.body }}</p>
        
        <h3>Deployment Information</h3>
        <table class="info-table">
            <tr><th>Deployment ID</th><td>{{ context.deployment_id }}</td></tr>
            <tr><th>Environment</th><td>{{ environment_emoji[context.environment] }} {{ context.environment|title }}</td></tr>
            <tr><th>Status</th><td>{{ context.status|title }}</td></tr>
            <tr><th>Started At</th><td>{{ context.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}</td></tr>
            {% if context.completed_at %}
            <tr><th>Completed At</th><td>{{ context.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}</td></tr>
            {% endif %}
        </table>
        
        {% if context.services %}
        <h3>Services</h3>
        <table class="info-table">
            {% for service, version in context.services.items() %}
            <tr><td>{{ service }}</td><td>{{ version }}</td></tr>
            {% endfor %}
        </table>
        {% endif %}
        
        {% if context.error_message %}
        <div class="error-box">
            <h3>Error Details</h3>
            <pre>{{ context.error_message }}</pre>
        </div>
        {% endif %}
        
        {% if notification.actions %}
        <h3>Actions</h3>
        {% for action in notification.actions %}
        <a href="{{ action.url }}" class="action-button">{{ action.text }}</a>
        {% endfor %}
        {% endif %}
        
        {% if context.workflow_urls %}
        <h3>Workflow Links</h3>
        <ul>
            {% for service, url in context.workflow_urls.items() %}
            <li><a href="{{ url }}">{{ service|title }} Workflow</a></li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    
    <div class="footer">
        <p>This notification was generated by the PratikoAI Deployment Orchestrator at {{ timestamp }}.</p>
    </div>
</body>
</html>
"""
    
    def _get_email_text_template(self) -> str:
        """Get plain text email template."""
        return """
{{ notification.title }}
{{ "=" * notification.title|length }}

{{ notification.body }}

Deployment Information:
- Deployment ID: {{ context.deployment_id }}
- Environment: {{ context.environment|title }}
- Status: {{ context.status|title }}
- Started At: {{ context.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
{% if context.completed_at -%}
- Completed At: {{ context.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
{% endif %}

{% if context.services -%}
Services:
{% for service, version in context.services.items() -%}
- {{ service }}: {{ version }}
{% endfor %}
{% endif %}

{% if context.error_message -%}
Error Details:
{{ context.error_message }}
{% endif %}

{% if notification.actions -%}
Actions:
{% for action in notification.actions -%}
- {{ action.text }}: {{ action.url }}
{% endfor %}
{% endif %}

{% if context.workflow_urls -%}
Workflow Links:
{% for service, url in context.workflow_urls.items() -%}
- {{ service|title }}: {{ url }}
{% endfor %}
{% endif %}

---
This notification was generated by the PratikoAI Deployment Orchestrator.
"""
    
    def _get_webhook_template(self) -> str:
        """Get webhook payload template."""
        return """
{# This is handled in format_for_webhook method directly #}
"""
    
    def _get_github_issue_template(self) -> str:
        """Get GitHub issue template."""
        return """
# Deployment Notification: {{ notification.title }}

**Deployment ID:** {{ context.deployment_id }}  
**Environment:** {{ context.environment|title }}  
**Status:** {{ context.status|title }}  
**Severity:** {{ notification.severity.value|title }}  
**Timestamp:** {{ timestamp }}

## Summary

{{ notification.body }}

## Deployment Details

{% if context.services -%}
### Services and Versions
{% for service, version in context.services.items() -%}
- **{{ service }}**: {{ version }}
{% endfor %}

{% endif -%}
### Timeline
- **Started:** {{ context.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
{% if context.completed_at -%}
- **Completed:** {{ context.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
{% endif %}

{% if context.error_message -%}
## Error Information

```
{{ context.error_message }}
```

{% endif -%}
{% if notification.actions -%}
## Recommended Actions

{% for action in notification.actions -%}
- [{{ action.text }}]({{ action.url }})
{% endfor %}

{% endif -%}
{% if context.workflow_urls -%}
## Workflow Links

{% for service, url in context.workflow_urls.items() -%}
- [{{ service|title }} Workflow]({{ url }})
{% endfor %}

{% endif -%}
{% if context.health_urls -%}
## Health Check URLs

{% for service, url in context.health_urls.items() -%}
- [{{ service|title }} Health]({{ url }})
{% endfor %}

{% endif -%}
## Next Steps

1. Review the workflow logs and error details above
2. Check service health and availability
3. Validate compatibility requirements
4. Consider rollback if necessary

---
*This issue was automatically created by the PratikoAI Deployment Orchestrator.*
"""


class NotificationDispatcher:
    """Dispatches notifications to various channels."""
    
    def __init__(self):
        self.formatter = NotificationFormatter()
        self.github = None
        if github_token := os.getenv('GITHUB_TOKEN'):
            self.github = Github(github_token)
    
    async def send_slack_notification(self, webhook_url: str, notification: NotificationMessage) -> bool:
        """Send notification to Slack."""
        try:
            payload = self.formatter.format_for_slack(notification)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    logger.info("Slack notification sent successfully")
                    return True
                else:
                    logger.error(f"Slack notification failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
    
    async def send_email_notification(self, smtp_config: Dict[str, str], 
                                    recipients: List[str], 
                                    notification: NotificationMessage) -> bool:
        """Send email notification."""
        try:
            # Format email content
            email_content = self.formatter.format_for_email(notification, html=True)
            text_content = self.formatter.format_for_email(notification, html=False)
            
            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_content['subject']
            msg['From'] = smtp_config['from_email']
            msg['To'] = ', '.join(recipients)
            
            # Add text and HTML parts
            text_part = MIMEText(text_content['body'], 'plain')
            html_part = MIMEText(email_content['body'], 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                if smtp_config.get('use_tls'):
                    server.starttls()
                if smtp_config.get('username'):
                    server.login(smtp_config['username'], smtp_config['password'])
                
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    async def send_webhook_notification(self, webhook_url: str, 
                                      notification: NotificationMessage,
                                      headers: Dict[str, str] = None) -> bool:
        """Send webhook notification."""
        try:
            payload = self.formatter.format_for_webhook(notification)
            request_headers = {'Content-Type': 'application/json'}
            if headers:
                request_headers.update(headers)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url, 
                    json=payload, 
                    headers=request_headers,
                    timeout=30
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("Webhook notification sent successfully")
                    return True
                else:
                    logger.error(f"Webhook notification failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
            return False
    
    async def create_github_issue(self, repo_name: str, 
                                notification: NotificationMessage,
                                assignees: List[str] = None) -> bool:
        """Create GitHub issue for notification."""
        try:
            if not self.github:
                logger.error("GitHub token not configured")
                return False
            
            repo = self.github.get_repo(repo_name)
            issue_content = self.formatter.format_for_github_issue(notification)
            
            issue = repo.create_issue(
                title=issue_content['title'],
                body=issue_content['body'],
                labels=issue_content['labels'],
                assignees=assignees or []
            )
            
            logger.info(f"GitHub issue created: {issue.html_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {str(e)}")
            return False


class NotificationManager:
    """Main notification management system."""
    
    def __init__(self, config_file: str = None):
        self.dispatcher = NotificationDispatcher()
        self.rules: List[NotificationRule] = []
        self.last_notification_times: Dict[str, datetime] = {}
        
        # Load configuration
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        else:
            self.setup_default_rules()
    
    def load_config(self, config_file: str):
        """Load notification configuration from file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Parse notification rules
            for rule_config in config.get('notification_rules', []):
                rule = NotificationRule(
                    event_types=[NotificationType(t) for t in rule_config['event_types']],
                    severity_levels=[Severity(s) for s in rule_config['severity_levels']],
                    channels=[NotificationChannel(c) for c in rule_config['channels']],
                    recipients=[
                        NotificationRecipient(
                            name=r['name'],
                            channel=NotificationChannel(r['channel']),
                            address=r['address'],
                            preferences=r.get('preferences', {}),
                            escalation_level=r.get('escalation_level', 1)
                        ) for r in rule_config['recipients']
                    ],
                    conditions=rule_config.get('conditions', {}),
                    cooldown_minutes=rule_config.get('cooldown_minutes', 0),
                    escalation_delay_minutes=rule_config.get('escalation_delay_minutes', 15)
                )
                self.rules.append(rule)
            
            logger.info(f"Loaded {len(self.rules)} notification rules from config")
            
        except Exception as e:
            logger.error(f"Failed to load notification config: {str(e)}")
            self.setup_default_rules()
    
    def setup_default_rules(self):
        """Setup default notification rules."""
        
        # Default recipients
        dev_team = [
            NotificationRecipient("Development Team", NotificationChannel.SLACK, "#deployments"),
            NotificationRecipient("DevOps Team", NotificationChannel.EMAIL, "devops@pratiko.ai")
        ]
        
        escalation_team = [
            NotificationRecipient("Engineering Manager", NotificationChannel.EMAIL, "engineering-manager@pratiko.ai", escalation_level=2),
            NotificationRecipient("CTO", NotificationChannel.EMAIL, "cto@pratiko.ai", escalation_level=3)
        ]
        
        # Rule 1: All deployment events to development team
        self.rules.append(NotificationRule(
            event_types=[
                NotificationType.DEPLOYMENT_STARTED,
                NotificationType.DEPLOYMENT_SUCCESS,
                NotificationType.DEPLOYMENT_FAILED,
                NotificationType.DEPLOYMENT_PARTIAL
            ],
            severity_levels=[Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.CRITICAL],
            channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
            recipients=dev_team,
            cooldown_minutes=5
        ))
        
        # Rule 2: Critical failures with escalation
        self.rules.append(NotificationRule(
            event_types=[
                NotificationType.DEPLOYMENT_FAILED,
                NotificationType.ROLLBACK_FAILED,
                NotificationType.MANUAL_INTERVENTION_REQUIRED
            ],
            severity_levels=[Severity.CRITICAL],
            channels=[NotificationChannel.EMAIL, NotificationChannel.GITHUB_ISSUE],
            recipients=dev_team + escalation_team,
            escalation_delay_minutes=10
        ))
        
        # Rule 3: Production environment alerts
        self.rules.append(NotificationRule(
            event_types=[
                NotificationType.DEPLOYMENT_FAILED,
                NotificationType.HEALTH_CHECK_FAILED
            ],
            severity_levels=[Severity.ERROR, Severity.CRITICAL],
            channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
            recipients=dev_team,
            conditions={"environment": "production"},
            cooldown_minutes=2
        ))
        
        logger.info(f"Setup {len(self.rules)} default notification rules")
    
    async def send_notification(self, notification_type: NotificationType,
                              context: DeploymentContext,
                              severity: Severity = Severity.INFO,
                              custom_message: str = None) -> Dict[str, bool]:
        """Send notification based on type and context."""
        
        # Create notification message
        message = self._create_notification_message(
            notification_type, context, severity, custom_message
        )
        
        # Find matching rules
        matching_rules = self._find_matching_rules(notification_type, severity, context)
        
        results = {}
        
        for rule in matching_rules:
            # Check cooldown
            rule_key = f"{notification_type.value}_{context.deployment_id}_{hash(str(rule))}"
            if self._is_on_cooldown(rule_key, rule.cooldown_minutes):
                logger.info(f"Notification {rule_key} is on cooldown, skipping")
                continue
            
            # Send to each channel/recipient combination
            for recipient in rule.recipients:
                if recipient.channel in rule.channels:
                    success = await self._send_to_recipient(recipient, message, context)
                    results[f"{recipient.channel.value}_{recipient.name}"] = success
                    
                    # Update last notification time
                    self.last_notification_times[rule_key] = datetime.now(timezone.utc)
        
        return results
    
    def _create_notification_message(self, notification_type: NotificationType,
                                   context: DeploymentContext,
                                   severity: Severity,
                                   custom_message: str = None) -> NotificationMessage:
        """Create a formatted notification message."""
        
        # Generate title and body based on notification type
        title, body = self._generate_message_content(notification_type, context, custom_message)
        
        # Generate actionable items
        actions = self._generate_actions(notification_type, context)
        
        return NotificationMessage(
            title=title,
            body=body,
            severity=severity,
            context=context,
            actions=actions,
            metadata={"notification_type": notification_type.value}
        )
    
    def _generate_message_content(self, notification_type: NotificationType,
                                context: DeploymentContext,
                                custom_message: str = None) -> tuple[str, str]:
        """Generate title and body for notification."""
        
        env_emoji = {"production": "🟢", "staging": "🟡", "development": "🔵"}
        env_icon = env_emoji.get(context.environment, "🔵")
        
        service_count = len(context.services)
        service_text = f"{service_count} service{'s' if service_count != 1 else ''}"
        
        if notification_type == NotificationType.DEPLOYMENT_STARTED:
            title = f"{env_icon} Deployment Started: {context.deployment_id}"
            body = custom_message or f"Cross-repository deployment started for {service_text} in {context.environment} environment."
            
        elif notification_type == NotificationType.DEPLOYMENT_SUCCESS:
            title = f"✅ Deployment Successful: {context.deployment_id}"
            body = custom_message or f"All {service_text} successfully deployed to {context.environment}."
            
        elif notification_type == NotificationType.DEPLOYMENT_FAILED:
            title = f"❌ Deployment Failed: {context.deployment_id}"
            body = custom_message or f"Deployment of {service_text} to {context.environment} failed."
            if context.error_message:
                body += f" Error: {context.error_message[:200]}"
                
        elif notification_type == NotificationType.DEPLOYMENT_PARTIAL:
            title = f"⚠️ Partial Deployment: {context.deployment_id}"
            body = custom_message or f"Some services failed to deploy to {context.environment}."
            
        elif notification_type == NotificationType.ROLLBACK_STARTED:
            title = f"🔄 Rollback Started: {context.deployment_id}"
            body = custom_message or f"Rolling back {service_text} in {context.environment} due to deployment failure."
            
        elif notification_type == NotificationType.ROLLBACK_SUCCESS:
            title = f"✅ Rollback Successful: {context.deployment_id}"
            body = custom_message or f"Successfully rolled back {service_text} in {context.environment}."
            
        elif notification_type == NotificationType.ROLLBACK_FAILED:
            title = f"🚨 Rollback Failed: {context.deployment_id}"
            body = custom_message or f"CRITICAL: Rollback failed for {service_text} in {context.environment}. Manual intervention required."
            
        elif notification_type == NotificationType.HEALTH_CHECK_FAILED:
            title = f"🏥 Health Check Failed: {context.deployment_id}"
            body = custom_message or f"Health checks failed for deployed services in {context.environment}."
            
        elif notification_type == NotificationType.COMPATIBILITY_WARNING:
            title = f"⚠️ Compatibility Warning: {context.deployment_id}"
            body = custom_message or f"Compatibility issues detected for {service_text} deployment to {context.environment}."
            
        elif notification_type == NotificationType.MANUAL_INTERVENTION_REQUIRED:
            title = f"🚨 Manual Intervention Required: {context.deployment_id}"
            body = custom_message or f"URGENT: Manual intervention required for {context.environment} deployment. Automated recovery failed."
            
        else:
            title = f"📢 Deployment Notification: {context.deployment_id}"
            body = custom_message or f"Deployment notification for {context.environment} environment."
        
        return title, body
    
    def _generate_actions(self, notification_type: NotificationType,
                        context: DeploymentContext) -> List[Dict[str, str]]:
        """Generate actionable items for notifications."""
        
        actions = []
        
        # Always include workflow links
        for service, url in context.workflow_urls.items():
            actions.append({
                "text": f"View {service.title()} Workflow",
                "url": url,
                "style": "default"
            })
        
        # Include health check links
        for service, url in context.health_urls.items():
            actions.append({
                "text": f"Check {service.title()} Health", 
                "url": url,
                "style": "default"
            })
        
        # Add specific actions based on notification type
        if notification_type in [NotificationType.DEPLOYMENT_FAILED, NotificationType.ROLLBACK_FAILED]:
            if context.rollback_available:
                # This would be a link to trigger rollback
                actions.append({
                    "text": "🔄 Trigger Rollback",
                    "url": f"https://github.com/your-org/deployment-actions/actions/workflows/rollback.yml?deployment_id={context.deployment_id}",
                    "style": "danger"
                })
            
            # Link to troubleshooting runbook
            actions.append({
                "text": "📖 Troubleshooting Guide",
                "url": "https://docs.pratiko.ai/deployment/troubleshooting",
                "style": "primary"
            })
        
        elif notification_type == NotificationType.MANUAL_INTERVENTION_REQUIRED:
            actions.append({
                "text": "🚨 Emergency Procedures",
                "url": "https://docs.pratiko.ai/deployment/emergency",
                "style": "danger"
            })
        
        # Version registry link
        actions.append({
            "text": "📊 Version Registry",
            "url": f"https://version-registry.pratiko.ai/deployments/{context.deployment_id}",
            "style": "default"
        })
        
        return actions
    
    def _find_matching_rules(self, notification_type: NotificationType,
                           severity: Severity,
                           context: DeploymentContext) -> List[NotificationRule]:
        """Find notification rules that match the given criteria."""
        
        matching_rules = []
        
        for rule in self.rules:
            # Check event type
            if notification_type not in rule.event_types:
                continue
            
            # Check severity
            if severity not in rule.severity_levels:
                continue
            
            # Check conditions
            if rule.conditions:
                if not self._check_conditions(rule.conditions, context):
                    continue
            
            matching_rules.append(rule)
        
        return matching_rules
    
    def _check_conditions(self, conditions: Dict[str, Any], context: DeploymentContext) -> bool:
        """Check if context matches the rule conditions."""
        
        for key, expected_value in conditions.items():
            if key == "environment":
                if context.environment != expected_value:
                    return False
            elif key == "services":
                if not any(service in context.services for service in expected_value):
                    return False
            elif key == "severity_threshold":
                # Custom condition logic can be added here
                pass
        
        return True
    
    def _is_on_cooldown(self, rule_key: str, cooldown_minutes: int) -> bool:
        """Check if a notification rule is on cooldown."""
        
        if cooldown_minutes <= 0:
            return False
        
        last_notification = self.last_notification_times.get(rule_key)
        if not last_notification:
            return False
        
        time_since_last = datetime.now(timezone.utc) - last_notification
        return time_since_last.total_seconds() < (cooldown_minutes * 60)
    
    async def _send_to_recipient(self, recipient: NotificationRecipient,
                               message: NotificationMessage,
                               context: DeploymentContext) -> bool:
        """Send notification to a specific recipient."""
        
        try:
            if recipient.channel == NotificationChannel.SLACK:
                return await self.dispatcher.send_slack_notification(recipient.address, message)
            
            elif recipient.channel == NotificationChannel.EMAIL:
                smtp_config = {
                    'host': os.getenv('SMTP_HOST', 'localhost'),
                    'port': int(os.getenv('SMTP_PORT', '587')),
                    'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
                    'username': os.getenv('SMTP_USERNAME'),
                    'password': os.getenv('SMTP_PASSWORD'),
                    'from_email': os.getenv('SMTP_FROM_EMAIL', 'noreply@pratiko.ai')
                }
                return await self.dispatcher.send_email_notification(
                    smtp_config, [recipient.address], message
                )
            
            elif recipient.channel == NotificationChannel.WEBHOOK:
                headers = recipient.preferences.get('headers', {})
                return await self.dispatcher.send_webhook_notification(
                    recipient.address, message, headers
                )
            
            elif recipient.channel == NotificationChannel.GITHUB_ISSUE:
                repo_name = recipient.preferences.get('repository', 'mickgian/PratikoAi-BE')
                assignees = recipient.preferences.get('assignees', [])
                return await self.dispatcher.create_github_issue(
                    repo_name, message, assignees
                )
            
            else:
                logger.warning(f"Unsupported notification channel: {recipient.channel}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification to {recipient.name}: {str(e)}")
            return False


# Example usage and testing
async def main():
    """Example usage of the notification system."""
    
    # Create notification manager
    manager = NotificationManager()
    
    # Create example deployment context
    context = DeploymentContext(
        deployment_id="deploy-prod-20240115-143022",
        environment="production",
        services={"backend": "1.2.0", "frontend-android": "2.1.0", "frontend-web": "2.0.5"},
        status="failed",
        started_at=datetime.now(timezone.utc),
        error_message="Backend health check failed after deployment",
        workflow_urls={
            "backend": "https://github.com/mickgian/PratikoAi-BE/actions/runs/123456",
            "frontend": "https://github.com/mickgian/PratikoAi-KMP/actions/runs/123457"
        },
        health_urls={
            "backend": "https://api.pratiko.ai/health",
            "frontend-web": "https://pratiko.ai/health"
        }
    )
    
    # Send deployment failure notification
    results = await manager.send_notification(
        NotificationType.DEPLOYMENT_FAILED,
        context,
        Severity.CRITICAL,
        "Production deployment failed due to backend health check timeout. Rollback initiated."
    )
    
    print("Notification results:", results)


if __name__ == "__main__":
    asyncio.run(main())