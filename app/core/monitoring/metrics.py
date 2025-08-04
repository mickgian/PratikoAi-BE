"""Prometheus metrics for PratikoAI monitoring dashboard.

This module defines all Prometheus metrics for monitoring cost, performance,
business metrics, and system health.
"""

import os
import psutil
from typing import Dict, Any
from prometheus_client import (
    Counter, Gauge, Histogram, Info, CollectorRegistry, 
    generate_latest, CONTENT_TYPE_LATEST
)

from app.core.config import settings
from app.core.logging import logger

# Create custom registry for better control
REGISTRY = CollectorRegistry()

# =============================================================================
# COST METRICS - Track LLM provider costs and user spending
# =============================================================================

llm_cost_total = Counter(
    'llm_cost_total_eur',
    'Total LLM API costs in EUR by provider and model',
    ['provider', 'model', 'user_id'],
    registry=REGISTRY
)

user_monthly_cost = Gauge(
    'user_monthly_cost_eur',
    'Current monthly cost per user in EUR (target <2.00)',
    ['user_id', 'plan_type'],
    registry=REGISTRY
)

api_calls_by_provider = Counter(
    'api_calls_total',
    'Total API calls by provider and success status',
    ['provider', 'model', 'status'],
    registry=REGISTRY
)

# =============================================================================
# PERFORMANCE METRICS - Track response times and system efficiency
# =============================================================================

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')),
    registry=REGISTRY
)

cache_hit_ratio = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio (0.0-1.0, target >0.8)',
    ['cache_type'],
    registry=REGISTRY
)

active_users = Gauge(
    'active_users_total',
    'Number of currently active users',
    ['time_window'],  # 5m, 1h, 24h
    registry=REGISTRY
)

# =============================================================================
# BUSINESS METRICS - Track revenue and growth toward €25k ARR
# =============================================================================

active_subscriptions = Gauge(
    'active_subscriptions_total',
    'Number of active paid subscriptions (target 50)',
    ['subscription_type', 'status'],
    registry=REGISTRY
)

monthly_revenue = Gauge(
    'monthly_revenue_eur',
    'Monthly Recurring Revenue in EUR (target 25000)',
    ['currency'],
    registry=REGISTRY
)

trial_conversions = Counter(
    'trial_conversions_total',
    'Number of trial to paid conversions',
    ['conversion_type', 'plan_type'],
    registry=REGISTRY
)

# =============================================================================
# SYSTEM METRICS - Track infrastructure health
# =============================================================================

database_connections = Gauge(
    'database_connections_active',
    'Number of active database connections',
    ['database_type', 'status'],
    registry=REGISTRY
)

redis_memory_usage = Gauge(
    'redis_memory_usage_bytes',
    'Redis memory usage in bytes',
    ['instance'],
    registry=REGISTRY
)

llm_errors = Counter(
    'llm_errors_total',
    'LLM provider errors by type',
    ['provider', 'error_type', 'model'],
    registry=REGISTRY
)

# =============================================================================
# BUSINESS-SPECIFIC METRICS - PratikoAI/NormoAI Operations
# =============================================================================

# Italian Tax Calculations
italian_tax_calculations_total = Counter(
    'italian_tax_calculations_total',
    'Total Italian tax calculations performed',
    ['calculation_type', 'status', 'user_id'],
    registry=REGISTRY
)

italian_tax_amount_calculated_eur = Counter(
    'italian_tax_amount_calculated_eur',
    'Total tax amounts calculated in EUR',
    ['calculation_type', 'tax_year'],
    registry=REGISTRY
)

# Document Processing Operations
document_processing_operations_total = Counter(
    'document_processing_operations_total', 
    'Total document processing operations',
    ['operation_type', 'document_type', 'status'],
    registry=REGISTRY
)

document_processing_duration_seconds = Histogram(
    'document_processing_duration_seconds',
    'Document processing duration in seconds',
    ['operation_type', 'document_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float('inf')),
    registry=REGISTRY
)

# Knowledge Base Queries
knowledge_base_queries_total = Counter(
    'knowledge_base_queries_total',
    'Total knowledge base queries',
    ['query_type', 'source', 'status'],
    registry=REGISTRY
)

knowledge_base_query_duration_seconds = Histogram(
    'knowledge_base_query_duration_seconds',
    'Knowledge base query duration in seconds',
    ['query_type', 'source'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, float('inf')),
    registry=REGISTRY
)

knowledge_base_results_found = Histogram(
    'knowledge_base_results_found',
    'Number of results found in knowledge base queries',
    ['query_type', 'source'],
    buckets=(0, 1, 5, 10, 25, 50, 100, float('inf')),
    registry=REGISTRY
)

# Payment Operations 
payment_operations_total = Counter(
    'payment_operations_total',
    'Total payment operations',
    ['operation_type', 'payment_method', 'status'],
    registry=REGISTRY
)

payment_amount_processed_eur = Counter(
    'payment_amount_processed_eur',
    'Total payment amounts processed in EUR',
    ['operation_type', 'currency'],
    registry=REGISTRY
)

payment_operation_duration_seconds = Histogram(
    'payment_operation_duration_seconds',
    'Payment operation duration in seconds',
    ['operation_type', 'payment_method'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float('inf')),
    registry=REGISTRY
)

# API Errors by Category
api_errors_total = Counter(
    'api_errors_total',
    'Total API errors by category and type',
    ['error_category', 'error_type', 'endpoint', 'status_code'],
    registry=REGISTRY
)

# User Actions
user_actions_total = Counter(
    'user_actions_total',
    'Total user actions performed',
    ['action_type', 'feature', 'user_type'],
    registry=REGISTRY
)

# =============================================================================
# ADDITIONAL SYSTEM METRICS
# =============================================================================

system_info = Info(
    'pratikoai_system_info',
    'System information',
    registry=REGISTRY
)

process_memory_bytes = Gauge(
    'process_memory_bytes',
    'Process memory usage in bytes',
    ['type'],  # rss, vms, shared
    registry=REGISTRY
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    registry=REGISTRY
)

# =============================================================================
# INITIALIZATION AND UTILITY FUNCTIONS
# =============================================================================

def initialize_metrics():
    """Initialize metrics with system information and default values."""
    try:
        # Set system information
        system_info.info({
            'version': settings.VERSION,
            'environment': settings.ENVIRONMENT.value,
            'python_version': os.sys.version.split()[0],
            'project_name': settings.PROJECT_NAME,
        })
        
        # Initialize default values
        cache_hit_ratio.labels(cache_type='llm_responses').set(0.0)
        cache_hit_ratio.labels(cache_type='conversations').set(0.0)
        cache_hit_ratio.labels(cache_type='embeddings').set(0.0)
        
        # Initialize active users
        active_users.labels(time_window='5m').set(0)
        active_users.labels(time_window='1h').set(0)
        active_users.labels(time_window='24h').set(0)
        
        # Initialize revenue tracking
        monthly_revenue.labels(currency='EUR').set(0.0)
        
        # Initialize subscription counts
        active_subscriptions.labels(subscription_type='monthly', status='active').set(0)
        active_subscriptions.labels(subscription_type='monthly', status='trial').set(0)
        active_subscriptions.labels(subscription_type='monthly', status='cancelled').set(0)
        
        logger.info(
            "prometheus_metrics_initialized",
            environment=settings.ENVIRONMENT.value,
            registry_collectors=len(REGISTRY._collector_to_names)
        )
        
    except Exception as e:
        logger.error(
            "prometheus_metrics_initialization_failed",
            error=str(e),
            exc_info=True
        )


def update_system_metrics():
    """Update system-level metrics like memory and CPU usage."""
    try:
        # Get process info
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Update memory metrics
        process_memory_bytes.labels(type='rss').set(memory_info.rss)
        process_memory_bytes.labels(type='vms').set(memory_info.vms)
        
        # Update CPU usage
        cpu_percent = process.cpu_percent()
        cpu_usage_percent.set(cpu_percent)
        
    except Exception as e:
        logger.error(
            "system_metrics_update_failed", 
            error=str(e),
            exc_info=True
        )


def get_registry() -> CollectorRegistry:
    """Get the Prometheus registry for metrics export."""
    return REGISTRY


def get_metrics_content() -> str:
    """Get metrics in Prometheus format."""
    try:
        # Update system metrics before export
        update_system_metrics()
        metrics_bytes = generate_latest(REGISTRY)
        return metrics_bytes.decode('utf-8') if isinstance(metrics_bytes, bytes) else metrics_bytes
    except Exception as e:
        logger.error(
            "metrics_generation_failed",
            error=str(e),
            exc_info=True
        )
        return ""


# =============================================================================
# HELPER FUNCTIONS FOR METRIC UPDATES
# =============================================================================

def track_llm_cost(provider: str, model: str, user_id: str, cost_eur: float):
    """Track LLM API cost."""
    llm_cost_total.labels(provider=provider, model=model, user_id=user_id).inc(cost_eur)


def track_api_call(provider: str, model: str, status: str):
    """Track API call by provider and status."""
    api_calls_by_provider.labels(provider=provider, model=model, status=status).inc()


def update_user_monthly_cost(user_id: str, plan_type: str, cost_eur: float):
    """Update user's monthly cost."""
    user_monthly_cost.labels(user_id=user_id, plan_type=plan_type).set(cost_eur)


def track_cache_performance(cache_type: str, hit_ratio: float):
    """Update cache hit ratio."""
    cache_hit_ratio.labels(cache_type=cache_type).set(hit_ratio)


def update_active_users_count(time_window: str, count: int):
    """Update active users count."""
    active_users.labels(time_window=time_window).set(count)


def update_subscription_metrics(subscription_type: str, status: str, count: int):
    """Update subscription counts."""
    active_subscriptions.labels(subscription_type=subscription_type, status=status).set(count)


def update_monthly_revenue(revenue_eur: float):
    """Update monthly revenue."""
    monthly_revenue.labels(currency='EUR').set(revenue_eur)


def track_trial_conversion(conversion_type: str, plan_type: str):
    """Track trial conversion."""
    trial_conversions.labels(conversion_type=conversion_type, plan_type=plan_type).inc()


def update_database_connections(database_type: str, status: str, count: int):
    """Update database connection count."""
    database_connections.labels(database_type=database_type, status=status).set(count)


def track_llm_error(provider: str, error_type: str, model: str):
    """Track LLM provider error."""
    llm_errors.labels(provider=provider, error_type=error_type, model=model).inc()


# =============================================================================
# BUSINESS-SPECIFIC METRIC TRACKING FUNCTIONS
# =============================================================================

def track_italian_tax_calculation(calculation_type: str, status: str, user_id: str, amount_eur: float = None, tax_year: str = None):
    """Track Italian tax calculation operation."""
    italian_tax_calculations_total.labels(
        calculation_type=calculation_type,
        status=status,
        user_id=user_id
    ).inc()
    
    if amount_eur and tax_year:
        italian_tax_amount_calculated_eur.labels(
            calculation_type=calculation_type,
            tax_year=tax_year
        ).inc(amount_eur)


def track_document_processing(operation_type: str, document_type: str, status: str, duration_seconds: float = None):
    """Track document processing operation."""
    document_processing_operations_total.labels(
        operation_type=operation_type,
        document_type=document_type,
        status=status
    ).inc()
    
    if duration_seconds:
        document_processing_duration_seconds.labels(
            operation_type=operation_type,
            document_type=document_type
        ).observe(duration_seconds)


def track_knowledge_base_query(query_type: str, source: str, status: str, duration_seconds: float, results_count: int):
    """Track knowledge base query operation."""
    knowledge_base_queries_total.labels(
        query_type=query_type,
        source=source,
        status=status
    ).inc()
    
    knowledge_base_query_duration_seconds.labels(
        query_type=query_type,
        source=source
    ).observe(duration_seconds)
    
    knowledge_base_results_found.labels(
        query_type=query_type,
        source=source
    ).observe(results_count)


def track_payment_operation(operation_type: str, payment_method: str, status: str, amount_eur: float = None, duration_seconds: float = None):
    """Track payment operation."""
    payment_operations_total.labels(
        operation_type=operation_type,
        payment_method=payment_method,
        status=status
    ).inc()
    
    if amount_eur:
        payment_amount_processed_eur.labels(
            operation_type=operation_type,
            currency="EUR"
        ).inc(amount_eur)
    
    if duration_seconds:
        payment_operation_duration_seconds.labels(
            operation_type=operation_type,
            payment_method=payment_method
        ).observe(duration_seconds)


def track_api_error(error_category: str, error_type: str, endpoint: str, status_code: int):
    """Track categorized API error."""
    api_errors_total.labels(
        error_category=error_category,
        error_type=error_type,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()


def track_user_action(action_type: str, feature: str, user_type: str):
    """Track user action."""
    user_actions_total.labels(
        action_type=action_type,
        feature=feature,
        user_type=user_type
    ).inc()


# Initialize metrics on module import
initialize_metrics()