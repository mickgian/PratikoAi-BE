"""
Local vector search provider implementation.

Provides vector search capabilities using in-memory or local storage,
suitable for development and fallback scenarios.
"""

import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from app.core.logging import logger


class LocalVectorProvider:
    """Local vector search provider using in-memory storage."""
    
    def __init__(self, embedding_dimension: int = 384, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize local vector provider."""
        self.embedding_dimension = embedding_dimension
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        
        # In-memory storage
        self.vectors = {}
        self.metadata = {}
        
        # Initialize embedding model if available
        self._initialize_embedding_model()
        
        logger.info("local_vector_provider_initialized",
                   dimension=embedding_dimension,
                   model=embedding_model,
                   has_embeddings=self.embedding_model is not None)
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model for embeddings."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence_transformers_not_available")
            return
        
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info("local_embedding_model_loaded", model=self.embedding_model_name)
        except Exception as e:
            logger.error("local_embedding_model_failed", error=str(e), model=self.embedding_model_name)
    
    def upsert(self, vectors: List[Dict[str, Any]]) -> bool:
        """Upsert vectors into local storage."""
        try:
            for item in vectors:
                doc_id = item["id"]
                vector = item["vector"]
                metadata = item.get("metadata", {})
                
                # Store vector and metadata
                self.vectors[doc_id] = vector
                self.metadata[doc_id] = {
                    **metadata,
                    "upserted_at": datetime.utcnow().isoformat(),
                    "provider": "local"
                }
            
            logger.debug("local_upsert_complete", count=len(vectors))
            return True
            
        except Exception as e:
            logger.error("local_upsert_failed", error=str(e), count=len(vectors))
            return False
    
    def _upsert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """Internal upsert method for testing."""
        return self.upsert(vectors)
    
    def query(self, vector: List[float], top_k: int = 10, namespace: str = None) -> List[Dict[str, Any]]:
        """Query vectors using cosine similarity."""
        try:
            if not self.vectors:
                logger.debug("local_query_empty_index")
                return []
            
            # Calculate cosine similarity for all vectors
            similarities = []
            for doc_id, stored_vector in self.vectors.items():
                similarity = self._cosine_similarity(vector, stored_vector)
                similarities.append({
                    "id": doc_id,
                    "score": similarity,
                    "metadata": self.metadata.get(doc_id, {})
                })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x["score"], reverse=True)
            results = similarities[:top_k]
            
            logger.debug("local_query_complete", 
                        query_vector_dim=len(vector),
                        total_vectors=len(self.vectors),
                        results=len(results))
            
            return results
            
        except Exception as e:
            logger.error("local_query_failed", error=str(e))
            return []
    
    def _query_vectors(self, vector: List[float], top_k: int = 10, namespace: str = None) -> List[Dict[str, Any]]:
        """Internal query method for testing."""
        return self.query(vector, top_k, namespace)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            import math
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            mag1 = math.sqrt(sum(a * a for a in vec1))
            mag2 = math.sqrt(sum(a * a for a in vec2))
            
            # Avoid division by zero
            if mag1 == 0 or mag2 == 0:
                return 0.0
            
            return dot_product / (mag1 * mag2)
            
        except Exception:
            return 0.0
    
    def get_index_dimension(self) -> Optional[int]:
        """Get the dimension of the vector index."""
        return self.embedding_dimension
    
    def test_connection(self) -> bool:
        """Test local provider connection (always returns True)."""
        try:
            # Simple test - verify we can store and retrieve
            test_vector = [0.1] * self.embedding_dimension
            test_doc = {
                "id": "test_connection",
                "vector": test_vector,
                "metadata": {"test": True}
            }
            
            # Test upsert
            success = self.upsert([test_doc])
            if not success:
                return False
            
            # Test query
            results = self.query(test_vector, top_k=1)
            
            # Cleanup test document
            if "test_connection" in self.vectors:
                del self.vectors["test_connection"]
            if "test_connection" in self.metadata:
                del self.metadata["test_connection"]
            
            return len(results) > 0 and results[0]["id"] == "test_connection"
            
        except Exception as e:
            logger.error("local_connection_test_failed", error=str(e))
            return False
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embeddings for text using the local model."""
        if not self.embedding_model:
            logger.warning("local_embedding_not_available")
            return None
        
        try:
            embedding = self.embedding_model.encode(text).tolist()
            logger.debug("local_text_embedded", text_length=len(text), embedding_dim=len(embedding))
            return embedding
        except Exception as e:
            logger.error("local_embedding_failed", error=str(e), text_length=len(text))
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the local vector store."""
        return {
            "provider": "local",
            "total_vectors": len(self.vectors),
            "embedding_dimension": self.embedding_dimension,
            "embedding_model": self.embedding_model_name,
            "has_embedding_model": self.embedding_model is not None,
            "memory_usage_mb": len(str(self.vectors)) / (1024 * 1024)  # Rough estimate
        }
    
    def clear(self) -> bool:
        """Clear all vectors from local storage."""
        try:
            vector_count = len(self.vectors)
            self.vectors.clear()
            self.metadata.clear()
            
            logger.info("local_storage_cleared", previous_count=vector_count)
            return True
            
        except Exception as e:
            logger.error("local_storage_clear_failed", error=str(e))
            return False
    
    def save_to_disk(self, filepath: str) -> bool:
        """Save local vectors to disk for persistence."""
        try:
            data = {
                "vectors": self.vectors,
                "metadata": self.metadata,
                "config": {
                    "embedding_dimension": self.embedding_dimension,
                    "embedding_model": self.embedding_model_name,
                    "saved_at": datetime.utcnow().isoformat()
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info("local_vectors_saved", filepath=filepath, count=len(self.vectors))
            return True
            
        except Exception as e:
            logger.error("local_vectors_save_failed", error=str(e), filepath=filepath)
            return False
    
    def load_from_disk(self, filepath: str) -> bool:
        """Load local vectors from disk."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.vectors = data.get("vectors", {})
            self.metadata = data.get("metadata", {})
            
            # Validate config compatibility
            config = data.get("config", {})
            saved_dimension = config.get("embedding_dimension")
            if saved_dimension and saved_dimension != self.embedding_dimension:
                logger.warning("local_dimension_mismatch",
                             current=self.embedding_dimension,
                             saved=saved_dimension)
            
            logger.info("local_vectors_loaded", 
                       filepath=filepath, 
                       count=len(self.vectors),
                       saved_at=config.get("saved_at"))
            return True
            
        except FileNotFoundError:
            logger.info("local_vectors_file_not_found", filepath=filepath)
            return False
        except Exception as e:
            logger.error("local_vectors_load_failed", error=str(e), filepath=filepath)
            return False