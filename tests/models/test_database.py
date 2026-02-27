"""Tests for database utility functions."""

import pytest

from app.models.database import get_async_database_url


class TestGetAsyncDatabaseUrl:
    """Test get_async_database_url function."""

    def test_convert_postgresql_url(self):
        """Test converting postgresql:// URL to async format."""
        url = "postgresql://user:pass@localhost:5432/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@localhost:5432/dbname"
        assert result.startswith("postgresql+asyncpg://")

    def test_convert_postgres_url(self):
        """Test converting postgres:// URL to async format."""
        url = "postgres://user:pass@localhost:5432/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@localhost:5432/dbname"
        assert result.startswith("postgresql+asyncpg://")

    def test_url_already_async(self):
        """Test that async URL is returned unchanged."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/dbname"
        result = get_async_database_url(url)

        assert result == url

    def test_url_with_query_parameters(self):
        """Test converting URL with query parameters."""
        url = "postgresql://user:pass@localhost:5432/dbname?sslmode=require"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@localhost:5432/dbname?sslmode=require"
        assert "sslmode=require" in result

    def test_url_with_special_characters(self):
        """Test converting URL with special characters in password."""
        url = "postgresql://user:p@ssw0rd!@localhost:5432/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:p@ssw0rd!@localhost:5432/dbname"

    def test_url_with_port(self):
        """Test converting URL with explicit port."""
        url = "postgresql://user:pass@db.example.com:5433/mydb"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@db.example.com:5433/mydb"
        assert ":5433" in result

    def test_url_without_port(self):
        """Test converting URL without explicit port."""
        url = "postgresql://user:pass@localhost/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@localhost/dbname"

    def test_url_with_ipv4_host(self):
        """Test converting URL with IPv4 address."""
        url = "postgresql://user:pass@192.168.1.100:5432/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@192.168.1.100:5432/dbname"

    def test_url_localhost(self):
        """Test converting localhost URL."""
        url = "postgresql://user:pass@localhost:5432/testdb"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        assert "localhost" in result

    def test_postgres_heroku_style_url(self):
        """Test converting Heroku-style postgres:// URL."""
        url = "postgres://user:pass@ec2-host.amazonaws.com:5432/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user:pass@ec2-host.amazonaws.com:5432/dbname"
        assert result.startswith("postgresql+asyncpg://")

    def test_only_first_occurrence_replaced(self):
        """Test that only the first occurrence of postgresql:// is replaced."""
        # Edge case: URL with 'postgresql://' in the database name
        url = "postgresql://user:pass@localhost:5432/db_postgresql://test"
        result = get_async_database_url(url)

        # Should only replace the first occurrence
        assert result.startswith("postgresql+asyncpg://")
        assert result.count("postgresql+asyncpg://") == 1

    def test_empty_credentials(self):
        """Test converting URL without credentials."""
        url = "postgresql://localhost:5432/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://localhost:5432/dbname"

    def test_url_with_username_only(self):
        """Test converting URL with username but no password."""
        url = "postgresql://user@localhost:5432/dbname"
        result = get_async_database_url(url)

        assert result == "postgresql+asyncpg://user@localhost:5432/dbname"

    def test_complex_query_string(self):
        """Test converting URL with complex query parameters."""
        url = "postgresql://user:pass@localhost:5432/db?sslmode=require&connect_timeout=10&application_name=myapp"
        result = get_async_database_url(url)

        assert (
            result
            == "postgresql+asyncpg://user:pass@localhost:5432/db?sslmode=require&connect_timeout=10&application_name=myapp"
        )
        assert "sslmode=require" in result
        assert "connect_timeout=10" in result

    def test_non_postgres_url_unchanged(self):
        """Test that non-PostgreSQL URLs are returned unchanged."""
        sqlite_url = "sqlite:///./test.db"
        result = get_async_database_url(sqlite_url)

        assert result == sqlite_url

    def test_mysql_url_unchanged(self):
        """Test that MySQL URLs are returned unchanged."""
        mysql_url = "mysql://user:pass@localhost:3306/dbname"
        result = get_async_database_url(mysql_url)

        assert result == mysql_url
