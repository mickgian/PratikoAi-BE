#!/usr/bin/env python3
"""
PratikoAI Cross-Repository Deployment Orchestrator

Advanced deployment coordination system that ensures synchronized deployments
between the KMP frontend and FastAPI backend repositories.

Features:
- Cross-repository workflow triggering
- Dependency-based deployment sequencing
- Health validation at each step
- Rollback capabilities
- Comprehensive notification system
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import requests
import httpx
from github import Github
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Deployment status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"


class ServiceType(Enum):
    """Service type enumeration."""
    BACKEND = "backend"
    FRONTEND_ANDROID = "frontend-android"
    FRONTEND_IOS = "frontend-ios"
    FRONTEND_DESKTOP = "frontend-desktop"
    FRONTEND_WEB = "frontend-web"


class Environment(Enum):
    """Environment enumeration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DeploymentStep:
    """Represents a single deployment step."""
    service: ServiceType
    version: str
    environment: Environment
    repository: str
    workflow_name: str
    depends_on: List[str] = field(default_factory=list)
    health_check_url: Optional[str] = None
    rollback_version: Optional[str] = None
    timeout_minutes: int = 30
    retry_count: int = 3


@dataclass
class DeploymentPlan:
    """Complete deployment plan with multiple steps."""
    plan_id: str
    environment: Environment
    steps: List[DeploymentStep]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "orchestrator"
    notifications: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentExecution:
    """Runtime execution state of a deployment plan."""
    plan_id: str
    status: DeploymentStatus
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    workflow_runs: Dict[str, str] = field(default_factory=dict)  # step_id -> run_id
    artifacts: Dict[str, Any] = field(default_factory=dict)


class CrossRepoOrchestrator:
    """Main orchestrator for cross-repository deployments."""
    
    def __init__(self, github_token: str, webhook_url: Optional[str] = None):
        self.github = Github(github_token)
        self.webhook_url = webhook_url
        self.executions: Dict[str, DeploymentExecution] = {}
        
        # Repository configuration
        self.repos = {
            "backend": "mickgian/PratikoAi-BE",
            "frontend": "mickgian/PratikoAi-KMP"
        }
        
        # Version registry integration
        self.version_registry_url = os.getenv('VERSION_REGISTRY_URL', 'http://localhost:8001')
        self.version_registry_token = os.getenv('VERSION_REGISTRY_TOKEN')
        
        # HTTP session for API calls
        self.session = requests.Session()
        if self.version_registry_token:
            self.session.headers['Authorization'] = f'Bearer {self.version_registry_token}'
    
    async def create_deployment_plan(self, 
                                   environment: Environment,
                                   backend_version: str,
                                   frontend_versions: Dict[str, str],
                                   created_by: str = "orchestrator") -> DeploymentPlan:
        """Create a deployment plan for synchronized deployment."""
        
        plan_id = f"deploy-{environment.value}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        logger.info(f"Creating deployment plan {plan_id} for {environment.value}")
        
        steps = []
        
        # Step 1: Deploy backend first
        backend_step = DeploymentStep(
            service=ServiceType.BACKEND,
            version=backend_version,
            environment=environment,
            repository=self.repos["backend"],
            workflow_name="deploy-backend.yml",
            health_check_url=self._get_health_check_url(ServiceType.BACKEND, environment),
            timeout_minutes=20,
            retry_count=2
        )
        steps.append(backend_step)
        
        # Step 2: Deploy frontend services (depend on backend)
        for platform, version in frontend_versions.items():
            service_type = ServiceType(f"frontend-{platform}")
            frontend_step = DeploymentStep(
                service=service_type,
                version=version,
                environment=environment,
                repository=self.repos["frontend"],
                workflow_name=f"deploy-{platform}.yml",
                depends_on=[backend_step.service.value],
                health_check_url=self._get_health_check_url(service_type, environment),
                timeout_minutes=25,
                retry_count=2
            )
            steps.append(frontend_step)
        
        # Configure notifications
        notifications = {
            "slack": {
                "webhook_url": os.getenv('SLACK_WEBHOOK_URL'),
                "channel": "#deployments"
            },
            "email": {
                "enabled": True,
                "recipients": ["devops@pratiko.ai", "engineering@pratiko.ai"]
            },
            "github": {
                "create_issue_on_failure": True,
                "repository": self.repos["backend"]
            }
        }
        
        plan = DeploymentPlan(
            plan_id=plan_id,
            environment=environment,
            steps=steps,
            created_by=created_by,
            notifications=notifications
        )
        
        logger.info(f"Created deployment plan with {len(steps)} steps")
        return plan
    
    async def execute_deployment_plan(self, plan: DeploymentPlan) -> DeploymentExecution:
        """Execute a deployment plan with proper sequencing and validation."""
        
        execution = DeploymentExecution(
            plan_id=plan.plan_id,
            status=DeploymentStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        
        self.executions[plan.plan_id] = execution
        
        try:
            logger.info(f"Starting execution of deployment plan {plan.plan_id}")
            await self._send_notification("deployment_started", plan, execution)
            
            # Execute steps in dependency order
            for step in self._resolve_dependency_order(plan.steps):
                execution.current_step = step.service.value
                
                logger.info(f"Executing step: {step.service.value} v{step.version}")
                
                # Check dependencies are completed
                if not await self._check_dependencies_completed(step, execution):
                    raise Exception(f"Dependencies not satisfied for {step.service.value}")
                
                # Execute the deployment step
                success = await self._execute_step(step, plan, execution)
                
                if success:
                    execution.completed_steps.append(step.service.value)
                    logger.info(f"Step {step.service.value} completed successfully")
                else:
                    execution.failed_steps.append(step.service.value)
                    execution.status = DeploymentStatus.FAILED
                    execution.error_message = f"Step {step.service.value} failed"
                    
                    # Attempt rollback
                    logger.error(f"Step {step.service.value} failed, initiating rollback")
                    await self._initiate_rollback(plan, execution)
                    return execution
            
            # All steps completed successfully
            execution.status = DeploymentStatus.SUCCESS
            execution.completed_at = datetime.now(timezone.utc)
            execution.current_step = None
            
            logger.info(f"Deployment plan {plan.plan_id} completed successfully")
            await self._send_notification("deployment_success", plan, execution)
            
        except Exception as e:
            logger.error(f"Deployment plan {plan.plan_id} failed: {str(e)}")
            execution.status = DeploymentStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            
            await self._send_notification("deployment_failed", plan, execution)
            await self._initiate_rollback(plan, execution)
        
        return execution
    
    def _resolve_dependency_order(self, steps: List[DeploymentStep]) -> List[DeploymentStep]:
        """Resolve deployment order based on dependencies."""
        
        # Simple topological sort
        ordered_steps = []
        remaining_steps = steps.copy()
        
        while remaining_steps:
            # Find steps with no unfulfilled dependencies
            ready_steps = []
            for step in remaining_steps:
                dependencies_met = all(
                    any(completed.service.value == dep for completed in ordered_steps)
                    for dep in step.depends_on
                )
                if dependencies_met:
                    ready_steps.append(step)
            
            if not ready_steps:
                # Circular dependency or invalid dependency
                raise Exception("Cannot resolve deployment dependencies")
            
            # Add ready steps to ordered list
            for step in ready_steps:
                ordered_steps.append(step)
                remaining_steps.remove(step)
        
        return ordered_steps
    
    async def _check_dependencies_completed(self, step: DeploymentStep, 
                                          execution: DeploymentExecution) -> bool:
        """Check if all dependencies for a step are completed."""
        
        if not step.depends_on:
            return True
        
        for dependency in step.depends_on:
            if dependency not in execution.completed_steps:
                logger.warning(f"Dependency {dependency} not completed for {step.service.value}")
                return False
        
        return True
    
    async def _execute_step(self, step: DeploymentStep, plan: DeploymentPlan, 
                           execution: DeploymentExecution) -> bool:
        """Execute a single deployment step."""
        
        try:
            # 1. Validate compatibility before deployment
            if not await self._validate_compatibility(step, plan):
                logger.error(f"Compatibility check failed for {step.service.value}")
                return False
            
            # 2. Trigger GitHub Actions workflow
            run_id = await self._trigger_workflow(step, plan)
            if not run_id:
                logger.error(f"Failed to trigger workflow for {step.service.value}")
                return False
            
            execution.workflow_runs[step.service.value] = run_id
            
            # 3. Wait for workflow completion
            if not await self._wait_for_workflow_completion(step, run_id):
                logger.error(f"Workflow failed for {step.service.value}")
                return False
            
            # 4. Perform health check
            if step.health_check_url:
                if not await self._perform_health_check(step):
                    logger.error(f"Health check failed for {step.service.value}")
                    return False
            
            # 5. Update version registry
            await self._update_version_registry(step, plan)
            
            return True
            
        except Exception as e:
            logger.error(f"Step execution failed for {step.service.value}: {str(e)}")
            return False
    
    async def _validate_compatibility(self, step: DeploymentStep, plan: DeploymentPlan) -> bool:
        """Validate compatibility before deployment."""
        
        try:
            # Use the version management system to check compatibility
            response = self.session.post(
                f"{self.version_registry_url}/api/v1/validate-deployment",
                json={
                    "service_type": step.service.value,
                    "version": step.version,
                    "environment": step.environment.value
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("can_deploy", False)
            else:
                logger.error(f"Compatibility check API error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Compatibility check failed: {str(e)}")
            return False
    
    async def _trigger_workflow(self, step: DeploymentStep, plan: DeploymentPlan) -> Optional[str]:
        """Trigger GitHub Actions workflow in the target repository."""
        
        try:
            repo = self.github.get_repo(step.repository)
            
            # Prepare workflow inputs
            inputs = {
                "version": step.version,
                "environment": step.environment.value,
                "deployment_id": plan.plan_id,
                "service_type": step.service.value,
                "orchestrated": "true"
            }
            
            # Add platform-specific inputs for frontend
            if step.service != ServiceType.BACKEND:
                platform = step.service.value.replace("frontend-", "")
                inputs["platform"] = platform
            
            # Trigger workflow
            workflow = repo.get_workflow(step.workflow_name)
            success = workflow.create_dispatch("main", inputs)
            
            if success:
                # Get the most recent run (there's a small delay)
                await asyncio.sleep(5)
                runs = workflow.get_runs()
                latest_run = runs[0] if runs.totalCount > 0 else None
                
                if latest_run:
                    logger.info(f"Triggered workflow {step.workflow_name} for {step.service.value}, run ID: {latest_run.id}")
                    return str(latest_run.id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to trigger workflow for {step.service.value}: {str(e)}")
            return None
    
    async def _wait_for_workflow_completion(self, step: DeploymentStep, run_id: str) -> bool:
        """Wait for GitHub Actions workflow to complete."""
        
        try:
            repo = self.github.get_repo(step.repository)
            
            # Poll workflow status
            timeout_seconds = step.timeout_minutes * 60
            poll_interval = 30  # Poll every 30 seconds
            elapsed_time = 0
            
            while elapsed_time < timeout_seconds:
                run = repo.get_workflow_run(int(run_id))
                
                logger.info(f"Workflow {run_id} status: {run.status} / {run.conclusion}")
                
                if run.status == "completed":
                    if run.conclusion == "success":
                        # Download artifacts if available
                        await self._download_workflow_artifacts(step, run)
                        return True
                    else:
                        logger.error(f"Workflow {run_id} failed with conclusion: {run.conclusion}")
                        return False
                
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
            
            logger.error(f"Workflow {run_id} timed out after {step.timeout_minutes} minutes")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for workflow {run_id}: {str(e)}")
            return False
    
    async def _download_workflow_artifacts(self, step: DeploymentStep, run) -> None:
        """Download and store workflow artifacts."""
        
        try:
            artifacts = run.get_artifacts()
            
            for artifact in artifacts:
                if artifact.name in ["deployment-info", "version-info", "health-report"]:
                    logger.info(f"Found artifact: {artifact.name}")
                    
                    # Store artifact metadata (actual download requires additional setup)
                    if step.service.value not in self.executions:
                        continue
                    
                    execution = next(
                        (exec for exec in self.executions.values() 
                         if step.service.value in exec.workflow_runs.values()),
                        None
                    )
                    
                    if execution:
                        execution.artifacts[f"{step.service.value}_{artifact.name}"] = {
                            "id": artifact.id,
                            "name": artifact.name,
                            "size": artifact.size_in_bytes,
                            "created_at": artifact.created_at.isoformat(),
                            "download_url": artifact.archive_download_url
                        }
            
        except Exception as e:
            logger.warning(f"Failed to download artifacts for {step.service.value}: {str(e)}")
    
    async def _perform_health_check(self, step: DeploymentStep) -> bool:
        """Perform health check on deployed service."""
        
        if not step.health_check_url:
            return True
        
        try:
            # Wait a bit for service to be ready
            await asyncio.sleep(10)
            
            async with httpx.AsyncClient(timeout=30) as client:
                for attempt in range(3):  # Retry up to 3 times
                    try:
                        response = await client.get(step.health_check_url)
                        
                        if response.status_code == 200:
                            health_data = response.json()
                            if health_data.get("status") == "healthy":
                                logger.info(f"Health check passed for {step.service.value}")
                                return True
                        
                        logger.warning(f"Health check attempt {attempt + 1} failed for {step.service.value}: {response.status_code}")
                        
                    except Exception as e:
                        logger.warning(f"Health check attempt {attempt + 1} error for {step.service.value}: {str(e)}")
                    
                    if attempt < 2:  # Don't sleep on the last attempt
                        await asyncio.sleep(10)
            
            logger.error(f"All health check attempts failed for {step.service.value}")
            return False
            
        except Exception as e:
            logger.error(f"Health check failed for {step.service.value}: {str(e)}")
            return False
    
    async def _update_version_registry(self, step: DeploymentStep, plan: DeploymentPlan) -> None:
        """Update version registry with deployment information."""
        
        try:
            payload = {
                "service_type": step.service.value,
                "version": step.version,
                "environment": step.environment.value,
                "deployed_by": plan.created_by,
                "deployment_id": plan.plan_id,
                "deployment_strategy": "orchestrated"
            }
            
            response = self.session.post(
                f"{self.version_registry_url}/api/v1/deployments",
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Updated version registry for {step.service.value}")
            else:
                logger.warning(f"Failed to update version registry: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Version registry update failed: {str(e)}")
    
    async def _initiate_rollback(self, plan: DeploymentPlan, execution: DeploymentExecution) -> None:
        """Initiate rollback of failed deployment."""
        
        logger.info(f"Initiating rollback for deployment {plan.plan_id}")
        execution.status = DeploymentStatus.ROLLING_BACK
        
        try:
            # Rollback completed steps in reverse order
            for step_name in reversed(execution.completed_steps):
                step = next((s for s in plan.steps if s.service.value == step_name), None)
                if step and step.rollback_version:
                    logger.info(f"Rolling back {step.service.value} to {step.rollback_version}")
                    
                    # Create rollback step
                    rollback_step = DeploymentStep(
                        service=step.service,
                        version=step.rollback_version,
                        environment=step.environment,
                        repository=step.repository,
                        workflow_name=step.workflow_name,
                        health_check_url=step.health_check_url,
                        timeout_minutes=15,
                        retry_count=1
                    )
                    
                    # Execute rollback
                    success = await self._execute_step(rollback_step, plan, execution)
                    if not success:
                        logger.error(f"Rollback failed for {step.service.value}")
            
            await self._send_notification("rollback_completed", plan, execution)
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            await self._send_notification("rollback_failed", plan, execution)
    
    def _get_health_check_url(self, service: ServiceType, environment: Environment) -> str:
        """Get health check URL for a service in an environment."""
        
        base_urls = {
            Environment.DEVELOPMENT: {
                ServiceType.BACKEND: "http://localhost:8000",
                ServiceType.FRONTEND_WEB: "http://localhost:3000"
            },
            Environment.STAGING: {
                ServiceType.BACKEND: "https://api-staging.pratiko.ai",
                ServiceType.FRONTEND_WEB: "https://staging.pratiko.ai"
            },
            Environment.PRODUCTION: {
                ServiceType.BACKEND: "https://api.pratiko.ai",
                ServiceType.FRONTEND_WEB: "https://pratiko.ai"
            }
        }
        
        base_url = base_urls.get(environment, {}).get(service)
        if base_url:
            return f"{base_url}/health"
        
        return None
    
    async def _send_notification(self, event_type: str, plan: DeploymentPlan, 
                               execution: DeploymentExecution) -> None:
        """Send notifications about deployment events."""
        
        try:
            # Prepare notification data
            notification_data = {
                "event": event_type,
                "plan_id": plan.plan_id,
                "environment": plan.environment.value,
                "status": execution.status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "steps": {
                    "completed": execution.completed_steps,
                    "failed": execution.failed_steps,
                    "current": execution.current_step
                },
                "duration": self._calculate_duration(execution),
                "error": execution.error_message
            }
            
            # Send Slack notification
            if plan.notifications.get("slack", {}).get("webhook_url"):
                await self._send_slack_notification(event_type, notification_data, plan)
            
            # Send email notification
            if plan.notifications.get("email", {}).get("enabled"):
                await self._send_email_notification(event_type, notification_data, plan)
            
            # Create GitHub issue on failure
            if (event_type in ["deployment_failed", "rollback_failed"] and 
                plan.notifications.get("github", {}).get("create_issue_on_failure")):
                await self._create_github_issue(notification_data, plan)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
    
    async def _send_slack_notification(self, event_type: str, data: Dict[str, Any], 
                                     plan: DeploymentPlan) -> None:
        """Send Slack notification."""
        
        webhook_url = plan.notifications["slack"]["webhook_url"]
        if not webhook_url:
            return
        
        # Format message based on event type
        color = {
            "deployment_started": "#36a64f",
            "deployment_success": "#36a64f",
            "deployment_failed": "#ff0000",
            "rollback_completed": "#ffaa00",
            "rollback_failed": "#ff0000"
        }.get(event_type, "#808080")
        
        message = {
            "attachments": [{
                "color": color,
                "title": f"🚀 Cross-Repository Deployment {event_type.replace('_', ' ').title()}",
                "fields": [
                    {"title": "Plan ID", "value": data["plan_id"], "short": True},
                    {"title": "Environment", "value": data["environment"], "short": True},
                    {"title": "Status", "value": data["status"], "short": True},
                    {"title": "Duration", "value": data["duration"], "short": True}
                ],
                "footer": "PratikoAI Deployment Orchestrator",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        if data["error"]:
            message["attachments"][0]["fields"].append({
                "title": "Error", 
                "value": data["error"], 
                "short": False
            })
        
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=message)
    
    async def _send_email_notification(self, event_type: str, data: Dict[str, Any], 
                                     plan: DeploymentPlan) -> None:
        """Send email notification (implementation depends on email service)."""
        
        # This would integrate with your email service (SendGrid, SES, etc.)
        logger.info(f"Email notification sent for {event_type}: {data['plan_id']}")
    
    async def _create_github_issue(self, data: Dict[str, Any], plan: DeploymentPlan) -> None:
        """Create GitHub issue for deployment failures."""
        
        try:
            repo_name = plan.notifications["github"]["repository"]
            repo = self.github.get_repo(repo_name)
            
            title = f"🚨 Cross-Repository Deployment Failed: {data['plan_id']}"
            
            body = f"""
## Deployment Failure Report

**Plan ID:** {data['plan_id']}  
**Environment:** {data['environment']}  
**Status:** {data['status']}  
**Timestamp:** {data['timestamp']}  
**Duration:** {data['duration']}

### Failed Steps
{', '.join(data['steps']['failed']) if data['steps']['failed'] else 'None'}

### Completed Steps
{', '.join(data['steps']['completed']) if data['steps']['completed'] else 'None'}

### Error Details
```
{data['error'] or 'No specific error message'}
```

### Next Steps
1. Review the deployment logs
2. Check service health status
3. Validate compatibility requirements
4. Consider manual rollback if needed

### Deployment Orchestrator
This issue was automatically created by the PratikoAI Deployment Orchestrator.

Labels: deployment-failure, orchestrator, {data['environment']}
            """
            
            repo.create_issue(
                title=title,
                body=body.strip(),
                labels=["deployment-failure", "orchestrator", data['environment']]
            )
            
            logger.info(f"Created GitHub issue for deployment failure: {data['plan_id']}")
            
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {str(e)}")
    
    def _calculate_duration(self, execution: DeploymentExecution) -> str:
        """Calculate deployment duration."""
        
        if not execution.started_at:
            return "Not started"
        
        end_time = execution.completed_at or datetime.now(timezone.utc)
        duration = end_time - execution.started_at
        
        minutes = int(duration.total_seconds() / 60)
        seconds = int(duration.total_seconds() % 60)
        
        return f"{minutes}m {seconds}s"
    
    async def get_deployment_status(self, plan_id: str) -> Optional[DeploymentExecution]:
        """Get current status of a deployment."""
        return self.executions.get(plan_id)
    
    async def cancel_deployment(self, plan_id: str) -> bool:
        """Cancel a running deployment."""
        
        execution = self.executions.get(plan_id)
        if not execution or execution.status != DeploymentStatus.RUNNING:
            return False
        
        execution.status = DeploymentStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)
        
        logger.info(f"Cancelled deployment {plan_id}")
        return True


# CLI Interface for the orchestrator
if __name__ == "__main__":
    import argparse
    
    async def main():
        parser = argparse.ArgumentParser(description="PratikoAI Cross-Repository Deployment Orchestrator")
        parser.add_argument("--github-token", required=True, help="GitHub personal access token")
        parser.add_argument("--environment", required=True, choices=["development", "staging", "production"])
        parser.add_argument("--backend-version", required=True, help="Backend version to deploy")
        parser.add_argument("--frontend-versions", required=True, help="JSON string of frontend versions")
        parser.add_argument("--webhook-url", help="Webhook URL for notifications")
        parser.add_argument("--created-by", default="cli", help="User triggering the deployment")
        
        args = parser.parse_args()
        
        # Parse frontend versions
        try:
            frontend_versions = json.loads(args.frontend_versions)
        except json.JSONDecodeError:
            print("Error: frontend-versions must be valid JSON")
            return
        
        # Create orchestrator
        orchestrator = CrossRepoOrchestrator(args.github_token, args.webhook_url)
        
        # Create deployment plan
        plan = await orchestrator.create_deployment_plan(
            Environment(args.environment),
            args.backend_version,
            frontend_versions,
            args.created_by
        )
        
        print(f"Created deployment plan: {plan.plan_id}")
        
        # Execute deployment
        execution = await orchestrator.execute_deployment_plan(plan)
        
        print(f"Deployment completed with status: {execution.status.value}")
        if execution.error_message:
            print(f"Error: {execution.error_message}")
    
    asyncio.run(main())