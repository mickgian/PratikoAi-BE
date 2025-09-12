"""
Enhanced vector service with environment-aware provider selection and guardrails.

Wraps the existing VectorService to add provider factory functionality while
maintaining backward compatibility with existing code.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import get_environment
from app.core.logging import logger
from app.services.vector_config import VectorConfig
from app.services.vector_provider_factory import VectorProviderFactory

# Import existing VectorService for fallback compatibility
from app.services.vector_service import VectorService as LegacyVectorService

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EnhancedVectorService:
    """Enhanced vector service with provider factory and guardrails."""
    
    def __init__(self, config: Optional[VectorConfig] = None):
        """Initialize enhanced vector service."""
        self.config = config or VectorConfig()
        self.environment = get_environment()
        
        # Initialize provider factory
        self.factory = VectorProviderFactory(self.config)
        
        # Initialize provider and embedding model
        self.provider = None
        self.embedding_model = None
        
        # Legacy service for fallback
        self.legacy_service = None
        
        # Initialize components
        self._initialize_provider()
        self._initialize_embedding_model()
        self._perform_startup_checks()
    
    def _initialize_provider(self):
        """Initialize vector provider using factory."""
        try:
            self.provider = self.factory.get_provider(self.environment)
            
            logger.info("enhanced_vector_service_provider_initialized",
                       provider=type(self.provider).__name__,
                       environment=self.environment.value)
            
        except Exception as e:
            logger.error("enhanced_vector_service_provider_failed", 
                        error=str(e),
                        environment=self.environment.value)
            
            # Fallback to legacy service for compatibility
            try:
                self.legacy_service = LegacyVectorService()
                logger.info("fallback_to_legacy_vector_service")
            except Exception as legacy_error:
                logger.error("legacy_vector_service_fallback_failed", error=str(legacy_error))
    
    def _initialize_embedding_model(self):
        """Initialize embedding model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence_transformers_not_available")
            return
        
        try:
            self.embedding_model = SentenceTransformer(self.config.embedding_model)
            logger.info("enhanced_embedding_model_initialized", 
                       model=self.config.embedding_model)
        except Exception as e:
            logger.error("enhanced_embedding_model_failed", 
                        error=str(e), 
                        model=self.config.embedding_model)
    
    def _perform_startup_checks(self):
        """Perform startup validation checks."""
        if not self.provider:
            logger.warning("enhanced_vector_service_no_provider")
            return
        
        try:
            checks = self.factory.perform_startup_checks(self.provider, self.embedding_model)
            
            # Log startup status
            logger.info("enhanced_vector_service_startup_complete",
                       provider=checks["provider_type"],
                       status=checks["status"],
                       warnings=len(checks["warnings"]),
                       errors=len(checks["errors"]))
            
            # Log configuration
            logger.info("enhanced_vector_service_configuration",
                       **self.config.to_safe_dict())
            
        except Exception as e:
            logger.error("enhanced_vector_service_startup_checks_failed", error=str(e))
    
    def is_available(self) -> bool:
        """Check if vector service is available."""
        if self.provider:
            return True
        elif self.legacy_service:
            return self.legacy_service.is_available()
        return False
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding vector for text."""
        if not text or not text.strip():
            return None
        
        # Use enhanced embedding model if available
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode(text.strip()).tolist()
                logger.debug("enhanced_embedding_created",
                           text_length=len(text),
                           dimension=len(embedding))
                return embedding
            except Exception as e:
                logger.error("enhanced_embedding_failed", error=str(e))
        
        # Fallback to legacy service
        if self.legacy_service:
            return self.legacy_service.create_embedding(text)
        
        return None
    
    def store_document(self, document_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        """Store document with enhanced provider selection."""
        if not self.is_available():
            logger.warning("enhanced_vector_service_unavailable", operation="store_document")
            return False
        
        # Generate embedding
        embedding = self.create_embedding(text)
        if not embedding:
            logger.warning("enhanced_store_document_no_embedding", document_id=document_id)
            return False
        
        # Use enhanced provider if available
        if self.provider:
            try:
                # Add environment-aware metadata
                enhanced_metadata = {
                    **metadata,
                    "environment": self.environment.value,
                    "service_version": "enhanced",
                    "stored_at": datetime.utcnow().isoformat()
                }
                
                vector_data = [{
                    "id": document_id,
                    "vector": embedding,
                    "metadata": enhanced_metadata
                }]
                
                # Build namespace if metadata contains domain
                namespace = None
                if "domain" in metadata:
                    namespace = self.config.build_namespace(
                        env=self.config.get_current_namespace_env(),
                        domain=metadata["domain"],
                        tenant=metadata.get("tenant", "default")
                    )
                
                success = self.provider.upsert(vector_data, namespace=namespace)
                
                if success:
                    logger.debug("enhanced_document_stored",
                               document_id=document_id,
                               namespace=namespace,
                               provider=type(self.provider).__name__)
                
                return success
                
            except Exception as e:
                logger.error("enhanced_store_document_failed", 
                           error=str(e), 
                           document_id=document_id)
        
        # Fallback to legacy service
        if self.legacy_service:
            return self.legacy_service.store_document(document_id, text, metadata)
        
        return False
    
    def search_similar(self, query_text: str, top_k: int = 10, 
                      domain: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for similar documents with enhanced filtering."""
        if not self.is_available():
            logger.warning("enhanced_vector_service_unavailable", operation="search_similar")
            return []
        
        # Generate query embedding
        query_embedding = self.create_embedding(query_text)
        if not query_embedding:
            logger.warning("enhanced_search_no_query_embedding")
            return []
        
        # Use enhanced provider if available
        if self.provider:
            try:
                # Build namespace for domain-specific search
                namespace = None
                if domain:
                    namespace = self.config.build_namespace(
                        env=self.config.get_current_namespace_env(),
                        domain=domain,
                        tenant="default"  # Could be parameterized
                    )
                
                results = self.provider.query(
                    vector=query_embedding,
                    top_k=top_k,
                    namespace=namespace,
                    filter_dict=filters
                )
                
                logger.debug("enhanced_search_complete",
                           query_length=len(query_text),
                           results=len(results),
                           domain=domain,
                           namespace=namespace)
                
                return results
                
            except Exception as e:
                logger.error("enhanced_search_failed", error=str(e))
        
        # Fallback to legacy service
        if self.legacy_service:
            return self.legacy_service.search_similar(query_text, top_k, filters)
        
        return []
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        stats = {
            "service_version": "enhanced",
            "environment": self.environment.value,
            "config": self.config.to_safe_dict(),
            "provider_available": self.provider is not None,
            "legacy_fallback": self.legacy_service is not None,
            "embedding_model_available": self.embedding_model is not None
        }
        
        # Add provider-specific stats
        if self.provider and hasattr(self.provider, 'get_stats'):
            try:
                stats["provider_stats"] = self.provider.get_stats()
            except Exception as e:
                stats["provider_stats_error"] = str(e)
        elif self.provider and hasattr(self.provider, 'get_index_stats'):
            try:
                stats["provider_stats"] = self.provider.get_index_stats()
            except Exception as e:
                stats["provider_stats_error"] = str(e)
        
        # Add legacy stats if available
        if self.legacy_service:
            try:
                stats["legacy_service_available"] = self.legacy_service.is_available()
            except Exception:
                pass
        
        return stats
    
    # Italian-specific methods for backward compatibility
    def store_italian_regulation(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Store Italian regulation document."""
        enhanced_metadata = {
            **metadata,
            "domain": "fiscale",  # Default domain for regulations
            "language": "italian",
            "document_type": "regulation"
        }
        return self.store_document(doc_id, content, enhanced_metadata)
    
    def store_ccnl_content(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Store CCNL (labor contract) content."""
        enhanced_metadata = {
            **metadata,
            "domain": "ccnl",
            "language": "italian",
            "document_type": "ccnl"
        }
        return self.store_document(doc_id, content, enhanced_metadata)
    
    def search_italian_regulations(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search Italian regulations specifically."""
        return self.search_similar(
            query_text=query,
            top_k=top_k,
            domain="fiscale",
            filters={"document_type": "regulation"}
        )
    
    def search_ccnl_content(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search CCNL content specifically."""
        return self.search_similar(
            query_text=query,
            top_k=top_k,
            domain="ccnl",
            filters={"document_type": "ccnl"}
        )


# Backward compatibility alias
VectorService = EnhancedVectorService