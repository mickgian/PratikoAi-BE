"""
Test vector configuration resolution and validation.

This module tests configuration parsing, environment variable resolution,
and validation logic for vector search setup.
"""

import os
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.core.config import Environment, get_settings


class TestConfigurationResolution:
    """Test configuration resolution from environment variables."""
    
    def test_pinecone_config_resolution_development(self):
        """Development environment should resolve Pinecone config correctly."""
        with patch.dict(os.environ, {
            "APP_ENV": "development",
            "PINECONE_API_KEY": "pcsk_test_dev_key",
            "PINECONE_ENVIRONMENT": "serverless",
            "PINECONE_INDEX_NAME": "pratikoai-dev"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.pinecone_api_key == "pcsk_test_dev_key"
            assert config.pinecone_environment == "serverless"
            assert config.pinecone_index_name == "pratikoai-dev"
            assert config.is_pinecone_configured() is True
    
    def test_pinecone_config_missing_api_key(self):
        """Configuration should detect missing API key."""
        with patch.dict(os.environ, {
            "APP_ENV": "staging",
            "PINECONE_ENVIRONMENT": "serverless",
            "PINECONE_INDEX_NAME": "pratikoai-staging"
            # PINECONE_API_KEY intentionally missing
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.is_pinecone_configured() is False
            assert config.get_missing_pinecone_config() == ["PINECONE_API_KEY"]
    
    def test_namespace_prefix_configuration(self):
        """Test namespace prefix configuration resolution."""
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "PINECONE_NAMESPACE_PREFIX": "prod-ns"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.namespace_prefix == "prod-ns"
    
    def test_namespace_prefix_default(self):
        """Test default namespace prefix when not specified."""
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.namespace_prefix == "env="
    
    def test_vector_strict_mode_configuration(self):
        """Test strict mode configuration parsing."""
        with patch.dict(os.environ, {
            "VECTOR_STRICT_EMBEDDER_MATCH": "true",
            "VECTOR_STRICT_MODE": "true"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.strict_embedder_match is True
            assert config.strict_mode is True
    
    def test_embedding_model_configuration(self):
        """Test embedding model configuration resolution."""
        with patch.dict(os.environ, {
            "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
            "EMBEDDING_DIMENSION": "384"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
            assert config.embedding_dimension == 384


class TestIndexNameGeneration:
    """Test index name generation logic."""
    
    def test_index_name_from_dimension(self):
        """Index name should be generated from embedding dimension."""
        from app.services.vector_config import VectorConfig
        
        config = VectorConfig()
        
        # Test different dimensions
        assert config.generate_index_name(384) == "pratikoai-embed-384"
        assert config.generate_index_name(768) == "pratikoai-embed-768"
        assert config.generate_index_name(1024) == "pratikoai-embed-1024"
    
    def test_index_name_from_model_slug(self):
        """Index name should be derivable from model identifier."""
        from app.services.vector_config import VectorConfig
        
        config = VectorConfig()
        
        # Test model-based naming (if we implement this feature)
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        expected_slug = "all-MiniLM-L6-v2"  # Extract model name part
        
        # This would be the logic for model-based naming
        index_name = config.generate_index_name_from_model(model_name)
        assert "all-MiniLM-L6-v2" in index_name.lower() or index_name == "pratikoai-embed-384"


class TestNamespaceGeneration:
    """Test namespace generation and validation."""
    
    def test_namespace_with_all_components(self):
        """Namespace should include all required components."""
        from app.services.vector_config import VectorConfig
        
        config = VectorConfig()
        
        namespace = config.build_namespace(
            env="staging",
            domain="legale", 
            tenant="client-123"
        )
        
        # Should contain all components
        assert "env=staging" in namespace
        assert "domain=legale" in namespace
        assert "tenant=client-123" in namespace
        
        # Should be properly formatted
        parts = namespace.split(",")
        assert len(parts) == 3
    
    def test_namespace_domain_validation(self):
        """Namespace should validate domain values."""
        from app.services.vector_config import VectorConfig
        
        config = VectorConfig()
        valid_domains = ["ccnl", "fiscale", "legale", "lavoro"]
        
        for domain in valid_domains:
            namespace = config.build_namespace(
                env="dev",
                domain=domain,
                tenant="default"
            )
            assert f"domain={domain}" in namespace
    
    def test_namespace_invalid_domain(self):
        """Namespace should reject invalid domain values."""
        from app.services.vector_config import VectorConfig
        
        config = VectorConfig()
        
        with pytest.raises(ValueError, match="Invalid domain"):
            config.build_namespace(
                env="dev",
                domain="invalid-domain",
                tenant="default"
            )
    
    def test_namespace_environment_validation(self):
        """Namespace should validate environment values."""
        from app.services.vector_config import VectorConfig
        
        config = VectorConfig()
        valid_envs = ["dev", "staging", "preprod", "prod"]
        
        for env in valid_envs:
            namespace = config.build_namespace(
                env=env,
                domain="fiscale",
                tenant="default"
            )
            assert f"env={env}" in namespace


class TestConfigurationValidation:
    """Test configuration validation logic."""
    
    def test_validate_production_requirements(self):
        """Production environment should require specific configurations."""
        with patch.dict(os.environ, {
            "APP_ENV": "production"
            # Missing required production configs
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            validation_errors = config.validate_for_environment(Environment.PRODUCTION)
            
            # Should have validation errors for missing configs
            assert len(validation_errors) > 0
            assert any("PINECONE_API_KEY" in error for error in validation_errors)
    
    def test_validate_development_permissive(self):
        """Development environment should be more permissive."""
        with patch.dict(os.environ, {
            "APP_ENV": "development"
            # Minimal config for development
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            validation_errors = config.validate_for_environment(Environment.DEVELOPMENT)
            
            # Development should have fewer validation errors
            assert len(validation_errors) == 0
    
    def test_validate_staging_requirements(self):
        """Staging should require some configs but be more flexible than production."""
        with patch.dict(os.environ, {
            "APP_ENV": "staging",
            "PINECONE_API_KEY": "staging-key"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            validation_errors = config.validate_for_environment(Environment.STAGING)
            
            # With API key, staging should validate successfully
            assert len(validation_errors) == 0


class TestEnvironmentSpecificBehavior:
    """Test environment-specific configuration behavior."""
    
    def test_development_config_override(self):
        """Development should allow easy overrides."""
        with patch.dict(os.environ, {
            "APP_ENV": "development",
            "VEC_PROVIDER": "local",  # Override to local
            "DEBUG_VECTOR_SEARCH": "true"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.get_provider_preference() == "local"
            assert config.debug_mode is True
    
    def test_production_config_strictness(self):
        """Production should enforce strict configuration."""
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "PINECONE_API_KEY": "prod-key",
            "VECTOR_STRICT_MODE": "true"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            assert config.get_provider_preference() == "pinecone"
            assert config.strict_mode is True
            assert config.allow_fallback_in_production() is False
    
    def test_staging_config_flexibility(self):
        """Staging should balance between dev flexibility and prod strictness."""
        with patch.dict(os.environ, {
            "APP_ENV": "staging",
            "PINECONE_API_KEY": "staging-key"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            
            # Should prefer pinecone when available
            assert config.get_provider_preference() == "pinecone"
            # But allow fallback
            assert config.allow_fallback() is True


class TestConfigurationSerialization:
    """Test configuration serialization for debugging and logging."""
    
    def test_safe_config_serialization(self):
        """Configuration should serialize safely without exposing secrets."""
        with patch.dict(os.environ, {
            "PINECONE_API_KEY": "pcsk_secret_key",
            "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            safe_config = config.to_safe_dict()
            
            # Should not contain secrets
            assert "pcsk_secret_key" not in str(safe_config)
            assert safe_config.get("pinecone_api_key") == "***REDACTED***"
            
            # Should contain non-sensitive config
            assert safe_config.get("embedding_model") == "sentence-transformers/all-MiniLM-L6-v2"
    
    def test_config_logging_format(self):
        """Configuration should provide logging-friendly format."""
        with patch.dict(os.environ, {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_INDEX_NAME": "pratikoai-dev",
            "EMBEDDING_DIMENSION": "384"
        }, clear=True):
            from app.services.vector_config import VectorConfig
            
            config = VectorConfig()
            log_message = config.format_for_logging()
            
            assert "index=pratikoai-dev" in log_message
            assert "dimension=384" in log_message
            assert "api_key=***" in log_message  # Masked


# Test fixtures and utilities
@pytest.fixture
def clean_environment():
    """Fixture to ensure clean environment for each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_config():
    """Fixture providing sample configuration for tests."""
    return {
        "PINECONE_API_KEY": "pcsk_test_key",
        "PINECONE_ENVIRONMENT": "serverless", 
        "PINECONE_INDEX_NAME": "pratikoai-test",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
        "EMBEDDING_DIMENSION": "384"
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])