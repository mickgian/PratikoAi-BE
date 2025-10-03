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

def get_wired_nodes_snapshot() -> dict[int, dict]:
    """Return a shallow copy of wired nodes registry to avoid mutation."""
    return {k: dict(v) for k, v in PHASE4_WIRED_NODES.items()}