"""
Expert Feedback Collection Service for Quality Analysis System.

Handles collection, validation, and processing of expert feedback on AI-generated answers.
Supports simple UI feedback (✅ ⚠️ ❌) and detailed categorization for Italian tax professionals.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.quality_analysis import (
    ExpertFeedback, ExpertProfile, FeedbackType, ItalianFeedbackCategory,
    QUALITY_ANALYSIS_CONFIG
)
from app.services.cache import CacheService


class FeedbackValidationError(Exception):
    """Custom exception for feedback validation errors"""
    pass


class ExpertFeedbackCollector:
    """
    Service for collecting and processing expert feedback on AI responses.
    
    Features:
    - Simple UI feedback buttons (✅ Correct, ⚠️ Incomplete, ❌ Wrong)
    - Italian categorization system for tax professionals
    - Sub-30 second response time requirement
    - Expert trust scoring and validation
    - Comprehensive feedback analytics
    """
    
    def __init__(
        self,
        db: AsyncSession,
        cache: Optional[CacheService] = None
    ):
        self.db = db
        self.cache = cache
        
        # Performance settings
        self.max_processing_time_seconds = QUALITY_ANALYSIS_CONFIG.MAX_FEEDBACK_PROCESSING_TIME_SECONDS
        self.cache_ttl = 3600  # 1 hour cache for feedback data
        
        # Italian feedback categories mapping
        self.italian_categories = {
            "normativa_obsoleta": "La normativa citata è obsoleta o non aggiornata",
            "interpretazione_errata": "L'interpretazione della normativa è errata",
            "caso_mancante": "Manca la trattazione di casi specifici",
            "calcolo_sbagliato": "I calcoli o le formule sono errati",
            "troppo_generico": "La risposta è troppo generica, serve più specificità"
        }
        
        # Statistics tracking
        self.stats = {
            'total_feedback_collected': 0,
            'avg_processing_time_ms': 0.0,
            'feedback_by_type': {'correct': 0, 'incomplete': 0, 'incorrect': 0},
            'feedback_by_category': {}
        }
    
    async def collect_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect expert feedback with comprehensive validation and processing.
        
        Args:
            feedback_data: Dictionary containing:
                - query_id: UUID of the original query
                - expert_id: UUID of the expert providing feedback
                - feedback_type: 'correct', 'incomplete', or 'incorrect'
                - category: Optional Italian category for detailed feedback
                - expert_answer: Optional corrected/improved answer
                - improvement_suggestions: Optional list of suggestions
                - time_spent_seconds: Time expert spent reviewing
                - confidence_score: Expert confidence in their feedback
                
        Returns:
            Dictionary with processing results and metadata
            
        Raises:
            FeedbackValidationError: If feedback validation fails
        """
        start_time = time.time()
        
        try:
            # Validate required fields
            self._validate_feedback_data(feedback_data)
            
            # Validate expert credentials
            expert = await self._validate_expert_credentials(feedback_data['expert_id'])
            
            # Process and store feedback
            feedback_record = await self._create_feedback_record(feedback_data, expert)
            
            # Update expert performance metrics
            await self._update_expert_metrics(expert, feedback_data)
            
            # Update system statistics
            self._update_statistics(feedback_data)
            
            # Cache feedback for quick retrieval
            if self.cache:
                await self._cache_feedback(feedback_record)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Ensure we meet the 30-second requirement
            if processing_time > 30000:
                logger.warning(f"Feedback processing exceeded 30s: {processing_time:.1f}ms")
            
            result = {
                'success': True,
                'feedback_id': str(feedback_record.id),
                'feedback_type': feedback_data['feedback_type'],
                'category': feedback_data.get('category'),
                'processing_time_ms': processing_time,
                'expert_trust_score': expert.trust_score,
                'action_taken': await self._determine_action(feedback_record)
            }
            
            # Include expert answer if provided
            if feedback_data.get('expert_answer'):
                result['expert_answer'] = feedback_data['expert_answer']
            
            logger.info(f"Feedback collected successfully: {feedback_record.id} in {processing_time:.1f}ms")
            
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Feedback collection failed after {processing_time:.1f}ms: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': processing_time
            }
    
    def _validate_feedback_data(self, feedback_data: Dict[str, Any]) -> None:
        """Validate feedback data structure and content"""
        
        # Required fields
        required_fields = ['query_id', 'expert_id', 'feedback_type', 'time_spent_seconds']
        
        for field in required_fields:
            if field not in feedback_data:
                raise FeedbackValidationError(f"Missing required field: {field}")
        
        # Validate feedback type
        valid_feedback_types = ['correct', 'incomplete', 'incorrect']
        if feedback_data['feedback_type'] not in valid_feedback_types:
            raise FeedbackValidationError(f"Invalid feedback_type: {feedback_data['feedback_type']}")
        
        # Validate category if provided
        if 'category' in feedback_data and feedback_data['category']:
            valid_categories = list(self.italian_categories.keys())
            if feedback_data['category'] not in valid_categories:
                raise FeedbackValidationError(f"Invalid category: {feedback_data['category']}")
        
        # Validate time spent
        try:
            time_spent = int(feedback_data['time_spent_seconds'])
            if time_spent <= 0:
                raise FeedbackValidationError("time_spent_seconds must be positive")
        except (ValueError, TypeError):
            raise FeedbackValidationError("time_spent_seconds must be an integer")
        
        # Validate confidence score if provided
        if 'confidence_score' in feedback_data:
            try:
                confidence = float(feedback_data['confidence_score'])
                if not 0.0 <= confidence <= 1.0:
                    raise FeedbackValidationError("confidence_score must be between 0.0 and 1.0")
            except (ValueError, TypeError):
                raise FeedbackValidationError("confidence_score must be a number")
        
        # Validate UUID fields
        try:
            UUID(feedback_data['query_id'])
            UUID(feedback_data['expert_id'])
        except (ValueError, TypeError):
            raise FeedbackValidationError("query_id and expert_id must be valid UUIDs")
    
    async def _validate_expert_credentials(self, expert_id: str) -> ExpertProfile:
        """Validate expert credentials and retrieve profile"""
        
        try:
            expert_uuid = UUID(expert_id)
            
            # Retrieve expert profile
            query = select(ExpertProfile).where(
                and_(
                    ExpertProfile.id == expert_uuid,
                    ExpertProfile.is_active == True,
                    ExpertProfile.is_verified == True
                )
            )
            
            result = await self.db.execute(query)
            expert = result.scalar_one_or_none()
            
            if not expert:
                raise FeedbackValidationError(f"Expert not found or not authorized: {expert_id}")
            
            # Check minimum trust score
            if expert.trust_score < QUALITY_ANALYSIS_CONFIG.MIN_EXPERT_TRUST_SCORE:
                raise FeedbackValidationError(
                    f"Expert trust score too low: {expert.trust_score} < {QUALITY_ANALYSIS_CONFIG.MIN_EXPERT_TRUST_SCORE}"
                )
            
            return expert
            
        except ValueError:
            raise FeedbackValidationError(f"Invalid expert_id format: {expert_id}")
    
    async def _create_feedback_record(
        self, 
        feedback_data: Dict[str, Any], 
        expert: ExpertProfile
    ) -> ExpertFeedback:
        """Create and store feedback record in database"""
        
        try:
            # Map feedback type to enum
            feedback_type = FeedbackType(feedback_data['feedback_type'])
            
            # Map category to enum if provided
            category = None
            if feedback_data.get('category'):
                category = ItalianFeedbackCategory(feedback_data['category'])
            
            # Create feedback record
            feedback_record = ExpertFeedback(
                query_id=UUID(feedback_data['query_id']),
                expert_id=expert.id,
                feedback_type=feedback_type,
                category=category,
                query_text=feedback_data.get('query_text', ''),
                original_answer=feedback_data.get('original_answer', ''),
                expert_answer=feedback_data.get('expert_answer'),
                improvement_suggestions=feedback_data.get('improvement_suggestions', []),
                regulatory_references=feedback_data.get('regulatory_references', []),
                confidence_score=feedback_data.get('confidence_score', 0.0),
                time_spent_seconds=feedback_data['time_spent_seconds'],
                complexity_rating=feedback_data.get('complexity_rating'),
                processing_time_ms=int((time.time() * 1000) % 1000000),  # Current processing time
                feedback_timestamp=datetime.utcnow()
            )
            
            # Add to database
            self.db.add(feedback_record)
            await self.db.commit()
            await self.db.refresh(feedback_record)
            
            return feedback_record
            
        except Exception as e:
            await self.db.rollback()
            raise FeedbackValidationError(f"Failed to create feedback record: {e}")
    
    async def _update_expert_metrics(self, expert: ExpertProfile, feedback_data: Dict[str, Any]) -> None:
        """Update expert performance metrics based on feedback"""
        
        try:
            # Update feedback count
            expert.feedback_count += 1
            
            # Update average response time
            current_avg = expert.average_response_time_seconds
            new_time = feedback_data['time_spent_seconds']
            expert.average_response_time_seconds = int(
                (current_avg * (expert.feedback_count - 1) + new_time) / expert.feedback_count
            )
            
            # Update trust score based on feedback quality and consistency
            confidence = feedback_data.get('confidence_score', 0.8)
            quality_boost = 0.01 * confidence  # Small incremental trust increase
            expert.trust_score = min(1.0, expert.trust_score + quality_boost)
            
            # Commit updates
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update expert metrics: {e}")
            await self.db.rollback()
    
    def _update_statistics(self, feedback_data: Dict[str, Any]) -> None:
        """Update internal statistics tracking"""
        
        self.stats['total_feedback_collected'] += 1
        
        # Update feedback type statistics
        feedback_type = feedback_data['feedback_type']
        self.stats['feedback_by_type'][feedback_type] += 1
        
        # Update category statistics
        category = feedback_data.get('category')
        if category:
            if category not in self.stats['feedback_by_category']:
                self.stats['feedback_by_category'][category] = 0
            self.stats['feedback_by_category'][category] += 1
    
    async def _cache_feedback(self, feedback_record: ExpertFeedback) -> None:
        """Cache feedback for quick retrieval"""
        
        try:
            cache_key = f"expert_feedback:{feedback_record.query_id}"
            
            feedback_data = {
                'id': str(feedback_record.id),
                'feedback_type': feedback_record.feedback_type.value,
                'category': feedback_record.category.value if feedback_record.category else None,
                'expert_answer': feedback_record.expert_answer,
                'confidence_score': feedback_record.confidence_score,
                'timestamp': feedback_record.feedback_timestamp.isoformat()
            }
            
            await self.cache.setex(cache_key, self.cache_ttl, feedback_data)
            
        except Exception as e:
            logger.warning(f"Failed to cache feedback: {e}")
    
    async def _determine_action(self, feedback_record: ExpertFeedback) -> str:
        """Determine what action should be taken based on feedback"""
        
        if feedback_record.feedback_type == FeedbackType.CORRECT:
            return "feedback_acknowledged"
        
        elif feedback_record.feedback_type == FeedbackType.INCOMPLETE:
            if feedback_record.expert_answer:
                return "answer_enhancement_queued"
            else:
                return "improvement_suggestion_logged"
        
        elif feedback_record.feedback_type == FeedbackType.INCORRECT:
            if feedback_record.expert_answer:
                return "correction_queued"
            else:
                return "critical_review_flagged"
        
        return "feedback_logged"
    
    async def get_feedback_by_query_id(self, query_id: str) -> List[Dict[str, Any]]:
        """Retrieve all feedback for a specific query"""
        
        try:
            # Check cache first
            if self.cache:
                cache_key = f"expert_feedback:{query_id}"
                cached_feedback = await self.cache.get(cache_key)
                if cached_feedback:
                    return [cached_feedback] if isinstance(cached_feedback, dict) else cached_feedback
            
            # Query database
            query = select(ExpertFeedback).where(
                ExpertFeedback.query_id == UUID(query_id)
            ).order_by(desc(ExpertFeedback.feedback_timestamp))
            
            result = await self.db.execute(query)
            feedback_records = result.scalars().all()
            
            # Convert to dict format
            feedback_list = []
            for record in feedback_records:
                feedback_data = {
                    'id': str(record.id),
                    'expert_id': str(record.expert_id),
                    'feedback_type': record.feedback_type.value,
                    'category': record.category.value if record.category else None,
                    'expert_answer': record.expert_answer,
                    'improvement_suggestions': record.improvement_suggestions,
                    'confidence_score': record.confidence_score,
                    'time_spent_seconds': record.time_spent_seconds,
                    'timestamp': record.feedback_timestamp.isoformat()
                }
                feedback_list.append(feedback_data)
            
            return feedback_list
            
        except Exception as e:
            logger.error(f"Failed to retrieve feedback for query {query_id}: {e}")
            return []
    
    async def get_expert_feedback_summary(self, expert_id: str, days: int = 30) -> Dict[str, Any]:
        """Get summary of expert's recent feedback activity"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Query for expert's recent feedback
            query = select(ExpertFeedback).where(
                and_(
                    ExpertFeedback.expert_id == UUID(expert_id),
                    ExpertFeedback.feedback_timestamp >= start_date
                )
            )
            
            result = await self.db.execute(query)
            feedback_records = result.scalars().all()
            
            # Calculate summary statistics
            total_feedback = len(feedback_records)
            
            if total_feedback == 0:
                return {
                    'expert_id': expert_id,
                    'period_days': days,
                    'total_feedback': 0,
                    'feedback_breakdown': {},
                    'average_confidence': 0.0,
                    'average_time_spent': 0
                }
            
            # Breakdown by feedback type
            feedback_breakdown = {'correct': 0, 'incomplete': 0, 'incorrect': 0}
            total_confidence = 0.0
            total_time = 0
            
            for record in feedback_records:
                feedback_breakdown[record.feedback_type.value] += 1
                total_confidence += record.confidence_score
                total_time += record.time_spent_seconds
            
            return {
                'expert_id': expert_id,
                'period_days': days,
                'total_feedback': total_feedback,
                'feedback_breakdown': feedback_breakdown,
                'average_confidence': total_confidence / total_feedback,
                'average_time_spent': total_time // total_feedback,
                'feedback_rate_per_day': total_feedback / days
            }
            
        except Exception as e:
            logger.error(f"Failed to get expert feedback summary: {e}")
            return {'error': str(e)}
    
    async def get_feedback_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive feedback analytics"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Query feedback statistics
            query = select(
                ExpertFeedback.feedback_type,
                ExpertFeedback.category,
                func.count().label('count'),
                func.avg(ExpertFeedback.confidence_score).label('avg_confidence'),
                func.avg(ExpertFeedback.time_spent_seconds).label('avg_time')
            ).where(
                ExpertFeedback.feedback_timestamp >= start_date
            ).group_by(
                ExpertFeedback.feedback_type,
                ExpertFeedback.category
            )
            
            result = await self.db.execute(query)
            analytics_data = result.all()
            
            # Process analytics data
            feedback_analytics = {
                'period_days': days,
                'total_feedback': 0,
                'feedback_by_type': {},
                'feedback_by_category': {},
                'overall_confidence': 0.0,
                'overall_avg_time': 0
            }
            
            total_count = 0
            total_confidence = 0.0
            total_time = 0.0
            
            for row in analytics_data:
                count = row.count
                total_count += count
                total_confidence += (row.avg_confidence or 0.0) * count
                total_time += (row.avg_time or 0.0) * count
                
                # Feedback by type
                feedback_type = row.feedback_type.value
                if feedback_type not in feedback_analytics['feedback_by_type']:
                    feedback_analytics['feedback_by_type'][feedback_type] = 0
                feedback_analytics['feedback_by_type'][feedback_type] += count
                
                # Feedback by category
                if row.category:
                    category = row.category.value
                    if category not in feedback_analytics['feedback_by_category']:
                        feedback_analytics['feedback_by_category'][category] = 0
                    feedback_analytics['feedback_by_category'][category] += count
            
            feedback_analytics['total_feedback'] = total_count
            if total_count > 0:
                feedback_analytics['overall_confidence'] = total_confidence / total_count
                feedback_analytics['overall_avg_time'] = int(total_time / total_count)
            
            return feedback_analytics
            
        except Exception as e:
            logger.error(f"Failed to get feedback analytics: {e}")
            return {'error': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current session statistics"""
        
        total_feedback = self.stats['total_feedback_collected']
        
        return {
            'session_statistics': self.stats,
            'italian_categories': self.italian_categories,
            'performance_metrics': {
                'avg_processing_time_ms': self.stats['avg_processing_time_ms'],
                'target_processing_time_ms': self.max_processing_time_seconds * 1000,
                'performance_target_met': self.stats['avg_processing_time_ms'] < 30000
            },
            'feedback_distribution': {
                'correct_percentage': (self.stats['feedback_by_type']['correct'] / total_feedback * 100) if total_feedback > 0 else 0,
                'incomplete_percentage': (self.stats['feedback_by_type']['incomplete'] / total_feedback * 100) if total_feedback > 0 else 0,
                'incorrect_percentage': (self.stats['feedback_by_type']['incorrect'] / total_feedback * 100) if total_feedback > 0 else 0
            }
        }
    
    async def batch_process_feedback(self, feedback_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process multiple feedback items in batch"""
        
        start_time = time.time()
        
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'processing_time_ms': 0,
            'individual_results': []
        }
        
        try:
            # Process feedback items concurrently with limited concurrency
            semaphore = asyncio.Semaphore(5)  # Limit concurrent processing
            
            async def process_single_feedback(feedback_data: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    return await self.collect_feedback(feedback_data)
            
            # Execute all feedback processing
            tasks = [process_single_feedback(feedback) for feedback in feedback_batch]
            individual_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            for i, result in enumerate(individual_results):
                results['total_processed'] += 1
                results['individual_results'].append({
                    'index': i,
                    'result': result if not isinstance(result, Exception) else {'error': str(result)}
                })
                
                if isinstance(result, Exception) or not result.get('success', False):
                    results['failed'] += 1
                else:
                    results['successful'] += 1
            
            results['processing_time_ms'] = (time.time() - start_time) * 1000
            
            logger.info(f"Batch feedback processing completed: {results['successful']}/{results['total_processed']} successful")
            
            return results
            
        except Exception as e:
            results['processing_time_ms'] = (time.time() - start_time) * 1000
            logger.error(f"Batch feedback processing failed: {e}")
            
            return {
                **results,
                'error': str(e)
            }