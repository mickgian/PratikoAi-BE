# RAG Conformance Dashboard

This dashboard tracks the implementation status of each step in the PratikoAI RAG blueprint.
It is automatically generated from the Mermaid diagram using append-only step numbering.
Each step should be audited and its documentation filled during the conformance review.

## Audit Summary

**Implementation Status Overview (Tiered Graph Hybrid):**

**Node Steps** (Runtime boundaries - must be wired):
- ✅ Implemented & Wired: 25 steps
- 🔌 Not Wired: 2 steps
- ❌ Missing: 0 steps
- Total Node steps: 27

**Internal Steps** (Pure transforms - implementation only):
- 🔌 Implemented: 108 steps
- ❌ Missing: 0 steps
- Total Internal steps: 108

**Overall Statistics:**
- ✅ Fully Functional: 25 steps
- 🔌 Implemented (internal) or Not Wired: 110 steps
- ❌ Missing: 0 steps
- Total steps: 135
## Step Registry

| Step | ID | Node | Type | Category | Owner | Doc |
|------|----|----|------|----------|-------|-----|
| 1 | RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate | ValidateRequest | process | platform | ❌ | [📄](steps/STEP-1-RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate.md) |
| 2 | RAG.platform.user.submits.query.via.post.api.v1.chat | Start | startEnd | platform | ❌ | [📄](steps/STEP-2-RAG.platform.user.submits.query.via.post.api.v1.chat.md) |
| 3 | RAG.platform.request.valid | ValidCheck | decision | platform | ❌ | [📄](steps/STEP-3-RAG.platform.request.valid.md) |
| 4 | RAG.privacy.gdprcompliance.record.processing.log.data.processing | GDPRLog | process | privacy | 🔌 | [📄](steps/STEP-4-RAG.privacy.gdprcompliance.record.processing.log.data.processing.md) |
| 5 | RAG.platform.return.400.bad.request | Error400 | error | platform | ❌ | [📄](steps/STEP-5-RAG.platform.return.400.bad.request.md) |
| 6 | RAG.privacy.privacy.anonymize.requests.enabled | PrivacyCheck | decision | privacy | 🔌 | [📄](steps/STEP-6-RAG.privacy.privacy.anonymize.requests.enabled.md) |
| 7 | RAG.privacy.anonymizer.anonymize.text.anonymize.pii | AnonymizeText | process | privacy | 🟡 | [📄](steps/STEP-7-RAG.privacy.anonymizer.anonymize.text.anonymize.pii.md) |
| 8 | RAG.response.langgraphagent.get.response.initialize.workflow | InitAgent | process | response | ❌ | [📄](steps/STEP-8-RAG.response.langgraphagent.get.response.initialize.workflow.md) |
| 9 | RAG.platform.pii.detected | PIICheck | decision | platform | ❌ | [📄](steps/STEP-9-RAG.platform.pii.detected.md) |
| 10 | RAG.platform.logger.info.log.pii.anonymization | LogPII | process | platform | ❌ | [📄](steps/STEP-10-RAG.platform.logger.info.log.pii.anonymization.md) |
| 11 | RAG.platform.langgraphagent.chat.convert.to.message.objects | ConvertMessages | process | platform | ❌ | [📄](steps/STEP-11-RAG.platform.langgraphagent.chat.convert.to.message.objects.md) |
| 12 | RAG.classify.langgraphagent.classify.user.query.extract.user.message | ExtractQuery | process | classify | 🔌 | [📄](steps/STEP-12-RAG.classify.langgraphagent.classify.user.query.extract.user.message.md) |
| 13 | RAG.platform.user.message.exists | MessageExists | decision | platform | 🔌 | [📄](steps/STEP-13-RAG.platform.user.message.exists.md) |
| 14 | RAG.facts.atomicfactsextractor.extract.extract.atomic.facts | ExtractFacts | process | facts | 🔌 | [📄](steps/STEP-14-RAG.facts.atomicfactsextractor.extract.extract.atomic.facts.md) |
| 15 | RAG.prompting.continue.without.classification | DefaultPrompt | process | prompting | ❌ | [📄](steps/STEP-15-RAG.prompting.continue.without.classification.md) |
| 16 | RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates | CanonicalizeFacts | process | facts | ❌ | [📄](steps/STEP-16-RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates.md) |
| 17 | RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment | AttachmentFingerprint | process | preflight | ❌ | [📄](steps/STEP-17-RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment.md) |
| 18 | RAG.facts.querysignature.compute.hash.from.canonical.facts | QuerySig | process | facts | ❌ | [📄](steps/STEP-18-RAG.facts.querysignature.compute.hash.from.canonical.facts.md) |
| 19 | RAG.preflight.attachments.present | AttachCheck | process | preflight | ❌ | [📄](steps/STEP-19-RAG.preflight.attachments.present.md) |
| 20 | RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe | GoldenFastGate | process | golden | 🔌 | [📄](steps/STEP-20-RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe.md) |
| 21 | RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields | QuickPreIngest | process | preflight | ❌ | [📄](steps/STEP-21-RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields.md) |
| 22 | RAG.docs.doc.dependent.or.refers.to.doc | DocDependent | process | docs | ❌ | [📄](steps/STEP-22-RAG.docs.doc.dependent.or.refers.to.doc.md) |
| 23 | RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb | RequireDocIngest | process | golden | 🔌 | [📄](steps/STEP-23-RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb.md) |
| 24 | RAG.preflight.goldenset.match.by.signature.or.semantic | GoldenLookup | process | preflight | ❌ | [📄](steps/STEP-24-RAG.preflight.goldenset.match.by.signature.or.semantic.md) |
| 25 | RAG.golden.high.confidence.match.score.at.least.0.90 | GoldenHit | process | golden | 🔌 | [📄](steps/STEP-25-RAG.golden.high.confidence.match.score.at.least.0.90.md) |
| 26 | RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes | KBContextCheck | process | kb | 🔌 | [📄](steps/STEP-26-RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes.md) |
| 27 | RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags | KBDelta | process | golden | 🔌 | [📄](steps/STEP-27-RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags.md) |
| 28 | RAG.golden.serve.golden.answer.with.citations | ServeGolden | process | golden | 🔌 | [📄](steps/STEP-28-RAG.golden.serve.golden.answer.with.citations.md) |
| 29 | RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present | PreContextFromGolden | process | facts | ❌ | [📄](steps/STEP-29-RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present.md) |
| 30 | RAG.response.return.chatresponse | ReturnComplete | process | response | ❌ | [📄](steps/STEP-30-RAG.response.return.chatresponse.md) |
| 31 | RAG.classify.domainactionclassifier.classify.rule.based.classification | ClassifyDomain | process | classify | 🔌 | [📄](steps/STEP-31-RAG.classify.domainactionclassifier.classify.rule.based.classification.md) |
| 32 | RAG.classify.calculate.domain.and.action.scores.match.italian.keywords | CalcScores | process | classify | 🔌 | [📄](steps/STEP-32-RAG.classify.calculate.domain.and.action.scores.match.italian.keywords.md) |
| 33 | RAG.classify.confidence.at.least.threshold | ConfidenceCheck | process | classify | 🔌 | [📄](steps/STEP-33-RAG.classify.confidence.at.least.threshold.md) |
| 34 | RAG.metrics.classificationmetrics.track.record.metrics | TrackMetrics | process | metrics | 🔌 | [📄](steps/STEP-34-RAG.metrics.classificationmetrics.track.record.metrics.md) |
| 35 | RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification | LLMFallback | process | classify | 🔌 | [📄](steps/STEP-35-RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification.md) |
| 36 | RAG.llm.llm.better.than.rule.based | LLMBetter | decision | llm | ❌ | [📄](steps/STEP-36-RAG.llm.llm.better.than.rule.based.md) |
| 37 | RAG.llm.use.llm.classification | UseLLM | process | llm | 🔌 | [📄](steps/STEP-37-RAG.llm.use.llm.classification.md) |
| 38 | RAG.platform.use.rule.based.classification | UseRuleBased | process | platform | ❌ | [📄](steps/STEP-38-RAG.platform.use.rule.based.classification.md) |
| 39 | RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost | KBPreFetch | process | preflight | ❌ | [📄](steps/STEP-39-RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost.md) |
| 40 | RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts | BuildContext | process | facts | ❌ | [📄](steps/STEP-40-RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts.md) |
| 41 | RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt | SelectPrompt | process | prompting | 🔌 | [📄](steps/STEP-41-RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt.md) |
| 42 | RAG.classify.classification.exists.and.confidence.at.least.0.6 | ClassConfidence | decision | classify | 🔌 | [📄](steps/STEP-42-RAG.classify.classification.exists.and.confidence.at.least.0.6.md) |
| 43 | RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt | DomainPrompt | process | classify | 🔌 | [📄](steps/STEP-43-RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt.md) |
| 44 | RAG.prompting.use.default.system.prompt | DefaultSysPrompt | process | prompting | ❌ | [📄](steps/STEP-44-RAG.prompting.use.default.system.prompt.md) |
| 45 | RAG.prompting.system.message.exists | CheckSysMsg | decision | prompting | 🔌 | [📄](steps/STEP-45-RAG.prompting.system.message.exists.md) |
| 46 | RAG.prompting.replace.system.message | ReplaceMsg | process | prompting | 🔌 | [📄](steps/STEP-46-RAG.prompting.replace.system.message.md) |
| 47 | RAG.prompting.insert.system.message | InsertMsg | process | prompting | 🔌 | [📄](steps/STEP-47-RAG.prompting.insert.system.message.md) |
| 48 | RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider | SelectProvider | process | providers | 🔌 | [📄](steps/STEP-48-RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider.md) |
| 49 | RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy | RouteStrategy | process | facts | 🔌 | [📄](steps/STEP-49-RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy.md) |
| 50 | RAG.platform.routing.strategy | StrategyType | decision | platform | ❌ | [📄](steps/STEP-50-RAG.platform.routing.strategy.md) |
| 51 | RAG.providers.select.cheapest.provider | CheapProvider | process | providers | 🔌 | [📄](steps/STEP-51-RAG.providers.select.cheapest.provider.md) |
| 52 | RAG.providers.select.best.provider | BestProvider | process | providers | 🔌 | [📄](steps/STEP-52-RAG.providers.select.best.provider.md) |
| 53 | RAG.providers.balance.cost.and.quality | BalanceProvider | process | providers | ❌ | [📄](steps/STEP-53-RAG.providers.balance.cost.and.quality.md) |
| 54 | RAG.providers.use.primary.provider | PrimaryProvider | process | providers | 🔌 | [📄](steps/STEP-54-RAG.providers.use.primary.provider.md) |
| 55 | RAG.providers.costcalculator.estimate.cost.calculate.query.cost | EstimateCost | process | providers | 🔌 | [📄](steps/STEP-55-RAG.providers.costcalculator.estimate.cost.calculate.query.cost.md) |
| 56 | RAG.providers.cost.within.budget | CostCheck | decision | providers | ❌ | [📄](steps/STEP-56-RAG.providers.cost.within.budget.md) |
| 57 | RAG.providers.create.provider.instance | CreateProvider | process | providers | 🔌 | [📄](steps/STEP-57-RAG.providers.create.provider.instance.md) |
| 58 | RAG.providers.select.cheaper.provider.or.fail | CheaperProvider | process | providers | 🔌 | [📄](steps/STEP-58-RAG.providers.select.cheaper.provider.or.fail.md) |
| 59 | RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response | CheckCache | process | cache | 🔌 | [📄](steps/STEP-59-RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response.md) |
| 60 | RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version | ResolveEpochs | process | golden | 🔌 | [📄](steps/STEP-60-RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version.md) |
| 61 | RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions | GenHash | process | cache | 🔌 | [📄](steps/STEP-61-RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions.md) |
| 62 | RAG.cache.cache.hit | CacheHit | decision | cache | 🔌 | [📄](steps/STEP-62-RAG.cache.cache.hit.md) |
| 63 | RAG.cache.usagetracker.track.track.cache.hit | TrackCacheHit | process | cache | 🔌 | [📄](steps/STEP-63-RAG.cache.usagetracker.track.track.cache.hit.md) |
| 64 | RAG.providers.llmprovider.chat.completion.make.api.call | LLMCall | process | providers | 🔌 | [📄](steps/STEP-64-RAG.providers.llmprovider.chat.completion.make.api.call.md) |
| 65 | RAG.cache.logger.info.log.cache.hit | LogCacheHit | process | cache | 🔌 | [📄](steps/STEP-65-RAG.cache.logger.info.log.cache.hit.md) |
| 66 | RAG.cache.return.cached.response | ReturnCached | process | cache | 🔌 | [📄](steps/STEP-66-RAG.cache.return.cached.response.md) |
| 67 | RAG.llm.llm.call.successful | LLMSuccess | decision | llm | 🔌 | [📄](steps/STEP-67-RAG.llm.llm.call.successful.md) |
| 68 | RAG.cache.cacheservice.cache.response.store.in.redis | CacheResponse | process | cache | 🔌 | [📄](steps/STEP-68-RAG.cache.cacheservice.cache.response.store.in.redis.md) |
| 69 | RAG.platform.another.attempt.allowed | RetryCheck | decision | platform | ❌ | [📄](steps/STEP-69-RAG.platform.another.attempt.allowed.md) |
| 70 | RAG.platform.prod.environment.and.last.retry | ProdCheck | decision | platform | ❌ | [📄](steps/STEP-70-RAG.platform.prod.environment.and.last.retry.md) |
| 71 | RAG.platform.return.500.error | Error500 | error | platform | ❌ | [📄](steps/STEP-71-RAG.platform.return.500.error.md) |
| 72 | RAG.providers.get.failover.provider | FailoverProvider | process | providers | 🔌 | [📄](steps/STEP-72-RAG.providers.get.failover.provider.md) |
| 73 | RAG.providers.retry.same.provider | RetrySame | process | providers | 🔌 | [📄](steps/STEP-73-RAG.providers.retry.same.provider.md) |
| 74 | RAG.metrics.usagetracker.track.track.api.usage | TrackUsage | process | metrics | 🔌 | [📄](steps/STEP-74-RAG.metrics.usagetracker.track.track.api.usage.md) |
| 75 | RAG.response.response.has.tool.calls | ToolCheck | process | response | ❌ | [📄](steps/STEP-75-RAG.response.response.has.tool.calls.md) |
| 76 | RAG.platform.convert.to.aimessage.with.tool.calls | ConvertAIMsg | process | platform | ❌ | [📄](steps/STEP-76-RAG.platform.convert.to.aimessage.with.tool.calls.md) |
| 77 | RAG.platform.convert.to.simple.aimessage | SimpleAIMsg | process | platform | ❌ | [📄](steps/STEP-77-RAG.platform.convert.to.simple.aimessage.md) |
| 78 | RAG.platform.langgraphagent.tool.call.execute.tools | ExecuteTools | process | platform | ❌ | [📄](steps/STEP-78-RAG.platform.langgraphagent.tool.call.execute.tools.md) |
| 79 | RAG.routing.tool.type | ToolType | decision | routing | ❌ | [📄](steps/STEP-79-RAG.routing.tool.type.md) |
| 80 | RAG.kb.knowledgesearchtool.search.kb.on.demand | KBQueryTool | process | kb | 🔌 | [📄](steps/STEP-80-RAG.kb.knowledgesearchtool.search.kb.on.demand.md) |
| 81 | RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements | CCNLQuery | process | ccnl | 🔌 | [📄](steps/STEP-81-RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements.md) |
| 82 | RAG.preflight.documentingesttool.process.process.attachments | DocIngest | process | preflight | ❌ | [📄](steps/STEP-82-RAG.preflight.documentingesttool.process.process.attachments.md) |
| 83 | RAG.golden.faqtool.faq.query.query.golden.set | FAQQuery | process | golden | 🔌 | [📄](steps/STEP-83-RAG.golden.faqtool.faq.query.query.golden.set.md) |
| 84 | RAG.preflight.attachmentvalidator.validate.check.files.and.limits | ValidateAttach | process | preflight | ❌ | [📄](steps/STEP-84-RAG.preflight.attachmentvalidator.validate.check.files.and.limits.md) |
| 85 | RAG.preflight.valid.attachments | AttachOK | decision | preflight | ❌ | [📄](steps/STEP-85-RAG.preflight.valid.attachments.md) |
| 86 | RAG.platform.return.tool.error.invalid.file | ToolErr | error | platform | ❌ | [📄](steps/STEP-86-RAG.platform.return.tool.error.invalid.file.md) |
| 87 | RAG.docs.docsanitizer.sanitize.strip.macros.and.js | DocSecurity | process | docs | ❌ | [📄](steps/STEP-87-RAG.docs.docsanitizer.sanitize.strip.macros.and.js.md) |
| 88 | RAG.classify.docclassifier.classify.detect.document.type | DocClassify | process | classify | 🔌 | [📄](steps/STEP-88-RAG.classify.docclassifier.classify.detect.document.type.md) |
| 89 | RAG.docs.document.type | DocType | decision | docs | 🔌 | [📄](steps/STEP-89-RAG.docs.document.type.md) |
| 90 | RAG.docs.fatturaparser.parse.xsd.xsd.validation | FatturaParser | process | docs | 🔌 | [📄](steps/STEP-90-RAG.docs.fatturaparser.parse.xsd.xsd.validation.md) |
| 91 | RAG.docs.f24parser.parse.ocr.layout.aware.ocr | F24Parser | process | docs | ❌ | [📄](steps/STEP-91-RAG.docs.f24parser.parse.ocr.layout.aware.ocr.md) |
| 92 | RAG.docs.contractparser.parse | ContractParser | process | docs | ❌ | [📄](steps/STEP-92-RAG.docs.contractparser.parse.md) |
| 93 | RAG.docs.payslipparser.parse | PayslipParser | process | docs | ❌ | [📄](steps/STEP-93-RAG.docs.payslipparser.parse.md) |
| 94 | RAG.docs.genericocr.parse.with.layout | GenericOCR | process | docs | ❌ | [📄](steps/STEP-94-RAG.docs.genericocr.parse.with.layout.md) |
| 95 | RAG.facts.extractor.extract.structured.fields | ExtractDocFacts | process | facts | 🔌 | [📄](steps/STEP-95-RAG.facts.extractor.extract.structured.fields.md) |
| 96 | RAG.docs.blobstore.put.encrypted.ttl.storage | StoreBlob | process | docs | ❌ | [📄](steps/STEP-96-RAG.docs.blobstore.put.encrypted.ttl.storage.md) |
| 97 | RAG.docs.provenance.log.ledger.entry | Provenance | process | docs | ❌ | [📄](steps/STEP-97-RAG.docs.provenance.log.ledger.entry.md) |
| 98 | RAG.facts.convert.to.toolmessage.facts.and.spans | ToToolResults | process | facts | ❌ | [📄](steps/STEP-98-RAG.facts.convert.to.toolmessage.facts.and.spans.md) |
| 99 | RAG.platform.return.to.tool.caller | ToolResults | process | platform | ❌ | [📄](steps/STEP-99-RAG.platform.return.to.tool.caller.md) |
| 100 | RAG.ccnl.ccnlcalculator.calculate.perform.calculations | CCNLCalc | process | ccnl | 🔌 | [📄](steps/STEP-100-RAG.ccnl.ccnlcalculator.calculate.perform.calculations.md) |
| 101 | RAG.response.return.to.chat.node.for.final.response | FinalResponse | process | response | ❌ | [📄](steps/STEP-101-RAG.response.return.to.chat.node.for.final.response.md) |
| 102 | RAG.response.langgraphagent.process.messages.convert.to.dict | ProcessMsg | process | response | 🔌 | [📄](steps/STEP-102-RAG.response.langgraphagent.process.messages.convert.to.dict.md) |
| 103 | RAG.platform.logger.info.log.completion | LogComplete | process | platform | ❌ | [📄](steps/STEP-103-RAG.platform.logger.info.log.completion.md) |
| 104 | RAG.streaming.streaming.requested | StreamCheck | decision | streaming | ❌ | [📄](steps/STEP-104-RAG.streaming.streaming.requested.md) |
| 105 | RAG.streaming.chatbotcontroller.chat.stream.setup.sse | StreamSetup | process | streaming | ❌ | [📄](steps/STEP-105-RAG.streaming.chatbotcontroller.chat.stream.setup.sse.md) |
| 106 | RAG.platform.create.async.generator | AsyncGen | process | platform | ❌ | [📄](steps/STEP-106-RAG.platform.create.async.generator.md) |
| 107 | RAG.preflight.singlepassstream.prevent.double.iteration | SinglePass | process | preflight | 🔌 | [📄](steps/STEP-107-RAG.preflight.singlepassstream.prevent.double.iteration.md) |
| 108 | RAG.streaming.write.sse.format.chunks | WriteSSE | process | streaming | 🔌 | [📄](steps/STEP-108-RAG.streaming.write.sse.format.chunks.md) |
| 109 | RAG.streaming.streamingresponse.send.chunks | StreamResponse | process | streaming | ❌ | [📄](steps/STEP-109-RAG.streaming.streamingresponse.send.chunks.md) |
| 110 | RAG.platform.send.done.frame | SendDone | process | platform | ❌ | [📄](steps/STEP-110-RAG.platform.send.done.frame.md) |
| 111 | RAG.metrics.collect.usage.metrics | CollectMetrics | process | metrics | 🔌 | [📄](steps/STEP-111-RAG.metrics.collect.usage.metrics.md) |
| 112 | RAG.response.return.response.to.user | End | startEnd | response | 🔌 | [📄](steps/STEP-112-RAG.response.return.response.to.user.md) |
| 113 | RAG.feedback.feedbackui.show.options.correct.incomplete.wrong | FeedbackUI | process | feedback | 🔌 | [📄](steps/STEP-113-RAG.feedback.feedbackui.show.options.correct.incomplete.wrong.md) |
| 114 | RAG.feedback.user.provides.feedback | FeedbackProvided | decision | feedback | 🔌 | [📄](steps/STEP-114-RAG.feedback.user.provides.feedback.md) |
| 115 | RAG.feedback.no.feedback | FeedbackEnd | process | feedback | 🔌 | [📄](steps/STEP-115-RAG.feedback.no.feedback.md) |
| 116 | RAG.feedback.feedback.type.selected | FeedbackTypeSel | process | feedback | 🔌 | [📄](steps/STEP-116-RAG.feedback.feedback.type.selected.md) |
| 117 | RAG.golden.post.api.v1.faq.feedback | FAQFeedback | process | golden | 🔌 | [📄](steps/STEP-117-RAG.golden.post.api.v1.faq.feedback.md) |
| 118 | RAG.kb.post.api.v1.knowledge.feedback | KnowledgeFeedback | process | kb | 🔌 | [📄](steps/STEP-118-RAG.kb.post.api.v1.knowledge.feedback.md) |
| 119 | RAG.metrics.expertfeedbackcollector.collect.feedback | ExpertFeedbackCollector | process | metrics | 🔌 | [📄](steps/STEP-119-RAG.metrics.expertfeedbackcollector.collect.feedback.md) |
| 120 | RAG.platform.validate.expert.credentials | ValidateExpert | process | platform | ❌ | [📄](steps/STEP-120-RAG.platform.validate.expert.credentials.md) |
| 121 | RAG.classify.trust.score.at.least.0.7 | TrustScoreOK | decision | classify | 🔌 | [📄](steps/STEP-121-RAG.classify.trust.score.at.least.0.7.md) |
| 122 | RAG.feedback.feedback.rejected | FeedbackRejected | error | feedback | 🔌 | [📄](steps/STEP-122-RAG.feedback.feedback.rejected.md) |
| 123 | RAG.feedback.create.expertfeedback.record | CreateFeedbackRec | process | feedback | 🔌 | [📄](steps/STEP-123-RAG.feedback.create.expertfeedback.record.md) |
| 124 | RAG.metrics.update.expert.metrics | UpdateExpertMetrics | process | metrics | 🔌 | [📄](steps/STEP-124-RAG.metrics.update.expert.metrics.md) |
| 125 | RAG.cache.cache.feedback.1h.ttl | CacheFeedback | process | cache | 🔌 | [📄](steps/STEP-125-RAG.cache.cache.feedback.1h.ttl.md) |
| 126 | RAG.platform.determine.action | DetermineAction | process | platform | ❌ | [📄](steps/STEP-126-RAG.platform.determine.action.md) |
| 127 | RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback | GoldenCandidate | process | golden | 🔌 | [📄](steps/STEP-127-RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback.md) |
| 128 | RAG.golden.auto.threshold.met.or.manual.approval | GoldenApproval | decision | golden | 🔌 | [📄](steps/STEP-128-RAG.golden.auto.threshold.met.or.manual.approval.md) |
| 129 | RAG.golden.goldenset.publish.or.update.versioned.entry | PublishGolden | process | golden | 🔌 | [📄](steps/STEP-129-RAG.golden.goldenset.publish.or.update.versioned.entry.md) |
| 130 | RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature | InvalidateFAQCache | process | preflight | 🔌 | [📄](steps/STEP-130-RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature.md) |
| ~~131~~ | ~~RAG.golden.vectorindex.upsert.faq.update.embeddings~~ | ~~VectorReindex~~ | ~~process~~ | ~~golden~~ | 🔴 | [📄](steps/STEP-131-RAG.golden.vectorindex.upsert.faq.update.embeddings.md) | DEPRECATED - pgvector automatic triggers |
| 132 | RAG.kb.rss.monitor | RSSMonitor | process | kb | 🔌 | [📄](steps/STEP-132-RAG.kb.rss.monitor.md) |
| 133 | RAG.platform.fetch.and.parse.sources | FetchFeeds | process | platform | ❌ | [📄](steps/STEP-133-RAG.platform.fetch.and.parse.sources.md) |
| 134 | RAG.docs.extract.text.and.metadata | ParseDocs | process | docs | 🔌 | [📄](steps/STEP-134-RAG.docs.extract.text.and.metadata.md) |
| 135 | RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates | GoldenRules | process | golden | 🔌 | [📄](steps/STEP-135-RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates.md) |

## How to Update

1. **Edit the Mermaid diagram**: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
2. **Regenerate registry and docs**: `python scripts/rag_stepgen.py --write`
3. **Fill/update per-step documentation**: Edit files in `docs/architecture/steps/`
4. **Review changes**: Check git diff to ensure only intended changes

## Statistics

- **Total Steps**: 135
- **By Type**: decision: 20, error: 4, process: 109, startEnd: 2
- **By Category**: cache: 8, ccnl: 2, classify: 9, docs: 11, facts: 8, feedback: 6, golden: 13, kb: 4, llm: 3, metrics: 5, platform: 24, preflight: 10, privacy: 3, prompting: 6, providers: 12, response: 6, routing: 1, streaming: 4
