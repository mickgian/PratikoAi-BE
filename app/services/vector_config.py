"""
Vector search configuration management.

Handles environment-aware configuration, validation, and provider selection
for vector search operations with Pinecone and local fallbacks.
"""

import os
from typing import Dict, List, Optional, Any
from enum import Enum

from app.core.config import Environment, get_environment
from app.core.logging import logger


class VectorProvider(str, Enum):
    """Available vector search providers."""
    LOCAL = "local"
    PINECONE = "pinecone"


class VectorConfig:
    """Configuration manager for vector search operations."""
    
    def __init__(self):
        """Initialize vector configuration from environment variables."""
        self.environment = get_environment()
        
        # Core vector settings
        self.vec_provider_override = os.getenv("VEC_PROVIDER")
        
        # Pinecone configuration
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "serverless")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "")
        self.namespace_prefix = os.getenv("PINECONE_NAMESPACE_PREFIX", "env=")
        
        # Embedding configuration
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        
        # Behavior configuration
        self.strict_embedder_match = os.getenv("VECTOR_STRICT_EMBEDDER_MATCH", "true").lower() == "true"
        self.strict_mode = os.getenv("VECTOR_STRICT_MODE", "false").lower() == "true"
        self.debug_mode = os.getenv("DEBUG_VECTOR_SEARCH", "false").lower() == "true"
    
    def get_provider_preference(self) -> str:
        """Get the preferred vector provider based on environment and configuration."""
        # Explicit override takes precedence
        if self.vec_provider_override in ["local", "pinecone"]:
            logger.info("vector_provider_override", 
                       provider=self.vec_provider_override,
                       environment=self.environment.value)
            return self.vec_provider_override
        
        # Environment-based defaults
        if self.environment == Environment.DEVELOPMENT:
            return VectorProvider.LOCAL
        elif self.environment == Environment.QA:
            # Use pinecone if configured, otherwise local
            return VectorProvider.PINECONE if self.is_pinecone_configured() else VectorProvider.LOCAL
        elif self.environment in [Environment.PREPROD, Environment.PRODUCTION]:  # PREPROD mirrors PRODUCTION
            return VectorProvider.PINECONE
        else:
            return VectorProvider.LOCAL
    
    def is_pinecone_configured(self) -> bool:
        """Check if Pinecone is properly configured."""
        return bool(self.pinecone_api_key and self.pinecone_environment)
    
    def get_missing_pinecone_config(self) -> List[str]:
        """Get list of missing Pinecone configuration variables."""
        missing = []
        if not self.pinecone_api_key:
            missing.append("PINECONE_API_KEY")
        if not self.pinecone_environment:
            missing.append("PINECONE_ENVIRONMENT")
        return missing
    
    def generate_index_name(self, dimension: Optional[int] = None) -> str:
        """Generate index name based on embedding dimension."""
        dim = dimension or self.embedding_dimension
        return f"pratikoai-embed-{dim}"
    
    def generate_index_name_from_model(self, model_name: str) -> str:
        """Generate index name from model identifier (fallback to dimension-based)."""
        # For now, fallback to dimension-based naming
        # Could be enhanced to extract model slug in future
        return self.generate_index_name()
    
    def build_namespace(self, env: str, domain: str, tenant: str = "default") -> str:
        """Build namespace string with required components."""
        # Validate domain
        valid_domains = ["ccnl", "fiscale", "legale", "lavoro"]
        if domain not in valid_domains:
            raise ValueError(f"Invalid domain: {domain}. Must be one of {valid_domains}")
        
        # Validate environment
        valid_envs = ["dev", "qa", "preprod", "prod"]
        if env not in valid_envs:
            raise ValueError(f"Invalid environment: {env}. Must be one of {valid_envs}")
        
        # Build namespace components
        components = [
            f"env={env}",
            f"domain={domain}", 
            f"tenant={tenant}"
        ]
        
        return ",".join(components)
    
    def get_current_namespace_env(self) -> str:
        """Get namespace environment identifier for current environment."""
        env_mapping = {
            Environment.DEVELOPMENT: "dev",
            Environment.QA: "qa",
            Environment.PREPROD: "preprod",
            Environment.PRODUCTION: "prod",
        }
        return env_mapping.get(self.environment, "dev")
    
    def validate_for_environment(self, environment: Environment) -> List[str]:
        """Validate configuration for specific environment."""
        errors = []

        if environment in [Environment.PRODUCTION, Environment.PREPROD]:
            # Production and PREPROD requirements (PREPROD mirrors PRODUCTION)
            if not self.pinecone_api_key:
                errors.append(f"PINECONE_API_KEY is required for {environment.value}")
            if not self.pinecone_environment:
                errors.append(f"PINECONE_ENVIRONMENT is required for {environment.value}")

        elif environment == Environment.QA:
            # QA is more flexible but warns if missing
            if self.get_provider_preference() == VectorProvider.PINECONE and not self.is_pinecone_configured():
                missing = self.get_missing_pinecone_config()
                errors.append(f"Pinecone configuration missing for {environment.value}: {', '.join(missing)}")

        # Development has minimal requirements (most permissive)

        return errors
    
    def allow_fallback(self) -> bool:
        """Check if fallback to local provider is allowed."""
        # PREPROD mirrors PRODUCTION behavior
        if self.environment in [Environment.PRODUCTION, Environment.PREPROD] and self.strict_mode:
            return False
        return True
    
    def allow_fallback_in_production(self) -> bool:
        """Check if fallback is allowed specifically in production."""
        return not self.strict_mode
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary with secrets masked."""
        return {
            "environment": self.environment.value,
            "provider_preference": self.get_provider_preference(),
            "pinecone_api_key": "***REDACTED***" if self.pinecone_api_key else None,
            "pinecone_environment": self.pinecone_environment,
            "pinecone_index_name": self.pinecone_index_name or self.generate_index_name(),
            "namespace_prefix": self.namespace_prefix,
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dimension,
            "strict_embedder_match": self.strict_embedder_match,
            "strict_mode": self.strict_mode,
            "debug_mode": self.debug_mode,
            "is_pinecone_configured": self.is_pinecone_configured(),
            "missing_config": self.get_missing_pinecone_config()
        }
    
    def format_for_logging(self) -> str:
        """Format configuration for logging output."""
        index_name = self.pinecone_index_name or self.generate_index_name()
        namespace_env = self.get_current_namespace_env()
        
        return (
            f"provider={self.get_provider_preference()} "
            f"environment={self.environment.value} "
            f"index={index_name} "
            f"namespace_prefix=env={namespace_env} "
            f"model={self.embedding_model} "
            f"dimension={self.embedding_dimension} "
            f"api_key={'***SET***' if self.pinecone_api_key else '***MISSING***'}"
        )
    
    def get_effective_index_name(self) -> str:
        """Get the effective index name (configured or generated)."""
        return self.pinecone_index_name or self.generate_index_name()
    
    def get_startup_validation_errors(self) -> List[str]:
        """Get validation errors that would prevent startup."""
        errors = []
        
        # Check environment-specific requirements
        env_errors = self.validate_for_environment(self.environment)
        errors.extend(env_errors)
        
        # Check if preferred provider is available
        preferred = self.get_provider_preference() 
        if preferred == VectorProvider.PINECONE and not self.is_pinecone_configured():
            if not self.allow_fallback():
                errors.append("Pinecone preferred but not configured, and fallback disabled")
        
        return errors