# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs): return None
    def rag_step_timer(*args, **kwargs): return nullcontext()

def step_48__select_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 48 — LangGraphAgent._get_optimal_provider Select LLM provider
    ID: RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider
    Type: process | Category: providers | Node: SelectProvider

    Entry point for LLM provider selection. Initiates the provider routing process
    based on the context (messages, strategy, budget constraints).

    Incoming: ReplaceMsg (Step 46), InsertMsg (Step 47)
    Outgoing: RouteStrategy (Step 49)
    """
    from app.core.llm.factory import RoutingStrategy
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(48, 'RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider', 'SelectProvider', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract messages (required)
        messages = params.get('messages', messages)
        if not messages:
            error_msg = 'Missing required parameter: messages'
            logger.error(f"STEP 48: {error_msg}")
            rag_step_log(
                step=48,
                step_id='RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider',
                node_label='SelectProvider',
                category='providers',
                type='process',
                error=error_msg,
                provider_selection_initiated=False,
                processing_stage="failed"
            )
            return {
                'provider_selection_initiated': False,
                'error': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Extract routing parameters with defaults
        routing_strategy = params.get('routing_strategy', RoutingStrategy.COST_OPTIMIZED)
        max_cost_eur = params.get('max_cost_eur')
        preferred_provider = params.get('preferred_provider')
        fallback_provider = params.get('fallback_provider')

        # Extract context parameters
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        # Log the provider selection initiation
        logger.info(
            f"STEP 48: Initiating provider selection",
            extra={
                'step': 48,
                'messages_count': len(messages),
                'routing_strategy': routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy),
                'max_cost_eur': max_cost_eur,
                'preferred_provider': preferred_provider
            }
        )

        rag_step_log(
            step=48,
            step_id='RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider',
            node_label='SelectProvider',
            category='providers',
            type='process',
            provider_selection_initiated=True,
            messages_count=len(messages),
            routing_strategy=routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy),
            max_cost_eur=max_cost_eur,
            preferred_provider=preferred_provider,
            fallback_provider=fallback_provider,
            user_id=user_id,
            session_id=session_id,
            processing_stage="started"
        )

        # Prepare context for next step (Step 49: RouteStrategy)
        result = {
            'provider_selection_initiated': True,
            'ready_for_routing': True,
            'messages': messages,
            'routing_strategy': routing_strategy,
            'max_cost_eur': max_cost_eur,
            'preferred_provider': preferred_provider,
            'fallback_provider': fallback_provider,
            'user_id': user_id,
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        rag_step_log(
            step=48,
            step_id='RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider',
            node_label='SelectProvider',
            category='providers',
            type='process',
            provider_selection_initiated=True,
            ready_for_routing=True,
            messages_count=len(messages),
            routing_strategy=routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy),
            max_cost_eur=max_cost_eur,
            preferred_provider=preferred_provider,
            processing_stage="completed"
        )

        return result

def step_51__cheap_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 51 — Select cheapest provider
    ID: RAG.providers.select.cheapest.provider
    Type: process | Category: providers | Node: CheapProvider

    Selects the cheapest LLM provider from available options within budget constraints.
    Receives context from Step 50 (StrategyType decision) and prepares for Step 55 (EstimateCost).

    Incoming: StrategyType (Step 50) with decision 'routing_to_cost_optimized'
    Outgoing: EstimateCost (Step 55)
    """
    from app.core.llm.factory import get_llm_factory
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(51, 'RAG.providers.select.cheapest.provider', 'CheapProvider', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get('messages', messages)
        if not messages:
            error_msg = 'Missing required parameter: messages'
            logger.error(f"STEP 51: {error_msg}")
            rag_step_log(
                step=51,
                step_id='RAG.providers.select.cheapest.provider',
                node_label='CheapProvider',
                category='providers',
                type='process',
                error=error_msg,
                provider_selected=False,
                processing_stage="failed"
            )
            return {
                'provider_selected': False,
                'error': error_msg,
                'provider': None,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Extract provider selection parameters
        max_cost_eur = params.get('max_cost_eur')
        preferred_provider = params.get('preferred_provider')
        fallback_provider = params.get('fallback_provider')
        routing_strategy = params.get('routing_strategy')

        # Additional context
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # Get the LLM factory and select cheapest provider using cost-optimized strategy
            factory = get_llm_factory()
            from app.core.llm.factory import RoutingStrategy
            provider = factory.get_optimal_provider(
                messages=messages,
                strategy=RoutingStrategy.COST_OPTIMIZED,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider
            )

            if not provider:
                # No provider available within budget
                logger.warning(
                    f"STEP 51: No cheap provider available within budget",
                    extra={
                        'step': 51,
                        'max_cost_eur': max_cost_eur,
                        'preferred_provider': preferred_provider,
                        'reason': 'no_provider_within_budget'
                    }
                )

                rag_step_log(
                    step=51,
                    step_id='RAG.providers.select.cheapest.provider',
                    node_label='CheapProvider',
                    category='providers',
                    type='process',
                    provider_selected=False,
                    reason='no_provider_within_budget',
                    max_cost_eur=max_cost_eur,
                    preferred_provider=preferred_provider,
                    processing_stage="completed"
                )

                return {
                    'provider_selected': False,
                    'provider': None,
                    'reason': 'no_provider_within_budget',
                    'max_cost_eur': max_cost_eur,
                    'preferred_provider': preferred_provider,
                    'messages': messages,
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Extract provider details
            provider_type = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
            model = getattr(provider, 'model', 'unknown')
            cost_per_token = getattr(provider, 'cost_per_token', 0.0)

            logger.info(
                f"STEP 51: Cheapest provider selected successfully",
                extra={
                    'step': 51,
                    'provider_type': provider_type,
                    'model': model,
                    'cost_per_token': cost_per_token,
                    'max_cost_eur': max_cost_eur,
                    'preferred_provider': preferred_provider
                }
            )

            rag_step_log(
                step=51,
                step_id='RAG.providers.select.cheapest.provider',
                node_label='CheapProvider',
                category='providers',
                type='process',
                provider_selected=True,
                provider_type=provider_type,
                model=model,
                cost_per_token=cost_per_token,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider,
                fallback_provider=fallback_provider,
                user_id=user_id,
                session_id=session_id,
                processing_stage="started"
            )

            # Prepare result for Step 55 (EstimateCost)
            result = {
                'provider_selected': True,
                'ready_for_cost_estimation': True,
                'provider': provider,
                'provider_type': provider_type,
                'model': model,
                'cost_per_token': cost_per_token,
                'max_cost_eur': max_cost_eur,
                'preferred_provider': preferred_provider,
                'fallback_provider': fallback_provider,
                'messages': messages,
                'routing_strategy': routing_strategy,
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=51,
                step_id='RAG.providers.select.cheapest.provider',
                node_label='CheapProvider',
                category='providers',
                type='process',
                provider_selected=True,
                ready_for_cost_estimation=True,
                provider_type=provider_type,
                model=model,
                cost_per_token=cost_per_token,
                processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"STEP 51: Failed to select cheapest provider",
                extra={
                    'step': 51,
                    'error': error_msg,
                    'max_cost_eur': max_cost_eur
                }
            )

            rag_step_log(
                step=51,
                step_id='RAG.providers.select.cheapest.provider',
                node_label='CheapProvider',
                category='providers',
                type='process',
                error=error_msg,
                provider_selected=False,
                processing_stage="failed"
            )

            return {
                'provider_selected': False,
                'error': error_msg,
                'provider': None,
                'max_cost_eur': max_cost_eur,
                'messages': messages,
                'timestamp': datetime.utcnow().isoformat()
            }

def step_52__best_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 52 — Select best provider
    ID: RAG.providers.select.best.provider
    Type: process | Category: providers | Node: BestProvider

    Selects the best quality LLM provider from available options.
    Receives context from Step 50 (StrategyType decision) and prepares for Step 55 (EstimateCost).

    Incoming: StrategyType (Step 50) with decision 'routing_to_quality_first'
    Outgoing: EstimateCost (Step 55)
    """
    from app.core.llm.factory import get_llm_factory, RoutingStrategy
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(52, 'RAG.providers.select.best.provider', 'BestProvider', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get('messages', messages)
        if not messages:
            error_msg = 'Missing required parameter: messages'
            logger.error(f"STEP 52: {error_msg}")
            rag_step_log(
                step=52, step_id='RAG.providers.select.best.provider', node_label='BestProvider',
                category='providers', type='process', error=error_msg, provider_selected=False, processing_stage="failed"
            )
            return {'provider_selected': False, 'error': error_msg, 'provider': None, 'timestamp': datetime.utcnow().isoformat()}

        # Extract provider selection parameters
        max_cost_eur = params.get('max_cost_eur')
        preferred_provider = params.get('preferred_provider')
        fallback_provider = params.get('fallback_provider')
        routing_strategy = params.get('routing_strategy')
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # Get the LLM factory and select best provider using quality-first strategy
            factory = get_llm_factory()
            provider = factory.get_optimal_provider(
                messages=messages,
                strategy=RoutingStrategy.QUALITY_FIRST,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider
            )

            if not provider:
                logger.warning(f"STEP 52: No best provider available", extra={'step': 52, 'max_cost_eur': max_cost_eur})
                rag_step_log(
                    step=52, step_id='RAG.providers.select.best.provider', node_label='BestProvider',
                    category='providers', type='process', provider_selected=False, reason='no_provider_available',
                    max_cost_eur=max_cost_eur, processing_stage="completed"
                )
                return {
                    'provider_selected': False, 'provider': None, 'reason': 'no_provider_available',
                    'max_cost_eur': max_cost_eur, 'messages': messages, 'timestamp': datetime.utcnow().isoformat()
                }

            # Extract provider details
            provider_type = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
            model = getattr(provider, 'model', 'unknown')
            cost_per_token = getattr(provider, 'cost_per_token', 0.0)

            logger.info(f"STEP 52: Best provider selected successfully", extra={
                'step': 52, 'provider_type': provider_type, 'model': model, 'cost_per_token': cost_per_token
            })

            # Prepare result for Step 55 (EstimateCost)
            result = {
                'provider_selected': True, 'ready_for_cost_estimation': True, 'provider': provider,
                'provider_type': provider_type, 'model': model, 'cost_per_token': cost_per_token,
                'max_cost_eur': max_cost_eur, 'preferred_provider': preferred_provider,
                'fallback_provider': fallback_provider, 'messages': messages, 'routing_strategy': routing_strategy,
                'user_id': user_id, 'session_id': session_id, 'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=52, step_id='RAG.providers.select.best.provider', node_label='BestProvider',
                category='providers', type='process', provider_selected=True, ready_for_cost_estimation=True,
                provider_type=provider_type, model=model, cost_per_token=cost_per_token, processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"STEP 52: Failed to select best provider", extra={'step': 52, 'error': error_msg})
            rag_step_log(
                step=52, step_id='RAG.providers.select.best.provider', node_label='BestProvider',
                category='providers', type='process', error=error_msg, provider_selected=False, processing_stage="failed"
            )
            return {
                'provider_selected': False, 'error': error_msg, 'provider': None,
                'messages': messages, 'timestamp': datetime.utcnow().isoformat()
            }

def step_53__balance_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 53 — Balance cost and quality
    ID: RAG.providers.balance.cost.and.quality
    Type: process | Category: providers | Node: BalanceProvider

    Selects a balanced LLM provider optimizing both cost and quality.
    Receives context from Step 50 (StrategyType decision) and prepares for Step 55 (EstimateCost).

    Incoming: StrategyType (Step 50) with decision 'routing_to_balanced'
    Outgoing: EstimateCost (Step 55)
    """
    from app.core.llm.factory import get_llm_factory, RoutingStrategy
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(53, 'RAG.providers.balance.cost.and.quality', 'BalanceProvider', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get('messages', messages)
        if not messages:
            error_msg = 'Missing required parameter: messages'
            logger.error(f"STEP 53: {error_msg}")
            rag_step_log(
                step=53, step_id='RAG.providers.balance.cost.and.quality', node_label='BalanceProvider',
                category='providers', type='process', error=error_msg, provider_selected=False, processing_stage="failed"
            )
            return {'provider_selected': False, 'error': error_msg, 'provider': None, 'timestamp': datetime.utcnow().isoformat()}

        # Extract provider selection parameters
        max_cost_eur = params.get('max_cost_eur')
        preferred_provider = params.get('preferred_provider')
        fallback_provider = params.get('fallback_provider')
        routing_strategy = params.get('routing_strategy')
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # Get the LLM factory and select balanced provider
            factory = get_llm_factory()
            provider = factory.get_optimal_provider(
                messages=messages,
                strategy=RoutingStrategy.BALANCED,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider
            )

            if not provider:
                logger.warning(f"STEP 53: No balanced provider available", extra={'step': 53, 'max_cost_eur': max_cost_eur})
                rag_step_log(
                    step=53, step_id='RAG.providers.balance.cost.and.quality', node_label='BalanceProvider',
                    category='providers', type='process', provider_selected=False, reason='no_provider_available',
                    max_cost_eur=max_cost_eur, processing_stage="completed"
                )
                return {
                    'provider_selected': False, 'provider': None, 'reason': 'no_provider_available',
                    'max_cost_eur': max_cost_eur, 'messages': messages, 'timestamp': datetime.utcnow().isoformat()
                }

            # Extract provider details
            provider_type = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
            model = getattr(provider, 'model', 'unknown')
            cost_per_token = getattr(provider, 'cost_per_token', 0.0)

            logger.info(f"STEP 53: Balanced provider selected successfully", extra={
                'step': 53, 'provider_type': provider_type, 'model': model, 'cost_per_token': cost_per_token
            })

            # Prepare result for Step 55 (EstimateCost)
            result = {
                'provider_selected': True, 'ready_for_cost_estimation': True, 'provider': provider,
                'provider_type': provider_type, 'model': model, 'cost_per_token': cost_per_token,
                'max_cost_eur': max_cost_eur, 'preferred_provider': preferred_provider,
                'fallback_provider': fallback_provider, 'messages': messages, 'routing_strategy': routing_strategy,
                'user_id': user_id, 'session_id': session_id, 'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=53, step_id='RAG.providers.balance.cost.and.quality', node_label='BalanceProvider',
                category='providers', type='process', provider_selected=True, ready_for_cost_estimation=True,
                provider_type=provider_type, model=model, cost_per_token=cost_per_token, processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"STEP 53: Failed to select balanced provider", extra={'step': 53, 'error': error_msg})
            rag_step_log(
                step=53, step_id='RAG.providers.balance.cost.and.quality', node_label='BalanceProvider',
                category='providers', type='process', error=error_msg, provider_selected=False, processing_stage="failed"
            )
            return {
                'provider_selected': False, 'error': error_msg, 'provider': None,
                'messages': messages, 'timestamp': datetime.utcnow().isoformat()
            }

def step_54__primary_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 54 — Use primary provider
    ID: RAG.providers.use.primary.provider
    Type: process | Category: providers | Node: PrimaryProvider

    Uses the primary provider with failover capability.
    Receives context from Step 50 (StrategyType decision) and prepares for Step 55 (EstimateCost).

    Incoming: StrategyType (Step 50) with decision 'routing_to_failover'
    Outgoing: EstimateCost (Step 55)
    """
    from app.core.llm.factory import get_llm_factory, RoutingStrategy
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(54, 'RAG.providers.use.primary.provider', 'PrimaryProvider', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get('messages', messages)
        if not messages:
            error_msg = 'Missing required parameter: messages'
            logger.error(f"STEP 54: {error_msg}")
            rag_step_log(
                step=54, step_id='RAG.providers.use.primary.provider', node_label='PrimaryProvider',
                category='providers', type='process', error=error_msg, provider_selected=False, processing_stage="failed"
            )
            return {'provider_selected': False, 'error': error_msg, 'provider': None, 'timestamp': datetime.utcnow().isoformat()}

        # Extract provider selection parameters
        max_cost_eur = params.get('max_cost_eur')
        preferred_provider = params.get('preferred_provider')
        fallback_provider = params.get('fallback_provider')
        routing_strategy = params.get('routing_strategy')
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # Get the LLM factory and select primary provider with failover strategy
            factory = get_llm_factory()
            provider = factory.get_optimal_provider(
                messages=messages,
                strategy=RoutingStrategy.FAILOVER,
                max_cost_eur=max_cost_eur,
                preferred_provider=preferred_provider
            )

            if not provider:
                logger.warning(f"STEP 54: No primary provider available", extra={'step': 54, 'max_cost_eur': max_cost_eur})
                rag_step_log(
                    step=54, step_id='RAG.providers.use.primary.provider', node_label='PrimaryProvider',
                    category='providers', type='process', provider_selected=False, reason='no_provider_available',
                    max_cost_eur=max_cost_eur, processing_stage="completed"
                )
                return {
                    'provider_selected': False, 'provider': None, 'reason': 'no_provider_available',
                    'max_cost_eur': max_cost_eur, 'messages': messages, 'timestamp': datetime.utcnow().isoformat()
                }

            # Extract provider details
            provider_type = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
            model = getattr(provider, 'model', 'unknown')
            cost_per_token = getattr(provider, 'cost_per_token', 0.0)

            logger.info(f"STEP 54: Primary provider selected successfully", extra={
                'step': 54, 'provider_type': provider_type, 'model': model, 'cost_per_token': cost_per_token
            })

            # Prepare result for Step 55 (EstimateCost)
            result = {
                'provider_selected': True, 'ready_for_cost_estimation': True, 'provider': provider,
                'provider_type': provider_type, 'model': model, 'cost_per_token': cost_per_token,
                'max_cost_eur': max_cost_eur, 'preferred_provider': preferred_provider,
                'fallback_provider': fallback_provider, 'messages': messages, 'routing_strategy': routing_strategy,
                'user_id': user_id, 'session_id': session_id, 'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=54, step_id='RAG.providers.use.primary.provider', node_label='PrimaryProvider',
                category='providers', type='process', provider_selected=True, ready_for_cost_estimation=True,
                provider_type=provider_type, model=model, cost_per_token=cost_per_token, processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"STEP 54: Failed to select primary provider", extra={'step': 54, 'error': error_msg})
            rag_step_log(
                step=54, step_id='RAG.providers.use.primary.provider', node_label='PrimaryProvider',
                category='providers', type='process', error=error_msg, provider_selected=False, processing_stage="failed"
            )
            return {
                'provider_selected': False, 'error': error_msg, 'provider': None,
                'messages': messages, 'timestamp': datetime.utcnow().isoformat()
            }

def step_55__estimate_cost(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 55 — CostCalculator.estimate_cost Calculate query cost
    ID: RAG.providers.costcalculator.estimate.cost.calculate.query.cost
    Type: process | Category: providers | Node: EstimateCost

    Estimates the cost of processing the query with the selected provider.
    Receives context from Steps 51-54 (provider selection) and prepares for Step 56 (CostCheck).

    Incoming: CheapProvider, BestProvider, BalanceProvider, PrimaryProvider (Steps 51-54)
    Outgoing: CostCheck (Step 56)
    """
    from app.core.logging import logger
    from datetime import datetime
    import tiktoken

    with rag_step_timer(55, 'RAG.providers.costcalculator.estimate.cost.calculate.query.cost', 'EstimateCost', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get('messages', messages)
        provider = params.get('provider')
        if not messages or not provider:
            error_msg = f'Missing required parameters: messages={bool(messages)}, provider={bool(provider)}'
            logger.error(f"STEP 55: {error_msg}")
            rag_step_log(
                step=55, step_id='RAG.providers.costcalculator.estimate.cost.calculate.query.cost', node_label='EstimateCost',
                category='providers', type='process', error=error_msg, cost_estimated=False, processing_stage="failed"
            )
            return {'cost_estimated': False, 'error': error_msg, 'estimated_cost': 0.0, 'timestamp': datetime.utcnow().isoformat()}

        # Extract provider and cost parameters
        provider_type = params.get('provider_type', 'unknown')
        model = params.get('model', 'unknown')
        cost_per_token = params.get('cost_per_token', 0.0)
        max_cost_eur = params.get('max_cost_eur')
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # Estimate token count for the messages
            total_tokens = 0

            # Simple token estimation - in production this would use the actual tokenizer
            for message in messages:
                if isinstance(message, dict):
                    content = message.get('content', '')
                elif hasattr(message, 'content'):
                    content = message.content
                else:
                    content = str(message)

                # Rough estimation: ~4 characters per token
                estimated_tokens = len(content) // 4 + 10  # +10 for role/formatting tokens
                total_tokens += estimated_tokens

            # Add response estimation (assume similar length to input)
            estimated_response_tokens = total_tokens
            total_tokens += estimated_response_tokens

            # Calculate estimated cost
            estimated_cost = total_tokens * cost_per_token
            estimated_cost_eur = estimated_cost  # Assuming cost_per_token is already in EUR

            logger.info(f"STEP 55: Cost estimation completed", extra={
                'step': 55, 'provider_type': provider_type, 'model': model, 'total_tokens': total_tokens,
                'cost_per_token': cost_per_token, 'estimated_cost_eur': estimated_cost_eur
            })

            # Prepare result for Step 56 (CostCheck)
            result = {
                'cost_estimated': True, 'ready_for_cost_check': True,
                'estimated_cost': estimated_cost_eur, 'estimated_tokens': total_tokens,
                'cost_per_token': cost_per_token, 'max_cost_eur': max_cost_eur,
                'provider': provider, 'provider_type': provider_type, 'model': model,
                'messages': messages, 'user_id': user_id, 'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=55, step_id='RAG.providers.costcalculator.estimate.cost.calculate.query.cost', node_label='EstimateCost',
                category='providers', type='process', cost_estimated=True, ready_for_cost_check=True,
                estimated_cost_eur=estimated_cost_eur, estimated_tokens=total_tokens, cost_per_token=cost_per_token,
                provider_type=provider_type, model=model, processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"STEP 55: Failed to estimate cost", extra={'step': 55, 'error': error_msg})
            rag_step_log(
                step=55, step_id='RAG.providers.costcalculator.estimate.cost.calculate.query.cost', node_label='EstimateCost',
                category='providers', type='process', error=error_msg, cost_estimated=False, processing_stage="failed"
            )
            return {
                'cost_estimated': False, 'error': error_msg, 'estimated_cost': 0.0,
                'messages': messages, 'timestamp': datetime.utcnow().isoformat()
            }

def step_56__cost_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 56 — Cost within budget?
    ID: RAG.providers.cost.within.budget
    Type: decision | Category: providers | Node: CostCheck

    Checks if the estimated cost is within the specified budget.
    Receives context from Step 55 (EstimateCost) and routes to Step 57 or Step 58.

    Incoming: EstimateCost (Step 55)
    Outgoing: CreateProvider (Step 57) if within budget, CheaperProvider (Step 58) if over budget
    """
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(56, 'RAG.providers.cost.within.budget', 'CostCheck', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        estimated_cost = params.get('estimated_cost', 0.0)
        max_cost_eur = params.get('max_cost_eur')

        # Extract additional context
        provider = params.get('provider')
        provider_type = params.get('provider_type')
        model = params.get('model')
        estimated_tokens = params.get('estimated_tokens')
        messages = params.get('messages', messages)
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        # Determine if cost is within budget
        within_budget = True
        decision = 'cost_within_budget'
        next_step = 'CreateProvider'

        if max_cost_eur is not None and estimated_cost > max_cost_eur:
            within_budget = False
            decision = 'cost_over_budget'
            next_step = 'CheaperProvider'

        logger.info(f"STEP 56: Cost check completed", extra={
            'step': 56, 'estimated_cost': estimated_cost, 'max_cost_eur': max_cost_eur,
            'within_budget': within_budget, 'decision': decision, 'next_step': next_step
        })

        # Prepare result
        result = {
            'within_budget': within_budget, 'decision': decision, 'next_step': next_step,
            'estimated_cost': estimated_cost, 'max_cost_eur': max_cost_eur,
            'cost_difference': (estimated_cost - max_cost_eur) if max_cost_eur else 0.0,
            'provider': provider, 'provider_type': provider_type, 'model': model,
            'estimated_tokens': estimated_tokens, 'messages': messages,
            'user_id': user_id, 'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        rag_step_log(
            step=56, step_id='RAG.providers.cost.within.budget', node_label='CostCheck',
            category='providers', type='decision', within_budget=within_budget, decision=decision,
            next_step=next_step, estimated_cost=estimated_cost, max_cost_eur=max_cost_eur,
            cost_difference=result['cost_difference'], provider_type=provider_type, model=model,
            estimated_tokens=estimated_tokens, processing_stage="completed"
        )

        return result

def step_57__create_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 57 — Create provider instance
    ID: RAG.providers.create.provider.instance
    Type: process | Category: providers | Node: CreateProvider

    Creates the final provider instance for query processing.
    Receives context from Step 56 (CostCheck) when cost is within budget.

    Incoming: CostCheck (Step 56) with decision 'cost_within_budget'
    Outgoing: Ready for query processing
    """
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(57, 'RAG.providers.create.provider.instance', 'CreateProvider', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        provider = params.get('provider')
        if not provider:
            error_msg = 'Missing required parameter: provider'
            logger.error(f"STEP 57: {error_msg}")
            rag_step_log(
                step=57, step_id='RAG.providers.create.provider.instance', node_label='CreateProvider',
                category='providers', type='process', error=error_msg, provider_created=False, processing_stage="failed"
            )
            return {'provider_created': False, 'error': error_msg, 'provider_instance': None, 'timestamp': datetime.utcnow().isoformat()}

        # Extract additional context
        provider_type = params.get('provider_type')
        model = params.get('model')
        estimated_cost = params.get('estimated_cost')
        estimated_tokens = params.get('estimated_tokens')
        messages = params.get('messages', messages)
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # The provider instance is already created from previous steps
            # This step confirms it's ready for use and finalizes the setup
            logger.info(f"STEP 57: Provider instance created successfully", extra={
                'step': 57, 'provider_type': provider_type, 'model': model,
                'estimated_cost': estimated_cost, 'estimated_tokens': estimated_tokens
            })

            # Prepare final result for query processing
            result = {
                'provider_created': True, 'ready_for_processing': True,
                'provider_instance': provider, 'provider_type': provider_type, 'model': model,
                'estimated_cost': estimated_cost, 'estimated_tokens': estimated_tokens,
                'messages': messages, 'user_id': user_id, 'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=57, step_id='RAG.providers.create.provider.instance', node_label='CreateProvider',
                category='providers', type='process', provider_created=True, ready_for_processing=True,
                provider_type=provider_type, model=model, estimated_cost=estimated_cost,
                estimated_tokens=estimated_tokens, processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"STEP 57: Failed to create provider instance", extra={'step': 57, 'error': error_msg})
            rag_step_log(
                step=57, step_id='RAG.providers.create.provider.instance', node_label='CreateProvider',
                category='providers', type='process', error=error_msg, provider_created=False, processing_stage="failed"
            )
            return {
                'provider_created': False, 'error': error_msg, 'provider_instance': None,
                'messages': messages, 'timestamp': datetime.utcnow().isoformat()
            }

def step_58__cheaper_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 58 — Select cheaper provider or fail
    ID: RAG.providers.select.cheaper.provider.or.fail
    Type: process | Category: providers | Node: CheaperProvider

    Attempts to select a cheaper provider when the estimated cost exceeds budget.
    Receives context from Step 56 (CostCheck) when cost is over budget.

    Incoming: CostCheck (Step 56) with decision 'cost_over_budget'
    Outgoing: Either a cheaper provider or failure
    """
    from app.core.llm.factory import get_llm_factory, RoutingStrategy
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(58, 'RAG.providers.select.cheaper.provider.or.fail', 'CheaperProvider', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters
        messages = params.get('messages', messages)
        max_cost_eur = params.get('max_cost_eur')
        if not messages:
            error_msg = 'Missing required parameter: messages'
            logger.error(f"STEP 58: {error_msg}")
            rag_step_log(
                step=58, step_id='RAG.providers.select.cheaper.provider.or.fail', node_label='CheaperProvider',
                category='providers', type='process', error=error_msg, cheaper_provider_found=False, processing_stage="failed"
            )
            return {'cheaper_provider_found': False, 'error': error_msg, 'provider': None, 'timestamp': datetime.utcnow().isoformat()}

        # Extract additional context
        original_estimated_cost = params.get('estimated_cost', 0.0)
        original_provider_type = params.get('provider_type')
        original_model = params.get('model')
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        try:
            # Try to find a cheaper provider by forcing cost-optimized strategy with stricter budget
            factory = get_llm_factory()

            # Reduce budget by 20% to ensure we get something cheaper
            reduced_budget = max_cost_eur * 0.8 if max_cost_eur else None

            cheaper_provider = factory.get_optimal_provider(
                messages=messages,
                strategy=RoutingStrategy.COST_OPTIMIZED,
                max_cost_eur=reduced_budget,
                preferred_provider=None  # Remove preference to allow cheapest option
            )

            if not cheaper_provider:
                # No cheaper provider available
                logger.warning(f"STEP 58: No cheaper provider available within budget", extra={
                    'step': 58, 'max_cost_eur': max_cost_eur, 'reduced_budget': reduced_budget,
                    'original_cost': original_estimated_cost
                })

                rag_step_log(
                    step=58, step_id='RAG.providers.select.cheaper.provider.or.fail', node_label='CheaperProvider',
                    category='providers', type='process', cheaper_provider_found=False, reason='no_cheaper_provider_available',
                    max_cost_eur=max_cost_eur, original_cost=original_estimated_cost, processing_stage="completed"
                )

                return {
                    'cheaper_provider_found': False, 'provider': None, 'reason': 'no_cheaper_provider_available',
                    'max_cost_eur': max_cost_eur, 'original_cost': original_estimated_cost,
                    'messages': messages, 'timestamp': datetime.utcnow().isoformat()
                }

            # Extract provider details
            provider_type = cheaper_provider.provider_type.value if hasattr(cheaper_provider.provider_type, 'value') else str(cheaper_provider.provider_type)
            model = getattr(cheaper_provider, 'model', 'unknown')
            cost_per_token = getattr(cheaper_provider, 'cost_per_token', 0.0)

            logger.info(f"STEP 58: Cheaper provider found successfully", extra={
                'step': 58, 'original_provider': original_provider_type, 'new_provider': provider_type,
                'original_model': original_model, 'new_model': model, 'new_cost_per_token': cost_per_token
            })

            # Prepare result - this provider will need to go through cost estimation again
            result = {
                'cheaper_provider_found': True, 'provider': cheaper_provider,
                'provider_type': provider_type, 'model': model, 'cost_per_token': cost_per_token,
                'max_cost_eur': max_cost_eur, 'reduced_budget': reduced_budget,
                'original_cost': original_estimated_cost, 'original_provider_type': original_provider_type,
                'original_model': original_model, 'messages': messages,
                'user_id': user_id, 'session_id': session_id,
                'needs_cost_recheck': True,  # Signal that this needs to go back to cost estimation
                'timestamp': datetime.utcnow().isoformat()
            }

            rag_step_log(
                step=58, step_id='RAG.providers.select.cheaper.provider.or.fail', node_label='CheaperProvider',
                category='providers', type='process', cheaper_provider_found=True,
                provider_type=provider_type, model=model, cost_per_token=cost_per_token,
                original_provider_type=original_provider_type, original_model=original_model,
                needs_cost_recheck=True, processing_stage="completed"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"STEP 58: Failed to select cheaper provider", extra={'step': 58, 'error': error_msg})
            rag_step_log(
                step=58, step_id='RAG.providers.select.cheaper.provider.or.fail', node_label='CheaperProvider',
                category='providers', type='process', error=error_msg, cheaper_provider_found=False, processing_stage="failed"
            )
            return {
                'cheaper_provider_found': False, 'error': error_msg, 'provider': None,
                'messages': messages, 'timestamp': datetime.utcnow().isoformat()
            }

def step_64__llmcall(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 64 — LLMProvider.chat_completion Make API call
    ID: RAG.providers.llmprovider.chat.completion.make.api.call
    Type: process | Category: providers | Node: LLMCall

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(64, 'RAG.providers.llmprovider.chat.completion.make.api.call', 'LLMCall', stage="start"):
        rag_step_log(step=64, step_id='RAG.providers.llmprovider.chat.completion.make.api.call', node_label='LLMCall',
                     category='providers', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=64, step_id='RAG.providers.llmprovider.chat.completion.make.api.call', node_label='LLMCall',
                     processing_stage="completed")
        return result

async def step_72__get_failover_provider(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 72 — Get FAILOVER provider
    ID: RAG.providers.get.failover.provider
    Type: process | Category: providers | Node: FailoverProvider

    Process step that selects a failover LLM provider when in production environment on the last retry.
    Uses FAILOVER routing strategy with increased cost limits to ensure reliability.
    """
    from app.core.logging import logger
    from app.core.config import settings
    from app.core.llm.factory import get_llm_provider, RoutingStrategy
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    conversation_messages = kwargs.get('messages') or ctx.get('messages', [])
    max_cost_eur = kwargs.get('max_cost_eur') or ctx.get('max_cost_eur') or settings.LLM_MAX_COST_EUR
    attempt_number = kwargs.get('attempt_number') or ctx.get('attempt_number', 0)
    max_retries = kwargs.get('max_retries') or ctx.get('max_retries', 3)
    environment = kwargs.get('environment') or ctx.get('environment')
    request_id = ctx.get('request_id', 'unknown')

    # Initialize result variables
    provider_obtained = False
    provider = None
    strategy = RoutingStrategy.FAILOVER
    failover_max_cost = max_cost_eur * 2  # Double cost limit for failover reliability
    provider_type = None
    model = None
    error = None
    is_failover = True

    # Log process start
    rag_step_log(
        step=72,
        step_id='RAG.providers.get.failover.provider',
        node_label='FailoverProvider',
        category='providers',
        type='process',
        processing_stage='started',
        request_id=request_id,
        strategy=strategy.value,
        max_cost_eur=failover_max_cost,
        attempt_number=attempt_number
    )

    try:
        # Get failover provider using FAILOVER strategy
        # Matches existing logic from graph.py:786-791
        logger.warning(
            f"attempting_fallback_provider",
            extra={
                'request_id': request_id,
                'step': 72,
                'strategy': strategy.value,
                'max_cost_eur': failover_max_cost,
                'original_max_cost': max_cost_eur,
                'attempt_number': attempt_number,
                'max_retries': max_retries
            }
        )

        provider = get_llm_provider(
            messages=conversation_messages,
            strategy=strategy,
            max_cost_eur=failover_max_cost
        )

        provider_obtained = True

        # Extract provider metadata
        if provider:
            provider_type = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
            model = provider.model

        logger.info(
            f"failover_provider_selected",
            extra={
                'request_id': request_id,
                'step': 72,
                'provider_type': provider_type,
                'model': model,
                'strategy': strategy.value,
                'max_cost_eur': failover_max_cost
            }
        )

    except Exception as e:
        # Failover provider selection failed
        error = str(e)
        provider_obtained = False
        provider = None

        logger.error(
            f"failover_provider_selection_failed",
            extra={
                'request_id': request_id,
                'step': 72,
                'error': error,
                'strategy': strategy.value,
                'max_cost_eur': failover_max_cost
            }
        )

    # Log process completion
    rag_step_log(
        step=72,
        step_id='RAG.providers.get.failover.provider',
        node_label='FailoverProvider',
        processing_stage='completed',
        request_id=request_id,
        provider_obtained=provider_obtained,
        strategy=strategy.value,
        provider_type=provider_type,
        model=model,
        max_cost_eur=failover_max_cost,
        is_failover=is_failover,
        error=error
    )

    # Build orchestration result
    result = {
        'provider_obtained': provider_obtained,
        'provider': provider,
        'strategy': strategy,
        'provider_type': provider_type,
        'model': model,
        'max_cost_eur': failover_max_cost,
        'original_max_cost': max_cost_eur,
        'is_failover': is_failover,
        'attempt_number': attempt_number,
        'max_retries': max_retries,
        'environment': environment,
        'error': error,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return result

async def step_73__retry_same(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 73 — Retry same provider
    ID: RAG.providers.retry.same.provider
    Type: process | Category: providers | Node: RetrySame

    Process step that retries the LLM call using the same provider (or failover provider if set).
    Increments the attempt counter and routes back to the LLM call step.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    provider = kwargs.get('provider') or ctx.get('provider')
    attempt_number = kwargs.get('attempt_number') or ctx.get('attempt_number', 0)
    max_retries = kwargs.get('max_retries') or ctx.get('max_retries', 3)
    conversation_messages = kwargs.get('messages') or ctx.get('messages', [])
    previous_errors = kwargs.get('previous_errors') or ctx.get('previous_errors', [])
    error = kwargs.get('error') or ctx.get('error')
    is_failover = kwargs.get('is_failover') or ctx.get('is_failover', False)
    request_id = ctx.get('request_id', 'unknown')

    # Initialize result variables
    retry_initiated = True
    next_attempt = attempt_number + 1  # Increment attempt number
    next_step = 'llm_call'  # Route back to LLM call
    provider_type = None
    model = None

    # Extract provider metadata
    if provider:
        provider_type = provider.provider_type.value if hasattr(provider.provider_type, 'value') else str(provider.provider_type)
        model = provider.model

    # Log process start
    rag_step_log(
        step=73,
        step_id='RAG.providers.retry.same.provider',
        node_label='RetrySame',
        category='providers',
        type='process',
        processing_stage='started',
        request_id=request_id,
        attempt_number=attempt_number,
        next_attempt=next_attempt,
        provider_type=provider_type,
        is_failover=is_failover
    )

    # Log retry initiation
    # Matches existing logic from graph.py:799 (continue)
    logger.info(
        f"retry_same_provider",
        extra={
            'request_id': request_id,
            'step': 73,
            'attempt_number': attempt_number,
            'next_attempt': next_attempt,
            'max_retries': max_retries,
            'provider_type': provider_type,
            'model': model,
            'is_failover': is_failover,
            'error': error
        }
    )

    # Log process completion
    rag_step_log(
        step=73,
        step_id='RAG.providers.retry.same.provider',
        node_label='RetrySame',
        processing_stage='completed',
        request_id=request_id,
        retry_initiated=retry_initiated,
        attempt_number=next_attempt,
        next_step=next_step,
        provider_type=provider_type,
        model=model,
        is_failover=is_failover
    )

    # Build orchestration result
    result = {
        'retry_initiated': retry_initiated,
        'attempt_number': next_attempt,
        'next_step': next_step,
        'provider': provider,
        'provider_type': provider_type,
        'model': model,
        'max_retries': max_retries,
        'messages': conversation_messages,
        'previous_errors': previous_errors,
        'is_failover': is_failover,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return result
