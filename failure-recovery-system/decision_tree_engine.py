#!/usr/bin/env python3
"""
Decision Tree Engine for Deployment Failure Recovery
===================================================

This module implements a sophisticated decision tree system that maps failure types
to appropriate recovery strategies. The decision tree considers multiple factors:
- Failure type and severity
- Affected components and their criticality
- Environment and business context
- Recovery complexity and resource availability

The engine uses a rule-based approach with configurable decision nodes and provides
clear reasoning for each decision made.
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
import uuid

from failure_categorizer import (
  CategorizedFailure, FailureType, FailureSeverity, 
  ComponentType, RecoveryComplexity, FailureContext
)


class DecisionNodeType(Enum):
  """Types of decision nodes in the recovery decision tree."""
  
  # Condition nodes check specific conditions
  CONDITION = "condition"
  
  # Action nodes execute specific recovery actions
  ACTION = "action"
  
  # Route nodes redirect to different decision branches
  ROUTE = "route"
  
  # Gate nodes require approval before proceeding
  GATE = "gate"
  
  # Parallel nodes execute multiple branches simultaneously
  PARALLEL = "parallel"
  
  # Loop nodes repeat actions until condition is met
  LOOP = "loop"


class ActionType(Enum):
  """Types of recovery actions that can be executed."""
  
  # Immediate automated actions
  RESTART_SERVICE = "restart_service"
  SCALE_UP_RESOURCES = "scale_up_resources"
  CLEAR_CACHE = "clear_cache"
  FAILOVER_TO_BACKUP = "failover_to_backup"
  ROLLBACK_DEPLOYMENT = "rollback_deployment"
  
  # Configuration and infrastructure actions
  UPDATE_CONFIGURATION = "update_configuration"
  RESTART_INFRASTRUCTURE = "restart_infrastructure"
  RESET_CONNECTIONS = "reset_connections"
  FLUSH_DNS_CACHE = "flush_dns_cache"
  
  # Manual intervention actions
  NOTIFY_TEAM = "notify_team"
  CREATE_INCIDENT = "create_incident"
  ESCALATE_TO_MANAGEMENT = "escalate_to_management"
  REQUEST_APPROVAL = "request_approval"
  
  # Diagnostic and monitoring actions
  COLLECT_DIAGNOSTICS = "collect_diagnostics"
  ENABLE_DEBUG_LOGGING = "enable_debug_logging"
  CAPTURE_METRICS = "capture_metrics"
  RUN_HEALTH_CHECKS = "run_health_checks"
  
  # Data and security actions
  BACKUP_DATA = "backup_data"
  VALIDATE_DATA_INTEGRITY = "validate_data_integrity"
  RESET_SECURITY_TOKENS = "reset_security_tokens"
  ISOLATE_AFFECTED_SYSTEMS = "isolate_affected_systems"
  
  # Communication actions
  UPDATE_STATUS_PAGE = "update_status_page"
  NOTIFY_USERS = "notify_users"
  SEND_ALERTS = "send_alerts"
  DOCUMENT_ACTIONS = "document_actions"


class DecisionResult(Enum):
  """Possible results of decision tree execution."""
  
  SUCCESS = "success"
  FAILURE = "failure" 
  REQUIRES_APPROVAL = "requires_approval"
  ESCALATION_NEEDED = "escalation_needed"
  MANUAL_INTERVENTION = "manual_intervention"
  PARTIAL_SUCCESS = "partial_success"
  TIMEOUT = "timeout"
  CANCELLED = "cancelled"


@dataclass
class DecisionNode:
  """Represents a single node in the decision tree."""
  
  node_id: str
  node_type: DecisionNodeType
  name: str
  description: str
  
  # Condition evaluation (for CONDITION nodes)
  condition: Optional[Dict[str, Any]] = None
  
  # Action specification (for ACTION nodes)
  action: Optional[ActionType] = None
  action_params: Optional[Dict[str, Any]] = None
  
  # Child nodes and routing
  children: List[str] = None  # Node IDs of child nodes
  success_node: Optional[str] = None  # Node to go to on success
  failure_node: Optional[str] = None  # Node to go to on failure
  
  # Execution constraints
  timeout_seconds: Optional[int] = None
  max_retries: int = 1
  requires_approval: bool = False
  
  # Metadata
  priority: int = 0
  tags: List[str] = None
  
  def __post_init__(self):
    if self.children is None:
      self.children = []
    if self.tags is None:
      self.tags = []


@dataclass
class DecisionPath:
  """Represents a path through the decision tree with execution results."""
  
  path_id: str
  failure_id: str
  start_time: datetime
  end_time: Optional[datetime] = None
  
  # Execution trace
  nodes_visited: List[str] = None
  actions_executed: List[Dict[str, Any]] = None
  decision_reasoning: List[str] = None
  
  # Results
  final_result: Optional[DecisionResult] = None
  success: bool = False
  error_message: Optional[str] = None
  
  # Metrics
  total_execution_time: Optional[float] = None
  actions_successful: int = 0
  actions_failed: int = 0
  
  def __post_init__(self):
    if self.nodes_visited is None:
      self.nodes_visited = []
    if self.actions_executed is None:
      self.actions_executed = []
    if self.decision_reasoning is None:
      self.decision_reasoning = []


@dataclass
class RecoveryStrategy:
  """Defines a complete recovery strategy with decision tree."""
  
  strategy_id: str
  name: str
  description: str
  
  # Applicability conditions
  failure_types: List[FailureType]
  severity_levels: List[FailureSeverity]
  component_types: List[ComponentType]
  environments: List[str]
  
  # Decision tree
  root_node_id: str
  nodes: Dict[str, DecisionNode]
  
  # Strategy metadata
  estimated_duration_minutes: int
  success_rate: float
  requires_human_oversight: bool = False
  data_safety_level: str = "safe"  # safe, caution, risk
  
  # Configuration
  max_execution_time: int = 3600  # seconds
  notification_settings: Dict[str, Any] = None
  
  def __post_init__(self):
    if self.notification_settings is None:
      self.notification_settings = {}


class DecisionTreeEngine:
  """
  Main engine for executing recovery decision trees based on failure categorization.
  
  The engine:
  1. Selects appropriate recovery strategies based on failure characteristics
  2. Executes decision trees with proper error handling and logging
  3. Provides clear reasoning for each decision made
  4. Supports parallel execution and approval gates
  5. Tracks execution metrics and success rates
  """
  
  def __init__(self, config_path: Optional[Path] = None):
    self.logger = logging.getLogger(__name__)
    self.config_path = config_path or Path(__file__).parent / "decision_tree_config.yaml"
    
    # Load configuration
    self.config = self._load_configuration()
    
    # Initialize recovery strategies
    self.strategies: Dict[str, RecoveryStrategy] = {}
    self._initialize_recovery_strategies()
    
    # Execution tracking
    self.active_executions: Dict[str, DecisionPath] = {}
    self.execution_history: List[DecisionPath] = []
    
    # Statistics
    self.stats = {
      "total_executions": 0,
      "successful_recoveries": 0,
      "failed_recoveries": 0,
      "average_execution_time": 0.0,
      "strategy_success_rates": {}
    }
    
    # Action executors (can be overridden for testing)
    self.action_executors: Dict[ActionType, Callable] = self._initialize_action_executors()
  
  def _load_configuration(self) -> Dict[str, Any]:
    """Load decision tree configuration."""
    default_config = {
      "max_concurrent_executions": 10,
      "default_timeout_seconds": 300,
      "approval_timeout_seconds": 1800,
      "retry_delay_seconds": 30,
      "logging_level": "INFO",
      "notifications": {
        "slack_webhook": "",
        "email_recipients": [],
        "status_page_api": ""
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
  
  def _initialize_recovery_strategies(self):
    """Initialize predefined recovery strategies."""
    
    # Strategy 1: Infrastructure Failure Recovery
    self.strategies["infrastructure_recovery"] = RecoveryStrategy(
      strategy_id="infrastructure_recovery",
      name="Infrastructure Failure Recovery",
      description="Handles container, pod, and infrastructure-level failures",
      failure_types=[FailureType.INFRASTRUCTURE, FailureType.RESOURCE],
      severity_levels=[FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.BACKEND, ComponentType.DATABASE],
      environments=["production", "staging"],
      root_node_id="infra_start",
      nodes=self._create_infrastructure_recovery_nodes(),
      estimated_duration_minutes=15,
      success_rate=0.85,
      requires_human_oversight=True
    )
    
    # Strategy 2: Application Error Recovery
    self.strategies["application_recovery"] = RecoveryStrategy(
      strategy_id="application_recovery", 
      name="Application Error Recovery",
      description="Handles application-level bugs and runtime errors",
      failure_types=[FailureType.APPLICATION, FailureType.TIMING],
      severity_levels=[FailureSeverity.MEDIUM, FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.BACKEND, ComponentType.FRONTEND],
      environments=["production", "staging", "development"],
      root_node_id="app_start",
      nodes=self._create_application_recovery_nodes(),
      estimated_duration_minutes=30,
      success_rate=0.75,
      requires_human_oversight=True
    )
    
    # Strategy 3: Database Recovery
    self.strategies["database_recovery"] = RecoveryStrategy(
      strategy_id="database_recovery",
      name="Database Recovery",
      description="Handles database connectivity and data integrity issues",
      failure_types=[FailureType.DATA, FailureType.RESOURCE],
      severity_levels=[FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.DATABASE],
      environments=["production", "staging"],
      root_node_id="db_start",
      nodes=self._create_database_recovery_nodes(),
      estimated_duration_minutes=45,
      success_rate=0.80,
      requires_human_oversight=True,
      data_safety_level="caution"
    )
    
    # Strategy 4: Configuration Fix
    self.strategies["configuration_fix"] = RecoveryStrategy(
      strategy_id="configuration_fix",
      name="Configuration Fix",
      description="Handles configuration and environment variable issues",
      failure_types=[FailureType.CONFIGURATION, FailureType.DEPENDENCY],
      severity_levels=[FailureSeverity.LOW, FailureSeverity.MEDIUM, FailureSeverity.HIGH],
      component_types=[ComponentType.BACKEND, ComponentType.API_GATEWAY],
      environments=["production", "staging", "development"],
      root_node_id="config_start",
      nodes=self._create_configuration_recovery_nodes(),
      estimated_duration_minutes=10,
      success_rate=0.90,
      requires_human_oversight=False
    )
    
    # Strategy 5: Security Incident Response
    self.strategies["security_response"] = RecoveryStrategy(
      strategy_id="security_response",
      name="Security Incident Response",
      description="Handles security breaches and authentication failures",
      failure_types=[FailureType.SECURITY],
      severity_levels=[FailureSeverity.HIGH, FailureSeverity.CRITICAL],
      component_types=[ComponentType.AUTHENTICATION, ComponentType.API_GATEWAY],
      environments=["production", "staging"],
      root_node_id="security_start",
      nodes=self._create_security_recovery_nodes(),
      estimated_duration_minutes=60,
      success_rate=0.70,
      requires_human_oversight=True,
      data_safety_level="risk"
    )
    
    # Strategy 6: Network Recovery
    self.strategies["network_recovery"] = RecoveryStrategy(
      strategy_id="network_recovery",
      name="Network Recovery",
      description="Handles network connectivity and DNS issues",
      failure_types=[FailureType.NETWORK],
      severity_levels=[FailureSeverity.MEDIUM, FailureSeverity.HIGH],
      component_types=[ComponentType.LOAD_BALANCER, ComponentType.CDN, ComponentType.API_GATEWAY],
      environments=["production", "staging"],
      root_node_id="network_start",
      nodes=self._create_network_recovery_nodes(),
      estimated_duration_minutes=20,
      success_rate=0.80,
      requires_human_oversight=False
    )
  
  def _create_infrastructure_recovery_nodes(self) -> Dict[str, DecisionNode]:
    """Create decision tree nodes for infrastructure failure recovery."""
    return {
      "infra_start": DecisionNode(
        node_id="infra_start",
        node_type=DecisionNodeType.CONDITION,
        name="Check Infrastructure Status",
        description="Evaluate current infrastructure health and resource availability",
        condition={"check": "infrastructure_health"},
        success_node="infra_resource_check",
        failure_node="infra_restart_services"
      ),
      
      "infra_resource_check": DecisionNode(
        node_id="infra_resource_check",
        node_type=DecisionNodeType.CONDITION,
        name="Check Resource Utilization",
        description="Verify if resource limits are causing the failure",
        condition={"check": "resource_utilization", "threshold": 90},
        success_node="infra_scale_up",
        failure_node="infra_health_check"
      ),
      
      "infra_scale_up": DecisionNode(
        node_id="infra_scale_up",
        node_type=DecisionNodeType.ACTION,
        name="Scale Up Resources",
        description="Increase CPU, memory, or disk resources",
        action=ActionType.SCALE_UP_RESOURCES,
        action_params={"target_utilization": 70, "scale_factor": 1.5},
        success_node="infra_verify_health",
        failure_node="infra_restart_services",
        timeout_seconds=180
      ),
      
      "infra_restart_services": DecisionNode(
        node_id="infra_restart_services",
        node_type=DecisionNodeType.ACTION,
        name="Restart Services",
        description="Restart failed containers/pods/services",
        action=ActionType.RESTART_SERVICE,
        action_params={"service_type": "all_affected", "graceful": True},
        success_node="infra_verify_health",
        failure_node="infra_restart_infrastructure",
        timeout_seconds=120,
        max_retries=2
      ),
      
      "infra_restart_infrastructure": DecisionNode(
        node_id="infra_restart_infrastructure",
        node_type=DecisionNodeType.GATE,
        name="Restart Infrastructure",
        description="Restart underlying infrastructure components",
        action=ActionType.RESTART_INFRASTRUCTURE,
        action_params={"components": ["nodes", "load_balancers"], "rolling": True},
        success_node="infra_verify_health",
        failure_node="infra_escalate",
        requires_approval=True,
        timeout_seconds=600
      ),
      
      "infra_health_check": DecisionNode(
        node_id="infra_health_check",
        node_type=DecisionNodeType.ACTION,
        name="Run Health Checks",
        description="Execute comprehensive health checks on infrastructure",
        action=ActionType.RUN_HEALTH_CHECKS,
        action_params={"scope": "infrastructure", "detailed": True},
        success_node="infra_verify_health",
        failure_node="infra_collect_diagnostics",
        timeout_seconds=60
      ),
      
      "infra_collect_diagnostics": DecisionNode(
        node_id="infra_collect_diagnostics",
        node_type=DecisionNodeType.ACTION,
        name="Collect Diagnostics",
        description="Gather system logs, metrics, and diagnostic information",
        action=ActionType.COLLECT_DIAGNOSTICS,
        action_params={"include": ["logs", "metrics", "events", "resource_usage"]},
        success_node="infra_escalate",
        failure_node="infra_escalate",
        timeout_seconds=120
      ),
      
      "infra_verify_health": DecisionNode(
        node_id="infra_verify_health",
        node_type=DecisionNodeType.CONDITION,
        name="Verify Recovery",
        description="Confirm that infrastructure recovery was successful",
        condition={"check": "infrastructure_health", "wait_time": 60},
        success_node="infra_success",
        failure_node="infra_escalate"
      ),
      
      "infra_escalate": DecisionNode(
        node_id="infra_escalate",
        node_type=DecisionNodeType.ACTION,
        name="Escalate to Operations Team",
        description="Create incident and notify operations team for manual intervention",
        action=ActionType.ESCALATE_TO_MANAGEMENT,
        action_params={"team": "operations", "priority": "high", "include_diagnostics": True},
        success_node="infra_failure",
        failure_node="infra_failure",
        timeout_seconds=30
      ),
      
      "infra_success": DecisionNode(
        node_id="infra_success",
        node_type=DecisionNodeType.ACTION,
        name="Recovery Successful",
        description="Infrastructure recovery completed successfully",
        action=ActionType.UPDATE_STATUS_PAGE,
        action_params={"status": "resolved", "message": "Infrastructure issues resolved"}
      ),
      
      "infra_failure": DecisionNode(
        node_id="infra_failure",
        node_type=DecisionNodeType.ACTION,
        name="Recovery Failed",
        description="Infrastructure recovery failed, manual intervention required",
        action=ActionType.CREATE_INCIDENT,
        action_params={"severity": "high", "description": "Infrastructure recovery failed"}
      )
    }
  
  def _create_application_recovery_nodes(self) -> Dict[str, DecisionNode]:
    """Create decision tree nodes for application error recovery."""
    return {
      "app_start": DecisionNode(
        node_id="app_start",
        node_type=DecisionNodeType.CONDITION,
        name="Analyze Error Patterns",
        description="Analyze application errors to determine recovery approach",
        condition={"check": "error_analysis"},
        success_node="app_check_recent_deploy",
        failure_node="app_collect_logs"
      ),
      
      "app_check_recent_deploy": DecisionNode(
        node_id="app_check_recent_deploy",
        node_type=DecisionNodeType.CONDITION,
        name="Check Recent Deployment",
        description="Check if errors started after recent deployment",
        condition={"check": "recent_deployment", "timeframe": "2h"},
        success_node="app_rollback_gate",
        failure_node="app_restart_services"
      ),
      
      "app_rollback_gate": DecisionNode(
        node_id="app_rollback_gate",
        node_type=DecisionNodeType.GATE,
        name="Rollback Decision Gate",
        description="Decide whether to rollback recent deployment",
        action=ActionType.REQUEST_APPROVAL,
        action_params={"action": "rollback_deployment", "timeout": 300},
        success_node="app_rollback",
        failure_node="app_restart_services",
        requires_approval=True
      ),
      
      "app_rollback": DecisionNode(
        node_id="app_rollback",
        node_type=DecisionNodeType.ACTION,
        name="Rollback Deployment",
        description="Rollback to previous known good deployment",
        action=ActionType.ROLLBACK_DEPLOYMENT,
        action_params={"strategy": "immediate", "backup_data": True},
        success_node="app_verify_rollback",
        failure_node="app_restart_services",
        timeout_seconds=300
      ),
      
      "app_restart_services": DecisionNode(
        node_id="app_restart_services",
        node_type=DecisionNodeType.ACTION,
        name="Restart Application Services",
        description="Restart application services to clear transient issues",
        action=ActionType.RESTART_SERVICE,
        action_params={"service_type": "application", "graceful": True},
        success_node="app_clear_cache",
        failure_node="app_enable_debug",
        timeout_seconds=120,
        max_retries=1
      ),
      
      "app_clear_cache": DecisionNode(
        node_id="app_clear_cache",
        node_type=DecisionNodeType.ACTION,
        name="Clear Application Cache",
        description="Clear application caches that might contain stale data",
        action=ActionType.CLEAR_CACHE,
        action_params={"cache_types": ["redis", "memcached", "application"]},
        success_node="app_verify_health",
        failure_node="app_enable_debug",
        timeout_seconds=60
      ),
      
      "app_enable_debug": DecisionNode(
        node_id="app_enable_debug",
        node_type=DecisionNodeType.ACTION,
        name="Enable Debug Logging",
        description="Enable detailed debug logging for troubleshooting",
        action=ActionType.ENABLE_DEBUG_LOGGING,
        action_params={"level": "DEBUG", "duration": 1800},
        success_node="app_collect_logs",
        failure_node="app_collect_logs",
        timeout_seconds=30
      ),
      
      "app_collect_logs": DecisionNode(
        node_id="app_collect_logs",
        node_type=DecisionNodeType.ACTION,
        name="Collect Application Logs",
        description="Collect recent application logs for analysis",
        action=ActionType.COLLECT_DIAGNOSTICS,
        action_params={"include": ["application_logs", "error_traces", "performance_metrics"]},
        success_node="app_escalate",
        failure_node="app_escalate",
        timeout_seconds=120
      ),
      
      "app_verify_rollback": DecisionNode(
        node_id="app_verify_rollback",
        node_type=DecisionNodeType.CONDITION,
        name="Verify Rollback Success",
        description="Verify that rollback resolved the application issues",
        condition={"check": "application_health", "wait_time": 120},
        success_node="app_success",
        failure_node="app_restart_services"
      ),
      
      "app_verify_health": DecisionNode(
        node_id="app_verify_health",
        node_type=DecisionNodeType.CONDITION,
        name="Verify Application Health",
        description="Verify that application recovery was successful",
        condition={"check": "application_health", "wait_time": 60},
        success_node="app_success",
        failure_node="app_escalate"
      ),
      
      "app_escalate": DecisionNode(
        node_id="app_escalate",
        node_type=DecisionNodeType.ACTION,
        name="Escalate to Development Team",
        description="Create incident and notify development team",
        action=ActionType.ESCALATE_TO_MANAGEMENT,
        action_params={"team": "development", "priority": "high", "include_logs": True},
        success_node="app_failure",
        failure_node="app_failure",
        timeout_seconds=30
      ),
      
      "app_success": DecisionNode(
        node_id="app_success",
        node_type=DecisionNodeType.ACTION,
        name="Recovery Successful",
        description="Application recovery completed successfully",
        action=ActionType.UPDATE_STATUS_PAGE,
        action_params={"status": "resolved", "message": "Application issues resolved"}
      ),
      
      "app_failure": DecisionNode(
        node_id="app_failure",
        node_type=DecisionNodeType.ACTION,
        name="Recovery Failed",
        description="Application recovery failed, manual intervention required",
        action=ActionType.CREATE_INCIDENT,
        action_params={"severity": "high", "description": "Application recovery failed"}
      )
    }
  
  def _create_database_recovery_nodes(self) -> Dict[str, DecisionNode]:
    """Create decision tree nodes for database recovery."""
    return {
      "db_start": DecisionNode(
        node_id="db_start",
        node_type=DecisionNodeType.ACTION,
        name="Backup Current State",
        description="Create backup before attempting database recovery",
        action=ActionType.BACKUP_DATA,
        action_params={"type": "incremental", "verify": True},
        success_node="db_check_connections",
        failure_node="db_escalate_immediate",
        timeout_seconds=300
      ),
      
      "db_check_connections": DecisionNode(
        node_id="db_check_connections",
        node_type=DecisionNodeType.CONDITION,
        name="Check Database Connections",
        description="Verify database connectivity and connection pool status",
        condition={"check": "database_connectivity"},
        success_node="db_check_integrity",
        failure_node="db_reset_connections"
      ),
      
      "db_reset_connections": DecisionNode(
        node_id="db_reset_connections",
        node_type=DecisionNodeType.ACTION,
        name="Reset Database Connections",
        description="Reset connection pools and establish new connections",
        action=ActionType.RESET_CONNECTIONS,
        action_params={"component": "database", "pool_size": "default"},
        success_node="db_check_integrity", 
        failure_node="db_restart_database",
        timeout_seconds=60
      ),
      
      "db_restart_database": DecisionNode(
        node_id="db_restart_database",
        node_type=DecisionNodeType.GATE,
        name="Restart Database Service",
        description="Restart database service (requires approval)",
        action=ActionType.RESTART_SERVICE,
        action_params={"service_type": "database", "graceful": True},
        success_node="db_check_integrity",
        failure_node="db_escalate_immediate",
        requires_approval=True,
        timeout_seconds=180
      ),
      
      "db_check_integrity": DecisionNode(
        node_id="db_check_integrity",
        node_type=DecisionNodeType.ACTION,
        name="Validate Data Integrity",
        description="Run data integrity checks and consistency validation",
        action=ActionType.VALIDATE_DATA_INTEGRITY,
        action_params={"scope": "critical_tables", "repair": False},
        success_node="db_verify_health",
        failure_node="db_integrity_gate",
        timeout_seconds=600
      ),
      
      "db_integrity_gate": DecisionNode(
        node_id="db_integrity_gate",
        node_type=DecisionNodeType.GATE,
        name="Data Integrity Issue Gate",
        description="Data integrity issues detected - decide on repair approach",
        action=ActionType.REQUEST_APPROVAL,
        action_params={"action": "repair_data_integrity", "risk": "high", "timeout": 600},
        success_node="db_repair_integrity",
        failure_node="db_escalate_immediate",
        requires_approval=True
      ),
      
      "db_repair_integrity": DecisionNode(
        node_id="db_repair_integrity",
        node_type=DecisionNodeType.ACTION,
        name="Repair Data Integrity",
        description="Attempt to repair data integrity issues",
        action=ActionType.VALIDATE_DATA_INTEGRITY,
        action_params={"scope": "critical_tables", "repair": True, "backup_first": True},
        success_node="db_verify_health",
        failure_node="db_escalate_immediate",
        timeout_seconds=1800
      ),
      
      "db_verify_health": DecisionNode(
        node_id="db_verify_health",
        node_type=DecisionNodeType.CONDITION,
        name="Verify Database Health",
        description="Verify that database recovery was successful",
        condition={"check": "database_health", "wait_time": 120},
        success_node="db_success",
        failure_node="db_escalate_immediate"
      ),
      
      "db_escalate_immediate": DecisionNode(
        node_id="db_escalate_immediate",
        node_type=DecisionNodeType.ACTION,
        name="Immediate Escalation",
        description="Immediately escalate to database team and management",
        action=ActionType.ESCALATE_TO_MANAGEMENT,
        action_params={"team": "database", "priority": "critical", "immediate": True},
        success_node="db_failure",
        failure_node="db_failure",
        timeout_seconds=30
      ),
      
      "db_success": DecisionNode(
        node_id="db_success",
        node_type=DecisionNodeType.ACTION,
        name="Recovery Successful",
        description="Database recovery completed successfully",
        action=ActionType.UPDATE_STATUS_PAGE,
        action_params={"status": "resolved", "message": "Database issues resolved"}
      ),
      
      "db_failure": DecisionNode(
        node_id="db_failure",
        node_type=DecisionNodeType.ACTION,
        name="Recovery Failed",
        description="Database recovery failed, immediate expert intervention required",
        action=ActionType.CREATE_INCIDENT,
        action_params={"severity": "critical", "description": "Database recovery failed - data integrity risk"}
      )
    }
  
  def _create_configuration_recovery_nodes(self) -> Dict[str, DecisionNode]:
    """Create decision tree nodes for configuration recovery."""
    return {
      "config_start": DecisionNode(
        node_id="config_start",
        node_type=DecisionNodeType.CONDITION,
        name="Validate Configuration",
        description="Check configuration files and environment variables",
        condition={"check": "configuration_validation"},
        success_node="config_success",
        failure_node="config_identify_issues"
      ),
      
      "config_identify_issues": DecisionNode(
        node_id="config_identify_issues",
        node_type=DecisionNodeType.ACTION,
        name="Identify Configuration Issues",
        description="Analyze configuration to identify specific problems",
        action=ActionType.COLLECT_DIAGNOSTICS,
        action_params={"include": ["config_files", "env_vars", "validation_errors"]},
        success_node="config_auto_fix",
        failure_node="config_manual_review",
        timeout_seconds=60
      ),
      
      "config_auto_fix": DecisionNode(
        node_id="config_auto_fix",
        node_type=DecisionNodeType.ACTION,
        name="Auto-Fix Configuration",
        description="Automatically fix common configuration issues",
        action=ActionType.UPDATE_CONFIGURATION,
        action_params={"auto_fix": True, "backup_first": True},
        success_node="config_restart_services",
        failure_node="config_manual_review",
        timeout_seconds=120
      ),
      
      "config_restart_services": DecisionNode(
        node_id="config_restart_services",
        node_type=DecisionNodeType.ACTION,
        name="Restart Services",
        description="Restart services to apply configuration changes",
        action=ActionType.RESTART_SERVICE,
        action_params={"service_type": "affected", "graceful": True},
        success_node="config_verify",
        failure_node="config_manual_review",
        timeout_seconds=120
      ),
      
      "config_verify": DecisionNode(
        node_id="config_verify",
        node_type=DecisionNodeType.CONDITION,
        name="Verify Configuration Fix",
        description="Verify that configuration changes resolved the issue",
        condition={"check": "configuration_validation", "wait_time": 30},
        success_node="config_success",
        failure_node="config_manual_review"
      ),
      
      "config_manual_review": DecisionNode(
        node_id="config_manual_review",
        node_type=DecisionNodeType.ACTION,
        name="Request Manual Review",
        description="Request manual review of configuration issues",
        action=ActionType.NOTIFY_TEAM,
        action_params={"team": "devops", "priority": "medium", "include_config": True},
        success_node="config_failure",
        failure_node="config_failure",
        timeout_seconds=30
      ),
      
      "config_success": DecisionNode(
        node_id="config_success",
        node_type=DecisionNodeType.ACTION,
        name="Recovery Successful",
        description="Configuration issues resolved successfully",
        action=ActionType.UPDATE_STATUS_PAGE,
        action_params={"status": "resolved", "message": "Configuration issues resolved"}
      ),
      
      "config_failure": DecisionNode(
        node_id="config_failure",
        node_type=DecisionNodeType.ACTION,
        name="Manual Intervention Required",
        description="Configuration recovery requires manual intervention",
        action=ActionType.CREATE_INCIDENT,
        action_params={"severity": "medium", "description": "Configuration recovery requires manual review"}
      )
    }
  
  def _create_security_recovery_nodes(self) -> Dict[str, DecisionNode]:
    """Create decision tree nodes for security incident response."""
    return {
      "security_start": DecisionNode(
        node_id="security_start",
        node_type=DecisionNodeType.ACTION,
        name="Isolate Affected Systems",
        description="Immediately isolate systems showing security issues",
        action=ActionType.ISOLATE_AFFECTED_SYSTEMS,
        action_params={"scope": "affected_components", "method": "network_isolation"},
        success_node="security_assess",
        failure_node="security_emergency",
        timeout_seconds=60
      ),
      
      "security_assess": DecisionNode(
        node_id="security_assess",
        node_type=DecisionNodeType.ACTION,
        name="Assess Security Impact",
        description="Analyze the scope and impact of the security incident",
        action=ActionType.COLLECT_DIAGNOSTICS,
        action_params={"include": ["security_logs", "access_logs", "auth_failures", "anomalies"]},
        success_node="security_reset_tokens",
        failure_node="security_emergency",
        timeout_seconds=180
      ),
      
      "security_reset_tokens": DecisionNode(
        node_id="security_reset_tokens",
        node_type=DecisionNodeType.ACTION,
        name="Reset Security Tokens",
        description="Reset all authentication tokens and sessions",
        action=ActionType.RESET_SECURITY_TOKENS,
        action_params={"scope": "all_active", "force_reauth": True},
        success_node="security_verify",
        failure_node="security_emergency",
        timeout_seconds=120
      ),
      
      "security_verify": DecisionNode(
        node_id="security_verify",
        node_type=DecisionNodeType.CONDITION,
        name="Verify Security Status",
        description="Verify that security measures have contained the incident",
        condition={"check": "security_status", "wait_time": 180},
        success_node="security_restore_access",
        failure_node="security_emergency"
      ),
      
      "security_restore_access": DecisionNode(
        node_id="security_restore_access",
        node_type=DecisionNodeType.GATE,
        name="Restore System Access",
        description="Gradually restore system access after security verification",
        action=ActionType.REQUEST_APPROVAL,
        action_params={"action": "restore_access", "timeout": 600},
        success_node="security_success",
        failure_node="security_emergency",
        requires_approval=True
      ),
      
      "security_emergency": DecisionNode(
        node_id="security_emergency",
        node_type=DecisionNodeType.ACTION,
        name="Emergency Security Response",
        description="Activate emergency security response procedures",
        action=ActionType.ESCALATE_TO_MANAGEMENT,
        action_params={"team": "security", "priority": "emergency", "immediate": True},
        success_node="security_failure",
        failure_node="security_failure",
        timeout_seconds=30
      ),
      
      "security_success": DecisionNode(
        node_id="security_success",
        node_type=DecisionNodeType.ACTION,
        name="Security Incident Contained",
        description="Security incident has been contained and resolved",
        action=ActionType.UPDATE_STATUS_PAGE,
        action_params={"status": "resolved", "message": "Security incident contained and resolved"}
      ),
      
      "security_failure": DecisionNode(
        node_id="security_failure",
        node_type=DecisionNodeType.ACTION,
        name="Emergency Response Required",
        description="Security incident requires emergency response",
        action=ActionType.CREATE_INCIDENT,
        action_params={"severity": "critical", "description": "Security incident - emergency response required"}
      )
    }
  
  def _create_network_recovery_nodes(self) -> Dict[str, DecisionNode]:
    """Create decision tree nodes for network recovery."""
    return {
      "network_start": DecisionNode(
        node_id="network_start",
        node_type=DecisionNodeType.ACTION,
        name="Run Network Diagnostics",
        description="Run comprehensive network connectivity tests",
        action=ActionType.RUN_HEALTH_CHECKS,
        action_params={"scope": "network", "include": ["connectivity", "dns", "latency"]},
        success_node="network_check_dns",
        failure_node="network_check_dns",
        timeout_seconds=120
      ),
      
      "network_check_dns": DecisionNode(
        node_id="network_check_dns",
        node_type=DecisionNodeType.CONDITION,
        name="Check DNS Resolution",
        description="Verify DNS resolution is working correctly",
        condition={"check": "dns_resolution"},
        success_node="network_check_load_balancer",
        failure_node="network_flush_dns"
      ),
      
      "network_flush_dns": DecisionNode(
        node_id="network_flush_dns",
        node_type=DecisionNodeType.ACTION,
        name="Flush DNS Cache",
        description="Clear DNS cache to resolve stale entries",
        action=ActionType.FLUSH_DNS_CACHE,
        action_params={"scope": "all_servers"},
        success_node="network_check_load_balancer",
        failure_node="network_escalate",
        timeout_seconds=60
      ),
      
      "network_check_load_balancer": DecisionNode(
        node_id="network_check_load_balancer",
        node_type=DecisionNodeType.CONDITION,
        name="Check Load Balancer Health",
        description="Verify load balancer configuration and health",
        condition={"check": "load_balancer_health"},
        success_node="network_success",
        failure_node="network_reset_load_balancer"
      ),
      
      "network_reset_load_balancer": DecisionNode(
        node_id="network_reset_load_balancer",
        node_type=DecisionNodeType.ACTION,
        name="Reset Load Balancer Configuration",
        description="Reset load balancer configuration to known good state",
        action=ActionType.UPDATE_CONFIGURATION,
        action_params={"component": "load_balancer", "reset_to_default": True},
        success_node="network_verify",
        failure_node="network_escalate",
        timeout_seconds=120
      ),
      
      "network_verify": DecisionNode(
        node_id="network_verify",
        node_type=DecisionNodeType.CONDITION,
        name="Verify Network Recovery",
        description="Verify that network issues have been resolved",
        condition={"check": "network_health", "wait_time": 60},
        success_node="network_success",
        failure_node="network_escalate"
      ),
      
      "network_escalate": DecisionNode(
        node_id="network_escalate",
        node_type=DecisionNodeType.ACTION,
        name="Escalate to Network Team",
        description="Escalate to network operations team",
        action=ActionType.ESCALATE_TO_MANAGEMENT,
        action_params={"team": "network", "priority": "high", "include_diagnostics": True},
        success_node="network_failure",
        failure_node="network_failure",
        timeout_seconds=30
      ),
      
      "network_success": DecisionNode(
        node_id="network_success",
        node_type=DecisionNodeType.ACTION,
        name="Network Recovery Successful",
        description="Network issues have been resolved",
        action=ActionType.UPDATE_STATUS_PAGE,
        action_params={"status": "resolved", "message": "Network connectivity restored"}
      ),
      
      "network_failure": DecisionNode(
        node_id="network_failure",
        node_type=DecisionNodeType.ACTION,
        name="Network Recovery Failed",
        description="Network recovery failed, expert intervention required",
        action=ActionType.CREATE_INCIDENT,
        action_params={"severity": "high", "description": "Network recovery failed"}
      )
    }
  
  def _initialize_action_executors(self) -> Dict[ActionType, Callable]:
    """Initialize action executor functions."""
    return {
      ActionType.RESTART_SERVICE: self._execute_restart_service,
      ActionType.SCALE_UP_RESOURCES: self._execute_scale_up_resources,
      ActionType.CLEAR_CACHE: self._execute_clear_cache,
      ActionType.FAILOVER_TO_BACKUP: self._execute_failover_to_backup,
      ActionType.ROLLBACK_DEPLOYMENT: self._execute_rollback_deployment,
      ActionType.UPDATE_CONFIGURATION: self._execute_update_configuration,
      ActionType.RESTART_INFRASTRUCTURE: self._execute_restart_infrastructure,
      ActionType.RESET_CONNECTIONS: self._execute_reset_connections,
      ActionType.FLUSH_DNS_CACHE: self._execute_flush_dns_cache,
      ActionType.NOTIFY_TEAM: self._execute_notify_team,
      ActionType.CREATE_INCIDENT: self._execute_create_incident,
      ActionType.ESCALATE_TO_MANAGEMENT: self._execute_escalate_to_management,
      ActionType.REQUEST_APPROVAL: self._execute_request_approval,
      ActionType.COLLECT_DIAGNOSTICS: self._execute_collect_diagnostics,
      ActionType.ENABLE_DEBUG_LOGGING: self._execute_enable_debug_logging,
      ActionType.CAPTURE_METRICS: self._execute_capture_metrics,
      ActionType.RUN_HEALTH_CHECKS: self._execute_run_health_checks,
      ActionType.BACKUP_DATA: self._execute_backup_data,
      ActionType.VALIDATE_DATA_INTEGRITY: self._execute_validate_data_integrity,
      ActionType.RESET_SECURITY_TOKENS: self._execute_reset_security_tokens,
      ActionType.ISOLATE_AFFECTED_SYSTEMS: self._execute_isolate_affected_systems,
      ActionType.UPDATE_STATUS_PAGE: self._execute_update_status_page,
      ActionType.NOTIFY_USERS: self._execute_notify_users,
      ActionType.SEND_ALERTS: self._execute_send_alerts,
      ActionType.DOCUMENT_ACTIONS: self._execute_document_actions
    }
  
  def select_recovery_strategy(self, failure: CategorizedFailure) -> Optional[RecoveryStrategy]:
    """
    Select the most appropriate recovery strategy for a categorized failure.
    
    Args:
      failure: Categorized failure to find strategy for
      
    Returns:
      RecoveryStrategy: Best matching strategy, or None if no match found
    """
    
    matching_strategies = []
    
    for strategy in self.strategies.values():
      # Check if strategy applies to this failure
      score = 0.0
      
      # Match failure type (highest weight)
      if failure.failure_type in strategy.failure_types:
        score += 3.0
      
      # Match severity level
      if failure.severity in strategy.severity_levels:
        score += 2.0
      
      # Match component types
      component_matches = len(set(failure.affected_components) & set(strategy.component_types))
      if component_matches > 0:
        score += min(2.0, component_matches * 0.5)
      
      # Match environment
      if failure.context.environment in strategy.environments:
        score += 1.0
      
      # Consider strategy success rate
      score += strategy.success_rate
      
      if score > 0:
        matching_strategies.append((strategy, score))
    
    if not matching_strategies:
      self.logger.warning(f"No matching recovery strategy found for failure {failure.failure_id}")
      return None
    
    # Sort by score and return best match
    matching_strategies.sort(key=lambda x: x[1], reverse=True)
    best_strategy = matching_strategies[0][0]
    
    self.logger.info(f"Selected recovery strategy '{best_strategy.name}' for failure {failure.failure_id}")
    return best_strategy
  
  def execute_recovery_strategy(self, 
                              failure: CategorizedFailure,
                              strategy: Optional[RecoveryStrategy] = None,
                              dry_run: bool = False) -> DecisionPath:
    """
    Execute a recovery strategy for a categorized failure.
    
    Args:
      failure: Categorized failure to recover from
      strategy: Specific strategy to use (auto-selected if None)
      dry_run: If True, simulate execution without taking real actions
      
    Returns:
      DecisionPath: Execution path with results and reasoning
    """
    
    if strategy is None:
      strategy = self.select_recovery_strategy(failure)
      if strategy is None:
        # Create a failed execution path
        path = DecisionPath(
          path_id=str(uuid.uuid4()),
          failure_id=failure.failure_id,
          start_time=datetime.now(),
          final_result=DecisionResult.FAILURE,
          success=False,
          error_message="No matching recovery strategy found"
        )
        path.end_time = datetime.now()
        return path
    
    # Create execution path
    path = DecisionPath(
      path_id=str(uuid.uuid4()),
      failure_id=failure.failure_id,
      start_time=datetime.now()
    )
    
    self.active_executions[path.path_id] = path
    
    try:
      self.logger.info(f"Starting recovery execution for failure {failure.failure_id} "
                      f"using strategy '{strategy.name}' (dry_run={dry_run})")
      
      # Execute decision tree starting from root node
      result = self._execute_decision_node(
        strategy=strategy,
        node_id=strategy.root_node_id,
        failure=failure,
        path=path,
        dry_run=dry_run
      )
      
      path.final_result = result
      path.success = (result == DecisionResult.SUCCESS)
      path.end_time = datetime.now()
      
      # Calculate execution time
      if path.end_time and path.start_time:
        path.total_execution_time = (path.end_time - path.start_time).total_seconds()
      
      self.logger.info(f"Recovery execution completed for {failure.failure_id}: "
                      f"{result.value} (duration: {path.total_execution_time:.1f}s)")
      
    except Exception as e:
      self.logger.error(f"Recovery execution failed for {failure.failure_id}: {e}")
      path.final_result = DecisionResult.FAILURE
      path.success = False
      path.error_message = str(e)
      path.end_time = datetime.now()
      if path.end_time and path.start_time:
        path.total_execution_time = (path.end_time - path.start_time).total_seconds()
    
    finally:
      # Move from active to history
      if path.path_id in self.active_executions:
        del self.active_executions[path.path_id]
      self.execution_history.append(path)
      
      # Update statistics
      self._update_execution_statistics(path, strategy)
    
    return path
  
  def _execute_decision_node(self,
                           strategy: RecoveryStrategy,
                           node_id: str,
                           failure: CategorizedFailure,
                           path: DecisionPath,
                           dry_run: bool = False,
                           depth: int = 0) -> DecisionResult:
    """Execute a single decision node and follow the appropriate path."""
    
    if depth > 20:  # Prevent infinite recursion
      self.logger.error(f"Maximum decision tree depth exceeded at node {node_id}")
      return DecisionResult.FAILURE
    
    if node_id not in strategy.nodes:
      self.logger.error(f"Decision node {node_id} not found in strategy {strategy.strategy_id}")
      return DecisionResult.FAILURE
    
    node = strategy.nodes[node_id]
    path.nodes_visited.append(node_id)
    
    self.logger.debug(f"Executing decision node: {node.name} ({node.node_type.value})")
    
    try:
      if node.node_type == DecisionNodeType.CONDITION:
        # Evaluate condition and follow appropriate branch
        condition_result = self._evaluate_condition(node.condition, failure, dry_run)
        
        reasoning = f"Condition '{node.name}': {condition_result}"
        path.decision_reasoning.append(reasoning)
        
        if condition_result:
          next_node = node.success_node
        else:
          next_node = node.failure_node
        
        if next_node:
          return self._execute_decision_node(strategy, next_node, failure, path, dry_run, depth + 1)
        else:
          return DecisionResult.SUCCESS if condition_result else DecisionResult.FAILURE
      
      elif node.node_type == DecisionNodeType.ACTION:
        # Execute action and follow appropriate branch
        action_result = self._execute_action(node, failure, path, dry_run)
        
        reasoning = f"Action '{node.name}': {action_result.value}"
        path.decision_reasoning.append(reasoning)
        
        if action_result == DecisionResult.SUCCESS:
          path.actions_successful += 1
          next_node = node.success_node
        else:
          path.actions_failed += 1
          next_node = node.failure_node
        
        if next_node:
          return self._execute_decision_node(strategy, next_node, failure, path, dry_run, depth + 1)
        else:
          return action_result
      
      elif node.node_type == DecisionNodeType.GATE:
        # Handle approval gates
        if node.requires_approval and not dry_run:
          approval_result = self._execute_action(node, failure, path, dry_run)
          if approval_result != DecisionResult.SUCCESS:
            return DecisionResult.REQUIRES_APPROVAL
        
        # Continue with action execution
        action_result = self._execute_action(node, failure, path, dry_run)
        
        reasoning = f"Gate '{node.name}': {action_result.value}"
        path.decision_reasoning.append(reasoning)
        
        if action_result == DecisionResult.SUCCESS:
          path.actions_successful += 1
          next_node = node.success_node
        else:
          path.actions_failed += 1
          next_node = node.failure_node
        
        if next_node:
          return self._execute_decision_node(strategy, next_node, failure, path, dry_run, depth + 1)
        else:
          return action_result
      
      elif node.node_type == DecisionNodeType.ROUTE:
        # Route to different branches based on conditions
        # This is a simplified implementation - could be extended for complex routing
        if node.children:
          next_node = node.children[0]  # Take first child for simplicity
          return self._execute_decision_node(strategy, next_node, failure, path, dry_run, depth + 1)
        else:
          return DecisionResult.SUCCESS
      
      elif node.node_type == DecisionNodeType.PARALLEL:
        # Execute multiple branches in parallel (simplified sequential execution for now)
        results = []
        for child_node_id in node.children:
          result = self._execute_decision_node(strategy, child_node_id, failure, path, dry_run, depth + 1)
          results.append(result)
        
        # Return success if any branch succeeded
        if any(result == DecisionResult.SUCCESS for result in results):
          return DecisionResult.SUCCESS
        else:
          return DecisionResult.FAILURE
      
      elif node.node_type == DecisionNodeType.LOOP:
        # Execute loop until condition is met or max iterations reached
        max_iterations = node.action_params.get("max_iterations", 3) if node.action_params else 3
        
        for iteration in range(max_iterations):
          if node.condition:
            condition_result = self._evaluate_condition(node.condition, failure, dry_run)
            if condition_result:
              break  # Loop condition met
          
          # Execute loop body
          if node.children:
            for child_node_id in node.children:
              result = self._execute_decision_node(strategy, child_node_id, failure, path, dry_run, depth + 1)
              if result != DecisionResult.SUCCESS:
                return result
        
        return DecisionResult.SUCCESS
      
      else:
        self.logger.error(f"Unknown node type: {node.node_type}")
        return DecisionResult.FAILURE
    
    except Exception as e:
      self.logger.error(f"Error executing node {node_id}: {e}")
      return DecisionResult.FAILURE
  
  def _evaluate_condition(self, condition: Dict[str, Any], failure: CategorizedFailure, dry_run: bool) -> bool:
    """Evaluate a condition node."""
    
    if not condition:
      return True
    
    check_type = condition.get("check", "")
    
    if dry_run:
      # In dry run mode, simulate condition results
      return True  # Assume conditions pass for simulation
    
    # Implement actual condition checks
    if check_type == "infrastructure_health":
      return self._check_infrastructure_health(failure)
    elif check_type == "resource_utilization":
      threshold = condition.get("threshold", 90)
      return self._check_resource_utilization(failure, threshold)
    elif check_type == "application_health":
      return self._check_application_health(failure)
    elif check_type == "database_health":
      return self._check_database_health(failure)
    elif check_type == "database_connectivity":
      return self._check_database_connectivity(failure)
    elif check_type == "configuration_validation":
      return self._check_configuration_validation(failure)
    elif check_type == "network_health":
      return self._check_network_health(failure)
    elif check_type == "dns_resolution":
      return self._check_dns_resolution(failure)
    elif check_type == "load_balancer_health":
      return self._check_load_balancer_health(failure)
    elif check_type == "security_status":
      return self._check_security_status(failure)
    elif check_type == "recent_deployment":
      timeframe = condition.get("timeframe", "2h")
      return self._check_recent_deployment(failure, timeframe)
    elif check_type == "error_analysis":
      return self._analyze_error_patterns(failure)
    else:
      self.logger.warning(f"Unknown condition check type: {check_type}")
      return False
  
  def _execute_action(self, node: DecisionNode, failure: CategorizedFailure, path: DecisionPath, dry_run: bool) -> DecisionResult:
    """Execute an action node."""
    
    if not node.action:
      self.logger.error(f"No action specified for node {node.node_id}")
      return DecisionResult.FAILURE
    
    action_info = {
      "node_id": node.node_id,
      "action": node.action.value,
      "parameters": node.action_params or {},
      "timestamp": datetime.now().isoformat(),
      "dry_run": dry_run
    }
    
    try:
      if dry_run:
        # Simulate action execution
        self.logger.info(f"[DRY RUN] Executing action: {node.action.value}")
        action_info["result"] = "simulated_success"
        action_info["duration"] = 1.0  # Simulated duration
        path.actions_executed.append(action_info)
        return DecisionResult.SUCCESS
      
      # Execute actual action
      executor = self.action_executors.get(node.action)
      if not executor:
        self.logger.error(f"No executor found for action: {node.action.value}")
        return DecisionResult.FAILURE
      
      start_time = time.time()
      result = executor(node.action_params or {}, failure)
      duration = time.time() - start_time
      
      action_info["result"] = result.value if isinstance(result, DecisionResult) else str(result)
      action_info["duration"] = duration
      path.actions_executed.append(action_info)
      
      self.logger.info(f"Action {node.action.value} completed: {result}")
      return result if isinstance(result, DecisionResult) else DecisionResult.SUCCESS
    
    except Exception as e:
      self.logger.error(f"Action {node.action.value} failed: {e}")
      action_info["result"] = f"error: {str(e)}"
      action_info["duration"] = 0.0
      path.actions_executed.append(action_info)
      return DecisionResult.FAILURE
  
  # Condition check implementations (simplified for demonstration)
  def _check_infrastructure_health(self, failure: CategorizedFailure) -> bool:
    """Check if infrastructure is healthy."""
    # Implement actual infrastructure health checks
    return True
  
  def _check_resource_utilization(self, failure: CategorizedFailure, threshold: float) -> bool:
    """Check if resource utilization is below threshold."""
    # Implement actual resource utilization checks
    return False  # Assume resources are over threshold
  
  def _check_application_health(self, failure: CategorizedFailure) -> bool:
    """Check if application is healthy."""
    # Implement actual application health checks
    return True
  
  def _check_database_health(self, failure: CategorizedFailure) -> bool:
    """Check if database is healthy."""
    # Implement actual database health checks
    return True
  
  def _check_database_connectivity(self, failure: CategorizedFailure) -> bool:
    """Check database connectivity."""
    # Implement actual database connectivity checks
    return False  # Assume connectivity issues
  
  def _check_configuration_validation(self, failure: CategorizedFailure) -> bool:
    """Validate configuration files."""
    # Implement actual configuration validation
    return True
  
  def _check_network_health(self, failure: CategorizedFailure) -> bool:
    """Check network health."""
    # Implement actual network health checks
    return True
  
  def _check_dns_resolution(self, failure: CategorizedFailure) -> bool:
    """Check DNS resolution."""
    # Implement actual DNS resolution checks
    return True
  
  def _check_load_balancer_health(self, failure: CategorizedFailure) -> bool:
    """Check load balancer health."""
    # Implement actual load balancer health checks
    return True
  
  def _check_security_status(self, failure: CategorizedFailure) -> bool:
    """Check security status."""
    # Implement actual security status checks
    return True
  
  def _check_recent_deployment(self, failure: CategorizedFailure, timeframe: str) -> bool:
    """Check if there was a recent deployment."""
    # Implement actual deployment history check
    return True  # Assume recent deployment
  
  def _analyze_error_patterns(self, failure: CategorizedFailure) -> bool:
    """Analyze error patterns."""
    # Implement actual error pattern analysis
    return True
  
  # Action executor implementations (simplified for demonstration)
  def _execute_restart_service(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute service restart."""
    self.logger.info(f"Restarting service with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_scale_up_resources(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute resource scaling."""
    self.logger.info(f"Scaling up resources with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_clear_cache(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute cache clearing."""
    self.logger.info(f"Clearing cache with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_failover_to_backup(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute failover to backup."""
    self.logger.info(f"Failing over to backup with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_rollback_deployment(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute deployment rollback."""
    self.logger.info(f"Rolling back deployment with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_update_configuration(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute configuration update."""
    self.logger.info(f"Updating configuration with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_restart_infrastructure(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute infrastructure restart."""
    self.logger.info(f"Restarting infrastructure with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_reset_connections(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute connection reset."""
    self.logger.info(f"Resetting connections with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_flush_dns_cache(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute DNS cache flush."""
    self.logger.info(f"Flushing DNS cache with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_notify_team(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute team notification."""
    self.logger.info(f"Notifying team with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_create_incident(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute incident creation."""
    self.logger.info(f"Creating incident with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_escalate_to_management(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute escalation to management."""
    self.logger.info(f"Escalating to management with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_request_approval(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute approval request."""
    self.logger.info(f"Requesting approval with params: {params}")
    return DecisionResult.SUCCESS  # Assume approval granted for demo
  
  def _execute_collect_diagnostics(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute diagnostic collection."""
    self.logger.info(f"Collecting diagnostics with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_enable_debug_logging(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute debug logging enablement."""
    self.logger.info(f"Enabling debug logging with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_capture_metrics(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute metrics capture."""
    self.logger.info(f"Capturing metrics with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_run_health_checks(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute health checks."""
    self.logger.info(f"Running health checks with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_backup_data(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute data backup."""
    self.logger.info(f"Backing up data with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_validate_data_integrity(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute data integrity validation."""
    self.logger.info(f"Validating data integrity with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_reset_security_tokens(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute security token reset."""
    self.logger.info(f"Resetting security tokens with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_isolate_affected_systems(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute system isolation."""
    self.logger.info(f"Isolating affected systems with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_update_status_page(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute status page update."""
    self.logger.info(f"Updating status page with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_notify_users(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute user notification."""
    self.logger.info(f"Notifying users with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_send_alerts(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute alert sending."""
    self.logger.info(f"Sending alerts with params: {params}")
    return DecisionResult.SUCCESS
  
  def _execute_document_actions(self, params: Dict[str, Any], failure: CategorizedFailure) -> DecisionResult:
    """Execute action documentation."""
    self.logger.info(f"Documenting actions with params: {params}")
    return DecisionResult.SUCCESS
  
  def _update_execution_statistics(self, path: DecisionPath, strategy: RecoveryStrategy):
    """Update execution statistics."""
    
    self.stats["total_executions"] += 1
    
    if path.success:
      self.stats["successful_recoveries"] += 1
    else:
      self.stats["failed_recoveries"] += 1
    
    # Update average execution time
    if path.total_execution_time:
      total = self.stats["total_executions"]
      current_avg = self.stats["average_execution_time"]
      self.stats["average_execution_time"] = (
        (current_avg * (total - 1) + path.total_execution_time) / total
      )
    
    # Update strategy success rates
    strategy_id = strategy.strategy_id
    if strategy_id not in self.stats["strategy_success_rates"]:
      self.stats["strategy_success_rates"][strategy_id] = {"total": 0, "successful": 0}
    
    self.stats["strategy_success_rates"][strategy_id]["total"] += 1
    if path.success:
      self.stats["strategy_success_rates"][strategy_id]["successful"] += 1
  
  def get_execution_statistics(self) -> Dict[str, Any]:
    """Get current execution statistics."""
    stats = self.stats.copy()
    
    # Calculate success rate
    if stats["total_executions"] > 0:
      stats["overall_success_rate"] = stats["successful_recoveries"] / stats["total_executions"]
    else:
      stats["overall_success_rate"] = 0.0
    
    # Calculate strategy success rates
    for strategy_id, strategy_stats in stats["strategy_success_rates"].items():
      if strategy_stats["total"] > 0:
        strategy_stats["success_rate"] = strategy_stats["successful"] / strategy_stats["total"]
      else:
        strategy_stats["success_rate"] = 0.0
    
    return stats
  
  def export_decision_path(self, path: DecisionPath, format: str = "json") -> str:
    """Export decision path in specified format."""
    
    if format.lower() == "json":
      path_dict = asdict(path)
      
      # Handle datetime serialization
      if path_dict["start_time"]:
        path_dict["start_time"] = path.start_time.isoformat()
      if path_dict["end_time"]:
        path_dict["end_time"] = path.end_time.isoformat()
      if path_dict["final_result"]:
        path_dict["final_result"] = path.final_result.value
      
      return json.dumps(path_dict, indent=2)
    
    elif format.lower() == "yaml":
      try:
        import yaml
        path_dict = asdict(path)
        
        if path_dict["start_time"]:
          path_dict["start_time"] = path.start_time.isoformat()
        if path_dict["end_time"]:
          path_dict["end_time"] = path.end_time.isoformat()
        if path_dict["final_result"]:
          path_dict["final_result"] = path.final_result.value
        
        return yaml.dump(path_dict, default_flow_style=False)
      
      except ImportError:
        return "PyYAML not available for YAML export"
    
    else:
      return f"Unsupported export format: {format}"


if __name__ == "__main__":
  # Example usage and testing
  logging.basicConfig(level=logging.INFO)
  
  # Import required modules for testing
  from failure_categorizer import FailureCategorizer, FailureContext
  
  # Create categorizer and decision tree engine
  categorizer = FailureCategorizer()
  engine = DecisionTreeEngine()
  
  # Example failure scenario
  error_messages = [
    "Connection refused to database server",
    "SQLAlchemy connection pool exhausted"
  ]
  
  log_entries = [
    "2024-01-15T10:00:00 ERROR: Database connection failed after 3 retries",
    "2024-01-15T10:00:05 ERROR: Connection pool size exceeded maximum limit"
  ]
  
  metrics = {
    "db_connection_errors": 15.0,
    "db_response_time": 8000.0,
    "error_rate": 25.0
  }
  
  status_codes = [500, 503]
  
  context = FailureContext(
    environment="production",
    timestamp=datetime.now(),
    affected_users=1000,
    error_rate=25.0
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
  print(f"Affected Components: {[c.value for c in failure.affected_components]}")
  print(f"Recovery Complexity: {failure.recovery_complexity.value}")
  
  # Execute recovery strategy
  print("\n=== Recovery Execution ===")
  path = engine.execute_recovery_strategy(failure, dry_run=True)
  
  print(f"Execution Result: {path.final_result.value if path.final_result else 'None'}")
  print(f"Success: {path.success}")
  print(f"Duration: {path.total_execution_time:.1f}s")
  print(f"Actions Successful: {path.actions_successful}")
  print(f"Actions Failed: {path.actions_failed}")
  
  print("\n=== Decision Path ===")
  for i, reasoning in enumerate(path.decision_reasoning, 1):
    print(f"{i}. {reasoning}")
  
  print("\n=== Actions Executed ===")
  for action in path.actions_executed:
    print(f"- {action['action']} ({action['result']}) [{action['duration']:.1f}s]")
  
  print(f"\n=== Execution Statistics ===")
  stats = engine.get_execution_statistics()
  print(f"Total Executions: {stats['total_executions']}")
  print(f"Success Rate: {stats['overall_success_rate']:.1%}")
  print(f"Average Duration: {stats['average_execution_time']:.1f}s")