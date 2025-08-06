"""
Advanced Circuit Breaker Manager for PratikoAI.

Implements provider-specific circuit breakers with advanced features including
gradual recovery, cost-aware breaking, and Italian market optimizations.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from uuid import uuid4

from app.core.config import settings
from app.core.logging import logger
from app.services.cache import CacheService


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    THROTTLED = "throttled"
    MAINTENANCE = "maintenance"


class FailureType(Enum):
    """Types of failures with different weights"""
    CONNECTION_REFUSED = "connection_refused"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "authentication_error"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


class AdvancedCircuitBreakerManager:
    """Advanced circuit breaker manager with provider isolation"""
    
    def __init__(self, cache: Optional[CacheService] = None):
        self.cache = cache
        self.circuits = {}
        self.failure_weights = {
            FailureType.CONNECTION_REFUSED: 1.0,
            FailureType.TIMEOUT: 0.7,
            FailureType.RATE_LIMIT: 0.3,
            FailureType.AUTHENTICATION_ERROR: 0.9,
            FailureType.SERVER_ERROR: 0.8,
            FailureType.UNKNOWN: 0.5
        }
        
    async def get_circuit_status(self, provider: str) -> Dict[str, Any]:
        """Get current circuit status for a provider"""
        if provider not in self.circuits:
            self.circuits[provider] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure_time": None,
                "success_count": 0,
                "last_success_time": None,
                "half_open_attempts": 0,
                "total_requests": 0,
                "cost_spent": 0.0,
                "cost_limit": 100.0
            }
        
        circuit = self.circuits[provider]
        return {
            "provider": provider,
            "state": circuit["state"].value,
            "failure_count": circuit["failure_count"],
            "success_count": circuit["success_count"],
            "total_requests": circuit["total_requests"],
            "health_score": self._calculate_health_score(circuit),
            "cost_remaining": circuit["cost_limit"] - circuit["cost_spent"]
        }
    
    def _calculate_health_score(self, circuit: Dict[str, Any]) -> float:
        """Calculate health score for a circuit"""
        total = circuit["total_requests"]
        if total == 0:
            return 1.0
        
        success_rate = circuit["success_count"] / total
        # Decay older failures
        if circuit["last_failure_time"]:
            time_since_failure = (datetime.utcnow() - circuit["last_failure_time"]).total_seconds()
            decay_factor = min(1.0, time_since_failure / 3600)  # 1 hour decay
            success_rate = success_rate * 0.7 + decay_factor * 0.3
        
        return min(1.0, max(0.0, success_rate))
    
    async def should_allow_request(self, provider: str, cost: float = 0.0) -> bool:
        """Check if request should be allowed through the circuit"""
        status = await self.get_circuit_status(provider)
        circuit = self.circuits[provider]
        
        # Check cost limits first
        if cost > 0 and circuit["cost_spent"] + cost > circuit["cost_limit"]:
            await self._transition_to_throttled(provider, "cost_limit_exceeded")
            return False
        
        state = CircuitState(status["state"])
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            # Check if enough time has passed to try half-open
            if circuit["last_failure_time"]:
                time_since_failure = (datetime.utcnow() - circuit["last_failure_time"]).total_seconds()
                if time_since_failure > 60:  # 1 minute timeout
                    await self._transition_to_half_open(provider)
                    return True
            return False
        elif state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return circuit["half_open_attempts"] < 3
        elif state == CircuitState.THROTTLED:
            # Apply throttling logic (e.g., 50% of requests)
            import random
            return random.random() < 0.5
        elif state == CircuitState.MAINTENANCE:
            return False
        
        return False
    
    async def record_success(self, provider: str, response_time: float = 0.0, cost: float = 0.0):
        """Record a successful request"""
        if provider not in self.circuits:
            await self.get_circuit_status(provider)  # Initialize
        
        circuit = self.circuits[provider]
        circuit["success_count"] += 1
        circuit["total_requests"] += 1
        circuit["last_success_time"] = datetime.utcnow()
        circuit["cost_spent"] += cost
        
        current_state = circuit["state"]
        
        if current_state == CircuitState.HALF_OPEN:
            circuit["half_open_attempts"] += 1
            # If we have enough successful attempts, close the circuit
            if circuit["half_open_attempts"] >= 3:
                await self._transition_to_closed(provider)
        elif current_state == CircuitState.THROTTLED:
            # Check if we can move back to closed based on success rate
            health_score = self._calculate_health_score(circuit)
            if health_score > 0.8:
                await self._transition_to_closed(provider)
    
    async def record_failure(self, provider: str, failure_type: FailureType = FailureType.UNKNOWN, cost: float = 0.0):
        """Record a failed request with weighted failure impact"""
        if provider not in self.circuits:
            await self.get_circuit_status(provider)  # Initialize
        
        circuit = self.circuits[provider]
        weight = self.failure_weights.get(failure_type, 0.5)
        
        circuit["failure_count"] += weight
        circuit["total_requests"] += 1
        circuit["last_failure_time"] = datetime.utcnow()
        circuit["cost_spent"] += cost
        
        current_state = circuit["state"]
        
        # Determine if circuit should open based on failure threshold
        if circuit["failure_count"] >= 5:  # Threshold for opening
            if current_state != CircuitState.OPEN:
                await self._transition_to_open(provider, f"failure_threshold_exceeded: {failure_type.value}")
        elif current_state == CircuitState.HALF_OPEN:
            # Any failure in half-open should go back to open
            await self._transition_to_open(provider, f"half_open_failure: {failure_type.value}")
    
    async def _transition_to_open(self, provider: str, reason: str):
        """Transition circuit to OPEN state"""
        self.circuits[provider]["state"] = CircuitState.OPEN
        self.circuits[provider]["half_open_attempts"] = 0
        logger.warning(f"Circuit opened for provider {provider}: {reason}")
    
    async def _transition_to_half_open(self, provider: str):
        """Transition circuit to HALF_OPEN state"""
        self.circuits[provider]["state"] = CircuitState.HALF_OPEN
        self.circuits[provider]["half_open_attempts"] = 0
        logger.info(f"Circuit transitioned to half-open for provider {provider}")
    
    async def _transition_to_closed(self, provider: str):
        """Transition circuit to CLOSED state"""
        self.circuits[provider]["state"] = CircuitState.CLOSED
        self.circuits[provider]["failure_count"] = 0
        self.circuits[provider]["half_open_attempts"] = 0
        logger.info(f"Circuit closed for provider {provider}")
    
    async def _transition_to_throttled(self, provider: str, reason: str):
        """Transition circuit to THROTTLED state"""
        self.circuits[provider]["state"] = CircuitState.THROTTLED
        logger.warning(f"Circuit throttled for provider {provider}: {reason}")
    
    async def set_maintenance_mode(self, provider: str, enabled: bool):
        """Set maintenance mode for a provider"""
        if provider not in self.circuits:
            await self.get_circuit_status(provider)  # Initialize
        
        if enabled:
            self.circuits[provider]["state"] = CircuitState.MAINTENANCE
            logger.info(f"Maintenance mode enabled for provider {provider}")
        else:
            self.circuits[provider]["state"] = CircuitState.CLOSED
            logger.info(f"Maintenance mode disabled for provider {provider}")
    
    async def start_gradual_recovery(self, provider: str, traffic_percentages: List[float]):
        """Start gradual recovery process"""
        if provider not in self.circuits:
            return {"success": False, "error": "Provider not found"}
        
        # Simplified implementation - in practice would involve more complex logic
        recovery_id = str(uuid4())
        
        # Start with first percentage
        if traffic_percentages:
            first_percentage = traffic_percentages[0]
            self.circuits[provider]["recovery_percentage"] = first_percentage
            self.circuits[provider]["recovery_id"] = recovery_id
            
            # Schedule recovery progression (simplified)
            asyncio.create_task(self._progress_recovery(provider, traffic_percentages[1:], recovery_id))
        
        return {
            "success": True,
            "recovery_id": recovery_id,
            "current_percentage": traffic_percentages[0] if traffic_percentages else 0
        }
    
    async def _progress_recovery(self, provider: str, remaining_percentages: List[float], recovery_id: str):
        """Progress through recovery percentages"""
        # Wait between progression steps
        await asyncio.sleep(300)  # 5 minutes
        
        if remaining_percentages and provider in self.circuits:
            circuit = self.circuits[provider]
            if circuit.get("recovery_id") == recovery_id:  # Still active recovery
                next_percentage = remaining_percentages[0]
                circuit["recovery_percentage"] = next_percentage
                
                # Continue with remaining percentages
                if len(remaining_percentages) > 1:
                    asyncio.create_task(self._progress_recovery(provider, remaining_percentages[1:], recovery_id))
                else:
                    # Recovery complete
                    await self._transition_to_closed(provider)
                    circuit.pop("recovery_percentage", None)
                    circuit.pop("recovery_id", None)
    
    def is_italian_market_hours(self) -> bool:
        """Check if current time is during Italian business hours"""
        now = datetime.utcnow()
        # Convert to Italian time (UTC+1/+2)
        italian_hour = (now.hour + 1) % 24  # Simplified, doesn't account for DST
        
        # Italian business hours: 9 AM to 6 PM
        return 9 <= italian_hour <= 18
    
    def is_august_vacation(self) -> bool:
        """Check if current date is during Italian August vacation period"""
        now = datetime.utcnow()
        return now.month == 8
    
    def is_tax_deadline_period(self) -> bool:
        """Check if current date is during tax deadline periods"""
        now = datetime.utcnow()
        # Italian tax deadlines are typically in July and November
        return now.month in [7, 11]
    
    async def apply_italian_market_rules(self, provider: str) -> Dict[str, Any]:
        """Apply Italian market-specific circuit breaker rules"""
        if provider not in self.circuits:
            await self.get_circuit_status(provider)
        
        circuit = self.circuits[provider]
        adjustments = {}
        
        # Adjust thresholds based on market conditions
        if self.is_august_vacation():
            # More lenient during vacation period
            adjustments["failure_threshold_multiplier"] = 1.5
            adjustments["reason"] = "august_vacation_adjustment"
        
        elif self.is_tax_deadline_period():
            # More strict during high-demand periods
            adjustments["failure_threshold_multiplier"] = 0.7
            adjustments["reason"] = "tax_deadline_adjustment"
        
        elif not self.is_italian_market_hours():
            # Different rules outside business hours
            adjustments["failure_threshold_multiplier"] = 1.2
            adjustments["reason"] = "off_hours_adjustment"
        
        else:
            # Standard business hours
            adjustments["failure_threshold_multiplier"] = 1.0
            adjustments["reason"] = "standard_hours"
        
        # Apply cost adjustments for Italian market
        if self.is_tax_deadline_period():
            # Increase cost limits during high-demand periods
            circuit["cost_limit"] = circuit.get("base_cost_limit", 100.0) * 1.5
        else:
            circuit["cost_limit"] = circuit.get("base_cost_limit", 100.0)
        
        return adjustments
    
    async def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics for all providers"""
        metrics = {
            "total_providers": len(self.circuits),
            "providers": {},
            "overall_health": 0.0,
            "alerts": []
        }
        
        total_health = 0.0
        for provider, circuit in self.circuits.items():
            health_score = self._calculate_health_score(circuit)
            
            provider_metrics = {
                "health_score": health_score,
                "state": circuit["state"].value,
                "success_rate": circuit["success_count"] / max(circuit["total_requests"], 1),
                "failure_count": circuit["failure_count"],
                "cost_utilization": circuit["cost_spent"] / circuit["cost_limit"],
                "last_failure_time": circuit["last_failure_time"].isoformat() if circuit["last_failure_time"] else None,
                "last_success_time": circuit["last_success_time"].isoformat() if circuit["last_success_time"] else None
            }
            
            metrics["providers"][provider] = provider_metrics
            total_health += health_score
            
            # Generate alerts
            if health_score < 0.3:
                metrics["alerts"].append({
                    "severity": "critical",
                    "provider": provider,
                    "message": f"Provider {provider} has critically low health score: {health_score:.2f}"
                })
            elif circuit["state"] == CircuitState.OPEN:
                metrics["alerts"].append({
                    "severity": "warning",
                    "provider": provider,
                    "message": f"Circuit breaker is OPEN for provider {provider}"
                })
            elif circuit["cost_spent"] / circuit["cost_limit"] > 0.9:
                metrics["alerts"].append({
                    "severity": "warning",
                    "provider": provider,
                    "message": f"Provider {provider} approaching cost limit: {circuit['cost_spent']:.2f}/{circuit['cost_limit']:.2f}"
                })
        
        metrics["overall_health"] = total_health / len(self.circuits) if self.circuits else 1.0
        
        return metrics
    
    async def generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts based on current circuit states and health"""
        alerts = []
        
        for provider, circuit in self.circuits.items():
            health_score = self._calculate_health_score(circuit)
            
            # Critical health alert
            if health_score < 0.3:
                alerts.append({
                    "id": f"health_{provider}_{int(time.time())}",
                    "severity": "critical",
                    "provider": provider,
                    "type": "health_degradation",
                    "message": f"Critical health degradation for {provider}: {health_score:.2f}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "health_score": health_score,
                        "failure_count": circuit["failure_count"],
                        "success_count": circuit["success_count"]
                    }
                })
            
            # Circuit state alerts
            if circuit["state"] == CircuitState.OPEN:
                alerts.append({
                    "id": f"circuit_{provider}_{int(time.time())}",
                    "severity": "error",
                    "provider": provider,
                    "type": "circuit_open",
                    "message": f"Circuit breaker OPEN for {provider}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "state": circuit["state"].value,
                        "failure_count": circuit["failure_count"]
                    }
                })
            
            # Cost limit alerts
            cost_utilization = circuit["cost_spent"] / circuit["cost_limit"]
            if cost_utilization > 0.9:
                alerts.append({
                    "id": f"cost_{provider}_{int(time.time())}",
                    "severity": "warning",
                    "provider": provider,
                    "type": "cost_limit_approaching",
                    "message": f"Cost limit approaching for {provider}: {cost_utilization:.1%}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "cost_spent": circuit["cost_spent"],
                        "cost_limit": circuit["cost_limit"],
                        "utilization": cost_utilization
                    }
                })
        
        return alerts
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all circuit breakers"""
        stats = {
            "total_circuits": len(self.circuits),
            "states_distribution": {state.value: 0 for state in CircuitState},
            "total_requests": 0,
            "total_successes": 0,
            "total_failures": 0,
            "total_cost_spent": 0.0,
            "average_health_score": 0.0
        }
        
        total_health = 0.0
        
        for provider, circuit in self.circuits.items():
            # State distribution
            state = circuit["state"].value
            stats["states_distribution"][state] += 1
            
            # Request stats
            stats["total_requests"] += circuit["total_requests"]
            stats["total_successes"] += circuit["success_count"]
            stats["total_failures"] += int(circuit["failure_count"])
            stats["total_cost_spent"] += circuit["cost_spent"]
            
            # Health score
            health = self._calculate_health_score(circuit)
            total_health += health
        
        if self.circuits:
            stats["average_health_score"] = total_health / len(self.circuits)
            stats["overall_success_rate"] = stats["total_successes"] / max(stats["total_requests"], 1)
        
        return stats