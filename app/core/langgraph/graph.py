"""This file contains the LangGraph Agent/workflow and interactions with the LLM."""

from typing import (
    AsyncGenerator,
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
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.tools import tools
from app.core.llm.base import LLMProvider
from app.core.llm.factory import get_llm_provider, RoutingStrategy
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.monitoring.metrics import track_llm_cost, track_api_call, track_classification_usage
from app.core.prompts import SYSTEM_PROMPT
from app.schemas import (
    GraphState,
    Message,
)
from app.services.cache import cache_service
from app.services.domain_action_classifier import DomainActionClassifier, DomainActionClassification, Action
from app.services.domain_prompt_templates import PromptTemplateManager
from app.services.golden_fast_path import GoldenFastPathService, EligibilityDecision
from app.services.knowledge_search_service import KnowledgeSearchService
from app.core.database import database_service
from app.services.usage_tracker import usage_tracker
from app.utils import (
    dump_messages,
)


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
        self._knowledge_search_service = None  # Will be initialized when needed (requires DB session)
        self._current_classification = None  # Store current query classification
        self._response_metadata = None  # Store response metadata
        self._kb_context = None  # Store retrieved knowledge context

        logger.info("llm_agent_initialized", environment=settings.ENVIRONMENT.value)

    async def _classify_user_query(self, messages: List[Message]) -> Optional[DomainActionClassification]:
        """Classify the latest user query using domain-action classifier.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            DomainActionClassification or None if no messages
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

    async def _retrieve_knowledge_context(self, messages: List[Message], session_id: str, user_id: Optional[str]) -> List[dict]:
        """
        Retrieve relevant knowledge context using hybrid search (BM25 + Vector + Recency).
        
        This implements RAG STEP 39 — KBPreFetch.
        
        Args:
            messages: List of conversation messages
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            List of relevant knowledge items
        """
        # Find the latest user message
        user_message = None
        for message in reversed(messages):
            if message.role == "user":
                user_message = message.content
                break
        
        if not user_message:
            return []
        
        try:
            # Create DB session for knowledge retrieval
            with database_service.get_session_maker() as db_session:
                # Try to get vector service (graceful degradation if unavailable)
                vector_service = None
                try:
                    from app.services.vector_service_enhanced import EnhancedVectorService
                    vector_service = EnhancedVectorService()
                except Exception as e:
                    logger.warning("vector_service_init_failed", error=str(e))
                    
                # Create knowledge search service for this request
                knowledge_search_service = KnowledgeSearchService(
                    db_session=db_session,
                    vector_service=vector_service
                )
                
                # Prepare query data for knowledge search
                query_data = {
                    "query": user_message,
                    "canonical_facts": [],  # TODO: Extract from atomic facts extraction
                    "user_id": user_id or "anonymous",
                    "session_id": session_id,
                    "trace_id": f"trace_{session_id}_{hash(user_message)}",
                    "context": {
                        "domain": self._current_classification.domain.value if self._current_classification else "general",
                        "language": "it"  # Default to Italian for Italian tax system
                    }
                }
                
                # Retrieve top-k knowledge items
                search_results = await knowledge_search_service.retrieve_topk(query_data)
                
                # Convert SearchResult objects to dict format for easier handling
                knowledge_items = []
                for result in search_results:
                    knowledge_items.append({
                        "id": result.id,
                        "title": result.title,
                        "content": result.content,
                        "category": result.category,
                        "source": result.source,
                        "score": result.score,
                        "updated_at": result.updated_at.isoformat() if result.updated_at else None
                    })
                
                # Store context for potential use in prompts
                self._kb_context = knowledge_items
                
                logger.info(
                    "knowledge_context_retrieved",
                    session_id=session_id,
                    results_count=len(knowledge_items),
                    avg_score=sum(item["score"] for item in knowledge_items) / len(knowledge_items) if knowledge_items else 0.0,
                    top_categories=[item["category"] for item in knowledge_items[:3]]
                )
                
                return knowledge_items
                
        except Exception as e:
            logger.error("knowledge_retrieval_failed", error=str(e), session_id=session_id, exc_info=True)
            return []

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

    def _get_routing_strategy(self) -> RoutingStrategy:
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

    def _get_classification_aware_routing(self, classification: DomainActionClassification) -> tuple[RoutingStrategy, float]:
        """Get routing strategy and cost limit based on domain-action classification.
        
        Args:
            classification: The domain-action classification result
            
        Returns:
            tuple: (routing_strategy, max_cost_eur)
        """
        # Map domain-action combinations to routing strategies
        strategy_map = {
            # High-accuracy requirements (legal, financial calculations)
            ("legal", "document_generation"): (RoutingStrategy.QUALITY_FIRST, 0.030),
            ("legal", "compliance_check"): (RoutingStrategy.QUALITY_FIRST, 0.025),
            ("tax", "calculation_request"): (RoutingStrategy.QUALITY_FIRST, 0.020),
            ("accounting", "document_analysis"): (RoutingStrategy.QUALITY_FIRST, 0.025),
            ("business", "strategic_advice"): (RoutingStrategy.QUALITY_FIRST, 0.025),
            
            # CCNL-specific routing (balanced for accuracy and cost)
            ("labor", "ccnl_query"): (RoutingStrategy.BALANCED, 0.018),
            ("labor", "calculation_request"): (RoutingStrategy.BALANCED, 0.020),
            
            # Balanced requirements (moderate complexity)
            ("tax", "strategic_advice"): (RoutingStrategy.BALANCED, 0.015),
            ("labor", "compliance_check"): (RoutingStrategy.BALANCED, 0.015),
            ("business", "document_generation"): (RoutingStrategy.BALANCED, 0.020),
            ("accounting", "compliance_check"): (RoutingStrategy.BALANCED, 0.015),
            
            # Cost-optimized for simple queries
            ("tax", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.010),
            ("legal", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.010),
            ("labor", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.010),
            ("business", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.010),
            ("accounting", "information_request"): (RoutingStrategy.COST_OPTIMIZED, 0.010),
        }
        
        # Get strategy for this domain-action combination
        key = (classification.domain.value, classification.action.value)
        strategy, max_cost = strategy_map.get(key, (RoutingStrategy.BALANCED, 0.020))
        
        # Adjust cost limits based on confidence
        if classification.confidence < 0.7:
            # Lower confidence -> use failover strategy and reduce cost limit
            strategy = RoutingStrategy.FAILOVER
            max_cost *= 0.8
        elif classification.confidence > 0.9:
            # Very high confidence -> can afford slightly higher cost for quality
            max_cost *= 1.2
        
        # Respect global maximum cost limit
        global_max_cost = getattr(settings, 'LLM_MAX_COST_EUR', 0.020)
        max_cost = min(max_cost, global_max_cost)
        
        return strategy, max_cost

    def _get_system_prompt(self, messages: List[Message], classification: Optional[DomainActionClassification]) -> str:
        """Get the appropriate system prompt based on classification.
        
        Args:
            messages: List of conversation messages
            classification: Domain-action classification result
            
        Returns:
            str: The system prompt to use
        """
        if not classification:
            # Fallback to default system prompt
            return SYSTEM_PROMPT
            
        # Only use domain-specific prompts for high confidence classifications
        if classification.confidence < settings.CLASSIFICATION_CONFIDENCE_THRESHOLD:
            logger.info(
                "classification_confidence_too_low",
                confidence=classification.confidence,
                threshold=settings.CLASSIFICATION_CONFIDENCE_THRESHOLD,
                using_default_prompt=True
            )
            return SYSTEM_PROMPT
            
        try:
            # Get the latest user message for context
            user_query = ""
            for message in reversed(messages):
                if message.role == "user":
                    user_query = message.content
                    break
            
            # Generate domain-specific prompt
            domain_prompt = self._prompt_template_manager.get_prompt(
                domain=classification.domain,
                action=classification.action,
                query=user_query,
                context=None,  # Could be enhanced later with conversation context
                document_type=classification.document_type
            )
            
            logger.info(
                "domain_specific_prompt_selected",
                domain=classification.domain.value,
                action=classification.action.value,
                confidence=classification.confidence
            )
            
            # Track domain-specific prompt usage
            track_classification_usage(
                domain=classification.domain.value,
                action=classification.action.value,
                confidence=classification.confidence,
                prompt_used=True
            )
            
            return domain_prompt
            
        except Exception as e:
            logger.error("domain_prompt_generation_failed", error=str(e), exc_info=True)
            return SYSTEM_PROMPT

    def _get_optimal_provider(self, messages: List[Message]) -> LLMProvider:
        """Get the optimal LLM provider for the given messages.

        Args:
            messages: List of conversation messages

        Returns:
            LLMProvider: The optimal provider for this request
        """
        try:
            # Use classification-aware routing if available
            if self._current_classification:
                strategy, max_cost = self._get_classification_aware_routing(self._current_classification)
            else:
                strategy = self._get_routing_strategy()
                max_cost = getattr(settings, 'LLM_MAX_COST_EUR', 0.020)
            
            preferred_provider = getattr(settings, 'LLM_PREFERRED_PROVIDER', None)
            
            provider = get_llm_provider(
                messages=messages,
                strategy=strategy,
                max_cost_eur=max_cost,
                preferred_provider=preferred_provider or None,
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

        # RAG STEP 39 — KBPreFetch: Retrieve knowledge context 
        session_id = state.session_id if hasattr(state, 'session_id') else "unknown_session"
        user_id = state.user_id if hasattr(state, 'user_id') else None
        await self._retrieve_knowledge_context(conversation_messages, session_id, user_id)

        # Get domain-specific system prompt or default
        system_prompt = self._get_system_prompt(conversation_messages, self._current_classification)
        
        # Add system prompt if not already present
        if not conversation_messages or conversation_messages[0].role != "system":
            system_message = Message(role="system", content=system_prompt)
            conversation_messages.insert(0, system_message)
        elif self._current_classification:
            # Replace existing system prompt with domain-specific one
            conversation_messages[0] = Message(role="system", content=system_prompt)

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

    def _should_continue(self, state: GraphState) -> Literal["end", "continue"]:
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

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """Create and configure the LangGraph workflow.

        Returns:
            Optional[CompiledStateGraph]: The configured LangGraph instance or None if init fails
        """
        if self._graph is None:
            try:
                graph_builder = StateGraph(GraphState)
                graph_builder.add_node("chat", self._chat)
                graph_builder.add_node("tool_call", self._tool_call)
                graph_builder.add_conditional_edges(
                    "chat",
                    self._should_continue,
                    {"continue": "tool_call", "end": END},
                )
                graph_builder.add_edge("tool_call", "chat")
                graph_builder.set_entry_point("chat")
                graph_builder.set_finish_point("chat")

                # Get connection pool (may be None in production if DB unavailable)
                connection_pool = await self._get_connection_pool()
                if connection_pool:
                    checkpointer = AsyncPostgresSaver(connection_pool)
                    await checkpointer.setup()
                else:
                    # In production, proceed without checkpointer if needed
                    checkpointer = None
                    if settings.ENVIRONMENT != Environment.PRODUCTION:
                        raise Exception("Connection pool initialization failed")

                self._graph = graph_builder.compile(
                    checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})"
                )

                logger.info(
                    "graph_created",
                    graph_name=f"{settings.PROJECT_NAME} Agent",
                    environment=settings.ENVIRONMENT.value,
                    has_checkpointer=checkpointer is not None,
                )
            except Exception as e:
                logger.error("graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # In production, we don't want to crash the app
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_graph")
                    return None
                raise e

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

    def _needs_complex_workflow(self, classification: Optional[DomainActionClassification]) -> bool:
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
            
            # RAG STEP 39 — KBPreFetch: Retrieve knowledge context for streaming
            await self._retrieve_knowledge_context(messages, session_id, user_id)
            
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
            system_prompt = self._get_system_prompt(messages, self._current_classification)
            
            # Prepare messages with system prompt
            processed_messages = messages.copy()
            if not processed_messages or processed_messages[0].role != "system":
                system_message = Message(role="system", content=system_prompt)
                processed_messages.insert(0, system_message)
            elif self._current_classification:
                # Replace existing system prompt with domain-specific one
                processed_messages[0] = Message(role="system", content=system_prompt)
            
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

    def __process_messages(self, messages: list[BaseMessage]) -> list[Message]:
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
