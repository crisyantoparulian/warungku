import os
import hmac
import hashlib
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/", "/health", "/test"]
        self.api_key = os.getenv("API_SECRET_KEY")

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Check API key in header
        api_key = request.headers.get("X-API-Key")
        if not api_key or not self._verify_api_key(api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )

        return await call_next(request)

    def _verify_api_key(self, provided_key: str) -> bool:
        """Verify the provided API key"""
        if not self.api_key:
            return False

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(
            provided_key.encode(),
            self.api_key.encode()
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        current_time = int(time.time())

        # Clean old requests (older than 1 minute)
        self._cleanup_old_requests(current_time)

        # Check rate limit
        if client_ip in self.requests:
            if len(self.requests[client_ip]) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "limit": self.requests_per_minute,
                        "window": "1 minute"
                    }
                )

        # Add current request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded IP first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host

    def _cleanup_old_requests(self, current_time: int):
        """Remove requests older than 1 minute"""
        cutoff_time = current_time - 60
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req_time for req_time in self.requests[ip]
                if req_time > cutoff_time
            ]

            # Remove empty entries
            if not self.requests[ip]:
                del self.requests[ip]


import time