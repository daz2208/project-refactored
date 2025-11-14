"""
Tests for input sanitization module.

Tests all sanitization functions to ensure they properly prevent:
- Path traversal attacks
- XSS attacks
- SQL injection
- Command injection
- Resource exhaustion
"""

import pytest
from fastapi import HTTPException
from backend.sanitization import (
    sanitize_filename,
    sanitize_text_content,
    sanitize_description,
    sanitize_username,
    validate_url,
    sanitize_cluster_name,
    validate_positive_integer,
)


# =============================================================================
# Filename Sanitization Tests
# =============================================================================

class TestFileSanitization:
    """Test filename sanitization against path traversal attacks."""

    def test_valid_filename(self):
        """Test that valid filenames pass through."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my_file.txt") == "my_file.txt"
        assert sanitize_filename("report-2024.docx") == "report-2024.docx"

    def test_path_traversal_attack(self):
        """Test that path traversal attempts are blocked."""
        with pytest.raises(HTTPException) as exc:
            sanitize_filename("../../../etc/passwd")
        assert exc.value.status_code == 400
        assert "forbidden" in exc.value.detail.lower()

    def test_path_traversal_variations(self):
        """Test various path traversal patterns."""
        dangerous_filenames = [
            "../../config.json",
            "~/secret.key",
            "/etc/shadow",
            "dir/../file.txt",
            "file\\..\\windows\\system32",
        ]
        for filename in dangerous_filenames:
            with pytest.raises(HTTPException):
                sanitize_filename(filename)

    def test_null_byte_injection(self):
        """Test that null bytes are blocked."""
        with pytest.raises(HTTPException):
            sanitize_filename("file.txt\x00.jpg")

    def test_empty_filename(self):
        """Test that empty filenames are rejected."""
        with pytest.raises(HTTPException) as exc:
            sanitize_filename("")
        assert exc.value.status_code == 400
        assert "empty" in exc.value.detail.lower()

        with pytest.raises(HTTPException):
            sanitize_filename("   ")

    def test_filename_too_long(self):
        """Test that overly long filenames are rejected."""
        long_name = "a" * 300 + ".txt"
        with pytest.raises(HTTPException) as exc:
            sanitize_filename(long_name)
        assert exc.value.status_code == 400
        assert "too long" in exc.value.detail.lower()

    def test_spaces_in_filename(self):
        """Test that spaces are converted to underscores."""
        assert sanitize_filename("my file.pdf") == "my_file.pdf"
        assert sanitize_filename("multiple  spaces.txt") == "multiple_spaces.txt"

    def test_special_characters(self):
        """Test that special characters are removed."""
        result = sanitize_filename("file!@#$%.txt")
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result

    def test_hidden_files(self):
        """Test that leading dots are removed (hidden files)."""
        result = sanitize_filename(".hidden_file.txt")
        assert not result.startswith(".")

    def test_preserve_extension(self):
        """Test that file extensions are preserved."""
        result = sanitize_filename("a" * 250 + ".pdf", allow_extension=True)
        assert result.endswith(".pdf")


# =============================================================================
# Text Content Sanitization Tests
# =============================================================================

class TestTextSanitization:
    """Test text content sanitization."""

    def test_valid_text(self):
        """Test that valid text passes through."""
        text = "This is a normal piece of text with some code: print('hello')"
        assert sanitize_text_content(text) == text

    def test_empty_content(self):
        """Test that empty content is rejected."""
        with pytest.raises(HTTPException) as exc:
            sanitize_text_content("")
        assert exc.value.status_code == 400
        assert "empty" in exc.value.detail.lower()

    def test_null_bytes(self):
        """Test that null bytes are rejected."""
        with pytest.raises(HTTPException) as exc:
            sanitize_text_content("text\x00with\x00nulls")
        assert exc.value.status_code == 400
        assert "null" in exc.value.detail.lower()

    def test_content_too_long(self):
        """Test that content exceeding max length is rejected."""
        max_length = 1000
        long_content = "a" * (max_length + 1)
        with pytest.raises(HTTPException) as exc:
            sanitize_text_content(long_content, max_length=max_length)
        assert exc.value.status_code == 400
        assert "too long" in exc.value.detail.lower()

    def test_normalize_line_endings(self):
        """Test that line endings are normalized."""
        # Windows style
        text = "line1\r\nline2\r\nline3"
        result = sanitize_text_content(text)
        assert result == "line1\nline2\nline3"

        # Old Mac style
        text = "line1\rline2\rline3"
        result = sanitize_text_content(text)
        assert result == "line1\nline2\nline3"

    def test_preserve_html_code(self):
        """Test that HTML in code examples is preserved (NOT stripped)."""
        # We preserve HTML because users might upload code examples
        # HTML escaping should happen at render time in frontend
        html_code = "<script>alert('test')</script>"
        result = sanitize_text_content(html_code)
        assert result == html_code  # NOT escaped - preserved for code storage

    def test_preserve_markdown(self):
        """Test that markdown is preserved."""
        markdown = "# Header\n\n**Bold** and *italic*\n\n```python\nprint('hello')\n```"
        result = sanitize_text_content(markdown)
        assert result == markdown

    def test_unicode_content(self):
        """Test that unicode content is handled."""
        unicode_text = "Hello 世界 🌍 Привет"
        result = sanitize_text_content(unicode_text)
        assert result == unicode_text


class TestDescriptionSanitization:
    """Test description field sanitization."""

    def test_none_description(self):
        """Test that None returns None."""
        assert sanitize_description(None) is None

    def test_empty_description(self):
        """Test that empty string returns None."""
        assert sanitize_description("") is None
        assert sanitize_description("   ") is None

    def test_valid_description(self):
        """Test that valid description passes through."""
        desc = "This is a description of the image"
        assert sanitize_description(desc) == desc

    def test_description_max_length(self):
        """Test that descriptions have shorter max length than full content."""
        # Descriptions should have a much smaller max length (5000 chars)
        long_desc = "a" * 6000
        with pytest.raises(HTTPException):
            sanitize_description(long_desc)


# =============================================================================
# Username Sanitization Tests
# =============================================================================

class TestUsernameSanitization:
    """Test username sanitization against injection attacks."""

    def test_valid_username(self):
        """Test that valid usernames pass through."""
        assert sanitize_username("john_doe") == "john_doe"
        assert sanitize_username("user123") == "user123"
        assert sanitize_username("my-username") == "my-username"

    def test_sql_injection_attempt(self):
        """Test that SQL injection attempts are blocked."""
        malicious_usernames = [
            "admin'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM users--",
        ]
        for username in malicious_usernames:
            with pytest.raises(HTTPException) as exc:
                sanitize_username(username)
            assert exc.value.status_code == 400

    def test_command_injection_attempt(self):
        """Test that command injection attempts are blocked."""
        malicious_usernames = [
            "user; rm -rf /",
            "user`whoami`",
            "user$(cat /etc/passwd)",
            "user|ls",
        ]
        for username in malicious_usernames:
            with pytest.raises(HTTPException):
                sanitize_username(username)

    def test_username_too_short(self):
        """Test that usernames must be at least 3 characters."""
        with pytest.raises(HTTPException) as exc:
            sanitize_username("ab")
        assert exc.value.status_code == 400
        assert "at least 3" in exc.value.detail.lower()

    def test_username_too_long(self):
        """Test that usernames cannot exceed max length."""
        long_username = "a" * 60
        with pytest.raises(HTTPException) as exc:
            sanitize_username(long_username)
        assert exc.value.status_code == 400
        assert "too long" in exc.value.detail.lower()

    def test_empty_username(self):
        """Test that empty usernames are rejected."""
        with pytest.raises(HTTPException):
            sanitize_username("")
        with pytest.raises(HTTPException):
            sanitize_username("   ")

    def test_reserved_usernames(self):
        """Test that reserved usernames are blocked."""
        reserved = ["admin", "root", "system", "test", "guest"]
        for username in reserved:
            with pytest.raises(HTTPException) as exc:
                sanitize_username(username)
            assert exc.value.status_code == 400
            assert "reserved" in exc.value.detail.lower()

    def test_special_characters(self):
        """Test that only alphanumeric, underscore, hyphen are allowed."""
        with pytest.raises(HTTPException):
            sanitize_username("user@domain")
        with pytest.raises(HTTPException):
            sanitize_username("user.name")
        with pytest.raises(HTTPException):
            sanitize_username("user name")  # spaces not allowed

    def test_unicode_characters(self):
        """Test that unicode characters are rejected."""
        with pytest.raises(HTTPException):
            sanitize_username("user世界")
        with pytest.raises(HTTPException):
            sanitize_username("userΘ")


# =============================================================================
# URL Validation Tests
# =============================================================================

class TestURLValidation:
    """Test URL validation against SSRF and file access attacks."""

    def test_valid_urls(self):
        """Test that valid HTTP/HTTPS URLs pass through."""
        urls = [
            "https://example.com",
            "http://example.com/page",
            "https://sub.example.com/path?query=value",
        ]
        for url in urls:
            assert validate_url(url) == url

    def test_file_protocol(self):
        """Test that file:// protocol is blocked."""
        with pytest.raises(HTTPException) as exc:
            validate_url("file:///etc/passwd")
        assert exc.value.status_code == 400
        assert "scheme" in exc.value.detail.lower()

    def test_ssrf_localhost(self):
        """Test that localhost URLs are blocked (SSRF protection)."""
        ssrf_urls = [
            "http://localhost/admin",
            "http://127.0.0.1/secrets",
            "http://0.0.0.0/",
            "http://[::1]/",
        ]
        for url in ssrf_urls:
            with pytest.raises(HTTPException) as exc:
                validate_url(url)
            assert exc.value.status_code == 400
            assert "internal" in exc.value.detail.lower() or "private" in exc.value.detail.lower()

    def test_ssrf_private_networks(self):
        """Test that private network IPs are blocked."""
        private_ips = [
            "http://192.168.1.1/",
            "http://10.0.0.1/",
            "http://172.16.0.1/",
            "http://169.254.1.1/",  # Link-local
        ]
        for url in private_ips:
            with pytest.raises(HTTPException):
                validate_url(url)

    def test_empty_url(self):
        """Test that empty URLs are rejected."""
        with pytest.raises(HTTPException):
            validate_url("")
        with pytest.raises(HTTPException):
            validate_url("   ")

    def test_url_too_long(self):
        """Test that overly long URLs are rejected."""
        long_url = "https://example.com/" + "a" * 3000
        with pytest.raises(HTTPException) as exc:
            validate_url(long_url)
        assert exc.value.status_code == 400
        assert "too long" in exc.value.detail.lower()

    def test_invalid_url_format(self):
        """Test that malformed URLs are rejected."""
        with pytest.raises(HTTPException):
            validate_url("not a url")
        with pytest.raises(HTTPException):
            validate_url("http://")

    def test_no_hostname(self):
        """Test that URLs without hostname are rejected."""
        with pytest.raises(HTTPException) as exc:
            validate_url("http:///path")
        assert exc.value.status_code == 400


# =============================================================================
# Cluster Name Sanitization Tests
# =============================================================================

class TestClusterNameSanitization:
    """Test cluster name sanitization."""

    def test_valid_cluster_name(self):
        """Test that valid cluster names pass through."""
        assert sanitize_cluster_name("Python Programming") == "Python Programming"
        assert sanitize_cluster_name("Web Development") == "Web Development"

    def test_empty_cluster_name(self):
        """Test that empty names are rejected."""
        with pytest.raises(HTTPException):
            sanitize_cluster_name("")
        with pytest.raises(HTTPException):
            sanitize_cluster_name("   ")

    def test_cluster_name_too_long(self):
        """Test that overly long names are rejected."""
        long_name = "a" * 150
        with pytest.raises(HTTPException) as exc:
            sanitize_cluster_name(long_name)
        assert exc.value.status_code == 400
        assert "too long" in exc.value.detail.lower()

    def test_null_bytes(self):
        """Test that null bytes are rejected."""
        with pytest.raises(HTTPException):
            sanitize_cluster_name("cluster\x00name")

    def test_unicode_cluster_names(self):
        """Test that unicode cluster names are allowed."""
        # Unlike usernames, cluster names can have unicode
        assert sanitize_cluster_name("Python 编程") == "Python 编程"


# =============================================================================
# Integer Validation Tests
# =============================================================================

class TestIntegerValidation:
    """Test positive integer validation."""

    def test_valid_integer(self):
        """Test that valid integers pass through."""
        assert validate_positive_integer(5, "test", 100) == 5
        assert validate_positive_integer(1, "test", 100) == 1
        assert validate_positive_integer(100, "test", 100) == 100

    def test_negative_integer(self):
        """Test that negative integers are rejected."""
        with pytest.raises(HTTPException) as exc:
            validate_positive_integer(-1, "test_param")
        assert exc.value.status_code == 400
        assert "positive" in exc.value.detail.lower()
        assert "test_param" in exc.value.detail

    def test_zero(self):
        """Test that zero is allowed (it's not negative)."""
        assert validate_positive_integer(0, "test") == 0

    def test_exceeds_max_value(self):
        """Test that values exceeding max are rejected."""
        with pytest.raises(HTTPException) as exc:
            validate_positive_integer(101, "test_param", max_value=100)
        assert exc.value.status_code == 400
        assert "too large" in exc.value.detail.lower()
        assert "100" in exc.value.detail

    def test_at_max_value(self):
        """Test that value at max is allowed."""
        assert validate_positive_integer(100, "test", max_value=100) == 100


# =============================================================================
# Integration Tests
# =============================================================================

class TestSanitizationIntegration:
    """Test sanitization functions together as they would be used in endpoints."""

    def test_upload_workflow(self):
        """Test typical upload workflow sanitization."""
        # Sanitize all inputs
        filename = sanitize_filename("my document.pdf")
        content = sanitize_text_content("This is the document content")
        description = sanitize_description("A PDF about Python")

        assert filename == "my_document.pdf"
        assert content == "This is the document content"
        assert description == "A PDF about Python"

    def test_user_registration_workflow(self):
        """Test user registration sanitization."""
        username = sanitize_username("new_user123")
        assert username == "new_user123"

        # Should block malicious usernames
        with pytest.raises(HTTPException):
            sanitize_username("admin'; DROP TABLE users;--")

    def test_url_upload_workflow(self):
        """Test URL upload sanitization."""
        url = validate_url("https://www.example.com/article")
        assert url == "https://www.example.com/article"

        # Should block SSRF
        with pytest.raises(HTTPException):
            validate_url("http://localhost:8080/admin")

    def test_search_workflow(self):
        """Test search endpoint sanitization."""
        top_k = validate_positive_integer(10, "top_k", max_value=50)
        assert top_k == 10

        # Should block excessive values
        with pytest.raises(HTTPException):
            validate_positive_integer(1000, "top_k", max_value=50)
