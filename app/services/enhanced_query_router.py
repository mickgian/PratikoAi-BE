"""Enhanced Query Router for PratikoAI.

Integrates domain-action classification with existing query processing pipeline
to provide intelligent routing and prompt selection for Italian professionals.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, Message, SystemMessage

from app.core.config import settings
from app.core.llm.factory import RoutingStrategy, get_llm_provider
from app.core.logging import logger
from app.services.cache import CacheService
from app.services.context_builder import ContextBuilder, QueryContext
from app.services.domain_action_classifier import DomainActionClassification, DomainActionClassifier
from app.services.domain_prompt_templates import PromptTemplateManager


class EnhancedQueryResponse:
    """Enhanced response with classification metadata"""

    def __init__(
        self,
        content: str,
        classification: DomainActionClassification,
        context_used: QueryContext | None = None,
        processing_time_ms: int = 0,
        model_used: str = "",
        cost_eur: float = 0.0,
        cache_hit: bool = False,
    ):
        self.content = content
        self.classification = classification
        self.context_used = context_used
        self.processing_time_ms = processing_time_ms
        self.model_used = model_used
        self.cost_eur = cost_eur
        self.cache_hit = cache_hit
        self.timestamp = datetime.utcnow()


class EnhancedQueryRouter:
    """Main query router that integrates classification, prompt templates,
    context enrichment, and LLM selection for optimal responses.
    """

    def __init__(self):
        self.settings = settings
        self.classifier = DomainActionClassifier()
        self.prompt_manager = PromptTemplateManager()
        self.context_builder = ContextBuilder()
        self.cache_service = CacheService()

        # Performance and cost optimization settings
        self.max_classification_time_ms = 100
        self.max_context_building_time_ms = 300
        self.max_total_processing_time_ms = 5000

    async def process_query(
        self, query: str, user_context: dict[str, Any] | None = None, enable_cache: bool = True
    ) -> EnhancedQueryResponse:
        """Process query through complete enhanced pipeline.

        Args:
            query: User query in Italian
            user_context: Additional user context
            enable_cache: Whether to use caching

        Returns:
            Enhanced response with classification and metadata
        """
        start_time = time.time()

        try:
            # Step 1: Check cache first (if enabled)
            cache_key = None
            if enable_cache:
                cache_key = self._generate_cache_key(query, user_context)
                cached_response = await self.cache_service.get_cached_llm_response(cache_key)
                if cached_response:
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    return EnhancedQueryResponse(
                        content=cached_response["content"],
                        classification=DomainActionClassification(**cached_response["classification"]),
                        processing_time_ms=int((time.time() - start_time) * 1000),
                        cache_hit=True,
                    )

            # Step 2: Classify query (domain + action)
            classification_start = time.time()
            classification = await self.classifier.classify(query)
            classification_time = int((time.time() - classification_start) * 1000)

            logger.info(
                f"Query classified as {classification.domain.value}+{classification.action.value} "
                f"(confidence: {classification.confidence:.2f}, time: {classification_time}ms)"
            )

            # Step 3: Build enriched context
            context_start = time.time()
            context = await self._build_enhanced_context(query, classification, user_context)
            context_time = int((time.time() - context_start) * 1000)

            # Step 4: Select optimal LLM provider based on domain-action
            provider = self._select_llm_provider(classification, context)

            # Step 5: Generate domain-action specific prompt
            system_prompt = self.prompt_manager.get_prompt(
                domain=classification.domain,
                action=classification.action,
                query=query,
                context={
                    "user_context": user_context,
                    "regulatory_context": context.regulatory_sources if context else [],
                    "faq_context": context.faq_sources if context else [],
                },
                document_type=classification.document_type,
            )

            # Step 6: Execute LLM call
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=query)]

            llm_start = time.time()
            response = await provider.chat_completion(
                messages=messages,
                temperature=self._get_temperature_for_action(classification.action),
                max_tokens=self._get_max_tokens_for_action(classification.action),
            )
            llm_time = int((time.time() - llm_start) * 1000)

            # Step 7: Calculate costs and metrics
            total_time = int((time.time() - start_time) * 1000)
            estimated_cost = provider.estimate_cost(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            )

            # Step 8: Cache successful response
            if enable_cache and cache_key and response.content:
                cache_data = {
                    "content": response.content,
                    "classification": classification.dict(),
                    "model_used": provider.model,
                    "cost_eur": estimated_cost,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await self.cache_service.cache_llm_response(
                    cache_key, cache_data, ttl_seconds=self._get_cache_ttl_for_classification(classification)
                )

            # Step 9: Log performance metrics
            logger.info(
                f"Query processing completed: classification={classification_time}ms, "
                f"context={context_time}ms, llm={llm_time}ms, total={total_time}ms, "
                f"cost=€{estimated_cost:.4f}, model={provider.model}"
            )

            return EnhancedQueryResponse(
                content=response.content,
                classification=classification,
                context_used=context,
                processing_time_ms=total_time,
                model_used=provider.model,
                cost_eur=estimated_cost,
                cache_hit=False,
            )

        except Exception as e:
            logger.error(f"Enhanced query processing failed: {e}")
            # Fallback to basic processing
            return await self._fallback_processing(query, user_context)

    async def _build_enhanced_context(
        self, query: str, classification: DomainActionClassification, user_context: dict[str, Any] | None
    ) -> QueryContext | None:
        """Build context with domain-specific enhancements"""
        try:
            # Adjust context building based on classification
            max_sources = self._get_context_sources_for_classification(classification)
            context_types = self._get_context_types_for_domain(classification.domain)

            context = await self.context_builder.build_context(
                query=query,
                max_sources=max_sources,
                search_types=context_types,
                boost_recent=classification.action in ["compliance_check", "calculation_request"],
            )

            return context

        except Exception as e:
            logger.warning(f"Context building failed: {e}")
            return None

    def _select_llm_provider(self, classification: DomainActionClassification, context: QueryContext | None):
        """Select optimal LLM provider based on domain-action requirements"""
        # Map domain-action combinations to routing strategies
        strategy_map = {
            # High-accuracy requirements
            ("legal", "document_generation"): RoutingStrategy.QUALITY_FIRST,
            ("legal", "compliance_check"): RoutingStrategy.QUALITY_FIRST,
            ("tax", "calculation_request"): RoutingStrategy.QUALITY_FIRST,
            ("accounting", "document_analysis"): RoutingStrategy.QUALITY_FIRST,
            # Balanced requirements
            ("tax", "strategic_advice"): RoutingStrategy.BALANCED,
            ("business", "strategic_advice"): RoutingStrategy.BALANCED,
            ("labor", "compliance_check"): RoutingStrategy.BALANCED,
            # Cost-optimized for simple queries
            ("tax", "information_request"): RoutingStrategy.COST_OPTIMIZED,
            ("accounting", "information_request"): RoutingStrategy.COST_OPTIMIZED,
        }

        # Determine strategy
        key = (classification.domain.value, classification.action.value)
        strategy = strategy_map.get(key, RoutingStrategy.BALANCED)

        # Adjust cost limits based on complexity
        max_cost_eur = self._get_max_cost_for_classification(classification)

        # Use fallback if confidence is low
        if classification.confidence < 0.7:
            strategy = RoutingStrategy.FAILOVER

        return get_llm_provider(
            strategy=strategy, max_cost_eur=max_cost_eur, preferred_provider=self.settings.LLM_PREFERRED_PROVIDER
        )

    def _get_temperature_for_action(self, action) -> float:
        """Get optimal temperature setting for different actions"""
        temperature_map = {
            "calculation_request": 0.0,  # Deterministic calculations
            "compliance_check": 0.1,  # Precise legal answers
            "document_analysis": 0.1,  # Accurate analysis
            "information_request": 0.2,  # Informative but consistent
            "document_generation": 0.3,  # Some creativity in drafting
            "strategic_advice": 0.4,  # Creative strategic thinking
        }
        return temperature_map.get(action.value, 0.2)

    def _get_max_tokens_for_action(self, action) -> int:
        """Get optimal max tokens for different actions"""
        tokens_map = {
            "calculation_request": 1000,  # Concise calculations
            "information_request": 1500,  # Detailed information
            "compliance_check": 1500,  # Thorough compliance review
            "document_analysis": 2000,  # Comprehensive analysis
            "strategic_advice": 2500,  # Detailed advice
            "document_generation": 3000,  # Full document drafting
        }
        return tokens_map.get(action.value, 2000)

    def _get_context_sources_for_classification(self, classification: DomainActionClassification) -> int:
        """Determine optimal number of context sources"""
        if classification.action in ["document_generation", "strategic_advice"]:
            return 12  # More context for complex tasks
        elif classification.action in ["compliance_check", "document_analysis"]:
            return 10  # Good context for accuracy
        else:
            return 8  # Standard context

    def _get_context_types_for_domain(self, domain) -> list[str]:
        """Get relevant context types for each domain"""
        domain_context_map = {
            "tax": ["regulation", "faq", "circular"],
            "legal": ["regulation", "jurisprudence", "knowledge"],
            "labor": ["regulation", "faq", "circular"],
            "business": ["knowledge", "faq", "regulation"],
            "accounting": ["regulation", "knowledge", "faq"],
        }
        return domain_context_map.get(domain.value, ["faq", "knowledge"])

    def _get_max_cost_for_classification(self, classification: DomainActionClassification) -> float:
        """Determine cost limits based on classification"""
        base_costs = {
            "information_request": 0.005,
            "calculation_request": 0.008,
            "compliance_check": 0.015,
            "document_analysis": 0.020,
            "strategic_advice": 0.025,
            "document_generation": 0.030,
        }

        base_cost = base_costs.get(classification.action.value, 0.015)

        # Increase budget for legal and complex business queries
        if classification.domain in ["legal", "business"]:
            base_cost *= 1.5

        # Reduce budget for low confidence classifications
        if classification.confidence < 0.7:
            base_cost *= 0.7

        return min(base_cost, self.settings.LLM_MAX_COST_EUR)

    def _get_cache_ttl_for_classification(self, classification: DomainActionClassification) -> int:
        """Determine cache TTL based on classification"""
        # Information that changes frequently gets shorter TTL
        ttl_map = {
            "calculation_request": 3600,  # 1 hour (rates may change)
            "compliance_check": 7200,  # 2 hours (regulations change)
            "information_request": 86400,  # 24 hours (general info stable)
            "document_analysis": 14400,  # 4 hours (case-specific)
            "strategic_advice": 7200,  # 2 hours (context-dependent)
            "document_generation": 1800,  # 30 minutes (highly specific)
        }
        return ttl_map.get(classification.action.value, 7200)

    def _generate_cache_key(self, query: str, user_context: dict[str, Any] | None) -> str:
        """Generate cache key for query and context"""
        import hashlib

        # Create deterministic hash from query and relevant context
        cache_input = query.lower().strip()
        if user_context:
            # Include only stable context elements
            stable_context = {k: v for k, v in user_context.items() if k in ["profession", "region", "company_type"]}
            cache_input += str(sorted(stable_context.items()))

        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]

    async def _fallback_processing(self, query: str, user_context: dict[str, Any] | None) -> EnhancedQueryResponse:
        """Fallback to basic processing when enhanced pipeline fails"""
        try:
            # Use default classification
            fallback_classification = DomainActionClassification(
                domain="tax",  # Default to tax domain
                action="information_request",  # Default to info request
                confidence=0.3,
                reasoning="Fallback classification due to processing error",
                fallback_used=True,
            )

            # Simple prompt
            provider = get_llm_provider(strategy=RoutingStrategy.COST_OPTIMIZED)
            messages = [
                SystemMessage(content="Sei un consulente fiscale italiano. Rispondi in modo professionale e preciso."),
                HumanMessage(content=query),
            ]

            response = await provider.chat_completion(messages=messages, temperature=0.2)

            return EnhancedQueryResponse(
                content=response.content,
                classification=fallback_classification,
                processing_time_ms=0,
                model_used=provider.model,
                cost_eur=0.0,
                cache_hit=False,
            )

        except Exception as e:
            logger.error(f"Fallback processing also failed: {e}")
            return EnhancedQueryResponse(
                content="Mi dispiace, si è verificato un errore nel processare la tua richiesta. Ti prego di riprovare.",
                classification=DomainActionClassification(
                    domain="tax", action="information_request", confidence=0.0, reasoning="Error fallback"
                ),
                processing_time_ms=0,
            )

    async def get_routing_stats(self) -> dict[str, Any]:
        """Get statistics about query routing and performance"""
        classifier_stats = self.classifier.get_classification_stats()
        template_combinations = self.prompt_manager.get_available_combinations()

        return {
            "classification_system": classifier_stats,
            "prompt_templates": template_combinations,
            "performance_targets": {
                "max_classification_time_ms": self.max_classification_time_ms,
                "max_context_building_time_ms": self.max_context_building_time_ms,
                "max_total_processing_time_ms": self.max_total_processing_time_ms,
            },
            "cost_optimization": {
                "strategy_mapping": "domain_action_based",
                "cache_enabled": True,
                "fallback_enabled": True,
            },
        }
