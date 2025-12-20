"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

# ruff: noqa: E402
# E402: Module level imports appear after code due to fallback handling for langgraph

import asyncio
import traceback
from collections.abc import AsyncGenerator
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
)

from asgiref.sync import sync_to_async
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
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
    class END:  # type: ignore[no-redef]
        pass

    class StateGraph:  # type: ignore[no-redef]
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

    class CompiledStateGraph:  # type: ignore[no-redef]
        async def ainvoke(self, state, **kwargs):
            return state

    class StateSnapshot:  # type: ignore[no-redef]
        pass


from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.tools import tools
from app.core.langgraph.types import RAGState
from app.core.llm.base import LLMProvider
from app.core.llm.factory import (
    RoutingStrategy,
    get_llm_provider,
)
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.monitoring.metrics import (
    track_api_call,
    track_classification_usage,
    track_llm_cost,
)
from app.core.prompts import SYSTEM_PROMPT
from app.schemas import (
    AttachmentInfo,
    GraphState,
    Message,
)
from app.services.cache import cache_service
from app.services.domain_action_classifier import (
    Action,
    DomainActionClassification,
    DomainActionClassifier,
)
from app.services.domain_prompt_templates import PromptTemplateManager
from app.services.golden_fast_path import (
    EligibilityResult,
    GoldenFastPathService,
)
from app.services.usage_tracker import usage_tracker
from app.utils import dump_messages

# Canonical observability imports (unified across repo)
try:
    from app.observability.rag_logging import (
        rag_step_log,
        rag_step_timer,
    )
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
from app.core.langgraph.nodes import (  # noqa: E402
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
from app.core.langgraph.nodes.step_004__gdpr_log import node_step_4  # noqa: E402
from app.core.langgraph.nodes.step_005__error400 import node_step_5  # noqa: E402
from app.core.langgraph.nodes.step_007__anonymize_text import node_step_7  # noqa: E402
from app.core.langgraph.nodes.step_008__init_agent import node_step_8  # noqa: E402
from app.core.langgraph.nodes.step_010__log_pii import node_step_10  # noqa: E402

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
from app.core.langgraph.nodes.step_032__calc_scores import node_step_32
from app.core.langgraph.nodes.step_033__confidence_check import node_step_33
from app.core.langgraph.nodes.step_034__track_metrics import node_step_34
from app.core.langgraph.nodes.step_035__llm_fallback import node_step_35
from app.core.langgraph.nodes.step_036__llm_better import node_step_36
from app.core.langgraph.nodes.step_037__use_llm import node_step_37
from app.core.langgraph.nodes.step_038__use_rule_based import node_step_38
from app.core.langgraph.nodes.step_039__kbpre_fetch import node_step_39
from app.core.langgraph.nodes.step_040__build_context import node_step_40
from app.core.langgraph.nodes.step_041__select_prompt import node_step_41
from app.core.langgraph.nodes.step_042__class_confidence import node_step_42
from app.core.langgraph.nodes.step_043__domain_prompt import node_step_43
from app.core.langgraph.nodes.step_044__default_sys_prompt import node_step_44
from app.core.langgraph.nodes.step_045__check_sys_msg import node_step_45
from app.core.langgraph.nodes.step_046__replace_msg import node_step_46
from app.core.langgraph.nodes.step_047__insert_msg import node_step_47

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

# Phase 4 Node imports
from app.core.langgraph.nodes.step_066__return_cached import node_step_66  # noqa: E402
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

# Phase 7 Node imports - Streaming/Response Lane
from app.core.langgraph.nodes.step_104__stream_check import node_step_104
from app.core.langgraph.nodes.step_105__stream_setup import node_step_105
from app.core.langgraph.nodes.step_106__async_gen import node_step_106
from app.core.langgraph.nodes.step_107__single_pass import node_step_107
from app.core.langgraph.nodes.step_108__write_sse import node_step_108
from app.core.langgraph.nodes.step_109__stream_response import node_step_109
from app.core.langgraph.nodes.step_110__send_done import node_step_110
from app.core.langgraph.nodes.step_111__collect_metrics import node_step_111

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

# Phase 1A nodes are now the default implementation


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
        self._connection_pool: AsyncConnectionPool | None = None
        self._graph: CompiledStateGraph | None = None
        self._current_provider: LLMProvider | None = None

        # Initialize domain-action classification services
        self._domain_classifier = DomainActionClassifier()
        self._prompt_template_manager = PromptTemplateManager()
        self._golden_fast_path_service = GoldenFastPathService()
        self._current_classification = None  # Store current query classification
        self._response_metadata = None  # Store response metadata

        # Initialize tracking attributes
        self._current_user_id: str | None = None
        self._current_session_id: str | None = None

        logger.info("llm_agent_initialized", environment=settings.ENVIRONMENT.value)

    async def _classify_user_query(self, messages: list[Message]) -> DomainActionClassification | None:
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
        # Handle both dict and Message object formats
        user_message = None
        for message in reversed(messages):
            # Get role - handle both dict and object formats
            role = message.role if hasattr(message, "role") else message.get("role")
            if role == "user":
                # Get content - handle both dict and object formats
                user_message = message.content if hasattr(message, "content") else message.get("content")
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
                fallback_used=classification.fallback_used,
            )

            # Track classification metrics
            track_classification_usage(
                domain=classification.domain.value,
                action=classification.action.value,
                confidence=classification.confidence,
                fallback_used=classification.fallback_used,
            )

            return classification

        except Exception as e:
            logger.error("query_classification_failed", error=str(e), exc_info=True)
            return None

    async def _check_golden_fast_path_eligibility(
        self, messages: list[Message], session_id: str, user_id: str | None
    ) -> EligibilityResult:
        """Check if the current query is eligible for golden fast-path processing.

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
            from app.services.golden_fast_path import (
                EligibilityDecision,
                EligibilityResult,
            )

            return EligibilityResult(
                decision=EligibilityDecision.NOT_ELIGIBLE,
                confidence=1.0,
                reasons=["no_user_message"],
                next_step="ClassifyDomain",
                allows_golden_lookup=False,
            )

        # Prepare query data for golden fast-path service
        query_data = {
            "query": user_message,
            "attachments": [],  # TODO: Extract attachments from request context in future
            "user_id": user_id or "anonymous",
            "session_id": session_id,
            "canonical_facts": [],  # TODO: Extract from atomic facts extraction in future
            "query_signature": f"session_{session_id}_{hash(user_message)}",
            "trace_id": f"trace_{session_id}_{int(time.time())}",
        }

        # Check eligibility using golden fast-path service
        return await self._golden_fast_path_service.is_eligible_for_fast_path(query_data)

    async def _get_cached_llm_response(
        self, provider: LLMProvider, messages: list[Message], tools: list, temperature: float, max_tokens: int
    ):
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
                messages=messages, model=provider.model, temperature=temperature
            )
            if cached_response:
                logger.info(
                    "llm_cache_hit",
                    model=provider.model,
                    provider=provider.provider_type.value,
                    message_count=len(messages),
                )

                # Track cache hit usage
                if hasattr(self, "_current_session_id") and hasattr(self, "_current_user_id"):
                    try:
                        await usage_tracker.track_llm_usage(
                            user_id=self._current_user_id,
                            session_id=self._current_session_id,
                            provider=provider.provider_type.value,
                            model=provider.model,
                            llm_response=cached_response,
                            response_time_ms=10,  # Minimal time for cache hit
                            cache_hit=True,
                            pii_detected=getattr(self, "_pii_detected", False),
                            pii_types=getattr(self, "_pii_types", None),
                        )
                    except Exception as e:
                        logger.error(
                            "cache_hit_tracking_failed",
                            error=str(e),
                            provider=provider.provider_type.value,
                            model=provider.model,
                        )

                return cached_response
        except Exception as e:
            logger.error("llm_cache_get_failed", error=str(e), model=provider.model)

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
            user_id = getattr(self, "_current_user_id", "unknown")

            # Track API call success/failure
            status = "success" if response else "error"
            track_api_call(provider=provider.provider_type.value, model=provider.model, status=status)

            # Track cost if response contains cost information
            if response and hasattr(response, "cost_eur") and response.cost_eur:
                track_llm_cost(
                    provider=provider.provider_type.value,
                    model=provider.model,
                    user_id=user_id,
                    cost_eur=response.cost_eur,
                )

        except Exception as e:
            logger.error(
                "prometheus_metrics_tracking_failed",
                error=str(e),
                provider=provider.provider_type.value,
                model=provider.model,
            )

        # Track usage (only for non-cached responses)
        if hasattr(self, "_current_session_id") and hasattr(self, "_current_user_id"):
            try:
                await usage_tracker.track_llm_usage(
                    user_id=self._current_user_id,
                    session_id=self._current_session_id,
                    provider=provider.provider_type.value,
                    model=provider.model,
                    llm_response=response,
                    response_time_ms=response_time_ms,
                    cache_hit=False,
                    pii_detected=getattr(self, "_pii_detected", False),
                    pii_types=getattr(self, "_pii_types", None),
                )
            except Exception as e:
                logger.error(
                    "usage_tracking_failed", error=str(e), provider=provider.provider_type.value, model=provider.model
                )

        # Cache the response for future use
        try:
            await cache_service.cache_response(
                messages=messages, model=provider.model, response=response, temperature=temperature
            )
            logger.info(
                "llm_response_cached",
                model=provider.model,
                provider=provider.provider_type.value,
                response_length=len(response.content),
            )
        except Exception as e:
            logger.error("llm_cache_set_failed", error=str(e), model=provider.model)

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

        strategy_str = getattr(settings, "LLM_ROUTING_STRATEGY", "cost_optimized")
        return strategy_map.get(strategy_str, RoutingStrategy.COST_OPTIMIZED)

    @staticmethod
    def _get_classification_aware_routing(classification: DomainActionClassification) -> tuple[RoutingStrategy, float]:
        """Return (routing_strategy, max_cost_eur) based solely on domain/action mapping.
        - No confidence-based scaling.
        - Apply global cap only if explicitly provided (non-None).
        """
        strategy_map = {
            # High-accuracy requirements
            ("legal", "document_generation"): (RoutingStrategy.QUALITY_FIRST, 0.030),
            ("legal", "compliance_check"): (RoutingStrategy.QUALITY_FIRST, 0.025),
            ("tax", "calculation_request"): (RoutingStrategy.QUALITY_FIRST, 0.020),
            ("accounting", "document_analysis"): (RoutingStrategy.QUALITY_FIRST, 0.025),
            ("business", "strategic_advice"): (RoutingStrategy.QUALITY_FIRST, 0.025),
            # CCNL / balanced
            ("labor", "ccnl_query"): (RoutingStrategy.BALANCED, 0.018),
            ("labor", "calculation_request"): (RoutingStrategy.BALANCED, 0.020),
            ("tax", "strategic_advice"): (RoutingStrategy.BALANCED, 0.015),
            ("labor", "compliance_check"): (RoutingStrategy.BALANCED, 0.015),
            ("business", "document_generation"): (RoutingStrategy.BALANCED, 0.020),
            ("accounting", "compliance_check"): (RoutingStrategy.BALANCED, 0.015),
            # Cost-optimized simple info (tests expect 0.015)
            ("tax", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("legal", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("labor", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("business", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.015),
            ("accounting", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.015),
        }

        key = (classification.domain.value, classification.action.value)
        strategy, base_cost = strategy_map.get(key, (RoutingStrategy.BALANCED, 0.020))

        # Only cap if explicitly configured (non-default); otherwise leave mapping as-is
        global_cap = getattr(settings, "LLM_MAX_COST_EUR", None)
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

    def _convert_langchain_message_to_dict(self, msg) -> dict | None:
        """Convert LangChain message object to plain dict.

        LangGraph checkpointer stores messages as LangChain objects (AIMessage,
        HumanMessage, SystemMessage), but our code expects plain dicts with
        'role' and 'content'.

        DEV-007 FIX: System messages are NOW INCLUDED (not filtered).
        Filtering happens ONLY in __process_messages() for frontend display.
        This prevents Steps 45-47 from re-inserting system messages every turn,
        which was causing message index shift and attachment misalignment.
        """
        # Already a dict - pass through (including system role!)
        if isinstance(msg, dict):
            return msg

        # LangChain message object - convert to dict
        if hasattr(msg, "content") and hasattr(msg, "type"):
            # Handle all message types explicitly
            if msg.type == "system":
                role = "system"  # Include system messages for graph processing
            elif msg.type == "ai":
                role = "assistant"
            else:
                role = "user"
            return {"role": role, "content": msg.content}

        # Handle Pydantic Message objects with role attribute (not type)
        # DEV-007 FIX: System messages with 'role' attribute are now included.
        if hasattr(msg, "role") and hasattr(msg, "content"):
            role = getattr(msg, "role", "user")
            return {"role": role, "content": msg.content}

        # Unknown type - try to extract what we can
        if hasattr(msg, "content"):
            return {"role": "user", "content": str(msg.content)}

        # Last resort
        return {"role": "user", "content": str(msg)}

    async def _get_prior_state(self, session_id: str) -> tuple[list[dict], list]:
        """Load prior conversation messages and attachments from checkpointer.

        DEV-007 Issue 11e: This method enables conversation context continuity
        by loading prior state from the LangGraph checkpoint. Without this,
        each turn is treated as independent and follow-up questions fail.

        Args:
            session_id: The thread/session ID for checkpoint lookup

        Returns:
            Tuple of (prior_messages, prior_attachments) from checkpoint.
            Returns ([], []) if no prior state exists or on error.
        """
        if self._graph is None:
            return [], []

        try:
            config = {"configurable": {"thread_id": session_id}}
            state = await self._graph.aget_state(config)

            if state and state.values:
                raw_messages = state.values.get("messages", [])
                prior_attachments = state.values.get("attachments", [])

                # DEV-007 Issue 11e FIX: Convert LangChain message objects to dicts
                # The checkpointer stores AIMessage/HumanMessage objects, not plain dicts
                # DEV-007 FIX: Filter out None values (system messages) to prevent prompt leakage
                prior_messages = [
                    converted
                    for msg in raw_messages
                    if (converted := self._convert_langchain_message_to_dict(msg)) is not None
                ]

                # Log if any messages were filtered (system messages)
                filtered_count = len(raw_messages) - len(prior_messages)
                logger.info(
                    "prior_state_loaded",
                    session_id=session_id,
                    raw_message_count=len(raw_messages),
                    message_count=len(prior_messages),
                    filtered_system_messages=filtered_count,
                    attachment_count=len(prior_attachments),
                )
                return prior_messages, prior_attachments
        except Exception as e:
            logger.warning(
                "failed_to_load_prior_state",
                session_id=session_id,
                error=str(e),
            )

        return [], []

    async def _get_system_prompt(
        self, messages: list[Message], classification: Optional["DomainActionClassification"]
    ) -> str:
        """Select the appropriate system prompt via RAG Step 41 orchestrator."""
        from app.orchestrators.prompting import step_41__select_prompt

        # Call the Step 41 orchestrator (thin orchestration pattern)
        result = await step_41__select_prompt(
            messages=messages,
            ctx={
                "classification": classification,
                "prompt_template_manager": self._prompt_template_manager,
                "request_id": getattr(self, "_current_request_id", "unknown"),
            },
        )

        # Extract the selected prompt from orchestrator result
        return result.get("selected_prompt", SYSTEM_PROMPT)  # type: ignore[no-any-return]

    async def _prepare_messages_with_system_prompt(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        classification: Optional["DomainActionClassification"] = None,
    ) -> list[Message]:
        """Ensure system message presence (RAG STEP 45 — CheckSysMsg) with backward-compatible signature."""
        if messages is None:  # Defensive check for runtime safety
            messages = []  # type: ignore[unreachable]
        msgs = messages  # operate IN-PLACE

        # Resolve classification (fallback to agent state)
        resolved_class = (
            classification if classification is not None else getattr(self, "_current_classification", None)
        )

        # Resolve prompt if not provided
        if system_prompt is None:
            try:
                system_prompt = await self._get_system_prompt(msgs, resolved_class)
            except Exception:
                from app.core.prompts import SYSTEM_PROMPT as _SP

                system_prompt = _SP

        # Use RAG STEP 45 orchestrator for system message existence decision
        from app.orchestrators.prompting import step_45__check_sys_msg

        step_45_decision = step_45__check_sys_msg(
            messages=msgs, ctx={"classification": resolved_class, "system_prompt": system_prompt}
        )

        # Route based on Step 45 decision
        if step_45_decision["next_step"] == 47:
            # Route to Step 47 (InsertMsg)
            from app.orchestrators.prompting import step_47__insert_msg

            msgs = step_47__insert_msg(
                messages=msgs, ctx={"system_prompt": system_prompt, "classification": resolved_class}
            )
            return msgs

        elif step_45_decision["next_step"] == 46:
            # Route to Step 46 (ReplaceMsg)
            from app.orchestrators.prompting import step_46__replace_msg

            msgs = step_46__replace_msg(
                messages=msgs, ctx={"new_system_prompt": system_prompt, "classification": resolved_class}
            )
            return msgs

        else:
            # Keep existing system message (action == "keep")
            return msgs

    def _get_optimal_provider(self, messages: list[Message]) -> LLMProvider:
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
                    max_cost = getattr(settings, "LLM_MAX_COST_EUR", 0.020)

                preferred_provider = getattr(settings, "LLM_PREFERRED_PROVIDER", None)
                settings_max_cost = getattr(settings, "LLM_MAX_COST_EUR", 0.020)

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
                next_step, decision = strategy_to_next_step.get(
                    strategy, ("BalanceProvider", "routing_fallback_to_balanced")
                )

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
                    classification_confidence=(
                        self._current_classification.confidence if self._current_classification else None
                    ),
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
                    routing_strategy=getattr(strategy, "value", None) if "strategy" in locals() else None,
                    processing_stage="error",
                )

                # RAG STEP 50 — Error during routing decision
                rag_step_log(
                    step=50,
                    step_id="RAG.platform.routing.strategy",
                    node_label="StrategyType",
                    decision="routing_decision_failed",
                    error=str(e),
                    routing_strategy=getattr(strategy, "value", None) if "strategy" in locals() else None,
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

    async def _get_connection_pool(self) -> AsyncConnectionPool | None:
        """Get a PostgreSQL connection pool using environment-specific settings.

        Returns:
            Optional[AsyncConnectionPool]: A connection pool for PostgreSQL database, or None if connection fails in production.
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
            if hasattr(msg, "role") and hasattr(msg, "content"):
                conversation_messages.append(Message(role=msg.role, content=msg.content))
            else:
                # Handle legacy message format
                conversation_messages.append(Message(role="user", content=str(msg)))

        # Classify user query
        self._current_classification = await self._classify_user_query(conversation_messages)

        # Get domain-specific system prompt or default
        system_prompt = await self._get_system_prompt(conversation_messages, self._current_classification)

        # Use RAG STEP 45 to prepare messages with system prompt
        conversation_messages = await self._prepare_messages_with_system_prompt(
            conversation_messages, system_prompt, self._current_classification
        )

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

                    ai_message = AIMessage(content=response.content, tool_calls=response.tool_calls)
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
                    provider=(
                        getattr(self._current_provider, "provider_type", {}).get("value", "unknown")
                        if self._current_provider
                        else "unknown"
                    ),
                    environment=settings.ENVIRONMENT.value,
                )
                llm_calls_num += 1

                # In production, we might want to fall back to a different provider/model
                if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                    logger.warning("attempting_fallback_provider", environment=settings.ENVIRONMENT.value)
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
    async def _tool_call(self, state: GraphState) -> dict[str, list[ToolMessage]]:
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
    def _route_strategy_type(state: dict[str, Any]) -> str:
        """Route from StrategyType node based on strategy decision."""
        strategy_type = state.get("decisions", {}).get("strategy_type", "PRIMARY")
        return strategy_type  # type: ignore[no-any-return]

    @staticmethod
    def _route_cost_check(state: dict[str, Any]) -> str:
        """Route from CostCheck node based on budget approval."""
        cost_ok = state.get("decisions", {}).get("cost_ok", True)
        return "approved" if cost_ok else "too_expensive"

    # Reuse existing routing functions with new names for clarity
    @staticmethod
    def _route_cache_hit(state: dict[str, Any]) -> str:
        """Route from CacheHit node based on cache status."""
        if state.get("cache_hit", False):
            return "hit"
        else:
            return "miss"

    @staticmethod
    def _route_llm_success(state: dict[str, Any]) -> str:
        """Route from LLMSuccess node."""
        if state.get("llm_success", True):
            return "success"
        else:
            return "retry"

    @staticmethod
    def _route_tool_check(state: dict[str, Any]) -> str:
        """Route from ToolCheck node."""
        if state.get("tool_calls") or state.get("tools", {}).get("requested", False):
            return "has_tools"
        else:
            return "no_tools"

    @staticmethod
    def _route_tool_type(state: dict[str, Any]) -> str:
        """Route from ToolType node based on tool type."""
        tool_type = state.get("tools", {}).get("type", "kb")
        mapping = {"kb": "kb", "ccnl": "ccnl", "doc": "doc", "faq": "faq"}
        return mapping.get(tool_type, "kb")

    @staticmethod
    def _route_prod_check(state: dict[str, Any]) -> str:
        """Route from ProdCheck node."""
        if state.get("llm", {}).get("should_failover", False):
            return "failover"
        else:
            return "retry_same"

    @staticmethod
    def _route_from_valid_check(state: dict[str, Any]) -> str:
        """Route from ValidCheck node based on request validity."""
        # Check in both root and decisions dict
        decisions = state.get("decisions", {})
        request_valid = state.get("request_valid") or decisions.get("request_valid")

        # Default to False for safety - invalid until proven valid
        if request_valid is None:
            request_valid = False

        branch = "GDPRLog" if request_valid else "Error400"
        logger.debug(
            "routing_decision",
            from_node="ValidCheck",
            to_node=branch,
            condition="request_valid",
            value=request_valid,
            reason=f"Request validation {'passed' if request_valid else 'failed'}",
        )

        if request_valid:
            return "GDPRLog"  # Valid request continues to GDPR logging (Step 4)
        else:
            return "Error400"  # Invalid request goes to Error400 (Step 5)

    @staticmethod
    def _route_from_privacy_check(_state: dict[str, Any]) -> str:
        """Route from PrivacyCheck node - always goes to PIICheck."""
        logger.debug(
            "routing_decision",
            from_node="PrivacyCheck",
            to_node="PIICheck",
            condition="always",
            value=True,
            reason="Privacy check complete, proceeding to PII detection",
        )
        return "PIICheck"

    @staticmethod
    def _route_from_pii_check(_state: dict[str, Any]) -> str:
        """Route from PIICheck node - goes to cache spine."""
        logger.debug(
            "routing_decision",
            from_node="PIICheck",
            to_node="CheckCache",
            condition="always",
            value=True,
            reason="PII check complete, proceeding to cache layer",
        )
        return "CheckCache"

    @staticmethod
    def _route_from_cache_hit(state: dict[str, Any]) -> str:
        """Route from CacheHit node based on cache status."""
        cache_hit = state.get("cache_hit", False)
        branch = "End" if cache_hit else "LLMCall"
        logger.debug(
            "routing_decision",
            from_node="CacheHit",
            to_node=branch,
            condition="cache_hit",
            value=cache_hit,
            reason=f"Cache {'hit' if cache_hit else 'miss'}, {'returning cached response' if cache_hit else 'calling LLM'}",
        )
        if cache_hit:
            return "End"
        else:
            return "LLMCall"

    @staticmethod
    def _route_from_llm_success(_state: dict[str, Any]) -> str:
        """Route from LLMSuccess node - simplified for Phase 1A."""
        logger.debug(
            "routing_decision",
            from_node="LLMSuccess",
            to_node="End",
            condition="always",
            value=True,
            reason="LLM call successful, completing workflow (Phase 1A simplified)",
        )
        return "End"

    # Phase 4 routing functions
    @staticmethod
    def _route_from_cache_hit_phase4(state: dict[str, Any]) -> str:
        """Route from CacheHit node in Phase 4 based on cache status."""
        cache_hit = state.get("cache_hit_decision", False)
        branch = "ReturnCached" if cache_hit else "LLMCall"
        logger.debug(
            "routing_decision",
            from_node="CacheHit",
            to_node=branch,
            condition="cache_hit_decision",
            value=cache_hit,
            reason=f"Cache {'hit' if cache_hit else 'miss'}, {'returning cached' if cache_hit else 'proceeding to LLM'}",
        )
        if cache_hit:
            return "ReturnCached"
        else:
            return "LLMCall"

    @staticmethod
    def _route_from_llm_success_phase4(state: dict[str, Any]) -> str:
        """Route from LLMSuccess node in Phase 4."""
        llm_success = state.get("llm_success_decision", True)
        branch = "CacheResponse" if llm_success else "RetryCheck"
        logger.debug(
            "routing_decision",
            from_node="LLMSuccess",
            to_node=branch,
            condition="llm_success_decision",
            value=llm_success,
            reason=f"LLM {'succeeded' if llm_success else 'failed'}, {'caching response' if llm_success else 'checking retry options'}",
        )
        if llm_success:
            return "CacheResponse"
        else:
            return "RetryCheck"

    @staticmethod
    def _route_from_retry_check(state: dict[str, Any]) -> str:
        """Route from RetryCheck node."""
        retry_allowed = state.get("llm", {}).get("retry_allowed", False)
        branch = "ProdCheck" if retry_allowed else "End"
        logger.debug(
            "routing_decision",
            from_node="RetryCheck",
            to_node=branch,
            condition="retry_allowed",
            value=retry_allowed,
            reason=f"Retry {'allowed' if retry_allowed else 'not allowed'}, {'checking production status' if retry_allowed else 'ending workflow'}",
        )
        if retry_allowed:
            return "ProdCheck"
        else:
            return "End"

    @staticmethod
    def _route_from_prod_check(state: dict[str, Any]) -> str:
        """Route from ProdCheck node."""
        should_failover = state.get("llm", {}).get("should_failover", False)
        branch = "FailoverProvider" if should_failover else "RetrySame"
        logger.debug(
            "routing_decision",
            from_node="ProdCheck",
            to_node=branch,
            condition="should_failover",
            value=should_failover,
            reason=f"Failover {'required' if should_failover else 'not required'}, {'switching to failover provider' if should_failover else 'retrying with same provider'}",
        )
        if should_failover:
            return "FailoverProvider"
        else:
            return "RetrySame"

    @staticmethod
    def _route_from_tool_check(state: dict[str, Any]) -> str:
        """Route from ToolCheck node."""
        tools_requested = state.get("tools", {}).get("requested", False)
        branch = "ToolType" if tools_requested else "StreamCheck"
        logger.debug(
            "routing_decision",
            from_node="ToolCheck",
            to_node=branch,
            condition="tools.requested",
            value=tools_requested,
            reason=f"Tools {'requested' if tools_requested else 'not requested'}, {'routing to tool type' if tools_requested else 'routing to stream check'}",
        )
        if tools_requested:
            return "ToolType"
        else:
            return "StreamCheck"

    @staticmethod
    def _route_from_tool_type(state: dict[str, Any]) -> str:
        """Route from ToolType node based on tool type."""
        tool_type = state.get("tools", {}).get("type", "kb")
        mapping = {"kb": "KBTool", "ccnl": "CCNLTool", "doc": "DocIngestTool", "faq": "FAQTool"}
        branch = mapping.get(tool_type, "KBTool")
        logger.debug(
            "routing_decision",
            from_node="ToolType",
            to_node=branch,
            condition="tools.type",
            value=tool_type,
            reason=f"Tool type is '{tool_type}', routing to {branch}",
        )
        return branch

    # Unified graph routing functions
    @staticmethod
    def _route_from_privacy_check_unified(state: dict[str, Any]) -> str:
        """Route from PrivacyCheck in unified graph."""
        anonymize_enabled = state.get("privacy", {}).get("anonymize_enabled", False)
        branch = "AnonymizeText" if anonymize_enabled else "InitAgent"
        logger.debug(
            "routing_decision",
            from_node="PrivacyCheck",
            to_node=branch,
            condition="privacy.anonymize_enabled",
            value=anonymize_enabled,
            reason=f"Anonymization {'enabled' if anonymize_enabled else 'disabled'}, {'anonymizing text' if anonymize_enabled else 'proceeding to agent initialization'}",
        )
        if anonymize_enabled:
            return "AnonymizeText"
        else:
            return "InitAgent"

    @staticmethod
    def _route_from_pii_check_unified(state: dict[str, Any]) -> str:
        """Route from PIICheck in unified graph."""
        pii_detected = state.get("privacy", {}).get("pii_detected", False)
        branch = "LogPII" if pii_detected else "InitAgent"
        logger.debug(
            "routing_decision",
            from_node="PIICheck",
            to_node=branch,
            condition="privacy.pii_detected",
            value=pii_detected,
            reason=f"PII {'detected' if pii_detected else 'not detected'}, {'logging PII' if pii_detected else 'proceeding to agent initialization'}",
        )
        if pii_detected:
            return "LogPII"
        else:
            return "InitAgent"

    @staticmethod
    def _route_from_golden_fast_gate(state: dict[str, Any]) -> str:
        """Route from GoldenFastGate - check if golden lookup is eligible."""
        eligible = state.get("golden", {}).get("eligible", False)
        branch = "GoldenLookup" if eligible else "ClassifyDomain"
        logger.debug(
            "routing_decision",
            from_node="GoldenFastGate",
            to_node=branch,
            condition="golden.eligible",
            value=eligible,
            reason=f"Golden lookup {'eligible' if eligible else 'not eligible'}, {'looking up golden answer' if eligible else 'proceeding to domain classification'}",
        )
        if eligible:
            return "GoldenLookup"
        else:
            return "ClassifyDomain"

    @staticmethod
    def _route_from_golden_hit(state: dict[str, Any]) -> str:
        """Route from GoldenHit - check if high confidence match found."""
        golden_hit = state.get("golden", {}).get("hit", False)
        branch = "KBContextCheck" if golden_hit else "ClassifyDomain"
        logger.debug(
            "routing_decision",
            from_node="GoldenHit",
            to_node=branch,
            condition="golden.hit",
            value=golden_hit,
            reason=f"Golden answer {'found' if golden_hit else 'not found'}, {'checking KB context' if golden_hit else 'proceeding to domain classification'}",
        )
        if golden_hit:
            return "KBContextCheck"
        else:
            return "ClassifyDomain"

    @staticmethod
    def _route_from_kb_delta(state: dict[str, Any]) -> str:
        """Route from KBDelta - check if KB is newer than golden."""
        kb_newer = state.get("golden", {}).get("kb_newer", False)
        branch = "ClassifyDomain" if kb_newer else "ServeGolden"
        logger.debug(
            "routing_decision",
            from_node="KBDelta",
            to_node=branch,
            condition="golden.kb_newer",
            value=kb_newer,
            reason=f"KB {'newer than golden' if kb_newer else 'not newer'}, {'need fresh LLM response with KB context' if kb_newer else 'golden answer still fresh'}",
        )
        if kb_newer:
            return "ClassifyDomain"  # Need fresh LLM response with KB context
        else:
            return "ServeGolden"  # Golden answer is still fresh

    @staticmethod
    def _route_from_confidence_check(state: dict[str, Any]) -> str:
        """Route from ConfidenceCheck - check if classification confidence is sufficient."""
        confidence_sufficient = state.get("classification", {}).get("confidence_sufficient", False)
        branch = "TrackMetrics" if confidence_sufficient else "LLMFallback"
        logger.debug(
            "routing_decision",
            from_node="ConfidenceCheck",
            to_node=branch,
            condition="classification.confidence_sufficient",
            value=confidence_sufficient,
            reason=f"Classification confidence {'sufficient' if confidence_sufficient else 'insufficient'}, {'tracking metrics' if confidence_sufficient else 'using LLM fallback'}",
        )
        if confidence_sufficient:
            return "TrackMetrics"
        else:
            return "LLMFallback"

    @staticmethod
    def _route_from_llm_better(state: dict[str, Any]) -> str:
        """Route from LLMBetter - check if LLM classification is better than rule-based."""
        llm_is_better = state.get("classification", {}).get("llm_is_better", False)
        branch = "UseLLM" if llm_is_better else "UseRuleBased"
        logger.debug(
            "routing_decision",
            from_node="LLMBetter",
            to_node=branch,
            condition="classification.llm_is_better",
            value=llm_is_better,
            reason=f"LLM classification {'better' if llm_is_better else 'not better'} than rule-based, {'using LLM' if llm_is_better else 'using rule-based'}",
        )
        if llm_is_better:
            return "UseLLM"
        else:
            return "UseRuleBased"

    @staticmethod
    def _route_from_class_confidence(state: dict[str, Any]) -> str:
        """Route from ClassConfidence - check if classification confidence is sufficient for domain prompt."""
        confidence_check = state.get("confidence_check", {})
        confidence_sufficient = confidence_check.get("confidence_sufficient", False)
        branch = "DomainPrompt" if confidence_sufficient else "DefaultSysPrompt"
        logger.debug(
            "routing_decision",
            from_node="ClassConfidence",
            to_node=branch,
            condition="confidence_check.confidence_sufficient",
            value=confidence_sufficient,
            reason=f"Classification confidence {'sufficient' if confidence_sufficient else 'insufficient'}, {'using domain-specific prompt' if confidence_sufficient else 'using default prompt'}",
        )
        if confidence_sufficient:
            return "DomainPrompt"
        else:
            return "DefaultSysPrompt"

    @staticmethod
    def _route_from_check_sys_msg(state: dict[str, Any]) -> str:
        """Route from CheckSysMsg - check if system message already exists."""
        sys_msg_exists = state.get("sys_msg_exists", False)
        branch = "ReplaceMsg" if sys_msg_exists else "InsertMsg"
        logger.debug(
            "routing_decision",
            from_node="CheckSysMsg",
            to_node=branch,
            condition="sys_msg_exists",
            value=sys_msg_exists,
            reason=f"System message {'exists' if sys_msg_exists else 'does not exist'}, {'replacing' if sys_msg_exists else 'inserting'} message",
        )
        if sys_msg_exists:
            return "ReplaceMsg"
        else:
            return "InsertMsg"

    @staticmethod
    def _route_from_strategy_type(state: dict[str, Any]) -> str:
        """Route from StrategyType based on routing strategy."""
        strategy = state.get("provider", {}).get("routing_strategy", "PRIMARY")
        mapping = {
            "COST_OPTIMIZED": "CheapProvider",
            "QUALITY_FIRST": "BestProvider",
            "BALANCED": "BalanceProvider",
            "PRIMARY": "PrimaryProvider",
            "FAILOVER": "PrimaryProvider",
        }
        branch = mapping.get(strategy, "PrimaryProvider")
        logger.debug(
            "routing_decision",
            from_node="StrategyType",
            to_node=branch,
            condition="provider.routing_strategy",
            value=strategy,
            reason=f"Routing strategy is '{strategy}', selecting {branch}",
        )
        return branch

    @staticmethod
    def _route_from_cost_check(state: dict[str, Any]) -> str:
        """Route from CostCheck - check if cost within budget."""
        cost_ok = state.get("provider", {}).get("cost_ok", True)
        branch = "CreateProvider" if cost_ok else "CheaperProvider"
        logger.debug(
            "routing_decision",
            from_node="CostCheck",
            to_node=branch,
            condition="provider.cost_ok",
            value=cost_ok,
            reason=f"Cost {'within budget' if cost_ok else 'exceeds budget'}, {'creating provider' if cost_ok else 'finding cheaper provider'}",
        )
        if cost_ok:
            return "CreateProvider"
        else:
            return "CheaperProvider"

    @staticmethod
    def _route_from_cache_hit_unified(state: dict[str, Any]) -> str:
        """Route from CacheHit in unified graph."""
        cache_hit = state.get("cache", {}).get("hit", False)
        branch = "ReturnCached" if cache_hit else "LLMCall"
        logger.debug(
            "routing_decision",
            from_node="CacheHit",
            to_node=branch,
            condition="cache.hit",
            value=cache_hit,
            reason=f"Cache {'hit' if cache_hit else 'miss'}, {'returning cached response' if cache_hit else 'calling LLM'}",
        )
        if cache_hit:
            return "ReturnCached"
        else:
            return "LLMCall"

    @staticmethod
    def _route_from_llm_success_unified(state: dict[str, Any]) -> str:
        """Route from LLMSuccess in unified graph."""
        llm = state.get("llm", {})
        llm_success = llm.get("success", True)

        # Check for non-retryable errors FIRST
        if not llm_success:
            error_type = llm.get("error_type")
            error_msg = str(llm.get("error", "")).lower()

            # Check if error is non-retryable
            is_non_retryable = (
                error_type in ("TypeError", "ValueError", "AttributeError")
                or "multiple values for keyword argument" in error_msg
            )

            if is_non_retryable:
                logger.error(
                    "routing_decision_non_retryable",
                    from_node="LLMSuccess",
                    to_node="End",
                    error_type=error_type,
                    reason="Non-retryable error detected, terminating workflow",
                )
                return "End"  # Skip retry, go straight to end

        # Normal routing
        branch = "CacheResponse" if llm_success else "RetryCheck"
        logger.debug(
            "routing_decision",
            from_node="LLMSuccess",
            to_node=branch,
            condition="llm.success",
            value=llm_success,
            reason=f"LLM {'succeeded' if llm_success else 'failed'}, {'caching response' if llm_success else 'checking retry options'}",
        )
        return branch

    @staticmethod
    def _route_from_stream_check(state: dict[str, Any]) -> str:
        """Route from StreamCheck - check if streaming requested."""
        streaming_requested = state.get("streaming", {}).get("requested", False)
        branch = "StreamSetup" if streaming_requested else "CollectMetrics"
        logger.debug(
            "routing_decision",
            from_node="StreamCheck",
            to_node=branch,
            condition="streaming.requested",
            value=streaming_requested,
            reason=f"Streaming {'requested' if streaming_requested else 'not requested'}, {'setting up stream' if streaming_requested else 'collecting metrics'}",
        )
        if streaming_requested:
            return "StreamSetup"
        else:
            return "CollectMetrics"

    async def create_graph_phase1a(self) -> CompiledStateGraph | None:
        """Create Phase 1A graph with explicit RAG nodes.

        Returns:
            Optional[CompiledStateGraph]: The Phase 1A graph or None if init fails
        """
        try:
            graph_builder = StateGraph(RAGState)

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
                "ValidCheck", self._route_from_valid_check, {"PrivacyCheck": "PrivacyCheck", "End": "End"}
            )
            graph_builder.add_conditional_edges(
                "PrivacyCheck", self._route_from_privacy_check, {"PIICheck": "PIICheck"}
            )
            graph_builder.add_conditional_edges("PIICheck", self._route_from_pii_check, {"CheckCache": "CheckCache"})
            graph_builder.add_edge("CheckCache", "CacheHit")
            graph_builder.add_conditional_edges(
                "CacheHit", self._route_from_cache_hit, {"End": "End", "LLMCall": "LLMCall"}
            )
            graph_builder.add_edge("LLMCall", "LLMSuccess")
            graph_builder.add_conditional_edges("LLMSuccess", self._route_from_llm_success, {"End": "End"})

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
                checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent Phase1A ({settings.ENVIRONMENT.value})"
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

    async def create_graph_phase4_lane(self) -> CompiledStateGraph | None:
        """Create Phase 4 graph with Cache → LLM → Tools lane.

        Returns:
            Optional[CompiledStateGraph]: The Phase 4 graph or None if init fails
        """
        try:
            graph_builder = StateGraph(RAGState)

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
                "ValidCheck", self._route_from_valid_check, {"PrivacyCheck": "PrivacyCheck", "End": "End"}
            )
            graph_builder.add_conditional_edges(
                "PrivacyCheck", self._route_from_privacy_check, {"PIICheck": "PIICheck"}
            )
            graph_builder.add_conditional_edges("PIICheck", self._route_from_pii_check, {"CheckCache": "CheckCache"})

            # Phase 4 cache lane edges
            graph_builder.add_edge("CheckCache", "CacheHit")
            track_edge(59, 62)  # CheckCache → CacheHit

            graph_builder.add_conditional_edges(
                "CacheHit", self._route_from_cache_hit_phase4, {"ReturnCached": "ReturnCached", "LLMCall": "LLMCall"}
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
                {"CacheResponse": "CacheResponse", "RetryCheck": "RetryCheck"},
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
                "RetryCheck", self._route_from_retry_check, {"ProdCheck": "ProdCheck", "End": "End"}
            )
            track_edge(69, 70)  # RetryCheck → ProdCheck (retry allowed)

            graph_builder.add_conditional_edges(
                "ProdCheck",
                self._route_from_prod_check,
                {"FailoverProvider": "FailoverProvider", "RetrySame": "RetrySame"},
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
                "ToolCheck", self._route_from_tool_check, {"ToolType": "ToolType", "End": "End"}
            )
            track_edge(75, 79)  # ToolCheck → ToolType (tools needed)

            graph_builder.add_conditional_edges(
                "ToolType",
                self._route_from_tool_type,
                {"KBTool": "KBTool", "CCNLTool": "CCNLTool", "DocIngestTool": "DocIngestTool", "FAQTool": "FAQTool"},
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
                checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent Phase4 ({settings.ENVIRONMENT.value})"
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

    async def create_graph_provider_lane(self) -> CompiledStateGraph | None:
        """Create Phase 5 graph with Provider Governance Lane.

        Implements: 48 SelectProvider → 49 RouteStrategy → 50 StrategyType → (51/52/53/54) → 55 EstimateCost → 56 CostCheck → (57 CreateProvider | 58 CheaperProvider)

        Returns:
            Optional[CompiledStateGraph]: The Phase 5 graph or None if init fails
        """
        try:
            graph_builder = StateGraph(RAGState)

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
                    "PRIMARY": "PrimaryProvider",
                },
            )

            # All strategy providers go to cost estimation
            graph_builder.add_edge("CheapProvider", "EstimateCost")
            graph_builder.add_edge("BestProvider", "EstimateCost")
            graph_builder.add_edge("BalanceProvider", "EstimateCost")
            graph_builder.add_edge("PrimaryProvider", "EstimateCost")

            # Cost check conditional routing
            graph_builder.add_edge("EstimateCost", "CostCheck")
            graph_builder.add_conditional_edges(
                "CostCheck", self._route_cost_check, {"approved": "CreateProvider", "too_expensive": "CheaperProvider"}
            )

            # Cheaper provider loops back to estimate cost
            graph_builder.add_edge("CheaperProvider", "EstimateCost")

            # Provider created, continue to cache lane
            graph_builder.add_edge("CreateProvider", "CheckCache")

            # Phase 4 Cache → LLM → Tools edges (reusing existing logic)
            graph_builder.add_edge("CheckCache", "CacheHit")
            graph_builder.add_conditional_edges(
                "CacheHit", self._route_cache_hit, {"hit": "ReturnCached", "miss": "LLMCall"}
            )

            graph_builder.add_edge("LLMCall", "LLMSuccess")
            graph_builder.add_conditional_edges(
                "LLMSuccess", self._route_llm_success, {"success": "CacheResponse", "retry": "RetryCheck"}
            )

            graph_builder.add_edge("CacheResponse", "TrackUsage")
            graph_builder.add_edge("TrackUsage", "ToolCheck")
            graph_builder.add_conditional_edges(
                "ToolCheck", self._route_tool_check, {"has_tools": "ToolType", "no_tools": "End"}
            )

            graph_builder.add_conditional_edges(
                "ToolType",
                self._route_tool_type,
                {"kb": "KBTool", "ccnl": "CCNLTool", "doc": "DocIngestTool", "faq": "FAQTool"},
            )

            # All tools go to results aggregation
            graph_builder.add_edge("KBTool", "ToolResults")
            graph_builder.add_edge("CCNLTool", "ToolResults")
            graph_builder.add_edge("DocIngestTool", "ToolResults")
            graph_builder.add_edge("FAQTool", "ToolResults")

            # Retry logic
            graph_builder.add_edge("RetryCheck", "ProdCheck")
            graph_builder.add_conditional_edges(
                "ProdCheck", self._route_prod_check, {"failover": "FailoverProvider", "retry_same": "RetrySame"}
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

    async def create_graph_phase7_streaming(self) -> CompiledStateGraph | None:
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
                lambda state: (
                    "StreamSetup" if state.get("streaming", {}).get("requested", False) else "CollectMetrics"
                ),
                {"StreamSetup": "StreamSetup", "CollectMetrics": "CollectMetrics"},
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
                name=f"{settings.PROJECT_NAME} Agent Phase7 Streaming ({settings.ENVIRONMENT.value})",
            )

            logger.info(
                "phase7_streaming_graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent Phase7 Streaming",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
            )

            return compiled_graph

        except Exception as e:
            logger.error(
                "phase7_streaming_graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value
            )
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_phase7_streaming_graph")
                return None
            raise e

    async def create_graph_unified(self) -> CompiledStateGraph | None:
        """Create unified graph connecting all 8 lanes.

        This implements the full RAG flow as specified in pratikoai_rag_hybrid.mmd diagram.
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
            graph_builder = StateGraph(RAGState)

            # ========== Add all nodes from all lanes ==========

            # Lane 1: Request/Privacy nodes
            graph_builder.add_node("ValidateRequest", node_step_1)
            graph_builder.add_node("ValidCheck", node_step_3)
            graph_builder.add_node("GDPRLog", node_step_4)
            graph_builder.add_node("Error400", node_step_5)
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
            graph_builder.add_node("CalcScores", node_step_32)
            graph_builder.add_node("ConfidenceCheck", node_step_33)
            graph_builder.add_node("TrackMetrics", node_step_34)
            graph_builder.add_node("LLMFallback", node_step_35)
            graph_builder.add_node("LLMBetter", node_step_36)
            graph_builder.add_node("UseLLM", node_step_37)
            graph_builder.add_node("UseRuleBased", node_step_38)
            graph_builder.add_node("KBPreFetch", node_step_39)
            graph_builder.add_node("BuildContext", node_step_40)
            graph_builder.add_node("SelectPrompt", node_step_41)
            graph_builder.add_node("ClassConfidence", node_step_42)
            graph_builder.add_node("DomainPrompt", node_step_43)
            graph_builder.add_node("DefaultSysPrompt", node_step_44)
            graph_builder.add_node("CheckSysMsg", node_step_45)
            graph_builder.add_node("ReplaceMsg", node_step_46)
            graph_builder.add_node("InsertMsg", node_step_47)

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
            # NOTE: Validation (Steps 1-7) happens in chatbot.py BEFORE entering graph
            # Graph starts at Step 8 (InitAgent) as per RAG architecture
            graph_builder.set_entry_point("InitAgent")

            # Keep ValidateRequest node for potential future use, but not in main flow
            graph_builder.add_edge("ValidateRequest", "ValidCheck")
            graph_builder.add_conditional_edges(
                "ValidCheck",
                self._route_from_valid_check,
                {"GDPRLog": "GDPRLog", "Error400": "Error400", "End": "End"},
            )
            graph_builder.add_edge("GDPRLog", "PrivacyCheck")
            graph_builder.add_edge("Error400", "End")  # Terminal error node
            graph_builder.add_conditional_edges(
                "PrivacyCheck",
                self._route_from_privacy_check_unified,
                {"AnonymizeText": "AnonymizeText", "InitAgent": "InitAgent"},
            )
            graph_builder.add_edge("AnonymizeText", "PIICheck")
            graph_builder.add_conditional_edges(
                "PIICheck", self._route_from_pii_check_unified, {"LogPII": "LogPII", "InitAgent": "InitAgent"}
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
                {"GoldenLookup": "GoldenLookup", "ClassifyDomain": "ClassifyDomain"},
            )
            graph_builder.add_edge("GoldenLookup", "GoldenHit")
            graph_builder.add_conditional_edges(
                "GoldenHit",
                self._route_from_golden_hit,
                {"KBContextCheck": "KBContextCheck", "ClassifyDomain": "ClassifyDomain"},
            )
            graph_builder.add_edge("KBContextCheck", "KBDelta")
            graph_builder.add_conditional_edges(
                "KBDelta",
                self._route_from_kb_delta,
                {"ServeGolden": "ServeGolden", "ClassifyDomain": "ClassifyDomain"},
            )
            graph_builder.add_edge("ServeGolden", "ReturnComplete")
            graph_builder.add_edge("ReturnComplete", "CollectMetrics")

            # ========== Wire Lane 4: Classification ==========
            # Wire classification flow with internal steps
            graph_builder.add_edge("ClassifyDomain", "CalcScores")
            graph_builder.add_edge("CalcScores", "ConfidenceCheck")

            # ConfidenceCheck decision: sufficient confidence → TrackMetrics, else → LLMFallback
            graph_builder.add_conditional_edges(
                "ConfidenceCheck",
                self._route_from_confidence_check,
                {"TrackMetrics": "TrackMetrics", "LLMFallback": "LLMFallback"},
            )

            # LLMFallback path
            graph_builder.add_edge("LLMFallback", "LLMBetter")

            # LLMBetter decision: LLM better → UseLLM, else → UseRuleBased
            graph_builder.add_conditional_edges(
                "LLMBetter", self._route_from_llm_better, {"UseLLM": "UseLLM", "UseRuleBased": "UseRuleBased"}
            )

            # Both paths converge at TrackMetrics
            graph_builder.add_edge("UseLLM", "TrackMetrics")
            graph_builder.add_edge("UseRuleBased", "TrackMetrics")

            # Continue to KB prefetch and context building
            graph_builder.add_edge("TrackMetrics", "KBPreFetch")
            graph_builder.add_edge("KBPreFetch", "BuildContext")
            graph_builder.add_edge("BuildContext", "SelectPrompt")
            graph_builder.add_edge("SelectPrompt", "ClassConfidence")

            # ========== Wire Lane 4→5: Classification to Prompt Selection ==========
            # ClassConfidence decision: confidence sufficient → DomainPrompt, else → DefaultSysPrompt
            graph_builder.add_conditional_edges(
                "ClassConfidence",
                self._route_from_class_confidence,
                {"DomainPrompt": "DomainPrompt", "DefaultSysPrompt": "DefaultSysPrompt"},
            )

            # Both prompt paths converge at CheckSysMsg
            graph_builder.add_edge("DomainPrompt", "CheckSysMsg")
            graph_builder.add_edge("DefaultSysPrompt", "CheckSysMsg")

            # CheckSysMsg decision: exists → ReplaceMsg, else → InsertMsg
            graph_builder.add_conditional_edges(
                "CheckSysMsg", self._route_from_check_sys_msg, {"ReplaceMsg": "ReplaceMsg", "InsertMsg": "InsertMsg"}
            )

            # Both message paths converge at SelectProvider
            graph_builder.add_edge("ReplaceMsg", "SelectProvider")
            graph_builder.add_edge("InsertMsg", "SelectProvider")

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
                    "PrimaryProvider": "PrimaryProvider",
                },
            )
            graph_builder.add_edge("CheapProvider", "EstimateCost")
            graph_builder.add_edge("BestProvider", "EstimateCost")
            graph_builder.add_edge("BalanceProvider", "EstimateCost")
            graph_builder.add_edge("PrimaryProvider", "EstimateCost")
            graph_builder.add_edge("EstimateCost", "CostCheck")
            graph_builder.add_conditional_edges(
                "CostCheck",
                self._route_from_cost_check,
                {"CreateProvider": "CreateProvider", "CheaperProvider": "CheaperProvider"},
            )
            graph_builder.add_edge("CreateProvider", "CheckCache")
            graph_builder.add_edge("CheaperProvider", "EstimateCost")  # Loop back

            # ========== Wire Lane 7: Cache/LLM/Tools ==========
            graph_builder.add_edge("CheckCache", "CacheHit")
            graph_builder.add_conditional_edges(
                "CacheHit", self._route_from_cache_hit_unified, {"ReturnCached": "ReturnCached", "LLMCall": "LLMCall"}
            )
            graph_builder.add_edge("ReturnCached", "StreamCheck")

            graph_builder.add_edge("LLMCall", "LLMSuccess")
            graph_builder.add_conditional_edges(
                "LLMSuccess",
                self._route_from_llm_success_unified,
                {"CacheResponse": "CacheResponse", "RetryCheck": "RetryCheck", "End": "End"},
            )
            graph_builder.add_edge("CacheResponse", "TrackUsage")
            graph_builder.add_edge("TrackUsage", "ToolCheck")

            # Retry path
            graph_builder.add_conditional_edges(
                "RetryCheck", self._route_from_retry_check, {"ProdCheck": "ProdCheck", "End": "End"}
            )
            graph_builder.add_conditional_edges(
                "ProdCheck",
                self._route_from_prod_check,
                {"FailoverProvider": "FailoverProvider", "RetrySame": "RetrySame"},
            )
            graph_builder.add_edge("FailoverProvider", "LLMCall")
            graph_builder.add_edge("RetrySame", "LLMCall")

            # Tools path
            graph_builder.add_conditional_edges(
                "ToolCheck", self._route_from_tool_check, {"ToolType": "ToolType", "StreamCheck": "StreamCheck"}
            )
            graph_builder.add_conditional_edges(
                "ToolType",
                self._route_from_tool_type,
                {"KBTool": "KBTool", "CCNLTool": "CCNLTool", "DocIngestTool": "DocIngestTool", "FAQTool": "FAQTool"},
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
                {"StreamSetup": "StreamSetup", "CollectMetrics": "CollectMetrics"},
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
                checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent Unified ({settings.ENVIRONMENT.value})"
            )

            logger.info(
                "unified_graph_created",
                graph_name=f"{settings.PROJECT_NAME} Agent Unified",
                environment=settings.ENVIRONMENT.value,
                has_checkpointer=checkpointer is not None,
                total_nodes=59,
            )

            return compiled_graph

        except Exception as e:
            logger.error("unified_graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                logger.warning("continuing_without_unified_graph")
                return None
            raise e

    async def create_graph(self) -> CompiledStateGraph | None:
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
        user_id: str | None = None,
        attachments: list[dict] | None = None,
    ) -> list[Message]:
        """Get a response from the LLM.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for Langfuse tracking.
            user_id (Optional[str]): The user ID for Langfuse tracking.
            attachments (list[dict] | None): Resolved file attachments for context (DEV-007).

        Returns:
            list[Message]: The response from the LLM.
        """
        # Store user and session info for tracking
        self._current_user_id = user_id
        self._current_session_id = session_id

        if self._graph is None:
            self._graph = await self.create_graph()
        # Type cast: LangGraph accepts dicts for config
        config: Any = {
            "configurable": {"thread_id": session_id},
            "callbacks": [CallbackHandler()],
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": settings.ENVIRONMENT.value,
                "debug": False,
            },
        }
        try:
            # Type cast: LangGraph accepts dicts matching the state schema
            input_state: Any = {
                "messages": dump_messages(messages),
                "session_id": session_id,
                "attachments": attachments or [],
            }
            response = await self._graph.ainvoke(input_state, config)  # type: ignore[union-attr]
            return self.__process_messages(response["messages"])
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            raise e
        finally:
            # Clean up tracking info
            self._current_user_id = None
            self._current_session_id = None

    @staticmethod
    def _needs_complex_workflow(classification: DomainActionClassification | None) -> bool:
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
            Action.CCNL_QUERY,  # Always needs CCNL database access
            Action.DOCUMENT_ANALYSIS,  # Might need document processing tools
            Action.CALCULATION_REQUEST,  # Might need calculation tools
            Action.COMPLIANCE_CHECK,  # Might need regulation lookup tools
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
        self,
        messages: list[Message],
        session_id: str,
        user_id: str | None = None,
        attachments: list[dict] | None = None,
    ) -> AsyncGenerator[str]:
        """Get a hybrid stream response using unified graph for pre-LLM steps.

        Phase 4 Implementation: Uses the unified graph to execute all steps (1-63)
        before the LLM call, then streams the LLM response (Step 64) directly.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.
            attachments (list[dict] | None): Resolved file attachments for context (DEV-007).

        Yields:
            str: Raw markdown chunks of the LLM response.
        """
        from app.observability.rag_logging import rag_step_log

        # Step 8: InitAgent - Entry into LangGraph workflow
        rag_step_log(
            step=8,
            step_id="RAG.langgraphagent.get.stream.response.initialize.workflow",
            node_label="InitAgent",
            processing_stage="entered",
            session_id=session_id,
            user_id=user_id,
            message_count=len(messages),
            method="get_stream_response",
            next_step=11,  # Next will be message conversion
        )

        logger.debug("get_stream_response_entry", session_id=session_id, user_id=user_id, message_count=len(messages))

        # Store user and session info for tracking
        self._current_user_id = user_id
        self._current_session_id = session_id

        # DEV-007 FIX: Invalidate conversation cache BEFORE processing new message
        # This ensures that after page refresh, the fresh checkpoint data is loaded
        # instead of stale cached data from before this message was processed
        await cache_service.invalidate_conversation(session_id)
        logger.debug(
            "conversation_cache_invalidated_for_new_message",
            session_id=session_id,
        )

        try:
            logger.debug("checking_graph_initialization", session_id=session_id)

            # Ensure unified graph is initialized
            if self._graph is None:
                logger.info("graph_is_none_calling_create_graph", session_id=session_id)
                self._graph = await self.create_graph()

            if self._graph is None:
                logger.error("unified_graph_not_available_fallback_to_direct", session_id=session_id)
                # Fallback to old direct streaming if graph unavailable
                self._current_classification = await self._classify_user_query(messages)
                async for chunk in self._stream_with_direct_llm(messages, session_id):
                    yield chunk
                return

            logger.debug("graph_initialized_successfully", session_id=session_id)

            # DEV-007 Issue 11e: Load prior conversation state for context continuity
            # This fixes follow-up questions failing for both regular queries AND document-based queries
            prior_messages, prior_attachments = await self._get_prior_state(session_id)

            # Build initial state for unified graph
            # Convert Message objects to dicts for graph compatibility
            current_message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]

            # DEV-007 Issue 11e + P0.10 FIX: Merge prior messages with current messages
            # This ensures the LLM has full conversation context for follow-up questions
            #
            # P0.10 FIX: The frontend sends ALL messages (including Turn 1's user+assistant).
            # Simply concatenating prior + current causes duplicates.
            # Instead, we must deduplicate by (role, content) tuple.

            # DEV-007 P0.11 DIAGNOSTIC: Log incoming messages for debugging
            prior_roles = [m.get("role") for m in prior_messages] if prior_messages else []
            current_roles = [m.get("role") for m in current_message_dicts]
            logger.info(
                "DEV007_P0.11_message_merge_inputs",
                session_id=session_id,
                prior_count=len(prior_messages) if prior_messages else 0,
                prior_roles=prior_roles,
                current_count=len(current_message_dicts),
                current_roles=current_roles,
            )

            if prior_messages:
                # Build set of (role, content) tuples from prior messages for deduplication
                prior_keys = {(m.get("role"), m.get("content")) for m in prior_messages}

                # Start with prior messages as base (they're from the checkpoint)
                merged_messages = list(prior_messages)

                # DEV-007 P0.12 FIX: Only add NEW USER messages from current
                # CRITICAL: The frontend may send assistant messages with slightly different
                # content (e.g., SSE streaming chunks vs final saved response).
                # We MUST NOT add assistant messages from frontend - only from checkpoint.
                # This prevents the duplicate assistant message bug on page refresh.
                new_messages_added = 0
                skipped_assistant = 0
                for msg in current_message_dicts:
                    role = msg.get("role")
                    # Skip assistant messages - checkpoint is the source of truth
                    if role == "assistant":
                        skipped_assistant += 1
                        continue
                    key = (role, msg.get("content"))
                    if key not in prior_keys:
                        merged_messages.append(msg)
                        prior_keys.add(key)  # Prevent duplicates within current_message_dicts
                        new_messages_added += 1

                merged_roles = [m.get("role") for m in merged_messages]
                logger.info(
                    "DEV007_P0.12_message_merge_result",
                    session_id=session_id,
                    prior_count=len(prior_messages),
                    current_count=len(current_message_dicts),
                    new_messages_added=new_messages_added,
                    skipped_assistant=skipped_assistant,
                    total_count=len(merged_messages),
                    merged_roles=merged_roles,
                )
            else:
                merged_messages = current_message_dicts
                logger.info(
                    "DEV007_P0.11_no_prior_messages",
                    session_id=session_id,
                    using_current_count=len(current_message_dicts),
                    current_roles=current_roles,
                )

            # DEV-007 FIX: Merge attachments and track message_index for correct restoration
            # Each attachment needs to know which user message it belongs to
            if attachments:
                # Calculate message index = count of user messages in PRIOR messages (0-indexed)
                # First user message = index 0, second user message = index 1, etc.
                user_msg_count = sum(1 for m in prior_messages if m.get("role") == "user")

                # Add message_index to new attachments
                for att in attachments:
                    att["message_index"] = user_msg_count

                # DEV-007 P0.3 FIX: MERGE with deduplication by attachment ID
                # CRITICAL: Add NEW attachments FIRST, then PRIOR
                # This ensures new uploads override stale prior attachments with wrong message_index
                # If user re-uploads same file, the NEW version (with correct message_index) takes precedence
                seen_ids = set()
                resolved_attachments = []
                duplicates_skipped = 0

                # Add NEW attachments FIRST (they have the CORRECT current message_index)
                for att in attachments:
                    att_id = att.get("id")
                    if att_id and att_id not in seen_ids:
                        seen_ids.add(att_id)
                        resolved_attachments.append(att)

                # Add PRIOR attachments (skip if already in new - they have stale message_index)
                for att in prior_attachments:
                    att_id = att.get("id")
                    if att_id and att_id not in seen_ids:
                        seen_ids.add(att_id)
                        resolved_attachments.append(att)
                    elif att_id in seen_ids:
                        duplicates_skipped += 1
                        logger.info(
                            "prior_attachment_superseded_by_new",
                            att_id=att_id,
                            filename=att.get("filename"),
                            reason="new_upload_takes_precedence",
                        )

                logger.info(
                    "attachments_merged",
                    session_id=session_id,
                    new_count=len(attachments),
                    prior_count=len(prior_attachments),
                    total=len(resolved_attachments),
                    duplicates_skipped=duplicates_skipped,
                    message_index=user_msg_count,
                    filenames=[a.get("filename", "unknown") for a in attachments],
                    # DEV-007 DIAGNOSTIC: Log full merged order to verify prior+new sequence
                    merged_order=[a.get("filename", "unknown") for a in resolved_attachments],
                    prior_filenames=[a.get("filename", "unknown") for a in prior_attachments],
                )
            elif prior_attachments:
                # No new attachments, restore from checkpoint for follow-up questions
                resolved_attachments = prior_attachments
                logger.info(
                    "attachments_restored_from_checkpoint",
                    session_id=session_id,
                    attachment_count=len(prior_attachments),
                )
            else:
                resolved_attachments = []

            # DEV-007 Issue 11e FIX: Extract the LAST user message for knowledge retrieval
            # The frontend sends full conversation history, so we need the LAST user message
            # (the follow-up question), not the FIRST (the original question)
            user_query_text = ""
            for msg in reversed(messages):
                if msg.role == "user":  # type: ignore[attr-defined]
                    user_query_text = msg.content  # type: ignore[attr-defined]
                    break

            # DEV-007 FIX: Calculate current message index for marking current vs prior attachments
            # This is the count of prior user messages (0-indexed: first user msg = 0)
            current_message_index = sum(1 for m in prior_messages if m.get("role") == "user")

            initial_state = {
                "request_id": session_id,  # RAGState requires request_id
                "messages": merged_messages,  # DEV-007: Now includes full conversation history
                "session_id": session_id,
                "user_id": user_id,
                "user_query": user_query_text,  # User query for KB retrieval
                "streaming": {"requested": True},  # Nested structure for StreamCheck routing
                "attachments": resolved_attachments,  # DEV-007: File attachments (current or restored)
                "current_message_index": current_message_index,  # DEV-007 FIX: For marking current vs prior attachments
            }

            logger.info(
                "unified_graph_streaming_started", session_id=session_id, user_id=user_id, message_count=len(messages)
            )

            # Execute unified graph through all pre-LLM steps
            # The graph will execute:
            # - Lane 1: Request/Privacy validation (Steps 1-10)
            # - Lane 2: Message processing (Steps 11-13)
            # - Lane 3: Golden fast-path check (Steps 20-30)
            # - Lane 4: Classification (Steps 31, 42)
            # - Lane 6: Provider selection (Steps 48-58)
            # - Lane 7: Cache check (Steps 59-62)
            # - Lane 7: LLM Call and Tool handling (Steps 64-99)
            # - Lane 8: Streaming (Steps 104-112)

            # For now, use the full graph - it will execute completely
            # TODO Phase 4.1: Optimize to stop at Step 62 for streaming
            logger.info("calling_graph_ainvoke", session_id=session_id)

            # Step 8: Log graph invocation start
            rag_step_log(
                step=8,
                step_id="RAG.langgraphagent.unified.graph.invoke.start",
                node_label="InitAgent",
                processing_stage="graph_invocation_started",
                session_id=session_id,
                user_id=user_id,
                transition="Step 8 → Unified Graph (Lanes 1-8)",
                next_step=11,  # First step in Lane 2 (message processing)
            )

            # Debug: Log config and graph state
            config_to_use = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 50,  # Increased from default 25 to prevent infinite loops
            }
            logger.debug(
                "graph_ainvoke_debug",
                session_id=session_id,
                config=config_to_use,
                initial_state_keys=list(initial_state.keys()),
                graph_exists=self._graph is not None,
                graph_has_checkpointer=hasattr(self._graph, "checkpointer") if self._graph else False,
            )

            # DEV-007 P0.6 FIX: Update checkpoint state with merged data BEFORE ainvoke()
            # ROOT CAUSE: LangGraph checkpoint restoration REPLACES initial_state when ainvoke() is called
            # The reducers only fire on state UPDATES during graph execution, NOT on checkpoint LOAD
            # So we must update the checkpoint state with merged data BEFORE calling ainvoke()
            #
            # DEV-007 P0.9 FIX: Also update messages to include the new user message
            # Without this, Turn 2 user message is lost because checkpoint replaces initial_state.messages
            if config_to_use.get("configurable", {}).get("thread_id"):  # type: ignore[attr-defined]
                try:
                    update_values = {
                        "current_message_index": current_message_index,
                        "messages": merged_messages,  # P0.9: Include new user message
                    }
                    if resolved_attachments:
                        update_values["attachments"] = resolved_attachments
                    await self._graph.aupdate_state(
                        config=config_to_use,
                        values=update_values,
                    )
                    logger.info(
                        "DEV007_checkpoint_state_updated_before_ainvoke",
                        session_id=session_id,
                        message_count=len(merged_messages),
                        attachment_count=len(resolved_attachments) if resolved_attachments else 0,
                        current_message_index=current_message_index,
                        attachment_ids=[a.get("id") for a in resolved_attachments] if resolved_attachments else [],
                        filenames=[a.get("filename", "unknown") for a in resolved_attachments]
                        if resolved_attachments
                        else [],
                    )
                except Exception as e:
                    # Log but don't fail - initial_state will still work for first turn
                    logger.warning(
                        "DEV007_checkpoint_state_update_failed",
                        session_id=session_id,
                        error=str(e),
                        error_type=type(e).__name__,
                        fallback="using_initial_state",
                    )

            # CRITICAL: Yield SSE comment immediately to establish connection
            # This prevents timeout during the 33-second graph execution in ainvoke()
            # SSE spec allows comment lines (starting with ":") which clients ignore
            yield ": starting\n\n"

            # Keepalive mechanism: Send ": keepalive\n\n" every 5 seconds during RAG processing
            # This prevents frontend timeout (30-120s) for long queries
            try:
                # Create the ainvoke task
                ainvoke_task = asyncio.create_task(self._graph.ainvoke(initial_state, config=config_to_use))

                # Wait for ainvoke with periodic keepalive checks
                keepalive_interval = 5.0  # seconds
                while not ainvoke_task.done():
                    try:
                        # Wait up to keepalive_interval for task to complete
                        await asyncio.wait_for(asyncio.shield(ainvoke_task), timeout=keepalive_interval)
                        # Task completed within interval
                        break
                    except TimeoutError:
                        # Timeout reached, send keepalive and continue waiting
                        logger.debug("sending_keepalive_during_rag", session_id=session_id)
                        yield ": keepalive\n\n"

                # Get the result from completed task
                state = await ainvoke_task
            except Exception as graph_error:
                # Get full traceback for debugging
                tb_str = "".join(traceback.format_exception(type(graph_error), graph_error, graph_error.__traceback__))

                # Step 8: Log graph invocation failure with full traceback
                rag_step_log(
                    step=8,
                    step_id="RAG.langgraphagent.unified.graph.invoke.error",
                    node_label="InitAgent",
                    processing_stage="graph_invocation_failed",
                    session_id=session_id,
                    user_id=user_id,
                    error=str(graph_error),
                    error_type=type(graph_error).__name__,
                    traceback=tb_str,
                    cannot_proceed_reason=f"Graph invocation failed: {str(graph_error)}",
                )
                logger.error(
                    "graph_ainvoke_failed",
                    session_id=session_id,
                    error=str(graph_error),
                    traceback=tb_str,
                    exc_info=True,
                )
                raise

            # Step 8: Log graph invocation completion
            rag_step_log(
                step=8,
                step_id="RAG.langgraphagent.unified.graph.invoke.completed",
                node_label="InitAgent",
                processing_stage="graph_invocation_completed",
                session_id=session_id,
                user_id=user_id,
                state_keys=list(state.keys()) if state else [],
                has_final_response=bool(state.get("final_response")) if state else False,
                has_cache_hit=bool(state.get("cache", {}).get("hit")) if state else False,
                next_step="response_processing",
            )

            logger.info(
                "graph_ainvoke_completed",
                session_id=session_id,
                state_keys=list(state.keys()) if state else [],
                has_final_response=bool(state.get("final_response")) if state else False,
                has_cache_hit=bool(state.get("cache", {}).get("hit")) if state else False,
            )

            # FIX: Extract LLM response and build final_response if missing
            # BUT: Skip extraction for streaming requests - let them fall through to provider.stream_completion()
            # This preserves token-by-token streaming while fixing non-streaming responses
            streaming_requested = state.get("streaming", {}).get("requested", False)

            # DIAGNOSTIC: Log streaming state after graph execution
            logger.info(
                "DIAGNOSTIC_streaming_state_after_graph",
                session_id=session_id,
                streaming_requested=streaming_requested,
                streaming_state=state.get("streaming"),
                has_final_response=bool(state.get("final_response")),
                has_llm_response=bool(state.get("llm_response")),
                has_llm_data=bool(state.get("llm")),
                state_keys=list(state.keys()),
            )

            if not state.get("final_response") and not streaming_requested:
                # Only extract for non-streaming responses
                # Streaming responses will fall through to provider.stream_completion() below
                llm_response_data = state.get("llm_response")

                # Debug logging to understand actual structure
                logger.info(
                    "llm_response_structure_debug",
                    session_id=session_id,
                    has_llm_response=bool(llm_response_data),
                    llm_response_type=type(llm_response_data).__name__ if llm_response_data else None,
                    llm_response_keys=list(llm_response_data.keys()) if isinstance(llm_response_data, dict) else None,
                    llm_response_sample=str(llm_response_data)[:500] if llm_response_data else None,
                )

                # Try multiple extraction paths for content
                content = None
                if llm_response_data:
                    if isinstance(llm_response_data, dict):
                        # Try various possible keys
                        content = (
                            llm_response_data.get("content")
                            or (
                                llm_response_data.get("response", {}).get("content")
                                if isinstance(llm_response_data.get("response"), dict)
                                else None
                            )
                            or llm_response_data.get("text")
                            or llm_response_data.get("message")
                        )
                    elif hasattr(llm_response_data, "content"):
                        content = llm_response_data.content

                    if content:
                        state["final_response"] = {"content": content, "type": "success"}
                        logger.info(
                            "final_response_extracted_from_llm_response",
                            session_id=session_id,
                            content_length=len(content),
                        )

                # Fallback: Extract from last assistant message if llm_response didn't work
                if not state.get("final_response"):
                    messages = state.get("messages", [])
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get("role") == "assistant":
                            content = msg.get("content", "")
                            if content:
                                state["final_response"] = {"content": content, "type": "success"}
                                logger.info(
                                    "final_response_extracted_from_messages",
                                    session_id=session_id,
                                    content_length=len(content),
                                )
                                break

            # Add diagnostic logging
            logger.info(
                "streaming_response_extraction",
                session_id=session_id,
                streaming_requested=streaming_requested,
                has_final_response=bool(state.get("final_response")),
                has_llm_response=bool(state.get("llm_response")),
                has_messages=bool(state.get("messages")),
                message_count=len(state.get("messages", [])),
                llm_success=state.get("llm", {}).get("success"),
                will_use_fallback_streaming=streaming_requested and not bool(state.get("final_response")),
            )

            # Check if there's a final response in the state
            final_response = state.get("final_response")

            # DIAGNOSTIC: Log final_response check
            logger.info(
                "DIAGNOSTIC_final_response_check",
                session_id=session_id,
                has_final_response=bool(final_response),
                final_response_type=final_response.get("type") if final_response else None,
                final_response_content_length=len(final_response.get("content", "")) if final_response else 0,
                streaming_requested=streaming_requested,
            )

            if final_response:
                # Check if this is an error response
                is_error = (
                    final_response.get("type") == "error"
                    or state.get("workflow_terminated") is True
                    or state.get("status_code", 200) >= 400
                )

                if is_error:
                    # Yield error content for streaming to frontend
                    error_msg = final_response.get("content", "An error occurred")
                    status_code = state.get("status_code", 400)
                    logger.error(
                        "graph_returned_error",
                        session_id=session_id,
                        status_code=status_code,
                        error_message=error_msg,
                        error_type=final_response.get("error_type"),
                    )
                    if error_msg:
                        yield error_msg
                    logger.info(
                        "unified_graph_error_response_streamed",
                        session_id=session_id,
                        status_code=status_code,
                        error_length=len(error_msg),
                    )
                    return

                # FIX: For streaming requests, don't yield complete response - use buffered streaming
                if streaming_requested:
                    logger.info(
                        "streaming_requested_skipping_complete_response",
                        session_id=session_id,
                        has_content=bool(final_response.get("content")),
                        will_use_buffered_streaming=True,
                    )
                    # Fall through to buffered streaming logic below
                    # Don't return - let the buffered streaming handle it
                else:
                    # Normal successful response for non-streaming requests
                    content = final_response.get("content", "")
                    logger.info(
                        "final_response_branch",
                        session_id=session_id,
                        has_content=bool(content),
                        content_length=len(content) if content else 0,
                    )
                    if content:
                        yield content
                    logger.info(
                        "unified_graph_streaming_completed_from_graph",
                        session_id=session_id,
                        response_length=len(content),
                    )
                    return

            # If no final_response but cache hit, return cached
            if state.get("cache", {}).get("hit"):
                cached_response = state.get("cache", {}).get("response", {})
                content = cached_response.get("content", "")
                logger.info(
                    "cache_hit_branch",
                    session_id=session_id,
                    has_content=bool(content),
                    content_length=len(content) if content else 0,
                )
                if content:
                    yield content
                logger.info("unified_graph_cache_hit_streaming", session_id=session_id, cached=True)
                return

            # FIX: Check for content to stream (from final_response or buffered response)
            content = None

            # Priority 0: Check for golden answer (served by Step 28)
            # This bypasses LLM entirely when a golden answer was served
            # Uses golden_hit and golden_answer which are declared in RAGState
            if state.get("golden_hit"):
                golden_answer = state.get("golden_answer")
                if golden_answer:
                    content = golden_answer
                    logger.info(
                        "streaming_from_golden_answer",
                        session_id=session_id,
                        content_length=len(content),
                        source="golden_served_step_28",
                    )

            # Priority 1: Check final_response (only if Priority 0 didn't set content)
            if not content and final_response and streaming_requested:
                content = final_response.get("content", "")
                if content:
                    logger.info(
                        "streaming_from_final_response",
                        session_id=session_id,
                        content_length=len(content),
                        source="final_response_with_streaming_requested",
                    )

            # Priority 2: Check buffered response from Step 64
            if not content:
                llm_data = state.get("llm", {})
                buffered_response = llm_data.get("response")

                if llm_data.get("success") and buffered_response:
                    # Extract content from LLMResponse object or dict format
                    if isinstance(buffered_response, dict):
                        content = buffered_response.get("content")
                    elif hasattr(buffered_response, "content"):
                        content = buffered_response.content

                    if content:
                        logger.info(
                            "streaming_from_buffered_response",
                            session_id=session_id,
                            content_length=len(content),
                            source="step_64_completed",
                        )

            # DIAGNOSTIC: Log content extraction result
            logger.info(
                "DIAGNOSTIC_content_extraction_result",
                session_id=session_id,
                content_found=bool(content),
                content_length=len(content) if content else 0,
                will_use_buffered_streaming=bool(content),
                will_fallback_to_provider_stream=not bool(content),
            )

            if content:
                # DEV-007 FIX: De-anonymize PII placeholders in buffered content
                # Previously only the fallback streaming path de-anonymized.
                # The buffered path was saving PII placeholders to chat history.
                privacy = state.get("privacy") or {}
                deanonymization_map = privacy.get("document_deanonymization_map", {})
                if deanonymization_map:
                    original_length = len(content)
                    for placeholder, original in sorted(
                        deanonymization_map.items(),
                        key=lambda x: len(x[0]),
                        reverse=True,
                    ):
                        content = content.replace(placeholder, original)
                    if len(content) != original_length:
                        logger.info(
                            "DEV007_buffered_content_deanonymized",
                            session_id=session_id,
                            original_length=original_length,
                            deanonymized_length=len(content),
                            placeholders_available=len(deanonymization_map),
                        )

                # Stream the buffered content by chunking at word boundaries
                logger.info(
                    "DIAGNOSTIC_starting_buffered_streaming_loop",  # pragma: allowlist secret
                    session_id=session_id,
                    content_length=len(content),
                    chunk_size=100,
                )
                chunk_size = 100  # Industry standard for buffered streaming
                i = 0
                chunk_count = 0
                while i < len(content):
                    # Find word boundary near chunk_size
                    end = min(i + chunk_size, len(content))

                    # If not at end, look for word boundary (space, newline, punctuation)
                    if end < len(content):
                        # Search forward up to 20 chars for a good breaking point
                        search_end = min(end + 20, len(content))
                        boundary_chars = (" ", "\n", "\t", ".", ",", "!", "?", ";", ":", ")")

                        # Find next boundary after target chunk size
                        best_break = -1
                        for boundary_char in boundary_chars:
                            pos = content.find(boundary_char, end, search_end)
                            if pos != -1:
                                if best_break == -1 or pos < best_break:
                                    best_break = pos

                        # Use boundary if found, otherwise use exact chunk_size
                        if best_break != -1:
                            end = best_break + 1  # Include the boundary character

                    chunk = content[i:end]
                    chunk_count += 1

                    # DIAGNOSTIC: Log each chunk before yielding
                    logger.info(
                        "DIAGNOSTIC_yielding_chunk",
                        session_id=session_id,
                        chunk_number=chunk_count,
                        chunk_size=len(chunk),
                        chunk_start_pos=i,
                        chunk_end_pos=end,
                        chunk_preview=chunk[:50] if len(chunk) > 50 else chunk,
                        remaining_content=len(content) - end,
                    )

                    try:
                        yield chunk

                        # DIAGNOSTIC: Log after successful yield
                        logger.info(
                            "DIAGNOSTIC_chunk_yielded_successfully", session_id=session_id, chunk_number=chunk_count
                        )
                    except Exception as yield_error:
                        # DIAGNOSTIC: Log any errors during yield
                        logger.error(
                            "DIAGNOSTIC_error_yielding_chunk",
                            session_id=session_id,
                            chunk_number=chunk_count,
                            error=str(yield_error),
                            error_type=type(yield_error).__name__,
                            exc_info=True,
                        )
                        raise

                    i = end
                    await asyncio.sleep(0.05)  # 50ms delay, industry standard

                logger.info(
                    "DIAGNOSTIC_buffered_streaming_complete",  # pragma: allowlist secret
                    session_id=session_id,
                    total_chunks_yielded=chunk_count,
                    total_content_length=len(content),
                )

                # Yield metadata marker for chat history save
                # This tells chatbot.py whether to use "golden_set" or "llm" as model_used
                golden_hit = state.get("golden_hit", False)
                yield f"__RESPONSE_METADATA__:golden_hit={golden_hit}"

                return  # Exit without making second LLM call

            # DIAGNOSTIC: We reached the fallback streaming path (content was not found)
            logger.warning(
                "DIAGNOSTIC_fallback_to_provider_streaming",  # pragma: allowlist secret
                session_id=session_id,
                reason="No buffered content found, making second LLM call",
                had_final_response=bool(final_response),
                had_llm_data=bool(state.get("llm")),
                streaming_requested=streaming_requested,
            )

            # Use provider from state if available, otherwise get one
            provider: LLMProvider | None = state.get("provider", {}).get("selected")
            processed_messages: list[Message] = state.get("processed_messages", messages)

            if not provider:
                # Fallback: classify and get provider directly
                self._current_classification = await self._classify_user_query(messages)
                system_prompt = await self._get_system_prompt(messages, self._current_classification)
                processed_messages = await self._prepare_messages_with_system_prompt(
                    messages, system_prompt, self._current_classification
                )
                provider = self._get_optimal_provider(processed_messages)

            # At this point provider is guaranteed to be non-None
            assert provider is not None, "Provider must be set at this point"

            # Stream from provider
            logger.info(
                "DIAGNOSTIC_starting_provider_stream_completion",
                session_id=session_id,
                provider=provider.provider_type.value if provider else None,
                model=provider.model if provider else None,
            )

            # DEV-007 FIX: Get de-anonymization map for PII restoration in fallback path
            privacy = state.get("privacy") or {}
            deanonymization_map = privacy.get("document_deanonymization_map", {})
            if deanonymization_map:
                logger.info(
                    "fallback_streaming_with_deanonymization",
                    session_id=session_id,
                    placeholder_count=len(deanonymization_map),
                )

            async for chunk in provider.stream_completion(
                messages=processed_messages,
                tools=None,
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
            ):
                # Handle both LLMStreamResponse objects and plain strings
                chunk_content: str | None = None
                if isinstance(chunk, str):
                    chunk_content = chunk
                elif hasattr(chunk, "content") and chunk.content:  # type: ignore[unreachable]
                    chunk_content = chunk.content

                if chunk_content:
                    # DEV-007 FIX: De-anonymize streaming content
                    if deanonymization_map:
                        for placeholder, original in sorted(
                            deanonymization_map.items(),
                            key=lambda x: len(x[0]),
                            reverse=True,
                        ):
                            chunk_content = chunk_content.replace(placeholder, original)
                    yield chunk_content

                if hasattr(chunk, "done") and chunk.done:
                    break

        except Exception as stream_error:
            # Step 8: InitAgent - Failure logging
            rag_step_log(
                step=8,
                step_id="RAG.langgraphagent.get.stream.response.error",
                node_label="InitAgent",
                processing_stage="failed",
                session_id=session_id,
                user_id=user_id,
                error=str(stream_error),
                error_type=type(stream_error).__name__,
                cannot_proceed_reason=f"Streaming failed: {str(stream_error)}",
            )

            logger.error(
                "unified_graph_streaming_failed", error=str(stream_error), session_id=session_id, user_id=user_id
            )
            raise stream_error
        finally:
            # Clean up tracking info
            self._current_user_id = None
            self._current_session_id = None
            self._current_classification = None

    async def _stream_with_direct_llm(self, messages: list[Message], session_id: str) -> AsyncGenerator[str]:
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
            processed_messages = await self._prepare_messages_with_system_prompt(
                messages, system_prompt, self._current_classification
            )

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
                provider=(
                    getattr(self._current_provider, "provider_type", {}).get("value", "unknown")
                    if self._current_provider
                    else "unknown"
                ),
            )
            raise

    async def _stream_with_langgraph_workflow(self, messages: list[Message], session_id: str) -> AsyncGenerator[str]:
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

            # Type cast: LangGraph accepts dicts for config
            config: Any = {
                "configurable": {"thread_id": session_id},
                "callbacks": [CallbackHandler()],
                "recursion_limit": 50,  # Increased from default 25 to prevent infinite loops
            }

            logger.info(
                "langgraph_workflow_stream_started",
                session_id=session_id,
                classification_used=self._current_classification is not None,
                domain=self._current_classification.domain.value if self._current_classification else None,
                action=self._current_classification.action.value if self._current_classification else None,
            )

            # Type cast: LangGraph accepts dicts matching the state schema
            input_state: Any = {
                "messages": dump_messages(messages),
                "session_id": session_id,
                "attachments": [],  # Attachments handled in get_stream_response
            }

            # Stream from LangGraph with filtering to avoid duplicates
            async for token, metadata in self._graph.astream(input_state, config, stream_mode="messages"):  # type: ignore[union-attr]
                try:
                    # Filter only from the main chat node to avoid tool call duplicates
                    if metadata.get("langgraph_node") == "chat":
                        if hasattr(token, "content") and token.content:
                            # Avoid yielding very large chunks (likely complete messages)
                            # This helps prevent the final complete message from being duplicated
                            if len(token.content) < 150:  # Threshold for token vs complete message
                                yield token.content

                except Exception as token_error:
                    logger.error("langgraph_token_processing_error", error=str(token_error), session_id=session_id)
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

        DEV-007 FIX: ALWAYS read from checkpoint first to prevent race conditions.
        The cache can contain stale data if page refresh happens during Turn 2 processing.
        Reading from checkpoint ensures we get the most recent persisted state.

        Args:
            session_id (str): The session ID for the conversation.

        Returns:
            list[Message]: The chat history.
        """
        # DEV-007 FIX: Always read from checkpoint for consistency
        # Previously checked cache first, causing race conditions on page refresh
        # where Turn 2's user message would show Turn 1's content
        if self._graph is None:
            self._graph = await self.create_graph()

        state: StateSnapshot = await sync_to_async(self._graph.get_state)(  # type: ignore[union-attr]
            config={"configurable": {"thread_id": session_id}}
        )
        # StateSnapshot.values exists but IDE type stubs don't recognize it
        messages = self.__process_messages(state.values["messages"]) if state.values else []

        # DEV-007 FIX: Restore attachments to correct messages using message_index
        # Each attachment has a message_index indicating which user message it belongs to
        if state.values:
            checkpoint_attachments = state.values.get("attachments", [])
            if checkpoint_attachments and messages:
                # Group attachments by message_index
                attachments_by_msg_idx: dict[int, list[dict]] = {}
                for a in checkpoint_attachments:
                    if a.get("id") and a.get("filename"):
                        idx = a.get("message_index", 0)  # Default to 0 for backwards compat
                        attachments_by_msg_idx.setdefault(idx, []).append(a)

                # Assign attachments to correct user messages
                user_msg_idx = 0
                for msg in messages:
                    if msg.role == "user":
                        if user_msg_idx in attachments_by_msg_idx:
                            msg.attachments = [
                                AttachmentInfo(
                                    id=str(a.get("id", "")),
                                    filename=a.get("filename", ""),
                                    type=a.get("mime_type"),
                                )
                                for a in attachments_by_msg_idx[user_msg_idx]
                            ]
                            logger.info(
                                "attachments_restored_to_message",
                                session_id=session_id,
                                message_index=user_msg_idx,
                                attachment_count=len(msg.attachments),
                                filenames=[a.filename for a in msg.attachments],
                            )
                        user_msg_idx += 1

                # DEV-007 FIX: De-anonymize PII placeholders before returning to frontend
                # PII placeholders like [NOME_E478], [INDIRIZZO_2D50] should be replaced
                # with original values using pii_map stored with each attachment
                combined_pii_map: dict[str, str] = {}
                for att in checkpoint_attachments:
                    if att.get("pii_map"):
                        combined_pii_map.update(att["pii_map"])

                if combined_pii_map and messages:
                    deanon_count = 0
                    for msg in messages:
                        if msg.content:
                            original_content = msg.content
                            for placeholder, original_value in combined_pii_map.items():
                                msg.content = msg.content.replace(placeholder, original_value)
                            if msg.content != original_content:
                                deanon_count += 1

                    if deanon_count > 0:
                        logger.info(
                            "pii_deanonymized_in_chat_history",
                            session_id=session_id,
                            messages_deanonymized=deanon_count,
                            pii_map_size=len(combined_pii_map),
                        )

        # Cache the conversation for future use
        if messages:
            try:
                await cache_service.cache_conversation(session_id, messages)
                logger.info("conversation_cached", session_id=session_id, message_count=len(messages))
            except Exception as e:
                logger.error("conversation_cache_set_failed", error=str(e), session_id=session_id)

        return messages

    @staticmethod
    def __process_messages(messages: list[BaseMessage]) -> list[Message]:
        """Convert messages from state to Message objects.

        Messages may be stored as dicts, Message objects, or BaseMessage objects.
        We need to convert them to BaseMessage objects before passing to convert_to_openai_messages.
        """
        # Convert dict/Message objects to BaseMessage objects
        base_messages = []
        for msg in messages:
            # Already a BaseMessage
            if isinstance(msg, BaseMessage):
                base_messages.append(msg)
            # Dict or Message object - convert based on role
            else:
                # Get role and content (handle both dict and Message object)
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                else:
                    # Pydantic Message object
                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", "")

                # Convert to appropriate BaseMessage type
                if role == "system":
                    base_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    base_messages.append(AIMessage(content=content))
                else:  # user or any other role
                    base_messages.append(HumanMessage(content=content))

        # Now convert to OpenAI format
        openai_style_messages = convert_to_openai_messages(base_messages)

        # DEV-007: Debug logging for system message leak investigation
        all_roles = [m.get("role") for m in openai_style_messages]
        system_count = sum(1 for r in all_roles if r == "system")
        if system_count > 0:
            logger.warning(
                "system_messages_in_checkpoint",
                system_count=system_count,
                all_roles=all_roles,
                msg_preview=[m.get("content", "")[:50] for m in openai_style_messages if m.get("role") == "system"],
            )

        # keep just assistant and user messages
        filtered = [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]

        logger.debug(
            "process_messages_filtered",
            original_count=len(openai_style_messages),
            filtered_count=len(filtered),
            roles_before=all_roles,
            roles_after=[m.role for m in filtered],
        )

        return filtered

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
                logger.error("conversation_cache_invalidation_failed", error=str(e), session_id=session_id)

            # Make sure the pool is initialized in the current event loop
            conn_pool = await self._get_connection_pool()

            # Use a new connection for this specific operation
            async with conn_pool.connection() as conn:  # type: ignore[union-attr]
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
