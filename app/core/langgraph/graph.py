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
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from openai import OpenAIError
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.tools import tools
from app.core.llm.factory import get_llm_provider, RoutingStrategy
from app.core.llm.base import LLMProvider
from app.services.domain_action_classifier import DomainActionClassifier, DomainActionClassification
from app.services.domain_prompt_templates import PromptTemplateManager
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.monitoring.metrics import track_llm_cost, track_api_call, track_llm_error, track_classification_usage
from app.core.prompts import SYSTEM_PROMPT
from app.core.decorators.cache import cache_llm_response, cache_conversation
from app.services.cache import cache_service
from app.services.usage_tracker import usage_tracker
from app.schemas import (
    GraphState,
    Message,
)
from app.utils import (
    dump_messages,
    prepare_messages,
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
        self._current_classification = None  # Store current query classification
        self._response_metadata = None  # Store response metadata

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

    async def get_stream_response(
        self, messages: list[Message], session_id: str, user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Get a stream response from the LLM with HTML formatting.

        Args:
            messages (list[Message]): The messages to send to the LLM.
            session_id (str): The session ID for the conversation.
            user_id (Optional[str]): The user ID for the conversation.

        Yields:
            str: HTML-formatted chunks of the LLM response.
        """
        from app.core.content_formatter import StreamingHTMLProcessor
        
        # Store user and session info for tracking
        self._current_user_id = user_id
        self._current_session_id = session_id
        
        # Initialize HTML processor for this stream
        html_processor = StreamingHTMLProcessor()
        
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [
                CallbackHandler()
            ],
        }
        if self._graph is None:
            self._graph = await self.create_graph()

        try:
            async for token, _ in self._graph.astream(
                {"messages": dump_messages(messages), "session_id": session_id}, config, stream_mode="messages"
            ):
                try:
                    # Get the content from the token
                    content = token.content if hasattr(token, 'content') else str(token)
                    
                    # Process each character through HTML formatter for proper streaming
                    for char in content:
                        html_chunk = await html_processor.process_token(char)
                        if html_chunk:
                            # Yield HTML chunk instead of raw token
                            yield html_chunk
                            
                except Exception as token_error:
                    logger.error("Error processing token", error=str(token_error), session_id=session_id)
                    # Continue with next token even if current one fails
                    continue
            
            # Finalize any remaining content in the processor
            final_chunk = await html_processor.finalize()
            if final_chunk:
                yield final_chunk
                
        except Exception as stream_error:
            logger.error("Error in stream processing", error=str(stream_error), session_id=session_id)
            raise stream_error
        finally:
            # Clean up tracking info
            self._current_user_id = None
            self._current_session_id = None

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
