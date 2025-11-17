#!/usr/bin/env python3
"""Example Usage of Sophisticated Deployment Failure Recovery System
================================================================

This script demonstrates comprehensive usage of the failure recovery system,
showcasing real-world scenarios and integration patterns.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from cicd_integration import CICDIntegrationManager, CICDPlatform, DeploymentEnvironment, DeploymentPhase
from decision_tree_engine import DecisionResult, DecisionTreeEngine

# Import failure recovery system components
from failure_categorizer import ComponentType, FailureCategorizer, FailureContext, FailureSeverity, FailureType
from recovery_orchestrator import ImpactLevel, RecoveryConstraints, RecoveryOrchestrator


async def example_database_failure_recovery():
    """Example 1: Database connection failure in production."""
    print("\n" + "=" * 80)
    print("🗄️  EXAMPLE 1: DATABASE FAILURE RECOVERY")
    print("=" * 80)

    # Initialize components
    categorizer = FailureCategorizer()
    orchestrator = RecoveryOrchestrator()

    # Simulate database failure scenario
    error_messages = [
        "psycopg2.OperationalError: FATAL: remaining connection slots are reserved",
        "sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 30 reached",
        "Connection to database failed after 5 retry attempts",
    ]

    log_entries = [
        "2024-01-15T14:30:15 ERROR [db.connection] Connection pool exhausted",
        "2024-01-15T14:30:16 CRITICAL [app.main] Database unavailable, failing health check",
        "2024-01-15T14:30:17 ERROR [api.users] Failed to authenticate user: database error",
        "2024-01-15T14:30:18 WARNING [monitoring] High error rate detected: 45%",
    ]

    metrics = {
        "db_connection_errors": 25.0,
        "db_response_time": 15000.0,  # 15 seconds
        "error_rate": 45.0,
        "active_connections": 50,
        "max_connections": 50,
        "cpu_utilization": 85.0,
        "memory_utilization": 92.0,
    }

    status_codes = [500, 503, 502]

    context = FailureContext(
        environment="production",
        timestamp=datetime.now(),
        affected_users=3500,
        affected_regions=["us-east-1", "us-west-2"],
        deployment_phase="post_deploy",
        error_rate=45.0,
        response_time_degradation=800.0,  # 800% increase
    )

    print("📊 Failure Analysis:")
    print(f"   • Error messages: {len(error_messages)}")
    print(f"   • Log entries: {len(log_entries)}")
    print(f"   • Status codes: {status_codes}")
    print(f"   • Error rate: {metrics['error_rate']}%")
    print(f"   • Affected users: {context.affected_users:,}")

    # Step 1: Categorize the failure
    print("\n🔍 Step 1: Categorizing Failure")
    failure = categorizer.categorize_failure(
        error_messages=error_messages,
        log_entries=log_entries,
        metrics=metrics,
        status_codes=status_codes,
        context=context,
    )

    print(f"   • Failure Type: {failure.failure_type.value.upper()}")
    print(f"   • Severity: {failure.severity.value.upper()}")
    print(f"   • Affected Components: {[c.value for c in failure.affected_components]}")
    print(f"   • Recovery Complexity: {failure.recovery_complexity.value}")
    print(f"   • Confidence Score: {failure.confidence_score:.1%}")
    print(f"   • Requires Rollback: {failure.requires_rollback}")
    print(f"   • Data Integrity Risk: {failure.data_integrity_risk}")

    # Step 2: Create recovery constraints
    print("\n⚙️  Step 2: Defining Recovery Constraints")
    constraints = RecoveryConstraints(
        max_downtime_minutes=10,  # Maximum 10 minutes downtime
        max_data_loss_seconds=0,  # No data loss acceptable
        min_availability_percent=99.0,
        requires_approval=True,  # Production requires approval
        notification_required=True,
        readonly_mode_acceptable=True,  # Can switch to read-only temporarily
        backup_systems_available=True,
    )

    print(f"   • Max Downtime: {constraints.max_downtime_minutes} minutes")
    print(f"   • Data Loss Tolerance: {constraints.max_data_loss_seconds} seconds")
    print(f"   • Min Availability: {constraints.min_availability_percent}%")
    print(f"   • Requires Approval: {constraints.requires_approval}")

    # Step 3: Create recovery plan
    print("\n📋 Step 3: Creating Recovery Plan")
    plan = await orchestrator.create_recovery_plan(failure, constraints)

    print(f"   • Plan ID: {plan.plan_id}")
    print(f"   • Primary Strategy: {plan.primary_strategy.name}")
    print(f"   • Fallback Strategies: {len(plan.fallback_strategies)}")
    print(f"   • Estimated Duration: {plan.estimated_duration_minutes} minutes")
    print(f"   • Success Probability: {plan.success_probability:.1%}")
    print(f"   • Estimated Impact: {plan.estimated_impact.value}")
    print(f"   • Rollback Points: {len(plan.rollback_points)}")

    # Step 4: Execute recovery plan
    print("\n🚀 Step 4: Executing Recovery Plan")
    execution = await orchestrator.execute_recovery_plan(plan, dry_run=True)

    print(f"   • Execution ID: {execution.execution_id}")
    print(f"   • Final Result: {execution.final_result.value if execution.final_result else 'None'}")
    print(f"   • Success: {'✅' if execution.success else '❌'}")
    print(f"   • Duration: {execution.metrics.recovery_duration_seconds:.1f} seconds")
    print(f"   • Strategies Completed: {len(execution.completed_strategies)}")
    print(f"   • Strategies Failed: {len(execution.failed_strategies)}")
    print(f"   • Fallback Strategies Used: {execution.metrics.fallback_strategies_used}")

    # Step 5: Show recovery progress
    print("\n📈 Recovery Progress:")
    for msg in execution.status_messages[-5:]:  # Show last 5 status messages
        level_emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        emoji = level_emoji.get(msg["level"], "📝")
        print(f"   {emoji} [{msg['phase']}] {msg['message']} ({msg['progress']:.0f}%)")

    # Step 6: Show decision reasoning
    print("\n🧠 Decision Reasoning:")
    for i, reasoning in enumerate(
        execution.decision_paths[0].decision_reasoning if execution.decision_paths else [], 1
    ):
        print(f"   {i}. {reasoning}")

    # Step 7: Show recommendations
    print("\n💡 Recommendations:")
    for rec in failure.recommended_actions[:5]:  # Show top 5 recommendations
        print(f"   • {rec}")

    return execution


async def example_frontend_deployment_failure():
    """Example 2: Frontend deployment failure with CI/CD integration."""
    print("\n" + "=" * 80)
    print("🌐 EXAMPLE 2: FRONTEND DEPLOYMENT FAILURE WITH CI/CD")
    print("=" * 80)

    # Initialize CI/CD integration
    integration_manager = CICDIntegrationManager()

    # Simulate GitHub Actions webhook payload for failed deployment
    github_payload = {
        "action": "completed",
        "workflow_run": {
            "id": 789012345,
            "name": "Deploy Frontend to Production",
            "head_branch": "main",
            "head_sha": "a1b2c3d4e5f6789012345678901234567890abcd",
            "conclusion": "failure",
            "created_at": "2024-01-15T16:45:00Z",
            "updated_at": "2024-01-15T16:52:30Z",
            "head_commit": {"message": "Update user dashboard with new analytics widgets"},
            "jobs": [
                {"name": "build-frontend", "conclusion": "success"},
                {"name": "run-tests", "conclusion": "success"},
                {"name": "deploy-to-production", "conclusion": "failure"},
            ],
        },
        "repository": {"full_name": "pratiko-ai/frontend-dashboard"},
        "sender": {"login": "frontend-developer"},
    }

    github_headers = {
        "X-GitHub-Event": "workflow_run",
        "X-Hub-Signature-256": "sha256=mock_signature_for_demo",
        "X-GitHub-Delivery": "12345678-1234-1234-1234-123456789abc",
    }

    print("📨 GitHub Webhook Received:")
    print(f"   • Repository: {github_payload['repository']['full_name']}")
    print(f"   • Workflow: {github_payload['workflow_run']['name']}")
    print(f"   • Branch: {github_payload['workflow_run']['head_branch']}")
    print(f"   • Commit: {github_payload['workflow_run']['head_sha'][:8]}...")
    print(f"   • Status: {github_payload['workflow_run']['conclusion']}")

    # Process the webhook event
    print("\n🔄 Processing Webhook Event")
    raw_payload = json.dumps(github_payload).encode("utf-8")

    response = await integration_manager.process_webhook_event(
        platform=CICDPlatform.GITHUB_ACTIONS, payload=github_payload, headers=github_headers, raw_payload=raw_payload
    )

    print(f"   • Response ID: {response.response_id}")
    print(f"   • Recovery Attempted: {'✅' if response.recovery_attempted else '❌'}")
    print(f"   • Recovery Successful: {'✅' if response.recovery_successful else '❌'}")
    print(f"   • Should Retry Deployment: {'✅' if response.should_retry_deployment else '❌'}")
    print(f"   • Should Rollback: {'✅' if response.should_rollback else '❌'}")
    print(f"   • Safe to Continue: {'✅' if response.safe_to_continue else '❌'}")

    if response.recovery_duration_seconds:
        print(f"   • Recovery Duration: {response.recovery_duration_seconds:.1f} seconds")

    # Show failure categorization
    if response.failure_categorization:
        print("\n🏷️  Failure Categorization:")
        cat = response.failure_categorization
        print(f"   • Type: {cat['type']}")
        print(f"   • Severity: {cat['severity']}")
        print(f"   • Components: {', '.join(cat['components'])}")

    # Show strategies used
    if response.strategies_used:
        print("\n🛠️  Recovery Strategies Used:")
        for strategy in response.strategies_used:
            print(f"   • {strategy}")

    # Show recommendations
    if response.recommendations:
        print("\n💡 CI/CD Recommendations:")
        for rec in response.recommendations:
            print(f"   • {rec}")

    # Show next steps
    if response.next_steps:
        print("\n👆 Next Steps:")
        for step in response.next_steps:
            print(f"   • {step}")

    return response


async def example_multi_component_failure():
    """Example 3: Complex failure affecting multiple components."""
    print("\n" + "=" * 80)
    print("🏗️  EXAMPLE 3: MULTI-COMPONENT SYSTEM FAILURE")
    print("=" * 80)

    # Initialize components
    categorizer = FailureCategorizer()
    DecisionTreeEngine()
    orchestrator = RecoveryOrchestrator()

    # Complex failure scenario - infrastructure issue affecting multiple components
    error_messages = [
        "kubernetes.client.rest.ApiException: (503) Service Unavailable",
        "connection refused: dial tcp 10.0.1.5:5432: connect: connection refused",
        "nginx: [error] connect() failed (111: Connection refused) while connecting to upstream",
        "redis.exceptions.ConnectionError: Error 111 connecting to redis-cluster:6379",
        "elasticsearch.exceptions.ConnectionError: Connection timeout",
    ]

    log_entries = [
        "2024-01-15T09:15:00 CRITICAL [k8s.node] Node worker-3 became NotReady",
        "2024-01-15T09:15:05 ERROR [lb.nginx] Upstream backend-service is down",
        "2024-01-15T09:15:08 ERROR [app.auth] Redis connection lost, session store unavailable",
        "2024-01-15T09:15:10 WARNING [app.search] Elasticsearch cluster unreachable",
        "2024-01-15T09:15:12 CRITICAL [db.postgres] Database connection pool exhausted",
        "2024-01-15T09:15:15 ERROR [monitoring.prometheus] Metrics collection failing",
        "2024-01-15T09:15:18 ALERT [alertmanager] High error rate detected across all services",
    ]

    metrics = {
        "node_availability": 66.7,  # 2 out of 3 nodes available
        "service_availability": 45.0,  # Multiple services down
        "error_rate": 78.0,
        "cpu_utilization": 95.0,  # Remaining nodes overloaded
        "memory_utilization": 88.0,
        "network_latency": 2500.0,  # High latency due to overload
        "active_connections": 15,
        "failed_health_checks": 8,
    }

    status_codes = [503, 502, 504, 500]

    context = FailureContext(
        environment="production",
        timestamp=datetime.now(),
        affected_users=8500,  # Large impact
        affected_regions=["us-east-1", "eu-west-1"],
        deployment_phase="monitoring",
        error_rate=78.0,
        response_time_degradation=1200.0,  # 12x slower
        resource_utilization={"cpu": 95.0, "memory": 88.0, "network": 75.0, "disk": 65.0},
    )

    print("🔥 Critical System Failure Detected:")
    print(f"   • Affected Users: {context.affected_users:,}")
    print(f"   • Error Rate: {metrics['error_rate']}%")
    print(f"   • Node Availability: {metrics['node_availability']}%")
    print(f"   • Service Availability: {metrics['service_availability']}%")
    print(f"   • Response Time Impact: {context.response_time_degradation:.0f}% increase")

    # Categorize the complex failure
    print("\n🔍 Failure Analysis:")
    failure = categorizer.categorize_failure(
        error_messages=error_messages,
        log_entries=log_entries,
        metrics=metrics,
        status_codes=status_codes,
        context=context,
    )

    print(f"   • Primary Type: {failure.failure_type.value.upper()}")
    print(f"   • Severity: {failure.severity.value.upper()} (Critical Infrastructure)")
    print(f"   • Components Affected: {len(failure.affected_components)}")

    component_list = [c.value.replace("_", " ").title() for c in failure.affected_components]
    for i, component in enumerate(component_list, 1):
        print(f"     {i}. {component}")

    print(f"   • Recovery Complexity: {failure.recovery_complexity.value.upper()}")
    print(f"   • Estimated Recovery Time: {failure.estimated_recovery_time} minutes")
    print(f"   • Data Integrity Risk: {'🔴 HIGH' if failure.data_integrity_risk else '🟢 LOW'}")

    # Create emergency recovery constraints
    print("\n🚨 Emergency Recovery Constraints:")
    emergency_constraints = RecoveryConstraints(
        max_downtime_minutes=20,  # Extended time for complex recovery
        max_data_loss_seconds=0,
        min_availability_percent=95.0,
        requires_approval=True,  # Critical failure needs approval
        notification_required=True,
        business_hours_only=False,  # Emergency - any time
        readonly_mode_acceptable=False,  # Need full functionality
        degraded_performance_acceptable=True,
        backup_systems_available=True,
        max_additional_resources=10,  # Allow scaling up
    )

    print(f"   • Max Downtime: {emergency_constraints.max_downtime_minutes} minutes")
    print(f"   • Target Availability: {emergency_constraints.min_availability_percent}%")
    print(f"   • Additional Resources: {emergency_constraints.max_additional_resources}")

    # Create comprehensive recovery plan
    print("\n📋 Emergency Recovery Plan:")
    plan = await orchestrator.create_recovery_plan(failure, emergency_constraints)

    print(f"   • Plan Type: {plan.primary_strategy.name}")
    print(f"   • Execution Phases: {len(plan.phases)}")
    print(f"   • Fallback Options: {len(plan.fallback_strategies)}")
    print(f"   • Success Probability: {plan.success_probability:.1%}")
    print(f"   • Impact Assessment: {plan.estimated_impact.value.upper()}")

    # Show execution phases
    print("\n📅 Recovery Phases:")
    for phase, strategies in plan.phases.items():
        if strategies:
            print(f"   • {phase.value.replace('_', ' ').title()}: {len(strategies)} strategies")

    # Execute emergency recovery
    print("\n🚀 Executing Emergency Recovery:")
    execution = await orchestrator.execute_recovery_plan(plan, dry_run=True)

    print(f"   • Execution Status: {'✅ SUCCESS' if execution.success else '❌ FAILED'}")
    print(f"   • Total Duration: {execution.metrics.recovery_duration_seconds:.1f} seconds")
    print(f"   • Components Recovered: {execution.metrics.components_recovered}")
    print(f"   • Components Failed: {execution.metrics.components_failed}")
    print(f"   • Manual Interventions: {execution.metrics.manual_interventions}")

    # Show recovery metrics
    if execution.metrics.users_affected:
        print("\n📊 Impact Metrics:")
        print(f"   • Users Affected: {execution.metrics.users_affected:,}")
        print(f"   • Transactions Lost: {execution.metrics.transactions_lost}")
        if execution.metrics.revenue_impact_dollars:
            print(f"   • Revenue Impact: ${execution.metrics.revenue_impact_dollars:,.2f}")
        print(f"   • Additional Costs: ${execution.metrics.additional_costs or 0:.2f}")

    # Show final system state
    print("\n🎯 Recovery Outcome:")
    if execution.success:
        print("   ✅ System restored to operational state")
        print("   ✅ All critical components recovered")
        print("   ✅ Performance within acceptable limits")
        print("   ✅ Data integrity preserved")
    else:
        print("   ❌ Automatic recovery incomplete")
        print("   ⚠️  Manual intervention required")
        print("   🔄 Escalation procedures activated")

    return execution


async def example_jenkins_pipeline_integration():
    """Example 4: Jenkins pipeline failure with automated recovery."""
    print("\n" + "=" * 80)
    print("🔨 EXAMPLE 4: JENKINS PIPELINE FAILURE INTEGRATION")
    print("=" * 80)

    # Initialize CI/CD integration
    integration_manager = CICDIntegrationManager()

    # Simulate Jenkins webhook payload
    jenkins_payload = {
        "build": {
            "fullDisplayName": "backend-api-production-deploy #156",
            "number": 156,
            "result": "FAILURE",
            "url": "https://jenkins.pratiko.ai/job/backend-api-production-deploy/156/",
            "duration": 1245000,  # ~20 minutes
            "timestamp": 1705485600000,  # Unix timestamp
            "scm": {
                "url": "https://github.com/pratiko-ai/backend-api",
                "branch": "main",
                "commit": "f1e2d3c4b5a6789012345678901234567890cdef",
                "message": "Optimize database queries and add caching layer",
            },
            "culprits": [{"fullName": "Backend Developer"}],
            "description": "Deployment failed during database migration step",
            "actions": [
                {"stageName": "Build", "status": "SUCCESS"},
                {"stageName": "Test", "status": "SUCCESS"},
                {"stageName": "Security Scan", "status": "SUCCESS"},
                {"stageName": "Deploy to Staging", "status": "SUCCESS"},
                {"stageName": "Integration Tests", "status": "SUCCESS"},
                {"stageName": "Deploy to Production", "status": "FAILURE"},
                {"stageName": "Database Migration", "status": "FAILURE"},
            ],
        }
    }

    jenkins_headers = {
        "X-Jenkins-Event": "build_completed",
        "X-Jenkins-Signature": "mock_jenkins_signature",
        "Content-Type": "application/json",
    }

    print("🔨 Jenkins Webhook Details:")
    build = jenkins_payload["build"]
    print(f"   • Job: {build['fullDisplayName']}")
    print(f"   • Build Number: #{build['number']}")
    print(f"   • Result: {build['result']}")
    print(f"   • Duration: {build['duration'] / 1000 / 60:.1f} minutes")
    print(f"   • Repository: {build['scm']['url']}")
    print(f"   • Branch: {build['scm']['branch']}")
    print(f"   • Commit: {build['scm']['commit'][:8]}...")

    # Show pipeline stages
    print("\n📋 Pipeline Stages:")
    for action in build.get("actions", []):
        status_emoji = "✅" if action["status"] == "SUCCESS" else "❌"
        print(f"   {status_emoji} {action['stageName']}: {action['status']}")

    # Process Jenkins webhook
    print("\n🔄 Processing Jenkins Webhook:")
    raw_payload = json.dumps(jenkins_payload).encode("utf-8")

    response = await integration_manager.process_webhook_event(
        platform=CICDPlatform.JENKINS, payload=jenkins_payload, headers=jenkins_headers, raw_payload=raw_payload
    )

    print("   • Event Processed: ✅")
    print(f"   • Recovery Triggered: {'✅' if response.recovery_attempted else '❌'}")
    print(f"   • Recovery Result: {'✅ SUCCESS' if response.recovery_successful else '❌ FAILED'}")

    if response.recovery_duration_seconds:
        print(f"   • Recovery Time: {response.recovery_duration_seconds:.1f} seconds")

    # Show deployment decision
    print("\n🎯 Deployment Decision:")
    print(f"   • Retry Deployment: {'✅ YES' if response.should_retry_deployment else '❌ NO'}")
    print(f"   • Rollback Required: {'✅ YES' if response.should_rollback else '❌ NO'}")
    print(f"   • Safe to Continue: {'✅ YES' if response.safe_to_continue else '❌ NO'}")

    # Show specific recommendations for Jenkins
    if response.recommendations:
        print("\n💡 Jenkins Integration Recommendations:")
        for i, rec in enumerate(response.recommendations, 1):
            print(f"   {i}. {rec}")

    # Show next steps for the pipeline
    if response.next_steps:
        print("\n👆 Jenkins Pipeline Next Steps:")
        for i, step in enumerate(response.next_steps, 1):
            print(f"   {i}. {step}")

    return response


async def example_performance_degradation_recovery():
    """Example 5: Performance degradation detection and recovery."""
    print("\n" + "=" * 80)
    print("⚡ EXAMPLE 5: PERFORMANCE DEGRADATION RECOVERY")
    print("=" * 80)

    # Initialize components
    categorizer = FailureCategorizer()
    orchestrator = RecoveryOrchestrator()

    # Performance degradation scenario
    error_messages = [
        "Request timeout: operation took longer than 30 seconds",
        "Connection pool timeout: unable to get connection within 10 seconds",
        "Slow query detected: execution time 45.7 seconds",
        "Memory allocation failed: insufficient memory for operation",
    ]

    log_entries = [
        "2024-01-15T11:20:00 WARNING [app.api] Response time p95 exceeded threshold: 8.5s",
        "2024-01-15T11:20:05 WARNING [db.query] Slow query detected: SELECT * FROM large_table",
        "2024-01-15T11:20:10 ERROR [cache.redis] Cache miss rate increased to 85%",
        "2024-01-15T11:20:15 WARNING [monitoring] Memory usage reached 95%",
        "2024-01-15T11:20:20 INFO [autoscaler] Attempting to scale up due to high load",
        "2024-01-15T11:20:25 ERROR [lb.haproxy] Backend response times degraded",
    ]

    metrics = {
        "response_time_p50": 2500.0,  # 2.5 seconds (normal: 200ms)
        "response_time_p95": 8500.0,  # 8.5 seconds (normal: 500ms)
        "response_time_p99": 15000.0,  # 15 seconds (normal: 1s)
        "cache_hit_rate": 15.0,  # Down from 90%
        "db_query_time_avg": 3500.0,  # 3.5 seconds (normal: 100ms)
        "cpu_utilization": 88.0,
        "memory_utilization": 95.0,
        "active_connections": 1250,  # High load
        "queue_depth": 450,  # Backlog building up
        "throughput_rps": 45.0,  # Down from 200 RPS
        "error_rate": 12.0,  # Moderate but concerning
    }

    status_codes = [200, 500, 502, 503, 504]  # Mix including timeouts

    context = FailureContext(
        environment="production",
        timestamp=datetime.now(),
        affected_users=2800,
        deployment_phase="monitoring",
        error_rate=12.0,
        response_time_degradation=425.0,  # 4.25x slower
        resource_utilization={"cpu": 88.0, "memory": 95.0, "disk": 70.0, "network": 65.0},
    )

    print("📉 Performance Degradation Detected:")
    print(f"   • Response Time P95: {metrics['response_time_p95']:.0f}ms (normal: 500ms)")
    print(f"   • Response Time P99: {metrics['response_time_p99']:.0f}ms (normal: 1000ms)")
    print(f"   • Cache Hit Rate: {metrics['cache_hit_rate']:.0f}% (normal: 90%)")
    print(f"   • Throughput: {metrics['throughput_rps']:.0f} RPS (normal: 200 RPS)")
    print(f"   • Queue Depth: {metrics['queue_depth']} requests")
    print(f"   • Memory Usage: {metrics['memory_utilization']:.0f}%")

    # Categorize performance issue
    print("\n🔍 Performance Analysis:")
    failure = categorizer.categorize_failure(
        error_messages=error_messages,
        log_entries=log_entries,
        metrics=metrics,
        status_codes=status_codes,
        context=context,
    )

    print(f"   • Issue Type: {failure.failure_type.value.upper()}")
    print(f"   • Severity: {failure.severity.value.upper()}")
    print(f"   • Root Cause Confidence: {failure.confidence_score:.1%}")
    print(f"   • Estimated Fix Time: {failure.estimated_recovery_time} minutes")

    # Performance-specific recovery constraints
    print("\n⚙️  Performance Recovery Constraints:")
    perf_constraints = RecoveryConstraints(
        max_downtime_minutes=2,  # Minimal downtime for performance fixes
        requires_approval=False,  # Performance fixes can be automatic
        readonly_mode_acceptable=True,  # Can temporarily limit writes
        degraded_performance_acceptable=False,  # Goal is to improve performance
        max_resource_utilization=0.95,  # Allow temporary resource increase
        max_additional_resources=5,  # Can scale up to fix performance
    )

    print(f"   • Max Downtime: {perf_constraints.max_downtime_minutes} minutes")
    print(f"   • Auto-approval: {'✅' if not perf_constraints.requires_approval else '❌'}")
    print(f"   • Read-only Mode OK: {'✅' if perf_constraints.readonly_mode_acceptable else '❌'}")
    print(f"   • Can Scale Up: {'✅' if perf_constraints.max_additional_resources else '❌'}")

    # Create performance recovery plan
    print("\n📋 Performance Recovery Plan:")
    plan = await orchestrator.create_recovery_plan(failure, perf_constraints)

    print(f"   • Strategy: {plan.primary_strategy.name}")
    print("   • Optimization Focus: Resource allocation and caching")
    print(f"   • Expected Improvement: {100 - plan.success_probability * 100:.0f}% response time reduction")
    print(f"   • Implementation Time: {plan.estimated_duration_minutes} minutes")

    # Execute performance optimization
    print("\n⚡ Executing Performance Recovery:")
    execution = await orchestrator.execute_recovery_plan(plan, dry_run=True)

    print(f"   • Optimization Result: {'✅ SUCCESS' if execution.success else '❌ FAILED'}")
    print(f"   • Execution Time: {execution.metrics.recovery_duration_seconds:.1f} seconds")

    # Show performance improvements (simulated)
    if execution.success:
        print("\n📈 Performance Improvements:")
        print("   • Response Time P95: 8.5s → 0.6s (93% improvement)")
        print("   • Response Time P99: 15.0s → 1.2s (92% improvement)")
        print("   • Cache Hit Rate: 15% → 88% (restored)")
        print("   • Throughput: 45 RPS → 185 RPS (4x improvement)")
        print("   • Memory Usage: 95% → 72% (optimized)")
        print("   • Queue Depth: 450 → 12 (cleared backlog)")

    # Show specific optimizations applied
    print("\n🛠️  Applied Optimizations:")
    optimizations = [
        "Scaled up backend services from 3 to 6 instances",
        "Increased Redis cache memory allocation by 50%",
        "Optimized database connection pool settings",
        "Enabled query result caching for expensive operations",
        "Adjusted load balancer timeouts and retry policies",
        "Implemented circuit breakers for external API calls",
    ]

    for i, opt in enumerate(optimizations, 1):
        print(f"   {i}. {opt}")

    return execution


async def main():
    """Run all failure recovery examples."""
    print("🎯 SOPHISTICATED DEPLOYMENT FAILURE RECOVERY SYSTEM")
    print("=" * 80)
    print("Demonstrating comprehensive failure recovery capabilities")
    print("All examples use simulated scenarios for safe demonstration")

    # Configure logging for examples
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise for demo
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    examples = [
        ("Database Connection Failure", example_database_failure_recovery),
        ("Frontend Deployment with CI/CD", example_frontend_deployment_failure),
        ("Multi-Component System Failure", example_multi_component_failure),
        ("Jenkins Pipeline Integration", example_jenkins_pipeline_integration),
        ("Performance Degradation", example_performance_degradation_recovery),
    ]

    results = []

    for name, example_func in examples:
        try:
            print(f"\n🚀 Running: {name}")
            result = await example_func()
            results.append((name, result, True))
            print(f"✅ Completed: {name}")
        except Exception as e:
            print(f"❌ Failed: {name} - {e}")
            results.append((name, str(e), False))

    # Summary
    print("\n" + "=" * 80)
    print("📊 EXAMPLES SUMMARY")
    print("=" * 80)

    successful = sum(1 for _, _, success in results if success)
    total = len(results)

    print(f"Total Examples: {total}")
    print(f"Successful: {successful}")
    print(f"Success Rate: {successful / total:.1%}")

    print("\n📋 Results:")
    for name, result, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   • {name}: {status}")

    print("\n💡 Key Takeaways:")
    print("   • Intelligent failure categorization enables targeted recovery")
    print("   • Decision trees provide clear reasoning for recovery actions")
    print("   • Multi-phase recovery ensures comprehensive system restoration")
    print("   • CI/CD integration enables automated deployment failure handling")
    print("   • Performance monitoring prevents small issues from becoming outages")

    print("\n🎯 Next Steps:")
    print("   • Review generated logs and reports")
    print("   • Customize recovery strategies for your specific environment")
    print("   • Integrate with your existing monitoring and CI/CD systems")
    print("   • Set up alerting and notification channels")
    print("   • Train your team on the recovery procedures")

    return results


if __name__ == "__main__":
    # Run all examples
    asyncio.run(main())
