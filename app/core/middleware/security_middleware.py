"""Security middleware for request monitoring and threat detection."""

import time
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.core.security import security_monitor, security_audit_logger
from app.core.security.audit_logger import SecurityEventType, SecuritySeverity


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security monitoring and threat detection."""
    
    def __init__(self, app, enabled: bool = True):
        """Initialize security middleware.
        
        Args:
            app: FastAPI application
            enabled: Whether security monitoring is enabled
        """
        super().__init__(app)
        self.enabled = enabled
        self.monitored_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/payments/",
            "/api/v1/security/",
            "/api/v1/italian/",
            "/api/v1/search/"
        }
        self.sensitive_endpoints = {
            "/api/v1/payments/webhook",
            "/api/v1/security/api-keys/",
            "/api/v1/auth/refresh"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            HTTP response
        """
        if not self.enabled:
            return await call_next(request)
        
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        try:
            # Pre-request security checks
            await self._pre_request_checks(request, client_ip, user_agent)
            
            # Process request
            response = await call_next(request)
            
            # Post-request security monitoring
            await self._post_request_monitoring(
                request, response, client_ip, user_agent, start_time
            )
            
            return response
            
        except HTTPException as e:
            # Log security-related HTTP exceptions
            await self._log_security_exception(request, e, client_ip, user_agent)
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(
                "security_middleware_error",
                path=str(request.url.path),
                method=request.method,
                client_ip=client_ip,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _pre_request_checks(
        self, 
        request: Request, 
        client_ip: str, 
        user_agent: str
    ) -> None:
        """Perform pre-request security checks.
        
        Args:
            request: HTTP request
            client_ip: Client IP address
            user_agent: User agent string
            
        Raises:
            HTTPException: If request is blocked
        """
        # Check if IP is blocked
        if security_monitor.is_ip_blocked(client_ip):
            logger.warning(
                "blocked_ip_request_attempted",
                client_ip=client_ip,
                path=str(request.url.path),
                method=request.method
            )
            
            await security_audit_logger.log_security_event(
                event_type=SecurityEventType.ACCESS_DENIED,
                severity=SecuritySeverity.HIGH,
                ip_address=client_ip,
                user_agent=user_agent,
                resource=str(request.url.path),
                action=request.method.lower(),
                outcome="blocked_ip",
                details={"reason": "IP address blocked by security system"}
            )
            
            raise HTTPException(
                status_code=403,
                detail="Access denied by security system"
            )
        
        # Check rate limiting
        if security_monitor.is_rate_limited(client_ip):
            logger.warning(
                "rate_limited_request_attempted",
                client_ip=client_ip,
                path=str(request.url.path)
            )
            
            await security_audit_logger.log_security_event(
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                severity=SecuritySeverity.MEDIUM,
                ip_address=client_ip,
                user_agent=user_agent,
                resource=str(request.url.path),
                action=request.method.lower(),
                outcome="rate_limited"
            )
            
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        # Check for suspicious patterns
        await self._check_suspicious_patterns(request, client_ip, user_agent)
    
    async def _check_suspicious_patterns(
        self,
        request: Request,
        client_ip: str,
        user_agent: str
    ) -> None:
        """Check for suspicious request patterns.
        
        Args:
            request: HTTP request
            client_ip: Client IP address
            user_agent: User agent string
        """
        path = str(request.url.path)
        
        # Check for common attack patterns
        suspicious_patterns = [
            "../",  # Path traversal
            "<script",  # XSS
            "union select",  # SQL injection
            "drop table",  # SQL injection
            "eval(",  # Code injection
            "base64_decode",  # Code injection
        ]
        
        query_string = str(request.url.query).lower()
        path_lower = path.lower()
        
        for pattern in suspicious_patterns:
            if pattern in path_lower or pattern in query_string:
                logger.warning(
                    "suspicious_pattern_detected",
                    client_ip=client_ip,
                    path=path,
                    pattern=pattern,
                    user_agent=user_agent[:100]
                )
                
                await security_audit_logger.log_security_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    severity=SecuritySeverity.HIGH,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    resource=path,
                    action="suspicious_request",
                    outcome="detected",
                    details={
                        "pattern": pattern,
                        "query_string": query_string[:200]
                    }
                )
                
                # Process as potential threat
                await security_monitor.process_security_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    ip_address=client_ip,
                    outcome="detected",
                    details={
                        "pattern": pattern,
                        "path": path,
                        "user_agent": user_agent[:100]
                    }
                )
                break
        
        # Check for automated/bot behavior
        if self._detect_bot_behavior(user_agent, request):
            await security_audit_logger.log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=SecuritySeverity.MEDIUM,
                ip_address=client_ip,
                user_agent=user_agent,
                resource=path,
                action="bot_detected",
                outcome="flagged",
                details={"detection_reason": "automated_behavior"}
            )
    
    def _detect_bot_behavior(self, user_agent: str, request: Request) -> bool:
        """Detect potential bot/automated behavior.
        
        Args:
            user_agent: User agent string
            request: HTTP request
            
        Returns:
            True if bot behavior detected
        """
        # Common bot indicators
        bot_indicators = [
            "bot", "crawler", "spider", "scraper", "python-requests",
            "curl", "wget", "libwww", "httpclient", "scan"
        ]
        
        user_agent_lower = user_agent.lower()
        
        # Check user agent
        for indicator in bot_indicators:
            if indicator in user_agent_lower:
                return True
        
        # Check for missing common headers
        if not request.headers.get("accept"):
            return True
        
        # Check for unusual header combinations
        if not request.headers.get("accept-language") and request.headers.get("accept"):
            return True
        
        return False
    
    async def _post_request_monitoring(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str,
        start_time: float
    ) -> None:
        """Perform post-request security monitoring.
        
        Args:
            request: HTTP request
            response: HTTP response
            client_ip: Client IP address
            user_agent: User agent string
            start_time: Request start time
        """
        path = str(request.url.path)
        method = request.method
        status_code = response.status_code
        duration = time.time() - start_time
        
        # Monitor authentication endpoints
        if path in ["/api/v1/auth/login", "/api/v1/auth/register"]:
            await self._monitor_auth_endpoint(
                request, response, client_ip, user_agent, path
            )
        
        # Monitor payment endpoints
        elif path.startswith("/api/v1/payments/"):
            await self._monitor_payment_endpoint(
                request, response, client_ip, user_agent, path
            )
        
        # Monitor API key endpoints
        elif path.startswith("/api/v1/security/api-keys/"):
            await self._monitor_api_key_endpoint(
                request, response, client_ip, user_agent, path
            )
        
        # Monitor for slow requests (potential DoS)
        if duration > 30.0:  # 30 seconds
            logger.warning(
                "slow_request_detected",
                client_ip=client_ip,
                path=path,
                method=method,
                duration=duration,
                status_code=status_code
            )
            
            await security_audit_logger.log_security_event(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=SecuritySeverity.MEDIUM,
                ip_address=client_ip,
                user_agent=user_agent,
                resource=path,
                action="slow_request",
                outcome="detected",
                details={
                    "duration_seconds": duration,
                    "status_code": status_code
                }
            )
        
        # Monitor high error rates
        if status_code >= 400:
            await self._monitor_error_response(
                request, response, client_ip, user_agent, path
            )
    
    async def _monitor_auth_endpoint(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str,
        path: str
    ) -> None:
        """Monitor authentication endpoints for security events."""
        status_code = response.status_code
        
        if path == "/api/v1/auth/login":
            if status_code == 200:
                # Successful login
                await security_monitor.process_security_event(
                    event_type=SecurityEventType.LOGIN_SUCCESS,
                    ip_address=client_ip,
                    outcome="success"
                )
            elif status_code in [401, 403]:
                # Failed login
                await security_monitor.process_security_event(
                    event_type=SecurityEventType.LOGIN_FAILURE,
                    ip_address=client_ip,
                    outcome="failure",
                    details={"status_code": status_code}
                )
        
        elif path == "/api/v1/auth/register":
            if status_code == 201:
                await security_audit_logger.log_authentication_event(
                    event_type=SecurityEventType.LOGIN_SUCCESS,  # Registration success
                    ip_address=client_ip,
                    user_agent=user_agent,
                    outcome="registration_success"
                )
    
    async def _monitor_payment_endpoint(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str,
        path: str
    ) -> None:
        """Monitor payment endpoints for security events."""
        status_code = response.status_code
        
        # Log payment-related security events
        if status_code == 200:
            outcome = "success"
        elif status_code in [400, 402, 403]:
            outcome = "failure"
        else:
            outcome = "unknown"
        
        await security_monitor.process_security_event(
            event_type=SecurityEventType.PAYMENT_ATTEMPT,
            ip_address=client_ip,
            outcome=outcome,
            details={
                "endpoint": path,
                "status_code": status_code
            }
        )
    
    async def _monitor_api_key_endpoint(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str,
        path: str
    ) -> None:
        """Monitor API key endpoints for security events."""
        method = request.method
        status_code = response.status_code
        
        # Determine event type based on endpoint and method
        if "generate" in path and method == "POST":
            event_type = SecurityEventType.API_KEY_CREATED
        elif "rotate" in path and method == "POST":
            event_type = SecurityEventType.API_KEY_ROTATED
        elif "revoke" in path and method == "POST":
            event_type = SecurityEventType.API_KEY_REVOKED
        else:
            event_type = SecurityEventType.ACCESS_GRANTED
        
        outcome = "success" if status_code < 400 else "failure"
        
        await security_monitor.process_security_event(
            event_type=event_type,
            ip_address=client_ip,
            outcome=outcome,
            details={
                "endpoint": path,
                "method": method,
                "status_code": status_code
            }
        )
    
    async def _monitor_error_response(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str,
        path: str
    ) -> None:
        """Monitor error responses for potential attacks."""
        status_code = response.status_code
        
        # Monitor for potential attacks based on error codes
        if status_code == 401:
            await security_monitor.process_security_event(
                event_type=SecurityEventType.ACCESS_DENIED,
                ip_address=client_ip,
                outcome="unauthorized",
                details={
                    "path": path,
                    "method": request.method
                }
            )
        elif status_code == 403:
            await security_monitor.process_security_event(
                event_type=SecurityEventType.ACCESS_DENIED,
                ip_address=client_ip,
                outcome="forbidden",
                details={
                    "path": path,
                    "method": request.method
                }
            )
        elif status_code == 429:
            await security_monitor.process_security_event(
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                ip_address=client_ip,
                outcome="rate_limited",
                details={
                    "path": path,
                    "method": request.method
                }
            )
    
    async def _log_security_exception(
        self,
        request: Request,
        exception: HTTPException,
        client_ip: str,
        user_agent: str
    ) -> None:
        """Log security-related HTTP exceptions."""
        path = str(request.url.path)
        status_code = exception.status_code
        
        # Determine security event type based on status code
        if status_code == 401:
            event_type = SecurityEventType.ACCESS_DENIED
            outcome = "unauthorized"
        elif status_code == 403:
            event_type = SecurityEventType.ACCESS_DENIED
            outcome = "forbidden"
        elif status_code == 429:
            event_type = SecurityEventType.RATE_LIMIT_EXCEEDED
            outcome = "rate_limited"
        else:
            event_type = SecurityEventType.SUSPICIOUS_ACTIVITY
            outcome = "http_error"
        
        await security_audit_logger.log_security_event(
            event_type=event_type,
            severity=SecuritySeverity.MEDIUM,
            ip_address=client_ip,
            user_agent=user_agent,
            resource=path,
            action=request.method.lower(),
            outcome=outcome,
            details={
                "status_code": status_code,
                "detail": str(exception.detail)
            }
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"