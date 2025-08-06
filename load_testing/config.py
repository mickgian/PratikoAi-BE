"""
Load Testing Configuration for PratikoAI.

This module defines configuration for load testing the system
to validate it can handle 50-100 concurrent users.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os
from enum import Enum


class LoadTestProfile(str, Enum):
    """Pre-defined load test profiles"""
    BASELINE = "baseline"
    NORMAL_DAY = "normal_day"
    PEAK_HOURS = "peak_hours"
    TAX_DEADLINE = "tax_deadline"
    STRESS_TEST = "stress_test"
    SPIKE_TEST = "spike_test"


@dataclass
class LoadTestConfig:
    """Configuration for load testing scenarios"""
    
    # Target metrics based on €25k ARR (50-100 customers)
    target_users: int = 50
    max_users: int = 100
    ramp_up_time: int = 60  # seconds
    test_duration: int = 300  # 5 minutes sustained
    
    # Performance SLAs
    target_p95_response_time: float = 3.0  # seconds for single user
    target_p95_response_time_50_users: float = 5.0  # seconds for 50 users
    target_p95_response_time_100_users: float = 8.0  # seconds for 100 users
    target_p99_response_time: float = 5.0
    target_error_rate: float = 0.01  # 1%
    target_throughput: int = 1000  # requests/minute
    target_cache_hit_rate: float = 0.7  # 70%
    
    # Test scenarios with weights
    scenarios: Dict[str, float] = field(default_factory=lambda: {
        "simple_query": 0.3,      # 30% - Simple FAQ-answerable queries
        "complex_query": 0.25,    # 25% - Complex LLM queries
        "tax_calculation": 0.2,   # 20% - Italian tax calculations
        "document_upload": 0.1,   # 10% - PDF processing
        "knowledge_search": 0.1,  # 10% - Regulatory searches
        "user_operations": 0.05   # 5% - Login, profile, settings
    })
    
    # Infrastructure limits
    max_db_connections: int = 100
    max_redis_connections: int = 200
    max_memory_gb: float = 8.0
    max_cpu_percent: float = 80.0
    max_disk_io_mbps: float = 100.0
    
    # Monitoring configuration
    monitor_interval: int = 5  # seconds
    collect_metrics: bool = True
    save_results: bool = True
    results_dir: str = "load_test_results"
    
    # Test behavior
    think_time_min: float = 1.0  # seconds
    think_time_max: float = 3.0  # seconds
    request_timeout: float = 30.0  # seconds
    
    # Italian market specific
    italian_tax_types: List[str] = field(default_factory=lambda: [
        "IVA", "IRPEF", "IMU", "TASI", "TARI"
    ])
    italian_document_types: List[str] = field(default_factory=lambda: [
        "fattura_elettronica", "f24", "dichiarazione_redditi", "contratto"
    ])
    italian_regions: List[str] = field(default_factory=lambda: [
        "Lombardia", "Lazio", "Campania", "Veneto", "Emilia-Romagna"
    ])


class LoadTestProfiles:
    """Pre-configured load testing profiles for different scenarios"""
    
    BASELINE = LoadTestConfig(
        target_users=1,
        max_users=1,
        test_duration=60,
        ramp_up_time=0,
        scenarios={
            "simple_query": 0.4,
            "complex_query": 0.3,
            "tax_calculation": 0.2,
            "knowledge_search": 0.1
        }
    )
    
    NORMAL_DAY = LoadTestConfig(
        target_users=30,
        max_users=30,
        test_duration=600,  # 10 minutes
        ramp_up_time=60,
        scenarios={
            "simple_query": 0.4,
            "complex_query": 0.3,
            "tax_calculation": 0.15,
            "knowledge_search": 0.1,
            "user_operations": 0.05
        }
    )
    
    PEAK_HOURS = LoadTestConfig(
        target_users=50,
        max_users=50,
        test_duration=300,  # 5 minutes
        ramp_up_time=60,
        scenarios={
            "simple_query": 0.25,
            "complex_query": 0.25,
            "tax_calculation": 0.25,
            "document_upload": 0.15,
            "knowledge_search": 0.1
        }
    )
    
    TAX_DEADLINE = LoadTestConfig(
        target_users=100,
        max_users=100,
        test_duration=1800,  # 30 minutes
        ramp_up_time=120,
        scenarios={
            "tax_calculation": 0.4,
            "document_upload": 0.3,
            "complex_query": 0.2,
            "simple_query": 0.1
        }
    )
    
    STRESS_TEST = LoadTestConfig(
        target_users=150,
        max_users=200,
        test_duration=600,  # 10 minutes
        ramp_up_time=60,
        scenarios={
            "complex_query": 0.35,
            "tax_calculation": 0.3,
            "document_upload": 0.2,
            "knowledge_search": 0.1,
            "user_operations": 0.05
        }
    )
    
    SPIKE_TEST = LoadTestConfig(
        target_users=10,
        max_users=100,
        test_duration=600,  # 10 minutes
        ramp_up_time=10,   # Very fast ramp
        scenarios={
            "simple_query": 0.3,
            "complex_query": 0.3,
            "tax_calculation": 0.2,
            "knowledge_search": 0.15,
            "user_operations": 0.05
        }
    )
    
    @classmethod
    def get_profile(cls, profile_name: LoadTestProfile) -> LoadTestConfig:
        """Get a pre-configured load test profile"""
        profiles = {
            LoadTestProfile.BASELINE: cls.BASELINE,
            LoadTestProfile.NORMAL_DAY: cls.NORMAL_DAY,
            LoadTestProfile.PEAK_HOURS: cls.PEAK_HOURS,
            LoadTestProfile.TAX_DEADLINE: cls.TAX_DEADLINE,
            LoadTestProfile.STRESS_TEST: cls.STRESS_TEST,
            LoadTestProfile.SPIKE_TEST: cls.SPIKE_TEST
        }
        return profiles.get(profile_name, cls.NORMAL_DAY)


@dataclass
class EndpointConfig:
    """Configuration for specific endpoint testing"""
    path: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict] = None
    expected_status: int = 200
    max_response_time: float = 3.0
    weight: float = 1.0  # Relative frequency


# Endpoint configurations for Italian market
ITALIAN_ENDPOINTS = {
    "simple_query": EndpointConfig(
        path="/api/query",
        method="POST",
        body={"query": "Come calcolare l'IVA?"},
        max_response_time=3.0,
        weight=0.3
    ),
    "complex_query": EndpointConfig(
        path="/api/query",
        method="POST",
        body={
            "query": "Analizza le implicazioni fiscali di una SRL che diventa SPA",
            "context": "detailed"
        },
        max_response_time=5.0,
        weight=0.25
    ),
    "tax_calculation": EndpointConfig(
        path="/api/tax/calculate",
        method="POST",
        body={
            "type": "IVA",
            "amount": 10000,
            "region": "Lombardia"
        },
        max_response_time=2.0,
        weight=0.2
    ),
    "document_upload": EndpointConfig(
        path="/api/document/analyze",
        method="POST",
        max_response_time=30.0,
        weight=0.1
    ),
    "knowledge_search": EndpointConfig(
        path="/api/knowledge/search",
        method="GET",
        max_response_time=3.0,
        weight=0.1
    ),
    "user_profile": EndpointConfig(
        path="/api/user/profile",
        method="GET",
        max_response_time=1.0,
        weight=0.05
    )
}


# Environment-specific configurations
def get_environment_config() -> Dict[str, str]:
    """Get environment-specific configuration"""
    return {
        "base_url": os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8000"),
        "auth_token": os.getenv("LOAD_TEST_AUTH_TOKEN", ""),
        "database_url": os.getenv("DATABASE_URL", "postgresql://localhost/pratikoai"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "prometheus_url": os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
        "grafana_url": os.getenv("GRAFANA_URL", "http://localhost:3000")
    }


# Test data generators
class TestDataGenerator:
    """Generate realistic test data for Italian market"""
    
    @staticmethod
    def generate_italian_queries() -> List[str]:
        """Generate realistic Italian tax/regulatory queries"""
        return [
            "Come calcolare l'IVA al 22%?",
            "Quali sono le aliquote IRPEF 2024?",
            "Scadenze fiscali per SRL",
            "Regime forfettario requisiti",
            "Fattura elettronica obblighi",
            "Deduzione spese mediche",
            "Bonus edilizi 2024",
            "Calcolo IMU prima casa",
            "Tassazione dividendi SRL",
            "Contributi INPS artigiani"
        ]
    
    @staticmethod
    def generate_tax_calculation_requests() -> List[Dict]:
        """Generate tax calculation test requests"""
        import random
        
        requests = []
        tax_types = ["IVA", "IRPEF", "IMU", "TASI"]
        regions = ["Lombardia", "Lazio", "Campania", "Veneto"]
        
        for _ in range(100):
            requests.append({
                "type": random.choice(tax_types),
                "amount": random.randint(1000, 100000),
                "region": random.choice(regions),
                "year": 2024
            })
        
        return requests
    
    @staticmethod
    def generate_test_users(count: int = 200) -> List[Dict]:
        """Generate test user accounts"""
        users = []
        for i in range(count):
            users.append({
                "email": f"loadtest_user_{i}@pratikoai.it",
                "password": "TestPassword123!",
                "company_name": f"Test Company {i}",
                "vat_number": f"IT{str(i).zfill(11)}"
            })
        return users