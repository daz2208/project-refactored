"""
Security Middleware for SyncBoard 3.0 Knowledge Bank.

Implements security best practices:
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- HTTPS enforcement for production
- Additional security hardening
"""

import os
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter
    - Strict-Transport-Security: Force HTTPS (production only)
    - Content-Security-Policy: Restrict resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    """
    
    def __init__(self, app: ASGIApp, environment: str = "development"):
        super().__init__(app)
        self.environment = environment
        self.is_production = environment == "production"
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        # Prevents browsers from interpreting files as a different MIME type
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking attacks
        # Prevents the page from being embedded in iframes
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable browser XSS filter
        # Legacy header, but still useful for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict-Transport-Security (HSTS): Force HTTPS
        # Only enable in production with HTTPS
        if self.is_production:
            # max-age=31536000 = 1 year
            # includeSubDomains = apply to all subdomains
            # preload = allow inclusion in browser HSTS preload list
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content-Security-Policy (CSP): Restrict resource loading
        # This is a restrictive policy - adjust based on your needs
        csp_policy = (
            "default-src 'self'; "  # Only load resources from same origin
            "script-src 'self' 'unsafe-inline'; "  # Allow inline scripts (needed for some frameworks)
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
            "img-src 'self' data: https:; "  # Allow images from same origin, data URIs, and HTTPS
            "font-src 'self' data:; "  # Allow fonts from same origin and data URIs
            "connect-src 'self'; "  # Allow AJAX requests to same origin
            "frame-ancestors 'none'; "  # Prevent embedding in iframes (same as X-Frame-Options)
            "base-uri 'self'; "  # Restrict <base> tag URLs
            "form-action 'self'; "  # Restrict form submission targets
            "upgrade-insecure-requests"  # Upgrade HTTP to HTTPS automatically
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Referrer-Policy: Control referrer information
        # no-referrer-when-downgrade = send referrer for HTTPS->HTTPS, but not HTTPS->HTTP
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy): Control browser features
        # Disable potentially dangerous features
        permissions_policy = (
            "geolocation=(), "  # Disable geolocation
            "microphone=(), "  # Disable microphone
            "camera=(), "  # Disable camera
            "payment=(), "  # Disable payment APIs
            "usb=(), "  # Disable USB access
            "magnetometer=(), "  # Disable magnetometer
            "gyroscope=(), "  # Disable gyroscope
            "accelerometer=()"  # Disable accelerometer
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        return response

# =============================================================================
# HTTPS Redirect Middleware
# =============================================================================

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirect HTTP requests to HTTPS in production.
    
    Only active when environment is 'production'.
    """
    
    def __init__(self, app: ASGIApp, environment: str = "development"):
        super().__init__(app)
        self.environment = environment
        self.is_production = environment == "production"
    
    async def dispatch(self, request: Request, call_next):
        # Only enforce HTTPS in production
        if self.is_production:
            # Check if request is HTTP (not HTTPS)
            if request.url.scheme == "http":
                # Build HTTPS URL
                https_url = request.url.replace(scheme="https")
                
                logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {https_url}")
                
                # Return 301 Permanent Redirect
                return Response(
                    status_code=301,
                    headers={"Location": str(https_url)}
                )
        
        # If HTTPS or not production, proceed normally
        response = await call_next(request)
        return response

# =============================================================================
# Helper Functions
# =============================================================================

def get_environment() -> str:
    """
    Get current environment from environment variable.
    
    Returns:
        "production", "staging", or "development"
    """
    env = os.environ.get("SYNCBOARD_ENVIRONMENT", "development").lower()
    
    # Validate environment
    valid_envs = ["production", "staging", "development"]
    if env not in valid_envs:
        logger.warning(f"Invalid environment '{env}', defaulting to 'development'")
        env = "development"
    
    return env

def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == "production"
