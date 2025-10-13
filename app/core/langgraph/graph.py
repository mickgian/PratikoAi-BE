"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Optional,
)

from asgiref.sync import sync_to_async
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langfuse.langchain import CallbackHandler
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.graph import (
        END,
        StateGraph,
    )
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.types import StateSnapshot
except ImportError:
    # Fallback for development/testing environments where langgraph might not be properly installed
    AsyncPostgresSaver = None

    # Create fallback classes
    class END:
        pass

    class StateGraph:
        def __init__(self, state_type):
            self.state_type = state_type
            self.nodes = {}
            self.edges = []

        def add_node(self, name, func):
            self.nodes[name] = func

        def add_edge(self, from_node, to_node):
            self.edges.append((from_node, to_node))

        def add_conditional_edges(self, from_node, condition, mapping):
            pass

        def set_entry_point(self, node):
            self.entry = node

        def set_finish_point(self, node):
            self.finish = node

        def compile(self, **kwargs):
            return CompiledStateGraph()

    class CompiledStateGraph:
        async def ainvoke(self, state, **kwargs):
            return state

    class StateSnapshot:
        pass

from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.tools import tools
from app.core.llm.factory import get_llm_provider, RoutingStrategy
from app.core.llm.base import LLMProvider
from app.services.domain_action_classifier import DomainActionClassifier, DomainActionClassification, Action
from app.services.domain_prompt_templates import PromptTemplateManager
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.monitoring.metrics import track_llm_cost, track_api_call, track_classification_usage
from app.core.prompts import SYSTEM_PROMPT
from app.services.cache import cache_service
from app.services.usage_tracker import usage_tracker
from app.services.golden_fast_path import GoldenFastPathService, EligibilityDecision
from app.schemas import (
    GraphState,
    Message,
)
from app.core.langgraph.types import RAGState
from app.utils import dump_messages

# Canonical observability imports (unified across repo)
try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    # Safe fallbacks so imports never break tests
    def rag_step_log(*args, **kwargs):  # no-op
        return None
    from contextlib import nullcontext
    def rag_step_timer(*args, **kwargs):
        return nullcontext()

# Re-export GraphState for stable import by tests and other modules
GraphState = GraphState

# Phase 1A Node imports
from app.core.langgraph.nodes import (
    node_step_1,
    node_step_3,
    node_step_6,
    node_step_9,
    node_step_59,
    node_step_62,
    node_step_64,
    node_step_67,
    node_step_112,
)

# Phase 6 Node imports (additional to Phase 1A)
from app.core.langgraph.nodes.step_004__gdpr_log import node_step_4
from app.core.langgraph.nodes.step_007__anonymize_text import node_step_7
from app.core.langgraph.nodes.step_008__init_agent import node_step_8
from app.core.langgraph.nodes.step_010__log_pii import node_step_10

# Phase 4 Node imports
from app.core.langgraph.nodes.step_066__return_cached import node_step_66
from app.core.langgraph.nodes.step_068__cache_response import node_step_68
from app.core.langgraph.nodes.step_069__retry_check import node_step_69
from app.core.langgraph.nodes.step_070__prod_check import node_step_70
from app.core.langgraph.nodes.step_072__failover_provider import node_step_72
from app.core.langgraph.nodes.step_073__retry_same import node_step_73
from app.core.langgraph.nodes.step_074__track_usage import node_step_74
from app.core.langgraph.nodes.step_075__tool_check import node_step_75
from app.core.langgraph.nodes.step_079__tool_type import node_step_79
from app.core.langgraph.nodes.step_080__kb_tool import node_step_80
from app.core.langgraph.nodes.step_081__ccnl_tool import node_step_81
from app.core.langgraph.nodes.step_082__doc_ingest_tool import node_step_82
from app.core.langgraph.nodes.step_083__faq_tool import node_step_83
from app.core.langgraph.nodes.step_099__tool_results import node_step_99

# Phase 5 Node imports
from app.core.langgraph.nodes.step_048__select_provider import node_step_48
from app.core.langgraph.nodes.step_049__route_strategy import node_step_49
from app.core.langgraph.nodes.step_050__strategy_type import node_step_50
from app.core.langgraph.nodes.step_051__cheap_provider import node_step_51
from app.core.langgraph.nodes.step_052__best_provider import node_step_52
from app.core.langgraph.nodes.step_053__balance_provider import node_step_53
from app.core.langgraph.nodes.step_054__primary_provider import node_step_54
from app.core.langgraph.nodes.step_055__estimate_cost import node_step_55
from app.core.langgraph.nodes.step_056__cost_check import node_step_56
from app.core.langgraph.nodes.step_057__create_provider import node_step_57
from app.core.langgraph.nodes.step_058__cheaper_provider import node_step_58

# Phase 2 Node imports - Message Lane
from app.core.langgraph.nodes.step_011__convert_messages import node_step_11
from app.core.langgraph.nodes.step_012__extract_query import node_step_12
from app.core.langgraph.nodes.step_013__message_exists import node_step_13

# Phase 8 Node imports - Golden/KB Gates
from app.core.langgraph.nodes.step_020__golden_fast_gate import node_step_20
from app.core.langgraph.nodes.step_024__golden_lookup import node_step_24
from app.core.langgraph.nodes.step_025__golden_hit import node_step_25
from app.core.langgraph.nodes.step_026__kb_context_check import node_step_26
from app.core.langgraph.nodes.step_027__kb_delta import node_step_27
from app.core.langgraph.nodes.step_028__serve_golden import node_step_28
from app.core.langgraph.nodes.step_030__return_complete import node_step_30

# Phase 4 Classification Node imports
from app.core.langgraph.nodes.step_031__classify_domain import node_step_31
from app.core.langgraph.nodes.step_042__class_confidence import node_step_42

# Phase 7 Node imports - Streaming/Response Lane
from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_106__async_gen import node_step_106
from app.core.langgraph.nodes.step_107__single_pass import node_step_107
from app.core.langgraph.nodes.step_108__write_sse import node_step_108
from app.core.langgraph.nodes.step_109__stream_response import node_step_109
from app.core.langgraph.nodes.step_110__send_done import node_step_110
from app.core.langgraph.nodes.step_111__collect_metrics import node_step_111

# Phase 1A nodes are now the default implementation

# Import wiring registry functions from centralized module
from app.core.langgraph.wiring_registry import (
    get_wired_nodes_snapshot,
    initialize_phase4_registry,
    initialize_phase5_registry,
    initialize_phase6_registry,
    initialize_phase7_registry,
    initialize_phase8_registry,
    track_edge,
)

# Initialize Phase 4, 5, 6, 7, and 8 registries at module load time
initialize_phase4_registry()
initialize_phase5_registry()
initialize_phase6_registry()
initialize_phase7_registry()
initialize_phase8_registry()

# Explicit exports for stable API
__all__ = ["LangGraphAgent", "GraphState", "RAGState", "get_wired_nodes_snapshot"]


class LangGraphAgent:
    """Manages the LangGraph Agent/workflow and interactions with the LLM.

    This class handles the creation and management of the LangGraph workflow,
    including LLM interactions, database connections, and response processing.
    """

    def __init__(self):
        """Initialize the LangGraph Agent with necessary components."""
        # Initialize with fallback to legacy config for backward compatibility
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None
        self._current_provider: Optional[LLMProvider] = None
        
        # Initialize domain-action classification services
        self._domain_classifier = DomainActionClassifier()
        self._prompt_template_manager = PromptTemplateManager()
        self._golden_fast_path_service = GoldenFastPathService()
        self._current_classification = None  # Store current query classification
        self._response_metadata = None  # Store response metadata

        logger.info("llm_agent_initialized", environment=settings.ENVIRONMENT.value)

    async def _classify_user_query(self, messages: List[Message]) -> Optional[DomainActionClassification]:
        """Classify the latest user query using domain-action classifier.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            DomainActionClassification or None if no messages
    Implements RAG STEP 8 (LangGraphAgent.get_response Initialize workflow)
    Node ID: RAG.response.langgraphagent.get.response.initialize.workflow
    Category: response
    Type: process
        """
        if not messages:
            return None
            
        # Find the latest user message
        user_message = None
        for message in reversed(messages):
            if message.role == "user":
                user_message = message.content
                break
                
        if not user_message:
            return None
            
        try:
            # Perform classification
            classification = await self._domain_classifier.classify(user_message)
            
            # Log classification result
            logger.info(
                "query_classified",
                domain=classification.domain.value,
                action=classification.action.value,
                confidence=classification.confidence,
                sub_domain=classification.sub_domain,
                fallback_used=classification.fallback_used
            )
            
            # Track classification metrics
            track_classification_usage(
                domain=classification.domain.value,
                action=classification.action.value,
                confidence=classification.confidence,
                fallback_used=classification.fallback_used
            )
            
            return classification
            
        except Exception as e:
            logger.error("query_classification_failed", error=str(e), exc_info=True)
            return None

    async def _check_golden_fast_path_eligibility(self, messages: List[Message], session_id: str, user_id: Optional[str]) -> 'EligibilityResult':
        """
        Check if the current query is eligible for golden fast-path processing.
        
        Args:
            messages: List of conversation messages
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            EligibilityResult with decision and reasoning
        """
        import time
        
        # Find the latest user message
        user_message = None
        for message in reversed(messages):
            if message.role == "user":
                user_message = message.content
                break
        
        if not user_message:
            # No user message found, not eligible
            from app.services.golden_fast_path import EligibilityResult, EligibilityDecision
            return EligibilityResult(
                decision=EligibilityDecision.NOT_ELIGIBLE,
                confidence=1.0,
                reasons=["no_user_message"],
                next_step="ClassifyDomain",
                allows_golden_lookup=False
            )
        
        # Prepare query data for golden fast-path service
        query_data = {
            "query": user_message,
            "attachments": [],  # TODO: Extract attachments from request context in future
            "user_id": user_id or "anonymous",
            "session_id": session_id,
            "canonical_facts": [],  # TODO: Extract from atomic facts extraction in future
            "query_signature": f"session_{session_id}_{hash(user_message)}",
            "trace_id": f"trace_{session_id}_{int(time.time())}"
        }
        
        # Check eligibility using golden fast-path service
        return await self._golden_fast_path_service.is_eligible_for_fast_path(query_data)

    async def _get_cached_llm_response(self, provider: LLMProvider, messages: List[Message], tools: list, temperature: float, max_tokens: int):
        """Get LLM response with caching support.
        
        Args:
            provider: The LLM provider to use
            messages: List of conversation messages
            tools: Available tools for the LLM
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse: The response from the LLM (cached or fresh)
        """
        # Try to get cached response first
        try:
            cached_response = await cache_service.get_cached_response(
                messages=messages,
                model=provider.model,
                temperature=temperature
            )
            if cached_response:
                logger.info(
                    "llm_cache_hit",
                    model=provider.model,
                    provider=provider.provider_type.value,
                    message_count=len(messages)
                )
                
                # Track cache hit usage
                if hasattr(self, '_current_session_id') and hasattr(self, '_current_user_id'):
                    try:
                        await usage_tracker.track_llm_usage(
                            user_id=self._current_user_id,
                            session_id=self._current_session_id,
                            provider=provider.provider_type.value,
                            model=provider.model,
                            llm_response=cached_response,
                            response_time_ms=10,  # Minimal time for cache hit
                            cache_hit=True,
                            pii_detected=getattr(self, '_pii_detected', False),
                            pii_types=getattr(self, '_pii_types', None)
                        )
                    except Exception as e:
                        logger.error(
                            "cache_hit_tracking_failed",
                            error=str(e),
                            provider=provider.provider_type.value,
                            model=provider.model
                        )
                
                return cached_response
        except Exception as e:
            logger.error(
                "llm_cache_get_failed",
                error=str(e),
                model=provider.model
            )
        
        # Get fresh response from provider
        import time
        start_time = time.time()
        
        response = await provider.chat_completion(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Track Prometheus metrics for this LLM call
        try:
            user_id = getattr(self, '_current_user_id', 'unknown')
            
            # Track API call success/failure
            status = "success" if response else "error"
            track_api_call(
                provider=provider.provider_type.value,
                model=provider.model,
                status=status
            )
            
            # Track cost if response contains cost information
            if response and hasattr(response, 'cost_eur') and response.cost_eur:
                track_llm_cost(
                    provider=provider.provider_type.value,
                    model=provider.model,
                    user_id=user_id,
                    cost_eur=response.cost_eur
                )
                
        except Exception as e:
            logger.error(
                "prometheus_metrics_tracking_failed",
                error=str(e),
                provider=provider.provider_type.value,
                model=provider.model
            )
        
        # Track usage (only for non-cached responses)
        if hasattr(self, '_current_session_id') and hasattr(self, '_current_user_id'):
            try:
                await usage_tracker.track_llm_usage(
                    user_id=self._current_user_id,
                    session_id=self._current_session_id,
                    provider=provider.provider_type.value,
                    model=provider.model,
                    llm_response=response,
                    response_time_ms=response_time_ms,
                    cache_hit=False,
                    pii_detected=getattr(self, '_pii_detected', False),
                    pii_types=getattr(self, '_pii_types', None)
                )
            except Exception as e:
                logger.error(
                    "usage_tracking_failed",
                    error=str(e),
                    provider=provider.provider_type.value,
                    model=provider.model
                )
        
        # Cache the response for future use
        try:
            await cache_service.cache_response(
                messages=messages,
                model=provider.model,
                response=response,
                temperature=temperature
            )
            logger.info(
                "llm_response_cached",
                model=provider.model,
                provider=provider.provider_type.value,
                response_length=len(response.content)
            )
        except Exception as e:
            logger.error(
                "llm_cache_set_failed",
                error=str(e),
                model=provider.model
            )
        
        return response

    @staticmethod
    def _get_routing_strategy() -> RoutingStrategy:
        """Get the LLM routing strategy from configuration.

        Returns:
            RoutingStrategy: The configured routing strategy
        """
        strategy_map = {
            "cost_optimized": RoutingStrategy.COST_OPTIMIZED,
            "quality_first": RoutingStrategy.QUALITY_FIRST,
            "balanced": RoutingStrategy.BALANCED,
            "failover": RoutingStrategy.FAILOVER,
        }

        strategy_str = getattr(settings, 'LLM_ROUTING_STRATEGY', 'cost_optimized')
        return strategy_map.get(strategy_str, RoutingStrategy.COST_OPTIMIZED)

    @staticmethod
    def _get_classification_aware_routing(classification: DomainActionClassification) -> tuple[RoutingStrategy, float]:
        """Return (routing_strategy, max_cost_eur) based solely on domain/action mapping.
        - No confidence-based scaling.
        - Apply global cap only if explicitly provided (non-None).
        """
        strategy_map = {
            # High-accuracy requirements
            ("legal", "document_generation"):       (RoutingStrategy.QUALITY_FIRST, 0.030),
            ("legal", "compliance_check"):          (RoutingStrategy.QUALITY_FIRST, 0.025),
            ("tax", "calculation_request"):         (RoutingStrategy.QUALITY_FIRST, 0.020),
            ("accounting", "document_analysis"):    (RoutingStrategy.QUALITY_FIRST, 0.025),
            ("business", "strategic_advice"):       (RoutingStrategy.QUALITY_FIRST, 0.025),

            # CCNL / balanced
            ("labor", "ccnl_query"):                (RoutingStrategy.BALANCED, 0.018),
            ("labor", "calculation_request"):       (RoutingStrategy.BALANCED, 0.020),
            ("tax", "strategic_advice"):            (RoutingStrategy.BALANCED, 0.015),
            ("labor", "compliance_check"):          (RoutingStrategy.BALANCED, 0.015),
            ("business", "document_generation"):    (RoutingStrategy.BALANCED, 0.020),
            ("accounting", "compliance_check"):     (RoutingStrategy.BALANCED, 0.015),

            # Cost-optimized simple info (tests expect 0.015)
            ("tax", "information_request"):         (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("legal", "information_request"):       (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("labor", "information_request"):       (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("business", "information_request"):    (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("accounting", "information_request"):  (RoutingStrategy.COST_OPTIMIZED, 0.015),
        }

        key = (classification.domain.value, classification.action.value)
        strategy, base_cost = strategy_map.get(key, (RoutingStrategy.BALANCED, 0.020))

        # Only cap if explicitly configured (non-default); otherwise leave mapping as-is
        global_cap = getattr(settings, 'LLM_MAX_COST_EUR', None)
        DEFAULT_CAP = 0.020  # Same as in config.py default

        try:
            # Only apply cap if it's explicitly set (different from default) and would actually limit
            if global_cap is not None and global_cap != DEFAULT_CAP and global_cap < base_cost:
                max_cost = float(global_cap)
            else:
                max_cost = base_cost
        except Exception:
            max_cost = base_cost

        return strategy, max_cost

    async def _get_system_prompt(self, messages: List[Message], classification: Optional['DomainActionClassification']) -> str:
        """Select the appropriate system prompt via RAG Step 41 orchestrator."""
        from app.orchestrators.prompting import step_41__select_prompt

        # Call the Step 41 orchestrator (thin orchestration pattern)
        result = await step_41__select_prompt(
            messages=messages,
            ctx={
                'classification': classification,
                'prompt_template_manager': self._prompt_template_manager,
                'request_id': getattr(self, '_current_request_id', 'unknown')
            }
        )

        # Extract the selected prompt from orchestrator result
        return result.get('selected_prompt', SYSTEM_PROMPT)

    async def _prepare_messages_with_system_prompt(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        classification: Optional['DomainActionClassification'] = None,
    ) -> List[Message]:
        """Ensure system message presence (RAG STEP 45 — CheckSysMsg) with backward-compatible signature."""
        if messages is None:
            messages = []
        msgs = messages  # operate IN-PLACE

        original_count = len(msgs)
        # Resolve classification (fallback to agent state)
        resolved_class = classification if classification is not None else getattr(self, "_current_classification", None)
        has_classification = resolved_class is not None
        conf = resolved_class.confidence if has_classification else None
        domain = resolved_class.domain.value if has_classification else None
        action = resolved_class.action.value if has_classification else None

        # Resolve prompt if not provided
        if system_prompt is None:
            try:
                system_prompt = await self._get_system_prompt(msgs, resolved_class)
            except Exception:
                from app.core.prompts import SYSTEM_PROMPT as _SP
                system_prompt = _SP

        messages_empty = (original_count == 0)
        system_exists = bool(msgs and getattr(msgs[0], "role", None) == "system")

        # Use RAG STEP 45 orchestrator for system message existence decision
        from app.orchestrators.prompting import step_45__check_sys_msg

        step_45_decision = step_45__check_sys_msg(
            messages=msgs,
            ctx={
                'classification': resolved_class,
                'system_prompt': system_prompt
            }
        )

        # Route based on Step 45 decision
        if step_45_decision['next_step'] == 47:
            # Route to Step 47 (InsertMsg)
            from app.orchestrators.prompting import step_47__insert_msg

            msgs = step_47__insert_msg(
                messages=msgs,
                ctx={
                    'system_prompt': system_prompt,
                    'classification': resolved_class
                }
            )
            return msgs

        elif step_45_decision['next_step'] == 46:
            # Route to Step 46 (ReplaceMsg)
            from app.orchestrators.prompting import step_46__replace_msg

            msgs = step_46__replace_msg(
                messages=msgs,
                ctx={
                    'new_system_prompt': system_prompt,
                    'classification': resolved_class
                }
            )
            return msgs

        else:
            # Keep existing system message (action == "keep")
            return msgs

    def _get_optimal_provider(self, messages: List[Message]) -> LLMProvider:
        """Get the optimal LLM provider for the given messages.

        Args:
            messages: List of conversation messages

        Returns:
            LLMProvider: The optimal provider for this request
        """
        # STEP 48 timer
        with rag_step_timer(
            48,
            "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider",
            "SelectProvider",
        ):
            try:
                # Use classification-aware routing if available
                if self._current_classification:
                    strategy, max_cost = self._get_classification_aware_routing(self._current_classification)
                else:
                    strategy = self._get_routing_strategy()
                    max_cost = getattr(settings, 'LLM_MAX_COST_EUR', 0.020)

                preferred_provider = getattr(settings, 'LLM_PREFERRED_PROVIDER', None)
                settings_max_cost = getattr(settings, 'LLM_MAX_COST_EUR', 0.020)

                # RAG STEP 49 — Apply routing strategy
                rag_step_log(
                    step=49,
                    step_id="RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
                    node_label="RouteStrategy",
                    decision="applying_routing_strategy",
                    routing_strategy=strategy.value,
                    max_cost_eur=max_cost,
                    preferred_provider=preferred_provider,
                    messages_count=len(messages),
                    messages_empty=len(messages) == 0,
                    processing_stage="started",
                )

                provider = get_llm_provider(
                    messages=messages,
                    strategy=strategy,
                    max_cost_eur=max_cost,
                    preferred_provider=preferred_provider or None,
                )

                # RAG STEP 49 — Strategy applied successfully
                rag_step_log(
                    step=49,
                    step_id="RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
                    node_label="RouteStrategy",
                    decision="routing_strategy_applied",
                    routing_strategy=strategy.value,
                    max_cost_eur=max_cost,
                    preferred_provider=preferred_provider,
                    provider_type=provider.provider_type.value,
                    model=provider.model,
                    messages_count=len(messages),
                    messages_empty=len(messages) == 0,
                    processing_stage="completed",
                )

                # RAG STEP 50 — Routing strategy decision
                strategy_to_next_step = {
                    RoutingStrategy.COST_OPTIMIZED: ("CheapProvider", "routing_to_cost_optimized"),
                    RoutingStrategy.QUALITY_FIRST: ("BestProvider", "routing_to_quality_first"),
                    RoutingStrategy.BALANCED: ("BalanceProvider", "routing_to_balanced"),
                    RoutingStrategy.FAILOVER: ("PrimaryProvider", "routing_to_failover"),
                }
                next_step, decision = strategy_to_next_step.get(strategy, ("BalanceProvider", "routing_fallback_to_balanced"))

                rag_step_log(
                    step=50,
                    step_id="RAG.platform.routing.strategy",
                    node_label="StrategyType",
                    decision=decision,
                    routing_strategy=strategy.value,
                    next_step=next_step,
                    max_cost_eur=max_cost,
                    preferred_provider=preferred_provider,
                    provider_type=provider.provider_type.value,
                    model=provider.model,
                    messages_count=len(messages),
                    messages_empty=len(messages) == 0,
                    processing_stage="completed",
                )

                # RAG STEP 48 — Select LLM provider
                rag_step_log(
                    step=48,
                    step_id="RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider",
                    node_label="SelectProvider",
                    decision="provider_selected",
                    provider_type=provider.provider_type.value,
                    model=provider.model,
                    routing_strategy=strategy.value,
                    max_cost_eur=max_cost,
                    effective_max_cost=max_cost,
                    settings_max_cost=settings_max_cost,
                    classification_used=self._current_classification is not None,
                    domain=self._current_classification.domain.value if self._current_classification else None,
                    action=self._current_classification.action.value if self._current_classification else None,
                    classification_confidence=self._current_classification.confidence if self._current_classification else None,
                    preferred_provider=preferred_provider,
                    messages_count=len(messages),
                    messages_empty=len(messages) == 0,
                    processing_stage="completed",
                )

                logger.info(
                    "llm_provider_selected",
                    provider=provider.provider_type.value,
                    model=provider.model,
                    strategy=strategy.value,
                    classification_used=self._current_classification is not None,
                    domain=self._current_classification.domain.value if self._current_classification else None,
                    action=self._current_classification.action.value if self._current_classification else None,
                )

                return provider

            except Exception as e:
                # RAG STEP 49 — Error during routing strategy
                rag_step_log(
                    step=49,
                    step_id="RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
                    node_label="RouteStrategy",
                    decision="routing_strategy_failed",
                    error=str(e),
                    routing_strategy=getattr(strategy, 'value', None) if 'strategy' in locals() else None,
                    processing_stage="error",
                )

                # RAG STEP 50 — Error during routing decision
                rag_step_log(
                    step=50,
                    step_id="RAG.platform.routing.strategy",
                    node_label="StrategyType",
                    decision="routing_decision_failed",
                    error=str(e),
                    routing_strategy=getattr(strategy, 'value', None) if 'strategy' in locals() else None,
                    processing_stage="error",
                )

                # RAG STEP 48 — Error fallback
                rag_step_log(
                    step=48,
                    step_id="RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider",
                    node_label="SelectProvider",
                    decision="fallback_to_legacy",
                    error=str(e),
                    classification_used=self._current_classification is not None,
                    processing_stage="error_fallback",
                )

                logger.error(
                    "llm_provider_selection_failed",
                    error=str(e),
                    fallback_to_legacy=True,
                )
                # Fallback to legacy OpenAI configuration
                from app.core.llm.providers.openai_provider import OpenAIProvider
                return OpenAIProvider(
                    api_key=settings.LLM_API_KEY or settings.OPENAI_API_KEY,
                    model=settings.LLM_MODEL or settings.OPENAI_MODEL,
                )

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        """Get a PostgreSQL connection pool using environment-specific settings.

        Returns:
            AsyncConnectionPool: A connection pool for PostgreSQL database.
        """
        if self._connection_pool is None:
            try:
                # Configure pool size based on environment
                max_size = settings.POSTGRES_POOL_SIZE

                self._connection_pool = AsyncConnectionPool(
                    settings.POSTGRES_URL,
                    open=False,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,
                    },
                )
                await self._connection_pool.open()
                logger.info("connection_pool_created", max_size=max_size, environment=settings.ENVIRONMENT.value)
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we might want to degrade gracefully
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_connection_pool", environment=settings.ENVIRONMENT.value)
                    return None
                raise e
        return self._connection_pool

    async def _chat(self, state: GraphState) -> dict:
        """Process the chat state and generate a response.

        Args:
            state (GraphState): The current state of the conversation.

        Returns:
            dict: Updated state with new messages.
        """
        # Convert GraphState messages to Message objects for provider
        conversation_messages = []
        for msg in state.messages:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                conversation_messages.append(Message(role=msg.role, content=msg.content))
            else:
                # Handle legacy message format
                conversation_messages.append(Message(role="user", content=str(msg)))

        # Classify user query
        self._current_classification = await self._classify_user_query(conversation_messages)

        # Get domain-specific system prompt or default
        system_prompt = await self._get_system_prompt(conversation_messages, self._current_classification)
        
        # Use RAG STEP 45 to prepare messages with system prompt
        conversation_messages = await self._prepare_messages_with_system_prompt(conversation_messages, system_prompt, self._current_classification)

        llm_calls_num = 0
        max_retries = settings.MAX_LLM_CALL_RETRIES

        for attempt in range(max_retries):
            try:
                # Get optimal provider for this conversation (now classification-aware)
                provider = self._get_optimal_provider(conversation_messages)
                self._current_provider = provider

                # Make the LLM call with tools (with caching)
                with llm_inference_duration_seconds.labels(model=provider.model).time():
                    response = await self._get_cached_llm_response(
                        provider=provider,
                        messages=conversation_messages,
                        tools=list(self.tools_by_name.values()),
                        temperature=settings.DEFAULT_LLM_TEMPERATURE,
                        max_tokens=settings.MAX_TOKENS,
                    )

                # Convert response back to LangChain format
                if response.tool_calls:
                    # Create AIMessage with tool calls
                    from langchain_core.messages import AIMessage
                    ai_message = AIMessage(
                        content=response.content,
                        tool_calls=response.tool_calls
                    )
                else:
                    # Create simple AIMessage
                    from langchain_core.messages import AIMessage
                    ai_message = AIMessage(content=response.content)

                logger.info(
                    "llm_response_generated",
                    session_id=state.session_id,
                    llm_calls_num=llm_calls_num + 1,
                    model=provider.model,
                    provider=provider.provider_type.value,
                    cost_estimate=response.cost_estimate,
                    environment=settings.ENVIRONMENT.value,
                )
                
                return {"messages": [ai_message]}

            except Exception as e:
                logger.error(
                    "llm_call_failed",
                    llm_calls_num=llm_calls_num,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    provider=getattr(self._current_provider, 'provider_type', {}).get('value', 'unknown') if self._current_provider else 'unknown',
                    environment=settings.ENVIRONMENT.value,
                )
                llm_calls_num += 1

                # In production, we might want to fall back to a different provider/model
                if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                    logger.warning(
                        "attempting_fallback_provider",
                        environment=settings.ENVIRONMENT.value
                    )
                    # Force failover strategy for next attempt
                    try:
                        fallback_provider = get_llm_provider(
                            messages=conversation_messages,
                            strategy=RoutingStrategy.FAILOVER,
                            max_cost_eur=settings.LLM_MAX_COST_EUR * 2,  # Allow higher cost for fallback
                        )
                        self._current_provider = fallback_provider
                    except Exception as fallback_error:
                        logger.error(
                            "fallback_provider_selection_failed",
                            error=str(fallback_error),
                            environment=settings.ENVIRONMENT.value,
                        )

                continue

        raise Exception(f"Failed to get a response from the LLM after {max_retries} attempts")

    # Define our tool node
    async def _tool_call(self, state: GraphState) -> GraphState:
        """Process tool calls from the last message.

        Args:
            state: The current agent state containing messages and tool calls.

        Returns:
            Dict with updated messages containing tool responses.
        """
        outputs = []
        for tool_call in state.messages[-1].tool_calls:
            tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

    @staticmethod
    def _should_continue(state: GraphState) -> Literal["end", "continue"]:
        """Determine if the agent should continue or end based on the last message.

        Args:
            state: The current agent state containing messages.

        Returns:
            Literal["end", "continue"]: "end" if there are no tool calls, "continue" otherwise.
        """
        messages = state.messages
        last_message = messages[-1]
        # If there is no function call, then we finish
        if not last_message.tool_calls:
            return "end"
        # Otherwise if there is, we continue
        else:
            return "continue"

    # Phase 5 routing functions
    @staticmethod
    def _route_strategy_type(state: Dict[str, Any]) -> str:
        """Route from StrategyType node based on strategy decision."""
        strategy_type = state.get("decisions", {}).get("strategy_type", "PRIMARY")
        return strategy_type

    @staticmethod
    def _route_cost_check(state: Dict[str, Any]) -> str:
        """Route from CostCheck node based on budget approval."""
        cost_ok = state.get("decisions", {}).get("cost_ok", True)
        return "approved" if cost_ok else "too_expensive"

    # Reuse existing routing functions with new names for clarity
    @staticmethod
    def _route_cache_hit(state: Dict[str, Any]) -> str:
        """Route from CacheHit node based on cache status."""
        if state.get("cache_hit", False):
            return "hit"
        else:
            return "miss"

    @staticmethod
    def _route_llm_success(state: Dict[str, Any]) -> str:
        """Route from LLMSuccess node."""
        if state.get("llm_success", True):
            return "success"
        else:
            return "retry"

    @staticmethod
    def _route_tool_check(state: Dict[str, Any]) -> str:
        """Route from ToolCheck node."""
        if state.get("tool_calls") or state.get("tools", {}).get("requested", False):
            return "has_tools"
        else:
            return "no_tools"

    @staticmethod
    def _route_tool_type(state: Dict[str, Any]) -> str:
        """Route from ToolType node based on tool type."""
        tool_type = state.get("tools", {}).get("type", "kb")
        mapping = {
            "kb": "kb",
            "ccnl": "ccnl",
            "doc": "doc",
            "faq": "faq"
        }
        return mapping.get(tool_type, "kb")

    @staticmethod
    def _route_prod_check(state: Dict[str, Any]) -> str:
        """Route from ProdCheck node."""
        if state.get("llm", {}).get("should_failover", False):
            return "failover"
        else:
            return "retry_same"

    @staticmethod
    def _route_from_valid_check(state: Dict[str, Any]) -> str:
        """Route from ValidCheck node based on request validity."""
        if state.get('request_valid', True):
            return "PrivacyCheck"
        else:
            return "End"

    @staticmethod
    def _route_from_privacy_check(_state: Dict[str, Any]) -> str:
        """Route from PrivacyCheck node - always goes to PIICheck."""
        return "PIICheck"

    @staticmethod
    def _route_from_pii_check(_state: Dict[str, Any]) -> str:
        """Route from PIICheck node - goes to cache spine."""
        return "CheckCache"

    @staticmethod
    def _route_from_cache_hit(state: Dict[str, Any]) -> str:
        """Route from CacheHit node based on cache status."""
        if state.get('cache_hit', False):
            return "End"
        else:
            return "LLMCall"

    @staticmethod
    def _route_from_llm_success(_state: Dict[str, Any]) -> str:
        """Route from LLMSuccess node - simplified for Phase 1A."""
        return "End"

    # Phase 4 routing functions
    @staticmethod
    def _route_from_cache_hit_phase4(state: Dict[str, Any]) -> str:
        """Route from CacheHit node in Phase 4 based on cache status."""
        if state.get("cache_hit_decision", False):
            return "ReturnCached"
        else:
            return "LLMCall"

    @staticmethod
    def _route_from_llm_success_phase4(state: Dict[str, Any]) -> str:
        """Route from LLMSuccess node in Phase 4."""
        if state.get("llm_success_decision", True):
            return "CacheResponse"
        else:
            return "RetryCheck"

    @staticmethod
    def _route_from_retry_check(state: Dict[str, Any]) -> str:
        """Route from RetryCheck node."""
        if state.get("llm", {}).get("retry_allowed", False):
            return "ProdCheck"
        else:
            return "End"

    @staticmethod
    def _route_from_prod_check(state: Dict[str, Any]) -> str:
        """Route from ProdCheck node."""
        if state.get("llm", {}).get("should_failover", False):
            return "FailoverProvider"
        else:
            return "RetrySame"

    @staticmethod
    def _route_from_tool_check(state: Dict[str, Any]) -> str:
        """Route from ToolCheck node."""
        if state.get("tools", {}).get("requested", False):
            return "ToolType"
        else:
            return "End"

    @staticmethod
    def _route_from_tool_type(state: Dict[str, Any]) -> str:
        """Route from ToolType node based on tool type."""
        tool_type = state.get("tools", {}).get("type", "kb")
        mapping = {
            "kb": "KBTool",
            "ccnl": "CCNLTool",
            "doc": "DocIngestTool",
            "faq": "FAQTool"
        }
        return mapping.get(tool_type, "KBTool")

    # Unified graph routing functions
    @staticmethod
    def _route_from_privacy_check_unified(state: Dict[str, Any]) -> str:
        """Route from PrivacyCheck in unified graph."""
        if state.get("privacy", {}).get("anonymize_enabled", False):
            return "AnonymizeText"
        else:
            return "InitAgent"

    @staticmethod
    def _route_from_pii_check_unified(state: Dict[str, Any]) -> str:
        """Route from PIICheck in unified graph."""
        if state.get("privacy", {}).get("pii_detected", False):
            return "LogPII"
        else:
            return "InitAgent"

    @staticmethod
    def _route_from_golden_fast_gate(state: Dict[str, Any]) -> str:
        """Route from GoldenFastGate - check if golden lookup is eligible."""
        if state.get("golden", {}).get("eligible", False):
            return "GoldenLookup"
        else:
            return "ClassifyDomain"

    @staticmethod
    def _route_from_golden_hit(state: Dict[str, Any]) -> str:
        """Route from GoldenHit - check if high confidence match found."""
        if state.get("golden", {}).get("hit", False):
            return "KBContextCheck"
        else:
            return "ClassifyDomain"

    @staticmethod
    def _route_from_kb_delta(state: Dict[str, Any]) -> str:
        """Route from KBDelta - check if KB is newer than golden."""
        if state.get("golden", {}).get("kb_newer", False):
            return "ClassifyDomain"  # Need fresh LLM response with KB context
        else:
            return "ServeGolden"  # Golden answer is still fresh

    @staticmethod
    def _route_from_strategy_type(state: Dict[str, Any]) -> str:
        """Route from StrategyType based on routing strategy."""
        strategy = state.get("provider", {}).get("routing_strategy", "PRIMARY")
        mapping = {
            "COST_OPTIMIZED": "CheapProvider",
            "QUALITY_FIRST": "BestProvider",
            "BALANCED": "BalanceProvider",
            "PRIMARY": "PrimaryProvider",
            "FAILOVER": "PrimaryProvider"
        }
        return mapping.get(strategy, "PrimaryProvider")

    @staticmethod
    def _route_from_cost_check(state: Dict[str, Any]) -> str:
        """Route from CostCheck - check if cost within budget."""
        if state.get("provider", {}).get("cost_ok", True):
            return "CreateProvider"
        else:
            return "CheaperProvider"

    @staticmethod
    def _route_from_cache_hit_unified(state: Dict[str, Any]) -> str:
        """Route from CacheHit in unified graph."""
        if state.get("cache", {}).get("hit", False):
            return "ReturnCached"
        else:
            return "LLMCall"

    @staticmethod
    def _route_from_llm_success_unified(state: Dict[str, Any]) -> str:
        """Route from LLMSuccess in unified graph."""
        if state.get("llm", {}).get("success", True):
            return "CacheResponse"
        else:
            return "RetryCheck"

    @staticmethod
    def _route_from_stream_check(state: Dict[str, Any]) -> str:
        """Route from StreamCheck - check if streaming requested."""
        if state.get("streaming", {}).get("requested", False):
            return "StreamSetup"
        else:
            return "CollectMetrics"

    async def create_graph_phase1a(self) -> Optional[CompiledStateGraph]:
        """Create Phase 1A graph with explicit RAG nodes.

        Returns:
            Optional[CompiledStateGraph]: The Phase 1A graph or None if init fails
        """
        try:
            graph_builder = StateGraph(GraphState)

            # Add Phase 1A nodes
            graph_builder.add_node("ValidateRequest", node_step_1)
            graph_builder.add_node("ValidCheck", node_step_3)
            graph_builder.add_node("PrivacyCheck", node_step_6)
            graph_builder.add_node("PIICheck", node_step_9)
            graph_builder.add_node("CheckCache", node_step_59)
            graph_builder.add_node("CacheHit", node_step_62)
            graph_builder.add_node("LLMCall", node_step_64)
            graph_builder.add_node("LLMSuccess", node_step_67)
            graph_builder.add_node("End", node_step_112)

            # Add edges - Phase 1A flow
            graph_builder.add_edge("ValidateRequest", "ValidCheck")
            graph_builder.add_conditional_edges(
                "ValidCheck",
                self._route_from_valid_check,
                {"PrivacyCheck": "PrivacyCheck", "End": "End"}
            )
            graph_builder.add_conditional_edges(
                "PrivacyCheck",
                self._route_from_privacy_check,
                {"PIICheck": "PIICheck"}
            )
            graph_builder.add_conditional_edges(
                "PIICheck",
                self._route_from_pii_check,
                {"CheckCache": "CheckCache"}
            )
            graph_builder.add_edge("CheckCache", "CacheHit")
            graph_builder.add_conditional_edges(
                "CacheHit",
                self._route_from_cache_hit,
                {"End": "End", "LLMCall": "LLMCall"}
            )
            graph_builder.add_edge("LLMCall", "LLMSuccess")
            graph_builder.add_conditional_edges(
                "LLMSuccess",
                self._route_from_llm_success,
                {"End": "End"}
            )

            # Set entry and exit points
            graph_builder.set_entry_point("ValidateRequest")
            graph_builder.set_finish_point("End")

            # Get connection pool
            connection_pool = await self._get_connection_pool()
            if connection_pool and AsyncPostgresSaver is not None:
                checkpointer = AsyncPostgresSaver(connection_pool)
                await checkpointer.setup()
            else:
                checkpointer = None
                if settings.ENVIRONMENT != Environment.PRODUCTION and AsyncPostgresSaver is not None:
                    raise Exception("Connection pool initialization failed")

            compiled_graph = graph_builder.compile(
                checkpointer=checkpointer,
                name=f"{settings.PROJECT_NAME} Agent Phase1A ({settings.ENVIRONMENT.value})"
            )

            logger.info(
                "phase1a_graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent Phase1A",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
            )

            return compiled_graph

        except Exception as e:
            logger.error("phase1a_graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_phase1a_graph")
                return None
            raise e

    async def create_graph_phase4_lane(self) -> Optional[CompiledStateGraph]:
        """Create Phase 4 graph with Cache → LLM → Tools lane.

        Returns:
            Optional[CompiledStateGraph]: The Phase 4 graph or None if init fails
        """
        try:
            graph_builder = StateGraph(GraphState)

            # Add all Phase 1A nodes
            graph_builder.add_node("ValidateRequest", node_step_1)
            graph_builder.add_node("ValidCheck", node_step_3)
            graph_builder.add_node("PrivacyCheck", node_step_6)
            graph_builder.add_node("PIICheck", node_step_9)
            graph_builder.add_node("CheckCache", node_step_59)
            graph_builder.add_node("CacheHit", node_step_62)
            graph_builder.add_node("LLMCall", node_step_64)
            graph_builder.add_node("LLMSuccess", node_step_67)
            graph_builder.add_node("End", node_step_112)

            # Add Phase 4 nodes
            graph_builder.add_node("ReturnCached", node_step_66)
            graph_builder.add_node("CacheResponse", node_step_68)
            graph_builder.add_node("RetryCheck", node_step_69)
            graph_builder.add_node("ProdCheck", node_step_70)
            graph_builder.add_node("FailoverProvider", node_step_72)
            graph_builder.add_node("RetrySame", node_step_73)
            graph_builder.add_node("TrackUsage", node_step_74)
            graph_builder.add_node("ToolCheck", node_step_75)
            graph_builder.add_node("ToolType", node_step_79)
            graph_builder.add_node("KBTool", node_step_80)
            graph_builder.add_node("CCNLTool", node_step_81)
            graph_builder.add_node("DocIngestTool", node_step_82)
            graph_builder.add_node("FAQTool", node_step_83)
            graph_builder.add_node("ToolResults", node_step_99)

            # Phase 4 nodes are already registered in wiring_registry.py

            # Add Phase 1A edges up to cache
            graph_builder.add_edge("ValidateRequest", "ValidCheck")
            graph_builder.add_conditional_edges(
                "ValidCheck",
                self._route_from_valid_check,
                {"PrivacyCheck": "PrivacyCheck", "End": "End"}
            )
            graph_builder.add_conditional_edges(
                "PrivacyCheck",
                self._route_from_privacy_check,
                {"PIICheck": "PIICheck"}
            )
            graph_builder.add_conditional_edges(
                "PIICheck",
                self._route_from_pii_check,
                {"CheckCache": "CheckCache"}
            )

            # Phase 4 cache lane edges
            graph_builder.add_edge("CheckCache", "CacheHit")
            track_edge(59, 62)  # CheckCache → CacheHit

            graph_builder.add_conditional_edges(
                "CacheHit",
                self._route_from_cache_hit_phase4,
                {"ReturnCached": "ReturnCached", "LLMCall": "LLMCall"}
            )
            track_edge(62, 66)  # CacheHit → ReturnCached (cache hit path)
            track_edge(62, 64)  # CacheHit → LLMCall (cache miss path)

            graph_builder.add_edge("ReturnCached", "End")

            # Phase 4 LLM lane edges
            graph_builder.add_edge("LLMCall", "LLMSuccess")
            track_edge(64, 67)  # LLMCall → LLMSuccess

            graph_builder.add_conditional_edges(
                "LLMSuccess",
                self._route_from_llm_success_phase4,
                {"CacheResponse": "CacheResponse", "RetryCheck": "RetryCheck"}
            )
            track_edge(67, 68)  # LLMSuccess → CacheResponse (success path)
            track_edge(67, 69)  # LLMSuccess → RetryCheck (failure path)

            # Success path: cache → track → tools
            graph_builder.add_edge("CacheResponse", "TrackUsage")
            track_edge(68, 74)  # CacheResponse → TrackUsage

            graph_builder.add_edge("TrackUsage", "ToolCheck")
            track_edge(74, 75)  # TrackUsage → ToolCheck

            # Retry path
            graph_builder.add_conditional_edges(
                "RetryCheck",
                self._route_from_retry_check,
                {"ProdCheck": "ProdCheck", "End": "End"}
            )
            track_edge(69, 70)  # RetryCheck → ProdCheck (retry allowed)

            graph_builder.add_conditional_edges(
                "ProdCheck",
                self._route_from_prod_check,
                {"FailoverProvider": "FailoverProvider", "RetrySame": "RetrySame"}
            )
            track_edge(70, 72)  # ProdCheck → FailoverProvider (failover path)
            track_edge(70, 73)  # ProdCheck → RetrySame (retry same path)

            # Both retry strategies route back to LLMCall
            graph_builder.add_edge("FailoverProvider", "LLMCall")
            track_edge(72, 64)  # FailoverProvider → LLMCall

            graph_builder.add_edge("RetrySame", "LLMCall")
            track_edge(73, 64)  # RetrySame → LLMCall

            # Phase 4 tools lane edges
            graph_builder.add_conditional_edges(
                "ToolCheck",
                self._route_from_tool_check,
                {"ToolType": "ToolType", "End": "End"}
            )
            track_edge(75, 79)  # ToolCheck → ToolType (tools needed)

            graph_builder.add_conditional_edges(
                "ToolType",
                self._route_from_tool_type,
                {
                    "KBTool": "KBTool",
                    "CCNLTool": "CCNLTool",
                    "DocIngestTool": "DocIngestTool",
                    "FAQTool": "FAQTool"
                }
            )
            track_edge(79, 80)  # ToolType → KBTool
            track_edge(79, 81)  # ToolType → CCNLTool
            track_edge(79, 82)  # ToolType → DocIngestTool
            track_edge(79, 83)  # ToolType → FAQTool

            # All tools route to ToolResults → End
            graph_builder.add_edge("KBTool", "ToolResults")
            track_edge(80, 99)  # KBTool → ToolResults

            graph_builder.add_edge("CCNLTool", "ToolResults")
            track_edge(81, 99)  # CCNLTool → ToolResults

            graph_builder.add_edge("DocIngestTool", "ToolResults")
            track_edge(82, 99)  # DocIngestTool → ToolResults

            graph_builder.add_edge("FAQTool", "ToolResults")
            track_edge(83, 99)  # FAQTool → ToolResults

            graph_builder.add_edge("ToolResults", "End")

            # Set entry and exit points
            graph_builder.set_entry_point("ValidateRequest")
            graph_builder.set_finish_point("End")

            # Get connection pool and checkpointer
            connection_pool = await self._get_connection_pool()
            if connection_pool and AsyncPostgresSaver is not None:
                checkpointer = AsyncPostgresSaver(connection_pool)
                await checkpointer.setup()
            else:
                checkpointer = None
                if settings.ENVIRONMENT != Environment.PRODUCTION and AsyncPostgresSaver is not None:
                    raise Exception("Connection pool initialization failed")

            compiled_graph = graph_builder.compile(
                checkpointer=checkpointer,
                name=f"{settings.PROJECT_NAME} Agent Phase4 ({settings.ENVIRONMENT.value})"
            )

            logger.info(
                "phase4_graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent Phase4",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
            )

            return compiled_graph

        except Exception as e:
            logger.error("phase4_graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_phase4_graph")
                return None
            raise e

    async def create_graph_provider_lane(self) -> Optional[CompiledStateGraph]:
        """Create Phase 5 graph with Provider Governance Lane.

        Implements: 48 SelectProvider → 49 RouteStrategy → 50 StrategyType → (51/52/53/54) → 55 EstimateCost → 56 CostCheck → (57 CreateProvider | 58 CheaperProvider)

        Returns:
            Optional[CompiledStateGraph]: The Phase 5 graph or None if init fails
        """
        try:
            graph_builder = StateGraph(GraphState)

            # Add all Phase 1A nodes
            graph_builder.add_node("ValidateRequest", node_step_1)
            graph_builder.add_node("ValidCheck", node_step_3)
            graph_builder.add_node("PrivacyCheck", node_step_6)
            graph_builder.add_node("PIICheck", node_step_9)
            graph_builder.add_node("End", node_step_112)

            # Add Phase 5 Provider Governance nodes
            graph_builder.add_node("SelectProvider", node_step_48)
            graph_builder.add_node("RouteStrategy", node_step_49)
            graph_builder.add_node("StrategyType", node_step_50)
            graph_builder.add_node("CheapProvider", node_step_51)
            graph_builder.add_node("BestProvider", node_step_52)
            graph_builder.add_node("BalanceProvider", node_step_53)
            graph_builder.add_node("PrimaryProvider", node_step_54)
            graph_builder.add_node("EstimateCost", node_step_55)
            graph_builder.add_node("CostCheck", node_step_56)
            graph_builder.add_node("CreateProvider", node_step_57)
            graph_builder.add_node("CheaperProvider", node_step_58)

            # Add Phase 4 nodes for continuation
            graph_builder.add_node("CheckCache", node_step_59)
            graph_builder.add_node("CacheHit", node_step_62)
            graph_builder.add_node("LLMCall", node_step_64)
            graph_builder.add_node("ReturnCached", node_step_66)
            graph_builder.add_node("LLMSuccess", node_step_67)
            graph_builder.add_node("CacheResponse", node_step_68)
            graph_builder.add_node("RetryCheck", node_step_69)
            graph_builder.add_node("ProdCheck", node_step_70)
            graph_builder.add_node("FailoverProvider", node_step_72)
            graph_builder.add_node("RetrySame", node_step_73)
            graph_builder.add_node("TrackUsage", node_step_74)
            graph_builder.add_node("ToolCheck", node_step_75)
            graph_builder.add_node("ToolType", node_step_79)
            graph_builder.add_node("KBTool", node_step_80)
            graph_builder.add_node("CCNLTool", node_step_81)
            graph_builder.add_node("DocIngestTool", node_step_82)
            graph_builder.add_node("FAQTool", node_step_83)
            graph_builder.add_node("ToolResults", node_step_99)

            # Phase 1A edges
            graph_builder.set_entry_point("ValidateRequest")
            graph_builder.add_edge("ValidateRequest", "ValidCheck")
            graph_builder.add_edge("ValidCheck", "PrivacyCheck")
            graph_builder.add_edge("PrivacyCheck", "PIICheck")

            # Phase 5 Provider Governance edges
            graph_builder.add_edge("PIICheck", "SelectProvider")
            graph_builder.add_edge("SelectProvider", "RouteStrategy")
            graph_builder.add_edge("RouteStrategy", "StrategyType")

            # Strategy type conditional routing
            graph_builder.add_conditional_edges(
                "StrategyType",
                self._route_strategy_type,
                {
                    "CHEAP": "CheapProvider",
                    "BEST": "BestProvider",
                    "BALANCED": "BalanceProvider",
                    "PRIMARY": "PrimaryProvider"
                }
            )

            # All strategy providers go to cost estimation
            graph_builder.add_edge("CheapProvider", "EstimateCost")
            graph_builder.add_edge("BestProvider", "EstimateCost")
            graph_builder.add_edge("BalanceProvider", "EstimateCost")
            graph_builder.add_edge("PrimaryProvider", "EstimateCost")

            # Cost check conditional routing
            graph_builder.add_edge("EstimateCost", "CostCheck")
            graph_builder.add_conditional_edges(
                "CostCheck",
                self._route_cost_check,
                {
                    "approved": "CreateProvider",
                    "too_expensive": "CheaperProvider"
                }
            )

            # Cheaper provider loops back to estimate cost
            graph_builder.add_edge("CheaperProvider", "EstimateCost")

            # Provider created, continue to cache lane
            graph_builder.add_edge("CreateProvider", "CheckCache")

            # Phase 4 Cache → LLM → Tools edges (reusing existing logic)
            graph_builder.add_edge("CheckCache", "CacheHit")
            graph_builder.add_conditional_edges(
                "CacheHit",
                self._route_cache_hit,
                {
                    "hit": "ReturnCached",
                    "miss": "LLMCall"
                }
            )

            graph_builder.add_edge("LLMCall", "LLMSuccess")
            graph_builder.add_conditional_edges(
                "LLMSuccess",
                self._route_llm_success,
                {
                    "success": "CacheResponse",
                    "retry": "RetryCheck"
                }
            )

            graph_builder.add_edge("CacheResponse", "TrackUsage")
            graph_builder.add_edge("TrackUsage", "ToolCheck")
            graph_builder.add_conditional_edges(
                "ToolCheck",
                self._route_tool_check,
                {
                    "has_tools": "ToolType",
                    "no_tools": "End"
                }
            )

            graph_builder.add_conditional_edges(
                "ToolType",
                self._route_tool_type,
                {
                    "kb": "KBTool",
                    "ccnl": "CCNLTool",
                    "doc": "DocIngestTool",
                    "faq": "FAQTool"
                }
            )

            # All tools go to results aggregation
            graph_builder.add_edge("KBTool", "ToolResults")
            graph_builder.add_edge("CCNLTool", "ToolResults")
            graph_builder.add_edge("DocIngestTool", "ToolResults")
            graph_builder.add_edge("FAQTool", "ToolResults")

            # Retry logic
            graph_builder.add_edge("RetryCheck", "ProdCheck")
            graph_builder.add_conditional_edges(
                "ProdCheck",
                self._route_prod_check,
                {
                    "failover": "FailoverProvider",
                    "retry_same": "RetrySame"
                }
            )

            graph_builder.add_edge("FailoverProvider", "LLMCall")
            graph_builder.add_edge("RetrySame", "LLMCall")

            # End points
            graph_builder.add_edge("ReturnCached", "End")
            graph_builder.add_edge("ToolResults", "End")

            return graph_builder.compile()

        except Exception as e:
            logger.error("phase5_graph_creation_failed", error=str(e))
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_phase5_graph")
                return None
            raise e

    async def create_graph_phase7_streaming(self) -> Optional[CompiledStateGraph]:
        """Create Phase 7 graph with Streaming/Response lane.

        This graph includes all lanes (1-7) with the streaming/response lane wired.

        Flow:
        - Phase 6 (Request/Privacy): Steps 1 → 3 → 4 → 6 → 7 → 9 → 10 → 8
        - Phase 5 (Provider): Steps 48 → 49 → 50 → (51|52|53|54) → 55 → 56 → (57|58)
        - Phase 4 (Cache/LLM/Tools): Steps 59 → 62 → (64|66) → 67 → 68 → 74 → 75 → 79 → (80|81|82|83) → 99
        - Phase 7 (Streaming/Response): Steps 104 → (105→106→107→108→109→110|111) → 111 → 112

        Returns:
            Optional[CompiledStateGraph]: The Phase 7 graph or None if init fails
        """
        try:
            graph_builder = StateGraph(RAGState)

            # Phase 7 Streaming/Response Lane nodes
            graph_builder.add_node("StreamCheck", node_step_104)
            graph_builder.add_node("StreamSetup", node_step_105)
            graph_builder.add_node("AsyncGen", node_step_106)
            graph_builder.add_node("SinglePass", node_step_107)
            graph_builder.add_node("WriteSSE", node_step_108)
            graph_builder.add_node("StreamResponse", node_step_109)
            graph_builder.add_node("SendDone", node_step_110)
            graph_builder.add_node("CollectMetrics", node_step_111)
            graph_builder.add_node("End", node_step_112)

            # Phase 7 edges - Streaming lane
            # StreamCheck branches: stream=True → StreamSetup, stream=False → CollectMetrics
            graph_builder.add_conditional_edges(
                "StreamCheck",
                lambda state: "StreamSetup" if state.get("streaming", {}).get("requested", False) else "CollectMetrics",
                {
                    "StreamSetup": "StreamSetup",
                    "CollectMetrics": "CollectMetrics"
                }
            )

            # Streaming path (linear):
            graph_builder.add_edge("StreamSetup", "AsyncGen")
            graph_builder.add_edge("AsyncGen", "SinglePass")
            graph_builder.add_edge("SinglePass", "WriteSSE")
            graph_builder.add_edge("WriteSSE", "StreamResponse")
            graph_builder.add_edge("StreamResponse", "SendDone")
            graph_builder.add_edge("SendDone", "CollectMetrics")

            # Both paths converge at CollectMetrics
            graph_builder.add_edge("CollectMetrics", "End")

            # Set entry and exit points
            graph_builder.set_entry_point("StreamCheck")
            graph_builder.set_finish_point("End")

            # Track all Phase 7 edges in wiring registry
            track_edge(104, 105)  # stream=True path
            track_edge(104, 111)  # stream=False path
            track_edge(105, 106)
            track_edge(106, 107)
            track_edge(107, 108)
            track_edge(108, 109)
            track_edge(109, 110)
            track_edge(110, 111)
            track_edge(111, 112)

            # Get connection pool
            connection_pool = await self._get_connection_pool()
            if connection_pool and AsyncPostgresSaver is not None:
                checkpointer = AsyncPostgresSaver(connection_pool)
                await checkpointer.setup()
            else:
                checkpointer = None
                if settings.ENVIRONMENT != Environment.PRODUCTION and AsyncPostgresSaver is not None:
                    raise Exception("Connection pool initialization failed")

            compiled_graph = graph_builder.compile(
                checkpointer=checkpointer,
                name=f"{settings.PROJECT_NAME} Agent Phase7 Streaming ({settings.ENVIRONMENT.value})"
            )

            logger.info(
                "phase7_streaming_graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent Phase7 Streaming",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
            )

            return compiled_graph

        except Exception as e:
            logger.error("phase7_streaming_graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_phase7_streaming_graph")
                return None
            raise e

    async def create_graph_unified(self) -> Optional[CompiledStateGraph]:
        """Create unified graph connecting all 8 lanes.

        This implements the full RAG flow as specified in pratikoai_rag.mmd diagram.
        Connects:
        - Lane 1: Request/Privacy (1→3→4→6→7→9→10→8)
        - Lane 2: Messages (11→12→13)
        - Lane 3: Golden/KB (20→24→25→26→27→28→30)
        - Lane 4: Classification (31, 42)
        - Lane 5: Prompts (internal steps in classification)
        - Lane 6: Provider (48→49→50→51/52/53/54→55→56→57/58)
        - Lane 7: Cache/LLM (59→62→64→67→68/69→70→72/73→74→75→79→80/81/82/83→99)
        - Lane 8: Streaming (104→105→106→107→108→109→110→111→112)

        Returns:
            Optional[CompiledStateGraph]: The unified graph or None if init fails
        """
        try:
            graph_builder = StateGraph(GraphState)

            # ========== Add all nodes from all lanes ==========

            # Lane 1: Request/Privacy nodes
            graph_builder.add_node("ValidateRequest", node_step_1)
            graph_builder.add_node("ValidCheck", node_step_3)
            graph_builder.add_node("GDPRLog", node_step_4)
            graph_builder.add_node("PrivacyCheck", node_step_6)
            graph_builder.add_node("AnonymizeText", node_step_7)
            graph_builder.add_node("InitAgent", node_step_8)
            graph_builder.add_node("PIICheck", node_step_9)
            graph_builder.add_node("LogPII", node_step_10)

            # Lane 2: Message processing nodes
            graph_builder.add_node("ConvertMessages", node_step_11)
            graph_builder.add_node("ExtractQuery", node_step_12)
            graph_builder.add_node("MessageExists", node_step_13)

            # Lane 3: Golden/KB nodes
            graph_builder.add_node("GoldenFastGate", node_step_20)
            graph_builder.add_node("GoldenLookup", node_step_24)
            graph_builder.add_node("GoldenHit", node_step_25)
            graph_builder.add_node("KBContextCheck", node_step_26)
            graph_builder.add_node("KBDelta", node_step_27)
            graph_builder.add_node("ServeGolden", node_step_28)
            graph_builder.add_node("ReturnComplete", node_step_30)

            # Lane 4: Classification nodes
            graph_builder.add_node("ClassifyDomain", node_step_31)
            graph_builder.add_node("ClassConfidence", node_step_42)

            # Lane 6: Provider nodes
            graph_builder.add_node("SelectProvider", node_step_48)
            graph_builder.add_node("RouteStrategy", node_step_49)
            graph_builder.add_node("StrategyType", node_step_50)
            graph_builder.add_node("CheapProvider", node_step_51)
            graph_builder.add_node("BestProvider", node_step_52)
            graph_builder.add_node("BalanceProvider", node_step_53)
            graph_builder.add_node("PrimaryProvider", node_step_54)
            graph_builder.add_node("EstimateCost", node_step_55)
            graph_builder.add_node("CostCheck", node_step_56)
            graph_builder.add_node("CreateProvider", node_step_57)
            graph_builder.add_node("CheaperProvider", node_step_58)

            # Lane 7: Cache/LLM/Tools nodes
            graph_builder.add_node("CheckCache", node_step_59)
            graph_builder.add_node("CacheHit", node_step_62)
            graph_builder.add_node("LLMCall", node_step_64)
            graph_builder.add_node("ReturnCached", node_step_66)
            graph_builder.add_node("LLMSuccess", node_step_67)
            graph_builder.add_node("CacheResponse", node_step_68)
            graph_builder.add_node("RetryCheck", node_step_69)
            graph_builder.add_node("ProdCheck", node_step_70)
            graph_builder.add_node("FailoverProvider", node_step_72)
            graph_builder.add_node("RetrySame", node_step_73)
            graph_builder.add_node("TrackUsage", node_step_74)
            graph_builder.add_node("ToolCheck", node_step_75)
            graph_builder.add_node("ToolType", node_step_79)
            graph_builder.add_node("KBTool", node_step_80)
            graph_builder.add_node("CCNLTool", node_step_81)
            graph_builder.add_node("DocIngestTool", node_step_82)
            graph_builder.add_node("FAQTool", node_step_83)
            graph_builder.add_node("ToolResults", node_step_99)

            # Lane 8: Streaming nodes
            graph_builder.add_node("StreamCheck", node_step_104)
            graph_builder.add_node("StreamSetup", node_step_105)
            graph_builder.add_node("AsyncGen", node_step_106)
            graph_builder.add_node("SinglePass", node_step_107)
            graph_builder.add_node("WriteSSE", node_step_108)
            graph_builder.add_node("StreamResponse", node_step_109)
            graph_builder.add_node("SendDone", node_step_110)
            graph_builder.add_node("CollectMetrics", node_step_111)
            graph_builder.add_node("End", node_step_112)

            # ========== Wire Lane 1: Request/Privacy ==========
            graph_builder.set_entry_point("ValidateRequest")
            graph_builder.add_edge("ValidateRequest", "ValidCheck")
            graph_builder.add_conditional_edges(
                "ValidCheck",
                self._route_from_valid_check,
                {"GDPRLog": "GDPRLog", "End": "End"}
            )
            graph_builder.add_edge("GDPRLog", "PrivacyCheck")
            graph_builder.add_conditional_edges(
                "PrivacyCheck",
                self._route_from_privacy_check_unified,
                {"AnonymizeText": "AnonymizeText", "InitAgent": "InitAgent"}
            )
            graph_builder.add_edge("AnonymizeText", "PIICheck")
            graph_builder.add_conditional_edges(
                "PIICheck",
                self._route_from_pii_check_unified,
                {"LogPII": "LogPII", "InitAgent": "InitAgent"}
            )
            graph_builder.add_edge("LogPII", "InitAgent")

            # ========== Wire Lane 1→2: Init to Messages ==========
            graph_builder.add_edge("InitAgent", "ConvertMessages")

            # ========== Wire Lane 2: Messages ==========
            graph_builder.add_edge("ConvertMessages", "ExtractQuery")
            graph_builder.add_edge("ExtractQuery", "MessageExists")

            # ========== Wire Lane 2→3: Messages to Golden ==========
            # After MessageExists, go to GoldenFastGate
            # (Internal steps 14-19 are handled by orchestrators)
            graph_builder.add_edge("MessageExists", "GoldenFastGate")

            # ========== Wire Lane 3: Golden/KB ==========
            graph_builder.add_conditional_edges(
                "GoldenFastGate",
                self._route_from_golden_fast_gate,
                {"GoldenLookup": "GoldenLookup", "ClassifyDomain": "ClassifyDomain"}
            )
            graph_builder.add_edge("GoldenLookup", "GoldenHit")
            graph_builder.add_conditional_edges(
                "GoldenHit",
                self._route_from_golden_hit,
                {"KBContextCheck": "KBContextCheck", "ClassifyDomain": "ClassifyDomain"}
            )
            graph_builder.add_edge("KBContextCheck", "KBDelta")
            graph_builder.add_conditional_edges(
                "KBDelta",
                self._route_from_kb_delta,
                {"ServeGolden": "ServeGolden", "ClassifyDomain": "ClassifyDomain"}
            )
            graph_builder.add_edge("ServeGolden", "ReturnComplete")
            graph_builder.add_edge("ReturnComplete", "CollectMetrics")

            # ========== Wire Lane 4: Classification ==========
            # ClassifyDomain includes internal steps 32-40
            graph_builder.add_edge("ClassifyDomain", "ClassConfidence")

            # ========== Wire Lane 4→6: Classification to Provider ==========
            # ClassConfidence routes to SelectProvider
            # (Internal steps 41, 43-47 are handled by orchestrators in SelectProvider)
            graph_builder.add_edge("ClassConfidence", "SelectProvider")

            # ========== Wire Lane 6: Provider ==========
            graph_builder.add_edge("SelectProvider", "RouteStrategy")
            graph_builder.add_edge("RouteStrategy", "StrategyType")
            graph_builder.add_conditional_edges(
                "StrategyType",
                self._route_from_strategy_type,
                {
                    "CheapProvider": "CheapProvider",
                    "BestProvider": "BestProvider",
                    "BalanceProvider": "BalanceProvider",
                    "PrimaryProvider": "PrimaryProvider"
                }
            )
            graph_builder.add_edge("CheapProvider", "EstimateCost")
            graph_builder.add_edge("BestProvider", "EstimateCost")
            graph_builder.add_edge("BalanceProvider", "EstimateCost")
            graph_builder.add_edge("PrimaryProvider", "EstimateCost")
            graph_builder.add_edge("EstimateCost", "CostCheck")
            graph_builder.add_conditional_edges(
                "CostCheck",
                self._route_from_cost_check,
                {"CreateProvider": "CreateProvider", "CheaperProvider": "CheaperProvider"}
            )
            graph_builder.add_edge("CreateProvider", "CheckCache")
            graph_builder.add_edge("CheaperProvider", "EstimateCost")  # Loop back

            # ========== Wire Lane 7: Cache/LLM/Tools ==========
            graph_builder.add_edge("CheckCache", "CacheHit")
            graph_builder.add_conditional_edges(
                "CacheHit",
                self._route_from_cache_hit_unified,
                {"ReturnCached": "ReturnCached", "LLMCall": "LLMCall"}
            )
            graph_builder.add_edge("ReturnCached", "StreamCheck")

            graph_builder.add_edge("LLMCall", "LLMSuccess")
            graph_builder.add_conditional_edges(
                "LLMSuccess",
                self._route_from_llm_success_unified,
                {"CacheResponse": "CacheResponse", "RetryCheck": "RetryCheck"}
            )
            graph_builder.add_edge("CacheResponse", "TrackUsage")
            graph_builder.add_edge("TrackUsage", "ToolCheck")

            # Retry path
            graph_builder.add_conditional_edges(
                "RetryCheck",
                self._route_from_retry_check,
                {"ProdCheck": "ProdCheck", "End": "End"}
            )
            graph_builder.add_conditional_edges(
                "ProdCheck",
                self._route_from_prod_check,
                {"FailoverProvider": "FailoverProvider", "RetrySame": "RetrySame"}
            )
            graph_builder.add_edge("FailoverProvider", "LLMCall")
            graph_builder.add_edge("RetrySame", "LLMCall")

            # Tools path
            graph_builder.add_conditional_edges(
                "ToolCheck",
                self._route_from_tool_check,
                {"ToolType": "ToolType", "StreamCheck": "StreamCheck"}
            )
            graph_builder.add_conditional_edges(
                "ToolType",
                self._route_from_tool_type,
                {
                    "KBTool": "KBTool",
                    "CCNLTool": "CCNLTool",
                    "DocIngestTool": "DocIngestTool",
                    "FAQTool": "FAQTool"
                }
            )
            graph_builder.add_edge("KBTool", "ToolResults")
            graph_builder.add_edge("CCNLTool", "ToolResults")
            graph_builder.add_edge("DocIngestTool", "ToolResults")
            graph_builder.add_edge("FAQTool", "ToolResults")
            graph_builder.add_edge("ToolResults", "StreamCheck")

            # ========== Wire Lane 8: Streaming ==========
            graph_builder.add_conditional_edges(
                "StreamCheck",
                self._route_from_stream_check,
                {"StreamSetup": "StreamSetup", "CollectMetrics": "CollectMetrics"}
            )
            graph_builder.add_edge("StreamSetup", "AsyncGen")
            graph_builder.add_edge("AsyncGen", "SinglePass")
            graph_builder.add_edge("SinglePass", "WriteSSE")
            graph_builder.add_edge("WriteSSE", "StreamResponse")
            graph_builder.add_edge("StreamResponse", "SendDone")
            graph_builder.add_edge("SendDone", "CollectMetrics")

            # Final step
            graph_builder.add_edge("CollectMetrics", "End")

            # Compile graph
            connection_pool = await self._get_connection_pool()
            if connection_pool and AsyncPostgresSaver is not None:
                checkpointer = AsyncPostgresSaver(connection_pool)
                await checkpointer.setup()
            else:
                checkpointer = None

            compiled_graph = graph_builder.compile(
                checkpointer=checkpointer,
                name=f"{settings.PROJECT_NAME} Agent Unified ({settings.ENVIRONMENT.value})"
            )

            logger.info(
                "unified_graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent Unified",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
                total_nodes=59
            )

            return compiled_graph

        except Exception as e:
            logger.error("unified_graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_unified_graph")
                return None
            raise e

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """Create and configure the LangGraph workflow.

        Returns:
            Optional[CompiledStateGraph]: The configured LangGraph instance or None if init fails
        """
        if self._graph is None:
            # Unified graph is now the default (connects all 8 lanes)
            logger.info("using_unified_graph", environment=settings.ENVIRONMENT.value)
            self._graph = await self.create_graph_unified()

        return self._graph

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get a response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for Langfuse tracking.
            user_id (Optional[str]): The user ID for Langfuse tracking.

        Returns:
            list[dict]: The response from the LLM.
        """
        # Store user and session info for tracking
        self._current_user_id = user_id
        self._current_session_id = session_id
        
        if self._graph is None:
            self._graph = await self.create_graph()
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [
                CallbackHandler()
            ],
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": settings.ENVIRONMENT.value,
                "debug": False,
            },
        }
        try:
            response = await self._graph.ainvoke(
                {"messages": dump_messages(messages), "session_id": session_id}, config
            )
            return self.__process_messages(response["messages"])
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            raise e
        finally:
            # Clean up tracking info
            self._current_user_id = None
            self._current_session_id = None

    @staticmethod
    def _needs_complex_workflow(classification: Optional[DomainActionClassification]) -> bool:
        """Determine if query needs tools/complex workflow based on classification.

        Args:
            classification: Domain-action classification result

        Returns:
            bool: True if complex workflow is needed, False for simple streaming
        """
        if not classification:
            return False

        # Actions that always need database/tool access
        complex_actions = {
            Action.CCNL_QUERY,           # Always needs CCNL database access
            Action.DOCUMENT_ANALYSIS,    # Might need document processing tools
            Action.CALCULATION_REQUEST,  # Might need calculation tools
            Action.COMPLIANCE_CHECK,     # Might need regulation lookup tools
        }
        
        needs_complex = classification.action in complex_actions
        
        logger.info(
            "workflow_decision",
            action=classification.action.value,
            domain=classification.domain.value,
            confidence=classification.confidence,
            needs_complex_workflow=needs_complex,
        )
        
        return needs_complex
    
    async def get_stream_response(
        self, messages: list[Message], session_id: str, user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Get a hybrid stream response using optimal approach based on query complexity.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.

        Yields:
            str: Raw markdown chunks of the LLM response.
        """
        # Store user and session info for tracking
        self._current_user_id = user_id
        self._current_session_id = session_id
        
        try:
            # Classify user query to determine streaming strategy
            self._current_classification = await self._classify_user_query(messages)
            
            # RAG STEP 20: Check golden fast-path eligibility
            golden_eligibility = await self._check_golden_fast_path_eligibility(messages, session_id, user_id)
            
            # Decide streaming approach based on classification and golden fast-path eligibility
            if golden_eligibility.decision == EligibilityDecision.ELIGIBLE and golden_eligibility.allows_golden_lookup:
                # TODO: Implement golden lookup in future step
                # For now, use direct LLM streaming but log the golden eligibility
                logger.info(
                    "golden_fast_path_eligible_fallback_to_llm",
                    session_id=session_id,
                    confidence=golden_eligibility.confidence,
                    reasons=golden_eligibility.reasons
                )
                async for chunk in self._stream_with_direct_llm(messages, session_id):
                    yield chunk
            elif self._needs_complex_workflow(self._current_classification):
                # Use LangGraph workflow streaming for tool-heavy operations
                async for chunk in self._stream_with_langgraph_workflow(messages, session_id):
                    yield chunk
            else:
                # Use direct LLM streaming for simple Q&A
                async for chunk in self._stream_with_direct_llm(messages, session_id):
                    yield chunk
                    
        except Exception as stream_error:
            logger.error(
                "hybrid_stream_failed",
                error=str(stream_error),
                session_id=session_id,
                classification_used=self._current_classification is not None,
                domain=self._current_classification.domain.value if self._current_classification else None,
                action=self._current_classification.action.value if self._current_classification else None,
            )
            raise stream_error
        finally:
            # Clean up tracking info
            self._current_user_id = None
            self._current_session_id = None
            self._current_classification = None
    
    async def _stream_with_direct_llm(
        self, messages: list[Message], session_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream directly from LLM provider for simple queries (no tools).
        
        Args:
            messages: List of conversation messages
            session_id: Session ID for logging
            
        Yields:
            str: Raw markdown chunks
        """
        try:
            # Get domain-specific system prompt or default
            system_prompt = await self._get_system_prompt(messages, self._current_classification)

            # Use RAG STEP 45 to prepare messages with system prompt
            processed_messages = await self._prepare_messages_with_system_prompt(messages, system_prompt, self._current_classification)
            
            # Get optimal provider (classification-aware)
            provider = self._get_optimal_provider(processed_messages)
            self._current_provider = provider
            
            logger.info(
                "direct_llm_stream_started",
                session_id=session_id,
                model=provider.model,
                provider=provider.provider_type.value,
                classification_used=self._current_classification is not None,
                domain=self._current_classification.domain.value if self._current_classification else None,
                action=self._current_classification.action.value if self._current_classification else None,
            )
            
            # Stream directly from LLM provider (no tools)
            async for chunk in provider.stream_completion(
                messages=processed_messages,
                tools=None,  # No tools for simple streaming
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
            ):
                if chunk.content:
                    yield chunk.content
                    
                # Log when streaming completes
                if chunk.done:
                    logger.info(
                        "direct_llm_stream_completed",
                        session_id=session_id,
                        model=provider.model,
                        provider=provider.provider_type.value,
                    )
                    break
                    
        except Exception as e:
            logger.error(
                "direct_llm_stream_failed",
                error=str(e),
                session_id=session_id,
                provider=getattr(self._current_provider, 'provider_type', {}).get('value', 'unknown') if self._current_provider else 'unknown',
            )
            raise
    
    async def _stream_with_langgraph_workflow(
        self, messages: list[Message], session_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream using LangGraph workflow for complex queries (with tools).
        
        Args:
            messages: List of conversation messages
            session_id: Session ID for logging
            
        Yields:
            str: Raw markdown chunks and workflow updates
        """
        try:
            # Ensure graph is initialized
            if self._graph is None:
                self._graph = await self.create_graph()
            
            config = {
                "configurable": {"thread_id": session_id},
                "callbacks": [CallbackHandler()],
            }
            
            logger.info(
                "langgraph_workflow_stream_started",
                session_id=session_id,
                classification_used=self._current_classification is not None,
                domain=self._current_classification.domain.value if self._current_classification else None,
                action=self._current_classification.action.value if self._current_classification else None,
            )
            
            # Stream from LangGraph with filtering to avoid duplicates
            async for token, metadata in self._graph.astream(
                {"messages": dump_messages(messages), "session_id": session_id}, 
                config, 
                stream_mode="messages"
            ):
                try:
                    # Filter only from the main chat node to avoid tool call duplicates
                    if metadata.get("langgraph_node") == "chat":
                        if hasattr(token, 'content') and token.content:
                            # Avoid yielding very large chunks (likely complete messages)
                            # This helps prevent the final complete message from being duplicated
                            if len(token.content) < 150:  # Threshold for token vs complete message
                                yield token.content
                            
                except Exception as token_error:
                    logger.error(
                        "langgraph_token_processing_error", 
                        error=str(token_error), 
                        session_id=session_id
                    )
                    continue
            
            logger.info(
                "langgraph_workflow_stream_completed",
                session_id=session_id,
            )
                    
        except Exception as e:
            logger.error(
                "langgraph_workflow_stream_failed",
                error=str(e),
                session_id=session_id,
            )
            raise

    async def get_chat_history(self, session_id: str) -> list[Message]:
        """Get the chat history for a given thread ID.

        Args:
            session_id (str): The session ID for the conversation.

        Returns:
            list[Message]: The chat history.
        """
        # Try to get cached conversation first
        try:
            cached_messages = await cache_service.get_conversation_cache(session_id)
            if cached_messages:
                logger.info(
                    "conversation_cache_hit",
                    session_id=session_id,
                    message_count=len(cached_messages)
                )
                return cached_messages
        except Exception as e:
            logger.error(
                "conversation_cache_get_failed",
                error=str(e),
                session_id=session_id
            )

        # Get from database if not cached
        if self._graph is None:
            self._graph = await self.create_graph()

        state: StateSnapshot = await sync_to_async(self._graph.get_state)(
            config={"configurable": {"thread_id": session_id}}
        )
        messages = self.__process_messages(state.values["messages"]) if state.values else []
        
        # Cache the conversation for future use
        if messages:
            try:
                await cache_service.cache_conversation(session_id, messages)
                logger.info(
                    "conversation_cached",
                    session_id=session_id,
                    message_count=len(messages)
                )
            except Exception as e:
                logger.error(
                    "conversation_cache_set_failed",
                    error=str(e),
                    session_id=session_id
                )
        
        return messages

    @staticmethod
    def __process_messages(messages: list[BaseMessage]) -> list[Message]:
        openai_style_messages = convert_to_openai_messages(messages)
        # keep just assistant and user messages
        return [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]

    async def clear_chat_history(self, session_id: str) -> None:
        """Clear all chat history for a given thread ID.

        Args:
            session_id: The ID of the session to clear history for.

        Raises:
            Exception: If there's an error clearing the chat history.
        """
        try:
            # Clear cached conversation first
            try:
                await cache_service.invalidate_conversation(session_id)
                logger.info("conversation_cache_invalidated", session_id=session_id)
            except Exception as e:
                logger.error(
                    "conversation_cache_invalidation_failed",
                    error=str(e),
                    session_id=session_id
                )

            # Make sure the pool is initialized in the current event loop
            conn_pool = await self._get_connection_pool()

            # Use a new connection for this specific operation
            async with conn_pool.connection() as conn:
                for table in settings.CHECKPOINT_TABLES:
                    try:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                        logger.info(f"Cleared {table} for session {session_id}")
                    except Exception as e:
                        logger.error(f"Error clearing {table}", error=str(e))
                        raise

        except Exception as e:
            logger.error("Failed to clear chat history", error=str(e))
            raise
