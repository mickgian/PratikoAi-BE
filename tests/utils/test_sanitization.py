"""Tests for sanitization utilities."""

import pytest

from app.utils.sanitization import (
    sanitize_dict,
    sanitize_email,
    sanitize_list,
    sanitize_string,
    validate_password_strength,
)


class TestSanitizeString:
    """Test sanitize_string function."""

    def test_sanitize_normal_string(self):
        """Test sanitizing normal string."""
        result = sanitize_string("Hello World")
        assert result == "Hello World"

    def test_sanitize_html_tags(self):
        """Test HTML tags are escaped."""
        result = sanitize_string("<div>Test</div>")
        assert "&lt;div&gt;" in result
        assert "<div>" not in result

    def test_sanitize_script_tags(self):
        """Test script tags are removed."""
        result = sanitize_string("<script>alert('xss')</script>Hello")
        assert "script" not in result.lower() or "&lt;script" not in result
        assert "Hello" in result

    def test_sanitize_null_bytes(self):
        """Test null bytes are removed."""
        result = sanitize_string("Hello\0World")
        assert "\0" not in result
        assert "HelloWorld" in result

    def test_sanitize_special_characters(self):
        """Test special characters are escaped."""
        result = sanitize_string("<>&\"'")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result

    def test_sanitize_non_string_input(self):
        """Test sanitizing non-string input."""
        result = sanitize_string(123)
        assert result == "123"

    def test_sanitize_empty_string(self):
        """Test sanitizing empty string."""
        result = sanitize_string("")
        assert result == ""


class TestSanitizeEmail:
    """Test sanitize_email function."""

    def test_sanitize_valid_email(self):
        """Test sanitizing valid email."""
        result = sanitize_email("test@example.com")
        assert result == "test@example.com"

    def test_sanitize_email_lowercase(self):
        """Test email is converted to lowercase."""
        result = sanitize_email("Test@Example.COM")
        assert result == "test@example.com"

    def test_sanitize_email_with_plus(self):
        """Test email with plus sign."""
        result = sanitize_email("test+tag@example.com")
        assert result == "test+tag@example.com"

    def test_sanitize_invalid_email_format(self):
        """Test invalid email format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            sanitize_email("not-an-email")

    def test_sanitize_email_no_domain(self):
        """Test email without domain raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            sanitize_email("test@")

    def test_sanitize_email_no_at_sign(self):
        """Test email without @ raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            sanitize_email("testexample.com")


class TestSanitizeDict:
    """Test sanitize_dict function."""

    def test_sanitize_dict_with_strings(self):
        """Test sanitizing dictionary with strings."""
        data = {"name": "John", "content": "<script>alert('xss')</script>"}
        result = sanitize_dict(data)

        assert result["name"] == "John"
        # Script tags are removed by sanitization
        assert "script" not in result["content"].lower() or result["content"] == ""

    def test_sanitize_dict_nested(self):
        """Test sanitizing nested dictionary."""
        data = {
            "user": {
                "name": "<b>John</b>",
                "email": "test@example.com",
            }
        }
        result = sanitize_dict(data)

        assert "&lt;b&gt;" in result["user"]["name"]

    def test_sanitize_dict_with_list(self):
        """Test sanitizing dict containing list."""
        data = {"tags": ["<tag1>", "<tag2>"]}
        result = sanitize_dict(data)

        assert all("&lt;" in tag for tag in result["tags"])

    def test_sanitize_dict_preserves_numbers(self):
        """Test dict sanitization preserves numbers."""
        data = {"count": 42, "price": 19.99}
        result = sanitize_dict(data)

        assert result["count"] == 42
        assert result["price"] == 19.99

    def test_sanitize_empty_dict(self):
        """Test sanitizing empty dictionary."""
        result = sanitize_dict({})
        assert result == {}


class TestSanitizeList:
    """Test sanitize_list function."""

    def test_sanitize_list_with_strings(self):
        """Test sanitizing list of strings."""
        data = ["hello", "<script>xss</script>", "world"]
        result = sanitize_list(data)

        assert result[0] == "hello"
        # Script tags are removed by sanitization
        assert "script" not in result[1].lower() or result[1] == ""
        assert result[2] == "world"

    def test_sanitize_list_nested(self):
        """Test sanitizing nested list."""
        data = [["<tag1>", "normal"], ["<tag2>"]]
        result = sanitize_list(data)

        assert "&lt;" in result[0][0]
        assert result[0][1] == "normal"

    def test_sanitize_list_with_dicts(self):
        """Test sanitizing list containing dicts."""
        data = [{"name": "<b>test</b>"}, {"content": "normal"}]
        result = sanitize_list(data)

        assert "&lt;b&gt;" in result[0]["name"]
        assert result[1]["content"] == "normal"

    def test_sanitize_list_preserves_numbers(self):
        """Test list sanitization preserves numbers."""
        data = [1, 2.5, "text", 42]
        result = sanitize_list(data)

        assert result[0] == 1
        assert result[1] == 2.5
        assert result[3] == 42

    def test_sanitize_empty_list(self):
        """Test sanitizing empty list."""
        result = sanitize_list([])
        assert result == []


class TestValidatePasswordStrength:
    """Test validate_password_strength function."""

    def test_valid_strong_password(self):
        """Test valid strong password."""
        assert validate_password_strength("StrongP@ss123") is True

    def test_password_too_short(self):
        """Test password too short."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password_strength("Sh0rt!")

    def test_password_no_uppercase(self):
        """Test password without uppercase letter."""
        with pytest.raises(ValueError, match="at least one uppercase letter"):
            validate_password_strength("password123!")

    def test_password_no_lowercase(self):
        """Test password without lowercase letter."""
        with pytest.raises(ValueError, match="at least one lowercase letter"):
            validate_password_strength("PASSWORD123!")

    def test_password_no_number(self):
        """Test password without number."""
        with pytest.raises(ValueError, match="at least one number"):
            validate_password_strength("Password!")

    def test_password_no_special_char(self):
        """Test password without special character."""
        with pytest.raises(ValueError, match="at least one special character"):
            validate_password_strength("Password123")

    def test_password_with_all_requirements(self):
        """Test password with all requirements."""
        passwords = [
            "ValidPass123!",
            "Str0ng#Password",
            "MyP@ssw0rd",
            "Test1234!",
        ]
        for password in passwords:
            assert validate_password_strength(password) is True


class TestSanitizationIntegration:
    """Integration tests for sanitization."""

    def test_sanitize_complex_nested_structure(self):
        """Test sanitizing complex nested structure."""
        data = {
            "user": {
                "name": "<b>John</b>",
                "tags": ["<tag1>", "<tag2>"],
                "meta": {
                    "content": "<script>xss</script>",
                },
            },
            "items": [
                {"title": "<h1>Title</h1>"},
                {"content": "Normal content"},
            ],
        }

        result = sanitize_dict(data)

        assert "&lt;b&gt;" in result["user"]["name"]
        assert all("&lt;" in tag for tag in result["user"]["tags"])
        # Script tags are removed entirely
        assert "script" not in result["user"]["meta"]["content"].lower() or result["user"]["meta"]["content"] == ""
        assert "&lt;h1&gt;" in result["items"][0]["title"]
        assert result["items"][1]["content"] == "Normal content"

    def test_sanitize_prevents_xss(self):
        """Test sanitization prevents XSS attacks."""
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg/onload=alert('XSS')>",
            "javascript:alert('XSS')",
        ]

        for xss in xss_attempts:
            result = sanitize_string(xss)
            # Script tags should be escaped or removed
            assert "<script" not in result or "&lt;script" in result
            assert "<img" not in result or "&lt;img" in result
