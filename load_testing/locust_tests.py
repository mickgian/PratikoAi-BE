"""
Locust Load Testing Implementation for PratikoAI.

This module implements load testing using Locust framework to simulate
realistic user behavior for 50-100 concurrent Italian tax/accounting users.
"""

from locust import HttpUser, task, between, events, LoadTestShape
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import random
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from load_testing.config import (
    LoadTestConfig,
    LoadTestProfiles,
    TestDataGenerator,
    ITALIAN_ENDPOINTS
)

logger = logging.getLogger(__name__)


class PratikoAIUser(HttpUser):
    """Simulated PratikoAI user for load testing"""
    
    wait_time = between(1, 3)  # Realistic user think time
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_data = TestDataGenerator()
        self.queries = self.test_data.generate_italian_queries()
        self.tax_requests = self.test_data.generate_tax_calculation_requests()
        self.token = None
        self.user_id = None
        
    def on_start(self):
        """Login and setup user session"""
        # Try to login with existing test user or create new one
        user_num = random.randint(1, 200)
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": f"loadtest_user_{user_num}@pratikoai.it",
                "password": "TestPassword123!"
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.user_id = data.get("user_id")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            response.success()
        else:
            # Try to register if login fails
            self._register_user(user_num)
    
    def _register_user(self, user_num: int):
        """Register a new test user"""
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": f"loadtest_user_{user_num}@pratikoai.it",
                "password": "TestPassword123!",
                "company_name": f"Test Company {user_num}",
                "vat_number": f"IT{str(user_num).zfill(11)}"
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            self.token = data.get("token")
            self.user_id = data.get("user_id")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
    
    @task(30)  # Weight: 30% of requests
    def simple_query(self):
        """Test FAQ-answerable queries"""
        query = random.choice(self.queries[:5])  # Simple queries
        
        start_time = time.time()
        with self.client.post(
            "/api/query",
            json={"query": query},
            catch_response=True,
            name="/api/query [simple]"
        ) as response:
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                # Check if response is from cache
                if response.headers.get('X-Cache-Hit') == 'true':
                    events.request_success.fire(
                        request_type="CACHE_HIT",
                        name="/api/query [simple]",
                        response_time=response_time * 1000,
                        response_length=len(response.content)
                    )
                
                # Validate response time SLA
                if response_time > 3.0:
                    response.failure(f"Simple query took {response_time:.2f}s (SLA: 3s)")
                else:
                    response.success()
            else:
                response.failure(f"Status code {response.status_code}")
    
    @task(25)  # Weight: 25% of requests
    def complex_query(self):
        """Test complex LLM queries"""
        complex_queries = [
            "Analizza le implicazioni fiscali di una SRL che diventa SPA",
            "Come ottimizzare la tassazione per un freelancer con partita IVA?",
            "Quali sono le novità fiscali per il 2024 in Italia?",
            "Confronta regime forfettario e regime ordinario per fatturato 50k€",
            "Strategie di pianificazione fiscale per startup innovative"
        ]
        
        query = random.choice(complex_queries)
        
        with self.client.post(
            "/api/query",
            json={
                "query": query,
                "context": "detailed",
                "include_sources": True
            },
            catch_response=True,
            timeout=30,
            name="/api/query [complex]"
        ) as response:
            if response.status_code == 200:
                # Complex queries can take longer
                if response.elapsed.total_seconds() > 5.0:
                    response.failure(f"Complex query took {response.elapsed.total_seconds():.2f}s (SLA: 5s)")
                else:
                    response.success()
                    
                # Verify response quality
                data = response.json()
                if len(data.get("response", "")) < 100:
                    response.failure("Response too short for complex query")
            else:
                response.failure(f"Status code {response.status_code}")
    
    @task(20)  # Weight: 20% of requests
    def tax_calculation(self):
        """Test Italian tax calculations"""
        tax_request = random.choice(self.tax_requests)
        
        with self.client.post(
            "/api/tax/calculate",
            json=tax_request,
            catch_response=True,
            name=f"/api/tax/calculate [{tax_request['type']}]"
        ) as response:
            if response.status_code == 200:
                # Validate calculation time
                if response.elapsed.total_seconds() > 2.0:
                    response.failure(f"Tax calculation took {response.elapsed.total_seconds():.2f}s (SLA: 2s)")
                else:
                    response.success()
                
                # Basic validation of results
                data = response.json()
                if "result" not in data or "breakdown" not in data:
                    response.failure("Invalid tax calculation response")
            else:
                response.failure(f"Status code {response.status_code}")
    
    @task(10)  # Weight: 10% of requests
    def document_upload(self):
        """Test document processing (simulated)"""
        # Simulate different document types
        doc_types = ["fattura_elettronica", "f24", "dichiarazione_redditi", "contratto"]
        doc_type = random.choice(doc_types)
        
        # Create mock PDF content
        mock_pdf_content = b"PDF-MOCK-CONTENT" * 1000  # ~16KB
        
        files = {
            "file": (f"test_{doc_type}.pdf", mock_pdf_content, "application/pdf")
        }
        
        data = {
            "document_type": doc_type,
            "extract_data": True
        }
        
        with self.client.post(
            "/api/document/analyze",
            files=files,
            data=data,
            catch_response=True,
            timeout=60,
            name=f"/api/document/analyze [{doc_type}]"
        ) as response:
            if response.status_code == 200:
                # Document processing can take up to 30s
                if response.elapsed.total_seconds() > 30.0:
                    response.failure(f"Document processing took {response.elapsed.total_seconds():.2f}s (SLA: 30s)")
                else:
                    response.success()
            else:
                response.failure(f"Status code {response.status_code}")
    
    @task(10)  # Weight: 10% of requests
    def knowledge_search(self):
        """Test regulatory knowledge searches"""
        search_terms = [
            "Circolare Agenzia Entrate 2024",
            "Decreto fiscale ultimo",
            "Normativa fatturazione elettronica",
            "Aliquote IVA settori",
            "Scadenze dichiarazioni 2024"
        ]
        
        search_query = random.choice(search_terms)
        
        with self.client.get(
            f"/api/knowledge/search",
            params={
                "q": search_query,
                "limit": 10,
                "include_context": True
            },
            catch_response=True,
            name="/api/knowledge/search"
        ) as response:
            if response.status_code == 200:
                if response.elapsed.total_seconds() > 3.0:
                    response.failure(f"Knowledge search took {response.elapsed.total_seconds():.2f}s (SLA: 3s)")
                else:
                    response.success()
                
                # Verify search results
                data = response.json()
                if not data.get("results"):
                    response.failure("No search results returned")
            else:
                response.failure(f"Status code {response.status_code}")
    
    @task(5)  # Weight: 5% of requests
    def user_operations(self):
        """Test user profile operations"""
        operations = [
            ("GET", "/api/user/profile", None),
            ("GET", "/api/user/subscription", None),
            ("GET", "/api/user/usage", None),
            ("PUT", "/api/user/settings", {"notifications": random.choice([True, False])}),
            ("GET", "/api/user/invoices", None)
        ]
        
        method, endpoint, data = random.choice(operations)
        
        if method == "GET":
            with self.client.get(
                endpoint,
                catch_response=True,
                name=endpoint
            ) as response:
                if response.status_code == 200:
                    if response.elapsed.total_seconds() > 1.0:
                        response.failure(f"User operation took {response.elapsed.total_seconds():.2f}s (SLA: 1s)")
                    else:
                        response.success()
                else:
                    response.failure(f"Status code {response.status_code}")
        else:  # PUT
            with self.client.put(
                endpoint,
                json=data,
                catch_response=True,
                name=endpoint
            ) as response:
                if response.status_code in [200, 204]:
                    response.success()
                else:
                    response.failure(f"Status code {response.status_code}")
    
    def on_stop(self):
        """Cleanup on user stop"""
        # Log out if needed
        if self.token:
            try:
                self.client.post("/api/auth/logout")
            except:
                pass


class StressTestUser(PratikoAIUser):
    """User behavior for stress testing"""
    
    wait_time = between(0.5, 1.5)  # More aggressive
    
    @task(40)
    def heavy_operations(self):
        """Focus on resource-intensive operations"""
        # More complex queries
        self.complex_query()
    
    @task(30)
    def concurrent_calculations(self):
        """Multiple tax calculations"""
        self.tax_calculation()
    
    @task(30)
    def document_processing(self):
        """Heavy document processing"""
        self.document_upload()


class CustomLoadShape(LoadTestShape):
    """
    Custom load shape for different test scenarios.
    Implements various patterns like ramp-up, spike, and sustained load.
    """
    
    def __init__(self):
        super().__init__()
        self.test_profile = LoadTestProfiles.PEAK_HOURS  # Default profile
        
    def tick(self):
        """
        Returns user count and spawn rate at each tick.
        Returns None to stop the test.
        """
        run_time = self.get_run_time()
        
        # Implement stepped load increase
        if run_time < 60:
            # Ramp up phase
            user_count = int((run_time / 60) * self.test_profile.target_users)
            spawn_rate = 2
        elif run_time < self.test_profile.test_duration - 60:
            # Sustained load
            user_count = self.test_profile.target_users
            spawn_rate = 1
        elif run_time < self.test_profile.test_duration:
            # Ramp down phase
            remaining = self.test_profile.test_duration - run_time
            user_count = int((remaining / 60) * self.test_profile.target_users)
            spawn_rate = 2
        else:
            # Test complete
            return None
        
        return (user_count, spawn_rate)


class SpikeLoadShape(LoadTestShape):
    """Load shape for spike testing"""
    
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 1},     # Normal load
        {"duration": 10, "users": 100, "spawn_rate": 20},   # Spike!
        {"duration": 300, "users": 100, "spawn_rate": 1},   # Sustained spike
        {"duration": 60, "users": 10, "spawn_rate": 5},     # Recovery
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
            run_time -= stage["duration"]
        
        return None


# Event handlers for detailed metrics collection
@events.request_success.add_listener
def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """Track successful requests for analysis"""
    # Could send to monitoring system
    logger.debug(f"Success: {name} in {response_time}ms")


@events.request_failure.add_listener
def on_request_failure(request_type, name, response_time, exception, **kwargs):
    """Track failed requests for analysis"""
    logger.warning(f"Failure: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment"""
    logger.info(f"Load test starting with {environment.parsed_options.num_users} users")
    
    # Could initialize monitoring connections here


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup and generate reports"""
    logger.info("Load test completed")
    
    # Generate summary statistics
    stats = environment.stats
    total_rps = stats.total.current_rps
    total_fail_ratio = stats.total.fail_ratio
    
    logger.info(f"Total RPS: {total_rps}")
    logger.info(f"Failure rate: {total_fail_ratio * 100:.2f}%")
    
    # Could save detailed metrics here


# Custom failure tracking
class DetailedStats:
    """Track detailed statistics beyond Locust defaults"""
    
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.retry_successes = 0
        self.retry_failures = 0
        self.circuit_breaker_opens = 0
        
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1
    
    @property
    def cache_hit_rate(self):
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0


# Global stats instance
detailed_stats = DetailedStats()