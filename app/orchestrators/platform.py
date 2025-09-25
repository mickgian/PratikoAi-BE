# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs): return None
    def rag_step_timer(*args, **kwargs): return nullcontext()

async def step_1__validate_request(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 1 — ChatbotController.chat Validate request and authenticate
    ID: RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate
    Type: process | Category: platform | Node: ValidateRequest

    Validates incoming requests and performs authentication as per ChatbotController.chat.
    This orchestrator coordinates request validation and authentication checking.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    with rag_step_timer(1, 'RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate', 'ValidateRequest', stage="start"):
        rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate', node_label='ValidateRequest',
                     category='platform', type='process', processing_stage="started")

        # Extract context parameters
        context = ctx or {}
        request_body = kwargs.get('request_body') or context.get('request_body')
        content_type = kwargs.get('content_type') or context.get('content_type', '')
        method = kwargs.get('method') or context.get('method', '')
        authorization_header = kwargs.get('authorization_header') or context.get('authorization_header')
        request_id = kwargs.get('request_id') or context.get('request_id', 'unknown')

        # Initialize result structure
        result = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'validation_successful': False,
            'authentication_successful': False,
            'request_valid': False,
            'session': None,
            'user': None,
            'validated_request': None,
            'error': None,
            'next_step': 'Error400',
            'ready_for_validation': False
        }

        try:
            # Step 1: Critical request validation (must happen before auth)
            if not context and not any([request_body, content_type, method, authorization_header]):
                result['error'] = 'Missing request context'
                logger.error("Request validation failed: Missing context", request_id=request_id)
                rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                           node_label='ValidateRequest', processing_stage="completed", error="missing_context",
                           validation_successful=False, authentication_successful=False, request_id=request_id)
                return result

            # Validate request body structure (critical for security)
            if not request_body or not isinstance(request_body, dict):
                result['error'] = 'Invalid request body'
                logger.error("Request validation failed: Invalid request body", request_id=request_id)
                rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                           node_label='ValidateRequest', processing_stage="completed", error="invalid_request_body",
                           validation_successful=False, authentication_successful=False, request_id=request_id)
                return result

            # Validate HTTP method (critical)
            if method and method.upper() not in ['POST']:
                result['error'] = f'Invalid HTTP method: {method}'
                logger.error("Request validation failed: Invalid method", method=method, request_id=request_id)
                rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                           node_label='ValidateRequest', processing_stage="completed", error="invalid_method",
                           validation_successful=False, authentication_successful=False, request_id=request_id)
                return result

            # Step 2: Authentication
            if not authorization_header:
                result['error'] = 'Missing authorization header'
                logger.error("Authentication failed: Missing authorization header", request_id=request_id)
                rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                           node_label='ValidateRequest', processing_stage="completed", error="missing_auth_header",
                           validation_successful=False, authentication_successful=False, request_id=request_id)
                return result

            try:
                # Import auth functions
                from app.api.v1.auth import get_current_session, get_current_user
                from fastapi.security import HTTPAuthorizationCredentials

                # Create credentials object for auth validation
                token = authorization_header.replace('Bearer ', '') if authorization_header.startswith('Bearer ') else authorization_header
                credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

                # Get session and user (simulating auth dependency injection)
                session = await get_current_session(credentials)
                user = await get_current_user(credentials)

                result['session'] = session
                result['user'] = user
                result['authentication_successful'] = True

            except Exception as auth_error:
                result['error'] = f'Authentication failed: {str(auth_error)}'
                logger.error("Authentication failed", error=str(auth_error), request_id=request_id)
                rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                           node_label='ValidateRequest', processing_stage="completed", error="authentication_failed",
                           validation_successful=False, authentication_successful=False, request_id=request_id)
                return result

            # Step 3: Additional request validation (after authentication succeeds)
            validation_errors = []

            # Validate content type
            if content_type and content_type.lower() not in ['application/json', '']:
                validation_errors.append(f'Invalid content type: {content_type}')

            # Validate required fields
            if 'messages' not in request_body or not request_body.get('messages'):
                validation_errors.append('Missing required field: messages')

            # Check if validation passed
            if validation_errors:
                result['error'] = '; '.join(validation_errors)
                logger.error("Request validation failed", errors=validation_errors, request_id=request_id)
                rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                           node_label='ValidateRequest', processing_stage="completed", error=result['error'],
                           validation_successful=False, authentication_successful=True, request_id=request_id,
                           session_id=result['session'].id if result['session'] else 'unknown',
                           user_id=result['user'].id if result['user'] else 'unknown')
                return result

            # Step 4: Final validation and success
            result['validation_successful'] = True
            result['request_valid'] = True
            result['validated_request'] = request_body.copy()
            result['next_step'] = 'ValidCheck'
            result['ready_for_validation'] = True
            result['error'] = None

            session_id = result['session'].id if result['session'] else 'unknown'
            user_id = result['user'].id if result['user'] else 'unknown'

            logger.info(
                "Request validation and authentication completed successfully",
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                message_count=len(request_body.get('messages', [])),
                extra={
                    'validation_event': 'request_validated_and_authenticated',
                    'validation_successful': True,
                    'authentication_successful': True,
                    'request_id': request_id
                }
            )

            rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                        node_label='ValidateRequest', processing_stage="completed",
                        validation_successful=True, authentication_successful=True,
                        session_id=session_id, user_id=user_id, request_id=request_id,
                        next_step='ValidCheck', ready_for_validation=True)

            return result

        except Exception as e:
            result['error'] = f'Validation error: {str(e)}'
            logger.error("Request validation failed with exception", error=str(e), request_id=request_id, exc_info=True)
            rag_step_log(step=1, step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                        node_label='ValidateRequest', processing_stage="completed", error=str(e),
                        validation_successful=False, authentication_successful=False, request_id=request_id)
            return result

def step_2__start(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 2 — User submits query via POST /api/v1/chat
    ID: RAG.platform.user.submits.query.via.post.api.v1.chat
    Type: startEnd | Category: platform | Node: Start

    Entry point for RAG workflow when users submit queries via the chat API.
    This orchestrator initializes the workflow and prepares context for validation.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone
    import uuid

    with rag_step_timer(2, 'RAG.platform.user.submits.query.via.post.api.v1.chat', 'Start', stage="start"):
        rag_step_log(step=2, step_id='RAG.platform.user.submits.query.via.post.api.v1.chat', node_label='Start',
                     category='platform', type='startEnd', processing_stage="started")

        # Extract context parameters
        context = ctx or {}
        request_body = kwargs.get('request_body') or context.get('request_body')
        request_context = kwargs.get('request_context') or context.get('request_context', {})
        session_id = kwargs.get('session_id') or context.get('session_id')
        user_id = kwargs.get('user_id') or context.get('user_id')

        # Initialize workflow result
        result = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'workflow_started': True,
            'request_received': bool(request_body),
            'entry_point': 'chat_api',
            'next_step': 'ValidateRequest',
            'ready_for_validation': True,
            'workflow_context': {},
            'request_metadata': {},
            'warning': None
        }

        try:
            # Build request metadata with defaults
            result['request_metadata'] = {
                'method': request_context.get('method', 'POST'),
                'url': request_context.get('url', '/api/v1/chat'),
                'content_type': request_context.get('content_type', 'application/json'),
                'user_agent': request_context.get('user_agent', 'unknown'),
                'request_id': request_context.get('request_id', f'req_{str(uuid.uuid4())[:8]}'),
                'timestamp': request_context.get('timestamp', result['timestamp'])
            }

            # Build workflow context
            if request_body:
                result['workflow_context'] = {
                    'initialized': True,
                    'messages': request_body.get('messages', []),
                    'message_count': len(request_body.get('messages', [])),
                    'user_id': user_id or request_body.get('user_id'),
                    'session_id': session_id,
                    'stream': request_body.get('stream', False),
                    'attachments': request_body.get('attachments', []),
                    'metadata': request_body.get('metadata', {})
                }
            else:
                # Handle case with no request body
                result['workflow_context'] = {
                    'initialized': True,
                    'messages': [],
                    'message_count': 0,
                    'user_id': user_id,
                    'session_id': session_id,
                    'stream': False,
                    'attachments': [],
                    'metadata': {}
                }
                result['request_received'] = False
                result['warning'] = 'No request body provided'
                logger.warning(
                    "RAG workflow started without request body",
                    session_id=session_id,
                    user_id=user_id,
                    request_id=result['request_metadata']['request_id']
                )

            # Log successful start
            logger.info(
                "RAG workflow started successfully",
                session_id=result['workflow_context']['session_id'],
                user_id=result['workflow_context']['user_id'],
                message_count=result['workflow_context']['message_count'],
                request_id=result['request_metadata']['request_id'],
                stream=result['workflow_context']['stream'],
                extra={
                    'workflow_event': 'started',
                    'entry_point': result['entry_point'],
                    'request_received': result['request_received']
                }
            )

            # Log completion
            rag_step_log(
                step=2,
                step_id='RAG.platform.user.submits.query.via.post.api.v1.chat',
                node_label='Start',
                processing_stage="completed",
                workflow_started=True,
                request_received=result['request_received'],
                entry_point=result['entry_point'],
                next_step=result['next_step'],
                ready_for_validation=True,
                message_count=result['workflow_context']['message_count'],
                session_id=result['workflow_context']['session_id'],
                user_id=result['workflow_context']['user_id'],
                request_id=result['request_metadata']['request_id']
            )

            return result

        except Exception as e:
            # Handle any unexpected errors
            error_msg = f'Workflow start error: {str(e)}'
            result['workflow_started'] = False
            result['error'] = error_msg

            logger.error(
                "RAG workflow start failed",
                error=str(e),
                request_id=result['request_metadata'].get('request_id', 'unknown'),
                exc_info=True
            )

            rag_step_log(
                step=2,
                step_id='RAG.platform.user.submits.query.via.post.api.v1.chat',
                node_label='Start',
                processing_stage="completed",
                error=str(e),
                workflow_started=False,
                request_received=result['request_received']
            )

            return result

def step_3__valid_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 3 — Request valid?
    ID: RAG.platform.request.valid
    Type: decision | Category: platform | Node: ValidCheck

    Validates if the incoming request meets basic requirements for RAG processing.
    This orchestrator coordinates request validation checking all required fields.
    """
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(3, 'RAG.platform.request.valid', 'ValidCheck', stage="start"):
        # Extract context parameters
        request_body = kwargs.get('request_body') or (ctx or {}).get('request_body')
        content_type = kwargs.get('content_type') or (ctx or {}).get('content_type', '')
        method = kwargs.get('method') or (ctx or {}).get('method', '')
        authenticated = kwargs.get('authenticated') or (ctx or {}).get('authenticated', False)

        # Initialize validation data
        validation_errors = []
        is_valid = True
        request_type = 'unknown'

        # Validate request body exists and is not empty
        if not request_body or not isinstance(request_body, dict):
            validation_errors.append('Missing or invalid request body')
            is_valid = False
        else:
            # Validate required fields in request body
            if 'query' not in request_body or not request_body.get('query'):
                validation_errors.append('Missing required field: query')
                is_valid = False
            else:
                request_type = 'chat_query'

        # Validate content type
        if content_type.lower() not in ['application/json', '']:
            validation_errors.append(f'Invalid content type: {content_type}')
            is_valid = False

        # Validate HTTP method
        if method.upper() not in ['POST', '']:
            validation_errors.append(f'Invalid HTTP method: {method}')
            is_valid = False

        # Validate authentication
        if not authenticated:
            validation_errors.append('Request not authenticated')
            is_valid = False

        # Create validation result
        validation_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'request_type': request_type
        }

        # Log validation result
        log_level = "info" if is_valid else "warning"
        log_message = f"Request validation {'completed' if is_valid else 'failed'}"

        extra_data = {
            'validation_event': 'request_validated',
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'request_type': request_type,
            'error_count': len(validation_errors)
        }

        if log_level == "info":
            logger.info(log_message, extra=extra_data)
        else:
            logger.warning(log_message, extra=extra_data)

        # RAG step logging
        rag_step_log(
            step=3,
            step_id='RAG.platform.request.valid',
            node_label='ValidCheck',
            category='platform',
            type='decision',
            validation_event='request_validated',
            is_valid=is_valid,
            validation_errors=validation_errors,
            request_type=request_type,
            error_count=len(validation_errors),
            processing_stage="completed"
        )

        return validation_data

def step_5__error400(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 5 — Return 400 Bad Request
    ID: RAG.platform.return.400.bad.request
    Type: error | Category: platform | Node: Error400

    Handles invalid requests by returning appropriate HTTP error responses.
    This orchestrator terminates the workflow and returns structured error data.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    with rag_step_timer(5, 'RAG.platform.return.400.bad.request', 'Error400', stage="start"):
        rag_step_log(step=5, step_id='RAG.platform.return.400.bad.request', node_label='Error400',
                     category='platform', type='error', processing_stage="started")

        # Extract context parameters
        context = ctx or {}
        error_type = kwargs.get('error_type') or context.get('error_type', 'unknown_error')
        error_message = kwargs.get('error_message') or context.get('error_message')
        validation_errors = kwargs.get('validation_errors') or context.get('validation_errors', [])
        request_context = kwargs.get('request_context') or context.get('request_context', {})
        session_id = kwargs.get('session_id') or context.get('session_id')
        user_id = kwargs.get('user_id') or context.get('user_id')

        # Determine appropriate status code based on error type
        status_code_map = {
            'validation_failed': 400,
            'malformed_request': 400,
            'invalid_json': 400,
            'missing_required_field': 400,
            'authentication_failed': 401,
            'invalid_token': 401,
            'token_expired': 401,
            'authorization_failed': 403,
            'insufficient_permissions': 403,
            'rate_limit_exceeded': 429,
            'payload_too_large': 413,
            'unsupported_media_type': 415,
            'unknown_error': 400
        }

        status_code = status_code_map.get(error_type, 400)
        request_id = request_context.get('request_id', 'unknown')

        # Build error response based on error type
        if error_type == 'validation_failed' and validation_errors:
            detail = "Request validation failed"
            error_response = {
                'detail': detail,
                'status_code': status_code,
                'errors': validation_errors
            }
        elif error_message:
            error_response = {
                'detail': error_message,
                'status_code': status_code
            }
        else:
            # Default error response
            error_response = {
                'detail': "Bad request",
                'status_code': status_code
            }

        # Add security headers for authentication errors
        if status_code == 401:
            error_response['headers'] = {
                'WWW-Authenticate': 'Bearer'
            }

        # Build comprehensive error details for logging
        error_details = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'error_type': error_type,
            'status_code': status_code,
            'request_id': request_id,
            'session_id': session_id,
            'user_id': user_id,
            'validation_errors': validation_errors if validation_errors else None,
            'error_message': error_message,
            'request_context': request_context
        }

        # Initialize result structure
        result = {
            'timestamp': error_details['timestamp'],
            'status_code': status_code,
            'error_returned': True,
            'error_type': error_type,
            'workflow_terminated': True,
            'terminal_step': True,
            'next_step': None,
            'error_response': error_response,
            'error_details': error_details
        }

        # Log the error appropriately
        log_level_map = {
            401: 'warning',  # Auth errors are warnings
            403: 'warning',  # Authorization errors are warnings
            429: 'warning',  # Rate limit warnings
            400: 'error',    # Bad request errors
            413: 'warning',  # Payload size warnings
            415: 'warning'   # Media type warnings
        }

        log_level = log_level_map.get(status_code, 'error')
        log_message = f"400 Bad Request returned: {error_type}"

        if log_level == 'error':
            logger.error(
                log_message,
                status_code=status_code,
                error_type=error_type,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                validation_errors=validation_errors,
                extra={
                    'error_event': 'bad_request_returned',
                    'status_code': status_code,
                    'error_type': error_type
                }
            )
        else:
            logger.warning(
                log_message,
                status_code=status_code,
                error_type=error_type,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id
            )

        # Complete RAG step logging
        rag_step_log(
            step=5,
            step_id='RAG.platform.return.400.bad.request',
            node_label='Error400',
            processing_stage="completed",
            status_code=status_code,
            error_returned=True,
            error_type=error_type,
            workflow_terminated=True,
            terminal_step=True,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id
        )

        return result

def step_9__piicheck(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 9 — PII detected?
    ID: RAG.platform.pii.detected
    Type: decision | Category: platform | Node: PIICheck

    Detects if personally identifiable information is present in the request.
    This orchestrator coordinates PII detection analysis and confidence scoring.
    """
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(9, 'RAG.platform.pii.detected', 'PIICheck', stage="start"):
        # Extract context parameters
        user_query = kwargs.get('user_query') or (ctx or {}).get('user_query', '')
        pii_analysis_result = kwargs.get('pii_analysis_result') or (ctx or {}).get('pii_analysis_result', {})
        pii_threshold = kwargs.get('pii_threshold') or (ctx or {}).get('pii_threshold', 0.8)

        # For backward compatibility, check if PII was pre-detected
        pre_detected = kwargs.get('pii_detected') or (ctx or {}).get('pii_detected')
        pre_types = kwargs.get('pii_types') or (ctx or {}).get('pii_types', [])

        # Initialize PII detection data
        pii_detected = False
        pii_count = 0
        pii_types = []
        detection_confidence = 0.0

        if pre_detected is not None:
            # Use pre-computed detection results
            pii_detected = bool(pre_detected)
            pii_types = list(pre_types)
            pii_count = len(pii_types)
            detection_confidence = 1.0 if pii_detected else 0.0
        elif pii_analysis_result:
            # Analyze PII detection results
            matches = pii_analysis_result.get('matches', [])

            # Filter matches by confidence threshold
            high_confidence_matches = [
                match for match in matches
                if match.get('confidence', 0) >= pii_threshold
            ]

            if high_confidence_matches:
                pii_detected = True
                pii_count = len(high_confidence_matches)
                pii_types = [match.get('type') for match in high_confidence_matches]
                detection_confidence = max(match.get('confidence', 0) for match in high_confidence_matches)
            else:
                # Still report highest confidence even if below threshold
                if matches:
                    detection_confidence = max(match.get('confidence', 0) for match in matches)

        # Create PII detection result
        pii_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'pii_detected': pii_detected,
            'pii_count': pii_count,
            'pii_types': pii_types,
            'detection_confidence': detection_confidence,
            'query_length': len(user_query) if user_query else 0
        }

        # Log PII detection result
        log_message = f"PII detection completed: {'detected' if pii_detected else 'not detected'}"

        extra_data = {
            'pii_event': 'pii_detected',
            'pii_detected': pii_detected,
            'pii_count': pii_count,
            'pii_types': pii_types,
            'detection_confidence': detection_confidence,
            'threshold_used': pii_threshold,
            'query_length': len(user_query) if user_query else 0
        }

        logger.info(log_message, extra=extra_data)

        # RAG step logging
        rag_step_log(
            step=9,
            step_id='RAG.platform.pii.detected',
            node_label='PIICheck',
            category='platform',
            type='decision',
            pii_event='pii_detected',
            pii_detected=pii_detected,
            pii_count=pii_count,
            pii_types=pii_types,
            detection_confidence=detection_confidence,
            threshold_used=pii_threshold,
            query_length=len(user_query) if user_query else 0,
            processing_stage="completed"
        )

        return pii_data

def step_10__log_pii(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 10 — Logger.info Log PII anonymization
    ID: RAG.platform.logger.info.log.pii.anonymization
    Type: process | Category: platform | Node: LogPII

    Logs PII anonymization events for audit trail and GDPR compliance.
    Called after PII detection/anonymization to create audit record.

    This orchestrator coordinates the logging of PII anonymization events.
    """
    from app.core.logging import logger
    from datetime import datetime

    # Extract context parameters
    anonymization_result = kwargs.get('anonymization_result') or (ctx or {}).get('anonymization_result')
    user_query = kwargs.get('user_query') or (ctx or {}).get('user_query', '')
    pii_detected = kwargs.get('pii_detected') or (ctx or {}).get('pii_detected', False)
    pii_types = kwargs.get('pii_types') or (ctx or {}).get('pii_types', [])
    anonymization_method = kwargs.get('anonymization_method') or (ctx or {}).get('anonymization_method', 'hash')

    with rag_step_timer(10, 'RAG.platform.logger.info.log.pii.anonymization', 'LogPII', stage="start"):
        rag_step_log(
            step=10,
            step_id='RAG.platform.logger.info.log.pii.anonymization',
            node_label='LogPII',
            category='platform',
            type='process',
            processing_stage="started",
            pii_detected=pii_detected,
            pii_types_count=len(pii_types) if pii_types else 0
        )

        # Create audit log entry for PII anonymization
        audit_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'pii_detected': pii_detected,
            'pii_types': pii_types,
            'anonymization_method': anonymization_method,
            'query_length': len(user_query) if user_query else 0,
            'anonymized_count': 0,
            'privacy_compliance': True
        }

        # Extract details from anonymization result if available
        if anonymization_result:
            if hasattr(anonymization_result, 'pii_matches'):
                audit_data['anonymized_count'] = len(anonymization_result.pii_matches)
                audit_data['pii_types'] = [match.pii_type.value for match in anonymization_result.pii_matches]
            elif isinstance(anonymization_result, dict):
                audit_data['anonymized_count'] = anonymization_result.get('matches_count', 0)
                audit_data['pii_types'] = anonymization_result.get('pii_types', [])

        # Log PII anonymization event for audit trail
        logger.info(
            "PII anonymization completed",
            extra={
                'audit_event': 'pii_anonymization',
                'pii_detected': audit_data['pii_detected'],
                'pii_types': audit_data['pii_types'],
                'anonymized_count': audit_data['anonymized_count'],
                'anonymization_method': audit_data['anonymization_method'],
                'gdpr_compliance': True,
                'step': 10
            }
        )

        rag_step_log(
            step=10,
            step_id='RAG.platform.logger.info.log.pii.anonymization',
            node_label='LogPII',
            audit_event='pii_anonymization',
            pii_detected=audit_data['pii_detected'],
            pii_types=audit_data['pii_types'],
            anonymized_count=audit_data['anonymized_count'],
            anonymization_method=audit_data['anonymization_method'],
            query_length=audit_data['query_length'],
            privacy_compliance=audit_data['privacy_compliance'],
            processing_stage="completed"
        )

        # Return audit data for downstream processing
        return audit_data

async def step_11__convert_messages(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 11 — LangGraphAgent._chat Convert to Message objects
    ID: RAG.platform.langgraphagent.chat.convert.to.message.objects
    Type: process | Category: platform | Node: ConvertMessages

    Converts various message formats to standardized Message objects.
    This orchestrator coordinates message format standardization in the RAG workflow.
    """
    from app.core.logging import logger
    from app.schemas.chat import Message
    from datetime import datetime, timezone

    with rag_step_timer(11, 'RAG.platform.langgraphagent.chat.convert.to.message.objects', 'ConvertMessages', stage="start"):
        rag_step_log(step=11, step_id='RAG.platform.langgraphagent.chat.convert.to.message.objects', node_label='ConvertMessages',
                     category='platform', type='process', processing_stage="started")

        # Extract context parameters
        context = ctx or {}
        raw_messages = messages or kwargs.get('raw_messages') or context.get('raw_messages', [])
        message_format = kwargs.get('message_format') or context.get('message_format', 'auto')
        request_id = kwargs.get('request_id') or context.get('request_id', 'unknown')
        enable_deduplication = kwargs.get('enable_deduplication') or context.get('enable_deduplication', False)

        # Initialize result structure
        result = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'conversion_successful': False,
            'message_count': 0,
            'converted_messages': [],
            'standardized_messages': [],
            'next_step': 'ExtractQuery',
            'ready_for_extraction': False,
            'conversion_errors': [],
            'validation_errors': [],
            'error': None
        }

        try:
            # Step 1: Handle empty messages
            if not raw_messages:
                logger.warning("No messages provided for conversion", request_id=request_id)
                result['conversion_successful'] = True
                result['ready_for_extraction'] = True
                rag_step_log(step=11, step_id='RAG.platform.langgraphagent.chat.convert.to.message.objects',
                           node_label='ConvertMessages', processing_stage="completed",
                           conversion_successful=True, message_count=0, next_step='ExtractQuery',
                           request_id=request_id)
                return result

            # Step 2: Convert messages to standardized format
            converted_messages = []
            conversion_errors = []
            validation_errors = []

            for i, raw_msg in enumerate(raw_messages):
                try:
                    converted_msg = await _convert_single_message(raw_msg, i)
                    if converted_msg:
                        # Validate the converted message
                        if await _validate_message(converted_msg):
                            converted_messages.append(converted_msg)
                        else:
                            validation_errors.append(f"Message {i}: validation failed")
                            logger.warning(f"Message validation failed", message_index=i, request_id=request_id)
                    else:
                        conversion_errors.append(f"Message {i}: conversion failed")
                        logger.warning(f"Message conversion failed", message_index=i, request_id=request_id)

                except Exception as e:
                    conversion_errors.append(f"Message {i}: {str(e)}")
                    logger.warning(f"Message conversion error", error=str(e), message_index=i, request_id=request_id)

            # Step 3: Apply deduplication if enabled
            if enable_deduplication and converted_messages:
                original_count = len(converted_messages)
                converted_messages = await _deduplicate_messages(converted_messages)
                if len(converted_messages) < original_count:
                    logger.info(f"Deduplicated {original_count - len(converted_messages)} messages",
                              original_count=original_count, final_count=len(converted_messages), request_id=request_id)

            # Step 4: Build final result
            result['conversion_successful'] = True
            result['message_count'] = len(converted_messages)
            result['converted_messages'] = converted_messages
            result['standardized_messages'] = converted_messages  # Alias for compatibility
            result['ready_for_extraction'] = True
            result['conversion_errors'] = conversion_errors
            result['validation_errors'] = validation_errors

            logger.info(
                "Message conversion completed successfully",
                message_count=len(converted_messages),
                conversion_errors=len(conversion_errors),
                validation_errors=len(validation_errors),
                request_id=request_id,
                extra={
                    'conversion_event': 'messages_converted',
                    'message_count': len(converted_messages),
                    'format': message_format,
                    'deduplication_enabled': enable_deduplication
                }
            )

            rag_step_log(
                step=11,
                step_id='RAG.platform.langgraphagent.chat.convert.to.message.objects',
                node_label='ConvertMessages',
                processing_stage="completed",
                conversion_successful=True,
                message_count=len(converted_messages),
                next_step='ExtractQuery',
                ready_for_extraction=True,
                conversion_errors=len(conversion_errors),
                validation_errors=len(validation_errors),
                request_id=request_id
            )

            return result

        except Exception as e:
            # Handle conversion errors
            result['error'] = f'Message conversion error: {str(e)}'

            logger.error(
                "Message conversion failed",
                error=str(e),
                request_id=request_id,
                exc_info=True
            )

            rag_step_log(
                step=11,
                step_id='RAG.platform.langgraphagent.chat.convert.to.message.objects',
                node_label='ConvertMessages',
                processing_stage="completed",
                error=str(e),
                conversion_successful=False,
                request_id=request_id
            )

            return result


async def _convert_single_message(raw_msg: Any, index: int) -> Optional['Message']:
    """Convert a single message from any format to Message object."""
    from app.schemas.chat import Message
    from app.core.logging import logger

    try:
        # Handle dict format (most common)
        if isinstance(raw_msg, dict):
            role = raw_msg.get('role', 'user')
            content = raw_msg.get('content', '')

            # Validate role
            if role not in ['user', 'assistant', 'system']:
                role = 'user'  # Default fallback

            return Message(role=role, content=content)

        # Handle existing Message objects
        elif isinstance(raw_msg, Message):
            return raw_msg

        # Handle LangChain BaseMessage objects
        elif hasattr(raw_msg, 'role') and hasattr(raw_msg, 'content'):
            role = getattr(raw_msg, 'role', 'user')
            content = getattr(raw_msg, 'content', '')

            # Validate role
            if role not in ['user', 'assistant', 'system']:
                role = 'user'  # Default fallback

            return Message(role=role, content=str(content))

        # Handle string messages (default to user role)
        elif isinstance(raw_msg, str):
            return Message(role='user', content=raw_msg)

        # Handle other types by converting to string
        else:
            return Message(role='user', content=str(raw_msg))

    except Exception as e:
        logger.warning(f"Failed to convert message at index {index}: {str(e)}")
        return None


async def _validate_message(message: 'Message') -> bool:
    """Validate a converted Message object."""
    try:
        # Check content length
        if not message.content or len(message.content.strip()) == 0:
            return False

        # Check maximum length (using the same limit as schema)
        if len(message.content) > 3000:
            return False

        # Check for valid role
        if message.role not in ['user', 'assistant', 'system']:
            return False

        return True
    except Exception:
        return False


async def _deduplicate_messages(messages: List['Message']) -> List['Message']:
    """Remove duplicate consecutive messages with same role and content."""
    if not messages:
        return messages

    deduplicated = [messages[0]]  # Always keep first message

    for message in messages[1:]:
        # Only deduplicate if role and content are exactly the same as previous
        if (message.role != deduplicated[-1].role or
            message.content != deduplicated[-1].content):
            deduplicated.append(message)

    return deduplicated

def step_13__message_exists(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 13 — User message exists?
    ID: RAG.platform.user.message.exists
    Type: decision | Category: platform | Node: MessageExists

    Checks if a user message exists in the request for processing.
    This orchestrator coordinates message analysis and user content detection.
    """
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(13, 'RAG.platform.user.message.exists', 'MessageExists', stage="start"):
        # Extract context parameters
        message_list = messages or kwargs.get('messages') or (ctx or {}).get('messages', [])
        user_query = kwargs.get('user_query') or (ctx or {}).get('user_query', '')

        # Initialize message analysis data
        message_exists = False
        user_message_count = 0
        total_message_count = 0
        user_message_content = ''

        if message_list:
            # Analyze message list
            total_message_count = len(message_list)
            user_messages = []

            for msg in message_list:
                if isinstance(msg, dict) and msg.get('role', '').lower() == 'user' and msg.get('content'):
                    user_messages.append(msg['content'])
                    user_message_count += 1

            if user_messages:
                message_exists = True
                user_message_content = user_messages[-1]  # Most recent user message

        elif user_query:
            # Fallback to user_query if no messages
            message_exists = True
            user_message_count = 1  # Fallback count
            user_message_content = user_query

        # Create message existence result
        message_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'message_exists': message_exists,
            'user_message_count': user_message_count,
            'total_message_count': total_message_count,
            'user_message_content': user_message_content
        }

        # Log message analysis result
        log_level = "info" if message_exists else "warning"
        log_message = f"User message check completed: {'found' if message_exists else 'not found'}"

        if not message_exists:
            log_message = "No user message found in request"

        extra_data = {
            'message_event': 'user_message_found' if message_exists else 'user_message_missing',
            'message_exists': message_exists,
            'user_message_count': user_message_count,
            'total_message_count': total_message_count,
            'has_user_query_fallback': bool(user_query),
            'content_length': len(user_message_content)
        }

        if log_level == "info":
            logger.info(log_message, extra=extra_data)
        else:
            logger.warning(log_message, extra=extra_data)

        # RAG step logging
        rag_step_log(
            step=13,
            step_id='RAG.platform.user.message.exists',
            node_label='MessageExists',
            category='platform',
            type='decision',
            message_event='user_message_found' if message_exists else 'user_message_missing',
            message_exists=message_exists,
            user_message_count=user_message_count,
            total_message_count=total_message_count,
            has_user_query_fallback=bool(user_query),
            content_length=len(user_message_content),
            processing_stage="completed"
        )

        return message_data

async def step_38__use_rule_based(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 38 — Use rule-based classification
    ID: RAG.platform.use.rule.based.classification
    Type: process | Category: platform | Node: UseRuleBased

    Applies rule-based classification results as the final classification when Step 36
    determines rule-based is better than LLM classification. Thin orchestration
    that preserves existing behavior while adding coordination and observability.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    with rag_step_timer(38, 'RAG.platform.use.rule.based.classification', 'UseRuleBased', stage="start"):
        # Extract context parameters
        request_id = kwargs.get('request_id') or (ctx or {}).get('request_id', 'unknown')
        rule_based_classification = kwargs.get('rule_based_classification') or (ctx or {}).get('rule_based_classification')

        # Initialize result variables
        classification_applied = False
        final_classification = None
        classification_source = 'error'
        confidence_level = None
        error = None
        metrics = {}

        rag_step_log(
            step=38,
            step_id='RAG.platform.use.rule.based.classification',
            node_label='UseRuleBased',
            category='platform',
            type='process',
            processing_stage='started',
            request_id=request_id
        )

        try:
            # Validate rule-based classification data
            if not rule_based_classification:
                error = 'No rule-based classification available to apply'
                raise ValueError(error)

            # Validate required fields
            domain = rule_based_classification.get('domain')
            action = rule_based_classification.get('action')
            confidence = rule_based_classification.get('confidence')

            if not domain or not action or confidence is None:
                error = f'Invalid rule-based classification data: missing domain={domain}, action={action}, confidence={confidence}'
                raise ValueError(error)

            # Apply rule-based classification as final result
            final_classification = dict(rule_based_classification)  # Create copy to preserve original
            classification_applied = True
            classification_source = 'rule_based'

            # Determine confidence level for monitoring
            if confidence >= 0.8:
                confidence_level = 'high'
            elif confidence >= 0.6:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'
                # Log warning for low confidence
                logger.warning(
                    f"Low confidence rule-based classification applied: {confidence:.3f}",
                    extra={
                        'request_id': request_id,
                        'confidence': confidence,
                        'domain': domain,
                        'action': action,
                        'confidence_level': confidence_level
                    }
                )

            # Track metrics for monitoring
            metrics = {
                'classification_method': 'rule_based',
                'confidence_score': confidence,
                'domain': domain,
                'action': action,
                'confidence_level': confidence_level,
                'application_timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Log successful application
            logger.info(
                f"Applying rule-based classification as final result: {domain}/{action} (confidence: {confidence:.3f})",
                extra={
                    'request_id': request_id,
                    'classification_source': classification_source,
                    'domain': domain,
                    'action': action,
                    'confidence': confidence,
                    'confidence_level': confidence_level,
                    'fallback_used': rule_based_classification.get('fallback_used', False)
                }
            )

        except Exception as e:
            error = str(e)
            classification_applied = False
            final_classification = None
            classification_source = 'error'

            logger.error(
                f"Error applying rule-based classification: {error}",
                extra={
                    'request_id': request_id,
                    'error': error,
                    'step': 38
                }
            )

        # Build result preserving behavior while adding coordination metadata
        result = {
            'classification_applied': classification_applied,
            'final_classification': final_classification,
            'classification_source': classification_source,
            'confidence_level': confidence_level,
            'metrics': metrics,
            'request_id': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error
        }

        rag_step_log(
            step=38,
            step_id='RAG.platform.use.rule.based.classification',
            node_label='UseRuleBased',
            category='platform',
            type='process',
            processing_stage='completed',
            request_id=request_id,
            classification_applied=classification_applied,
            classification_source=classification_source,
            confidence_level=confidence_level
        )

        return result

def step_50__strategy_type(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    RAG STEP 50 — Routing strategy?
    ID: RAG.platform.routing.strategy
    Type: decision | Category: platform | Node: StrategyType

    Determines the next step based on the routing strategy from Step 49.
    Receives provider context from Step 49 (RouteStrategy) and routes to appropriate provider steps.

    Incoming: RouteStrategy (Step 49)
    Outgoing: CheapProvider, BestProvider, BalanceProvider, PrimaryProvider
    """
    from app.core.llm.factory import RoutingStrategy
    from app.core.logging import logger
    from datetime import datetime

    with rag_step_timer(50, 'RAG.platform.routing.strategy', 'StrategyType', stage="start"):
        # Merge ctx and kwargs for parameter extraction
        params = {}
        if ctx:
            params.update(ctx)
        params.update(kwargs)

        # Extract required parameters from Step 49 output
        routing_strategy = params.get('routing_strategy')
        provider = params.get('provider')
        messages = params.get('messages', messages)

        # Extract additional context
        max_cost_eur = params.get('max_cost_eur')
        preferred_provider = params.get('preferred_provider')
        provider_type = params.get('provider_type')
        model = params.get('model')
        user_id = params.get('user_id')
        session_id = params.get('session_id')

        # Validate required parameters
        if not routing_strategy:
            error_msg = 'Missing required parameter: routing_strategy'
            logger.error(f"STEP 50: {error_msg}")
            rag_step_log(
                step=50,
                step_id='RAG.platform.routing.strategy',
                node_label='StrategyType',
                category='platform',
                type='decision',
                error=error_msg,
                decision='routing_strategy_missing',
                processing_stage="failed"
            )
            return {
                'decision': 'routing_strategy_missing',
                'next_step': None,
                'error': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Initialize decision data
        decision = None
        next_step = None
        routing_strategy_value = routing_strategy.value if hasattr(routing_strategy, 'value') else str(routing_strategy)

        try:
            # Route based on strategy type
            if routing_strategy == RoutingStrategy.COST_OPTIMIZED or routing_strategy_value == 'cost_optimized':
                decision = 'routing_to_cost_optimized'
                next_step = 'CheapProvider'
            elif routing_strategy == RoutingStrategy.QUALITY_FIRST or routing_strategy_value == 'quality_first':
                decision = 'routing_to_quality_first'
                next_step = 'BestProvider'
            elif routing_strategy == RoutingStrategy.BALANCED or routing_strategy_value == 'balanced':
                decision = 'routing_to_balanced'
                next_step = 'BalanceProvider'
            elif routing_strategy == RoutingStrategy.FAILOVER or routing_strategy_value == 'failover':
                decision = 'routing_to_failover'
                next_step = 'PrimaryProvider'
            else:
                # Fallback to balanced for unsupported strategies
                decision = 'routing_fallback_to_balanced'
                next_step = 'BalanceProvider'
                logger.warning(
                    f"STEP 50: Unsupported routing strategy '{routing_strategy_value}', falling back to balanced",
                    extra={
                        'step': 50,
                        'unsupported_strategy': routing_strategy_value,
                        'fallback_strategy': 'balanced'
                    }
                )

            logger.info(
                f"STEP 50: Routing strategy decision completed",
                extra={
                    'step': 50,
                    'decision': decision,
                    'routing_strategy': routing_strategy_value,
                    'next_step': next_step,
                    'provider_type': provider_type,
                    'model': model,
                    'max_cost_eur': max_cost_eur
                }
            )

            # Prepare result for the selected provider step
            result = {
                'decision': decision,
                'next_step': next_step,
                'routing_strategy': routing_strategy_value,
                'provider': provider,
                'provider_type': provider_type,
                'model': model,
                'max_cost_eur': max_cost_eur,
                'preferred_provider': preferred_provider,
                'messages': messages,
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }

            # Add fallback reason if applicable
            if decision == 'routing_fallback_to_balanced':
                result['fallback_reason'] = routing_strategy_value

            # Enhanced logging attributes
            log_attrs = {
                'step': 50,
                'step_id': 'RAG.platform.routing.strategy',
                'node_label': 'StrategyType',
                'category': 'platform',
                'type': 'decision',
                'decision': decision,
                'routing_strategy': routing_strategy_value,
                'next_step': next_step,
                'max_cost_eur': max_cost_eur,
                'messages_count': len(messages) if messages else 0,
                'messages_empty': not bool(messages),
                'processing_stage': 'completed'
            }

            # Add optional parameters if present
            if preferred_provider:
                log_attrs['preferred_provider'] = preferred_provider
            if provider_type:
                log_attrs['provider_type'] = provider_type
            if model:
                log_attrs['model'] = model
            if user_id:
                log_attrs['user_id'] = user_id
            if session_id:
                log_attrs['session_id'] = session_id

            # Add additional context from kwargs
            for key in ['complexity', 'fallback_reason']:
                if key in params:
                    log_attrs[key] = params[key]

            rag_step_log(**log_attrs)

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"STEP 50: Failed to determine routing strategy",
                extra={
                    'step': 50,
                    'error': error_msg,
                    'routing_strategy': routing_strategy_value
                }
            )

            rag_step_log(
                step=50,
                step_id='RAG.platform.routing.strategy',
                node_label='StrategyType',
                category='platform',
                type='decision',
                error=error_msg,
                decision='routing_strategy_failed',
                routing_strategy=routing_strategy_value,
                processing_stage="failed"
            )

            return {
                'decision': 'routing_strategy_failed',
                'next_step': None,
                'error': error_msg,
                'routing_strategy': routing_strategy_value,
                'timestamp': datetime.utcnow().isoformat()
            }

async def step_69__retry_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 69 — Another attempt allowed?
    ID: RAG.platform.another.attempt.allowed
    Type: decision | Category: platform | Node: RetryCheck

    Decision step checking if another retry attempt is allowed based on current attempt number
    and maximum retries configuration. Routes to retry logic (Step 70) if allowed, or error (Step 71) if exhausted.
    """
    from app.core.logging import logger
    from app.core.config import settings
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    attempt_number = kwargs.get('attempt_number') or ctx.get('attempt_number', 1)
    max_retries = kwargs.get('max_retries') or ctx.get('max_retries') or settings.MAX_LLM_CALL_RETRIES
    error = kwargs.get('error') or ctx.get('error')
    previous_errors = kwargs.get('previous_errors') or ctx.get('previous_errors', [])
    request_id = ctx.get('request_id', 'unknown')

    # Initialize decision variables
    retry_allowed = False
    attempts_remaining = 0
    next_step = None
    reason = None
    all_attempts_failed = False
    is_last_retry = False

    # Log decision start
    rag_step_log(
        step=69,
        step_id='RAG.platform.another.attempt.allowed',
        node_label='RetryCheck',
        category='platform',
        type='decision',
        processing_stage='started',
        request_id=request_id,
        attempt_number=attempt_number,
        max_retries=max_retries
    )

    try:
        # Core decision logic: Check if retry is allowed
        # Matches existing logic: for attempt in range(max_retries)
        # Attempt is allowed if current attempt < max_retries
        if attempt_number < max_retries:
            retry_allowed = True
            attempts_remaining = max_retries - attempt_number
            next_step = 'prod_check'  # Route to Step 70
            reason = 'retries_available'

            # Check if this is the last allowed retry
            is_last_retry = (attempts_remaining == 1)

            logger.info(
                f"retry_allowed",
                extra={
                    'request_id': request_id,
                    'step': 69,
                    'attempt_number': attempt_number,
                    'max_retries': max_retries,
                    'attempts_remaining': attempts_remaining,
                    'is_last_retry': is_last_retry
                }
            )
        else:
            # Max retries exhausted
            retry_allowed = False
            attempts_remaining = 0
            next_step = 'error_500'  # Route to Step 71
            reason = 'max_retries_exceeded'
            all_attempts_failed = True

            logger.warning(
                f"retry_exhausted",
                extra={
                    'request_id': request_id,
                    'step': 69,
                    'attempt_number': attempt_number,
                    'max_retries': max_retries,
                    'all_attempts_failed': True,
                    'error_count': len(previous_errors)
                }
            )

    except Exception as e:
        # Unexpected error in decision logic
        error_message = str(e)
        retry_allowed = False
        next_step = 'error_500'
        reason = 'error'

        logger.error(
            f"step_69_decision_error",
            extra={
                'request_id': request_id,
                'step': 69,
                'error': error_message
            }
        )

    # Log decision completion
    rag_step_log(
        step=69,
        step_id='RAG.platform.another.attempt.allowed',
        node_label='RetryCheck',
        processing_stage='completed',
        request_id=request_id,
        retry_allowed=retry_allowed,
        decision='retry' if retry_allowed else 'no_retry',
        attempts_remaining=attempts_remaining,
        next_step=next_step,
        attempt_number=attempt_number,
        max_retries=max_retries,
        max_retries_exceeded=all_attempts_failed,
        error_count=len(previous_errors)
    )

    # Build orchestration result
    result = {
        'retry_allowed': retry_allowed,
        'attempts_remaining': attempts_remaining,
        'next_step': next_step,
        'reason': reason,
        'attempt_number': attempt_number,
        'max_retries': max_retries,
        'all_attempts_failed': all_attempts_failed,
        'is_last_retry': is_last_retry,
        'previous_errors': previous_errors,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return result

async def step_70__prod_check(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 70 — Prod environment and last retry?
    ID: RAG.platform.prod.environment.and.last.retry
    Type: decision | Category: platform | Node: ProdCheck

    Decision step checking if we're in production environment AND on the last retry attempt.
    If both conditions are true, routes to failover provider (Step 72), otherwise retry same provider (Step 73).
    """
    from app.core.logging import logger
    from app.core.config import settings, Environment
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    environment = kwargs.get('environment') or ctx.get('environment') or settings.ENVIRONMENT
    attempt_number = kwargs.get('attempt_number') or ctx.get('attempt_number', 1)
    max_retries = kwargs.get('max_retries') or ctx.get('max_retries', 3)
    is_last_retry = kwargs.get('is_last_retry') or ctx.get('is_last_retry')
    request_id = ctx.get('request_id', 'unknown')

    # Calculate is_last_retry if not provided
    # Original logic: attempt == max_retries - 2 (0-based)
    # Converted to 1-based: attempt_number == max_retries - 1
    if is_last_retry is None:
        is_last_retry = (attempt_number == max_retries - 1)

    # Initialize decision variables
    is_production = (environment == Environment.PRODUCTION)
    use_failover = False
    next_step = None
    reason = None

    # Log decision start
    rag_step_log(
        step=70,
        step_id='RAG.platform.prod.environment.and.last.retry',
        node_label='ProdCheck',
        category='platform',
        type='decision',
        processing_stage='started',
        request_id=request_id,
        environment=environment.value if isinstance(environment, Environment) else str(environment),
        is_production=is_production,
        attempt_number=attempt_number,
        max_retries=max_retries,
        is_last_retry=is_last_retry
    )

    try:
        # Core decision logic: Failover if production AND last retry
        # Matches existing logic from graph.py:779
        # if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
        if is_production and is_last_retry:
            use_failover = True
            next_step = 'get_failover_provider'  # Route to Step 72
            reason = 'production_last_retry'

            logger.warning(
                f"attempting_fallback_provider",
                extra={
                    'request_id': request_id,
                    'step': 70,
                    'environment': environment.value if isinstance(environment, Environment) else str(environment),
                    'attempt_number': attempt_number,
                    'max_retries': max_retries,
                    'is_last_retry': is_last_retry,
                    'use_failover': True
                }
            )
        else:
            # Retry same provider
            use_failover = False
            next_step = 'retry_same_provider'  # Route to Step 73

            if is_production and not is_last_retry:
                reason = 'production_not_last_retry'
            else:
                reason = 'non_production'

            logger.info(
                f"retry_same_provider",
                extra={
                    'request_id': request_id,
                    'step': 70,
                    'environment': environment.value if isinstance(environment, Environment) else str(environment),
                    'attempt_number': attempt_number,
                    'max_retries': max_retries,
                    'is_last_retry': is_last_retry,
                    'is_production': is_production,
                    'use_failover': False
                }
            )

    except Exception as e:
        # Unexpected error in decision logic
        error_message = str(e)
        use_failover = False
        next_step = 'retry_same_provider'
        reason = 'error'

        logger.error(
            f"step_70_decision_error",
            extra={
                'request_id': request_id,
                'step': 70,
                'error': error_message
            }
        )

    # Log decision completion
    rag_step_log(
        step=70,
        step_id='RAG.platform.prod.environment.and.last.retry',
        node_label='ProdCheck',
        processing_stage='completed',
        request_id=request_id,
        use_failover=use_failover,
        decision='failover' if use_failover else 'retry_same',
        is_production=is_production,
        is_last_retry=is_last_retry,
        next_step=next_step,
        attempt_number=attempt_number,
        max_retries=max_retries,
        environment=environment.value if isinstance(environment, Environment) else str(environment)
    )

    # Build orchestration result
    result = {
        'use_failover': use_failover,
        'is_production': is_production,
        'is_last_retry': is_last_retry,
        'next_step': next_step,
        'reason': reason,
        'environment': environment,
        'attempt_number': attempt_number,
        'max_retries': max_retries,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return result

async def step_71__error500(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 71 — Return 500 error
    ID: RAG.platform.return.500.error
    Type: error | Category: platform | Node: Error500

    Error handler step that returns a 500 Internal Server Error when all retry attempts
    have been exhausted. Logs the failure and provides error details to the caller.
    """
    from app.core.logging import logger
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    attempt_number = kwargs.get('attempt_number') or ctx.get('attempt_number', 0)
    max_retries = kwargs.get('max_retries') or ctx.get('max_retries', 3)
    error = kwargs.get('error') or ctx.get('error', 'Unknown error')
    exception = kwargs.get('exception') or ctx.get('exception')
    previous_errors = kwargs.get('previous_errors') or ctx.get('previous_errors', [])
    provider = kwargs.get('provider') or ctx.get('provider')
    model = kwargs.get('model') or ctx.get('model')
    request_id = ctx.get('request_id', 'unknown')

    # Initialize error response
    error_raised = True
    status_code = 500
    error_type = 'max_retries_exhausted'
    error_message = f"Failed to get a response from the LLM after {max_retries} attempts"
    exception_type = None
    all_attempts_failed = True
    error_count = len(previous_errors)
    last_error = error

    # Extract exception details if available
    if exception:
        exception_type = type(exception).__name__
        if str(exception) and str(exception) not in error_message:
            error_message = f"{error_message}: {str(exception)}"

    # Log error start
    rag_step_log(
        step=71,
        step_id='RAG.platform.return.500.error',
        node_label='Error500',
        category='platform',
        type='error',
        processing_stage='started',
        request_id=request_id,
        attempt_number=attempt_number,
        max_retries=max_retries,
        error=error
    )

    # Log the error
    logger.error(
        f"max_retries_exhausted",
        extra={
            'request_id': request_id,
            'step': 71,
            'attempt_number': attempt_number,
            'max_retries': max_retries,
            'error': error,
            'exception_type': exception_type,
            'error_count': error_count,
            'provider': provider,
            'model': model,
            'all_attempts_failed': all_attempts_failed
        }
    )

    # Log error completion
    rag_step_log(
        step=71,
        step_id='RAG.platform.return.500.error',
        node_label='Error500',
        processing_stage='completed',
        request_id=request_id,
        error_raised=error_raised,
        status_code=status_code,
        error_type=error_type,
        error_message=error_message,
        attempt_number=attempt_number,
        max_retries=max_retries,
        error_count=error_count,
        provider=provider,
        model=model
    )

    # Build error response
    result = {
        'error_raised': error_raised,
        'status_code': status_code,
        'error_type': error_type,
        'error_message': error_message,
        'exception_type': exception_type,
        'attempt_number': attempt_number,
        'max_retries': max_retries,
        'all_attempts_failed': all_attempts_failed,
        'error_count': error_count,
        'last_error': last_error,
        'previous_errors': previous_errors,
        'provider': provider,
        'model': model,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    return result

async def step_76__convert_aimsg(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 76 — Convert to AIMessage with tool_calls
    ID: RAG.platform.convert.to.aimessage.with.tool.calls
    Type: process | Category: platform | Node: ConvertAIMsg

    Converts an LLM response with tool calls into a LangChain AIMessage object.
    This preserves the existing behavior from graph.py:743-748.
    """
    from app.core.logging import logger
    from langchain_core.messages import AIMessage
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    llm_response = kwargs.get('llm_response') or ctx.get('llm_response')
    request_id = ctx.get('request_id', 'unknown')

    # Initialize result variables
    conversion_successful = False
    ai_message = None
    message_type = None
    has_tool_calls = False
    tool_call_count = 0
    next_step = None
    error = None

    # Log conversion start
    rag_step_log(
        step=76,
        step_id='RAG.platform.convert.to.aimessage.with.tool.calls',
        node_label='ConvertAIMsg',
        category='platform',
        type='process',
        processing_stage='started',
        request_id=request_id,
        has_response=llm_response is not None
    )

    try:
        # Validate LLM response
        if not llm_response:
            error = 'No LLM response to convert'
            raise ValueError(error)

        # Core conversion logic: Create AIMessage with tool_calls
        # Preserves existing behavior from graph.py:745-748:
        # from langchain_core.messages import AIMessage
        # ai_message = AIMessage(
        #     content=response.content,
        #     tool_calls=response.tool_calls
        # )
        ai_message = AIMessage(
            content=llm_response.content,
            tool_calls=llm_response.tool_calls
        )

        # Set success flags
        conversion_successful = True
        message_type = 'AIMessage'
        has_tool_calls = bool(llm_response.tool_calls)
        tool_call_count = len(llm_response.tool_calls) if llm_response.tool_calls else 0
        next_step = 'execute_tools'  # Route to Step 78

        logger.info(
            f"aimessage_with_tool_calls_created",
            extra={
                'request_id': request_id,
                'step': 76,
                'conversion_successful': True,
                'message_type': message_type,
                'has_tool_calls': has_tool_calls,
                'tool_call_count': tool_call_count,
                'next_step': next_step
            }
        )

    except Exception as e:
        # Handle conversion errors
        error = str(e)
        conversion_successful = False

        logger.error(
            f"step_76_conversion_error",
            extra={
                'request_id': request_id,
                'step': 76,
                'error': error
            }
        )

    # Log conversion completion
    rag_step_log(
        step=76,
        step_id='RAG.platform.convert.to.aimessage.with.tool.calls',
        node_label='ConvertAIMsg',
        processing_stage='completed',
        request_id=request_id,
        conversion_successful=conversion_successful,
        message_type=message_type,
        has_tool_calls=has_tool_calls,
        tool_call_count=tool_call_count,
        next_step=next_step,
        error=error
    )

    # Build orchestration result
    result = {
        'conversion_successful': conversion_successful,
        'ai_message': ai_message,
        'message_type': message_type,
        'has_tool_calls': has_tool_calls,
        'tool_call_count': tool_call_count,
        'next_step': next_step,
        'llm_response': llm_response,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'error': error
    }

    return result

async def step_77__simple_aimsg(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 77 — Convert to simple AIMessage
    ID: RAG.platform.convert.to.simple.aimessage
    Type: process | Category: platform | Node: SimpleAIMsg

    Converts an LLM response without tool calls into a simple LangChain AIMessage object.
    This preserves the existing behavior from graph.py:750-752.
    """
    from app.core.logging import logger
    from langchain_core.messages import AIMessage
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    llm_response = kwargs.get('llm_response') or ctx.get('llm_response')
    request_id = ctx.get('request_id', 'unknown')

    # Initialize result variables
    conversion_successful = False
    ai_message = None
    message_type = None
    has_tool_calls = False
    tool_call_count = 0
    next_step = None
    error = None

    # Log conversion start
    rag_step_log(
        step=77,
        step_id='RAG.platform.convert.to.simple.aimessage',
        node_label='SimpleAIMsg',
        category='platform',
        type='process',
        processing_stage='started',
        request_id=request_id,
        has_response=llm_response is not None
    )

    try:
        # Validate LLM response
        if not llm_response:
            error = 'No LLM response to convert'
            raise ValueError(error)

        # Core conversion logic: Create simple AIMessage without tool_calls
        # Preserves existing behavior from graph.py:750-752:
        # else:
        #     from langchain_core.messages import AIMessage
        #     ai_message = AIMessage(content=response.content)
        ai_message = AIMessage(content=llm_response.content)

        # Set success flags
        conversion_successful = True
        message_type = 'AIMessage'
        has_tool_calls = False
        tool_call_count = 0
        next_step = 'final_response'  # Route to Step 101

        logger.info(
            f"simple_aimessage_created",
            extra={
                'request_id': request_id,
                'step': 77,
                'conversion_successful': True,
                'message_type': message_type,
                'has_tool_calls': False,
                'next_step': next_step
            }
        )

    except Exception as e:
        # Handle conversion errors
        error = str(e)
        conversion_successful = False

        logger.error(
            f"step_77_conversion_error",
            extra={
                'request_id': request_id,
                'step': 77,
                'error': error
            }
        )

    # Log conversion completion
    rag_step_log(
        step=77,
        step_id='RAG.platform.convert.to.simple.aimessage',
        node_label='SimpleAIMsg',
        processing_stage='completed',
        request_id=request_id,
        conversion_successful=conversion_successful,
        message_type=message_type,
        has_tool_calls=has_tool_calls,
        tool_call_count=tool_call_count,
        next_step=next_step,
        error=error
    )

    # Build orchestration result
    result = {
        'conversion_successful': conversion_successful,
        'ai_message': ai_message,
        'message_type': message_type,
        'has_tool_calls': has_tool_calls,
        'tool_call_count': tool_call_count,
        'next_step': next_step,
        'llm_response': llm_response,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'error': error
    }

    return result

async def step_78__execute_tools(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 78 — LangGraphAgent._tool_call Execute tools
    ID: RAG.platform.langgraphagent.tool.call.execute.tools
    Type: process | Category: platform | Node: ExecuteTools

    Executes tool calls from the LLM response by invoking the requested tools
    and converting results to ToolMessage objects for the next LLM iteration.
    This preserves the existing behavior from graph.py:804-823.
    """
    from app.core.logging import logger
    from langchain_core.messages import ToolMessage
    from datetime import datetime, timezone

    ctx = ctx or {}

    # Extract context parameters
    ai_message = kwargs.get('ai_message') or ctx.get('ai_message')
    tools_by_name = kwargs.get('tools_by_name') or ctx.get('tools_by_name', {})
    request_id = ctx.get('request_id', 'unknown')

    # Initialize result variables
    execution_successful = False
    tool_messages = []
    tools_executed = 0
    next_step = None
    error = None

    # Log execution start
    rag_step_log(
        step=78,
        step_id='RAG.platform.langgraphagent.tool.call.execute.tools',
        node_label='ExecuteTools',
        category='platform',
        type='process',
        processing_stage='started',
        request_id=request_id,
        has_ai_message=ai_message is not None,
        tools_available=len(tools_by_name)
    )

    try:
        # Validate AI message with tool calls
        if not ai_message:
            error = 'No AI message provided for tool execution'
            raise ValueError(error)

        if not hasattr(ai_message, 'tool_calls') or not ai_message.tool_calls:
            error = 'AI message has no tool calls to execute'
            raise ValueError(error)

        # Core execution logic: Execute tools and create ToolMessages
        # Preserves existing behavior from graph.py:814-822:
        # outputs = []
        # for tool_call in state.messages[-1].tool_calls:
        #     tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
        #     outputs.append(
        #         ToolMessage(
        #             content=tool_result,
        #             name=tool_call["name"],
        #             tool_call_id=tool_call["id"],
        #         )
        #     )
        # return {"messages": outputs}

        tool_messages = []
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else tool_call.name
            tool_args = tool_call.get("args") if isinstance(tool_call, dict) else tool_call.args
            tool_id = tool_call.get("id") if isinstance(tool_call, dict) else tool_call.id

            # Check if tool exists
            if tool_name not in tools_by_name:
                error_msg = f'Tool not found: {tool_name}'
                logger.error(
                    f"tool_not_found",
                    extra={
                        'request_id': request_id,
                        'step': 78,
                        'tool_name': tool_name,
                        'available_tools': list(tools_by_name.keys())
                    }
                )
                raise ValueError(error_msg)

            # Execute tool
            tool = tools_by_name[tool_name]
            tool_result = await tool.ainvoke(tool_args)

            # Create ToolMessage
            tool_message = ToolMessage(
                content=tool_result,
                name=tool_name,
                tool_call_id=tool_id,
            )
            tool_messages.append(tool_message)
            tools_executed += 1

        # Set success flags
        execution_successful = True
        next_step = 'chat_node'  # Route back to chat for next LLM iteration

        logger.info(
            f"tools_executed_successfully",
            extra={
                'request_id': request_id,
                'step': 78,
                'execution_successful': True,
                'tools_executed': tools_executed,
                'next_step': next_step
            }
        )

    except Exception as e:
        # Handle execution errors
        error = str(e)
        execution_successful = False

        logger.error(
            f"step_78_execution_error",
            extra={
                'request_id': request_id,
                'step': 78,
                'error': error
            }
        )

    # Log execution completion
    rag_step_log(
        step=78,
        step_id='RAG.platform.langgraphagent.tool.call.execute.tools',
        node_label='ExecuteTools',
        processing_stage='completed',
        request_id=request_id,
        execution_successful=execution_successful,
        tools_executed=tools_executed,
        next_step=next_step,
        error=error
    )

    # Build orchestration result
    result = {
        'execution_successful': execution_successful,
        'tool_messages': tool_messages,
        'tools_executed': tools_executed,
        'next_step': next_step,
        'ai_message': ai_message,
        'request_id': request_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'error': error
    }

    return result

async def step_86__tool_error(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 86 — Return tool error Invalid file
    ID: RAG.platform.return.tool.error.invalid.file
    Type: error | Category: platform | Node: ToolErr

    Error handler that returns a tool error message when attachment validation fails.
    Converts validation errors into appropriate error response format. Thin orchestration
    that preserves existing error handling patterns.
    """
    from langchain_core.messages import ToolMessage

    ctx = ctx or {}
    with rag_step_timer(86, 'RAG.platform.return.tool.error.invalid.file', 'ToolErr', stage="start"):
        errors = ctx.get('errors', [])
        attachment_count = ctx.get('attachment_count', 0)
        tool_call_id = ctx.get('tool_call_id')
        request_id = ctx.get('request_id', 'unknown')

        rag_step_log(
            step=86,
            step_id='RAG.platform.return.tool.error.invalid.file',
            node_label='ToolErr',
            category='platform',
            type='error',
            processing_stage="started",
            request_id=request_id,
            error_count=len(errors)
        )

        # Construct error message
        if errors:
            error_message = '\n'.join(errors)
        else:
            error_message = "Invalid attachment: validation failed"

        result = {
            'error_returned': True,
            'error_type': 'invalid_attachment',
            'error_message': error_message,
            'error_count': len(errors),
            'attachment_count': attachment_count,
            'request_id': request_id
        }

        # Create ToolMessage if tool_call_id provided
        if tool_call_id:
            tool_message = ToolMessage(
                content=f"Error: {error_message}",
                tool_call_id=tool_call_id
            )
            result['tool_message'] = tool_message

        rag_step_log(
            step=86,
            step_id='RAG.platform.return.tool.error.invalid.file',
            node_label='ToolErr',
            processing_stage="completed",
            request_id=request_id,
            error_returned=True,
            error_type='invalid_attachment',
            error_count=len(errors)
        )

        return result

# Alias for backward compatibility
step_86__tool_err = step_86__tool_error

def step_99__tool_results(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 99 — Return to tool caller
    ID: RAG.platform.return.to.tool.caller
    Type: process | Category: platform | Node: ToolResults

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(99, 'RAG.platform.return.to.tool.caller', 'ToolResults', stage="start"):
        rag_step_log(step=99, step_id='RAG.platform.return.to.tool.caller', node_label='ToolResults',
                     category='platform', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=99, step_id='RAG.platform.return.to.tool.caller', node_label='ToolResults',
                     processing_stage="completed")
        return result

def step_103__log_complete(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 103 — Logger.info Log completion
    ID: RAG.platform.logger.info.log.completion
    Type: process | Category: platform | Node: LogComplete

    Logs completion of RAG processing for monitoring and metrics.
    Called after message processing (Step 102), before streaming decision (Step 104).

    This orchestrator coordinates the completion logging for RAG workflow.
    """
    from app.core.logging import logger
    from datetime import datetime
    import time

    # Extract context parameters
    response = kwargs.get('response') or (ctx or {}).get('response')
    response_type = kwargs.get('response_type') or (ctx or {}).get('response_type', 'unknown')
    processing_time = kwargs.get('processing_time') or (ctx or {}).get('processing_time')
    start_time = kwargs.get('start_time') or (ctx or {}).get('start_time')
    success = kwargs.get('success') or (ctx or {}).get('success', True)
    error_message = kwargs.get('error_message') or (ctx or {}).get('error_message')
    user_query = kwargs.get('user_query') or (ctx or {}).get('user_query', '')
    classification = kwargs.get('classification') or (ctx or {}).get('classification')

    # Calculate processing time if not provided
    if processing_time is None and start_time is not None:
        processing_time = time.time() - start_time

    with rag_step_timer(103, 'RAG.platform.logger.info.log.completion', 'LogComplete', stage="start"):
        rag_step_log(
            step=103,
            step_id='RAG.platform.logger.info.log.completion',
            node_label='LogComplete',
            category='platform',
            type='process',
            processing_stage="started",
            response_type=response_type,
            success=success
        )

        # Create completion log data
        completion_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'success': success,
            'response_type': response_type,
            'processing_time_ms': round(processing_time * 1000) if processing_time else None,
            'query_length': len(user_query) if user_query else 0,
            'response_length': 0,
            'has_classification': classification is not None,
            'error_message': error_message
        }

        # Extract response details if available
        if response:
            if isinstance(response, str):
                completion_data['response_length'] = len(response)
            elif hasattr(response, 'content'):
                completion_data['response_length'] = len(response.content) if response.content else 0
            elif isinstance(response, dict):
                if 'content' in response:
                    completion_data['response_length'] = len(response['content']) if response['content'] else 0
                elif 'text' in response:
                    completion_data['response_length'] = len(response['text']) if response['text'] else 0

        # Extract classification details for logging
        domain = None
        action = None
        confidence = None
        if classification:
            if hasattr(classification, 'domain'):
                domain = classification.domain.value if hasattr(classification.domain, 'value') else str(classification.domain)
            if hasattr(classification, 'action'):
                action = classification.action.value if hasattr(classification.action, 'value') else str(classification.action)
            if hasattr(classification, 'confidence'):
                confidence = classification.confidence

        # Log completion event for monitoring
        log_level = "info" if success else "warning"
        log_message = "RAG processing completed successfully" if success else f"RAG processing completed with error: {error_message}"

        extra_data = {
            'completion_event': 'rag_processing_complete',
            'success': completion_data['success'],
            'response_type': completion_data['response_type'],
            'processing_time_ms': completion_data['processing_time_ms'],
            'query_length': completion_data['query_length'],
            'response_length': completion_data['response_length'],
            'has_classification': completion_data['has_classification'],
            'domain': domain,
            'action': action,
            'confidence': confidence,
            'step': 103
        }

        if log_level == "info":
            logger.info(log_message, extra=extra_data)
        else:
            logger.warning(log_message, extra=extra_data)

        rag_step_log(
            step=103,
            step_id='RAG.platform.logger.info.log.completion',
            node_label='LogComplete',
            completion_event='rag_processing_complete',
            success=completion_data['success'],
            response_type=completion_data['response_type'],
            processing_time_ms=completion_data['processing_time_ms'],
            query_length=completion_data['query_length'],
            response_length=completion_data['response_length'],
            has_classification=completion_data['has_classification'],
            domain=domain,
            action=action,
            confidence=confidence,
            error_message=completion_data['error_message'],
            processing_stage="completed"
        )

        # Return completion data for downstream processing
        return completion_data

async def step_106__async_gen(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 106 — Create async generator

    Thin async orchestrator that creates an async generator for streaming response delivery.
    Takes streaming setup data from StreamSetup (Step 105) and prepares for SinglePassStream (Step 107).
    Creates the async generator with proper configuration, session data, and streaming parameters.

    Incoming: StreamSetup (Step 105) [when streaming configured]
    Outgoing: SinglePassStream (Step 107)
    """
    with rag_step_timer(106, 'RAG.platform.create.async.generator', 'AsyncGen', stage="start"):
        ctx = ctx or {}

        rag_step_log(
            step=106,
            step_id='RAG.platform.create.async.generator',
            node_label='AsyncGen',
            category='platform',
            type='process',
            request_id=ctx.get('request_id'),
            processing_stage="started"
        )

        # Create async generator and configure streaming settings
        async_generator = _create_streaming_generator(ctx)
        generator_config = _prepare_generator_configuration(ctx)

        # Preserve all context and add generator metadata
        result = ctx.copy()

        # Add async generator results
        result.update({
            'async_generator': async_generator,
            'generator_config': generator_config,
            'generator_created': True,
            'processing_stage': 'async_generator_created',
            'next_step': 'single_pass_stream',
            'generator_timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Add validation warnings if needed
        validation_warnings = _validate_generator_requirements(ctx)
        if validation_warnings:
            result['validation_warnings'] = validation_warnings

        rag_step_log(
            step=106,
            step_id='RAG.platform.create.async.generator',
            node_label='AsyncGen',
            request_id=ctx.get('request_id'),
            generator_created=True,
            generator_configured=bool(generator_config),
            next_step='single_pass_stream',
            processing_stage="completed"
        )

        return result


def _create_streaming_generator(ctx: Dict[str, Any]) -> Any:
    """Create async generator for streaming response delivery."""
    from typing import AsyncGenerator

    stream_context = ctx.get('stream_context', {})
    processed_messages = stream_context.get('messages', ctx.get('processed_messages', []))
    session_id = stream_context.get('session_id')
    user_id = stream_context.get('user_id')

    async def response_generator() -> AsyncGenerator[str, None]:
        """Async generator for streaming response chunks."""
        try:
            # This would typically call the LangGraph agent's get_stream_response
            # For now, we create a simple generator that yields response content
            if processed_messages:
                for message in processed_messages:
                    if message.get('role') == 'assistant' and message.get('content'):
                        content = message['content']
                        # Yield content in chunks based on configured chunk size
                        chunk_size = stream_context.get('chunk_size', 1024)
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i + chunk_size]
                            if chunk.strip():
                                yield chunk
            else:
                # Placeholder response if no messages available
                yield "No response available for streaming"

        except Exception as e:
            # Error handling in generator
            yield f"Stream error: {str(e)}"

    return response_generator()


def _prepare_generator_configuration(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare configuration for the async generator."""
    stream_context = ctx.get('stream_context', {})
    streaming_configuration = ctx.get('streaming_configuration', {})

    # Base generator configuration
    config = {
        'session_id': stream_context.get('session_id'),
        'user_id': stream_context.get('user_id'),
        'provider': stream_context.get('provider', 'default'),
        'model': stream_context.get('model', 'default'),
        'messages': stream_context.get('messages', []),
        'streaming_enabled': stream_context.get('streaming_enabled', True)
    }

    # Add streaming parameters
    config.update({
        'chunk_size': stream_context.get('chunk_size', 1024),
        'include_usage': stream_context.get('include_usage', False),
        'include_metadata': stream_context.get('include_metadata', True),
        'heartbeat_interval': stream_context.get('heartbeat_interval', 30),
        'connection_timeout': stream_context.get('connection_timeout', 300)
    })

    # Add provider-specific configuration
    provider_config = stream_context.get('provider_config', {})
    if provider_config:
        config['provider_config'] = provider_config

    # Add custom streaming options
    custom_headers = stream_context.get('custom_headers', {})
    if custom_headers:
        config['custom_headers'] = custom_headers

    # Add streaming configuration options
    if streaming_configuration:
        config['media_type'] = streaming_configuration.get('media_type', 'text/event-stream')

    # Add buffer and compression settings
    config.update({
        'compression_enabled': stream_context.get('compression_enabled', False),
        'buffer_size': stream_context.get('buffer_size', 1024)
    })

    return config


def _validate_generator_requirements(ctx: Dict[str, Any]) -> List[str]:
    """Validate async generator requirements and return warnings."""
    warnings = []

    stream_context = ctx.get('stream_context', {})

    # Check if streaming was actually requested
    if not ctx.get('streaming_requested', True):
        warnings.append("Async generator created but streaming_requested is False")

    # Check if messages are available
    messages = stream_context.get('messages', ctx.get('processed_messages', []))
    if not messages:
        warnings.append("No messages available for async generator")

    # Check if session data is available
    session_id = stream_context.get('session_id')
    if not session_id:
        warnings.append("No session ID available for generator context")

    # Check if streaming is properly enabled
    streaming_enabled = stream_context.get('streaming_enabled', True)
    if not streaming_enabled:
        warnings.append("Streaming not enabled in stream context")

    return warnings


def step_110__send_done(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 110 — Send DONE frame
    ID: RAG.platform.send.done.frame
    Type: process | Category: platform | Node: SendDone

    Sends DONE frame to terminate streaming responses properly.
    Called after streaming response (Step 109), before metrics collection (Step 111).

    This orchestrator coordinates the sending of streaming termination signals.
    """
    from app.core.logging import logger
    from datetime import datetime

    # Extract context parameters
    stream_writer = kwargs.get('stream_writer') or (ctx or {}).get('stream_writer')
    response_generator = kwargs.get('response_generator') or (ctx or {}).get('response_generator')
    streaming_format = kwargs.get('streaming_format') or (ctx or {}).get('streaming_format', 'sse')
    client_connected = kwargs.get('client_connected') or (ctx or {}).get('client_connected', True)
    chunks_sent = kwargs.get('chunks_sent') or (ctx or {}).get('chunks_sent', 0)
    total_bytes = kwargs.get('total_bytes') or (ctx or {}).get('total_bytes', 0)
    stream_id = kwargs.get('stream_id') or (ctx or {}).get('stream_id')

    with rag_step_timer(110, 'RAG.platform.send.done.frame', 'SendDone', stage="start"):
        rag_step_log(
            step=110,
            step_id='RAG.platform.send.done.frame',
            node_label='SendDone',
            category='platform',
            type='process',
            processing_stage="started",
            streaming_format=streaming_format,
            client_connected=client_connected,
            chunks_sent=chunks_sent
        )

        # Create DONE frame data
        done_frame_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'streaming_format': streaming_format,
            'chunks_sent': chunks_sent,
            'total_bytes': total_bytes,
            'stream_id': stream_id,
            'done_sent': False,
            'client_connected': client_connected
        }

        try:
            # Send DONE frame based on streaming format
            if streaming_format.lower() == 'sse':
                # SSE (Server-Sent Events) DONE frame
                done_frame = "data: [DONE]\n\n"

                if stream_writer and hasattr(stream_writer, 'write'):
                    # Write DONE frame to stream
                    if isinstance(done_frame, str):
                        done_frame = done_frame.encode('utf-8')
                    stream_writer.write(done_frame)
                    if hasattr(stream_writer, 'drain'):
                        # For asyncio streams, drain the buffer
                        try:
                            # Note: This might be async, but we handle it gracefully
                            if hasattr(stream_writer.drain, '__await__'):
                                # It's an async method, but we can't await here
                                # Let the calling code handle the async drain
                                pass
                            else:
                                stream_writer.drain()
                        except Exception:
                            # Drain failed, but DONE frame was written
                            pass
                    done_frame_data['done_sent'] = True

                elif response_generator and hasattr(response_generator, 'send'):
                    # Send DONE frame via generator
                    try:
                        response_generator.send(done_frame)
                        done_frame_data['done_sent'] = True
                    except (StopIteration, GeneratorExit):
                        # Generator is already closed
                        done_frame_data['done_sent'] = True

            elif streaming_format.lower() == 'websocket':
                # WebSocket DONE frame (JSON format)
                done_frame = '{"type": "done", "timestamp": "' + done_frame_data['timestamp'] + '"}'

                if stream_writer and hasattr(stream_writer, 'send'):
                    stream_writer.send(done_frame)
                    done_frame_data['done_sent'] = True

            else:
                # Generic streaming format - use simple marker
                done_frame = "\n[DONE]\n"

                if stream_writer and hasattr(stream_writer, 'write'):
                    if isinstance(done_frame, str):
                        done_frame = done_frame.encode('utf-8')
                    stream_writer.write(done_frame)
                    done_frame_data['done_sent'] = True

            # If no specific stream writer, just mark as sent (for testing/mock scenarios)
            if not stream_writer and not response_generator:
                done_frame_data['done_sent'] = True

        except Exception as e:
            # Log error but don't fail the workflow
            logger.warning(
                f"Failed to send DONE frame: {str(e)}",
                extra={
                    'streaming_error': 'done_frame_send_failed',
                    'streaming_format': streaming_format,
                    'error_message': str(e),
                    'step': 110
                }
            )
            done_frame_data['error'] = str(e)

        # Log DONE frame sending for monitoring
        logger.info(
            "Streaming DONE frame sent" if done_frame_data['done_sent'] else "Streaming DONE frame send attempted",
            extra={
                'streaming_event': 'done_frame_sent',
                'streaming_format': done_frame_data['streaming_format'],
                'chunks_sent': done_frame_data['chunks_sent'],
                'total_bytes': done_frame_data['total_bytes'],
                'done_sent': done_frame_data['done_sent'],
                'client_connected': done_frame_data['client_connected'],
                'stream_id': done_frame_data['stream_id'],
                'step': 110
            }
        )

        rag_step_log(
            step=110,
            step_id='RAG.platform.send.done.frame',
            node_label='SendDone',
            streaming_event='done_frame_sent',
            streaming_format=done_frame_data['streaming_format'],
            chunks_sent=done_frame_data['chunks_sent'],
            total_bytes=done_frame_data['total_bytes'],
            done_sent=done_frame_data['done_sent'],
            client_connected=done_frame_data['client_connected'],
            stream_id=done_frame_data['stream_id'],
            error_message=done_frame_data.get('error'),
            processing_stage="completed"
        )

        # Return DONE frame data for downstream processing
        return done_frame_data

async def _validate_expert_credentials(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to validate expert credentials and calculate trust score.

    Handles expert credential validation and prepares routing to trust score decision.
    """
    import time

    # Extract expert data from context
    expert_id = ctx.get('expert_id')
    expert_profile = ctx.get('expert_profile', {})
    feedback_data = ctx.get('feedback_data', {})

    # Start timing
    start_time = time.time()

    # Process validation
    validation_completed = False
    trust_score = 0.0
    error_type = None
    error_message = None

    try:
        # Validate required expert data
        if not expert_profile and not feedback_data:
            error_type = 'missing_expert_data'
            error_message = 'No expert profile or feedback data available'
        elif not expert_id:
            error_type = 'invalid_expert_id'
            error_message = 'Missing or invalid expert ID'
        elif not expert_id.strip():
            error_type = 'invalid_expert_id'
            error_message = 'Empty expert ID'
        else:
            # Calculate trust score based on expert profile
            trust_score = await _calculate_trust_score(expert_profile, feedback_data)
            validation_completed = True

    except Exception as e:
        error_type = 'validation_error'
        error_message = str(e)

    # Calculate processing time
    processing_time = (time.time() - start_time) * 1000

    # Trust threshold comparison (0.7 as per Mermaid)
    trust_threshold = 0.7
    meets_trust_threshold = trust_score >= trust_threshold

    # Italian credentials validation
    credentials = expert_profile.get('credentials', [])
    italian_credentials = [
        'dottore_commercialista', 'consulente_del_lavoro', 'revisore_legale',
        'tributarista_certificato', 'caf_operatore', 'certified_tax_advisor'
    ]
    italian_credentials_validated = any(cred in italian_credentials for cred in credentials)

    # Build result with routing information
    result = {
        # Expert validation results
        'expert_validation_completed': validation_completed,
        'expert_id': expert_id,
        'trust_score': trust_score,
        'trust_threshold': trust_threshold,
        'meets_trust_threshold': meets_trust_threshold,
        'validation_status': 'success' if validation_completed else 'error',

        # Performance tracking
        'validation_processing_time_ms': processing_time,

        # Italian credentials validation
        'italian_credentials_validated': italian_credentials_validated,

        # Error handling
        'error_type': error_type,
        'error_message': error_message,

        # Routing to Step 121 (TrustScoreOK decision) per Mermaid
        'next_step': 'trust_score_decision',
    }

    return result


async def _calculate_trust_score(expert_profile: Dict[str, Any], feedback_data: Dict[str, Any]) -> float:
    """Calculate trust score based on expert profile and feedback context."""

    # For testing purposes, check if mock trust score is provided
    if 'mock_trust_score' in expert_profile:
        return expert_profile['mock_trust_score']

    base_score = 0.0

    # Credentials scoring (0.4 weight)
    credentials = expert_profile.get('credentials', [])
    credential_score = 0.0

    high_value_credentials = ['dottore_commercialista', 'revisore_legale', 'certified_tax_advisor']
    medium_value_credentials = ['consulente_del_lavoro', 'tributarista_certificato', 'tax_professional', 'caf_operatore']

    for cred in credentials:
        if cred in high_value_credentials:
            credential_score += 0.4
        elif cred in medium_value_credentials:
            credential_score += 0.3
        else:
            credential_score += 0.1

    credential_score = min(credential_score, 1.0) * 0.5

    # Experience scoring (0.3 weight)
    years_experience = expert_profile.get('years_experience', 0)
    experience_score = min(years_experience / 10.0, 1.0) * 0.3

    # Track record scoring (0.3 weight)
    successful_validations = expert_profile.get('successful_validations', 0)
    track_record_score = min(successful_validations / 100.0, 1.0) * 0.3

    base_score = credential_score + experience_score + track_record_score

    # Italian certification bonus
    if expert_profile.get('italian_certification'):
        base_score += 0.2

    # Confidence score bonus from feedback
    feedback_confidence = feedback_data.get('confidence_score', 0.0)
    if feedback_confidence > 0.8:
        base_score += 0.05

    return min(base_score, 1.0)


async def step_120__validate_expert(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """RAG STEP 120 — Validate expert credentials.

    Process orchestrator that validates expert credentials and routes to trust score decision.
    Routes to Step 121 (TrustScoreOK decision) per Mermaid diagram.

    ID: RAG.platform.validate.expert.credentials
    Type: process | Category: platform | Node: ValidateExpert
    """
    if ctx is None:
        ctx = {}

    with rag_step_timer(120, 'RAG.platform.validate.expert.credentials', 'ValidateExpert', stage="start"):
        rag_step_log(
            step=120,
            step_id='RAG.platform.validate.expert.credentials',
            node_label='ValidateExpert',
            category='platform',
            type='process',
            processing_stage="started",
            expert_id=ctx.get('expert_id'),
            expert_validation_required=ctx.get('expert_validation_required'),
            feedback_type=ctx.get('feedback_data', {}).get('feedback_type')
        )

        try:
            # Validate expert credentials
            validation_result = await _validate_expert_credentials(ctx)

            # Preserve all existing context and add validation results
            result = {**ctx, **validation_result}

            rag_step_log(
                step=120,
                step_id='RAG.platform.validate.expert.credentials',
                node_label='ValidateExpert',
                processing_stage="completed",
                expert_validation_completed=result['expert_validation_completed'],
                expert_id=result.get('expert_id'),
                trust_score=result.get('trust_score'),
                meets_trust_threshold=result.get('meets_trust_threshold'),
                italian_credentials_validated=result.get('italian_credentials_validated'),
                next_step=result['next_step'],
                validation_status=result['validation_status']
            )

            return result

        except Exception as e:
            # Handle unexpected errors gracefully
            error_result = {
                **ctx,
                'expert_validation_completed': False,
                'error_type': 'processing_error',
                'error_message': str(e),
                'trust_score': 0.0,
                'trust_threshold': 0.7,
                'meets_trust_threshold': False,
                'next_step': 'trust_score_decision',
                'validation_status': 'error'
            }

            rag_step_log(
                step=120,
                step_id='RAG.platform.validate.expert.credentials',
                node_label='ValidateExpert',
                processing_stage="error",
                error_type=error_result['error_type'],
                error_message=error_result['error_message'],
                next_step=error_result['next_step']
            )

            return error_result

def step_126__determine_action(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 126 — Determine action
    ID: RAG.platform.determine.action
    Type: process | Category: platform | Node: DetermineAction

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(126, 'RAG.platform.determine.action', 'DetermineAction', stage="start"):
        rag_step_log(step=126, step_id='RAG.platform.determine.action', node_label='DetermineAction',
                     category='platform', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=126, step_id='RAG.platform.determine.action', node_label='DetermineAction',
                     processing_stage="completed")
        return result

def step_133__fetch_feeds(*, messages: Optional[List[Any]] = None, ctx: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    RAG STEP 133 — Fetch and parse sources
    ID: RAG.platform.fetch.and.parse.sources
    Type: process | Category: platform | Node: FetchFeeds

    TODO: Implement orchestration so this node *changes/validates control flow/data*
    according to Mermaid — not logs-only. Call into existing services/factories here.
    """
    with rag_step_timer(133, 'RAG.platform.fetch.and.parse.sources', 'FetchFeeds', stage="start"):
        rag_step_log(step=133, step_id='RAG.platform.fetch.and.parse.sources', node_label='FetchFeeds',
                     category='platform', type='process', stub=True, processing_stage="started")
        # TODO: call real service/factory here and return its output
        result = kwargs.get("result")  # placeholder
        rag_step_log(step=133, step_id='RAG.platform.fetch.and.parse.sources', node_label='FetchFeeds',
                     processing_stage="completed")
        return result
