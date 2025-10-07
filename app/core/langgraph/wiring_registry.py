"""
Lightweight wiring registry for audit visibility.

This module contains only the static wiring registry without any heavy imports
or initialization code, allowing the audit to load node wiring information quickly.
"""

# Phase 4 wiring registry - tracks which nodes are wired in the graph
PHASE4_WIRED_NODES = {
    59: {"id": "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response", "name": "node_step_59", "incoming": [], "outgoing": [62]},
    62: {"id": "RAG.cache.cache.hit", "name": "node_step_62", "incoming": [59], "outgoing": [64, 66]},
    64: {"id": "RAG.providers.llmprovider.chat.completion.make.api.call", "name": "node_step_64", "incoming": [62, 72, 73], "outgoing": [67]},
    66: {"id": "RAG.cache.return.cached.response", "name": "node_step_66", "incoming": [62], "outgoing": []},
    67: {"id": "RAG.llm.llm.call.successful", "name": "node_step_67", "incoming": [64], "outgoing": [68, 69]},
    68: {"id": "RAG.cache.cacheservice.cache.response.store.in.redis", "name": "node_step_68", "incoming": [67], "outgoing": [74]},
    69: {"id": "RAG.platform.another.attempt.allowed", "name": "node_step_69", "incoming": [67], "outgoing": [70]},
    70: {"id": "RAG.platform.prod.environment.and.last.retry", "name": "node_step_70", "incoming": [69], "outgoing": [72, 73]},
    72: {"id": "RAG.providers.get.failover.provider", "name": "node_step_72", "incoming": [70], "outgoing": [64]},
    73: {"id": "RAG.providers.retry.same.provider", "name": "node_step_73", "incoming": [70], "outgoing": [64]},
    74: {"id": "RAG.metrics.usagetracker.track.track.api.usage", "name": "node_step_74", "incoming": [68], "outgoing": [75]},
    75: {"id": "RAG.platform.tool.check", "name": "node_step_75", "incoming": [74], "outgoing": [79]},
    79: {"id": "RAG.routing.tool.type", "name": "node_step_79", "incoming": [75], "outgoing": [80, 81, 82, 83]},
    80: {"id": "RAG.kb.query.tool", "name": "node_step_80", "incoming": [79], "outgoing": [99]},
    81: {"id": "RAG.ccnl.query.tool", "name": "node_step_81", "incoming": [79], "outgoing": [99]},
    82: {"id": "RAG.docs.ingest.tool", "name": "node_step_82", "incoming": [79], "outgoing": [99]},
    83: {"id": "RAG.faq.query.tool", "name": "node_step_83", "incoming": [79], "outgoing": [99]},
    99: {"id": "RAG.platform.return.to.tool.caller", "name": "node_step_99", "incoming": [80, 81, 82, 83], "outgoing": []},
}

# Phase 5 wiring registry - Provider Governance Lane
PHASE5_WIRED_NODES = {
    48: {"id": "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider", "name": "node_step_48", "incoming": [], "outgoing": [49]},
    49: {"id": "RAG.platform.routing.strategy", "name": "node_step_49", "incoming": [48], "outgoing": [50]},
    50: {"id": "RAG.platform.routing.strategy.type", "name": "node_step_50", "incoming": [49], "outgoing": [51, 52, 53, 54]},
    51: {"id": "RAG.providers.select.cheapest.provider", "name": "node_step_51", "incoming": [50], "outgoing": [55]},
    52: {"id": "RAG.providers.select.best.provider", "name": "node_step_52", "incoming": [50], "outgoing": [55]},
    53: {"id": "RAG.providers.balance.cost.and.quality", "name": "node_step_53", "incoming": [50], "outgoing": [55]},
    54: {"id": "RAG.providers.use.primary.provider", "name": "node_step_54", "incoming": [50], "outgoing": [55]},
    55: {"id": "RAG.providers.costcalculator.estimate.cost.calculate.query.cost", "name": "node_step_55", "incoming": [51, 52, 53, 54, 58], "outgoing": [56]},
    56: {"id": "RAG.providers.cost.check", "name": "node_step_56", "incoming": [55], "outgoing": [57, 58]},
    57: {"id": "RAG.providers.create.provider.instance", "name": "node_step_57", "incoming": [56], "outgoing": [59]},
    58: {"id": "RAG.providers.find.cheaper.provider", "name": "node_step_58", "incoming": [56], "outgoing": [55]},
}

# Phase 6 wiring registry - Request/Privacy Lane
PHASE6_WIRED_NODES = {
    1: {"id": "RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate", "name": "node_step_1", "incoming": [], "outgoing": [3]},
    3: {"id": "RAG.platform.request.valid", "name": "node_step_3", "incoming": [1], "outgoing": [4]},
    4: {"id": "RAG.privacy.gdprcompliance.record.processing.log.data.processing", "name": "node_step_4", "incoming": [3], "outgoing": [6]},
    6: {"id": "RAG.privacy.privacy.anonymize.requests.enabled", "name": "node_step_6", "incoming": [4], "outgoing": [7]},
    7: {"id": "RAG.privacy.anonymizer.anonymize.text.anonymize.pii", "name": "node_step_7", "incoming": [6], "outgoing": [9]},
    9: {"id": "RAG.platform.pii.detected", "name": "node_step_9", "incoming": [7], "outgoing": [10]},
    10: {"id": "RAG.platform.logger.info.log.pii.anonymization", "name": "node_step_10", "incoming": [9], "outgoing": [8]},
    8: {"id": "RAG.response.langgraphagent.get.response.initialize.workflow", "name": "node_step_8", "incoming": [10], "outgoing": []},
}

# Global wiring registry (combined view)
WIRED_NODES: dict[int, dict] = {}

def initialize_phase4_registry() -> None:
    """Initialize Phase 4 nodes in the wiring registry."""
    WIRED_NODES.update(PHASE4_WIRED_NODES)

def initialize_phase5_registry() -> None:
    """Initialize Phase 5 nodes in the wiring registry."""
    WIRED_NODES.update(PHASE5_WIRED_NODES)

def initialize_phase6_registry() -> None:
    """Initialize Phase 6 nodes in the wiring registry."""
    WIRED_NODES.update(PHASE6_WIRED_NODES)

def track_edge(from_step: int, to_step: int) -> None:
    """Track an edge between two steps in the wiring registry."""
    if from_step in WIRED_NODES:
        WIRED_NODES[from_step]["outgoing"] = sorted(set(WIRED_NODES[from_step]["outgoing"] + [to_step]))
    if to_step in WIRED_NODES:
        WIRED_NODES[to_step]["incoming"] = sorted(set(WIRED_NODES[to_step]["incoming"] + [from_step]))

def get_wired_nodes_snapshot() -> dict[int, dict]:
    """Return a shallow copy of wired nodes registry to avoid mutation."""
    return {k: dict(v) for k, v in WIRED_NODES.items()}