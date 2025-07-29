#!/usr/bin/env python3
"""
PratikoAI Health Monitor and Rollback Integration

Integration layer that connects the health monitoring system with the rollback orchestrator
to provide seamless automatic failure detection and rollback capabilities.

Features:
- Seamless integration between health monitoring and rollback systems
- Automatic rollback triggering based on health conditions
- Comprehensive logging and audit trails
- Recovery validation and verification
- Post-rollback health verification
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import signal
import sys

from health_monitor import HealthMonitor, HealthStatus, HealthReport
from rollback_orchestrator import (
    RollbackOrchestrator, RollbackTrigger, RollbackTarget, 
    RollbackReason, RollbackExecution, RollbackStatus
)

logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """Configuration for health monitor and rollback integration."""
    deployment_id: str
    environment: str
    services: List[str]
    health_config_file: str = "health_monitor_config.yaml"
    rollback_config_file: str = "rollback_config.yaml"
    integration_log_file: str = "/var/log/pratiko-integration.log"
    verification_timeout_minutes: int = 10
    post_rollback_monitoring_minutes: int = 30
    auto_rollback_enabled: bool = True
    require_manual_approval: bool = False


class HealthRollbackIntegration:
    """Main integration class that coordinates health monitoring and rollback operations."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.health_monitor: Optional[HealthMonitor] = None
        self.rollback_orchestrator: Optional[RollbackOrchestrator] = None
        
        self.active_rollbacks: Dict[str, RollbackExecution] = {}
        self.rollback_history: List[Dict[str, Any]] = []
        self.is_running = False
        
        # Set up logging
        self._setup_logging()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.integration_log_file),
                logging.StreamHandler()
            ]
        )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
    
    async def initialize(self):
        """Initialize health monitor and rollback orchestrator."""
        try:
            # Initialize health monitor
            self.health_monitor = HealthMonitor(self.config.health_config_file)
            
            # Initialize rollback orchestrator
            self.rollback_orchestrator = RollbackOrchestrator()
            
            # Connect health monitor to rollback orchestrator
            self.health_monitor.set_rollback_orchestrator(self.rollback_orchestrator)
            
            logger.info("Health monitor and rollback orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize integration: {str(e)}")
            raise
    
    async def start_integrated_monitoring(self):
        """Start integrated health monitoring with automatic rollback capabilities."""
        if not self.health_monitor or not self.rollback_orchestrator:
            raise RuntimeError("Integration not initialized")
        
        self.is_running = True
        logger.info(f"Starting integrated monitoring for deployment: {self.config.deployment_id}")
        
        try:
            # Start health monitoring
            monitoring_task = asyncio.create_task(
                self.health_monitor.start_monitoring(self.config.deployment_id)
            )
            
            # Start integration supervision
            supervision_task = asyncio.create_task(
                self._supervise_integration()
            )
            
            # Wait for completion or interruption
            await asyncio.gather(monitoring_task, supervision_task, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Integrated monitoring failed: {str(e)}")
            raise
        finally:
            self.is_running = False
    
    async def _supervise_integration(self):
        """Supervise the integration and handle rollback events."""
        while self.is_running:
            try:
                # Check for completed rollbacks
                await self._check_rollback_completions()
                
                # Verify post-rollback health
                await self._verify_post_rollback_health()
                
                # Clean up old rollback records
                self._cleanup_old_rollbacks()
                
                # Generate periodic integration reports
                await self._generate_integration_report()
                
                # Wait before next supervision cycle
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Supervision error: {str(e)}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def trigger_manual_rollback(self, reason: str, services: List[str] = None,
                                    preserve_logs: bool = True) -> RollbackExecution:
        """Manually trigger a rollback operation."""
        if not self.rollback_orchestrator:
            raise RuntimeError("Rollback orchestrator not initialized")
        
        # Preserve logs if requested
        if preserve_logs and self.health_monitor:
            logger.info("Preserving logs before manual rollback...")
            await self.health_monitor.log_preserver.preserve_system_logs(self.config.deployment_id)
        
        # Create rollback trigger
        trigger = RollbackTrigger(
            trigger_id=f"manual_{int(datetime.now().timestamp())}",
            reason=RollbackReason.MANUAL,
            triggered_by="manual_operator",
            deployment_id=self.config.deployment_id,
            message=f"Manual rollback requested: {reason}",
            metadata={"manual_reason": reason}
        )
        
        # Determine rollback targets
        if services:
            targets = [
                RollbackTarget(service=service, environment=self.config.environment)
                for service in services
            ]
        else:
            targets = [
                RollbackTarget(service=service, environment=self.config.environment)
                for service in self.config.services
            ]
        
        # Execute rollback
        execution = await self.rollback_orchestrator.initiate_rollback(
            trigger, targets, "manual_operator"
        )
        
        # Track the rollback
        self.active_rollbacks[execution.execution_id] = execution
        
        logger.info(f"Manual rollback initiated: {execution.execution_id}")
        return execution
    
    async def _check_rollback_completions(self):
        """Check for completed rollback operations and handle post-processing."""
        completed_rollbacks = []
        
        for execution_id, execution in self.active_rollbacks.items():
            # Check if rollback is complete
            if execution.status in [RollbackStatus.COMPLETED, RollbackStatus.FAILED, RollbackStatus.PARTIALLY_COMPLETED]:
                completed_rollbacks.append(execution_id)
                
                # Log completion
                logger.info(f"Rollback {execution_id} completed with status: {execution.status.value}")
                
                # Add to history
                self.rollback_history.append({
                    "execution_id": execution_id,
                    "deployment_id": execution.deployment_id,
                    "status": execution.status.value,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "services": [target.service for target in execution.targets],
                    "trigger_reason": execution.trigger.reason.value,
                    "success_rate": len(execution.completed_steps) / len(execution.targets) if execution.targets else 0
                })
                
                # If rollback was successful, start post-rollback monitoring
                if execution.status == RollbackStatus.COMPLETED:
                    await self._start_post_rollback_monitoring(execution)
        
        # Remove completed rollbacks from active tracking
        for execution_id in completed_rollbacks:
            del self.active_rollbacks[execution_id]
    
    async def _start_post_rollback_monitoring(self, execution: RollbackExecution):
        """Start enhanced monitoring after successful rollback."""
        logger.info(f"Starting post-rollback monitoring for {execution.execution_id}")
        
        # Create a task for post-rollback monitoring
        asyncio.create_task(self._monitor_post_rollback_health(execution))
    
    async def _monitor_post_rollback_health(self, execution: RollbackExecution):
        """Monitor system health after rollback to ensure stability."""
        try:
            monitoring_end = datetime.now(timezone.utc).timestamp() + (self.config.post_rollback_monitoring_minutes * 60)
            
            consecutive_healthy_checks = 0
            required_healthy_checks = 5  # Need 5 consecutive healthy checks
            
            while datetime.now(timezone.utc).timestamp() < monitoring_end:
                if not self.health_monitor:
                    break
                
                # Generate health report
                health_report = await self.health_monitor.generate_health_report(self.config.deployment_id)
                
                # Check if system is healthy
                if health_report.overall_status == HealthStatus.HEALTHY:
                    consecutive_healthy_checks += 1
                    logger.info(f"Post-rollback health check {consecutive_healthy_checks}/{required_healthy_checks} passed")
                    
                    if consecutive_healthy_checks >= required_healthy_checks:
                        logger.info(f"Post-rollback stability confirmed for {execution.execution_id}")
                        await self._send_rollback_success_notification(execution, health_report)
                        break
                else:
                    consecutive_healthy_checks = 0
                    logger.warning(f"Post-rollback health issues detected: {health_report.failed_checks}")
                
                await asyncio.sleep(60)  # Check every minute
            
            # If we didn't achieve stability, log a warning
            if consecutive_healthy_checks < required_healthy_checks:
                logger.warning(f"Post-rollback stability not confirmed for {execution.execution_id}")
                await self._send_rollback_instability_alert(execution)
                
        except Exception as e:
            logger.error(f"Post-rollback monitoring failed: {str(e)}")
    
    async def _verify_post_rollback_health(self):
        """Verify health status after rollback operations."""
        if not self.health_monitor or not self.active_rollbacks:
            return
        
        # Generate current health report
        health_report = await self.health_monitor.generate_health_report(self.config.deployment_id)
        
        # Check if we have any active rollbacks that might need attention
        for execution_id, execution in self.active_rollbacks.items():
            if execution.status == RollbackStatus.IN_PROGRESS:
                # Check if rollback is taking too long
                if execution.started_at:
                    duration_minutes = (datetime.now(timezone.utc) - execution.started_at).total_seconds() / 60
                    if duration_minutes > self.config.verification_timeout_minutes:
                        logger.warning(f"Rollback {execution_id} taking longer than expected ({duration_minutes:.1f} minutes)")
    
    async def _send_rollback_success_notification(self, execution: RollbackExecution, health_report: HealthReport):
        """Send notification about successful rollback and system recovery."""
        notification_data = {
            "type": "rollback_success",
            "execution_id": execution.execution_id,
            "deployment_id": execution.deployment_id,
            "services_rolled_back": [target.service for target in execution.targets],
            "rollback_duration": (execution.completed_at - execution.started_at).total_seconds() / 60 if execution.completed_at and execution.started_at else None,
            "health_status": health_report.overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"ROLLBACK SUCCESS: {json.dumps(notification_data, indent=2)}")
        # Here you would integrate with your notification system
    
    async def _send_rollback_instability_alert(self, execution: RollbackExecution):
        """Send alert about post-rollback instability."""
        alert_data = {
            "type": "rollback_instability",
            "execution_id": execution.execution_id,
            "deployment_id": execution.deployment_id,
            "message": "System health not stable after rollback - manual intervention may be required",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.warning(f"ROLLBACK INSTABILITY ALERT: {json.dumps(alert_data, indent=2)}")
        # Here you would integrate with your notification system
    
    def _cleanup_old_rollbacks(self):
        """Clean up old rollback history records."""
        # Keep last 100 rollbacks
        if len(self.rollback_history) > 100:
            self.rollback_history = self.rollback_history[-100:]
    
    async def _generate_integration_report(self):
        """Generate periodic integration status report."""
        if not self.health_monitor:
            return
        
        try:
            # Generate health report
            health_report = await self.health_monitor.generate_health_report(self.config.deployment_id)
            
            # Create integration report
            integration_report = {
                "deployment_id": self.config.deployment_id,
                "environment": self.config.environment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "health_status": health_report.overall_status.value,
                "active_rollbacks": len(self.active_rollbacks),
                "total_rollbacks": len(self.rollback_history),
                "recent_rollbacks": self.rollback_history[-5:] if self.rollback_history else [],
                "services_status": health_report.services,
                "system_recommendations": health_report.recommendations
            }
            
            # Log report every hour
            if datetime.now().minute == 0:
                logger.info(f"Integration Status Report: {json.dumps(integration_report, indent=2)}")
                
        except Exception as e:
            logger.error(f"Failed to generate integration report: {str(e)}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        health_report = None
        if self.health_monitor:
            health_report = await self.health_monitor.generate_health_report(self.config.deployment_id)
        
        return {
            "integration_running": self.is_running,
            "deployment_id": self.config.deployment_id,
            "environment": self.config.environment,
            "health_status": health_report.overall_status.value if health_report else "unknown",
            "active_rollbacks": len(self.active_rollbacks),
            "total_rollbacks": len(self.rollback_history),
            "auto_rollback_enabled": self.config.auto_rollback_enabled,
            "last_report_time": datetime.now(timezone.utc).isoformat()
        }
    
    async def shutdown(self):
        """Gracefully shutdown the integration."""
        logger.info("Shutting down health monitor and rollback integration...")
        
        self.is_running = False
        
        # Stop health monitoring
        if self.health_monitor:
            await self.health_monitor.stop_monitoring()
        
        # Wait for any active rollbacks to complete (with timeout)
        if self.active_rollbacks:
            logger.info(f"Waiting for {len(self.active_rollbacks)} active rollbacks to complete...")
            
            timeout = 300  # 5 minutes timeout
            start_time = datetime.now(timezone.utc).timestamp()
            
            while self.active_rollbacks and (datetime.now(timezone.utc).timestamp() - start_time) < timeout:
                await asyncio.sleep(10)
                await self._check_rollback_completions()
            
            if self.active_rollbacks:
                logger.warning(f"Shutting down with {len(self.active_rollbacks)} rollbacks still active")
        
        logger.info("Integration shutdown complete")


# CLI interface for the integration
async def main():
    """Main CLI interface for the health monitor and rollback integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PratikoAI Health Monitor and Rollback Integration")
    parser.add_argument("--deployment-id", required=True, help="Deployment ID to monitor")
    parser.add_argument("--environment", required=True, help="Environment (staging/production)")
    parser.add_argument("--services", nargs="+", default=["backend", "frontend", "database"], help="Services to monitor")
    parser.add_argument("--health-config", default="health_monitor_config.yaml", help="Health monitor config file")
    parser.add_argument("--rollback-config", default="rollback_config.yaml", help="Rollback config file")
    parser.add_argument("--log-file", default="/var/log/pratiko-integration.log", help="Integration log file")
    parser.add_argument("--disable-auto-rollback", action="store_true", help="Disable automatic rollback")
    parser.add_argument("--manual-rollback", help="Trigger manual rollback with reason")
    parser.add_argument("--status", action="store_true", help="Show integration status")
    
    args = parser.parse_args()
    
    # Create integration configuration
    config = IntegrationConfig(
        deployment_id=args.deployment_id,
        environment=args.environment,
        services=args.services,
        health_config_file=args.health_config,
        rollback_config_file=args.rollback_config,
        integration_log_file=args.log_file,
        auto_rollback_enabled=not args.disable_auto_rollback
    )
    
    # Initialize integration
    integration = HealthRollbackIntegration(config)
    await integration.initialize()
    
    try:
        if args.manual_rollback:
            # Trigger manual rollback
            print(f"Triggering manual rollback: {args.manual_rollback}")
            execution = await integration.trigger_manual_rollback(args.manual_rollback)
            print(f"Rollback initiated: {execution.execution_id}")
            
        elif args.status:
            # Show status
            status = await integration.get_status()
            print(json.dumps(status, indent=2))
            
        else:
            # Start integrated monitoring
            print(f"Starting integrated monitoring for deployment: {args.deployment_id}")
            await integration.start_integrated_monitoring()
            
    except KeyboardInterrupt:
        print("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        await integration.shutdown()


if __name__ == "__main__":
    asyncio.run(main())