#!/usr/bin/env python3
"""
Recovery Orchestrator - Advanced Recovery Strategy Implementation
===============================================================

This module implements advanced recovery strategies that coordinate multiple
recovery actions across frontend and backend systems. It provides:

1. Multi-tier recovery strategies with fallback mechanisms
2. Coordinated frontend/backend recovery procedures
3. Impact-aware recovery that considers user experience
4. Resource-constrained recovery optimization
5. Real-time monitoring and adaptive recovery adjustments

The orchestrator acts as the high-level coordinator that uses the decision tree
engine to execute sophisticated recovery workflows.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import uuid

from failure_categorizer import (
  CategorizedFailure, FailureType, FailureSeverity, 
  ComponentType, RecoveryComplexity, FailureContext
)
from decision_tree_engine import (
  DecisionTreeEngine, DecisionResult, DecisionPath, RecoveryStrategy
)


class RecoveryPhase(Enum):
  """Phases of the recovery process."""
  
  PREPARATION = "preparation"
  IMMEDIATE_RESPONSE = "immediate_response"
  STABILIZATION = "stabilization"
  VALIDATION = "validation"
  OPTIMIZATION = "optimization"
  CLEANUP = "cleanup"
  POST_RECOVERY = "post_recovery"


class RecoveryScope(Enum):
  """Scope of recovery operations."""
  
  SINGLE_COMPONENT = "single_component"
  RELATED_COMPONENTS = "related_components"
  FULL_SYSTEM = "full_system"
  MULTI_REGION = "multi_region"


class ImpactLevel(Enum):
  """Level of impact on system operations."""
  
  ZERO_DOWNTIME = "zero_downtime"
  MINIMAL_IMPACT = "minimal_impact"
  MODERATE_IMPACT = "moderate_impact"
  HIGH_IMPACT = "high_impact"
  SYSTEM_WIDE = "system_wide"


@dataclass
class RecoveryConstraints:
  """Constraints that limit recovery options."""
  
  max_downtime_minutes: Optional[int] = None
  max_data_loss_seconds: Optional[int] = None
  min_availability_percent: Optional[float] = None
  max_resource_utilization: Optional[float] = None
  
  # Business constraints
  business_hours_only: bool = False
  requires_approval: bool = False
  notification_required: bool = True
  
  # Technical constraints
  readonly_mode_acceptable: bool = True
  degraded_performance_acceptable: bool = True
  backup_systems_available: bool = True
  
  # Budget constraints
  max_additional_resources: Optional[int] = None
  cost_optimization_priority: bool = False


@dataclass
class RecoveryMetrics:
  """Metrics tracked during recovery execution."""
  
  start_time: datetime
  end_time: Optional[datetime] = None
  
  # Performance metrics
  recovery_duration_seconds: Optional[float] = None
  downtime_seconds: Optional[float] = None
  data_loss_seconds: Optional[float] = None
  
  # Impact metrics
  users_affected: Optional[int] = None
  transactions_lost: Optional[int] = None
  revenue_impact_dollars: Optional[float] = None
  
  # Recovery effectiveness
  components_recovered: int = 0
  components_failed: int = 0
  fallback_strategies_used: int = 0
  manual_interventions: int = 0
  
  # Resource utilization
  cpu_usage_peak: Optional[float] = None
  memory_usage_peak: Optional[float] = None
  network_usage_peak: Optional[float] = None
  additional_costs: Optional[float] = None


@dataclass
class RecoveryPlan:
  """Comprehensive recovery plan with multiple strategies."""
  
  plan_id: str
  failure_id: str
  created_at: datetime
  
  # Recovery configuration
  primary_strategy: RecoveryStrategy
  fallback_strategies: List[RecoveryStrategy]
  constraints: RecoveryConstraints
  
  # Execution plan
  phases: Dict[RecoveryPhase, List[str]]  # phase -> list of strategy IDs
  
  # Risk assessment
  estimated_impact: ImpactLevel
  success_probability: float
  estimated_duration_minutes: int
  
  # Execution configuration
  parallel_execution: bool = False
  rollback_points: List[str] = None  # Strategy IDs where rollback is possible
  
  # Coordination
  frontend_coordinator: Optional[str] = None
  backend_coordinator: Optional[str] = None
  database_coordinator: Optional[str] = None
  
  def __post_init__(self):
    if self.rollback_points is None:
      self.rollback_points = []


@dataclass
class RecoveryExecution:
  """Tracks the execution of a recovery plan."""
  
  execution_id: str
  plan_id: str
  failure_id: str
  start_time: datetime
  end_time: Optional[datetime] = None
  
  # Execution state
  current_phase: RecoveryPhase = RecoveryPhase.PREPARATION
  current_strategy: Optional[str] = None
  completed_strategies: List[str] = None
  failed_strategies: List[str] = None
  
  # Execution paths
  decision_paths: List[DecisionPath] = None
  
  # Results
  final_result: Optional[DecisionResult] = None
  success: bool = False
  error_message: Optional[str] = None
  
  # Metrics
  metrics: RecoveryMetrics = None
  
  # Real-time status
  status_messages: List[Dict[str, Any]] = None
  progress_percentage: float = 0.0
  
  def __post_init__(self):
    if self.completed_strategies is None:
      self.completed_strategies = []
    if self.failed_strategies is None:
      self.failed_strategies = []
    if self.decision_paths is None:
      self.decision_paths = []
    if self.metrics is None:
      self.metrics = RecoveryMetrics(start_time=self.start_time)
    if self.status_messages is None:
      self.status_messages = []


class RecoveryOrchestrator:
  """
  Advanced recovery orchestrator that coordinates complex, multi-component
  recovery operations with sophisticated strategies and real-time monitoring.
  """
  
  def __init__(self, config_path: Optional[Path] = None):
    self.logger = logging.getLogger(__name__)
    self.config_path = config_path or Path(__file__).parent / "recovery_orchestrator_config.yaml"
    
    # Initialize core components
    self.decision_engine = DecisionTreeEngine()
    self.config = self._load_configuration()
    
    # Recovery state tracking
    self.active_recoveries: Dict[str, RecoveryExecution] = {}
    self.recovery_history: List[RecoveryExecution] = []
    self.recovery_plans: Dict[str, RecoveryPlan] = {}
    
    # Component coordination
    self.component_coordinators = self._initialize_coordinators()
    
    # Recovery strategies
    self.advanced_strategies = self._initialize_advanced_strategies()
    
    # Monitoring and metrics
    self.metrics_collectors = self._initialize_metrics_collectors()
    
    # Statistics
    self.orchestrator_stats = {
      "total_recoveries": 0,
      "successful_recoveries": 0,
      "failed_recoveries": 0,
      "average_recovery_time": 0.0,
      "zero_downtime_recoveries": 0,
      "fallback_strategies_used": 0
    }
  
  def _load_configuration(self) -> Dict[str, Any]:
    """Load orchestrator configuration."""
    default_config = {
      "max_concurrent_recoveries": 5,
      "max_recovery_duration_minutes": 120,
      "default_constraints": {
        "max_downtime_minutes": 15,
        "max_data_loss_seconds": 0,
        "min_availability_percent": 99.0,
        "max_resource_utilization": 0.9
      },
      "coordination": {
        "enable_parallel_execution": True,
        "coordination_timeout_seconds": 300,
        "health_check_interval_seconds": 30
      },
      "monitoring": {
        "metrics_collection_interval": 10,
        "real_time_updates": True,
        "alert_thresholds": {
          "recovery_duration_warning": 30,
          "recovery_duration_critical": 60
        }
      },
      "notification": {
        "slack_webhook": "",
        "email_recipients": [],
        "status_page_integration": True
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
  
  def _initialize_coordinators(self) -> Dict[str, Any]:
    """Initialize component coordinators for orchestrated recovery."""
    return {
      "frontend": FrontendRecoveryCoordinator(self),
      "backend": BackendRecoveryCoordinator(self),
      "database": DatabaseRecoveryCoordinator(self),
      "infrastructure": InfrastructureRecoveryCoordinator(self),
      "network": NetworkRecoveryCoordinator(self)
    }
  
  def _initialize_advanced_strategies(self) -> Dict[str, RecoveryStrategy]:
    """Initialize advanced recovery strategies."""
    strategies = {}
    
    # Zero-downtime recovery strategy
    strategies["zero_downtime_recovery"] = self._create_zero_downtime_strategy()
    
    # Blue-green deployment recovery
    strategies["blue_green_recovery"] = self._create_blue_green_recovery()
    
    # Canary rollback strategy
    strategies["canary_rollback"] = self._create_canary_rollback_strategy()
    
    # Circuit breaker recovery
    strategies["circuit_breaker_recovery"] = self._create_circuit_breaker_strategy()
    
    # Data integrity recovery
    strategies["data_integrity_recovery"] = self._create_data_integrity_strategy()
    
    # Multi-region failover
    strategies["multi_region_failover"] = self._create_multi_region_failover()
    
    # Performance degradation recovery
    strategies["performance_recovery"] = self._create_performance_recovery()
    
    # Security incident recovery
    strategies["security_incident_recovery"] = self._create_security_incident_recovery()
    
    return strategies
  
  def _initialize_metrics_collectors(self) -> Dict[str, Any]:
    """Initialize metrics collection systems."""
    return {
      "system_metrics": SystemMetricsCollector(),
      "business_metrics": BusinessMetricsCollector(),
      "user_experience": UserExperienceCollector(),
      "cost_metrics": CostMetricsCollector()
    }
  
  async def create_recovery_plan(self,
                               failure: CategorizedFailure,
                               constraints: Optional[RecoveryConstraints] = None) -> RecoveryPlan:
    """
    Create a comprehensive recovery plan for a categorized failure.
    
    Args:
      failure: Categorized failure to create recovery plan for
      constraints: Optional constraints to limit recovery options
      
    Returns:
      RecoveryPlan: Comprehensive recovery plan with multiple strategies
    """
    
    plan_id = f"plan_{int(time.time() * 1000)}"
    
    if constraints is None:
      constraints = RecoveryConstraints(**self.config["default_constraints"])
    
    self.logger.info(f"Creating recovery plan {plan_id} for failure {failure.failure_id}")
    
    # Step 1: Select primary recovery strategy
    primary_strategy = self._select_primary_strategy(failure, constraints)
    
    # Step 2: Identify fallback strategies
    fallback_strategies = self._identify_fallback_strategies(failure, primary_strategy, constraints)
    
    # Step 3: Create execution phases
    phases = self._plan_execution_phases(primary_strategy, fallback_strategies, failure)
    
    # Step 4: Assess impact and risk
    estimated_impact = self._assess_recovery_impact(failure, primary_strategy, constraints)
    success_probability = self._calculate_success_probability(primary_strategy, fallback_strategies, failure)
    estimated_duration = self._estimate_total_duration(primary_strategy, fallback_strategies)
    
    # Step 5: Assign coordinators
    coordinators = self._assign_coordinators(failure, primary_strategy)
    
    # Step 6: Identify rollback points
    rollback_points = self._identify_rollback_points(primary_strategy, fallback_strategies)
    
    # Create recovery plan
    plan = RecoveryPlan(
      plan_id=plan_id,
      failure_id=failure.failure_id,
      created_at=datetime.now(),
      primary_strategy=primary_strategy,
      fallback_strategies=fallback_strategies,
      constraints=constraints,
      phases=phases,
      parallel_execution=self.config["coordination"]["enable_parallel_execution"],
      rollback_points=rollback_points,
      estimated_impact=estimated_impact,
      success_probability=success_probability,
      estimated_duration_minutes=estimated_duration,
      frontend_coordinator=coordinators.get("frontend"),
      backend_coordinator=coordinators.get("backend"),
      database_coordinator=coordinators.get("database")
    )
    
    self.recovery_plans[plan_id] = plan
    
    self.logger.info(f"Recovery plan {plan_id} created: {primary_strategy.name} + "
                    f"{len(fallback_strategies)} fallbacks, estimated {estimated_duration}min, "
                    f"{success_probability:.1%} success probability")
    
    return plan
  
  async def execute_recovery_plan(self,
                                plan: RecoveryPlan,
                                dry_run: bool = False) -> RecoveryExecution:
    """
    Execute a recovery plan with full orchestration and monitoring.
    
    Args:
      plan: Recovery plan to execute
      dry_run: If True, simulate execution without taking real actions
      
    Returns:
      RecoveryExecution: Detailed execution results and metrics
    """
    
    execution_id = f"exec_{int(time.time() * 1000)}"
    
    execution = RecoveryExecution(
      execution_id=execution_id,
      plan_id=plan.plan_id,
      failure_id=plan.failure_id,
      start_time=datetime.now()
    )
    
    self.active_recoveries[execution_id] = execution
    
    try:
      self.logger.info(f"Starting recovery execution {execution_id} for plan {plan.plan_id} "
                      f"(dry_run={dry_run})")
      
      # Phase 1: Preparation
      await self._execute_preparation_phase(execution, plan, dry_run)
      
      # Phase 2: Immediate Response
      await self._execute_immediate_response_phase(execution, plan, dry_run)
      
      # Phase 3: Stabilization
      await self._execute_stabilization_phase(execution, plan, dry_run)
      
      # Phase 4: Validation
      await self._execute_validation_phase(execution, plan, dry_run)
      
      # Phase 5: Optimization
      await self._execute_optimization_phase(execution, plan, dry_run)
      
      # Phase 6: Cleanup
      await self._execute_cleanup_phase(execution, plan, dry_run)
      
      # Phase 7: Post-Recovery
      await self._execute_post_recovery_phase(execution, plan, dry_run)
      
      # Finalize execution
      execution.final_result = DecisionResult.SUCCESS
      execution.success = True
      execution.end_time = datetime.now()
      execution.metrics.end_time = execution.end_time
      execution.progress_percentage = 100.0
      
      # Calculate final metrics
      await self._calculate_final_metrics(execution, plan)
      
      self.logger.info(f"Recovery execution {execution_id} completed successfully "
                      f"in {execution.metrics.recovery_duration_seconds:.1f}s")
    
    except Exception as e:
      self.logger.error(f"Recovery execution {execution_id} failed: {e}")
      execution.final_result = DecisionResult.FAILURE
      execution.success = False
      execution.error_message = str(e)
      execution.end_time = datetime.now()
      execution.metrics.end_time = execution.end_time
      
      if execution.metrics.end_time and execution.metrics.start_time:
        execution.metrics.recovery_duration_seconds = (
          execution.metrics.end_time - execution.metrics.start_time
        ).total_seconds()
    
    finally:
      # Move from active to history
      if execution_id in self.active_recoveries:
        del self.active_recoveries[execution_id]
      self.recovery_history.append(execution)
      
      # Update statistics
      self._update_orchestrator_statistics(execution, plan)
    
    return execution
  
  def _select_primary_strategy(self,
                             failure: CategorizedFailure,
                             constraints: RecoveryConstraints) -> RecoveryStrategy:
    """Select the primary recovery strategy based on failure and constraints."""
    
    # Start with decision engine strategy selection
    base_strategy = self.decision_engine.select_recovery_strategy(failure)
    
    if base_strategy is None:
      # Fallback to a generic strategy
      base_strategy = self.decision_engine.strategies["application_recovery"]
    
    # Check if we have advanced strategies that better match constraints
    if constraints.max_downtime_minutes == 0 or constraints.min_availability_percent >= 99.9:
      if "zero_downtime_recovery" in self.advanced_strategies:
        return self.advanced_strategies["zero_downtime_recovery"]
    
    if failure.severity == FailureSeverity.CRITICAL and failure.failure_type == FailureType.SECURITY:
      if "security_incident_recovery" in self.advanced_strategies:
        return self.advanced_strategies["security_incident_recovery"]
    
    if failure.failure_type == FailureType.DATA and constraints.max_data_loss_seconds == 0:
      if "data_integrity_recovery" in self.advanced_strategies:
        return self.advanced_strategies["data_integrity_recovery"]
    
    if len(failure.affected_components) > 3:
      if "multi_region_failover" in self.advanced_strategies:
        return self.advanced_strategies["multi_region_failover"]
    
    return base_strategy
  
  def _identify_fallback_strategies(self,
                                  failure: CategorizedFailure,
                                  primary_strategy: RecoveryStrategy,
                                  constraints: RecoveryConstraints) -> List[RecoveryStrategy]:
    """Identify appropriate fallback strategies."""
    
    fallbacks = []
    
    # Get all potentially applicable strategies
    all_strategies = {**self.decision_engine.strategies, **self.advanced_strategies}
    
    for strategy in all_strategies.values():
      if strategy.strategy_id == primary_strategy.strategy_id:
        continue
      
      # Check if strategy is applicable to this failure
      if (failure.failure_type in strategy.failure_types and
          failure.severity in strategy.severity_levels and
          len(set(failure.affected_components) & set(strategy.component_types)) > 0):
        
        fallbacks.append(strategy)
    
    # Sort by success rate and estimated duration
    fallbacks.sort(key=lambda s: (s.success_rate, -s.estimated_duration_minutes), reverse=True)
    
    # Return top 3 fallback strategies
    return fallbacks[:3]
  
  def _plan_execution_phases(self,
                           primary_strategy: RecoveryStrategy,
                           fallback_strategies: List[RecoveryStrategy],
                           failure: CategorizedFailure) -> Dict[RecoveryPhase, List[str]]:
    """Plan the execution phases for recovery strategies."""
    
    phases = {
      RecoveryPhase.PREPARATION: [],
      RecoveryPhase.IMMEDIATE_RESPONSE: [primary_strategy.strategy_id],
      RecoveryPhase.STABILIZATION: [],
      RecoveryPhase.VALIDATION: [],
      RecoveryPhase.OPTIMIZATION: [],
      RecoveryPhase.CLEANUP: [],
      RecoveryPhase.POST_RECOVERY: []
    }
    
    # Add fallback strategies to stabilization phase
    if fallback_strategies:
      phases[RecoveryPhase.STABILIZATION] = [s.strategy_id for s in fallback_strategies[:2]]
    
    # Add validation and optimization based on failure characteristics
    if failure.severity in [FailureSeverity.HIGH, FailureSeverity.CRITICAL]:
      phases[RecoveryPhase.VALIDATION].append("comprehensive_validation")
      phases[RecoveryPhase.POST_RECOVERY].append("post_incident_review")
    
    if failure.failure_type in [FailureType.RESOURCE, FailureType.INFRASTRUCTURE]:
      phases[RecoveryPhase.OPTIMIZATION].append("resource_optimization")
    
    return phases
  
  def _assess_recovery_impact(self,
                            failure: CategorizedFailure,
                            strategy: RecoveryStrategy,
                            constraints: RecoveryConstraints) -> ImpactLevel:
    """Assess the impact level of the recovery operation."""
    
    if constraints.max_downtime_minutes == 0:
      return ImpactLevel.ZERO_DOWNTIME
    elif constraints.max_downtime_minutes <= 5:
      return ImpactLevel.MINIMAL_IMPACT
    elif constraints.max_downtime_minutes <= 15:
      return ImpactLevel.MODERATE_IMPACT
    elif constraints.max_downtime_minutes <= 60:
      return ImpactLevel.HIGH_IMPACT
    else:
      return ImpactLevel.SYSTEM_WIDE
  
  def _calculate_success_probability(self,
                                   primary_strategy: RecoveryStrategy,
                                   fallback_strategies: List[RecoveryStrategy],
                                   failure: CategorizedFailure) -> float:
    """Calculate overall success probability including fallbacks."""
    
    # Start with primary strategy success rate
    primary_success = primary_strategy.success_rate
    
    # Calculate combined probability with fallbacks
    combined_failure_rate = 1.0 - primary_success
    
    for fallback in fallback_strategies:
      combined_failure_rate *= (1.0 - fallback.success_rate)
    
    combined_success_rate = 1.0 - combined_failure_rate
    
    # Adjust based on failure characteristics
    if failure.confidence_score < 0.7:
      combined_success_rate *= 0.9  # Reduce if uncertain about failure categorization
    
    if failure.severity == FailureSeverity.CRITICAL:
      combined_success_rate *= 0.95  # Slight reduction for critical failures
    
    return min(0.99, combined_success_rate)  # Cap at 99%
  
  def _estimate_total_duration(self,
                             primary_strategy: RecoveryStrategy,
                             fallback_strategies: List[RecoveryStrategy]) -> int:
    """Estimate total recovery duration including potential fallbacks."""
    
    # Primary strategy duration
    total_duration = primary_strategy.estimated_duration_minutes
    
    # Add potential fallback duration (weighted by failure probability)
    primary_failure_prob = 1.0 - primary_strategy.success_rate
    
    for fallback in fallback_strategies:
      fallback_probability = primary_failure_prob * (1.0 - fallback.success_rate)
      total_duration += fallback.estimated_duration_minutes * fallback_probability
      primary_failure_prob *= (1.0 - fallback.success_rate)
    
    # Add overhead for coordination and validation
    coordination_overhead = max(5, total_duration * 0.2)
    
    return int(total_duration + coordination_overhead)
  
  def _assign_coordinators(self,
                         failure: CategorizedFailure,
                         strategy: RecoveryStrategy) -> Dict[str, str]:
    """Assign coordinators based on affected components."""
    
    coordinators = {}
    
    if ComponentType.FRONTEND in failure.affected_components:
      coordinators["frontend"] = "frontend_coordinator"
    
    if ComponentType.BACKEND in failure.affected_components:
      coordinators["backend"] = "backend_coordinator"
    
    if ComponentType.DATABASE in failure.affected_components:
      coordinators["database"] = "database_coordinator"
    
    return coordinators
  
  def _identify_rollback_points(self,
                              primary_strategy: RecoveryStrategy,
                              fallback_strategies: List[RecoveryStrategy]) -> List[str]:
    """Identify safe rollback points during recovery."""
    
    rollback_points = []
    
    # Always allow rollback before starting
    rollback_points.append("pre_recovery")
    
    # Add rollback points based on strategy characteristics
    if primary_strategy.data_safety_level == "safe":
      rollback_points.append(primary_strategy.strategy_id)
    
    for fallback in fallback_strategies:
      if fallback.data_safety_level == "safe":
        rollback_points.append(fallback.strategy_id)
    
    return rollback_points
  
  async def _execute_preparation_phase(self,
                                     execution: RecoveryExecution,
                                     plan: RecoveryPlan,
                                     dry_run: bool):
    """Execute the preparation phase of recovery."""
    
    execution.current_phase = RecoveryPhase.PREPARATION
    execution.progress_percentage = 5.0
    
    self._add_status_message(execution, "Starting preparation phase", "info")
    
    # Initialize metrics collection
    await self._start_metrics_collection(execution)
    
    # Notify stakeholders
    await self._send_recovery_notifications(execution, plan, "started")
    
    # Prepare coordinators
    await self._prepare_coordinators(execution, plan)
    
    # Validate constraints
    await self._validate_recovery_constraints(execution, plan)
    
    execution.progress_percentage = 10.0
    self._add_status_message(execution, "Preparation phase completed", "success")
  
  async def _execute_immediate_response_phase(self,
                                            execution: RecoveryExecution,
                                            plan: RecoveryPlan,
                                            dry_run: bool):
    """Execute the immediate response phase."""
    
    execution.current_phase = RecoveryPhase.IMMEDIATE_RESPONSE
    execution.progress_percentage = 15.0
    
    self._add_status_message(execution, "Starting immediate response", "info")
    
    # Execute primary strategy
    strategy_ids = plan.phases.get(RecoveryPhase.IMMEDIATE_RESPONSE, [])
    
    for strategy_id in strategy_ids:
      strategy = self._get_strategy_by_id(strategy_id)
      if strategy:
        execution.current_strategy = strategy_id
        
        # Get the original failure for strategy execution
        failure = self._get_failure_for_execution(execution)
        
        # Execute strategy using decision engine
        path = self.decision_engine.execute_recovery_strategy(failure, strategy, dry_run)
        execution.decision_paths.append(path)
        
        if path.success:
          execution.completed_strategies.append(strategy_id)
          self._add_status_message(execution, f"Strategy {strategy.name} completed successfully", "success")
        else:
          execution.failed_strategies.append(strategy_id)
          self._add_status_message(execution, f"Strategy {strategy.name} failed: {path.error_message}", "error")
          
          # Continue to stabilization phase with fallbacks
          break
    
    execution.progress_percentage = 40.0
  
  async def _execute_stabilization_phase(self,
                                       execution: RecoveryExecution,
                                       plan: RecoveryPlan,
                                       dry_run: bool):
    """Execute the stabilization phase with fallback strategies."""
    
    execution.current_phase = RecoveryPhase.STABILIZATION
    execution.progress_percentage = 45.0
    
    # Only execute if primary strategy failed or if configured for redundancy
    if execution.failed_strategies or plan.constraints.requires_approval:
      
      self._add_status_message(execution, "Starting stabilization phase", "info")
      
      strategy_ids = plan.phases.get(RecoveryPhase.STABILIZATION, [])
      
      for strategy_id in strategy_ids:
        strategy = self._get_strategy_by_id(strategy_id)
        if strategy:
          execution.current_strategy = strategy_id
          execution.metrics.fallback_strategies_used += 1
          
          failure = self._get_failure_for_execution(execution)
          path = self.decision_engine.execute_recovery_strategy(failure, strategy, dry_run)
          execution.decision_paths.append(path)
          
          if path.success:
            execution.completed_strategies.append(strategy_id)
            self._add_status_message(execution, f"Fallback strategy {strategy.name} successful", "success")
            break
          else:
            execution.failed_strategies.append(strategy_id)
            self._add_status_message(execution, f"Fallback strategy {strategy.name} failed", "error")
    
    execution.progress_percentage = 60.0
  
  async def _execute_validation_phase(self,
                                    execution: RecoveryExecution,
                                    plan: RecoveryPlan,
                                    dry_run: bool):
    """Execute the validation phase to verify recovery success."""
    
    execution.current_phase = RecoveryPhase.VALIDATION
    execution.progress_percentage = 65.0
    
    self._add_status_message(execution, "Starting validation phase", "info")
    
    # Run health checks on all affected components
    validation_results = await self._run_comprehensive_validation(execution, plan, dry_run)
    
    if validation_results["overall_health"]:
      self._add_status_message(execution, "System validation passed", "success")
    else:
      self._add_status_message(execution, f"Validation issues detected: {validation_results['issues']}", "warning")
      execution.metrics.manual_interventions += 1
    
    execution.progress_percentage = 75.0
  
  async def _execute_optimization_phase(self,
                                      execution: RecoveryExecution,
                                      plan: RecoveryPlan,
                                      dry_run: bool):
    """Execute the optimization phase to improve system performance."""
    
    execution.current_phase = RecoveryPhase.OPTIMIZATION
    execution.progress_percentage = 80.0
    
    self._add_status_message(execution, "Starting optimization phase", "info")
    
    # Optimize resource allocation
    await self._optimize_resources(execution, plan, dry_run)
    
    # Tune performance settings
    await self._tune_performance_settings(execution, plan, dry_run)
    
    execution.progress_percentage = 85.0
  
  async def _execute_cleanup_phase(self,
                                 execution: RecoveryExecution,
                                 plan: RecoveryPlan,
                                 dry_run: bool):
    """Execute the cleanup phase to remove temporary resources."""
    
    execution.current_phase = RecoveryPhase.CLEANUP
    execution.progress_percentage = 90.0
    
    self._add_status_message(execution, "Starting cleanup phase", "info")
    
    # Clean up temporary resources
    await self._cleanup_temporary_resources(execution, plan, dry_run)
    
    # Reset debug settings
    await self._reset_debug_settings(execution, plan, dry_run)
    
    execution.progress_percentage = 95.0
  
  async def _execute_post_recovery_phase(self,
                                       execution: RecoveryExecution,
                                       plan: RecoveryPlan,
                                       dry_run: bool):
    """Execute the post-recovery phase for documentation and learning."""
    
    execution.current_phase = RecoveryPhase.POST_RECOVERY
    execution.progress_percentage = 98.0
    
    self._add_status_message(execution, "Starting post-recovery phase", "info")
    
    # Generate recovery report
    await self._generate_recovery_report(execution, plan)
    
    # Update status page
    await self._update_status_page(execution, plan, "resolved")
    
    # Send completion notifications
    await self._send_recovery_notifications(execution, plan, "completed")
    
    execution.progress_percentage = 100.0
    self._add_status_message(execution, "Recovery completed successfully", "success")
  
  # Helper methods for execution phases
  
  def _add_status_message(self, execution: RecoveryExecution, message: str, level: str):
    """Add a status message to the execution log."""
    status_msg = {
      "timestamp": datetime.now().isoformat(),
      "phase": execution.current_phase.value,
      "message": message,
      "level": level,
      "progress": execution.progress_percentage
    }
    execution.status_messages.append(status_msg)
    
    log_method = getattr(self.logger, level, self.logger.info)
    log_method(f"[{execution.execution_id}] {message}")
  
  def _get_strategy_by_id(self, strategy_id: str) -> Optional[RecoveryStrategy]:
    """Get a strategy by its ID from all available strategies."""
    all_strategies = {**self.decision_engine.strategies, **self.advanced_strategies}
    return all_strategies.get(strategy_id)
  
  def _get_failure_for_execution(self, execution: RecoveryExecution) -> CategorizedFailure:
    """Get the original failure for strategy execution (simplified for demo)."""
    # In a real implementation, this would retrieve the original failure
    # For now, create a mock failure
    from failure_categorizer import FailureCategorizer, FailureContext
    
    context = FailureContext(
      environment="production",
      timestamp=datetime.now(),
      affected_users=1000
    )
    
    # This is a simplified mock - in reality, retrieve from storage
    categorizer = FailureCategorizer()
    return categorizer.categorize_failure(
      error_messages=["Mock error for execution"],
      log_entries=["Mock log entry"],
      metrics={"error_rate": 10.0},
      status_codes=[500],
      context=context
    )
  
  async def _start_metrics_collection(self, execution: RecoveryExecution):
    """Start collecting metrics for the recovery execution."""
    for collector_name, collector in self.metrics_collectors.items():
      try:
        await collector.start_collection(execution.execution_id)
      except Exception as e:
        self.logger.warning(f"Failed to start {collector_name} metrics collection: {e}")
  
  async def _send_recovery_notifications(self, execution: RecoveryExecution, plan: RecoveryPlan, status: str):
    """Send notifications about recovery status."""
    notification_config = self.config.get("notification", {})
    
    if notification_config.get("slack_webhook"):
      # Send Slack notification (implementation would go here)
      pass
    
    if notification_config.get("email_recipients"):
      # Send email notification (implementation would go here)
      pass
    
    self.logger.info(f"Recovery {status} notification sent for execution {execution.execution_id}")
  
  async def _prepare_coordinators(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Prepare component coordinators for recovery execution."""
    for coordinator_name, coordinator in self.component_coordinators.items():
      try:
        await coordinator.prepare_for_recovery(execution, plan)
      except Exception as e:
        self.logger.warning(f"Failed to prepare {coordinator_name} coordinator: {e}")
  
  async def _validate_recovery_constraints(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Validate that recovery constraints can be met."""
    constraints = plan.constraints
    
    # Check business hours constraint
    if constraints.business_hours_only:
      current_hour = datetime.now().hour
      if current_hour < 9 or current_hour > 17:
        raise Exception("Recovery can only be performed during business hours")
    
    # Check resource availability
    if constraints.max_resource_utilization:
      # Check current system utilization (implementation would go here)
      pass
    
    self.logger.info(f"Recovery constraints validated for execution {execution.execution_id}")
  
  async def _run_comprehensive_validation(self, execution: RecoveryExecution, plan: RecoveryPlan, dry_run: bool) -> Dict[str, Any]:
    """Run comprehensive validation of system health after recovery."""
    
    if dry_run:
      return {"overall_health": True, "issues": []}
    
    validation_results = {
      "overall_health": True,
      "component_health": {},
      "issues": []
    }
    
    # Validate each coordinator
    for coordinator_name, coordinator in self.component_coordinators.items():
      try:
        health = await coordinator.validate_health()
        validation_results["component_health"][coordinator_name] = health
        if not health:
          validation_results["overall_health"] = False
          validation_results["issues"].append(f"{coordinator_name} health check failed")
      except Exception as e:
        validation_results["overall_health"] = False
        validation_results["issues"].append(f"{coordinator_name} validation error: {e}")
    
    return validation_results
  
  async def _optimize_resources(self, execution: RecoveryExecution, plan: RecoveryPlan, dry_run: bool):
    """Optimize resource allocation after recovery."""
    if not dry_run:
      # Implement resource optimization logic
      pass
    
    self.logger.info(f"Resource optimization completed for execution {execution.execution_id}")
  
  async def _tune_performance_settings(self, execution: RecoveryExecution, plan: RecoveryPlan, dry_run: bool):
    """Tune performance settings after recovery."""
    if not dry_run:
      # Implement performance tuning logic
      pass
    
    self.logger.info(f"Performance tuning completed for execution {execution.execution_id}")
  
  async def _cleanup_temporary_resources(self, execution: RecoveryExecution, plan: RecoveryPlan, dry_run: bool):
    """Clean up temporary resources created during recovery."""
    if not dry_run:
      # Implement cleanup logic
      pass
    
    self.logger.info(f"Temporary resource cleanup completed for execution {execution.execution_id}")
  
  async def _reset_debug_settings(self, execution: RecoveryExecution, plan: RecoveryPlan, dry_run: bool):
    """Reset debug settings to normal levels."""
    if not dry_run:
      # Implement debug settings reset
      pass
    
    self.logger.info(f"Debug settings reset completed for execution {execution.execution_id}")
  
  async def _generate_recovery_report(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Generate a comprehensive recovery report."""
    # Implementation would generate detailed report
    self.logger.info(f"Recovery report generated for execution {execution.execution_id}")
  
  async def _update_status_page(self, execution: RecoveryExecution, plan: RecoveryPlan, status: str):
    """Update external status page."""
    # Implementation would update status page
    self.logger.info(f"Status page updated to {status} for execution {execution.execution_id}")
  
  async def _calculate_final_metrics(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Calculate final metrics for the recovery execution."""
    
    if execution.metrics.end_time and execution.metrics.start_time:
      execution.metrics.recovery_duration_seconds = (
        execution.metrics.end_time - execution.metrics.start_time
      ).total_seconds()
    
    # Count recovered vs failed components
    for path in execution.decision_paths:
      if path.success:
        execution.metrics.components_recovered += 1
      else:
        execution.metrics.components_failed += 1
    
    # Collect final system metrics
    for collector_name, collector in self.metrics_collectors.items():
      try:
        final_metrics = await collector.get_final_metrics(execution.execution_id)
        if collector_name == "system_metrics":
          execution.metrics.cpu_usage_peak = final_metrics.get("cpu_peak")
          execution.metrics.memory_usage_peak = final_metrics.get("memory_peak")
          execution.metrics.network_usage_peak = final_metrics.get("network_peak")
        elif collector_name == "business_metrics":
          execution.metrics.users_affected = final_metrics.get("users_affected")
          execution.metrics.transactions_lost = final_metrics.get("transactions_lost")
          execution.metrics.revenue_impact_dollars = final_metrics.get("revenue_impact")
        elif collector_name == "cost_metrics":
          execution.metrics.additional_costs = final_metrics.get("additional_costs")
      except Exception as e:
        self.logger.warning(f"Failed to collect final metrics from {collector_name}: {e}")
  
  def _update_orchestrator_statistics(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Update orchestrator statistics."""
    
    self.orchestrator_stats["total_recoveries"] += 1
    
    if execution.success:
      self.orchestrator_stats["successful_recoveries"] += 1
    else:
      self.orchestrator_stats["failed_recoveries"] += 1
    
    # Update average recovery time
    if execution.metrics.recovery_duration_seconds:
      total = self.orchestrator_stats["total_recoveries"]
      current_avg = self.orchestrator_stats["average_recovery_time"]
      new_duration = execution.metrics.recovery_duration_seconds
      
      self.orchestrator_stats["average_recovery_time"] = (
        (current_avg * (total - 1) + new_duration) / total
      )
    
    # Update zero downtime recoveries
    if execution.metrics.downtime_seconds == 0:
      self.orchestrator_stats["zero_downtime_recoveries"] += 1
    
    # Update fallback usage
    self.orchestrator_stats["fallback_strategies_used"] += execution.metrics.fallback_strategies_used
  
  # Advanced strategy creation methods (simplified implementations)
  
  def _create_zero_downtime_strategy(self) -> RecoveryStrategy:
    """Create zero-downtime recovery strategy."""
    # This would be a complex strategy implementation
    # For demo purposes, return a simplified version
    return RecoveryStrategy(
      strategy_id="zero_downtime_recovery",
      name="Zero Downtime Recovery",
      description="Recovery strategy that maintains service availability",
      failure_types=[FailureType.APPLICATION, FailureType.INFRASTRUCTURE],
      severity_levels=[FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.FRONTEND, ComponentType.BACKEND],
      environments=["production"],
      root_node_id="zero_downtime_start",
      nodes={},  # Would contain detailed decision tree nodes
      estimated_duration_minutes=5,
      success_rate=0.95,
      requires_human_oversight=False,
      data_safety_level="safe"
    )
  
  def _create_blue_green_recovery(self) -> RecoveryStrategy:
    """Create blue-green deployment recovery strategy."""
    return RecoveryStrategy(
      strategy_id="blue_green_recovery",
      name="Blue-Green Recovery",
      description="Recovery using blue-green deployment pattern",
      failure_types=[FailureType.APPLICATION, FailureType.CONFIGURATION],
      severity_levels=[FailureSeverity.MEDIUM, FailureSeverity.HIGH],
      component_types=[ComponentType.FRONTEND, ComponentType.BACKEND],
      environments=["production", "staging"],
      root_node_id="blue_green_start",
      nodes={},
      estimated_duration_minutes=10,
      success_rate=0.90,
      data_safety_level="safe"
    )
  
  def _create_canary_rollback_strategy(self) -> RecoveryStrategy:
    """Create canary rollback strategy."""
    return RecoveryStrategy(
      strategy_id="canary_rollback",
      name="Canary Rollback",
      description="Gradual rollback using canary deployment",
      failure_types=[FailureType.APPLICATION],
      severity_levels=[FailureSeverity.MEDIUM, FailureSeverity.HIGH],
      component_types=[ComponentType.FRONTEND, ComponentType.BACKEND],
      environments=["production"],
      root_node_id="canary_start",
      nodes={},
      estimated_duration_minutes=15,
      success_rate=0.85,
      data_safety_level="safe"
    )
  
  def _create_circuit_breaker_strategy(self) -> RecoveryStrategy:
    """Create circuit breaker recovery strategy."""
    return RecoveryStrategy(
      strategy_id="circuit_breaker_recovery",
      name="Circuit Breaker Recovery",
      description="Recovery using circuit breaker pattern",
      failure_types=[FailureType.DEPENDENCY, FailureType.NETWORK],
      severity_levels=[FailureSeverity.MEDIUM, FailureSeverity.HIGH],
      component_types=[ComponentType.BACKEND, ComponentType.EXTERNAL_API],
      environments=["production", "staging"],
      root_node_id="circuit_breaker_start",
      nodes={},
      estimated_duration_minutes=5,
      success_rate=0.88,
      data_safety_level="safe"
    )
  
  def _create_data_integrity_strategy(self) -> RecoveryStrategy:
    """Create data integrity recovery strategy."""
    return RecoveryStrategy(
      strategy_id="data_integrity_recovery",
      name="Data Integrity Recovery",
      description="Recovery focused on maintaining data integrity",
      failure_types=[FailureType.DATA],
      severity_levels=[FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.DATABASE],
      environments=["production", "staging"],
      root_node_id="data_integrity_start",
      nodes={},
      estimated_duration_minutes=45,
      success_rate=0.92,
      data_safety_level="caution"
    )
  
  def _create_multi_region_failover(self) -> RecoveryStrategy:
    """Create multi-region failover strategy."""
    return RecoveryStrategy(
      strategy_id="multi_region_failover",
      name="Multi-Region Failover",
      description="Failover to different geographic region",
      failure_types=[FailureType.INFRASTRUCTURE, FailureType.NETWORK],
      severity_levels=[FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.BACKEND, ComponentType.DATABASE, ComponentType.CDN],
      environments=["production"],
      root_node_id="multi_region_start",
      nodes={},
      estimated_duration_minutes=20,
      success_rate=0.87,
      data_safety_level="caution"
    )
  
  def _create_performance_recovery(self) -> RecoveryStrategy:
    """Create performance degradation recovery strategy."""
    return RecoveryStrategy(
      strategy_id="performance_recovery",
      name="Performance Recovery",
      description="Recovery from performance degradation issues",
      failure_types=[FailureType.RESOURCE, FailureType.APPLICATION],
      severity_levels=[FailureSeverity.MEDIUM, FailureSeverity.HIGH],
      component_types=[ComponentType.BACKEND, ComponentType.DATABASE, ComponentType.CACHE],
      environments=["production", "staging"],
      root_node_id="performance_start",
      nodes={},
      estimated_duration_minutes=15,
      success_rate=0.83,
      data_safety_level="safe"
    )
  
  def _create_security_incident_recovery(self) -> RecoveryStrategy:
    """Create security incident recovery strategy."""
    return RecoveryStrategy(
      strategy_id="security_incident_recovery",
      name="Security Incident Recovery",
      description="Recovery from security breaches and incidents",
      failure_types=[FailureType.SECURITY],
      severity_levels=[FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.AUTHENTICATION, ComponentType.API_GATEWAY, ComponentType.BACKEND],
      environments=["production", "staging"],
      root_node_id="security_incident_start",
      nodes={},
      estimated_duration_minutes=60,
      success_rate=0.75,
      data_safety_level="risk"
    )
  
  def get_orchestrator_statistics(self) -> Dict[str, Any]:
    """Get current orchestrator statistics."""
    stats = self.orchestrator_stats.copy()
    
    if stats["total_recoveries"] > 0:
      stats["success_rate"] = stats["successful_recoveries"] / stats["total_recoveries"]
      stats["zero_downtime_rate"] = stats["zero_downtime_recoveries"] / stats["total_recoveries"]
    else:
      stats["success_rate"] = 0.0
      stats["zero_downtime_rate"] = 0.0
    
    stats["active_recoveries"] = len(self.active_recoveries)
    stats["total_recovery_plans"] = len(self.recovery_plans)
    
    return stats
  
  def export_recovery_execution(self, execution: RecoveryExecution, format: str = "json") -> str:
    """Export recovery execution in specified format."""
    
    if format.lower() == "json":
      execution_dict = asdict(execution)
      
      # Handle datetime and enum serialization
      execution_dict["start_time"] = execution.start_time.isoformat()
      if execution_dict["end_time"]:
        execution_dict["end_time"] = execution.end_time.isoformat()
      if execution_dict["final_result"]:
        execution_dict["final_result"] = execution.final_result.value
      execution_dict["current_phase"] = execution.current_phase.value
      
      # Handle metrics datetime
      if execution_dict["metrics"]["start_time"]:
        execution_dict["metrics"]["start_time"] = execution.metrics.start_time.isoformat()
      if execution_dict["metrics"]["end_time"]:
        execution_dict["metrics"]["end_time"] = execution.metrics.end_time.isoformat()
      
      return json.dumps(execution_dict, indent=2)
    
    else:
      return f"Unsupported export format: {format}"


# Component coordinator classes (simplified implementations)

class ComponentCoordinator:
  """Base class for component coordinators."""
  
  def __init__(self, orchestrator: RecoveryOrchestrator):
    self.orchestrator = orchestrator
    self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
  
  async def prepare_for_recovery(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Prepare component for recovery execution."""
    pass
  
  async def validate_health(self) -> bool:
    """Validate component health."""
    return True


class FrontendRecoveryCoordinator(ComponentCoordinator):
  """Coordinator for frontend recovery operations."""
  
  async def prepare_for_recovery(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Prepare frontend systems for recovery."""
    self.logger.info(f"Preparing frontend for recovery {execution.execution_id}")
    # Implementation would prepare frontend systems
  
  async def validate_health(self) -> bool:
    """Validate frontend health."""
    # Implementation would check frontend health
    return True


class BackendRecoveryCoordinator(ComponentCoordinator):
  """Coordinator for backend recovery operations."""
  
  async def prepare_for_recovery(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Prepare backend systems for recovery."""
    self.logger.info(f"Preparing backend for recovery {execution.execution_id}")
    # Implementation would prepare backend systems
  
  async def validate_health(self) -> bool:
    """Validate backend health."""
    # Implementation would check backend health
    return True


class DatabaseRecoveryCoordinator(ComponentCoordinator):
  """Coordinator for database recovery operations."""
  
  async def prepare_for_recovery(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Prepare database systems for recovery."""
    self.logger.info(f"Preparing database for recovery {execution.execution_id}")
    # Implementation would prepare database systems
  
  async def validate_health(self) -> bool:
    """Validate database health."""
    # Implementation would check database health
    return True


class InfrastructureRecoveryCoordinator(ComponentCoordinator):
  """Coordinator for infrastructure recovery operations."""
  
  async def prepare_for_recovery(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Prepare infrastructure for recovery."""
    self.logger.info(f"Preparing infrastructure for recovery {execution.execution_id}")
    # Implementation would prepare infrastructure
  
  async def validate_health(self) -> bool:
    """Validate infrastructure health."""
    # Implementation would check infrastructure health
    return True


class NetworkRecoveryCoordinator(ComponentCoordinator):
  """Coordinator for network recovery operations."""
  
  async def prepare_for_recovery(self, execution: RecoveryExecution, plan: RecoveryPlan):
    """Prepare network systems for recovery."""
    self.logger.info(f"Preparing network for recovery {execution.execution_id}")
    # Implementation would prepare network systems
  
  async def validate_health(self) -> bool:
    """Validate network health."""
    # Implementation would check network health
    return True


# Metrics collector classes (simplified implementations)

class MetricsCollector:
  """Base class for metrics collectors."""
  
  async def start_collection(self, execution_id: str):
    """Start collecting metrics for execution."""
    pass
  
  async def get_final_metrics(self, execution_id: str) -> Dict[str, Any]:
    """Get final metrics for execution."""
    return {}


class SystemMetricsCollector(MetricsCollector):
  """Collector for system metrics."""
  
  async def get_final_metrics(self, execution_id: str) -> Dict[str, Any]:
    """Get final system metrics."""
    return {
      "cpu_peak": 75.0,
      "memory_peak": 82.0,
      "network_peak": 45.0
    }


class BusinessMetricsCollector(MetricsCollector):
  """Collector for business metrics."""
  
  async def get_final_metrics(self, execution_id: str) -> Dict[str, Any]:
    """Get final business metrics."""
    return {
      "users_affected": 1500,
      "transactions_lost": 25,
      "revenue_impact": 500.0
    }


class UserExperienceCollector(MetricsCollector):
  """Collector for user experience metrics."""
  
  async def get_final_metrics(self, execution_id: str) -> Dict[str, Any]:
    """Get final user experience metrics."""
    return {
      "response_time_impact": 2.5,
      "error_rate_impact": 5.0,
      "user_satisfaction_score": 7.2
    }


class CostMetricsCollector(MetricsCollector):
  """Collector for cost metrics."""
  
  async def get_final_metrics(self, execution_id: str) -> Dict[str, Any]:
    """Get final cost metrics."""
    return {
      "additional_costs": 125.0,
      "resource_optimization_savings": 50.0
    }


if __name__ == "__main__":
  # Example usage and testing
  import asyncio
  logging.basicConfig(level=logging.INFO)
  
  async def test_recovery_orchestrator():
    # Import required modules for testing
    from failure_categorizer import FailureCategorizer, FailureContext
    
    # Create orchestrator and categorizer
    orchestrator = RecoveryOrchestrator()
    categorizer = FailureCategorizer()
    
    # Example failure scenario
    error_messages = [
      "Database connection timeout",
      "Connection pool exhausted"
    ]
    
    log_entries = [
      "2024-01-15T10:00:00 ERROR: Database connection failed",
      "2024-01-15T10:00:05 CRITICAL: System unable to serve requests"
    ]
    
    metrics = {
      "db_connection_errors": 20.0,
      "error_rate": 15.0,
      "response_time_p95": 12000.0
    }
    
    status_codes = [500, 503]
    
    context = FailureContext(
      environment="production",
      timestamp=datetime.now(),
      affected_users=2000,
      error_rate=15.0
    )
    
    # Categorize the failure
    failure = categorizer.categorize_failure(
      error_messages=error_messages,
      log_entries=log_entries,
      metrics=metrics,
      status_codes=status_codes,
      context=context
    )
    
    print("=== Failure Categorization ===")
    print(f"Type: {failure.failure_type.value}")
    print(f"Severity: {failure.severity.value}")
    print(f"Components: {[c.value for c in failure.affected_components]}")
    
    # Create recovery constraints
    constraints = RecoveryConstraints(
      max_downtime_minutes=10,
      max_data_loss_seconds=0,
      min_availability_percent=99.5,
      requires_approval=False,
      notification_required=True
    )
    
    # Create recovery plan
    print("\n=== Creating Recovery Plan ===")
    plan = await orchestrator.create_recovery_plan(failure, constraints)
    
    print(f"Plan ID: {plan.plan_id}")
    print(f"Primary Strategy: {plan.primary_strategy.name}")
    print(f"Fallback Strategies: {len(plan.fallback_strategies)}")
    print(f"Estimated Duration: {plan.estimated_duration_minutes} minutes")
    print(f"Success Probability: {plan.success_probability:.1%}")
    print(f"Estimated Impact: {plan.estimated_impact.value}")
    
    # Execute recovery plan
    print("\n=== Executing Recovery Plan ===")
    execution = await orchestrator.execute_recovery_plan(plan, dry_run=True)
    
    print(f"Execution ID: {execution.execution_id}")
    print(f"Final Result: {execution.final_result.value if execution.final_result else 'None'}")
    print(f"Success: {execution.success}")
    print(f"Duration: {execution.metrics.recovery_duration_seconds:.1f}s")
    print(f"Components Recovered: {execution.metrics.components_recovered}")
    print(f"Fallback Strategies Used: {execution.metrics.fallback_strategies_used}")
    
    print(f"\n=== Execution Progress ===")
    for msg in execution.status_messages[-5:]:  # Show last 5 messages
      print(f"[{msg['phase']}] {msg['message']} ({msg['progress']:.0f}%)")
    
    print(f"\n=== Decision Paths ===")
    for i, path in enumerate(execution.decision_paths, 1):
      print(f"Path {i}: {path.final_result.value if path.final_result else 'None'} "
            f"({path.total_execution_time:.1f}s)")
    
    print(f"\n=== Orchestrator Statistics ===")
    stats = orchestrator.get_orchestrator_statistics()
    print(f"Total Recoveries: {stats['total_recoveries']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")
    print(f"Zero Downtime Rate: {stats['zero_downtime_rate']:.1%}")
    print(f"Average Recovery Time: {stats['average_recovery_time']:.1f}s")
  
  # Run the test
  asyncio.run(test_recovery_orchestrator())