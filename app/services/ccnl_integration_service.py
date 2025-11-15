"""CCNL Integration Service - Main orchestrator for CCNL chat integration.

This service coordinates between all CCNL components to provide a unified
interface for natural language queries about Italian labor agreements.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.langgraph.tools.ccnl_tool import ccnl_tool
from app.core.logging import logger
from app.core.monitoring.metrics import track_ccnl_query
from app.services.ccnl_response_formatter import ccnl_response_formatter
from app.services.domain_action_classifier import Action, Domain, DomainActionClassifier
from app.services.vector_service import vector_service


class CCNLIntegrationService:
    """Main service for CCNL integration with PratikoAI chat system."""

    def __init__(self):
        self.domain_classifier = DomainActionClassifier()
        self.ccnl_examples = self._load_example_queries()

    def _load_example_queries(self) -> list[dict[str, Any]]:
        """Load example queries for testing and demonstrations."""
        return [
            {
                "user_query": "Qual è lo stipendio medio di un operaio metalmeccanico a Milano?",
                "expected_classification": {"domain": Domain.LABOR, "action": Action.CCNL_QUERY},
                "expected_tool_params": {
                    "query_type": "salary_calculation",
                    "sector": "metalmeccanico",
                    "job_category": "operaio",
                    "geographic_area": "nord",
                },
            },
            {
                "user_query": "Quanti giorni di ferie ha un impiegato nel commercio con 5 anni di esperienza?",
                "expected_classification": {"domain": Domain.LABOR, "action": Action.CCNL_QUERY},
                "expected_tool_params": {
                    "query_type": "leave_calculation",
                    "sector": "commercio",
                    "job_category": "impiegato",
                    "experience_years": 5,
                },
            },
            {
                "user_query": "Confronta gli stipendi tra edilizia e metalmeccanico per un operaio",
                "expected_classification": {"domain": Domain.LABOR, "action": Action.CCNL_QUERY},
                "expected_tool_params": {
                    "query_type": "comparison",
                    "sectors": ["edilizia", "metalmeccanico"],
                    "job_category": "operaio",
                },
            },
            {
                "user_query": "Quanto preavviso devo dare per dimettermi se lavoro nel tessile da 3 anni?",
                "expected_classification": {"domain": Domain.LABOR, "action": Action.CCNL_QUERY},
                "expected_tool_params": {"query_type": "notice_period", "sector": "tessile", "experience_years": 3},
            },
            {
                "user_query": "Cerca informazioni sui contratti del settore bancario",
                "expected_classification": {"domain": Domain.LABOR, "action": Action.CCNL_QUERY},
                "expected_tool_params": {
                    "query_type": "search",
                    "sector": "bancario",
                    "search_terms": "contratti settore bancario",
                },
            },
        ]

    async def process_ccnl_query(
        self, user_query: str, user_id: str | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """Process a user query that may be CCNL-related.

        Args:
            user_query: Natural language query from user
            user_id: User ID for tracking
            session_id: Session ID for tracking

        Returns:
            Dict containing response and metadata
        """
        try:
            # Classify the query to determine if it's CCNL-related
            classification = await self.domain_classifier.classify(user_query)

            logger.info(
                "ccnl_query_processed",
                query=user_query[:100],
                domain=classification.domain.value,
                action=classification.action.value,
                confidence=classification.confidence,
                user_id=user_id,
                session_id=session_id,
            )

            # Check if this is a CCNL query
            is_ccnl_query = classification.domain == Domain.LABOR and (
                classification.action == Action.CCNL_QUERY or classification.confidence > 0.8
            )

            if not is_ccnl_query:
                return {
                    "is_ccnl_query": False,
                    "should_use_ccnl_tool": False,
                    "classification": {
                        "domain": classification.domain.value,
                        "action": classification.action.value,
                        "confidence": classification.confidence,
                    },
                    "message": "Query not identified as CCNL-related",
                }

            # Extract parameters for CCNL tool
            tool_params = self._extract_ccnl_parameters(user_query, classification)

            # Execute CCNL query using the tool
            ccnl_response = await ccnl_tool._arun(**tool_params)

            return {
                "is_ccnl_query": True,
                "should_use_ccnl_tool": True,
                "classification": {
                    "domain": classification.domain.value,
                    "action": classification.action.value,
                    "confidence": classification.confidence,
                    "sub_domain": classification.sub_domain,
                },
                "tool_params": tool_params,
                "ccnl_response": ccnl_response,
                "formatted": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("ccnl_query_processing_failed", query=user_query[:100], error=str(e), exc_info=True)
            return {
                "is_ccnl_query": False,
                "should_use_ccnl_tool": False,
                "error": f"CCNL query processing failed: {str(e)}",
                "message": "Errore durante l'elaborazione della query CCNL",
            }

    def _extract_ccnl_parameters(self, user_query: str, classification) -> dict[str, Any]:
        """Extract parameters for CCNL tool from user query and classification.

        Args:
            user_query: Original user query
            classification: Domain-action classification result

        Returns:
            Parameters for CCNL tool
        """
        query_lower = user_query.lower()

        # Determine query type based on keywords and action
        query_type = "search"  # Default

        if any(word in query_lower for word in ["stipendio", "salario", "guadagna", "quanto costa", "retribuzione"]):
            query_type = "salary_calculation"
        elif any(word in query_lower for word in ["ferie", "permessi", "congedo", "giorni", "vacanza"]):
            query_type = "leave_calculation"
        elif any(word in query_lower for word in ["preavviso", "dimissioni", "licenziamento", "terminare"]):
            query_type = "notice_period"
        elif any(word in query_lower for word in ["confronta", "paragona", "differenze", "migliore"]):
            query_type = "comparison"
        elif any(word in query_lower for word in ["informazioni", "contratti", "settore", "cerca"]):
            if classification.action == Action.CCNL_QUERY:
                query_type = "sector_info"

        # Extract sector
        sector = None
        sector_keywords = {
            "metalmeccanico": ["metalmeccanico", "metalmeccanica", "metallurgia", "meccanica"],
            "edilizia": ["edilizia", "costruzioni", "cantiere", "muratore"],
            "commercio": ["commercio", "negozio", "vendita", "retail", "commesso"],
            "tessile": ["tessile", "abbigliamento", "moda", "sartoria"],
            "chimico": ["chimico", "chimica", "farmaceutico", "petrolchimico"],
            "alimentare": ["alimentare", "cibo", "ristorante", "cuoco"],
            "trasporti": ["trasporti", "camionista", "autista", "logistica"],
            "bancario": ["bancario", "banca", "credito", "finanziario"],
            "assicurazioni": ["assicurazioni", "polizze", "assicurativo"],
        }

        for sector_name, keywords in sector_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                sector = sector_name
                break

        # Extract job category
        job_category = None
        if any(word in query_lower for word in ["operaio", "operai"]):
            job_category = "operaio"
        elif any(word in query_lower for word in ["impiegato", "impiegati", "employee"]):
            job_category = "impiegato"
        elif any(word in query_lower for word in ["dirigente", "manager", "direttore"]):
            job_category = "dirigente"
        elif any(word in query_lower for word in ["apprendista", "tirocinante"]):
            job_category = "apprendista"

        # Extract geographic area
        geographic_area = None
        north_cities = ["milano", "torino", "genova", "bologna", "venezia", "nord"]
        center_cities = ["roma", "firenze", "ancona", "perugia", "centro"]
        south_cities = ["napoli", "bari", "catanzaro", "sud", "meridione"]

        if any(city in query_lower for city in north_cities):
            geographic_area = "nord"
        elif any(city in query_lower for city in center_cities):
            geographic_area = "centro"
        elif any(city in query_lower for city in south_cities):
            geographic_area = "sud"

        # Extract experience years
        experience_years = None
        import re

        experience_match = re.search(r"(\d+)\s*ann[oi]", query_lower)
        if experience_match:
            experience_years = int(experience_match.group(1))

        return {
            "query_type": query_type,
            "sector": sector,
            "job_category": job_category,
            "geographic_area": geographic_area,
            "experience_years": experience_years,
            "search_terms": user_query if query_type in ["search", "sector_info"] else None,
        }

    async def test_integration(self) -> dict[str, Any]:
        """Test CCNL integration with example queries.

        Returns:
            Test results summary
        """
        logger.info("ccnl_integration_test_started")

        test_results = {
            "total_tests": len(self.ccnl_examples),
            "passed": 0,
            "failed": 0,
            "results": [],
            "vector_service_available": vector_service.is_available(),
        }

        for i, example in enumerate(self.ccnl_examples):
            try:
                logger.info(f"ccnl_test_{i + 1}_started", query=example["user_query"])

                result = await self.process_ccnl_query(
                    user_query=example["user_query"], user_id="test_user", session_id=f"test_session_{i + 1}"
                )

                test_result = {
                    "test_id": i + 1,
                    "query": example["user_query"],
                    "success": result.get("is_ccnl_query", False),
                    "classification": result.get("classification", {}),
                    "tool_params": result.get("tool_params", {}),
                    "has_response": bool(result.get("ccnl_response")),
                    "error": result.get("error"),
                }

                if test_result["success"] and test_result["has_response"]:
                    test_results["passed"] += 1
                    logger.info(f"ccnl_test_{i + 1}_passed")
                else:
                    test_results["failed"] += 1
                    logger.warning(f"ccnl_test_{i + 1}_failed", error=test_result["error"])

                test_results["results"].append(test_result)

            except Exception as e:
                test_results["failed"] += 1
                error_result = {"test_id": i + 1, "query": example["user_query"], "success": False, "error": str(e)}
                test_results["results"].append(error_result)
                logger.error(f"ccnl_test_{i + 1}_exception", error=str(e))

        logger.info(
            "ccnl_integration_test_completed",
            total=test_results["total_tests"],
            passed=test_results["passed"],
            failed=test_results["failed"],
            success_rate=test_results["passed"] / test_results["total_tests"],
        )

        return test_results

    def get_integration_status(self) -> dict[str, Any]:
        """Get current status of CCNL integration components.

        Returns:
            Status of all integration components
        """
        try:
            return {
                "ccnl_tool_available": ccnl_tool is not None,
                "domain_classifier_available": self.domain_classifier is not None,
                "response_formatter_available": ccnl_response_formatter is not None,
                "vector_service_available": vector_service.is_available(),
                "example_queries_loaded": len(self.ccnl_examples),
                "supported_query_types": [
                    "salary_calculation",
                    "leave_calculation",
                    "notice_period",
                    "comparison",
                    "search",
                    "sector_info",
                ],
                "supported_sectors": [
                    "metalmeccanico",
                    "edilizia",
                    "commercio",
                    "tessile",
                    "chimico",
                    "alimentare",
                    "trasporti",
                    "bancario",
                    "assicurazioni",
                ],
                "integration_ready": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("ccnl_integration_status_check_failed", error=str(e))
            return {"integration_ready": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}


# Global instance
ccnl_integration_service = CCNLIntegrationService()
