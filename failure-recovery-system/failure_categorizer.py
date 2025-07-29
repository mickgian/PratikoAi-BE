#!/usr/bin/env python3
"""
Sophisticated Failure Categorization System
==========================================

This module provides a comprehensive system for categorizing deployment failures
based on multiple dimensions: type, severity, component impact, and recovery complexity.

The categorization enables intelligent decision-making for automated recovery strategies.
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import re


class FailureType(Enum):
  """Primary failure categories based on root cause analysis."""
  
  # Infrastructure failures - problems with underlying systems
  INFRASTRUCTURE = "infrastructure"
  
  # Configuration failures - incorrect settings or environment issues
  CONFIGURATION = "configuration"
  
  # Dependency failures - external service or library issues
  DEPENDENCY = "dependency"
  
  # Resource failures - insufficient compute, memory, storage, or network
  RESOURCE = "resource"
  
  # Application failures - bugs in application code
  APPLICATION = "application"
  
  # Data failures - database, migration, or data integrity issues
  DATA = "data"
  
  # Security failures - authentication, authorization, or security violations
  SECURITY = "security"
  
  # Network failures - connectivity, DNS, or networking issues
  NETWORK = "network"
  
  # Timing failures - race conditions, timeouts, or synchronization issues
  TIMING = "timing"
  
  # Human errors - manual intervention mistakes or process violations
  HUMAN_ERROR = "human_error"


class FailureSeverity(Enum):
  """Severity levels based on business impact and urgency of resolution."""
  
  # Critical: Complete service outage, data loss risk, security breach
  CRITICAL = "critical"
  
  # High: Major functionality broken, significant user impact
  HIGH = "high"
  
  # Medium: Some features broken, moderate user impact
  MEDIUM = "medium"
  
  # Low: Minor issues, minimal user impact
  LOW = "low"
  
  # Info: Non-impacting issues, informational only
  INFO = "info"


class ComponentType(Enum):
  """System components that can be affected by failures."""
  
  FRONTEND = "frontend"
  BACKEND = "backend"
  DATABASE = "database"
  API_GATEWAY = "api_gateway"
  LOAD_BALANCER = "load_balancer"
  CACHE = "cache"
  MESSAGE_QUEUE = "message_queue"
  FILE_STORAGE = "file_storage"
  CDN = "cdn"
  MONITORING = "monitoring"
  LOGGING = "logging"
  AUTHENTICATION = "authentication"
  EXTERNAL_API = "external_api"


class RecoveryComplexity(Enum):
  """Complexity level for recovery operations."""
  
  # Automatic: Can be resolved by automated systems without human intervention
  AUTOMATIC = "automatic"
  
  # Semi_automatic: Requires minimal human oversight or approval
  SEMI_AUTOMATIC = "semi_automatic"
  
  # Manual: Requires significant human intervention and expertise
  MANUAL = "manual"
  
  # Complex: Requires coordination across multiple teams or systems
  COMPLEX = "complex"
  
  # Emergency: Requires immediate expert attention and possibly external help
  EMERGENCY = "emergency"


@dataclass
class FailureContext:
  """Additional context information about the failure."""
  
  environment: str  # development, staging, production
  timestamp: datetime
  affected_users: Optional[int] = None
  affected_regions: List[str] = None
  deployment_phase: Optional[str] = None  # build, test, deploy, post_deploy
  error_rate: Optional[float] = None
  response_time_degradation: Optional[float] = None
  resource_utilization: Dict[str, float] = None
  
  def __post_init__(self):
    if self.affected_regions is None:
      self.affected_regions = []
    if self.resource_utilization is None:
      self.resource_utilization = {}


@dataclass
class FailureSignature:
  """Unique signature identifying specific failure patterns."""
  
  error_patterns: List[str]  # Regex patterns for error messages
  log_patterns: List[str]    # Patterns in log files
  metric_thresholds: Dict[str, Tuple[str, float]]  # metric_name: (operator, threshold)
  status_codes: List[int]    # HTTP status codes associated with failure
  component_states: Dict[ComponentType, str]  # Expected component states


@dataclass
class CategorizedFailure:
  """Complete failure categorization with all metadata."""
  
  failure_id: str
  failure_type: FailureType
  severity: FailureSeverity
  affected_components: Set[ComponentType]
  recovery_complexity: RecoveryComplexity
  context: FailureContext
  signature: Optional[FailureSignature] = None
  
  # Decision rationale
  categorization_reasoning: str = ""
  confidence_score: float = 0.0
  
  # Recovery guidance
  recommended_actions: List[str] = None
  estimated_recovery_time: Optional[int] = None  # minutes
  requires_rollback: bool = False
  data_integrity_risk: bool = False
  
  def __post_init__(self):
    if self.recommended_actions is None:
      self.recommended_actions = []
    
    # Convert set to list for JSON serialization
    if isinstance(self.affected_components, set):
      self.affected_components = list(self.affected_components)


class FailureCategorizer:
  """
  Sophisticated failure categorization engine that analyzes deployment failures
  and categorizes them across multiple dimensions for intelligent recovery decisions.
  """
  
  def __init__(self, config_path: Optional[Path] = None):
    self.logger = logging.getLogger(__name__)
    self.config_path = config_path or Path(__file__).parent / "failure_categorization_config.yaml"
    
    # Load configuration and failure patterns
    self.config = self._load_configuration()
    self.failure_patterns = self._load_failure_patterns()
    
    # Initialize categorization rules
    self._initialize_categorization_rules()
    
    # Statistics tracking
    self.categorization_stats = {
      "total_categorizations": 0,
      "by_type": {},
      "by_severity": {},
      "average_confidence": 0.0
    }
  
  def _load_configuration(self) -> Dict[str, Any]:
    """Load categorization configuration from file."""
    # Default configuration if file doesn't exist
    default_config = {
      "severity_scoring": {
        "user_impact_weight": 0.3,
        "business_impact_weight": 0.3,
        "recovery_time_weight": 0.2,
        "data_risk_weight": 0.2
      },
      "component_dependencies": {
        "frontend": ["api_gateway", "cdn"],
        "backend": ["database", "cache", "message_queue"],
        "api_gateway": ["backend", "authentication"],
        "database": [],
        "cache": [],
        "authentication": ["database"]
      },
      "environment_risk_multipliers": {
        "production": 2.0,
        "staging": 1.2,
        "development": 0.8
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
  
  def _load_failure_patterns(self) -> Dict[FailureType, List[FailureSignature]]:
    """Load known failure patterns for automatic categorization."""
    patterns = {
      FailureType.INFRASTRUCTURE: [
        FailureSignature(
          error_patterns=[
            r"connection refused",
            r"host unreachable",
            r"service unavailable",
            r"502 bad gateway",
            r"503 service unavailable"
          ],
          log_patterns=[
            r"container failed to start",
            r"pod scheduling failed",
            r"node not ready"
          ],
          metric_thresholds={
            "cpu_utilization": (">", 95.0),
            "memory_utilization": (">", 95.0),
            "disk_utilization": (">", 98.0)
          },
          status_codes=[502, 503, 504],
          component_states={}
        )
      ],
      
      FailureType.CONFIGURATION: [
        FailureSignature(
          error_patterns=[
            r"configuration error",
            r"invalid configuration",
            r"missing environment variable",
            r"permission denied",
            r"file not found"
          ],
          log_patterns=[
            r"config validation failed",
            r"environment variable .* not set",
            r"invalid yaml syntax"
          ],
          metric_thresholds={},
          status_codes=[400, 401, 403, 404],
          component_states={}
        )
      ],
      
      FailureType.DEPENDENCY: [
        FailureSignature(
          error_patterns=[
            r"dependency not found",
            r"module not found",
            r"import error",
            r"external service timeout",
            r"api rate limit exceeded"
          ],
          log_patterns=[
            r"failed to connect to external service",
            r"dependency health check failed",
            r"third.party api error"
          ],
          metric_thresholds={
            "external_api_error_rate": (">", 10.0),
            "dependency_response_time": (">", 30000)
          },
          status_codes=[424, 429, 502, 503, 504],
          component_states={}
        )
      ],
      
      FailureType.RESOURCE: [
        FailureSignature(
          error_patterns=[
            r"out of memory",
            r"disk space exceeded",
            r"too many open files",
            r"connection pool exhausted",
            r"quota exceeded"
          ],
          log_patterns=[
            r"oom killed",
            r"no space left on device",
            r"resource quota exceeded"
          ],
          metric_thresholds={
            "memory_utilization": (">", 90.0),
            "disk_utilization": (">", 95.0),
            "cpu_utilization": (">", 90.0),
            "connection_pool_usage": (">", 95.0)
          },
          status_codes=[503, 507],
          component_states={}
        )
      ],
      
      FailureType.APPLICATION: [
        FailureSignature(
          error_patterns=[
            r"null pointer exception",
            r"index out of bounds",
            r"assertion error",
            r"runtime error",
            r"unhandled exception"
          ],
          log_patterns=[
            r"traceback",
            r"stack trace",
            r"fatal error",
            r"segmentation fault"
          ],
          metric_thresholds={
            "error_rate": (">", 5.0),
            "response_time_p99": (">", 10000)
          },
          status_codes=[500, 422],
          component_states={}
        )
      ],
      
      FailureType.DATA: [
        FailureSignature(
          error_patterns=[
            r"database connection failed",
            r"migration failed",
            r"constraint violation",
            r"deadlock detected",
            r"data corruption"
          ],
          log_patterns=[
            r"database error",
            r"sql error",
            r"migration rollback",
            r"constraint failed"
          ],
          metric_thresholds={
            "db_connection_errors": (">", 1.0),
            "db_response_time": (">", 5000)
          },
          status_codes=[409, 422, 500],
          component_states={}
        )
      ],
      
      FailureType.SECURITY: [
        FailureSignature(
          error_patterns=[
            r"authentication failed",
            r"authorization denied",
            r"invalid token",
            r"security violation",
            r"suspicious activity"
          ],
          log_patterns=[
            r"auth failure",
            r"invalid credentials",
            r"access denied",
            r"security alert"
          ],
          metric_thresholds={
            "failed_auth_rate": (">", 10.0)
          },
          status_codes=[401, 403, 418],
          component_states={}
        )
      ],
      
      FailureType.NETWORK: [
        FailureSignature(
          error_patterns=[
            r"network timeout",
            r"dns resolution failed",
            r"connection reset",
            r"network unreachable",
            r"ssl handshake failed"
          ],
          log_patterns=[
            r"network error",
            r"timeout occurred",
            r"connection lost",
            r"dns lookup failed"
          ],
          metric_thresholds={
            "network_latency": (">", 1000),
            "packet_loss": (">", 1.0)
          },
          status_codes=[408, 502, 504],
          component_states={}
        )
      ],
      
      FailureType.TIMING: [
        FailureSignature(
          error_patterns=[
            r"timeout",
            r"deadlock",
            r"race condition",
            r"lock timeout",
            r"synchronization error"
          ],
          log_patterns=[
            r"timeout exceeded",
            r"deadlock detected",
            r"race condition",
            r"lock contention"
          ],
          metric_thresholds={
            "response_time_p95": (">", 30000),
            "lock_wait_time": (">", 10000)
          },
          status_codes=[408, 409, 503],
          component_states={}
        )
      ],
      
      FailureType.HUMAN_ERROR: [
        FailureSignature(
          error_patterns=[
            r"manual intervention required",
            r"deployment aborted by user",
            r"incorrect manual configuration",
            r"user cancelled operation"
          ],
          log_patterns=[
            r"manual deployment step failed",
            r"user intervention",
            r"manual rollback initiated"
          ],
          metric_thresholds={},
          status_codes=[400, 422],
          component_states={}
        )
      ]
    }
    
    return patterns
  
  def _initialize_categorization_rules(self):
    """Initialize the decision rules for failure categorization."""
    self.severity_rules = {
      # Critical severity indicators
      "critical_indicators": [
        "complete service outage",
        "data loss",
        "security breach",
        "production down",
        "database corruption",
        "payment system failure"
      ],
      
      # High severity indicators
      "high_indicators": [
        "major feature broken",
        "api endpoints failing",
        "authentication failure",
        "significant performance degradation",
        "user data access issues"
      ],
      
      # Medium severity indicators
      "medium_indicators": [
        "some features unavailable",
        "non-critical api errors",
        "performance issues",
        "ui rendering problems",
        "cache failures"
      ],
      
      # Low severity indicators
      "low_indicators": [
        "minor ui issues",
        "non-critical warnings",
        "logging issues",
        "minor performance degradation",
        "cosmetic problems"
      ]
    }
    
    self.complexity_rules = {
      RecoveryComplexity.AUTOMATIC: [
        "restart service",
        "clear cache",
        "retry failed operation",
        "scale up resources",
        "failover to backup"
      ],
      
      RecoveryComplexity.SEMI_AUTOMATIC: [
        "configuration update",
        "dependency version rollback",
        "database connection reset",
        "load balancer reconfiguration"
      ],
      
      RecoveryComplexity.MANUAL: [
        "code fix required",
        "manual data correction",
        "infrastructure changes",
        "third-party service coordination"
      ],
      
      RecoveryComplexity.COMPLEX: [
        "multi-system coordination",
        "data migration required",
        "security incident response",
        "cross-team collaboration needed"
      ],
      
      RecoveryComplexity.EMERGENCY: [
        "data corruption detected",
        "security breach confirmed",
        "complete system failure",
        "regulatory compliance violation"
      ]
    }
  
  def categorize_failure(self,
                        error_messages: List[str],
                        log_entries: List[str],
                        metrics: Dict[str, float],
                        status_codes: List[int],
                        context: FailureContext,
                        additional_info: Optional[Dict[str, Any]] = None) -> CategorizedFailure:
    """
    Categorize a deployment failure based on available information.
    
    Args:
      error_messages: List of error messages encountered
      log_entries: Relevant log entries
      metrics: System metrics at time of failure
      status_codes: HTTP status codes observed
      context: Additional context about the failure
      additional_info: Any additional information for categorization
      
    Returns:
      CategorizedFailure: Complete categorization with recommended actions
    """
    
    failure_id = f"failure_{int(time.time() * 1000)}"
    
    # Step 1: Pattern matching for failure type identification
    failure_type, type_confidence = self._identify_failure_type(
      error_messages, log_entries, metrics, status_codes
    )
    
    # Step 2: Severity assessment based on multiple factors
    severity, severity_confidence = self._assess_severity(
      error_messages, log_entries, metrics, context, additional_info
    )
    
    # Step 3: Component impact analysis
    affected_components = self._analyze_component_impact(
      failure_type, error_messages, log_entries, context
    )
    
    # Step 4: Recovery complexity determination
    recovery_complexity = self._determine_recovery_complexity(
      failure_type, severity, affected_components, context
    )
    
    # Step 5: Generate failure signature for future reference
    signature = self._generate_failure_signature(
      error_messages, log_entries, metrics, status_codes
    )
    
    # Step 6: Create reasoning explanation
    reasoning = self._generate_categorization_reasoning(
      failure_type, severity, affected_components, recovery_complexity,
      type_confidence, severity_confidence
    )
    
    # Step 7: Generate recommended actions
    recommended_actions = self._generate_recommended_actions(
      failure_type, severity, affected_components, recovery_complexity, context
    )
    
    # Step 8: Estimate recovery time
    estimated_recovery_time = self._estimate_recovery_time(
      failure_type, severity, recovery_complexity, context
    )
    
    # Step 9: Assess risks
    requires_rollback = self._assess_rollback_requirement(
      failure_type, severity, context
    )
    
    data_integrity_risk = self._assess_data_integrity_risk(
      failure_type, affected_components, error_messages
    )
    
    # Calculate overall confidence score
    overall_confidence = (type_confidence + severity_confidence) / 2
    
    # Create categorized failure
    categorized_failure = CategorizedFailure(
      failure_id=failure_id,
      failure_type=failure_type,
      severity=severity,
      affected_components=affected_components,
      recovery_complexity=recovery_complexity,
      context=context,
      signature=signature,
      categorization_reasoning=reasoning,
      confidence_score=overall_confidence,
      recommended_actions=recommended_actions,
      estimated_recovery_time=estimated_recovery_time,
      requires_rollback=requires_rollback,
      data_integrity_risk=data_integrity_risk
    )
    
    # Update statistics
    self._update_statistics(categorized_failure)
    
    self.logger.info(f"Categorized failure {failure_id}: {failure_type.value} "
                    f"({severity.value}) with {overall_confidence:.2f} confidence")
    
    return categorized_failure
  
  def _identify_failure_type(self,
                           error_messages: List[str],
                           log_entries: List[str],
                           metrics: Dict[str, float],
                           status_codes: List[int]) -> Tuple[FailureType, float]:
    """Identify the primary failure type using pattern matching."""
    
    type_scores = {failure_type: 0.0 for failure_type in FailureType}
    
    # Combine all text for analysis
    all_text = " ".join(error_messages + log_entries).lower()
    
    # Pattern matching against known signatures
    for failure_type, signatures in self.failure_patterns.items():
      for signature in signatures:
        score = 0.0
        
        # Check error patterns
        for pattern in signature.error_patterns:
          if re.search(pattern, all_text, re.IGNORECASE):
            score += 2.0
        
        # Check log patterns
        for pattern in signature.log_patterns:
          if re.search(pattern, all_text, re.IGNORECASE):
            score += 1.5
        
        # Check metric thresholds
        for metric_name, (operator, threshold) in signature.metric_thresholds.items():
          if metric_name in metrics:
            metric_value = metrics[metric_name]
            if ((operator == ">" and metric_value > threshold) or
                (operator == "<" and metric_value < threshold) or
                (operator == "=" and abs(metric_value - threshold) < 0.1)):
              score += 1.0
        
        # Check status codes
        if any(code in signature.status_codes for code in status_codes):
          score += 0.5
        
        type_scores[failure_type] += score
    
    # Find the highest scoring type
    if max(type_scores.values()) == 0:
      # No clear pattern match, use heuristics
      return self._heuristic_type_identification(error_messages, log_entries, metrics)
    
    best_type = max(type_scores, key=type_scores.get)
    max_score = type_scores[best_type]
    
    # Calculate confidence as normalized score
    confidence = min(1.0, max_score / 5.0)  # Normalize to 0-1 range
    
    return best_type, confidence
  
  def _heuristic_type_identification(self,
                                   error_messages: List[str],
                                   log_entries: List[str],
                                   metrics: Dict[str, float]) -> Tuple[FailureType, float]:
    """Fallback heuristic identification when patterns fail."""
    
    all_text = " ".join(error_messages + log_entries).lower()
    
    # Simple keyword-based heuristics
    heuristics = [
      (FailureType.INFRASTRUCTURE, ["container", "pod", "node", "cluster", "k8s", "docker"]),
      (FailureType.CONFIGURATION, ["config", "environment", "variable", "setting", "yaml"]),
      (FailureType.DEPENDENCY, ["import", "module", "package", "dependency", "library"]),
      (FailureType.RESOURCE, ["memory", "cpu", "disk", "quota", "limit", "resource"]),
      (FailureType.APPLICATION, ["exception", "error", "bug", "traceback", "runtime"]),
      (FailureType.DATA, ["database", "sql", "migration", "data", "table", "query"]),
      (FailureType.SECURITY, ["auth", "permission", "token", "credential", "security"]),
      (FailureType.NETWORK, ["network", "connection", "timeout", "dns", "ssl", "tcp"]),
      (FailureType.TIMING, ["timeout", "deadlock", "race", "synchronization", "lock"])
    ]
    
    type_scores = {}
    for failure_type, keywords in heuristics:
      score = sum(1 for keyword in keywords if keyword in all_text)
      if score > 0:
        type_scores[failure_type] = score
    
    if not type_scores:
      return FailureType.APPLICATION, 0.3  # Default fallback
    
    best_type = max(type_scores, key=type_scores.get)
    confidence = min(0.7, type_scores[best_type] / 3.0)  # Lower confidence for heuristics
    
    return best_type, confidence
  
  def _assess_severity(self,
                      error_messages: List[str],
                      log_entries: List[str],
                      metrics: Dict[str, float],
                      context: FailureContext,
                      additional_info: Optional[Dict[str, Any]]) -> Tuple[FailureSeverity, float]:
    """Assess failure severity based on multiple factors."""
    
    all_text = " ".join(error_messages + log_entries).lower()
    
    # Initialize severity score
    severity_score = 0.0
    confidence_factors = []
    
    # Factor 1: Environment impact (production is more critical)
    env_multiplier = self.config["environment_risk_multipliers"].get(context.environment, 1.0)
    severity_score *= env_multiplier
    confidence_factors.append(0.8)  # High confidence in environment factor
    
    # Factor 2: User impact
    if context.affected_users:
      if context.affected_users > 10000:
        severity_score += 4.0
      elif context.affected_users > 1000:
        severity_score += 3.0
      elif context.affected_users > 100:
        severity_score += 2.0
      else:
        severity_score += 1.0
      confidence_factors.append(0.9)
    
    # Factor 3: Error rate impact
    if context.error_rate:
      if context.error_rate > 50:
        severity_score += 4.0
      elif context.error_rate > 20:
        severity_score += 3.0
      elif context.error_rate > 5:
        severity_score += 2.0
      else:
        severity_score += 1.0
      confidence_factors.append(0.8)
    
    # Factor 4: Response time degradation
    if context.response_time_degradation:
      if context.response_time_degradation > 500:  # 500% increase
        severity_score += 3.0
      elif context.response_time_degradation > 200:
        severity_score += 2.0
      elif context.response_time_degradation > 50:
        severity_score += 1.0
      confidence_factors.append(0.7)
    
    # Factor 5: Keyword-based severity indicators
    for severity_level, indicators in self.severity_rules.items():
      if severity_level == "critical_indicators":
        for indicator in indicators:
          if indicator in all_text:
            severity_score += 5.0
            confidence_factors.append(0.9)
      elif severity_level == "high_indicators":
        for indicator in indicators:
          if indicator in all_text:
            severity_score += 3.0
            confidence_factors.append(0.8)
      elif severity_level == "medium_indicators":
        for indicator in indicators:
          if indicator in all_text:
            severity_score += 2.0
            confidence_factors.append(0.7)
      elif severity_level == "low_indicators":
        for indicator in indicators:
          if indicator in all_text:
            severity_score += 1.0
            confidence_factors.append(0.6)
    
    # Convert score to severity level
    if severity_score >= 8.0:
      severity = FailureSeverity.CRITICAL
    elif severity_score >= 6.0:
      severity = FailureSeverity.HIGH
    elif severity_score >= 3.0:
      severity = FailureSeverity.MEDIUM
    elif severity_score >= 1.0:
      severity = FailureSeverity.LOW
    else:
      severity = FailureSeverity.INFO
    
    # Calculate confidence as average of contributing factors
    confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    return severity, confidence
  
  def _analyze_component_impact(self,
                              failure_type: FailureType,
                              error_messages: List[str],
                              log_entries: List[str],
                              context: FailureContext) -> Set[ComponentType]:
    """Analyze which system components are affected by the failure."""
    
    affected_components = set()
    all_text = " ".join(error_messages + log_entries).lower()
    
    # Component detection patterns
    component_patterns = {
      ComponentType.FRONTEND: ["frontend", "ui", "react", "vue", "angular", "javascript", "css", "html"],
      ComponentType.BACKEND: ["backend", "api", "server", "fastapi", "django", "flask", "express"],
      ComponentType.DATABASE: ["database", "db", "sql", "postgres", "mysql", "mongodb", "redis"],
      ComponentType.API_GATEWAY: ["gateway", "proxy", "nginx", "traefik", "envoy", "kong"],
      ComponentType.LOAD_BALANCER: ["load balancer", "lb", "haproxy", "nginx", "aws elb", "alb"],
      ComponentType.CACHE: ["cache", "redis", "memcached", "elasticsearch", "varnish"],
      ComponentType.MESSAGE_QUEUE: ["queue", "kafka", "rabbitmq", "sqs", "pubsub", "nats"],
      ComponentType.FILE_STORAGE: ["storage", "s3", "gcs", "azure blob", "file system", "disk"],
      ComponentType.CDN: ["cdn", "cloudflare", "cloudfront", "fastly", "edge"],
      ComponentType.MONITORING: ["monitoring", "prometheus", "grafana", "datadog", "newrelic"],
      ComponentType.LOGGING: ["logging", "logs", "fluentd", "logstash", "cloudwatch"],
      ComponentType.AUTHENTICATION: ["auth", "login", "jwt", "oauth", "saml", "ldap"],
      ComponentType.EXTERNAL_API: ["external", "third party", "api", "webhook", "integration"]
    }
    
    # Check for component mentions in error messages and logs
    for component, keywords in component_patterns.items():
      if any(keyword in all_text for keyword in keywords):
        affected_components.add(component)
    
    # Infer components based on failure type
    type_component_mapping = {
      FailureType.INFRASTRUCTURE: [ComponentType.BACKEND, ComponentType.DATABASE],
      FailureType.CONFIGURATION: [ComponentType.BACKEND, ComponentType.API_GATEWAY],
      FailureType.DEPENDENCY: [ComponentType.BACKEND, ComponentType.EXTERNAL_API],
      FailureType.RESOURCE: [ComponentType.BACKEND, ComponentType.DATABASE, ComponentType.CACHE],
      FailureType.APPLICATION: [ComponentType.BACKEND, ComponentType.FRONTEND],
      FailureType.DATA: [ComponentType.DATABASE, ComponentType.BACKEND],
      FailureType.SECURITY: [ComponentType.AUTHENTICATION, ComponentType.API_GATEWAY],
      FailureType.NETWORK: [ComponentType.LOAD_BALANCER, ComponentType.CDN, ComponentType.API_GATEWAY],
      FailureType.TIMING: [ComponentType.BACKEND, ComponentType.DATABASE, ComponentType.CACHE]
    }
    
    if failure_type in type_component_mapping:
      affected_components.update(type_component_mapping[failure_type])
    
    # Add dependent components based on configuration
    dependencies = self.config.get("component_dependencies", {})
    additional_components = set()
    
    for component in affected_components:
      component_name = component.value
      if component_name in dependencies:
        for dep in dependencies[component_name]:
          try:
            additional_components.add(ComponentType(dep))
          except ValueError:
            pass  # Invalid component type in configuration
    
    affected_components.update(additional_components)
    
    # Ensure at least one component is identified
    if not affected_components:
      affected_components.add(ComponentType.BACKEND)  # Default assumption
    
    return affected_components
  
  def _determine_recovery_complexity(self,
                                   failure_type: FailureType,
                                   severity: FailureSeverity,
                                   affected_components: Set[ComponentType],
                                   context: FailureContext) -> RecoveryComplexity:
    """Determine the complexity level required for recovery."""
    
    # Base complexity by failure type
    type_complexity_mapping = {
      FailureType.INFRASTRUCTURE: RecoveryComplexity.MANUAL,
      FailureType.CONFIGURATION: RecoveryComplexity.SEMI_AUTOMATIC,
      FailureType.DEPENDENCY: RecoveryComplexity.SEMI_AUTOMATIC,
      FailureType.RESOURCE: RecoveryComplexity.AUTOMATIC,
      FailureType.APPLICATION: RecoveryComplexity.MANUAL,
      FailureType.DATA: RecoveryComplexity.COMPLEX,
      FailureType.SECURITY: RecoveryComplexity.EMERGENCY,
      FailureType.NETWORK: RecoveryComplexity.SEMI_AUTOMATIC,
      FailureType.TIMING: RecoveryComplexity.MANUAL,
      FailureType.HUMAN_ERROR: RecoveryComplexity.MANUAL
    }
    
    base_complexity = type_complexity_mapping.get(failure_type, RecoveryComplexity.MANUAL)
    
    # Adjust based on severity
    if severity == FailureSeverity.CRITICAL:
      if base_complexity in [RecoveryComplexity.AUTOMATIC, RecoveryComplexity.SEMI_AUTOMATIC]:
        return RecoveryComplexity.MANUAL
      elif base_complexity == RecoveryComplexity.MANUAL:
        return RecoveryComplexity.COMPLEX
      else:
        return RecoveryComplexity.EMERGENCY
    
    # Adjust based on environment
    if context.environment == "production":
      complexity_levels = list(RecoveryComplexity)
      current_index = complexity_levels.index(base_complexity)
      if current_index < len(complexity_levels) - 1:
        return complexity_levels[current_index + 1]
    
    # Adjust based on number of affected components
    if len(affected_components) > 3:
      complexity_levels = list(RecoveryComplexity)
      current_index = complexity_levels.index(base_complexity)
      if current_index < len(complexity_levels) - 1:
        return complexity_levels[current_index + 1]
    
    return base_complexity
  
  def _generate_failure_signature(self,
                                error_messages: List[str],
                                log_entries: List[str],
                                metrics: Dict[str, float],
                                status_codes: List[int]) -> FailureSignature:
    """Generate a signature for this specific failure pattern."""
    
    # Extract key error patterns
    error_patterns = []
    for msg in error_messages:
      # Normalize error message to create a pattern
      pattern = re.sub(r'\d+', 'NUM', msg.lower())
      pattern = re.sub(r'[a-f0-9-]{36}', 'UUID', pattern)  # UUIDs
      pattern = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP', pattern)  # IP addresses
      error_patterns.append(pattern)
    
    # Extract log patterns
    log_patterns = []
    for entry in log_entries:
      pattern = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'TIMESTAMP', entry.lower())
      pattern = re.sub(r'\d+', 'NUM', pattern)
      log_patterns.append(pattern)
    
    # Create metric thresholds based on current values
    metric_thresholds = {}
    for metric_name, value in metrics.items():
      if value > 80:  # High values suggest thresholds
        metric_thresholds[metric_name] = (">", value * 0.9)
      elif value < 10:  # Low values suggest thresholds
        metric_thresholds[metric_name] = ("<", value * 1.1)
    
    return FailureSignature(
      error_patterns=error_patterns[:5],  # Limit to top 5 patterns
      log_patterns=log_patterns[:5],
      metric_thresholds=metric_thresholds,
      status_codes=list(set(status_codes)),  # Remove duplicates
      component_states={}
    )
  
  def _generate_categorization_reasoning(self,
                                       failure_type: FailureType,
                                       severity: FailureSeverity,
                                       affected_components: Set[ComponentType],
                                       recovery_complexity: RecoveryComplexity,
                                       type_confidence: float,
                                       severity_confidence: float) -> str:
    """Generate human-readable reasoning for the categorization decision."""
    
    reasoning_parts = []
    
    # Failure type reasoning
    reasoning_parts.append(
      f"Categorized as {failure_type.value.upper()} failure with {type_confidence:.1%} confidence "
      f"based on error pattern analysis and symptom matching."
    )
    
    # Severity reasoning
    reasoning_parts.append(
      f"Assessed as {severity.value.upper()} severity with {severity_confidence:.1%} confidence "
      f"considering environmental impact, user affected count, and business criticality."
    )
    
    # Component impact reasoning
    component_names = [comp.value.replace('_', ' ').title() for comp in affected_components]
    reasoning_parts.append(
      f"Identified {len(affected_components)} affected components: {', '.join(component_names)}. "
      f"Impact analysis considered direct failures and downstream dependencies."
    )
    
    # Recovery complexity reasoning
    reasoning_parts.append(
      f"Recovery complexity determined as {recovery_complexity.value.upper()} based on "
      f"failure type characteristics, severity level, and operational requirements."
    )
    
    return " ".join(reasoning_parts)
  
  def _generate_recommended_actions(self,
                                  failure_type: FailureType,
                                  severity: FailureSeverity,
                                  affected_components: Set[ComponentType],
                                  recovery_complexity: RecoveryComplexity,
                                  context: FailureContext) -> List[str]:
    """Generate specific recommended actions for recovery."""
    
    actions = []
    
    # Type-specific actions
    type_actions = {
      FailureType.INFRASTRUCTURE: [
        "Check container/pod status and restart if necessary",
        "Verify infrastructure health and resource availability",
        "Scale up resources if capacity limits are reached",
        "Check for node failures and reschedule workloads"
      ],
      FailureType.CONFIGURATION: [
        "Validate configuration files for syntax errors",
        "Check environment variable settings",
        "Verify service connectivity and endpoint configurations",
        "Review recent configuration changes and revert if necessary"
      ],
      FailureType.DEPENDENCY: [
        "Check external service status and connectivity",
        "Verify API keys and authentication credentials",
        "Implement circuit breaker or fallback mechanisms",
        "Contact third-party service providers if needed"
      ],
      FailureType.RESOURCE: [
        "Increase memory or CPU allocations",
        "Clear disk space or expand storage capacity",
        "Optimize database queries and connection pools",
        "Implement resource monitoring and alerting"
      ],
      FailureType.APPLICATION: [
        "Review recent code changes and consider rollback",
        "Analyze application logs for specific error details",
        "Deploy hotfix if root cause is identified",
        "Implement additional error handling and logging"
      ],
      FailureType.DATA: [
        "Check database connectivity and status",
        "Verify data integrity and run consistency checks",
        "Review recent migrations and consider rollback",
        "Implement database backup and recovery procedures"
      ],
      FailureType.SECURITY: [
        "Immediately isolate affected systems",
        "Review authentication and authorization logs",
        "Reset compromised credentials",
        "Conduct security incident response procedures"
      ],
      FailureType.NETWORK: [
        "Check network connectivity and DNS resolution",
        "Verify firewall rules and security group settings",
        "Test load balancer configuration and health checks",
        "Implement network monitoring and diagnostics"
      ],
      FailureType.TIMING: [
        "Increase timeout values for critical operations",
        "Review and optimize database query performance",
        "Implement proper synchronization mechanisms",
        "Add distributed locking where appropriate"
      ],
      FailureType.HUMAN_ERROR: [
        "Review deployment procedures and documentation",
        "Implement additional approval steps for critical changes",
        "Provide additional training for deployment procedures",
        "Enhance automation to reduce manual intervention"
      ]
    }
    
    actions.extend(type_actions.get(failure_type, []))
    
    # Severity-specific actions
    if severity in [FailureSeverity.CRITICAL, FailureSeverity.HIGH]:
      actions.extend([
        "Initiate incident response procedures",
        "Notify stakeholders and management",
        "Consider immediate rollback to last known good state",
        "Activate emergency response team"
      ])
    
    # Environment-specific actions
    if context.environment == "production":
      actions.extend([
        "Follow production change management procedures",
        "Document all actions taken for post-incident review",
        "Consider maintenance window for complex fixes",
        "Prepare communication for affected users"
      ])
    
    # Component-specific actions
    if ComponentType.DATABASE in affected_components:
      actions.extend([
        "Check database connection pools and active connections",
        "Verify database server resources and performance",
        "Review recent database changes and migrations"
      ])
    
    if ComponentType.FRONTEND in affected_components:
      actions.extend([
        "Check CDN status and cache invalidation",
        "Verify frontend build and deployment artifacts",
        "Test user-facing functionality across different browsers"
      ])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_actions = []
    for action in actions:
      if action not in seen:
        seen.add(action)
        unique_actions.append(action)
    
    return unique_actions
  
  def _estimate_recovery_time(self,
                            failure_type: FailureType,
                            severity: FailureSeverity,
                            recovery_complexity: RecoveryComplexity,
                            context: FailureContext) -> int:
    """Estimate recovery time in minutes."""
    
    # Base estimates by complexity
    complexity_time_mapping = {
      RecoveryComplexity.AUTOMATIC: 5,
      RecoveryComplexity.SEMI_AUTOMATIC: 15,
      RecoveryComplexity.MANUAL: 60,
      RecoveryComplexity.COMPLEX: 180,
      RecoveryComplexity.EMERGENCY: 360
    }
    
    base_time = complexity_time_mapping.get(recovery_complexity, 60)
    
    # Adjust for failure type
    type_multipliers = {
      FailureType.INFRASTRUCTURE: 1.5,
      FailureType.CONFIGURATION: 0.8,
      FailureType.DEPENDENCY: 1.2,
      FailureType.RESOURCE: 0.6,
      FailureType.APPLICATION: 1.3,
      FailureType.DATA: 2.0,
      FailureType.SECURITY: 1.5,
      FailureType.NETWORK: 1.1,
      FailureType.TIMING: 1.4,
      FailureType.HUMAN_ERROR: 0.9
    }
    
    base_time *= type_multipliers.get(failure_type, 1.0)
    
    # Adjust for severity
    severity_multipliers = {
      FailureSeverity.CRITICAL: 1.5,
      FailureSeverity.HIGH: 1.2,
      FailureSeverity.MEDIUM: 1.0,
      FailureSeverity.LOW: 0.8,
      FailureSeverity.INFO: 0.5
    }
    
    base_time *= severity_multipliers.get(severity, 1.0)
    
    # Adjust for environment
    if context.environment == "production":
      base_time *= 1.3  # More careful in production
    elif context.environment == "development":
      base_time *= 0.7  # Faster in development
    
    return int(base_time)
  
  def _assess_rollback_requirement(self,
                                 failure_type: FailureType,
                                 severity: FailureSeverity,
                                 context: FailureContext) -> bool:
    """Determine if rollback is required for recovery."""
    
    # Automatic rollback triggers
    rollback_triggers = [
      severity in [FailureSeverity.CRITICAL, FailureSeverity.HIGH],
      failure_type in [FailureType.DATA, FailureType.SECURITY, FailureType.APPLICATION],
      context.environment == "production" and severity != FailureSeverity.LOW,
      context.error_rate and context.error_rate > 20,
      context.affected_users and context.affected_users > 1000
    ]
    
    return any(rollback_triggers)
  
  def _assess_data_integrity_risk(self,
                                failure_type: FailureType,
                                affected_components: Set[ComponentType],
                                error_messages: List[str]) -> bool:
    """Assess if there's risk to data integrity."""
    
    high_risk_indicators = [
      failure_type == FailureType.DATA,
      ComponentType.DATABASE in affected_components,
      any("corruption" in msg.lower() for msg in error_messages),
      any("consistency" in msg.lower() for msg in error_messages),
      any("transaction" in msg.lower() for msg in error_messages),
      any("rollback" in msg.lower() for msg in error_messages)
    ]
    
    return any(high_risk_indicators)
  
  def _update_statistics(self, categorized_failure: CategorizedFailure):
    """Update categorization statistics for analysis."""
    
    self.categorization_stats["total_categorizations"] += 1
    
    # Update type statistics
    failure_type = categorized_failure.failure_type.value
    if failure_type not in self.categorization_stats["by_type"]:
      self.categorization_stats["by_type"][failure_type] = 0
    self.categorization_stats["by_type"][failure_type] += 1
    
    # Update severity statistics
    severity = categorized_failure.severity.value
    if severity not in self.categorization_stats["by_severity"]:
      self.categorization_stats["by_severity"][severity] = 0
    self.categorization_stats["by_severity"][severity] += 1
    
    # Update average confidence
    total = self.categorization_stats["total_categorizations"]
    current_avg = self.categorization_stats["average_confidence"]
    new_confidence = categorized_failure.confidence_score
    
    self.categorization_stats["average_confidence"] = (
      (current_avg * (total - 1) + new_confidence) / total
    )
  
  def export_categorized_failure(self, failure: CategorizedFailure, format: str = "json") -> str:
    """Export categorized failure in specified format."""
    
    if format.lower() == "json":
      # Convert to JSON-serializable format
      failure_dict = asdict(failure)
      
      # Handle special types
      failure_dict["failure_type"] = failure.failure_type.value
      failure_dict["severity"] = failure.severity.value
      failure_dict["recovery_complexity"] = failure.recovery_complexity.value
      failure_dict["affected_components"] = [comp.value for comp in failure.affected_components]
      failure_dict["context"]["timestamp"] = failure.context.timestamp.isoformat()
      
      return json.dumps(failure_dict, indent=2)
    
    elif format.lower() == "yaml":
      try:
        import yaml
        failure_dict = asdict(failure)
        failure_dict["failure_type"] = failure.failure_type.value
        failure_dict["severity"] = failure.severity.value
        failure_dict["recovery_complexity"] = failure.recovery_complexity.value
        failure_dict["affected_components"] = [comp.value for comp in failure.affected_components]
        failure_dict["context"]["timestamp"] = failure.context.timestamp.isoformat()
        
        return yaml.dump(failure_dict, default_flow_style=False)
      
      except ImportError:
        return "PyYAML not available for YAML export"
    
    else:
      return f"Unsupported export format: {format}"
  
  def get_statistics(self) -> Dict[str, Any]:
    """Get current categorization statistics."""
    return self.categorization_stats.copy()


if __name__ == "__main__":
  # Example usage and testing
  logging.basicConfig(level=logging.INFO)
  
  categorizer = FailureCategorizer()
  
  # Example failure scenario
  error_messages = [
    "Connection refused to database server",
    "SQLAlchemy connection pool exhausted",
    "Unable to connect to PostgreSQL database"
  ]
  
  log_entries = [
    "2024-01-15T10:00:00 ERROR: Database connection failed after 3 retries",
    "2024-01-15T10:00:05 ERROR: Connection pool size exceeded maximum limit",
    "2024-01-15T10:00:10 CRITICAL: Application unable to serve requests"
  ]
  
  metrics = {
    "db_connection_errors": 15.0,
    "db_response_time": 8000.0,
    "error_rate": 25.0,
    "response_time_p95": 15000.0
  }
  
  status_codes = [500, 503, 502]
  
  context = FailureContext(
    environment="production",
    timestamp=datetime.now(),
    affected_users=5000,
    affected_regions=["us-east-1", "us-west-2"],
    deployment_phase="deploy",
    error_rate=25.0,
    response_time_degradation=300.0
  )
  
  # Categorize the failure
  categorized = categorizer.categorize_failure(
    error_messages=error_messages,
    log_entries=log_entries,
    metrics=metrics,
    status_codes=status_codes,
    context=context
  )
  
  # Display results
  print("Failure Categorization Results:")
  print("=" * 50)
  print(f"Failure ID: {categorized.failure_id}")
  print(f"Type: {categorized.failure_type.value}")
  print(f"Severity: {categorized.severity.value}")
  print(f"Affected Components: {[c.value for c in categorized.affected_components]}")
  print(f"Recovery Complexity: {categorized.recovery_complexity.value}")
  print(f"Confidence Score: {categorized.confidence_score:.2f}")
  print(f"Requires Rollback: {categorized.requires_rollback}")
  print(f"Data Integrity Risk: {categorized.data_integrity_risk}")
  print(f"Estimated Recovery Time: {categorized.estimated_recovery_time} minutes")
  
  print("\nCategorization Reasoning:")
  print(categorized.categorization_reasoning)
  
  print("\nRecommended Actions:")
  for i, action in enumerate(categorized.recommended_actions, 1):
    print(f"  {i}. {action}")
  
  print(f"\nExported JSON:")
  print(categorizer.export_categorized_failure(categorized, "json"))