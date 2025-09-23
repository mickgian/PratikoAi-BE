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

async def step_17__attachment_fingerprint(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 17 — AttachmentFingerprint.compute SHA-256 per attachment
    ID: RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment
    Type: process | Category: preflight | Node: AttachmentFingerprint

    Computes SHA-256 hashes for each attachment to enable deduplication,
    caching, and change detection. Thin orchestration that preserves existing
    hash computation patterns from KnowledgeIntegrator.
    """
    import hashlib

    ctx = ctx or {}
    with rag_step_timer(17, 'RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment', 'AttachmentFingerprint', stage="start"):
        attachments = ctx.get('attachments', [])
        request_id = ctx.get('request_id', 'unknown')

        rag_step_log(
            step=17,
            step_id='RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment',
            node_label='AttachmentFingerprint',
            category='preflight',
            type='process',
            processing_stage="started",
            request_id=request_id,
            attachment_count=len(attachments)
        )

        fingerprints = []
        hash_set = set()

        for attachment in attachments:
            content = attachment.get('content', b'')
            filename = attachment.get('filename', 'unknown')
            size = attachment.get('size', len(content) if content else 0)

            # Compute SHA-256 hash (same pattern as KnowledgeIntegrator._generate_content_hash)
            hash_value = hashlib.sha256(content).hexdigest()

            fingerprints.append({
                'hash': hash_value,
                'filename': filename,
                'size': size,
                'mime_type': attachment.get('mime_type')
            })

            hash_set.add(hash_value)

        # Detect duplicates
        has_duplicates = len(fingerprints) > len(hash_set)
        duplicate_count = len(fingerprints) - len(hash_set) if has_duplicates else 0

        result = {
            'hashes_computed': True,
            'attachment_count': len(attachments),
            'fingerprints': fingerprints,
            'has_duplicates': has_duplicates,
            'duplicate_count': duplicate_count,
            'next_step': 'attachments_present_check',  # Routes to Step 19
            'request_id': request_id
        }

        rag_step_log(
            step=17,
            step_id='RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment',
            node_label='AttachmentFingerprint',
            processing_stage="completed",
            request_id=request_id,
            attachment_count=len(attachments),
            hashes_computed=True,
            has_duplicates=has_duplicates,
            duplicate_count=duplicate_count
        )

        return result

async def step_19__attach_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 19 — Attachments present?
    ID: RAG.preflight.attachments.present
    Type: process | Category: preflight | Node: AttachCheck

    Decision step that checks whether attachments are present in the request.
    Routes to document validation (Step 84) if attachments exist, otherwise
    continues to golden set matching (Step 24). Thin orchestration that preserves
    existing attachment presence checking logic.
    """
    ctx = ctx or {}
    with rag_step_timer(19, 'RAG.preflight.attachments.present', 'AttachCheck', stage="start"):
        fingerprints = ctx.get('fingerprints', [])
        attachment_count = ctx.get('attachment_count', len(fingerprints))
        request_id = ctx.get('request_id', 'unknown')

        rag_step_log(
            step=19,
            step_id='RAG.preflight.attachments.present',
            node_label='AttachCheck',
            category='preflight',
            type='process',
            processing_stage="started",
            request_id=request_id,
            attachment_count=attachment_count
        )

        # Check if attachments are present (simple presence check)
        attachments_present = len(fingerprints) > 0

        # Determine next step based on presence
        next_step = 'validate_attachments' if attachments_present else 'golden_set_lookup'
        decision = 'present' if attachments_present else 'absent'

        result = {
            'attachments_present': attachments_present,
            'attachment_count': attachment_count,
            'next_step': next_step,
            'request_id': request_id
        }

        rag_step_log(
            step=19,
            step_id='RAG.preflight.attachments.present',
            node_label='AttachCheck',
            processing_stage="completed",
            request_id=request_id,
            attachments_present=attachments_present,
            attachment_count=attachment_count,
            decision=decision
        )

        return result

async def step_21__doc_pre_ingest(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 21 — DocPreIngest.quick_extract type sniff and key fields
    ID: RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields
    Type: process | Category: preflight | Node: QuickPreIngest

    Performs quick document type detection and key field extraction based on MIME type
    and basic metadata analysis. Thin orchestration that prepares documents for
    deeper processing in subsequent steps.
    """
    from app.models.document_simple import DOCUMENT_CONFIG

    ctx = ctx or {}
    with rag_step_timer(21, 'RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields', 'QuickPreIngest', stage="start"):
        fingerprints = ctx.get('fingerprints', [])
        attachment_count = ctx.get('attachment_count', len(fingerprints))
        request_id = ctx.get('request_id', 'unknown')

        rag_step_log(
            step=21,
            step_id='RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields',
            node_label='QuickPreIngest',
            category='preflight',
            type='process',
            processing_stage="started",
            request_id=request_id,
            document_count=attachment_count
        )

        extracted_docs = []
        supported_mime_types = DOCUMENT_CONFIG['SUPPORTED_MIME_TYPES']

        for fingerprint in fingerprints:
            filename = fingerprint.get('filename', 'unknown')
            mime_type = fingerprint.get('mime_type', 'unknown')
            size = fingerprint.get('size', 0)
            hash_value = fingerprint.get('hash', '')

            # Detect document type from MIME type
            detected_type = 'unknown'
            if mime_type in supported_mime_types:
                doc_type_enum = supported_mime_types[mime_type]
                detected_type = doc_type_enum.value

            # Extract potential category hints from filename (basic heuristics)
            potential_category = None
            filename_lower = filename.lower()
            if 'fattura' in filename_lower or 'fpa' in filename_lower:
                potential_category = 'fattura_elettronica'
            elif 'f24' in filename_lower:
                potential_category = 'f24'
            elif 'contratto' in filename_lower or 'contract' in filename_lower:
                potential_category = 'contratto'
            elif 'busta' in filename_lower or 'paga' in filename_lower or 'payslip' in filename_lower:
                potential_category = 'busta_paga'
            elif 'bilancio' in filename_lower:
                potential_category = 'bilancio'

            doc_info = {
                'filename': filename,
                'mime_type': mime_type,
                'detected_type': detected_type,
                'size': size,
                'hash': hash_value,
                'potential_category': potential_category
            }

            extracted_docs.append(doc_info)

        result = {
            'extraction_completed': True,
            'document_count': len(extracted_docs),
            'extracted_docs': extracted_docs,
            'next_step': 'doc_dependent_check',  # Routes to Step 22
            'request_id': request_id
        }

        rag_step_log(
            step=21,
            step_id='RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields',
            node_label='QuickPreIngest',
            processing_stage="completed",
            request_id=request_id,
            extraction_completed=True,
            document_count=len(extracted_docs)
        )

        return result

# Alias for backward compatibility
step_21__quick_pre_ingest = step_21__doc_pre_ingest

def step_24__golden_lookup(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 24 — GoldenSet.match_by_signature_or_semantic
    ID: RAG.preflight.goldenset.match.by.signature.or.semantic
    Type: process | Category: preflight | Node: GoldenLookup

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(24, 'RAG.preflight.goldenset.match.by.signature.or.semantic', 'GoldenLookup', stage="start"):
        rag_step_log(step=24, step_id='RAG.preflight.goldenset.match.by.signature.or.semantic', node_label='GoldenLookup',
                     category='preflight', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=24, step_id='RAG.preflight.goldenset.match.by.signature.or.semantic', node_label='GoldenLookup',
                     processing_stage="completed")
        return result

async def step_39__kbpre_fetch(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 39 — KnowledgeSearch.retrieve_topk BM25 and vectors and recency boost
    ID: RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost
    Type: process | Category: preflight | Node: KBPreFetch

    Performs hybrid knowledge search using BM25, vector search, and recency boost
    to retrieve relevant knowledge items for context building. Thin orchestration
    that preserves existing KnowledgeSearchService behavior.
    """
    from app.core.logging import logger
    from app.services.knowledge_search_service import KnowledgeSearchService, SearchMode
    from datetime import datetime, timezone

    with rag_step_timer(39, 'RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost', 'KBPreFetch', stage="start"):
        # Extract context parameters
        request_id = kwargs.get('request_id') or (ctx or {}).get('request_id', 'unknown')
        user_message = kwargs.get('user_message') or (ctx or {}).get('user_message', '')
        canonical_facts = kwargs.get('canonical_facts') or (ctx or {}).get('canonical_facts', [])
        user_id = kwargs.get('user_id') or (ctx or {}).get('user_id')
        session_id = kwargs.get('session_id') or (ctx or {}).get('session_id')
        trace_id = kwargs.get('trace_id') or (ctx or {}).get('trace_id')

        # Search configuration parameters
        search_mode = kwargs.get('search_mode') or (ctx or {}).get('search_mode', SearchMode.HYBRID.value)
        filters = kwargs.get('filters') or (ctx or {}).get('filters', {})
        max_results = kwargs.get('max_results') or (ctx or {}).get('max_results', 10)

        # Initialize result variables
        search_performed = False
        knowledge_items = []
        total_results = 0
        error = None

        rag_step_log(
            step=39,
            step_id='RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost',
            node_label='KBPreFetch',
            category='preflight',
            type='process',
            processing_stage='started',
            request_id=request_id,
            search_query=user_message[:100] if user_message else '',
            search_mode=search_mode
        )

        try:
            # TODO: In real implementation, inject KnowledgeSearchService via dependency injection
            # For thin orchestrator pattern, we'll receive the service as a parameter
            knowledge_service = kwargs.get('knowledge_service')

            if not knowledge_service:
                # Fallback: create service instance (for production use)
                # This would typically be handled by a factory or dependency container
                from app.services.knowledge_search_service import KnowledgeSearchService
                from app.core.config import get_settings

                # For now, create a minimal service instance
                # In production, this would be properly injected
                settings = get_settings()
                knowledge_service = KnowledgeSearchService(
                    db_session=None,  # Would be injected in real usage
                    vector_service=None,
                    config=getattr(settings, 'knowledge_search', None)
                )

            # Prepare query data for the service
            query_data = {
                'query': user_message,
                'canonical_facts': canonical_facts,
                'user_id': user_id,
                'session_id': session_id,
                'trace_id': trace_id,
                'search_mode': search_mode,
                'filters': filters,
                'max_results': max_results
            }

            # Perform the knowledge search
            knowledge_items = await knowledge_service.retrieve_topk(query_data)
            search_performed = True
            total_results = len(knowledge_items)

            # Log successful search
            logger.info(
                f"Knowledge search completed: {total_results} items retrieved",
                extra={
                    'request_id': request_id,
                    'search_query': user_message[:100] if user_message else '',
                    'search_mode': search_mode,
                    'total_results': total_results,
                    'filters': filters,
                    'max_results': max_results
                }
            )

        except Exception as e:
            error = str(e)
            search_performed = False
            knowledge_items = []
            total_results = 0

            logger.error(
                f"Error in knowledge search: {error}",
                extra={
                    'request_id': request_id,
                    'error': error,
                    'step': 39,
                    'search_query': user_message[:100] if user_message else ''
                }
            )

        # Build result preserving behavior while adding coordination metadata
        result = {
            'search_performed': search_performed,
            'knowledge_items': knowledge_items,
            'total_results': total_results,
            'search_query': user_message,
            'search_mode': search_mode,
            'filters': filters,
            'max_results': max_results,
            'canonical_facts': canonical_facts,
            'user_id': user_id,
            'session_id': session_id,
            'trace_id': trace_id,
            'request_id': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error
        }

        rag_step_log(
            step=39,
            step_id='RAG.preflight.knowledgesearch.retrieve.topk.bm25.and.vectors.and.recency.boost',
            node_label='KBPreFetch',
            category='preflight',
            type='process',
            processing_stage='completed',
            request_id=request_id,
            search_performed=search_performed,
            total_results=total_results,
            search_mode=search_mode
        )

        return result

def step_82__doc_ingest(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 82 — DocumentIngestTool.process Process attachments
    ID: RAG.preflight.documentingesttool.process.process.attachments
    Type: process | Category: preflight | Node: DocIngest

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(82, 'RAG.preflight.documentingesttool.process.process.attachments', 'DocIngest', stage="start"):
        rag_step_log(step=82, step_id='RAG.preflight.documentingesttool.process.process.attachments', node_label='DocIngest',
                     category='preflight', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=82, step_id='RAG.preflight.documentingesttool.process.process.attachments', node_label='DocIngest',
                     processing_stage="completed")
        return result

async def step_84__validate_attachments(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 84 — AttachmentValidator.validate Check files and limits
    ID: RAG.preflight.attachmentvalidator.validate.check.files.and.limits
    Type: process | Category: preflight | Node: ValidateAttach

    Validates attachments against file size limits, file count limits, and supported
    MIME types using DOCUMENT_CONFIG settings. Thin orchestration that preserves
    existing validation logic from DocumentUploader.
    """
    from app.models.document_simple import DOCUMENT_CONFIG

    ctx = ctx or {}
    with rag_step_timer(84, 'RAG.preflight.attachmentvalidator.validate.check.files.and.limits', 'ValidateAttach', stage="start"):
        fingerprints = ctx.get('fingerprints', [])
        attachment_count = ctx.get('attachment_count', len(fingerprints))
        request_id = ctx.get('request_id', 'unknown')

        rag_step_log(
            step=84,
            step_id='RAG.preflight.attachmentvalidator.validate.check.files.and.limits',
            node_label='ValidateAttach',
            category='preflight',
            type='process',
            processing_stage="started",
            request_id=request_id,
            attachment_count=attachment_count
        )

        errors = []
        max_file_size_bytes = DOCUMENT_CONFIG['MAX_FILE_SIZE_MB'] * 1024 * 1024
        max_files = DOCUMENT_CONFIG['MAX_FILES_PER_UPLOAD']
        supported_mime_types = DOCUMENT_CONFIG['SUPPORTED_MIME_TYPES']

        # Check file count limit
        if attachment_count > max_files:
            errors.append(f"Too many files. Maximum {max_files} files allowed, got {attachment_count}")

        # Check each file
        for fingerprint in fingerprints:
            filename = fingerprint.get('filename', 'unknown')
            size = fingerprint.get('size', 0)
            mime_type = fingerprint.get('mime_type', 'unknown')

            # Check file size
            if size > max_file_size_bytes:
                errors.append(
                    f"File '{filename}' too large. Maximum {DOCUMENT_CONFIG['MAX_FILE_SIZE_MB']}MB, "
                    f"got {size / 1024 / 1024:.1f}MB"
                )

            # Check MIME type
            if mime_type not in supported_mime_types:
                errors.append(
                    f"File '{filename}' has unsupported type '{mime_type}'. "
                    f"Supported types: {', '.join(supported_mime_types.keys())}"
                )

        validation_passed = len(errors) == 0

        result = {
            'validation_passed': validation_passed,
            'attachment_count': attachment_count,
            'errors': errors,
            'next_step': 'valid_attachments_check',  # Routes to Step 85
            'request_id': request_id
        }

        rag_step_log(
            step=84,
            step_id='RAG.preflight.attachmentvalidator.validate.check.files.and.limits',
            node_label='ValidateAttach',
            processing_stage="completed",
            request_id=request_id,
            validation_passed=validation_passed,
            attachment_count=attachment_count,
            error_count=len(errors)
        )

        return result

# Alias for backward compatibility
step_84__validate_attach = step_84__validate_attachments

async def step_85__valid_attachments_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 85 — Valid attachments?
    ID: RAG.preflight.valid.attachments
    Type: decision | Category: preflight | Node: AttachOK

    Decision step that checks validation results from Step 84.
    Routes to document pre-ingest (Step 21) if valid, otherwise returns
    error (Step 86). Thin orchestration that preserves existing validation
    decision logic.
    """
    ctx = ctx or {}
    with rag_step_timer(85, 'RAG.preflight.valid.attachments', 'AttachOK', stage="start"):
        validation_passed = ctx.get('validation_passed', True)
        errors = ctx.get('errors', [])
        attachment_count = ctx.get('attachment_count', 0)
        request_id = ctx.get('request_id', 'unknown')

        # If validation_passed not set, check errors list
        if 'validation_passed' not in ctx:
            validation_passed = len(errors) == 0

        rag_step_log(
            step=85,
            step_id='RAG.preflight.valid.attachments',
            node_label='AttachOK',
            category='preflight',
            type='decision',
            processing_stage="started",
            request_id=request_id,
            attachment_count=attachment_count
        )

        # Determine next step based on validation
        attachments_valid = validation_passed
        next_step = 'doc_pre_ingest' if attachments_valid else 'tool_error'
        decision = 'valid' if attachments_valid else 'invalid'

        result = {
            'attachments_valid': attachments_valid,
            'attachment_count': attachment_count,
            'errors': errors,
            'error_count': len(errors),
            'next_step': next_step,
            'request_id': request_id
        }

        rag_step_log(
            step=85,
            step_id='RAG.preflight.valid.attachments',
            node_label='AttachOK',
            processing_stage="completed",
            request_id=request_id,
            attachments_valid=attachments_valid,
            error_count=len(errors),
            decision=decision
        )

        return result

# Alias for backward compatibility
step_85__attach_ok = step_85__valid_attachments_check

def step_107__single_pass(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 107 — SinglePassStream Prevent double iteration
    ID: RAG.preflight.singlepassstream.prevent.double.iteration
    Type: process | Category: preflight | Node: SinglePass

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(107, 'RAG.preflight.singlepassstream.prevent.double.iteration', 'SinglePass', stage="start"):
        rag_step_log(step=107, step_id='RAG.preflight.singlepassstream.prevent.double.iteration', node_label='SinglePass',
                     category='preflight', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=107, step_id='RAG.preflight.singlepassstream.prevent.double.iteration', node_label='SinglePass',
                     processing_stage="completed")
        return result

def step_130__invalidate_faqcache(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 130 — CacheService.invalidate_faq by id or signature
    ID: RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature
    Type: process | Category: preflight | Node: InvalidateFAQCache

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(130, 'RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature', 'InvalidateFAQCache', stage="start"):
        rag_step_log(step=130, step_id='RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature', node_label='InvalidateFAQCache',
                     category='preflight', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=130, step_id='RAG.preflight.cacheservice.invalidate.faq.by.id.or.signature', node_label='InvalidateFAQCache',
                     processing_stage="completed")
        return result
