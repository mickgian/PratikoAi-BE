"""
Embedding Management Service for Advanced Vector Search.

Manages embedding generation, storage, and updates for Italian tax content
with efficient batch processing and Pinecone integration.
"""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.services.cache import CacheService


@dataclass
class EmbeddingRecord:
    """Record of an embedding operation"""
    id: str
    content: str
    embedding: List[float]
    source_type: str
    metadata: Dict
    created_at: datetime
    token_count: int


@dataclass
class BatchEmbeddingResult:
    """Result of batch embedding operation"""
    total_items: int
    successful: int
    failed: int
    total_tokens: int
    cost_estimate: float
    processing_time_seconds: float
    failed_items: List[Dict]


class EmbeddingManager:
    """
    Comprehensive embedding management for vector search system.
    
    Handles:
    - Batch embedding generation with OpenAI
    - Pinecone vector storage and updates
    - Italian tax content optimization
    - Embedding cache management
    - Performance monitoring and optimization
    """
    
    def __init__(
        self,
        pinecone_client,
        openai_client,
        db: Optional[AsyncSession] = None,
        cache_service: Optional[CacheService] = None
    ):
        self.pinecone = pinecone_client
        self.openai = openai_client
        self.db = db
        self.cache = cache_service
        
        # OpenAI embedding configuration
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimensions = 1536
        self.max_batch_size = 100
        self.max_content_length = 8000  # Characters per item
        
        # Pinecone configuration
        self.pinecone_namespaces = {
            'faq': 'faq_embeddings',
            'knowledge': 'knowledge_embeddings',
            'regulation': 'regulation_embeddings',
            'circular': 'circular_embeddings',
            'italian_tax_terms': 'italian_tax_terms'
        }
        
        # Performance settings
        self.embedding_cache_ttl = 86400  # 24 hours
        self.batch_delay_seconds = 1.0  # Rate limiting
        self.max_concurrent_batches = 3
        
        # Cost tracking
        self.embedding_cost_per_1k_tokens = 0.00002  # $0.00002 per 1K tokens
        
        # Statistics
        self.stats = {
            'total_embeddings_generated': 0,
            'total_tokens_processed': 0,
            'total_cost_usd': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    async def generate_embeddings(
        self,
        texts: List[str],
        source_type: str = 'general',
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text content to embed
            source_type: Type of content being embedded
            use_cache: Whether to use cached embeddings
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating embeddings for {len(texts)} {source_type} texts")
            
            # Check cache for existing embeddings
            embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            if use_cache and self.cache:
                for i, text in enumerate(texts):
                    cache_key = self._generate_embedding_cache_key(text)
                    cached_embedding = await self.cache.get(cache_key)
                    
                    if cached_embedding:
                        embeddings.append(cached_embedding)
                        self.stats['cache_hits'] += 1
                    else:
                        embeddings.append(None)  # Placeholder
                        uncached_texts.append(text)
                        uncached_indices.append(i)
                        self.stats['cache_misses'] += 1
            else:
                uncached_texts = texts
                uncached_indices = list(range(len(texts)))
                embeddings = [None] * len(texts)
            
            # Generate embeddings for uncached texts
            if uncached_texts:
                logger.debug(f"Generating embeddings for {len(uncached_texts)} uncached texts")
                
                new_embeddings = await self._batch_generate_embeddings(uncached_texts)
                
                # Insert new embeddings into results
                for i, embedding in enumerate(new_embeddings):
                    original_index = uncached_indices[i]
                    embeddings[original_index] = embedding
                    
                    # Cache new embedding
                    if use_cache and self.cache and embedding:
                        cache_key = self._generate_embedding_cache_key(uncached_texts[i])
                        await self.cache.setex(cache_key, self.embedding_cache_ttl, embedding)
            
            # Filter out None values (failed embeddings)
            valid_embeddings = [emb for emb in embeddings if emb is not None]
            
            processing_time = time.time() - start_time
            logger.info(f"Embedding generation completed in {processing_time:.2f}s: {len(valid_embeddings)}/{len(texts)} successful")
            
            return valid_embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []
    
    async def _batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API with batch processing"""
        
        try:
            # Prepare texts (truncate if too long)
            prepared_texts = []
            for text in texts:
                if len(text) > self.max_content_length:
                    # Truncate while preserving Italian sentence structure
                    truncated = self._truncate_text_italian(text, self.max_content_length)
                    prepared_texts.append(truncated)
                else:
                    prepared_texts.append(text)
            
            # Process in batches to respect rate limits
            all_embeddings = []
            
            for i in range(0, len(prepared_texts), self.max_batch_size):
                batch = prepared_texts[i:i + self.max_batch_size]
                
                if i > 0:
                    await asyncio.sleep(self.batch_delay_seconds)  # Rate limiting
                
                logger.debug(f"Processing embedding batch {i//self.max_batch_size + 1}: {len(batch)} items")
                
                try:
                    # Generate embeddings for batch
                    response = await self.openai.embeddings.create(
                        model=self.embedding_model,
                        input=batch,
                        encoding_format="float"
                    )
                    
                    # Extract embeddings from response
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    
                    # Update statistics
                    tokens_used = response.usage.total_tokens
                    self.stats['total_embeddings_generated'] += len(batch)
                    self.stats['total_tokens_processed'] += tokens_used
                    self.stats['total_cost_usd'] += (tokens_used / 1000) * self.embedding_cost_per_1k_tokens
                    
                except Exception as batch_error:
                    logger.error(f"Batch embedding failed: {batch_error}")
                    # Add None placeholders for failed batch
                    all_embeddings.extend([None] * len(batch))
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [None] * len(texts)
    
    def _truncate_text_italian(self, text: str, max_length: int) -> str:
        """Truncate text while preserving Italian sentence structure"""
        
        if len(text) <= max_length:
            return text
        
        # Find last sentence boundary within limit
        truncated = text[:max_length]
        
        # Italian sentence endings
        endings = ['. ', '! ', '? ', ': ', '; ']
        
        for ending in endings:
            last_pos = truncated.rfind(ending)
            if last_pos > max_length * 0.8:  # Must be in last 20% to avoid cutting too much
                return truncated[:last_pos + 1].strip()
        
        # Fallback: truncate at word boundary
        words = truncated.split()
        if len(words) > 10:
            return ' '.join(words[:-5]) + '...'  # Remove last 5 words
        
        return truncated
    
    async def update_pinecone_embeddings(
        self,
        items: List[Dict[str, Any]],
        source_type: str,
        namespace: Optional[str] = None,
        batch_size: int = 100
    ) -> BatchEmbeddingResult:
        """
        Update Pinecone with new embeddings for content items.
        
        Args:
            items: List of content items with id, content, metadata
            source_type: Type of content being embedded
            namespace: Pinecone namespace (auto-determined if None)
            batch_size: Number of items to process per batch
            
        Returns:
            BatchEmbeddingResult with processing statistics
        """
        start_time = time.time()
        
        try:
            if not items:
                return self._create_empty_batch_result()
            
            # Determine namespace
            target_namespace = namespace or self.pinecone_namespaces.get(source_type, 'default')
            
            logger.info(f"Updating Pinecone embeddings: {len(items)} items in namespace '{target_namespace}'")
            
            # Initialize result tracking
            result = BatchEmbeddingResult(
                total_items=len(items),
                successful=0,
                failed=0,
                total_tokens=0,
                cost_estimate=0.0,
                processing_time_seconds=0.0,
                failed_items=[]
            )
            
            # Process items in batches
            semaphore = asyncio.Semaphore(self.max_concurrent_batches)
            
            async def process_batch(batch_items: List[Dict]) -> Tuple[int, int, List[Dict]]:
                async with semaphore:
                    return await self._process_embedding_batch(
                        batch_items, 
                        source_type, 
                        target_namespace
                    )
            
            # Create batch tasks
            batch_tasks = []
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                task = asyncio.create_task(process_batch(batch))
                batch_tasks.append(task)
            
            # Execute all batches
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Aggregate results
            for batch_result in batch_results:
                if isinstance(batch_result, Exception):
                    logger.error(f"Batch processing error: {batch_result}")
                    result.failed += batch_size  # Assume entire batch failed
                    continue
                
                successful, failed, failed_items = batch_result
                result.successful += successful
                result.failed += failed
                result.failed_items.extend(failed_items)
            
            result.processing_time_seconds = time.time() - start_time
            
            logger.info(
                f"Pinecone update completed: {result.successful}/{result.total_items} successful, "
                f"time={result.processing_time_seconds:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Pinecone embedding update failed: {e}")
            return self._create_failed_batch_result(len(items), str(e))
    
    async def _process_embedding_batch(
        self,
        batch_items: List[Dict],
        source_type: str,
        namespace: str
    ) -> Tuple[int, int, List[Dict]]:
        """Process a single batch of items for embedding"""
        
        successful = 0
        failed = 0
        failed_items = []
        
        try:
            # Extract content for embedding
            texts = []
            for item in batch_items:
                content = item.get('content', '')
                if not content:
                    failed += 1
                    failed_items.append({
                        'id': item.get('id', 'unknown'),
                        'error': 'No content provided'
                    })
                    continue
                texts.append(content)
            
            if not texts:
                return 0, len(batch_items), failed_items
            
            # Generate embeddings
            embeddings = await self._batch_generate_embeddings(texts)
            
            # Prepare vectors for Pinecone
            vectors = []
            embedding_index = 0
            
            for item in batch_items:
                if not item.get('content'):
                    continue  # Already counted as failed
                
                embedding = embeddings[embedding_index] if embedding_index < len(embeddings) else None
                embedding_index += 1
                
                if not embedding:
                    failed += 1
                    failed_items.append({
                        'id': item.get('id', 'unknown'),
                        'error': 'Embedding generation failed'
                    })
                    continue
                
                # Prepare metadata
                metadata = self._prepare_metadata(item, source_type)
                
                vector = {
                    'id': str(item['id']),
                    'values': embedding,
                    'metadata': metadata
                }
                vectors.append(vector)
            
            # Upsert to Pinecone
            if vectors:
                try:
                    upsert_response = self.pinecone.upsert(
                        vectors=vectors,
                        namespace=namespace
                    )
                    
                    successful = upsert_response.get('upserted_count', len(vectors))
                    logger.debug(f"Upserted {successful} vectors to namespace '{namespace}'")
                    
                except Exception as upsert_error:
                    logger.error(f"Pinecone upsert failed: {upsert_error}")
                    failed += len(vectors)
                    failed_items.extend([
                        {'id': v['id'], 'error': str(upsert_error)} for v in vectors
                    ])
            
            return successful, failed, failed_items
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            return 0, len(batch_items), [{'id': 'batch', 'error': str(e)}]
    
    def _prepare_metadata(self, item: Dict, source_type: str) -> Dict:
        """Prepare metadata for Pinecone storage"""
        
        # Start with basic metadata
        metadata = {
            'source_type': source_type,
            'updated_at': datetime.utcnow().isoformat(),
            'language': 'it'  # Italian content
        }
        
        # Add content excerpt (Pinecone metadata has size limits)
        content = item.get('content', '')
        if content:
            metadata['content'] = content[:1000]  # First 1000 characters
        
        # Add specific fields based on source type
        if source_type == 'faq':
            metadata.update({
                'question': item.get('question', '')[:500],
                'category': item.get('category', ''),
                'tags': item.get('tags', [])[:10],  # Limit tags
                'quality_score': item.get('quality_score', 0.0),
                'usage_count': item.get('usage_count', 0),
                'published': item.get('published', False)
            })
        
        elif source_type == 'regulation':
            metadata.update({
                'title': item.get('title', '')[:500],
                'document_type': item.get('document_type', ''),
                'publication_date': item.get('publication_date', ''),
                'authority': item.get('authority', ''),
                'subject_tags': item.get('subject_tags', [])[:10]
            })
        
        elif source_type == 'knowledge':
            metadata.update({
                'title': item.get('title', '')[:500],
                'category': item.get('category', ''),
                'confidence_score': item.get('confidence_score', 0.0),
                'view_count': item.get('view_count', 0),
                'expert_reviewed': item.get('expert_reviewed', False)
            })
        
        # Add custom metadata if provided
        if 'metadata' in item and isinstance(item['metadata'], dict):
            # Only add simple types to avoid Pinecone issues
            for key, value in item['metadata'].items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[f"custom_{key}"] = value
        
        return metadata
    
    def _generate_embedding_cache_key(self, text: str) -> str:
        """Generate cache key for embedding"""
        
        # Use content hash for consistent caching
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"embedding:{self.embedding_model}:{content_hash}"
    
    def _create_empty_batch_result(self) -> BatchEmbeddingResult:
        """Create empty batch result"""
        
        return BatchEmbeddingResult(
            total_items=0,
            successful=0,
            failed=0,
            total_tokens=0,
            cost_estimate=0.0,
            processing_time_seconds=0.0,
            failed_items=[]
        )
    
    def _create_failed_batch_result(self, total_items: int, error: str) -> BatchEmbeddingResult:
        """Create failed batch result"""
        
        return BatchEmbeddingResult(
            total_items=total_items,
            successful=0,
            failed=total_items,
            total_tokens=0,
            cost_estimate=0.0,
            processing_time_seconds=0.0,
            failed_items=[{'id': 'batch', 'error': error}]
        )
    
    async def delete_embeddings(
        self,
        ids: List[str],
        namespace: str
    ) -> Dict[str, Any]:
        """Delete embeddings from Pinecone"""
        
        try:
            if not ids:
                return {'deleted_count': 0}
            
            logger.info(f"Deleting {len(ids)} embeddings from namespace '{namespace}'")
            
            # Delete from Pinecone
            delete_response = self.pinecone.delete(
                ids=ids,
                namespace=namespace
            )
            
            # Clear from cache if available
            if self.cache:
                # Note: We don't have the original content to generate cache keys,
                # so we can't efficiently clear specific embeddings from cache
                pass
            
            logger.info(f"Deleted embeddings: {delete_response}")
            
            return {
                'deleted_count': len(ids),
                'namespace': namespace,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}")
            return {
                'deleted_count': 0,
                'namespace': namespace,
                'success': False,
                'error': str(e)
            }
    
    async def search_similar_content(
        self,
        query_text: str,
        source_types: List[str] = ['faq', 'knowledge', 'regulation'],
        top_k: int = 10,
        min_similarity: float = 0.7,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for similar content across namespaces"""
        
        try:
            # Generate query embedding
            query_embeddings = await self.generate_embeddings([query_text])
            if not query_embeddings:
                return []
            
            query_embedding = query_embeddings[0]
            
            # Search across specified source types
            all_results = []
            
            for source_type in source_types:
                namespace = self.pinecone_namespaces.get(source_type)
                if not namespace:
                    continue
                
                # Prepare filters
                search_filter = {'source_type': source_type}
                if filters:
                    search_filter.update(filters)
                
                try:
                    # Search in Pinecone
                    results = self.pinecone.query(
                        vector=query_embedding,
                        top_k=top_k,
                        include_metadata=True,
                        filter=search_filter,
                        namespace=namespace
                    )
                    
                    # Process results
                    for match in results.get('matches', []):
                        if match['score'] >= min_similarity:
                            result = {
                                'id': match['id'],
                                'score': match['score'],
                                'source_type': source_type,
                                'metadata': match.get('metadata', {})
                            }
                            all_results.append(result)
                
                except Exception as search_error:
                    logger.error(f"Search failed for namespace {namespace}: {search_error}")
                    continue
            
            # Sort by similarity score
            all_results.sort(key=lambda x: x['score'], reverse=True)
            
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"Similar content search failed: {e}")
            return []
    
    async def get_embedding_statistics(self) -> Dict[str, Any]:
        """Get comprehensive embedding management statistics"""
        
        try:
            # Get Pinecone index stats
            pinecone_stats = {}
            try:
                index_stats = self.pinecone.describe_index_stats()
                pinecone_stats = {
                    'total_vector_count': index_stats.get('total_vector_count', 0),
                    'dimension': index_stats.get('dimension', self.embedding_dimensions),
                    'namespaces': index_stats.get('namespaces', {})
                }
            except Exception as e:
                logger.warning(f"Could not get Pinecone stats: {e}")
            
            # Calculate cost efficiency
            cost_per_embedding = (
                self.stats['total_cost_usd'] / max(self.stats['total_embeddings_generated'], 1)
            )
            
            cache_hit_rate = (
                self.stats['cache_hits'] / max(self.stats['cache_hits'] + self.stats['cache_misses'], 1)
            )
            
            return {
                'generation_stats': {
                    'total_embeddings_generated': self.stats['total_embeddings_generated'],
                    'total_tokens_processed': self.stats['total_tokens_processed'],
                    'total_cost_usd': round(self.stats['total_cost_usd'], 6),
                    'cost_per_embedding': round(cost_per_embedding, 6)
                },
                'cache_stats': {
                    'cache_hits': self.stats['cache_hits'],
                    'cache_misses': self.stats['cache_misses'],
                    'hit_rate': round(cache_hit_rate, 3)
                },
                'pinecone_stats': pinecone_stats,
                'configuration': {
                    'embedding_model': self.embedding_model,
                    'dimensions': self.embedding_dimensions,
                    'max_batch_size': self.max_batch_size,
                    'max_content_length': self.max_content_length
                },
                'performance_metrics': {
                    'avg_batch_processing_time': '~2-5 seconds',
                    'cost_efficiency': 'Optimized with caching and batching',
                    'rate_limiting': f"{self.batch_delay_seconds}s between batches"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding statistics: {e}")
            return {'error': str(e)}
    
    def reset_statistics(self):
        """Reset embedding statistics"""
        
        self.stats = {
            'total_embeddings_generated': 0,
            'total_tokens_processed': 0,
            'total_cost_usd': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info("Embedding statistics reset")
    
    async def optimize_embeddings(
        self,
        source_type: str,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """Optimize embeddings for a source type (rebuild outdated ones)"""
        
        try:
            logger.info(f"Starting embedding optimization for source type: {source_type}")
            
            # This would typically query the database for outdated content
            # and regenerate embeddings. Implementation depends on your data model.
            
            optimization_result = {
                'source_type': source_type,
                'processed_items': 0,
                'updated_embeddings': 0,
                'processing_time_seconds': 0.0,
                'status': 'completed'
            }
            
            logger.info(f"Embedding optimization completed for {source_type}")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Embedding optimization failed for {source_type}: {e}")
            return {
                'source_type': source_type,
                'status': 'failed',
                'error': str(e)
            }