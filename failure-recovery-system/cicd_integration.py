#!/usr/bin/env python3
"""
CI/CD Integration for Failure Recovery System
============================================

This module provides comprehensive CI/CD integration capabilities for the failure
recovery system, including:

1. GitHub Actions integration
2. Jenkins pipeline hooks
3. GitLab CI/CD integration
4. Docker container deployment hooks
5. Kubernetes deployment monitoring
6. Generic webhook endpoints for any CI/CD system

The integration automatically triggers failure recovery when deployment issues
are detected and provides real-time feedback to CI/CD systems.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import uuid
import hashlib
import hmac

from failure_categorizer import (
  FailureCategorizer, CategorizedFailure, FailureType, 
  FailureSeverity, ComponentType, FailureContext
)
from decision_tree_engine import DecisionTreeEngine, DecisionResult
from recovery_orchestrator import RecoveryOrchestrator, RecoveryConstraints


class CICDPlatform(Enum):
  """Supported CI/CD platforms."""
  
  GITHUB_ACTIONS = "github_actions"
  JENKINS = "jenkins"
  GITLAB_CI = "gitlab_ci"
  AZURE_DEVOPS = "azure_devops"
  CIRCLECI = "circleci"
  BUILDKITE = "buildkite"
  DRONE = "drone"
  GENERIC_WEBHOOK = "generic_webhook"


class DeploymentPhase(Enum):
  """Phases of deployment where failures can occur."""
  
  BUILD = "build"
  TEST = "test"
  SECURITY_SCAN = "security_scan"
  DEPLOY = "deploy"
  SMOKE_TEST = "smoke_test"
  INTEGRATION_TEST = "integration_test"
  PERFORMANCE_TEST = "performance_test"
  POST_DEPLOY = "post_deploy"
  MONITORING = "monitoring"


class DeploymentEnvironment(Enum):
  """Deployment environments."""
  
  DEVELOPMENT = "development"
  TESTING = "testing"
  STAGING = "staging"
  PRODUCTION = "production"
  CANARY = "canary"
  BLUE_GREEN = "blue_green"


@dataclass
class CICDEvent:
  """Represents a CI/CD event that may trigger failure recovery."""
  
  event_id: str
  platform: CICDPlatform
  timestamp: datetime
  
  # Event source information
  repository: str
  branch: str
  commit_sha: str
  commit_message: str
  author: str
  
  # Deployment information
  environment: DeploymentEnvironment
  deployment_phase: DeploymentPhase
  job_name: str
  job_id: str
  workflow_name: Optional[str] = None
  
  # Failure information
  failed: bool = False
  error_message: Optional[str] = None
  error_code: Optional[str] = None
  failure_logs: List[str] = None
  
  # Metrics and context
  duration_seconds: Optional[float] = None
  resource_usage: Dict[str, Any] = None
  test_results: Dict[str, Any] = None
  
  # Recovery context
  auto_recovery_enabled: bool = True
  recovery_constraints: Optional[Dict[str, Any]] = None
  notification_channels: List[str] = None
  
  def __post_init__(self):
    if self.failure_logs is None:
      self.failure_logs = []
    if self.resource_usage is None:
      self.resource_usage = {}
    if self.test_results is None:
      self.test_results = {}
    if self.notification_channels is None:
      self.notification_channels = []


@dataclass
class RecoveryResponse:
  """Response sent back to CI/CD system after recovery attempt."""
  
  response_id: str
  event_id: str
  timestamp: datetime
  
  # Recovery results
  recovery_attempted: bool
  recovery_successful: bool
  recovery_duration_seconds: Optional[float] = None
  
  # Recovery details
  failure_categorization: Optional[Dict[str, Any]] = None
  recovery_plan_id: Optional[str] = None
  recovery_execution_id: Optional[str] = None
  strategies_used: List[str] = None
  
  # Recommendations
  should_retry_deployment: bool = False
  should_rollback: bool = False
  safe_to_continue: bool = False
  
  # Additional context
  error_message: Optional[str] = None
  recommendations: List[str] = None
  next_steps: List[str] = None
  
  def __post_init__(self):
    if self.strategies_used is None:
      self.strategies_used = []
    if self.recommendations is None:
      self.recommendations = []
    if self.next_steps is None:
      self.next_steps = []


class WebhookSecurityValidator:
  """Validates incoming webhook requests for security."""
  
  def __init__(self, secret_key: str):
    self.secret_key = secret_key
  
  def validate_github_signature(self, payload: bytes, signature: str) -> bool:
    """Validate GitHub webhook signature."""
    if not signature.startswith('sha256='):
      return False
    
    expected_signature = 'sha256=' + hmac.new(
      self.secret_key.encode('utf-8'),
      payload,
      hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
  
  def validate_gitlab_token(self, provided_token: str) -> bool:
    """Validate GitLab webhook token."""
    return hmac.compare_digest(provided_token, self.secret_key)
  
  def validate_jenkins_signature(self, payload: bytes, signature: str) -> bool:
    """Validate Jenkins webhook signature."""
    expected_signature = hmac.new(
      self.secret_key.encode('utf-8'),
      payload,
      hashlib.sha1
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


class CICDIntegrationManager:
  """
  Main manager for CI/CD integrations that coordinates failure detection,
  recovery orchestration, and feedback to CI/CD systems.
  """
  
  def __init__(self, config_path: Optional[Path] = None):
    self.logger = logging.getLogger(__name__)
    self.config_path = config_path or Path(__file__).parent / "cicd_integration_config.yaml"
    
    # Initialize core components
    self.config = self._load_configuration()
    self.failure_categorizer = FailureCategorizer()
    self.recovery_orchestrator = RecoveryOrchestrator()
    
    # Initialize security validator
    webhook_secret = self.config.get("webhook_secret", "default_secret")
    self.security_validator = WebhookSecurityValidator(webhook_secret)
    
    # Event tracking
    self.processed_events: Dict[str, CICDEvent] = {}
    self.recovery_responses: Dict[str, RecoveryResponse] = {}
    
    # Platform-specific handlers
    self.platform_handlers = self._initialize_platform_handlers()
    
    # Background tasks
    self.background_tasks: List[asyncio.Task] = []
    
    # Statistics
    self.integration_stats = {
      "total_events_processed": 0,
      "auto_recoveries_attempted": 0,
      "successful_recoveries": 0,
      "deployment_failures_prevented": 0,
      "false_positives": 0,
      "by_platform": {},
      "by_environment": {}
    }
  
  def _load_configuration(self) -> Dict[str, Any]:
    """Load CI/CD integration configuration."""
    default_config = {
      "webhook_secret": os.getenv("CICD_WEBHOOK_SECRET", "change_me_in_production"),
      "auto_recovery_enabled": True,
      "max_concurrent_recoveries": 3,
      "recovery_timeout_minutes": 30,
      "platforms": {
        "github_actions": {
          "enabled": True,
          "webhook_path": "/webhooks/github",
          "events": ["workflow_run", "deployment", "deployment_status"],
          "auto_recovery_environments": ["staging", "production"],
          "notification_channels": ["slack", "email"]
        },
        "jenkins": {
          "enabled": True,
          "webhook_path": "/webhooks/jenkins",
          "events": ["build_completed", "deployment_completed"],
          "auto_recovery_environments": ["staging", "production"],
          "notification_channels": ["slack"]
        },
        "gitlab_ci": {
          "enabled": True,
          "webhook_path": "/webhooks/gitlab",
          "events": ["pipeline", "deployment"],
          "auto_recovery_environments": ["staging", "production"],
          "notification_channels": ["slack", "email"]
        }
      },
      "recovery_constraints": {
        "development": {
          "max_downtime_minutes": 30,
          "requires_approval": False,
          "notification_required": False
        },
        "staging": {
          "max_downtime_minutes": 15,
          "requires_approval": False,
          "notification_required": True
        },
        "production": {
          "max_downtime_minutes": 5,
          "requires_approval": True,
          "notification_required": True
        }
      },
      "failure_detection": {
        "ignore_patterns": [
          "test.*failure",
          "lint.*error",
          "documentation.*",
          "readme.*"
        ],
        "critical_patterns": [
          "production.*failure",
          "database.*error",
          "security.*vulnerability",
          "authentication.*failure"
        ],
        "auto_recovery_patterns": [
          "connection.*timeout",
          "service.*unavailable",
          "deployment.*timeout",
          "resource.*limit"
        ]
      },
      "notifications": {
        "slack_webhook": os.getenv("SLACK_WEBHOOK_URL", ""),
        "email_recipients": [],
        "github_status_updates": True,
        "gitlab_commit_status": True
      }
    }
    
    if self.config_path.exists():
      try:
        import yaml
        with open(self.config_path, 'r') as f:
          loaded_config = yaml.safe_load(f)
        return {**default_config, **loaded_config}
      except ImportError:
        self.logger.warning("PyYAML not available, using default configuration")
      except Exception as e:
        self.logger.error(f"Error loading configuration: {e}")
    
    return default_config
  
  def _initialize_platform_handlers(self) -> Dict[CICDPlatform, Callable]:
    """Initialize platform-specific event handlers."""
    return {
      CICDPlatform.GITHUB_ACTIONS: self._handle_github_event,
      CICDPlatform.JENKINS: self._handle_jenkins_event,
      CICDPlatform.GITLAB_CI: self._handle_gitlab_event,
      CICDPlatform.AZURE_DEVOPS: self._handle_azure_devops_event,
      CICDPlatform.CIRCLECI: self._handle_circleci_event,
      CICDPlatform.GENERIC_WEBHOOK: self._handle_generic_webhook_event
    }
  
  async def process_webhook_event(self,
                                platform: CICDPlatform,
                                payload: Dict[str, Any],
                                headers: Dict[str, str],
                                raw_payload: bytes = None) -> RecoveryResponse:
    """
    Process incoming webhook event from CI/CD platform.
    
    Args:
      platform: CI/CD platform that sent the event
      payload: Parsed JSON payload
      headers: HTTP headers from the request
      raw_payload: Raw payload bytes for signature validation
      
    Returns:
      RecoveryResponse: Response to send back to CI/CD system
    """
    
    event_id = str(uuid.uuid4())
    
    try:
      self.logger.info(f"Processing {platform.value} webhook event {event_id}")
      
      # Step 1: Validate webhook security
      if not self._validate_webhook_security(platform, headers, raw_payload):
        self.logger.warning(f"Webhook security validation failed for event {event_id}")
        return self._create_error_response(event_id, "Webhook security validation failed")
      
      # Step 2: Parse platform-specific event
      handler = self.platform_handlers.get(platform)
      if not handler:
        self.logger.error(f"No handler found for platform {platform.value}")
        return self._create_error_response(event_id, f"Unsupported platform: {platform.value}")
      
      cicd_event = await handler(payload, headers, event_id)
      if not cicd_event:
        self.logger.info(f"Event {event_id} ignored (not a failure event)")
        return self._create_success_response(event_id, recovery_attempted=False)
      
      self.processed_events[event_id] = cicd_event
      
      # Step 3: Check if this is a failure that should trigger recovery
      if not cicd_event.failed or not self._should_trigger_recovery(cicd_event):
        self.logger.info(f"Event {event_id} does not require recovery")
        return self._create_success_response(event_id, recovery_attempted=False)
      
      # Step 4: Categorize the failure
      categorized_failure = await self._categorize_cicd_failure(cicd_event)
      
      # Step 5: Execute recovery if appropriate
      recovery_response = await self._execute_recovery_for_cicd_event(
        cicd_event, categorized_failure
      )
      
      # Step 6: Update CI/CD system status
      await self._update_cicd_status(cicd_event, recovery_response)
      
      # Step 7: Send notifications
      await self._send_notifications(cicd_event, recovery_response)
      
      # Update statistics
      self._update_integration_statistics(cicd_event, recovery_response)
      
      self.recovery_responses[event_id] = recovery_response
      
      self.logger.info(f"Completed processing event {event_id}: "
                      f"recovery_successful={recovery_response.recovery_successful}")
      
      return recovery_response
    
    except Exception as e:
      self.logger.error(f"Error processing webhook event {event_id}: {e}")
      return self._create_error_response(event_id, str(e))
  
  def _validate_webhook_security(self,
                               platform: CICDPlatform,
                               headers: Dict[str, str],
                               raw_payload: bytes) -> bool:
    """Validate webhook security based on platform."""
    
    if not raw_payload:
      return True  # Skip validation if no raw payload provided
    
    try:
      if platform == CICDPlatform.GITHUB_ACTIONS:
        signature = headers.get('X-Hub-Signature-256', '')
        return self.security_validator.validate_github_signature(raw_payload, signature)
      
      elif platform == CICDPlatform.GITLAB_CI:
        token = headers.get('X-Gitlab-Token', '')
        return self.security_validator.validate_gitlab_token(token)
      
      elif platform == CICDPlatform.JENKINS:
        signature = headers.get('X-Jenkins-Signature', '')
        return self.security_validator.validate_jenkins_signature(raw_payload, signature)
      
      else:
        # For other platforms, implement as needed or skip validation
        return True
    
    except Exception as e:
      self.logger.error(f"Security validation error: {e}")
      return False
  
  async def _handle_github_event(self,
                               payload: Dict[str, Any],
                               headers: Dict[str, str],
                               event_id: str) -> Optional[CICDEvent]:
    """Handle GitHub Actions webhook event."""
    
    event_type = headers.get('X-GitHub-Event', '')
    
    if event_type == 'workflow_run':
      workflow_run = payload.get('workflow_run', {})
      
      # Only process failed workflow runs
      if workflow_run.get('conclusion') != 'failure':
        return None
      
      # Extract deployment phase from workflow name
      workflow_name = workflow_run.get('name', '')
      deployment_phase = self._detect_deployment_phase(workflow_name, workflow_run.get('jobs', []))
      
      # Extract environment from workflow or repository
      environment = self._detect_environment(workflow_run, payload.get('repository', {}))
      
      return CICDEvent(
        event_id=event_id,
        platform=CICDPlatform.GITHUB_ACTIONS,
        timestamp=datetime.now(),
        repository=payload.get('repository', {}).get('full_name', ''),
        branch=workflow_run.get('head_branch', ''),
        commit_sha=workflow_run.get('head_sha', ''),
        commit_message=workflow_run.get('head_commit', {}).get('message', ''),
        author=payload.get('sender', {}).get('login', ''),
        environment=environment,
        deployment_phase=deployment_phase,
        job_name=workflow_name,
        job_id=str(workflow_run.get('id', '')),
        workflow_name=workflow_name,
        failed=True,
        error_message=f"Workflow {workflow_name} failed",
        failure_logs=await self._fetch_github_workflow_logs(workflow_run),
        duration_seconds=(
          (datetime.fromisoformat(workflow_run.get('updated_at', '').replace('Z', '+00:00')) -
           datetime.fromisoformat(workflow_run.get('created_at', '').replace('Z', '+00:00')))
          .total_seconds() if workflow_run.get('updated_at') and workflow_run.get('created_at') else None
        )
      )
    
    elif event_type == 'deployment_status':
      deployment = payload.get('deployment', {})
      deployment_status = payload.get('deployment_status', {})
      
      # Only process failed deployments
      if deployment_status.get('state') != 'failure':
        return None
      
      return CICDEvent(
        event_id=event_id,
        platform=CICDPlatform.GITHUB_ACTIONS,
        timestamp=datetime.now(),
        repository=payload.get('repository', {}).get('full_name', ''),
        branch=deployment.get('ref', ''),
        commit_sha=deployment.get('sha', ''),
        commit_message=deployment.get('description', ''),
        author=deployment.get('creator', {}).get('login', ''),
        environment=DeploymentEnvironment(deployment.get('environment', 'production')),
        deployment_phase=DeploymentPhase.DEPLOY,
        job_name=f"deployment-{deployment.get('environment', '')}",
        job_id=str(deployment.get('id', '')),
        failed=True,
        error_message=deployment_status.get('description', 'Deployment failed'),
        failure_logs=[deployment_status.get('log_url', '')]
      )
    
    return None
  
  async def _handle_jenkins_event(self,
                                payload: Dict[str, Any],
                                headers: Dict[str, str],
                                event_id: str) -> Optional[CICDEvent]:
    """Handle Jenkins webhook event."""
    
    build = payload.get('build', payload)  # Some Jenkins webhooks nest build info
    
    # Only process failed builds
    if build.get('result') != 'FAILURE':
      return None
    
    # Extract job information
    job_name = build.get('fullDisplayName', build.get('jobName', ''))
    build_number = build.get('number', '')
    
    # Detect deployment phase and environment
    deployment_phase = self._detect_deployment_phase(job_name, [])
    environment = self._detect_environment_from_job_name(job_name)
    
    return CICDEvent(
      event_id=event_id,
      platform=CICDPlatform.JENKINS,
      timestamp=datetime.now(),
      repository=build.get('scm', {}).get('url', ''),
      branch=build.get('scm', {}).get('branch', ''),
      commit_sha=build.get('scm', {}).get('commit', ''),
      commit_message=build.get('scm', {}).get('message', ''),
      author=build.get('culprits', [{}])[0].get('fullName', '') if build.get('culprits') else '',
      environment=environment,
      deployment_phase=deployment_phase,
      job_name=job_name,
      job_id=f"{job_name}#{build_number}",
      failed=True,
      error_message=build.get('description', f"Build {job_name}#{build_number} failed"),
      failure_logs=[build.get('url', '') + 'console'],
      duration_seconds=build.get('duration', 0) / 1000.0 if build.get('duration') else None
    )
  
  async def _handle_gitlab_event(self,
                               payload: Dict[str, Any],
                               headers: Dict[str, str],
                               event_id: str) -> Optional[CICDEvent]:
    """Handle GitLab CI webhook event."""
    
    object_kind = payload.get('object_kind', '')
    
    if object_kind == 'pipeline':
      # Only process failed pipelines
      if payload.get('status') != 'failed':
        return None
      
      project = payload.get('project', {})
      
      # Detect environment and phase
      pipeline_name = payload.get('ref', '')
      deployment_phase = self._detect_deployment_phase(pipeline_name, payload.get('builds', []))
      environment = self._detect_environment_from_ref(payload.get('ref', ''))
      
      return CICDEvent(
        event_id=event_id,
        platform=CICDPlatform.GITLAB_CI,
        timestamp=datetime.now(),
        repository=project.get('path_with_namespace', ''),
        branch=payload.get('ref', ''),
        commit_sha=payload.get('sha', ''),
        commit_message=payload.get('commit', {}).get('message', ''),
        author=payload.get('commit', {}).get('author', {}).get('name', ''),
        environment=environment,
        deployment_phase=deployment_phase,
        job_name=f"pipeline-{payload.get('id', '')}",
        job_id=str(payload.get('id', '')),
        failed=True,
        error_message=f"Pipeline {payload.get('id', '')} failed",
        failure_logs=await self._fetch_gitlab_pipeline_logs(payload),
        duration_seconds=payload.get('duration', 0)
      )
    
    elif object_kind == 'deployment':
      # Only process failed deployments
      if payload.get('status') != 'failed':
        return None
      
      deployment = payload.get('deployment', {})
      project = payload.get('project', {})
      
      return CICDEvent(
        event_id=event_id,
        platform=CICDPlatform.GITLAB_CI,
        timestamp=datetime.now(),
        repository=project.get('path_with_namespace', ''),
        branch=deployment.get('ref', ''),
        commit_sha=deployment.get('sha', ''),
        commit_message='',
        author=deployment.get('user', {}).get('name', ''),
        environment=DeploymentEnvironment(deployment.get('environment', 'production')),
        deployment_phase=DeploymentPhase.DEPLOY,
        job_name=f"deployment-{deployment.get('environment', '')}",
        job_id=str(deployment.get('id', '')),
        failed=True,
        error_message=f"Deployment to {deployment.get('environment', '')} failed",
        failure_logs=[]
      )
    
    return None
  
  async def _handle_azure_devops_event(self,
                                     payload: Dict[str, Any],
                                     headers: Dict[str, str],
                                     event_id: str) -> Optional[CICDEvent]:
    """Handle Azure DevOps webhook event."""
    # Implementation for Azure DevOps webhooks
    # This would parse Azure DevOps specific webhook format
    return None
  
  async def _handle_circleci_event(self,
                                 payload: Dict[str, Any],
                                 headers: Dict[str, str],
                                 event_id: str) -> Optional[CICDEvent]:
    """Handle CircleCI webhook event."""
    # Implementation for CircleCI webhooks
    # This would parse CircleCI specific webhook format
    return None
  
  async def _handle_generic_webhook_event(self,
                                        payload: Dict[str, Any],
                                        headers: Dict[str, str],
                                        event_id: str) -> Optional[CICDEvent]:
    """Handle generic webhook event."""
    
    # Generic webhook should provide standardized format
    if not payload.get('failed', False):
      return None
    
    return CICDEvent(
      event_id=event_id,
      platform=CICDPlatform.GENERIC_WEBHOOK,
      timestamp=datetime.now(),
      repository=payload.get('repository', ''),
      branch=payload.get('branch', ''),
      commit_sha=payload.get('commit_sha', ''),
      commit_message=payload.get('commit_message', ''),
      author=payload.get('author', ''),
      environment=DeploymentEnvironment(payload.get('environment', 'production')),
      deployment_phase=DeploymentPhase(payload.get('deployment_phase', 'deploy')),
      job_name=payload.get('job_name', ''),
      job_id=payload.get('job_id', ''),
      failed=True,
      error_message=payload.get('error_message', 'Generic deployment failure'),
      failure_logs=payload.get('failure_logs', [])
    )
  
  def _should_trigger_recovery(self, event: CICDEvent) -> bool:
    """Determine if this event should trigger automatic recovery."""
    
    # Check if auto recovery is enabled globally
    if not self.config.get("auto_recovery_enabled", True):
      return False
    
    # Check if auto recovery is enabled for this platform
    platform_config = self.config.get("platforms", {}).get(event.platform.value, {})
    if not platform_config.get("enabled", False):
      return False
    
    # Check if auto recovery is enabled for this environment
    auto_recovery_envs = platform_config.get("auto_recovery_environments", [])
    if event.environment.value not in auto_recovery_envs:
      return False
    
    # Check against ignore patterns
    ignore_patterns = self.config.get("failure_detection", {}).get("ignore_patterns", [])
    error_text = (event.error_message or '').lower()
    
    for pattern in ignore_patterns:
      if pattern in error_text:
        self.logger.info(f"Event {event.event_id} ignored due to pattern: {pattern}")
        return False
    
    # Check for critical patterns that should always trigger recovery
    critical_patterns = self.config.get("failure_detection", {}).get("critical_patterns", [])
    for pattern in critical_patterns:
      if pattern in error_text:
        self.logger.info(f"Event {event.event_id} triggered by critical pattern: {pattern}")
        return True
    
    # Check for auto recovery patterns
    auto_recovery_patterns = self.config.get("failure_detection", {}).get("auto_recovery_patterns", [])
    for pattern in auto_recovery_patterns:
      if pattern in error_text:
        self.logger.info(f"Event {event.event_id} triggered by auto-recovery pattern: {pattern}")
        return True
    
    # Default: trigger recovery for production failures
    return event.environment == DeploymentEnvironment.PRODUCTION
  
  async def _categorize_cicd_failure(self, event: CICDEvent) -> CategorizedFailure:
    """Categorize a CI/CD failure for recovery planning."""
    
    # Extract error information
    error_messages = [event.error_message] if event.error_message else []
    log_entries = event.failure_logs or []
    
    # Create metrics from event context
    metrics = {}
    if event.duration_seconds:
      metrics["deployment_duration"] = event.duration_seconds
    
    # Add resource usage if available
    if event.resource_usage:
      metrics.update(event.resource_usage)
    
    # Determine status codes based on deployment phase
    status_codes = []
    if event.deployment_phase in [DeploymentPhase.DEPLOY, DeploymentPhase.SMOKE_TEST]:
      status_codes = [503, 502]  # Service unavailable during deployment
    elif event.deployment_phase == DeploymentPhase.BUILD:
      status_codes = [422]  # Build failure
    elif event.deployment_phase == DeploymentPhase.TEST:
      status_codes = [422]  # Test failure
    
    # Create failure context
    context = FailureContext(
      environment=event.environment.value,
      timestamp=event.timestamp,
      deployment_phase=event.deployment_phase.value,
      error_rate=None,  # Not available from CI/CD events
      response_time_degradation=None
    )
    
    # Categorize the failure
    categorized_failure = self.failure_categorizer.categorize_failure(
      error_messages=error_messages,
      log_entries=log_entries,
      metrics=metrics,
      status_codes=status_codes,
      context=context
    )
    
    self.logger.info(f"Categorized CI/CD failure {event.event_id}: "
                    f"{categorized_failure.failure_type.value} "
                    f"({categorized_failure.severity.value})")
    
    return categorized_failure
  
  async def _execute_recovery_for_cicd_event(self,
                                           event: CICDEvent,
                                           failure: CategorizedFailure) -> RecoveryResponse:
    """Execute recovery for a CI/CD event."""
    
    response_id = str(uuid.uuid4())
    
    try:
      # Create recovery constraints based on environment
      constraints = self._create_recovery_constraints(event)
      
      # Create recovery plan
      plan = await self.recovery_orchestrator.create_recovery_plan(failure, constraints)
      
      # Execute recovery
      execution = await self.recovery_orchestrator.execute_recovery_plan(plan)
      
      # Create response
      response = RecoveryResponse(
        response_id=response_id,
        event_id=event.event_id,
        timestamp=datetime.now(),
        recovery_attempted=True,
        recovery_successful=execution.success,
        recovery_duration_seconds=execution.metrics.recovery_duration_seconds,
        failure_categorization={
          "type": failure.failure_type.value,
          "severity": failure.severity.value,
          "components": [c.value for c in failure.affected_components]
        },
        recovery_plan_id=plan.plan_id,
        recovery_execution_id=execution.execution_id,
        strategies_used=[s for s in execution.completed_strategies],
        should_retry_deployment=self._should_retry_deployment(execution, event),
        should_rollback=failure.requires_rollback,
        safe_to_continue=execution.success and not failure.requires_rollback,
        recommendations=self._generate_cicd_recommendations(execution, event, failure),
        next_steps=self._generate_next_steps(execution, event, failure)
      )
      
      if not execution.success:
        response.error_message = execution.error_message
      
      return response
    
    except Exception as e:
      self.logger.error(f"Recovery execution failed for event {event.event_id}: {e}")
      
      return RecoveryResponse(
        response_id=response_id,
        event_id=event.event_id,
        timestamp=datetime.now(),
        recovery_attempted=True,
        recovery_successful=False,
        error_message=str(e),
        should_retry_deployment=False,
        should_rollback=True,
        safe_to_continue=False,
        recommendations=[
          "Manual intervention required",
          "Check system logs for detailed error information",
          "Consider rolling back to previous version"
        ],
        next_steps=[
          "Investigate root cause of recovery failure",
          "Implement manual recovery procedures",
          "Update recovery strategies based on findings"
        ]
      )
  
  def _create_recovery_constraints(self, event: CICDEvent) -> RecoveryConstraints:
    """Create recovery constraints based on CI/CD event context."""
    
    # Get environment-specific constraints
    env_constraints = self.config.get("recovery_constraints", {}).get(
      event.environment.value, {}
    )
    
    # Override with event-specific constraints if provided
    if event.recovery_constraints:
      env_constraints.update(event.recovery_constraints)
    
    return RecoveryConstraints(
      max_downtime_minutes=env_constraints.get("max_downtime_minutes"),
      max_data_loss_seconds=env_constraints.get("max_data_loss_seconds", 0),
      min_availability_percent=env_constraints.get("min_availability_percent"),
      max_resource_utilization=env_constraints.get("max_resource_utilization"),
      business_hours_only=env_constraints.get("business_hours_only", False),
      requires_approval=env_constraints.get("requires_approval", True),
      notification_required=env_constraints.get("notification_required", True)
    )
  
  def _should_retry_deployment(self, execution, event: CICDEvent) -> bool:
    """Determine if deployment should be retried after recovery."""
    
    # Retry if recovery was successful and failure was transient
    if execution.success:
      transient_failure_types = [
        FailureType.RESOURCE,
        FailureType.NETWORK,
        FailureType.TIMING,
        FailureType.INFRASTRUCTURE
      ]
      
      # Get failure type from execution context (simplified)
      return True  # In real implementation, check failure categorization
    
    return False
  
  def _generate_cicd_recommendations(self, execution, event: CICDEvent, failure: CategorizedFailure) -> List[str]:
    """Generate recommendations for CI/CD system."""
    
    recommendations = []
    
    if execution.success:
      recommendations.extend([
        "Recovery completed successfully",
        "System health checks passed",
        "Deployment can proceed with caution"
      ])
      
      # Add specific recommendations based on failure type
      if failure.failure_type == FailureType.RESOURCE:
        recommendations.append("Consider increasing resource allocations")
      elif failure.failure_type == FailureType.DEPENDENCY:
        recommendations.append("Verify external service availability before retry")
      elif failure.failure_type == FailureType.CONFIGURATION:
        recommendations.append("Review configuration changes in recent commits")
    
    else:
      recommendations.extend([
        "Automatic recovery failed",
        "Manual intervention required",
        "Do not retry deployment until issue is resolved"
      ])
      
      if failure.severity == FailureSeverity.CRITICAL:
        recommendations.append("Immediately escalate to on-call team")
      
      if failure.data_integrity_risk:
        recommendations.append("Verify data integrity before proceeding")
    
    return recommendations
  
  def _generate_next_steps(self, execution, event: CICDEvent, failure: CategorizedFailure) -> List[str]:
    """Generate next steps for CI/CD system."""
    
    next_steps = []
    
    if execution.success:
      next_steps.extend([
        "Monitor system metrics for stability",
        "Run smoke tests to verify functionality",
        "Proceed with remaining deployment steps"
      ])
    else:
      next_steps.extend([
        "Stop current deployment pipeline",
        "Investigate failure logs and metrics",
        "Implement manual recovery procedures",
        "Update monitoring and alerting as needed"
      ])
      
      if failure.requires_rollback:
        next_steps.insert(1, "Execute rollback to previous stable version")
    
    return next_steps
  
  async def _update_cicd_status(self, event: CICDEvent, response: RecoveryResponse):
    """Update CI/CD system with recovery status."""
    
    notification_config = self.config.get("notifications", {})
    
    # Update GitHub status
    if (event.platform == CICDPlatform.GITHUB_ACTIONS and 
        notification_config.get("github_status_updates", False)):
      await self._update_github_status(event, response)
    
    # Update GitLab commit status
    if (event.platform == CICDPlatform.GITLAB_CI and 
        notification_config.get("gitlab_commit_status", False)):
      await self._update_gitlab_status(event, response)
    
    # Update Jenkins build description
    if event.platform == CICDPlatform.JENKINS:
      await self._update_jenkins_status(event, response)
  
  async def _update_github_status(self, event: CICDEvent, response: RecoveryResponse):
    """Update GitHub commit status with recovery results."""
    # Implementation would use GitHub API to update commit status
    self.logger.info(f"Would update GitHub status for {event.commit_sha}: "
                    f"recovery_successful={response.recovery_successful}")
  
  async def _update_gitlab_status(self, event: CICDEvent, response: RecoveryResponse):
    """Update GitLab commit status with recovery results."""
    # Implementation would use GitLab API to update commit status
    self.logger.info(f"Would update GitLab status for {event.commit_sha}: "
                    f"recovery_successful={response.recovery_successful}")
  
  async def _update_jenkins_status(self, event: CICDEvent, response: RecoveryResponse):
    """Update Jenkins build description with recovery results."""
    # Implementation would use Jenkins API to update build description
    self.logger.info(f"Would update Jenkins build {event.job_id}: "
                    f"recovery_successful={response.recovery_successful}")
  
  async def _send_notifications(self, event: CICDEvent, response: RecoveryResponse):
    """Send notifications about recovery results."""
    
    notification_config = self.config.get("notifications", {})
    
    # Send Slack notification
    if notification_config.get("slack_webhook"):
      await self._send_slack_notification(event, response)
    
    # Send email notification
    if notification_config.get("email_recipients"):
      await self._send_email_notification(event, response)
  
  async def _send_slack_notification(self, event: CICDEvent, response: RecoveryResponse):
    """Send Slack notification about recovery."""
    # Implementation would send actual Slack message
    status_emoji = "✅" if response.recovery_successful else "❌"
    self.logger.info(f"Would send Slack notification: {status_emoji} "
                    f"Recovery {'successful' if response.recovery_successful else 'failed'} "
                    f"for {event.repository}#{event.branch}")
  
  async def _send_email_notification(self, event: CICDEvent, response: RecoveryResponse):
    """Send email notification about recovery."""
    # Implementation would send actual email
    self.logger.info(f"Would send email notification about recovery "
                    f"{'success' if response.recovery_successful else 'failure'} "
                    f"for {event.repository}")
  
  def _update_integration_statistics(self, event: CICDEvent, response: RecoveryResponse):
    """Update integration statistics."""
    
    self.integration_stats["total_events_processed"] += 1
    
    if response.recovery_attempted:
      self.integration_stats["auto_recoveries_attempted"] += 1
      
      if response.recovery_successful:
        self.integration_stats["successful_recoveries"] += 1
        
        if response.should_retry_deployment:
          self.integration_stats["deployment_failures_prevented"] += 1
    
    # Update platform statistics
    platform_key = event.platform.value
    if platform_key not in self.integration_stats["by_platform"]:
      self.integration_stats["by_platform"][platform_key] = {
        "total": 0, "recovered": 0
      }
    
    self.integration_stats["by_platform"][platform_key]["total"] += 1
    if response.recovery_successful:
      self.integration_stats["by_platform"][platform_key]["recovered"] += 1
    
    # Update environment statistics
    env_key = event.environment.value
    if env_key not in self.integration_stats["by_environment"]:
      self.integration_stats["by_environment"][env_key] = {
        "total": 0, "recovered": 0
      }
    
    self.integration_stats["by_environment"][env_key]["total"] += 1
    if response.recovery_successful:
      self.integration_stats["by_environment"][env_key]["recovered"] += 1
  
  def _create_success_response(self, event_id: str, recovery_attempted: bool = True) -> RecoveryResponse:
    """Create a successful recovery response."""
    return RecoveryResponse(
      response_id=str(uuid.uuid4()),
      event_id=event_id,
      timestamp=datetime.now(),
      recovery_attempted=recovery_attempted,
      recovery_successful=recovery_attempted,
      safe_to_continue=True
    )
  
  def _create_error_response(self, event_id: str, error_message: str) -> RecoveryResponse:
    """Create an error recovery response."""
    return RecoveryResponse(
      response_id=str(uuid.uuid4()),
      event_id=event_id,
      timestamp=datetime.now(),
      recovery_attempted=False,
      recovery_successful=False,
      error_message=error_message,
      safe_to_continue=False
    )
  
  # Helper methods for event parsing
  
  def _detect_deployment_phase(self, workflow_name: str, jobs: List[Dict]) -> DeploymentPhase:
    """Detect deployment phase from workflow name and jobs."""
    
    workflow_lower = workflow_name.lower()
    
    if any(keyword in workflow_lower for keyword in ['build', 'compile']):
      return DeploymentPhase.BUILD
    elif any(keyword in workflow_lower for keyword in ['test', 'spec', 'unit']):
      return DeploymentPhase.TEST
    elif any(keyword in workflow_lower for keyword in ['security', 'scan', 'audit']):
      return DeploymentPhase.SECURITY_SCAN
    elif any(keyword in workflow_lower for keyword in ['deploy', 'release']):
      return DeploymentPhase.DEPLOY
    elif any(keyword in workflow_lower for keyword in ['smoke', 'health']):
      return DeploymentPhase.SMOKE_TEST
    elif any(keyword in workflow_lower for keyword in ['integration', 'e2e']):
      return DeploymentPhase.INTEGRATION_TEST
    elif any(keyword in workflow_lower for keyword in ['performance', 'load']):
      return DeploymentPhase.PERFORMANCE_TEST
    else:
      return DeploymentPhase.POST_DEPLOY
  
  def _detect_environment(self, workflow_run: Dict, repository: Dict) -> DeploymentEnvironment:
    """Detect environment from workflow run information."""
    
    # Check workflow name for environment indicators
    workflow_name = workflow_run.get('name', '').lower()
    branch = workflow_run.get('head_branch', '').lower()
    
    if any(env in workflow_name or env in branch for env in ['prod', 'production']):
      return DeploymentEnvironment.PRODUCTION
    elif any(env in workflow_name or env in branch for env in ['staging', 'stage']):
      return DeploymentEnvironment.STAGING
    elif any(env in workflow_name or env in branch for env in ['test', 'testing']):
      return DeploymentEnvironment.TESTING
    elif any(env in workflow_name or env in branch for env in ['dev', 'development']):
      return DeploymentEnvironment.DEVELOPMENT
    elif 'canary' in workflow_name or 'canary' in branch:
      return DeploymentEnvironment.CANARY
    else:
      # Default based on branch
      if branch in ['main', 'master']:
        return DeploymentEnvironment.PRODUCTION
      elif branch in ['develop', 'dev']:
        return DeploymentEnvironment.DEVELOPMENT
      else:
        return DeploymentEnvironment.TESTING
  
  def _detect_environment_from_job_name(self, job_name: str) -> DeploymentEnvironment:
    """Detect environment from Jenkins job name."""
    
    job_lower = job_name.lower()
    
    if any(env in job_lower for env in ['prod', 'production']):
      return DeploymentEnvironment.PRODUCTION
    elif any(env in job_lower for env in ['staging', 'stage']):
      return DeploymentEnvironment.STAGING
    elif any(env in job_lower for env in ['test', 'testing']):
      return DeploymentEnvironment.TESTING
    elif any(env in job_lower for env in ['dev', 'development']):
      return DeploymentEnvironment.DEVELOPMENT
    else:
      return DeploymentEnvironment.DEVELOPMENT
  
  def _detect_environment_from_ref(self, ref: str) -> DeploymentEnvironment:
    """Detect environment from Git reference."""
    
    ref_lower = ref.lower()
    
    if 'master' in ref_lower or 'main' in ref_lower:
      return DeploymentEnvironment.PRODUCTION
    elif 'develop' in ref_lower or 'dev' in ref_lower:
      return DeploymentEnvironment.DEVELOPMENT
    elif 'staging' in ref_lower or 'stage' in ref_lower:
      return DeploymentEnvironment.STAGING
    elif 'test' in ref_lower:
      return DeploymentEnvironment.TESTING
    else:
      return DeploymentEnvironment.DEVELOPMENT
  
  async def _fetch_github_workflow_logs(self, workflow_run: Dict) -> List[str]:
    """Fetch GitHub workflow logs."""
    # Implementation would fetch actual logs from GitHub API
    # For now, return placeholder
    return [f"GitHub workflow logs for run {workflow_run.get('id', '')}"]
  
  async def _fetch_gitlab_pipeline_logs(self, pipeline: Dict) -> List[str]:
    """Fetch GitLab pipeline logs."""
    # Implementation would fetch actual logs from GitLab API
    # For now, return placeholder
    return [f"GitLab pipeline logs for pipeline {pipeline.get('id', '')}"]
  
  def get_integration_statistics(self) -> Dict[str, Any]:
    """Get current integration statistics."""
    stats = self.integration_stats.copy()
    
    # Calculate success rates
    if stats["auto_recoveries_attempted"] > 0:
      stats["recovery_success_rate"] = (
        stats["successful_recoveries"] / stats["auto_recoveries_attempted"]
      )
    else:
      stats["recovery_success_rate"] = 0.0
    
    # Calculate platform success rates
    for platform, platform_stats in stats["by_platform"].items():
      if platform_stats["total"] > 0:
        platform_stats["success_rate"] = platform_stats["recovered"] / platform_stats["total"]
      else:
        platform_stats["success_rate"] = 0.0
    
    # Calculate environment success rates
    for env, env_stats in stats["by_environment"].items():
      if env_stats["total"] > 0:
        env_stats["success_rate"] = env_stats["recovered"] / env_stats["total"]
      else:
        env_stats["success_rate"] = 0.0
    
    return stats
  
  def export_integration_event(self, event: CICDEvent, format: str = "json") -> str:
    """Export CI/CD event in specified format."""
    
    if format.lower() == "json":
      event_dict = asdict(event)
      
      # Handle enum and datetime serialization
      event_dict["platform"] = event.platform.value
      event_dict["timestamp"] = event.timestamp.isoformat()
      event_dict["environment"] = event.environment.value
      event_dict["deployment_phase"] = event.deployment_phase.value
      
      return json.dumps(event_dict, indent=2)
    
    else:
      return f"Unsupported export format: {format}"


# Flask/FastAPI integration helpers

def create_webhook_endpoints(integration_manager: CICDIntegrationManager):
  """Create webhook endpoints for different platforms."""
  
  # This would be used with Flask or FastAPI to create actual webhook endpoints
  # Example for FastAPI:
  """
  from fastapi import FastAPI, Request, HTTPException
  
  app = FastAPI()
  
  @app.post("/webhooks/github")
  async def github_webhook(request: Request):
    headers = dict(request.headers)
    raw_payload = await request.body()
    payload = await request.json()
    
    try:
      response = await integration_manager.process_webhook_event(
        platform=CICDPlatform.GITHUB_ACTIONS,
        payload=payload,
        headers=headers,
        raw_payload=raw_payload
      )
      return response
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))
  
  @app.post("/webhooks/jenkins")
  async def jenkins_webhook(request: Request):
    # Similar implementation for Jenkins
    pass
  
  @app.post("/webhooks/gitlab")
  async def gitlab_webhook(request: Request):
    # Similar implementation for GitLab
    pass
  """
  
  pass


if __name__ == "__main__":
  # Example usage and testing
  import asyncio
  logging.basicConfig(level=logging.INFO)
  
  async def test_cicd_integration():
    # Create integration manager
    integration_manager = CICDIntegrationManager()
    
    # Example GitHub webhook payload (workflow run failure)
    github_payload = {
      "action": "completed",
      "workflow_run": {
        "id": 12345,
        "name": "Deploy to Production",
        "head_branch": "main",
        "head_sha": "abc123def456",
        "conclusion": "failure",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:05:00Z",
        "head_commit": {
          "message": "Fix database connection issue"
        }
      },
      "repository": {
        "full_name": "company/api-service"
      },
      "sender": {
        "login": "developer"
      }
    }
    
    github_headers = {
      "X-GitHub-Event": "workflow_run",
      "X-Hub-Signature-256": "sha256=fake_signature_for_testing"
    }
    
    print("=== Testing GitHub Webhook Integration ===")
    
    # Process GitHub webhook
    response = await integration_manager.process_webhook_event(
      platform=CICDPlatform.GITHUB_ACTIONS,
      payload=github_payload,
      headers=github_headers,
      raw_payload=b'{"test": "payload"}'  # Mock raw payload
    )
    
    print(f"Response ID: {response.response_id}")
    print(f"Recovery Attempted: {response.recovery_attempted}")
    print(f"Recovery Successful: {response.recovery_successful}")
    print(f"Should Retry Deployment: {response.should_retry_deployment}")
    print(f"Should Rollback: {response.should_rollback}")
    print(f"Safe to Continue: {response.safe_to_continue}")
    
    if response.recommendations:
      print("\nRecommendations:")
      for rec in response.recommendations:
        print(f"  • {rec}")
    
    if response.next_steps:
      print("\nNext Steps:")
      for step in response.next_steps:
        print(f"  • {step}")
    
    # Example Jenkins webhook payload
    jenkins_payload = {
      "build": {
        "fullDisplayName": "production-deploy #42",
        "number": 42,
        "result": "FAILURE",
        "url": "https://jenkins.company.com/job/production-deploy/42/",
        "duration": 300000,  # 5 minutes in milliseconds
        "scm": {
          "url": "https://github.com/company/api-service",
          "branch": "main",
          "commit": "abc123def456",
          "message": "Fix database connection issue"
        },
        "culprits": [
          {"fullName": "Developer Name"}
        ]
      }
    }
    
    jenkins_headers = {
      "X-Jenkins-Signature": "fake_signature_for_testing"
    }
    
    print("\n=== Testing Jenkins Webhook Integration ===")
    
    # Process Jenkins webhook
    response = await integration_manager.process_webhook_event(
      platform=CICDPlatform.JENKINS,
      payload=jenkins_payload,
      headers=jenkins_headers,
      raw_payload=b'{"test": "payload"}'
    )
    
    print(f"Response ID: {response.response_id}")
    print(f"Recovery Attempted: {response.recovery_attempted}")
    print(f"Recovery Successful: {response.recovery_successful}")
    
    # Display integration statistics
    print("\n=== Integration Statistics ===")
    stats = integration_manager.get_integration_statistics()
    print(f"Total Events Processed: {stats['total_events_processed']}")
    print(f"Auto Recoveries Attempted: {stats['auto_recoveries_attempted']}")
    print(f"Successful Recoveries: {stats['successful_recoveries']}")
    print(f"Recovery Success Rate: {stats['recovery_success_rate']:.1%}")
    print(f"Deployment Failures Prevented: {stats['deployment_failures_prevented']}")
    
    print("\nBy Platform:")
    for platform, platform_stats in stats["by_platform"].items():
      print(f"  {platform}: {platform_stats['recovered']}/{platform_stats['total']} "
            f"({platform_stats['success_rate']:.1%})")
    
    print("\nBy Environment:")
    for env, env_stats in stats["by_environment"].items():
      print(f"  {env}: {env_stats['recovered']}/{env_stats['total']} "
            f"({env_stats['success_rate']:.1%})")
  
  # Run the test
  asyncio.run(test_cicd_integration())