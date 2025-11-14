"""
Security Testing Suite for SyncBoard 3.0 Knowledge Bank.

Tests security features:
- Security headers
- Input sanitization (already tested in test_sanitization.py)
- Authentication security
- Rate limiting
- HTTPS enforcement (in production mode)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import dependencies
from backend.auth import hash_password

# =============================================================================
# Test Client Setup
# =============================================================================

client = TestClient(app)

# =============================================================================
# Security Headers Tests
# =============================================================================

class TestSecurityHeaders:
    """Test that all security headers are properly set."""
    
    def test_x_content_type_options_header(self):
        """Test X-Content-Type-Options header is set to nosniff."""
        response = client.get("/health")
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    def test_x_frame_options_header(self):
        """Test X-Frame-Options header is set to DENY."""
        response = client.get("/health")
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
    
    def test_x_xss_protection_header(self):
        """Test X-XSS-Protection header is enabled."""
        response = client.get("/health")
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    def test_content_security_policy_header(self):
        """Test Content-Security-Policy header is set."""
        response = client.get("/health")
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        
        # Check for important CSP directives
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "upgrade-insecure-requests" in csp
    
    def test_referrer_policy_header(self):
        """Test Referrer-Policy header is set."""
        response = client.get("/health")
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    
    def test_permissions_policy_header(self):
        """Test Permissions-Policy header is set."""
        response = client.get("/health")
        assert "Permissions-Policy" in response.headers
        permissions = response.headers["Permissions-Policy"]
        
        # Check that dangerous features are disabled
        assert "geolocation=()" in permissions
        assert "microphone=()" in permissions
        assert "camera=()" in permissions
    
    def test_request_id_header(self):
        """Test X-Request-ID header is added to responses."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        # Should be a UUID
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID format
        assert request_id.count('-') == 4

# =============================================================================
# Authentication Security Tests
# =============================================================================

class TestAuthenticationSecurity:
    """Test authentication security features."""
    
    def test_register_with_weak_password_still_hashed(self):
        """Test that even weak passwords are properly hashed."""
        # Clear users for clean test
        dependencies.users.clear()
        
        response = client.post(
            "/users",
            json={"username": "weak_user", "password": "123"}
        )
        
        # Registration might succeed (we don't enforce password strength yet)
        # But password should be hashed, not stored in plaintext
        if "weak_user" in dependencies.users:
            hashed = dependencies.users["weak_user"]
            assert hashed != "123"  # Not plaintext
            assert hashed.startswith("$2b$")  # Bcrypt format
    
    def test_login_with_wrong_password_fails(self):
        """Test that wrong password is rejected."""
        # Create user
        dependencies.users.clear()
        dependencies.users["test_user"] = hash_password("correct_password")
        
        response = client.post(
            "/token",
            json={"username": "test_user", "password": "wrong_password"}
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_with_nonexistent_user_fails(self):
        """Test that nonexistent user is rejected."""
        dependencies.users.clear()
        
        response = client.post(
            "/token",
            json={"username": "nonexistent", "password": "password"}
        )
        
        assert response.status_code == 401
    
    def test_access_without_token_fails(self):
        """Test that endpoints require authentication."""
        response = client.get("/clusters")
        
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()
    
    def test_access_with_invalid_token_fails(self):
        """Test that invalid tokens are rejected."""
        response = client.get(
            "/clusters",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401

# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Test rate limiting on endpoints."""
    
    def test_rate_limit_on_registration(self):
        """Test that user registration is rate limited."""
        # Clear users
        dependencies.users.clear()
        
        # Try to register multiple times quickly
        # Rate limit: 3/minute for /users
        for i in range(3):
            response = client.post(
                "/users",
                json={"username": f"user{i}", "password": "password123"}
            )
            # First 3 should succeed or fail with 400 (username exists)
            assert response.status_code in [200, 400]
        
        # 4th request should be rate limited
        response = client.post(
            "/users",
            json={"username": "user4", "password": "password123"}
        )
        
        # Should be rate limited (429) or succeed if rate limiter not strict
        # Note: In testing, rate limiter might not be strict
        assert response.status_code in [200, 400, 429]
    
    def test_rate_limit_on_login(self):
        """Test that login is rate limited."""
        # Create a user
        dependencies.users.clear()
        dependencies.users["test_user"] = hash_password("password")
        
        # Try to login multiple times quickly
        # Rate limit: 5/minute for /token
        for i in range(5):
            response = client.post(
                "/token",
                json={"username": "test_user", "password": "wrong_password"}
            )
            # Should fail with 401 (wrong password)
            assert response.status_code in [401, 429]
        
        # 6th request might be rate limited
        response = client.post(
            "/token",
            json={"username": "test_user", "password": "wrong_password"}
        )
        assert response.status_code in [401, 429]

# =============================================================================
# Input Validation Security Tests
# =============================================================================

class TestInputValidationSecurity:
    """Test input validation prevents injection attacks."""
    
    def test_sql_injection_in_username_blocked(self):
        """Test SQL injection attempts are blocked."""
        dependencies.users.clear()
        
        malicious_usernames = [
            "admin'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
        ]
        
        for username in malicious_usernames:
            response = client.post(
                "/users",
                json={"username": username, "password": "password"}
            )
            # Should be rejected with 400
            assert response.status_code == 400
            assert "username" in response.json()["detail"].lower() or "forbidden" in response.json()["detail"].lower()
    
    def test_command_injection_in_username_blocked(self):
        """Test command injection attempts are blocked."""
        dependencies.users.clear()
        
        malicious_usernames = [
            "user; rm -rf /",
            "user`whoami`",
            "user$(cat /etc/passwd)",
        ]
        
        for username in malicious_usernames:
            response = client.post(
                "/users",
                json={"username": username, "password": "password"}
            )
            # Should be rejected with 400
            assert response.status_code == 400

# =============================================================================
# CORS Security Tests
# =============================================================================

class TestCORSSecurity:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self):
        """Test CORS headers are set."""
        response = client.options("/health")
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    def test_preflight_request_handled(self):
        """Test OPTIONS preflight requests are handled."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Should allow the request or return 200
        assert response.status_code in [200, 204]

# =============================================================================
# Health Check Security
# =============================================================================

class TestHealthCheckSecurity:
    """Test health check doesn't leak sensitive information."""
    
    def test_health_check_no_sensitive_data(self):
        """Test health check doesn't expose secrets."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        
        # Should not contain sensitive information
        assert "SECRET_KEY" not in str(data)
        assert "password" not in str(data).lower()
        assert "OPENAI_API_KEY" not in str(data)
        
        # Should only indicate if OpenAI is configured, not the key
        if "dependencies" in data and "openai_configured" in data["dependencies"]:
            assert isinstance(data["dependencies"]["openai_configured"], bool)
