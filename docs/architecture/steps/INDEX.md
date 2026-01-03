# RAG Pipeline Steps (1-135)

**Auto-generated:** 2026-01-03 18:27:27
**Total Steps:** 138

> 💡 This directory contains 138 detailed step documents describing the complete RAG pipeline from request to response.

---

## 📖 Overview

Each step document describes a specific operation in the RAG pipeline:
- **Purpose:** What the step does
- **Inputs:** What data it receives
- **Outputs:** What data it produces
- **Logic:** Decision points and flow control
- **Related Steps:** Dependencies and connections

---

## 🗺️ Steps by Phase

### Initialization & Validation (1-10)

<details>
<summary>View 10 steps</summary>

- **[Step 1](STEP-1-RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate.md)** - platform → chatbotcontroller → chat → validate → request → and → authenticate
- **[Step 10](STEP-10-RAG.platform.logger.info.log.pii.anonymization.md)** - platform → logger → info → log → pii → anonymization
- **[Step 2](STEP-2-RAG.platform.user.submits.query.via.post.api.v1.chat.md)** - platform → user → submits → query → via → post → api → v1 → chat
- **[Step 3](STEP-3-RAG.platform.request.valid.md)** - platform → request → valid
- **[Step 4](STEP-4-RAG.privacy.gdprcompliance.record.processing.log.data.processing.md)** - privacy → gdprcompliance → record → processing → log → data → processing
- **[Step 5](STEP-5-RAG.platform.return.400.bad.request.md)** - platform → return → 400 → bad → request
- **[Step 6](STEP-6-RAG.privacy.privacy.anonymize.requests.enabled.md)** - privacy → privacy → anonymize → requests → enabled
- **[Step 7](STEP-7-RAG.privacy.anonymizer.anonymize.text.anonymize.pii.md)** - privacy → anonymizer → anonymize → text → anonymize → pii
- **[Step 8](STEP-8-RAG.response.langgraphagent.get.response.initialize.workflow.md)** - response → langgraphagent → get → response → initialize → workflow
- **[Step 9](STEP-9-RAG.platform.pii.detected.md)** - platform → pii → detected

</details>

### Classification & Facts (11-20)

<details>
<summary>View 10 steps</summary>

- **[Step 11](STEP-11-RAG.platform.langgraphagent.chat.convert.to.message.objects.md)** - platform → langgraphagent → chat → convert → to → message → objects
- **[Step 12](STEP-12-RAG.classify.langgraphagent.classify.user.query.extract.user.message.md)** - classify → langgraphagent → classify → user → query → extract → user → message
- **[Step 13](STEP-13-RAG.platform.user.message.exists.md)** - platform → user → message → exists
- **[Step 14](STEP-14-RAG.facts.atomicfactsextractor.extract.extract.atomic.facts.md)** - facts → atomicfactsextractor → extract → extract → atomic → facts
- **[Step 15](STEP-15-RAG.prompting.continue.without.classification.md)** - prompting → continue → without → classification
- **[Step 16](STEP-16-RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates.md)** - facts → atomicfactsextractor → canonicalize → normalize → dates → amounts → rates
- **[Step 17](STEP-17-RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment.md)** - preflight → attachmentfingerprint → compute → sha → 256 → per → attachment
- **[Step 18](STEP-18-RAG.facts.querysignature.compute.hash.from.canonical.facts.md)** - facts → querysignature → compute → hash → from → canonical → facts
- **[Step 19](STEP-19-RAG.preflight.attachments.present.md)** - preflight → attachments → present
- **[Step 20](STEP-20-RAG.golden.golden.fast.path.eligible.no.doc.or.quick.check.safe.md)** - golden → golden → fast → path → eligible → no → doc → or → quick → check → safe

</details>

### Knowledge Retrieval (21-40)

<details>
<summary>View 22 steps</summary>

- **[Step 21](STEP-21-RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields.md)** - preflight → docpreingest → quick → extract → type → sniff → and → key → fields
- **[Step 22](STEP-22-RAG.docs.doc.dependent.or.refers.to.doc.md)** - docs → doc → dependent → or → refers → to → doc
- **[Step 23](STEP-23-RAG.golden.plannerhint.require.doc.ingest.first.ingest.then.golden.and.kb.md)** - golden → plannerhint → require → doc → ingest → first → ingest → then → golden → and → kb
- **[Step 24](STEP-24-RAG.preflight.goldenset.match.by.signature.or.semantic.md)** - preflight → goldenset → match → by → signature → or → semantic
- **[Step 25](STEP-25-RAG.golden.high.confidence.match.score.at.least.0.90.md)** - golden → high → confidence → match → score → at → least → 0 → 90
- **[Step 26](STEP-26-RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes.md)** - kb → knowledgesearch → context → topk → fetch → recent → kb → for → changes
- **[Step 27](STEP-27-RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags.md)** - golden → kb → newer → than → golden → as → of → or → conflicting → tags
- **[Step 28](STEP-28-RAG.golden.serve.golden.answer.with.citations.md)** - golden → serve → golden → answer → with → citations
- **[Step 30](STEP-30-RAG.response.return.chatresponse.md)** - response → return → chatresponse
- **[Step 31](STEP-31-RAG.classify.domainactionclassifier.classify.rule.based.classification.md)** - classify → domainactionclassifier → classify → rule → based → classification
- **[Step 32](STEP-32-RAG.classify.calculate.domain.and.action.scores.match.italian.keywords.md)** - classify → calculate → domain → and → action → scores → match → italian → keywords
- **[Step 33](STEP-33-RAG.classify.confidence.at.least.threshold.md)** - classify → confidence → at → least → threshold
- **[Step 34](STEP-34-RAG.metrics.classificationmetrics.track.record.metrics.md)** - metrics → classificationmetrics → track → record → metrics
- **[Step 35](STEP-35-RAG.classify.domainactionclassifier.llm.fallback.use.llm.classification.md)** - classify → domainactionclassifier → llm → fallback → use → llm → classification
- **[Step 36](STEP-36-RAG.llm.llm.better.than.rule.based.md)** - llm → llm → better → than → rule → based
- **[Step 37](STEP-37-RAG.llm.use.llm.classification.md)** - llm → use → llm → classification
- **[Step 38](STEP-38-RAG.platform.use.rule.based.classification.md)** - platform → use → rule → based → classification
- **[Step 39](STEP-39-RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost.md)** - preflight → knowledgesearch → retrieve → topk → bm25 → and → vectors → and → recency → boost

</details>

### Prompting & Provider Selection (41-60)

<details>
<summary>View 20 steps</summary>

- **[Step 41](STEP-41-RAG.prompting.langgraphagent.get.system.prompt.select.appropriate.prompt.md)** - prompting → langgraphagent → get → system → prompt → select → appropriate → prompt
- **[Step 42](STEP-42-RAG.classify.classification.exists.and.confidence.at.least.0.6.md)** - classify → classification → exists → and → confidence → at → least → 0 → 6
- **[Step 43](STEP-43-RAG.classify.prompttemplatemanager.get.prompt.get.domain.specific.prompt.md)** - classify → prompttemplatemanager → get → prompt → get → domain → specific → prompt
- **[Step 44](STEP-44-RAG.prompting.use.default.system.prompt.md)** - prompting → use → default → system → prompt
- **[Step 45](STEP-45-RAG.prompting.system.message.exists.md)** - prompting → system → message → exists
- **[Step 46](STEP-46-RAG.prompting.replace.system.message.md)** - prompting → replace → system → message
- **[Step 47](STEP-47-RAG.prompting.insert.system.message.md)** - prompting → insert → system → message
- **[Step 48](STEP-48-RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider.md)** - providers → langgraphagent → get → optimal → provider → select → llm → provider
- **[Step 49](STEP-49-RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy.md)** - facts → llmfactory → get → optimal → provider → apply → routing → strategy
- **[Step 50](STEP-50-RAG.platform.routing.strategy.md)** - platform → routing → strategy
- **[Step 51](STEP-51-RAG.providers.select.cheapest.provider.md)** - providers → select → cheapest → provider
- **[Step 52](STEP-52-RAG.providers.select.best.provider.md)** - providers → select → best → provider
- **[Step 53](STEP-53-RAG.providers.balance.cost.and.quality.md)** - providers → balance → cost → and → quality
- **[Step 54](STEP-54-RAG.providers.use.primary.provider.md)** - providers → use → primary → provider
- **[Step 55](STEP-55-RAG.providers.costcalculator.estimate.cost.calculate.query.cost.md)** - providers → costcalculator → estimate → cost → calculate → query → cost
- **[Step 56](STEP-56-RAG.providers.cost.within.budget.md)** - providers → cost → within → budget
- **[Step 57](STEP-57-RAG.providers.create.provider.instance.md)** - providers → create → provider → instance
- **[Step 58](STEP-58-RAG.providers.select.cheaper.provider.or.fail.md)** - providers → select → cheaper → provider → or → fail
- **[Step 59](STEP-59-RAG.cache.langgraphagent.get.cached.llm.response.check.for.cached.response.md)** - cache → langgraphagent → get → cached → llm → response → check → for → cached → response
- **[Step 60](STEP-60-RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version.md)** - golden → epochstamps → resolve → kb → epoch → golden → epoch → ccnl → epoch → parser → version

</details>

### LLM Execution & Caching (61-80)

<details>
<summary>View 20 steps</summary>

- **[Step 61](STEP-61-RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions.md)** - cache → cacheservice → generate → response → key → sig → and → doc → hashes → and → epochs → and → versions
- **[Step 62](STEP-62-RAG.cache.cache.hit.md)** - cache → cache → hit
- **[Step 63](STEP-63-RAG.cache.usagetracker.track.track.cache.hit.md)** - cache → usagetracker → track → track → cache → hit
- **[Step 64](STEP-64-RAG.providers.llmprovider.chat.completion.make.api.call.md)** - providers → llmprovider → chat → completion → make → api → call
- **[Step 65](STEP-65-RAG.cache.logger.info.log.cache.hit.md)** - cache → logger → info → log → cache → hit
- **[Step 66](STEP-66-RAG.cache.return.cached.response.md)** - cache → return → cached → response
- **[Step 67](STEP-67-RAG.llm.llm.call.successful.md)** - llm → llm → call → successful
- **[Step 68](STEP-68-RAG.cache.cacheservice.cache.response.store.in.redis.md)** - cache → cacheservice → cache → response → store → in → redis
- **[Step 69](STEP-69-RAG.platform.another.attempt.allowed.md)** - platform → another → attempt → allowed
- **[Step 70](STEP-70-RAG.platform.prod.environment.and.last.retry.md)** - platform → prod → environment → and → last → retry
- **[Step 71](STEP-71-RAG.platform.return.500.error.md)** - platform → return → 500 → error
- **[Step 72](STEP-72-RAG.providers.get.failover.provider.md)** - providers → get → failover → provider
- **[Step 73](STEP-73-RAG.providers.retry.same.provider.md)** - providers → retry → same → provider
- **[Step 74](STEP-74-RAG.metrics.usagetracker.track.track.api.usage.md)** - metrics → usagetracker → track → track → api → usage
- **[Step 75](STEP-75-RAG.response.response.has.tool.calls.md)** - response → response → has → tool → calls
- **[Step 76](STEP-76-RAG.platform.convert.to.aimessage.with.tool.calls.md)** - platform → convert → to → aimessage → with → tool → calls
- **[Step 77](STEP-77-RAG.platform.convert.to.simple.aimessage.md)** - platform → convert → to → simple → aimessage
- **[Step 78](STEP-78-RAG.platform.langgraphagent.tool.call.execute.tools.md)** - platform → langgraphagent → tool → call → execute → tools
- **[Step 79](STEP-79-RAG.routing.tool.type.md)** - routing → tool → type
- **[Step 80](STEP-80-RAG.kb.knowledgesearchtool.search.kb.on.demand.md)** - kb → knowledgesearchtool → search → kb → on → demand

</details>

### Tool Execution & Document Processing (81-100)

<details>
<summary>View 20 steps</summary>

- **[Step 100](STEP-100-RAG.ccnl.ccnlcalculator.calculate.perform.calculations.md)** - ccnl → ccnlcalculator → calculate → perform → calculations
- **[Step 81](STEP-81-RAG.ccnl.ccnltool.ccnl.query.query.labor.agreements.md)** - ccnl → ccnltool → ccnl → query → query → labor → agreements
- **[Step 82](STEP-82-RAG.preflight.documentingesttool.process.process.attachments.md)** - preflight → documentingesttool → process → process → attachments
- **[Step 83](STEP-83-RAG.golden.faqtool.faq.query.query.golden.set.md)** - golden → faqtool → faq → query → query → golden → set
- **[Step 84](STEP-84-RAG.preflight.attachmentvalidator.validate.check.files.and.limits.md)** - preflight → attachmentvalidator → validate → check → files → and → limits
- **[Step 85](STEP-85-RAG.preflight.valid.attachments.md)** - preflight → valid → attachments
- **[Step 86](STEP-86-RAG.platform.return.tool.error.invalid.file.md)** - platform → return → tool → error → invalid → file
- **[Step 87](STEP-87-RAG.docs.docsanitizer.sanitize.strip.macros.and.js.md)** - docs → docsanitizer → sanitize → strip → macros → and → js
- **[Step 88](STEP-88-RAG.classify.docclassifier.classify.detect.document.type.md)** - classify → docclassifier → classify → detect → document → type
- **[Step 89](STEP-89-RAG.docs.document.type.md)** - docs → document → type
- **[Step 90](STEP-90-RAG.docs.fatturaparser.parse.xsd.xsd.validation.md)** - docs → fatturaparser → parse → xsd → xsd → validation
- **[Step 91](STEP-91-RAG.docs.f24parser.parse.ocr.layout.aware.ocr.md)** - docs → f24parser → parse → ocr → layout → aware → ocr
- **[Step 92](STEP-92-RAG.docs.contractparser.parse.md)** - docs → contractparser → parse
- **[Step 93](STEP-93-RAG.docs.payslipparser.parse.md)** - docs → payslipparser → parse
- **[Step 94](STEP-94-RAG.docs.genericocr.parse.with.layout.md)** - docs → genericocr → parse → with → layout
- **[Step 95](STEP-95-RAG.facts.extractor.extract.structured.fields.md)** - facts → extractor → extract → structured → fields
- **[Step 96](STEP-96-RAG.docs.blobstore.put.encrypted.ttl.storage.md)** - docs → blobstore → put → encrypted → ttl → storage
- **[Step 97](STEP-97-RAG.docs.provenance.log.ledger.entry.md)** - docs → provenance → log → ledger → entry
- **[Step 98](STEP-98-RAG.facts.convert.to.toolmessage.facts.and.spans.md)** - facts → convert → to → toolmessage → facts → and → spans
- **[Step 99](STEP-99-RAG.platform.return.to.tool.caller.md)** - platform → return → to → tool → caller

</details>

### Response & Streaming (101-120)

<details>
<summary>View 20 steps</summary>

- **[Step 101](STEP-101-RAG.response.return.to.chat.node.for.final.response.md)** - response → return → to → chat → node → for → final → response
- **[Step 102](STEP-102-RAG.response.langgraphagent.process.messages.convert.to.dict.md)** - response → langgraphagent → process → messages → convert → to → dict
- **[Step 103](STEP-103-RAG.platform.logger.info.log.completion.md)** - platform → logger → info → log → completion
- **[Step 104](STEP-104-RAG.streaming.streaming.requested.md)** - streaming → streaming → requested
- **[Step 105](STEP-105-RAG.streaming.chatbotcontroller.chat.stream.setup.sse.md)** - streaming → chatbotcontroller → chat → stream → setup → sse
- **[Step 106](STEP-106-RAG.platform.create.async.generator.md)** - platform → create → async → generator
- **[Step 107](STEP-107-RAG.preflight.singlepassstream.prevent.double.iteration.md)** - preflight → singlepassstream → prevent → double → iteration
- **[Step 108](STEP-108-RAG.streaming.write.sse.format.chunks.md)** - streaming → write → sse → format → chunks
- **[Step 109](STEP-109-RAG.streaming.streamingresponse.send.chunks.md)** - streaming → streamingresponse → send → chunks
- **[Step 110](STEP-110-RAG.platform.send.done.frame.md)** - platform → send → done → frame
- **[Step 111](STEP-111-RAG.metrics.collect.usage.metrics.md)** - metrics → collect → usage → metrics
- **[Step 112](STEP-112-RAG.response.return.response.to.user.md)** - response → return → response → to → user
- **[Step 113](STEP-113-RAG.feedback.feedbackui.show.options.correct.incomplete.wrong.md)** - feedback → feedbackui → show → options → correct → incomplete → wrong
- **[Step 114](STEP-114-RAG.feedback.user.provides.feedback.md)** - feedback → user → provides → feedback
- **[Step 115](STEP-115-RAG.feedback.no.feedback.md)** - feedback → no → feedback
- **[Step 116](STEP-116-RAG.feedback.feedback.type.selected.md)** - feedback → feedback → type → selected
- **[Step 117](STEP-117-RAG.golden.post.api.v1.faq.feedback.md)** - golden → post → api → v1 → faq → feedback
- **[Step 118](STEP-118-RAG.kb.post.api.v1.knowledge.feedback.md)** - kb → post → api → v1 → knowledge → feedback
- **[Step 119](STEP-119-RAG.metrics.expertfeedbackcollector.collect.feedback.md)** - metrics → expertfeedbackcollector → collect → feedback
- **[Step 120](STEP-120-RAG.platform.validate.expert.credentials.md)** - platform → validate → expert → credentials

</details>

### Feedback & Golden Set (121-135)

<details>
<summary>View 15 steps</summary>

- **[Step 121](STEP-121-RAG.classify.trust.score.at.least.0.7.md)** - classify → trust → score → at → least → 0 → 7
- **[Step 122](STEP-122-RAG.feedback.feedback.rejected.md)** - feedback → feedback → rejected
- **[Step 123](STEP-123-RAG.feedback.create.expertfeedback.record.md)** - feedback → create → expertfeedback → record
- **[Step 124](STEP-124-RAG.metrics.update.expert.metrics.md)** - metrics → update → expert → metrics
- **[Step 125](STEP-125-RAG.cache.cache.feedback.1h.ttl.md)** - cache → cache → feedback → 1h → ttl
- **[Step 126](STEP-126-RAG.platform.determine.action.md)** - platform → determine → action
- **[Step 127](STEP-127-RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback.md)** - golden → goldensetupdater → propose → candidate → from → expert → feedback
- **[Step 128](STEP-128-RAG.golden.auto.threshold.met.or.manual.approval.md)** - golden → auto → threshold → met → or → manual → approval
- **[Step 129](STEP-129-RAG.golden.goldenset.publish.or.update.versioned.entry.md)** - golden → goldenset → publish → or → update → versioned → entry
- **[Step 130](STEP-130-RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature.md)** - preflight → cacheservice → invalidate → faq → by → id → or → signature
- **[Step 131](STEP-131-RAG.golden.vectorindex.upsert.faq.update.embeddings.md)** - golden → vectorindex → upsert → faq → update → embeddings
- **[Step 132](STEP-132-RAG.kb.rss.monitor.md)** - kb → rss → monitor
- **[Step 133](STEP-133-RAG.platform.fetch.and.parse.sources.md)** - platform → fetch → and → parse → sources
- **[Step 134](STEP-134-RAG.docs.extract.text.and.metadata.md)** - docs → extract → text → and → metadata
- **[Step 135](STEP-135-RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates.md)** - golden → goldensetupdater → auto → rule → eval → new → or → obsolete → candidates

</details>


---

## 🔍 Quick Find

**Common Topics:**

- **Authentication:** Steps 1-5
- **Privacy/GDPR:** Steps 6-10
- **Classification:** Steps 11-42
- **Golden Set:** Steps 20-30, 127-131
- **Knowledge Retrieval:** Steps 39-40
- **LLM Providers:** Steps 48-73
- **Caching:** Steps 59-68
- **Tool Execution:** Steps 78-99
- **Streaming:** Steps 104-112
- **Feedback:** Steps 113-135
- **RSS Monitoring:** Step 132

---

## 📊 Statistics

- **Initialization & Validation (1-10):** 10 steps
- **Classification & Facts (11-20):** 10 steps
- **Knowledge Retrieval (21-40):** 22 steps
- **Prompting & Provider Selection (41-60):** 20 steps
- **LLM Execution & Caching (61-80):** 20 steps
- **Tool Execution & Document Processing (81-100):** 20 steps
- **Response & Streaming (101-120):** 20 steps
- **Feedback & Golden Set (121-135):** 15 steps

- **Total:** 138 steps

---

**Last Updated:** 2026-01-03 18:27:27
