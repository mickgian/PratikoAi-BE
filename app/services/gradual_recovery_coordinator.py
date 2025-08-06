"""
Gradual Recovery Coordinator for Advanced Circuit Breakers.

Manages sophisticated recovery strategies for failed providers with progressive
traffic restoration and intelligent failure detection during recovery phases.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from uuid import uuid4

from app.core.logging import logger
from app.services.cache import CacheService
from app.services.advanced_circuit_breaker import CircuitState, FailureType
from app.services.provider_health_scorer import ProviderHealthScorer, HealthStatus


class RecoveryPhase(Enum):
    """Recovery phases"""
    PREPARATION = "preparation"
    INITIAL = "initial"
    PROGRESSIVE = "progressive" 
    VALIDATION = "validation"
    COMPLETION = "completion"
    FAILED = "failed"


class RecoveryStrategy(Enum):
    """Recovery strategy types"""
    CONSERVATIVE = "conservative"  # Slow, careful recovery
    MODERATE = "moderate"          # Balanced approach
    AGGRESSIVE = "aggressive"      # Fast recovery for urgent needs
    ITALIAN_MARKET = "italian_market"  # Italian market-specific


@dataclass
class RecoveryPlan:
    """Recovery plan configuration"""
    recovery_id: str
    provider: str
    strategy: RecoveryStrategy
    traffic_percentages: List[float]
    phase_durations: List[int]  # Duration in seconds for each phase
    success_thresholds: List[float]  # Required success rate for each phase
    failure_tolerance: List[int]  # Max failures allowed per phase
    current_phase: int
    created_at: datetime
    estimated_completion: datetime


@dataclass
class RecoveryStatus:
    """Current recovery status"""
    recovery_id: str
    provider: str
    phase: RecoveryPhase
    current_percentage: float
    success_rate: float
    failures_in_phase: int
    phase_start_time: datetime
    time_remaining: int
    health_score: float
    can_progress: bool


class GradualRecoveryCoordinator:
    """Manages gradual recovery processes for circuit breakers"""
    
    def __init__(self, 
                 health_scorer: ProviderHealthScorer,
                 cache: Optional[CacheService] = None):
        self.health_scorer = health_scorer
        self.cache = cache
        self.active_recoveries = {}  # recovery_id -> RecoveryPlan
        self.recovery_history = {}   # provider -> list of recovery attempts
        self.recovery_tasks = {}     # recovery_id -> asyncio.Task
        
        # Recovery strategies configuration
        self.strategies = self._initialize_strategies()
        
        # Italian market specific settings
        self.italian_adjustments = {
            "peak_hours_factor": 0.8,      # Slower during peak hours
            "tax_deadline_factor": 0.6,    # Much slower during deadlines
            "vacation_factor": 1.2,        # Faster during August vacation
            "off_hours_factor": 1.1        # Slightly faster off hours
        }
        
        # Statistics
        self.stats = {
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "average_recovery_time": 0.0,
            "current_active_recoveries": 0
        }
    
    async def start_recovery(self, 
                           provider: str, 
                           strategy: RecoveryStrategy = RecoveryStrategy.MODERATE,
                           custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start gradual recovery for a provider"""
        
        try:
            # Check if recovery already in progress
            existing_recovery = self._get_active_recovery_for_provider(provider)
            if existing_recovery:
                return {
                    "success": False,
                    "error": "Recovery already in progress",
                    "existing_recovery_id": existing_recovery.recovery_id
                }
            
            # Create recovery plan
            recovery_plan = await self._create_recovery_plan(provider, strategy, custom_config or {})
            
            # Store the plan
            self.active_recoveries[recovery_plan.recovery_id] = recovery_plan
            
            # Start recovery task
            recovery_task = asyncio.create_task(
                self._execute_recovery(recovery_plan.recovery_id)
            )
            self.recovery_tasks[recovery_plan.recovery_id] = recovery_task
            
            # Update statistics
            self.stats["total_recoveries"] += 1
            self.stats["current_active_recoveries"] += 1
            
            logger.info(f"Started recovery for {provider} with strategy {strategy.value} (ID: {recovery_plan.recovery_id})")
            
            return {
                "success": True,
                "recovery_id": recovery_plan.recovery_id,
                "provider": provider,
                "strategy": strategy.value,
                "estimated_completion": recovery_plan.estimated_completion.isoformat(),
                "initial_percentage": recovery_plan.traffic_percentages[0] if recovery_plan.traffic_percentages else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to start recovery for {provider}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_recovery_status(self, recovery_id: str) -> Optional[RecoveryStatus]:
        """Get current status of a recovery process"""
        
        if recovery_id not in self.active_recoveries:
            return None
        
        plan = self.active_recoveries[recovery_id]
        
        try:
            # Get current health score
            health_metrics = {"total_requests": 0}  # Placeholder
            health_score_obj = await self.health_scorer.calculate_health_score(
                plan.provider, health_metrics
            )
            
            # Calculate current status
            current_phase_index = plan.current_phase
            current_percentage = plan.traffic_percentages[current_phase_index] if current_phase_index < len(plan.traffic_percentages) else 100.0
            
            # Determine phase
            phase = RecoveryPhase.PROGRESSIVE
            if current_phase_index == 0:
                phase = RecoveryPhase.INITIAL
            elif current_phase_index >= len(plan.traffic_percentages) - 1:
                phase = RecoveryPhase.COMPLETION
            
            # Calculate time remaining
            phase_start = plan.created_at + timedelta(
                seconds=sum(plan.phase_durations[:current_phase_index])
            )
            phase_duration = plan.phase_durations[current_phase_index] if current_phase_index < len(plan.phase_durations) else 300
            time_remaining = max(0, phase_duration - (datetime.utcnow() - phase_start).total_seconds())
            
            return RecoveryStatus(
                recovery_id=recovery_id,
                provider=plan.provider,
                phase=phase,
                current_percentage=current_percentage,
                success_rate=0.85,  # Would be calculated from actual metrics
                failures_in_phase=0,  # Would be tracked during recovery
                phase_start_time=phase_start,
                time_remaining=int(time_remaining),
                health_score=health_score_obj.overall_score,
                can_progress=health_score_obj.overall_score > 0.7
            )
            
        except Exception as e:
            logger.error(f"Failed to get recovery status for {recovery_id}: {e}")
            return None
    
    async def abort_recovery(self, recovery_id: str, reason: str = "manual_abort") -> bool:
        """Abort an ongoing recovery"""
        
        try:
            if recovery_id not in self.active_recoveries:
                return False
            
            plan = self.active_recoveries[recovery_id]
            
            # Cancel recovery task
            if recovery_id in self.recovery_tasks:
                self.recovery_tasks[recovery_id].cancel()
                del self.recovery_tasks[recovery_id]
            
            # Update statistics
            self.stats["failed_recoveries"] += 1
            self.stats["current_active_recoveries"] -= 1
            
            # Record in history
            await self._record_recovery_history(plan, "aborted", reason)
            
            # Clean up
            del self.active_recoveries[recovery_id]
            
            logger.warning(f"Aborted recovery {recovery_id} for {plan.provider}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to abort recovery {recovery_id}: {e}")
            return False
    
    async def _create_recovery_plan(self, 
                                  provider: str, 
                                  strategy: RecoveryStrategy,
                                  custom_config: Dict[str, Any]) -> RecoveryPlan:
        """Create a recovery plan based on strategy and Italian market conditions"""
        
        # Get base strategy configuration
        strategy_config = self.strategies[strategy]
        
        # Apply Italian market adjustments
        italian_factor = await self._calculate_italian_market_factor()
        
        # Adjust traffic percentages
        base_percentages = custom_config.get("traffic_percentages", strategy_config["traffic_percentages"])
        adjusted_percentages = [p for p in base_percentages]  # Copy base percentages
        
        # Adjust phase durations based on market conditions
        base_durations = custom_config.get("phase_durations", strategy_config["phase_durations"])
        adjusted_durations = [int(d * italian_factor) for d in base_durations]
        
        # Calculate estimated completion time
        total_duration = sum(adjusted_durations)
        estimated_completion = datetime.utcnow() + timedelta(seconds=total_duration)
        
        recovery_id = str(uuid4())
        
        plan = RecoveryPlan(
            recovery_id=recovery_id,
            provider=provider,
            strategy=strategy,
            traffic_percentages=adjusted_percentages,
            phase_durations=adjusted_durations,
            success_thresholds=custom_config.get("success_thresholds", strategy_config["success_thresholds"]),
            failure_tolerance=custom_config.get("failure_tolerance", strategy_config["failure_tolerance"]),
            current_phase=0,
            created_at=datetime.utcnow(),
            estimated_completion=estimated_completion
        )
        
        return plan
    
    async def _execute_recovery(self, recovery_id: str):
        """Execute the recovery process"""
        
        try:
            plan = self.active_recoveries[recovery_id]
            
            logger.info(f"Starting recovery execution for {plan.provider} (ID: {recovery_id})")
            
            for phase_index in range(len(plan.traffic_percentages)):
                # Update current phase
                plan.current_phase = phase_index
                
                traffic_percentage = plan.traffic_percentages[phase_index]
                phase_duration = plan.phase_durations[phase_index]
                success_threshold = plan.success_thresholds[phase_index]
                failure_tolerance = plan.failure_tolerance[phase_index]
                
                logger.info(f"Recovery {recovery_id} entering phase {phase_index}: {traffic_percentage}% traffic for {phase_duration}s")
                
                # Execute phase
                phase_success = await self._execute_recovery_phase(
                    plan, phase_index, traffic_percentage, phase_duration, 
                    success_threshold, failure_tolerance
                )
                
                if not phase_success:
                    logger.warning(f"Recovery {recovery_id} failed in phase {phase_index}")
                    await self._handle_recovery_failure(plan, phase_index)
                    return
                
                # Wait for phase duration (with early exit conditions)
                await self._wait_for_phase_completion(plan, phase_index, phase_duration)
                
                # Validate phase success
                if not await self._validate_phase_success(plan, phase_index, success_threshold):
                    logger.warning(f"Recovery {recovery_id} failed validation in phase {phase_index}")
                    await self._handle_recovery_failure(plan, phase_index)
                    return
            
            # Recovery completed successfully
            await self._complete_recovery(plan)
            
        except asyncio.CancelledError:
            logger.info(f"Recovery {recovery_id} was cancelled")
        except Exception as e:
            logger.error(f"Recovery execution failed for {recovery_id}: {e}")
            plan = self.active_recoveries.get(recovery_id)
            if plan:
                await self._handle_recovery_failure(plan, plan.current_phase, str(e))
    
    async def _execute_recovery_phase(self, 
                                    plan: RecoveryPlan, 
                                    phase_index: int,
                                    traffic_percentage: float,
                                    phase_duration: int,
                                    success_threshold: float,
                                    failure_tolerance: int) -> bool:
        """Execute a single recovery phase"""
        
        try:
            # Apply traffic percentage (this would integrate with load balancer)
            await self._apply_traffic_percentage(plan.provider, traffic_percentage)
            
            # Monitor phase for initial period
            monitor_duration = min(60, phase_duration // 3)  # Monitor for up to 60s or 1/3 of phase
            
            success_count = 0
            failure_count = 0
            
            # Simulate monitoring (in real implementation, this would check actual metrics)
            for _ in range(monitor_duration):
                await asyncio.sleep(1)
                
                # Get current health
                health_metrics = await self._get_current_health_metrics(plan.provider)
                if health_metrics.get("success_rate", 0) > success_threshold:
                    success_count += 1
                else:
                    failure_count += 1
                
                # Early failure detection
                if failure_count > failure_tolerance:
                    logger.warning(f"Recovery {plan.recovery_id} exceeded failure tolerance in phase {phase_index}")
                    return False
            
            # Check overall phase success
            overall_success_rate = success_count / max(success_count + failure_count, 1)
            return overall_success_rate >= success_threshold
            
        except Exception as e:
            logger.error(f"Phase execution failed for {plan.recovery_id} phase {phase_index}: {e}")
            return False
    
    async def _wait_for_phase_completion(self, plan: RecoveryPlan, phase_index: int, duration: int):
        """Wait for phase completion with monitoring"""
        
        start_time = time.time()
        while time.time() - start_time < duration:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            # Check if recovery was aborted
            if plan.recovery_id not in self.active_recoveries:
                raise asyncio.CancelledError("Recovery was aborted")
            
            # Early success detection
            health_metrics = await self._get_current_health_metrics(plan.provider)
            if health_metrics.get("health_score", 0) > 0.9:
                logger.info(f"Recovery {plan.recovery_id} phase {phase_index} showing excellent health, considering early progression")
                # Could implement early progression logic here
    
    async def _validate_phase_success(self, plan: RecoveryPlan, phase_index: int, threshold: float) -> bool:
        """Validate that phase was successful"""
        
        try:
            health_metrics = await self._get_current_health_metrics(plan.provider)
            success_rate = health_metrics.get("success_rate", 0)
            health_score = health_metrics.get("health_score", 0)
            
            # Phase is successful if both success rate and health score meet thresholds
            return success_rate >= threshold and health_score >= 0.7
            
        except Exception as e:
            logger.error(f"Phase validation failed for {plan.recovery_id} phase {phase_index}: {e}")
            return False
    
    async def _complete_recovery(self, plan: RecoveryPlan):
        """Complete successful recovery"""
        
        try:
            # Apply 100% traffic
            await self._apply_traffic_percentage(plan.provider, 100.0)
            
            # Update statistics
            self.stats["successful_recoveries"] += 1
            self.stats["current_active_recoveries"] -= 1
            
            # Calculate recovery time
            recovery_time = (datetime.utcnow() - plan.created_at).total_seconds()
            self._update_average_recovery_time(recovery_time)
            
            # Record in history
            await self._record_recovery_history(plan, "completed", f"Successful recovery in {recovery_time:.1f}s")
            
            # Clean up
            if plan.recovery_id in self.recovery_tasks:
                del self.recovery_tasks[plan.recovery_id]
            del self.active_recoveries[plan.recovery_id]
            
            logger.info(f"Recovery {plan.recovery_id} completed successfully for {plan.provider}")
            
        except Exception as e:
            logger.error(f"Failed to complete recovery {plan.recovery_id}: {e}")
    
    async def _handle_recovery_failure(self, plan: RecoveryPlan, failed_phase: int, reason: str = "phase_failure"):
        """Handle recovery failure"""
        
        try:
            # Set traffic back to 0%
            await self._apply_traffic_percentage(plan.provider, 0.0)
            
            # Update statistics
            self.stats["failed_recoveries"] += 1
            self.stats["current_active_recoveries"] -= 1
            
            # Record in history
            await self._record_recovery_history(
                plan, "failed", 
                f"Failed at phase {failed_phase}: {reason}"
            )
            
            # Clean up
            if plan.recovery_id in self.recovery_tasks:
                del self.recovery_tasks[plan.recovery_id]
            del self.active_recoveries[plan.recovery_id]
            
            logger.error(f"Recovery {plan.recovery_id} failed for {plan.provider} at phase {failed_phase}: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to handle recovery failure for {plan.recovery_id}: {e}")
    
    async def _apply_traffic_percentage(self, provider: str, percentage: float):
        """Apply traffic percentage to provider (integrate with load balancer)"""
        
        # This would integrate with actual load balancer/traffic routing
        logger.info(f"Applied {percentage}% traffic to {provider}")
        
        # Simulate latency
        await asyncio.sleep(0.1)
    
    async def _get_current_health_metrics(self, provider: str) -> Dict[str, float]:
        """Get current health metrics for provider"""
        
        try:
            # This would get actual metrics from monitoring system
            health_score_obj = await self.health_scorer.calculate_health_score(
                provider, {"total_requests": 0}
            )
            
            return {
                "success_rate": health_score_obj.metrics.success_rate,
                "health_score": health_score_obj.overall_score,
                "response_time": health_score_obj.metrics.average_response_time,
                "availability": health_score_obj.metrics.availability
            }
            
        except Exception as e:
            logger.error(f"Failed to get health metrics for {provider}: {e}")
            return {"success_rate": 0.5, "health_score": 0.5}
    
    async def _calculate_italian_market_factor(self) -> float:
        """Calculate adjustment factor based on Italian market conditions"""
        
        now = datetime.utcnow()
        italian_hour = (now.hour + 1) % 24  # Simplified UTC+1
        
        # Base factor
        factor = 1.0
        
        # Peak hours adjustment (slower recovery)
        if 9 <= italian_hour <= 18:
            factor *= self.italian_adjustments["peak_hours_factor"]
        else:
            factor *= self.italian_adjustments["off_hours_factor"]
        
        # Tax deadline periods (much slower recovery)
        if now.month in [7, 11]:
            factor *= self.italian_adjustments["tax_deadline_factor"]
        
        # August vacation (faster recovery allowed)
        elif now.month == 8:
            factor *= self.italian_adjustments["vacation_factor"]
        
        return factor
    
    def _get_active_recovery_for_provider(self, provider: str) -> Optional[RecoveryPlan]:
        """Get active recovery plan for a provider"""
        
        for plan in self.active_recoveries.values():
            if plan.provider == provider:
                return plan
        return None
    
    def _initialize_strategies(self) -> Dict[RecoveryStrategy, Dict[str, List]]:
        """Initialize recovery strategy configurations"""
        
        return {
            RecoveryStrategy.CONSERVATIVE: {
                "traffic_percentages": [5.0, 10.0, 25.0, 50.0, 75.0, 100.0],
                "phase_durations": [300, 300, 600, 600, 600, 300],  # 5,5,10,10,10,5 minutes
                "success_thresholds": [0.95, 0.93, 0.90, 0.88, 0.85, 0.85],
                "failure_tolerance": [1, 2, 3, 5, 8, 10]
            },
            RecoveryStrategy.MODERATE: {
                "traffic_percentages": [10.0, 25.0, 50.0, 100.0],
                "phase_durations": [180, 300, 300, 180],  # 3,5,5,3 minutes
                "success_thresholds": [0.90, 0.88, 0.85, 0.85],
                "failure_tolerance": [2, 5, 8, 10]
            },
            RecoveryStrategy.AGGRESSIVE: {
                "traffic_percentages": [25.0, 75.0, 100.0],
                "phase_durations": [120, 180, 120],  # 2,3,2 minutes
                "success_thresholds": [0.85, 0.83, 0.80],
                "failure_tolerance": [5, 10, 15]
            },
            RecoveryStrategy.ITALIAN_MARKET: {
                "traffic_percentages": [5.0, 15.0, 30.0, 60.0, 85.0, 100.0],
                "phase_durations": [240, 360, 480, 480, 360, 240],  # Italian-optimized timing
                "success_thresholds": [0.92, 0.90, 0.88, 0.85, 0.83, 0.80],
                "failure_tolerance": [1, 3, 5, 8, 12, 15]
            }
        }
    
    async def _record_recovery_history(self, plan: RecoveryPlan, outcome: str, details: str):
        """Record recovery attempt in history"""
        
        if plan.provider not in self.recovery_history:
            self.recovery_history[plan.provider] = []
        
        history_record = {
            "recovery_id": plan.recovery_id,
            "timestamp": datetime.utcnow(),
            "strategy": plan.strategy.value,
            "outcome": outcome,
            "details": details,
            "duration_seconds": (datetime.utcnow() - plan.created_at).total_seconds(),
            "phases_completed": plan.current_phase
        }
        
        self.recovery_history[plan.provider].append(history_record)
        
        # Keep only last 20 recovery attempts per provider
        if len(self.recovery_history[plan.provider]) > 20:
            self.recovery_history[plan.provider] = self.recovery_history[plan.provider][-20:]
    
    def _update_average_recovery_time(self, recovery_time: float):
        """Update average recovery time statistic"""
        
        if self.stats["successful_recoveries"] == 1:
            self.stats["average_recovery_time"] = recovery_time
        else:
            # Calculate running average
            total_recoveries = self.stats["successful_recoveries"]
            current_avg = self.stats["average_recovery_time"]
            self.stats["average_recovery_time"] = ((current_avg * (total_recoveries - 1)) + recovery_time) / total_recoveries
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get recovery coordinator statistics"""
        
        success_rate = 0.0
        if self.stats["total_recoveries"] > 0:
            success_rate = self.stats["successful_recoveries"] / self.stats["total_recoveries"]
        
        return {
            "recovery_stats": self.stats,
            "success_rate": success_rate,
            "active_recoveries": list(self.active_recoveries.keys()),
            "tracked_providers": len(self.recovery_history),
            "italian_adjustments": self.italian_adjustments,
            "available_strategies": [strategy.value for strategy in RecoveryStrategy]
        }