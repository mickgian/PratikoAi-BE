"""
Lightweight wiring registry for audit visibility.

This module contains only the static wiring registry without any heavy imports
or initialization code, allowing the audit to load node wiring information quickly.
"""

# Canonical step ID mapping (source of truth from rag_conformance.md)
STEP_IDS = {
    # Phase 6: Request/Privacy Lane
    1: "RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate",
    3: "RAG.platform.request.valid",
    4: "RAG.privacy.gdprcompliance.record.processing.log.data.processing",
    6: "RAG.privacy.privacy.anonymize.requests.enabled",
    7: "RAG.privacy.anonymizer.anonymize.text.anonymize.pii",
    8: "RAG.response.langgraphagent.get.response.initialize.workflow",
    9: "RAG.platform.pii.detected",
    10: "RAG.platform.logger.info.log.pii.anonymization",

    # Phase 8: Golden/KB Gates
    20: "RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe",
    24: "RAG.preflight.goldenset.match.by.signature.or.semantic",
    25: "RAG.golden.high.confidence.match.score.at.least.0.90",
    26: "RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes",
    27: "RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags",
    28: "RAG.golden.serve.golden.answer.with.citations",
    30: "RAG.response.return.chatresponse",

    # Phase 5: Provider Governance Lane
    48: "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider",
    49: "RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy",
    50: "RAG.platform.routing.strategy.type",
    51: "RAG.providers.select.cheapest.provider",
    52: "RAG.providers.select.best.provider",
    53: "RAG.providers.balance.cost.and.quality",
    54: "RAG.providers.use.primary.provider",
    55: "RAG.providers.costcalculator.estimate.cost.calculate.query.cost",
    56: "RAG.providers.cost.within.budget",
    57: "RAG.providers.create.provider.instance",
    58: "RAG.providers.select.cheaper.provider.or.fail",

    # Phase 4: Cache → LLM → Tools Lane
    59: "RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response",
    62: "RAG.cache.cache.hit",
    64: "RAG.providers.llmprovider.chat.completion.make.api.call",
    66: "RAG.cache.return.cached.response",
    67: "RAG.llm.llm.call.successful",
    68: "RAG.cache.cacheservice.cache.response.store.in.redis",
    69: "RAG.platform.another.attempt.allowed",
    70: "RAG.platform.prod.environment.and.last.retry",
    72: "RAG.providers.get.failover.provider",
    73: "RAG.providers.retry.same.provider",
    74: "RAG.metrics.usagetracker.track.track.api.usage",
    75: "RAG.response.response.has.tool.calls",
    79: "RAG.routing.tool.type",
    80: "RAG.kb.knowledgesearchtool.search.kb.on.demand",
    81: "RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements",
    82: "RAG.preflight.documentingesttool.process.process.attachments",
    83: "RAG.golden.faqtool.faq.query.query.golden.set",
    99: "RAG.platform.return.to.tool.caller",

    # Phase 7: Streaming/Response Lane
    104: "RAG.streaming.streaming.requested",
    105: "RAG.streaming.chatbotcontroller.chat.stream.setup.sse",
    106: "RAG.platform.create.async.generator",
    107: "RAG.preflight.singlepassstream.prevent.double.iteration",
    108: "RAG.streaming.write.sse.format.chunks",
    109: "RAG.streaming.streamingresponse.send.chunks",
    110: "RAG.platform.send.done.frame",
    111: "RAG.metrics.collect.usage.metrics",
    112: "RAG.response.return.response.to.user",
}

# Phase 4 wiring registry - tracks which nodes are wired in the graph
PHASE4_WIRED_NODES = {
    59: {"id": STEP_IDS[59], "name": "node_step_59", "incoming": [], "outgoing": [62]},
    62: {"id": STEP_IDS[62], "name": "node_step_62", "incoming": [59], "outgoing": [64, 66]},
    64: {"id": STEP_IDS[64], "name": "node_step_64", "incoming": [62, 72, 73], "outgoing": [67]},
    66: {"id": STEP_IDS[66], "name": "node_step_66", "incoming": [62], "outgoing": []},
    67: {"id": STEP_IDS[67], "name": "node_step_67", "incoming": [64], "outgoing": [68, 69]},
    68: {"id": STEP_IDS[68], "name": "node_step_68", "incoming": [67], "outgoing": [74]},
    69: {"id": STEP_IDS[69], "name": "node_step_69", "incoming": [67], "outgoing": [70]},
    70: {"id": STEP_IDS[70], "name": "node_step_70", "incoming": [69], "outgoing": [72, 73]},
    72: {"id": STEP_IDS[72], "name": "node_step_72", "incoming": [70], "outgoing": [64]},
    73: {"id": STEP_IDS[73], "name": "node_step_73", "incoming": [70], "outgoing": [64]},
    74: {"id": STEP_IDS[74], "name": "node_step_74", "incoming": [68], "outgoing": [75]},
    75: {"id": STEP_IDS[75], "name": "node_step_75", "incoming": [74], "outgoing": [79]},
    79: {"id": STEP_IDS[79], "name": "node_step_79", "incoming": [75], "outgoing": [80, 81, 82, 83]},
    80: {"id": STEP_IDS[80], "name": "node_step_80", "incoming": [79], "outgoing": [99]},
    81: {"id": STEP_IDS[81], "name": "node_step_81", "incoming": [79], "outgoing": [99]},
    82: {"id": STEP_IDS[82], "name": "node_step_82", "incoming": [79], "outgoing": [99]},
    83: {"id": STEP_IDS[83], "name": "node_step_83", "incoming": [79], "outgoing": [99]},
    99: {"id": STEP_IDS[99], "name": "node_step_99", "incoming": [80, 81, 82, 83], "outgoing": []},
}

# Phase 5 wiring registry - Provider Governance Lane
PHASE5_WIRED_NODES = {
    48: {"id": STEP_IDS[48], "name": "node_step_48", "incoming": [], "outgoing": [49]},
    49: {"id": STEP_IDS[49], "name": "node_step_49", "incoming": [48], "outgoing": [50]},
    50: {"id": STEP_IDS[50], "name": "node_step_50", "incoming": [49], "outgoing": [51, 52, 53, 54]},
    51: {"id": STEP_IDS[51], "name": "node_step_51", "incoming": [50], "outgoing": [55]},
    52: {"id": STEP_IDS[52], "name": "node_step_52", "incoming": [50], "outgoing": [55]},
    53: {"id": STEP_IDS[53], "name": "node_step_53", "incoming": [50], "outgoing": [55]},
    54: {"id": STEP_IDS[54], "name": "node_step_54", "incoming": [50], "outgoing": [55]},
    55: {"id": STEP_IDS[55], "name": "node_step_55", "incoming": [51, 52, 53, 54, 58], "outgoing": [56]},
    56: {"id": STEP_IDS[56], "name": "node_step_56", "incoming": [55], "outgoing": [57, 58]},
    57: {"id": STEP_IDS[57], "name": "node_step_57", "incoming": [56], "outgoing": [59]},
    58: {"id": STEP_IDS[58], "name": "node_step_58", "incoming": [56], "outgoing": [55]},
}

# Phase 6 wiring registry - Request/Privacy Lane
PHASE6_WIRED_NODES = {
    1: {"id": STEP_IDS[1], "name": "node_step_1", "incoming": [], "outgoing": [3]},
    3: {"id": STEP_IDS[3], "name": "node_step_3", "incoming": [1], "outgoing": [4]},
    4: {"id": STEP_IDS[4], "name": "node_step_4", "incoming": [3], "outgoing": [6]},
    6: {"id": STEP_IDS[6], "name": "node_step_6", "incoming": [4], "outgoing": [7]},
    7: {"id": STEP_IDS[7], "name": "node_step_7", "incoming": [6], "outgoing": [9]},
    9: {"id": STEP_IDS[9], "name": "node_step_9", "incoming": [7], "outgoing": [10]},
    10: {"id": STEP_IDS[10], "name": "node_step_10", "incoming": [9], "outgoing": [8]},
    8: {"id": STEP_IDS[8], "name": "node_step_8", "incoming": [10], "outgoing": []},
}

# Phase 7 wiring registry - Streaming/Response Lane
PHASE7_WIRED_NODES = {
    104: {"id": STEP_IDS[104], "name": "node_step_104", "incoming": [], "outgoing": [105, 111]},
    105: {"id": STEP_IDS[105], "name": "node_step_105", "incoming": [104], "outgoing": [106]},
    106: {"id": STEP_IDS[106], "name": "node_step_106", "incoming": [105], "outgoing": [107]},
    107: {"id": STEP_IDS[107], "name": "node_step_107", "incoming": [106], "outgoing": [108]},
    108: {"id": STEP_IDS[108], "name": "node_step_108", "incoming": [107], "outgoing": [109]},
    109: {"id": STEP_IDS[109], "name": "node_step_109", "incoming": [108], "outgoing": [110]},
    110: {"id": STEP_IDS[110], "name": "node_step_110", "incoming": [109], "outgoing": [111]},
    111: {"id": STEP_IDS[111], "name": "node_step_111", "incoming": [104, 110], "outgoing": [112]},
    112: {"id": STEP_IDS[112], "name": "node_step_112", "incoming": [111], "outgoing": []},
}

# Phase 8 wiring registry - Golden/KB Gates
PHASE8_WIRED_NODES = {
    20: {"id": STEP_IDS[20], "name": "node_step_20", "incoming": [], "outgoing": [24]},
    24: {"id": STEP_IDS[24], "name": "node_step_24", "incoming": [20], "outgoing": [25]},
    25: {"id": STEP_IDS[25], "name": "node_step_25", "incoming": [24], "outgoing": [26]},
    26: {"id": STEP_IDS[26], "name": "node_step_26", "incoming": [25], "outgoing": [27]},
    27: {"id": STEP_IDS[27], "name": "node_step_27", "incoming": [26], "outgoing": [28]},
    28: {"id": STEP_IDS[28], "name": "node_step_28", "incoming": [27], "outgoing": [30]},
    30: {"id": STEP_IDS[30], "name": "node_step_30", "incoming": [28], "outgoing": []},
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

def initialize_phase7_registry() -> None:
    """Initialize Phase 7 nodes in the wiring registry."""
    WIRED_NODES.update(PHASE7_WIRED_NODES)

def initialize_phase8_registry() -> None:
    """Initialize Phase 8 nodes in the wiring registry."""
    WIRED_NODES.update(PHASE8_WIRED_NODES)

def track_edge(from_step: int, to_step: int) -> None:
    """Track an edge between two steps in the wiring registry."""
    if from_step in WIRED_NODES:
        WIRED_NODES[from_step]["outgoing"] = sorted(set(WIRED_NODES[from_step]["outgoing"] + [to_step]))
    if to_step in WIRED_NODES:
        WIRED_NODES[to_step]["incoming"] = sorted(set(WIRED_NODES[to_step]["incoming"] + [from_step]))

def get_wired_nodes_snapshot() -> dict[int, dict]:
    """Return a shallow copy of wired nodes registry to avoid mutation."""
    return {k: dict(v) for k, v in WIRED_NODES.items()}

def get_wired_ids() -> set[str]:
    """Return the set of all wired step IDs."""
    return {node["id"] for node in WIRED_NODES.values()}

def get_step_id(step: int) -> str | None:
    """Get the canonical ID for a step number."""
    return STEP_IDS.get(step)