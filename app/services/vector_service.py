"""Vector database service for semantic search and knowledge embeddings."""

import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    from pinecone import Pinecone, ServerlessSpec
    from sentence_transformers import SentenceTransformer
    VECTOR_DEPENDENCIES_AVAILABLE = True
except ImportError:
    VECTOR_DEPENDENCIES_AVAILABLE = False

from app.core.config import settings
from app.core.logging import logger


class VectorService:
    """Service for vector database operations and semantic search."""
    
    def __init__(self):
        """Initialize vector service with Pinecone and embedding model."""
        self.pinecone_client = None
        self.index = None
        self.embedding_model = None
        
        if not VECTOR_DEPENDENCIES_AVAILABLE:
            logger.warning("vector_dependencies_not_available", 
                         message="Pinecone and sentence-transformers not installed")
            return
        
        self._initialize_pinecone()
        self._initialize_embedding_model()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone client and index."""
        try:
            if not settings.PINECONE_API_KEY:
                logger.warning("pinecone_api_key_not_configured")
                return
            
            # Initialize Pinecone client
            from pinecone import Pinecone, ServerlessSpec
            
            self.pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
            
            # Check if index exists, create if not
            existing_indexes = self.pinecone_client.list_indexes().names()
            
            if settings.PINECONE_INDEX_NAME not in existing_indexes:
                logger.info(
                    "creating_pinecone_index",
                    index_name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.VECTOR_DIMENSION
                )
                
                self.pinecone_client.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.VECTOR_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            
            # Connect to index
            self.index = self.pinecone_client.Index(settings.PINECONE_INDEX_NAME)
            
            logger.info(
                "pinecone_initialized",
                index_name=settings.PINECONE_INDEX_NAME
            )
            
        except Exception as e:
            logger.error(
                "pinecone_initialization_failed",
                error=str(e),
                exc_info=True
            )
            self.pinecone_client = None
            self.index = None
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model for embeddings."""
        try:
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(
                "embedding_model_initialized",
                model=settings.EMBEDDING_MODEL
            )
            
        except Exception as e:
            logger.error(
                "embedding_model_initialization_failed",
                model=settings.EMBEDDING_MODEL,
                error=str(e),
                exc_info=True
            )
            self.embedding_model = None
    
    def is_available(self) -> bool:
        """Check if vector service is available."""
        return (
            VECTOR_DEPENDENCIES_AVAILABLE and 
            self.pinecone_client is not None and 
            self.index is not None and 
            self.embedding_model is not None
        )
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding vector for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if service unavailable
        """
        if not self.is_available():
            logger.warning("vector_service_not_available", operation="create_embedding")
            return None
        
        try:
            # Clean and normalize text
            text = text.strip()
            if not text:
                return None
            
            # Generate embedding
            embedding = self.embedding_model.encode(text).tolist()
            
            logger.debug(
                "embedding_created",
                text_length=len(text),
                embedding_dimension=len(embedding)
            )
            
            return embedding
            
        except Exception as e:
            logger.error(
                "embedding_creation_failed",
                text_length=len(text) if text else 0,
                error=str(e)
            )
            return None
    
    def store_document(self, document_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        """Store document in vector database.
        
        Args:
            document_id: Unique document identifier
            text: Document text content
            metadata: Document metadata
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("vector_service_not_available", operation="store_document")
            return False
        
        try:
            # Create embedding
            embedding = self.create_embedding(text)
            if not embedding:
                return False
            
            # Prepare metadata with additional info
            vector_metadata = {
                **metadata,
                "text": text[:1000],  # Store first 1000 chars for preview
                "text_length": len(text),
                "stored_at": datetime.utcnow().isoformat(),
                "text_hash": hashlib.md5(text.encode()).hexdigest()
            }
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[(document_id, embedding, vector_metadata)]
            )
            
            logger.info(
                "document_stored",
                document_id=document_id,
                text_length=len(text),
                metadata_keys=list(metadata.keys())
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "document_storage_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True
            )
            return False
    
    def search_similar_documents(
        self, 
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using semantic search.
        
        Args:
            query: Search query text
            filter_metadata: Metadata filters
            top_k: Number of results to return
            
        Returns:
            List of similar documents with scores
        """
        if not self.is_available():
            logger.warning("vector_service_not_available", operation="search_similar")
            return []
        
        try:
            # Create query embedding
            query_embedding = self.create_embedding(query)
            if not query_embedding:
                return []
            
            # Set default top_k
            if top_k is None:
                top_k = settings.MAX_SEARCH_RESULTS
            
            # Search in Pinecone
            search_results = self.index.query(
                vector=query_embedding,
                filter=filter_metadata,
                top_k=top_k,
                include_metadata=True
            )
            
            # Process results
            results = []
            for match in search_results.matches:
                if match.score >= settings.VECTOR_SIMILARITY_THRESHOLD:
                    result = {
                        "id": match.id,
                        "score": match.score,
                        "metadata": match.metadata,
                        "text_preview": match.metadata.get("text", ""),
                    }
                    results.append(result)
            
            logger.info(
                "similarity_search_completed",
                query_length=len(query),
                results_count=len(results),
                total_matches=len(search_results.matches)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "similarity_search_failed",
                query=query[:100],  # Log first 100 chars
                error=str(e),
                exc_info=True
            )
            return []
    
    def hybrid_search(
        self, 
        query: str, 
        keyword_results: List[Dict[str, Any]] = None,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining semantic and keyword search.
        
        Args:
            query: Search query
            keyword_results: Results from keyword search
            semantic_weight: Weight for semantic search (0-1)
            
        Returns:
            Combined and ranked results
        """
        try:
            # Get semantic search results
            semantic_results = self.search_similar_documents(query)
            
            # If no keyword results provided, return semantic only
            if not keyword_results:
                return semantic_results
            
            # Combine results with weighted scoring
            combined_results = {}
            
            # Add semantic results with weight
            for result in semantic_results:
                doc_id = result["id"]
                combined_results[doc_id] = {
                    **result,
                    "hybrid_score": result["score"] * semantic_weight,
                    "semantic_score": result["score"],
                    "keyword_score": 0.0
                }
            
            # Add keyword results with weight
            keyword_weight = 1.0 - semantic_weight
            for result in keyword_results:
                doc_id = result.get("id", result.get("document_id", ""))
                keyword_score = result.get("score", 0.5)  # Default score if not provided
                
                if doc_id in combined_results:
                    # Update existing result
                    combined_results[doc_id]["hybrid_score"] += keyword_score * keyword_weight
                    combined_results[doc_id]["keyword_score"] = keyword_score
                else:
                    # Add new result
                    combined_results[doc_id] = {
                        **result,
                        "hybrid_score": keyword_score * keyword_weight,
                        "semantic_score": 0.0,
                        "keyword_score": keyword_score
                    }
            
            # Sort by hybrid score and return
            sorted_results = sorted(
                combined_results.values(),
                key=lambda x: x["hybrid_score"],
                reverse=True
            )
            
            logger.info(
                "hybrid_search_completed",
                query=query[:50],
                semantic_count=len(semantic_results),
                keyword_count=len(keyword_results) if keyword_results else 0,
                combined_count=len(sorted_results)
            )
            
            return sorted_results[:settings.MAX_SEARCH_RESULTS]
            
        except Exception as e:
            logger.error(
                "hybrid_search_failed",
                query=query[:100],
                error=str(e),
                exc_info=True
            )
            # Fallback to semantic search only
            return self.search_similar_documents(query)
    
    def store_italian_regulation(
        self, 
        regulation_id: int, 
        title: str, 
        summary: str, 
        full_text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Store Italian regulation in vector database for semantic search.
        
        Args:
            regulation_id: Regulation database ID
            title: Regulation title
            summary: Regulation summary
            full_text: Full regulation text
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            # Combine title, summary, and text for embedding
            combined_text = f"{title}\n\n{summary}\n\n{full_text}"
            
            # Prepare document ID and metadata
            document_id = f"regulation_{regulation_id}"
            vector_metadata = {
                **metadata,
                "type": "regulation",
                "regulation_id": regulation_id,
                "title": title,
                "summary": summary,
                "language": "italian"
            }
            
            return self.store_document(document_id, combined_text, vector_metadata)
            
        except Exception as e:
            logger.error(
                "regulation_storage_failed",
                regulation_id=regulation_id,
                error=str(e)
            )
            return False
    
    def store_tax_rate_info(
        self,
        rate_id: int,
        description: str,
        tax_type: str,
        rate_percentage: float,
        conditions_text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Store tax rate information for semantic search.
        
        Args:
            rate_id: Tax rate database ID
            description: Rate description
            tax_type: Type of tax
            rate_percentage: Tax rate percentage
            conditions_text: Conditions and applicability text
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            # Create searchable text
            combined_text = f"""
            Aliquota {tax_type}: {rate_percentage}%
            Descrizione: {description}
            Condizioni: {conditions_text}
            """
            
            # Prepare document ID and metadata
            document_id = f"tax_rate_{rate_id}"
            vector_metadata = {
                **metadata,
                "type": "tax_rate",
                "rate_id": rate_id,
                "tax_type": tax_type,
                "rate_percentage": rate_percentage,
                "description": description,
                "language": "italian"
            }
            
            return self.store_document(document_id, combined_text, vector_metadata)
            
        except Exception as e:
            logger.error(
                "tax_rate_storage_failed",
                rate_id=rate_id,
                error=str(e)
            )
            return False
    
    def store_legal_template(
        self,
        template_id: int,
        title: str,
        content: str,
        category: str,
        variables: List[str],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store legal template for semantic search.
        
        Args:
            template_id: Template database ID
            title: Template title
            content: Template content
            category: Template category
            variables: Required variables
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            # Create searchable text including template purpose
            searchable_text = f"""
            Modello {category}: {title}
            Contenuto: {content}
            Variabili richieste: {', '.join(variables)}
            """
            
            # Prepare document ID and metadata
            document_id = f"template_{template_id}"
            vector_metadata = {
                **metadata,
                "type": "legal_template",
                "template_id": template_id,
                "title": title,
                "category": category,
                "variables": variables,
                "language": "italian"
            }
            
            return self.store_document(document_id, searchable_text, vector_metadata)
            
        except Exception as e:
            logger.error(
                "template_storage_failed",
                template_id=template_id,
                error=str(e)
            )
            return False
    
    def search_italian_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        language: str = "italian"
    ) -> List[Dict[str, Any]]:
        """Search Italian knowledge base using semantic search.
        
        Args:
            query: Search query in Italian
            knowledge_type: Filter by type (regulation, tax_rate, template)
            language: Language filter
            
        Returns:
            Relevant knowledge items
        """
        try:
            # Prepare filters
            filters = {"language": language}
            if knowledge_type:
                filters["type"] = knowledge_type
            
            # Perform semantic search
            results = self.search_similar_documents(
                query=query,
                filter_metadata=filters
            )
            
            # Enhance results with type-specific information
            enhanced_results = []
            for result in results:
                metadata = result["metadata"]
                enhanced_result = {
                    **result,
                    "knowledge_type": metadata.get("type", "unknown"),
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", metadata.get("summary", "")),
                }
                
                # Add type-specific fields
                if metadata.get("type") == "regulation":
                    enhanced_result.update({
                        "regulation_id": metadata.get("regulation_id"),
                        "authority": metadata.get("authority", ""),
                    })
                elif metadata.get("type") == "tax_rate":
                    enhanced_result.update({
                        "rate_id": metadata.get("rate_id"),
                        "tax_type": metadata.get("tax_type", ""),
                        "rate_percentage": metadata.get("rate_percentage", 0),
                    })
                elif metadata.get("type") == "legal_template":
                    enhanced_result.update({
                        "template_id": metadata.get("template_id"),
                        "category": metadata.get("category", ""),
                        "variables": metadata.get("variables", []),
                    })
                
                enhanced_results.append(enhanced_result)
            
            logger.info(
                "italian_knowledge_search_completed",
                query=query[:50],
                knowledge_type=knowledge_type,
                results_count=len(enhanced_results)
            )
            
            return enhanced_results
            
        except Exception as e:
            logger.error(
                "italian_knowledge_search_failed",
                query=query[:100],
                knowledge_type=knowledge_type,
                error=str(e),
                exc_info=True
            )
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get vector database index statistics.
        
        Returns:
            Index statistics
        """
        if not self.is_available():
            return {"status": "unavailable", "reason": "Vector service not initialized"}
        
        try:
            stats = self.index.describe_index_stats()
            
            return {
                "status": "available",
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {},
                "model": settings.EMBEDDING_MODEL,
                "similarity_threshold": settings.VECTOR_SIMILARITY_THRESHOLD
            }
            
        except Exception as e:
            logger.error(
                "index_stats_retrieval_failed", 
                error=str(e)
            )
            return {"status": "error", "error": str(e)}
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document from vector database.
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.warning("vector_service_not_available", operation="delete_document")
            return False
        
        try:
            self.index.delete(ids=[document_id])
            
            logger.info(
                "document_deleted",
                document_id=document_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "document_deletion_failed",
                document_id=document_id,
                error=str(e)
            )
            return False


# Global instance
vector_service = VectorService()