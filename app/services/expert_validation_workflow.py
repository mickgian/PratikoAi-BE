"""
Expert Validation Workflow for Quality Analysis System.

Manages expert validation processes including trust scoring, consensus mechanisms,
and validation workflows for complex queries and improvements.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.quality_analysis import (
    ExpertProfile, ExpertValidation, ExpertFeedback, SystemImprovement,
    ExpertCredentialType, QUALITY_ANALYSIS_CONFIG
)
from app.services.cache import CacheService


class ValidationWorkflowError(Exception):
    """Custom exception for validation workflow operations"""
    pass


class ExpertValidationWorkflow:
    """
    Expert validation workflow manager.
    
    Features:
    - Expert qualification and trust scoring
    - Multi-expert consensus mechanisms
    - Validation assignment and tracking
    - Quality assurance workflows
    - Performance analytics and monitoring
    - Italian tax professional certification
    """
    
    def __init__(
        self,
        db: AsyncSession,
        cache: Optional[CacheService] = None
    ):
        self.db = db
        self.cache = cache
        
        # Trust scoring parameters
        self.base_trust_score = 0.5
        self.max_trust_score = 1.0
        self.min_trust_score = 0.1
        
        # Validation thresholds
        self.min_expert_trust_score = QUALITY_ANALYSIS_CONFIG.MIN_EXPERT_TRUST_SCORE
        self.consensus_threshold = 0.8
        self.validation_timeout_hours = 48
        
        # Cache settings
        self.expert_cache_ttl = 3600  # 1 hour
        self.validation_cache_ttl = 1800  # 30 minutes
        
        # Italian professional credentials scoring
        self.credential_weights = {
            ExpertCredentialType.DOTTORE_COMMERCIALISTA: 0.3,
            ExpertCredentialType.REVISORE_LEGALE: 0.25,
            ExpertCredentialType.CONSULENTE_FISCALE: 0.2,
            ExpertCredentialType.CONSULENTE_LAVORO: 0.15,
            ExpertCredentialType.CAF_OPERATOR: 0.1
        }
        
        # Statistics tracking
        self.stats = {
            'validations_requested': 0,
            'validations_completed': 0,
            'consensus_reached': 0,
            'avg_validation_time_hours': 0.0,
            'expert_participation_rate': 0.0
        }
    
    async def calculate_expert_trust_score(self, expert_profile: Dict[str, Any]) -> float:
        """
        Calculate comprehensive trust score for an expert.
        
        Args:
            expert_profile: Expert profile data including credentials, experience, and history
            
        Returns:
            Trust score between 0.0 and 1.0
        """
        try:
            # Base score from credentials
            credentials_score = self._calculate_credentials_score(expert_profile.get('credentials', []))
            
            # Experience score (0-0.25)
            experience_years = expert_profile.get('experience_years', 0)
            experience_score = min(experience_years / 20.0, 0.25)  # Max at 20 years
            
            # Performance history score (0-0.3)
            accuracy_history = expert_profile.get('feedback_accuracy_history', 0.5)
            performance_score = accuracy_history * 0.3
            
            # Response time score (0-0.1)
            avg_response_time = expert_profile.get('response_time_avg_seconds', 300)
            response_score = max(0, 0.1 - (avg_response_time - 180) / 3600)  # Penalty for > 3 minutes
            
            # Specialization bonus (0-0.05)
            specializations = expert_profile.get('specializations', [])
            specialization_score = min(len(specializations) * 0.01, 0.05)
            
            # Calculate total trust score
            total_score = (
                credentials_score +
                experience_score +
                performance_score +
                response_score +
                specialization_score
            )
            
            # Ensure within bounds
            trust_score = max(self.min_trust_score, min(self.max_trust_score, total_score))
            
            logger.debug(f"Trust score calculated: {trust_score:.3f} (credentials: {credentials_score:.3f}, experience: {experience_score:.3f}, performance: {performance_score:.3f})")
            
            return trust_score
            
        except Exception as e:
            logger.error(f"Trust score calculation failed: {e}")
            return self.base_trust_score
    
    async def validate_expert_answer(self, expert_answer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an expert-provided answer for quality and accuracy.
        
        Args:
            expert_answer: Answer data with content, references, and metadata
            
        Returns:
            Validation results with quality scores and recommendations
        """
        try:
            answer_id = expert_answer.get('answer_id', str(uuid4()))
            expert_id = expert_answer.get('expert_id', '')
            query = expert_answer.get('query', '')
            answer_text = expert_answer.get('expert_answer', '')
            regulatory_references = expert_answer.get('regulatory_references', [])
            confidence_level = expert_answer.get('confidence_level', 0.0)
            
            # Get expert profile for trust scoring
            expert_profile = await self._get_expert_profile(expert_id)
            
            validation_result = {
                'answer_id': answer_id,
                'expert_id': expert_id,
                'is_valid': True,
                'quality_score': 0.0,
                'validation_details': {},
                'recommendations': []
            }
            
            # Content quality assessment
            content_quality = self._assess_content_quality(answer_text, query)
            validation_result['validation_details']['content_quality'] = content_quality
            
            # Regulatory references validation
            references_quality = self._validate_regulatory_references(regulatory_references)
            validation_result['validation_details']['references_quality'] = references_quality
            
            # Expert confidence vs actual quality
            confidence_alignment = self._assess_confidence_alignment(confidence_level, content_quality)
            validation_result['validation_details']['confidence_alignment'] = confidence_alignment
            
            # Italian language and professional terminology
            language_quality = self._assess_italian_professional_language(answer_text)
            validation_result['validation_details']['language_quality'] = language_quality
            
            # Calculate overall quality score
            overall_quality = (
                content_quality * 0.4 +
                references_quality * 0.3 +
                confidence_alignment * 0.15 +
                language_quality * 0.15
            )
            
            validation_result['quality_score'] = overall_quality
            validation_result['is_valid'] = overall_quality >= 0.7
            
            # Generate recommendations
            if overall_quality < 0.8:
                validation_result['recommendations'] = self._generate_quality_recommendations(
                    validation_result['validation_details']
                )
            
            # Add expert trust factor
            if expert_profile:
                validation_result['expert_trust_score'] = expert_profile.get('trust_score', 0.5)
                validation_result['expert_credentials'] = expert_profile.get('credentials', [])
            
            # Store validation record
            await self._store_validation_record(validation_result)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Expert answer validation failed: {e}")
            return {
                'answer_id': expert_answer.get('answer_id', ''),
                'is_valid': False,
                'error': str(e),
                'quality_score': 0.0
            }
    
    async def calculate_expert_consensus(self, expert_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate consensus among multiple expert answers.
        
        Args:
            expert_answers: List of expert answers with confidence and trust scores
            
        Returns:
            Consensus results with final answer and agreement metrics
        """
        try:
            if not expert_answers:
                return {'consensus_reached': False, 'error': 'No expert answers provided'}
            
            # Weight answers by expert trust scores
            weighted_answers = []
            for answer in expert_answers:
                trust_score = answer.get('trust_score', 0.5)
                confidence = answer.get('confidence', 0.5)
                weight = trust_score * confidence
                
                weighted_answers.append({
                    **answer,
                    'weight': weight
                })
            
            # Sort by weight
            weighted_answers.sort(key=lambda x: x['weight'], reverse=True)
            
            # Analyze semantic similarity between answers
            similarity_matrix = await self._calculate_answer_similarities(expert_answers)
            
            # Determine consensus groups
            consensus_groups = self._identify_consensus_groups(weighted_answers, similarity_matrix)
            
            # Select dominant consensus
            dominant_group = max(consensus_groups, key=lambda g: sum(a['weight'] for a in g['answers']))
            
            # Calculate consensus strength
            total_weight = sum(a['weight'] for a in weighted_answers)
            consensus_weight = sum(a['weight'] for a in dominant_group['answers'])
            consensus_strength = consensus_weight / total_weight if total_weight > 0 else 0
            
            consensus_reached = (
                consensus_strength >= self.consensus_threshold and 
                len(dominant_group['answers']) >= 2
            )
            
            # Generate final answer
            final_answer = self._synthesize_consensus_answer(dominant_group['answers']) if consensus_reached else None
            
            # Calculate agreement metrics
            agreement_score = self._calculate_agreement_score(similarity_matrix)
            
            result = {
                'consensus_reached': consensus_reached,
                'consensus_strength': consensus_strength,
                'consensus_group_size': len(dominant_group['answers']),
                'total_experts': len(expert_answers),
                'agreement_score': agreement_score,
                'final_answer': final_answer,
                'disagreement_areas': self._identify_disagreement_areas(expert_answers) if not consensus_reached else [],
                'dominant_viewpoint': dominant_group.get('representative_answer', ''),
                'alternative_viewpoints': [
                    group['representative_answer'] 
                    for group in consensus_groups 
                    if group != dominant_group
                ][:2]  # Top 2 alternative viewpoints
            }
            
            # Update statistics
            self.stats['consensus_reached'] += 1 if consensus_reached else 0
            
            return result
            
        except Exception as e:
            logger.error(f"Consensus calculation failed: {e}")
            return {'consensus_reached': False, 'error': str(e)}
    
    async def process_feedback_loop(self, feedback_loop_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process continuous feedback loop between experts and system.
        
        Args:
            feedback_loop_data: Data including query, initial answer, expert corrections, and learning
            
        Returns:
            Feedback loop processing results with improvements and satisfaction
        """
        try:
            query_id = feedback_loop_data.get('query_id', '')
            initial_answer = feedback_loop_data.get('initial_answer', '')
            expert_corrections = feedback_loop_data.get('expert_corrections', [])
            system_learning_applied = feedback_loop_data.get('system_learning_applied', False)
            
            loop_result = {
                'query_id': query_id,
                'learning_applied': system_learning_applied,
                'expert_satisfaction': 0.0,
                'improvement_quality': 0.0,
                'feedback_loop_iterations': len(expert_corrections),
                'final_answer_quality': 0.0
            }
            
            if not expert_corrections:
                return {**loop_result, 'improved_answer': initial_answer}
            
            # Process expert corrections iteratively
            improved_answer = initial_answer
            iteration_quality_scores = []
            
            for i, correction in enumerate(expert_corrections):
                expert_id = correction.get('expert_id', '')
                correction_text = correction.get('correction', '')
                corrected_answer = correction.get('corrected_answer', '')
                
                # Assess correction quality
                correction_quality = self._assess_correction_quality(
                    improved_answer, corrected_answer, correction_text
                )
                iteration_quality_scores.append(correction_quality)
                
                # Apply correction if quality is good
                if correction_quality > 0.7:
                    improved_answer = corrected_answer
                    
                    # Log learning application
                    if system_learning_applied:
                        await self._log_learning_application(query_id, correction, i + 1)
                
                # Update expert performance based on correction quality
                await self._update_expert_performance(expert_id, correction_quality)
            
            # Calculate final metrics
            loop_result['improvement_quality'] = sum(iteration_quality_scores) / len(iteration_quality_scores)
            loop_result['final_answer_quality'] = self._assess_content_quality(improved_answer, query_id)
            loop_result['improved_answer'] = improved_answer
            
            # Calculate expert satisfaction (simulated based on quality improvements)
            initial_quality = self._assess_content_quality(initial_answer, query_id)
            final_quality = loop_result['final_answer_quality']
            quality_improvement = final_quality - initial_quality
            
            # Satisfaction based on quality improvement and expert engagement
            loop_result['expert_satisfaction'] = min(0.5 + quality_improvement + (len(expert_corrections) * 0.1), 1.0)
            
            # Store feedback loop record
            await self._store_feedback_loop_record(loop_result)
            
            return loop_result
            
        except Exception as e:
            logger.error(f"Feedback loop processing failed: {e}")
            return {'error': str(e), 'learning_applied': False, 'expert_satisfaction': 0.0}
    
    def _calculate_credentials_score(self, credentials: List[str]) -> float:
        """Calculate score based on professional credentials"""
        
        total_score = 0.0
        
        for credential in credentials:
            try:
                credential_type = ExpertCredentialType(credential.lower().replace(' ', '_'))
                weight = self.credential_weights.get(credential_type, 0.05)
                total_score += weight
            except (ValueError, AttributeError):
                # Unknown credential, small bonus
                total_score += 0.02
        
        return min(total_score, 0.35)  # Max 35% from credentials
    
    def _assess_content_quality(self, content: str, query: str) -> float:
        """Assess the quality of content based on various criteria"""
        
        if not content or len(content.strip()) < 50:
            return 0.1
        
        quality_score = 0.0
        
        # Length appropriateness (0-0.2)
        content_length = len(content)
        if 200 <= content_length <= 800:
            quality_score += 0.2
        elif 100 <= content_length < 200 or 800 < content_length <= 1200:
            quality_score += 0.15
        else:
            quality_score += 0.1
        
        # Professional terminology (0-0.3)
        professional_terms = [
            'ai sensi', 'secondo', 'normativa', 'decreto', 'legge',
            'articolo', 'comma', 'dichiarazione', 'versamento'
        ]
        
        content_lower = content.lower()
        professional_matches = sum(1 for term in professional_terms if term in content_lower)
        quality_score += min(professional_matches * 0.05, 0.3)
        
        # Structure and clarity (0-0.25)
        structure_elements = ['**', '#', '1.', '2.', '-', '•']
        has_structure = any(elem in content for elem in structure_elements)
        quality_score += 0.15 if has_structure else 0.05
        
        # Query relevance (0-0.25)
        if query:
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            relevance = len(query_words & content_words) / max(len(query_words), 1)
            quality_score += relevance * 0.25
        else:
            quality_score += 0.15  # Default if no query provided
        
        return min(quality_score, 1.0)
    
    def _validate_regulatory_references(self, references: List[str]) -> float:
        """Validate regulatory references for accuracy and currency"""
        
        if not references:
            return 0.3  # Some penalty for missing references
        
        quality_score = 0.0
        valid_references = 0
        
        for ref in references:
            ref_lower = ref.lower()
            
            # Check for valid Italian regulatory patterns
            if any(pattern in ref_lower for pattern in ['d.l.', 'decreto legge', 'legge', 'l.']):
                valid_references += 1
                
                # Check for recent dates (2020+)
                import re
                year_matches = re.findall(r'\b(20\d{2})\b', ref)
                if year_matches and any(int(year) >= 2020 for year in year_matches):
                    quality_score += 0.2
                else:
                    quality_score += 0.1
            
            elif any(pattern in ref_lower for pattern in ['circolare', 'risoluzione', 'provvedimento']):
                valid_references += 1
                quality_score += 0.15
        
        # Bonus for multiple valid references
        if valid_references > 1:
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def _assess_confidence_alignment(self, stated_confidence: float, actual_quality: float) -> float:
        """Assess alignment between stated confidence and actual quality"""
        
        confidence_diff = abs(stated_confidence - actual_quality)
        
        # Perfect alignment = 1.0, large difference = 0.0
        alignment_score = max(0, 1.0 - (confidence_diff * 2))
        
        return alignment_score
    
    def _assess_italian_professional_language(self, text: str) -> float:
        """Assess Italian professional language usage"""
        
        text_lower = text.lower()
        
        # Professional Italian phrases
        professional_phrases = [
            'ai sensi dell\'art', 'in base alla normativa', 'secondo quanto previsto',
            'come stabilito dal', 'ai fini dell\'applicazione', 'in conformità a',
            'salvo quanto previsto', 'fatte salve le disposizioni'
        ]
        
        phrase_matches = sum(1 for phrase in professional_phrases if phrase in text_lower)
        phrase_score = min(phrase_matches * 0.2, 0.6)
        
        # Grammar and style indicators
        good_indicators = [
            'pertanto', 'tuttavia', 'inoltre', 'infatti', 'ovvero',
            'ossia', 'nonché', 'qualora', 'laddove'
        ]
        
        indicator_matches = sum(1 for indicator in good_indicators if indicator in text_lower)
        indicator_score = min(indicator_matches * 0.1, 0.4)
        
        return min(phrase_score + indicator_score, 1.0)
    
    def _generate_quality_recommendations(self, validation_details: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving answer quality"""
        
        recommendations = []
        
        content_quality = validation_details.get('content_quality', 0.0)
        if content_quality < 0.7:
            recommendations.append("Migliorare la struttura e la completezza della risposta")
        
        references_quality = validation_details.get('references_quality', 0.0)
        if references_quality < 0.6:
            recommendations.append("Aggiungere riferimenti normativi aggiornati")
        
        language_quality = validation_details.get('language_quality', 0.0)
        if language_quality < 0.7:
            recommendations.append("Utilizzare terminologia fiscale più professionale")
        
        confidence_alignment = validation_details.get('confidence_alignment', 0.0)
        if confidence_alignment < 0.6:
            recommendations.append("Calibrare meglio il livello di fiducia nella risposta")
        
        return recommendations
    
    async def _calculate_answer_similarities(self, answers: List[Dict[str, Any]]) -> List[List[float]]:
        """Calculate semantic similarity matrix between answers"""
        
        # Simple similarity based on word overlap (can be enhanced with embeddings)
        similarity_matrix = []
        
        for i, answer1 in enumerate(answers):
            row = []
            text1 = answer1.get('answer', '').lower().split()
            
            for j, answer2 in enumerate(answers):
                if i == j:
                    row.append(1.0)
                else:
                    text2 = answer2.get('answer', '').lower().split()
                    
                    if not text1 or not text2:
                        row.append(0.0)
                    else:
                        # Jaccard similarity
                        intersection = len(set(text1) & set(text2))
                        union = len(set(text1) | set(text2))
                        similarity = intersection / union if union > 0 else 0.0
                        row.append(similarity)
            
            similarity_matrix.append(row)
        
        return similarity_matrix
    
    def _identify_consensus_groups(self, answers: List[Dict[str, Any]], similarity_matrix: List[List[float]]) -> List[Dict[str, Any]]:
        """Identify groups of similar answers for consensus analysis"""
        
        groups = []
        used_indices = set()
        
        for i, answer in enumerate(answers):
            if i in used_indices:
                continue
            
            # Start new group
            group_answers = [answer]
            group_indices = {i}
            
            # Find similar answers
            for j, other_answer in enumerate(answers):
                if j != i and j not in used_indices:
                    if similarity_matrix[i][j] > 0.6:  # Similarity threshold
                        group_answers.append(other_answer)
                        group_indices.add(j)
            
            used_indices.update(group_indices)
            
            # Create group
            groups.append({
                'answers': group_answers,
                'size': len(group_answers),
                'representative_answer': group_answers[0].get('answer', ''),  # Highest weighted answer
                'avg_confidence': sum(a.get('confidence', 0) for a in group_answers) / len(group_answers),
                'total_weight': sum(a.get('weight', 0) for a in group_answers)
            })
        
        return groups
    
    def _synthesize_consensus_answer(self, answers: List[Dict[str, Any]]) -> str:
        """Synthesize final answer from consensus group"""
        
        if not answers:
            return ""
        
        # For now, return the highest weighted answer
        # In a more sophisticated implementation, this could merge content
        best_answer = max(answers, key=lambda a: a.get('weight', 0))
        return best_answer.get('answer', '')
    
    def _calculate_agreement_score(self, similarity_matrix: List[List[float]]) -> float:
        """Calculate overall agreement score from similarity matrix"""
        
        if not similarity_matrix or len(similarity_matrix) < 2:
            return 1.0
        
        total_similarity = 0
        comparisons = 0
        
        for i in range(len(similarity_matrix)):
            for j in range(i + 1, len(similarity_matrix[i])):
                total_similarity += similarity_matrix[i][j]
                comparisons += 1
        
        return total_similarity / comparisons if comparisons > 0 else 0.0
    
    def _identify_disagreement_areas(self, answers: List[Dict[str, Any]]) -> List[str]:
        """Identify areas of disagreement between expert answers"""
        
        # Simple implementation based on content analysis
        disagreements = []
        
        # Look for conflicting statements
        answer_texts = [a.get('answer', '').lower() for a in answers]
        
        # Check for yes/no conflicts
        yes_indicators = ['sì', 'si', 'corretto', 'applicabile', 'possibile']
        no_indicators = ['no', 'non', 'impossibile', 'non applicabile', 'errato']
        
        has_positive = any(any(indicator in text for indicator in yes_indicators) for text in answer_texts)
        has_negative = any(any(indicator in text for indicator in no_indicators) for text in answer_texts)
        
        if has_positive and has_negative:
            disagreements.append("Opinioni contrastanti sulla applicabilità")
        
        # Check for numerical conflicts (simplified)
        import re
        all_numbers = []
        for text in answer_texts:
            numbers = re.findall(r'\d+[.,]?\d*%?', text)
            all_numbers.extend(numbers)
        
        if len(set(all_numbers)) > 1 and len(all_numbers) > 1:
            disagreements.append("Valori numerici discordanti")
        
        return disagreements[:3]  # Limit to top 3 disagreements
    
    def _assess_correction_quality(self, original: str, corrected: str, correction_note: str) -> float:
        """Assess the quality of an expert correction"""
        
        # Simple quality assessment
        quality_score = 0.5  # Base score
        
        # Length improvement
        if len(corrected) > len(original) * 1.1:
            quality_score += 0.2
        
        # Has correction explanation
        if correction_note and len(correction_note) > 20:
            quality_score += 0.2
        
        # Professional terminology added
        professional_terms = ['decreto', 'legge', 'normativa', 'articolo', 'comma']
        original_terms = sum(1 for term in professional_terms if term in original.lower())
        corrected_terms = sum(1 for term in professional_terms if term in corrected.lower())
        
        if corrected_terms > original_terms:
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    async def _get_expert_profile(self, expert_id: str) -> Optional[Dict[str, Any]]:
        """Get expert profile with caching"""
        
        try:
            # Check cache first
            if self.cache:
                cache_key = f"expert_profile:{expert_id}"
                cached_profile = await self.cache.get(cache_key)
                if cached_profile:
                    return cached_profile
            
            # Query database
            query = select(ExpertProfile).where(ExpertProfile.id == UUID(expert_id))
            result = await self.db.execute(query)
            expert = result.scalar_one_or_none()
            
            if expert:
                profile = {
                    'id': str(expert.id),
                    'credentials': expert.credentials,
                    'experience_years': expert.experience_years,
                    'specializations': expert.specializations,
                    'trust_score': expert.trust_score,
                    'feedback_accuracy_history': expert.feedback_accuracy_rate,
                    'response_time_avg_seconds': expert.average_response_time_seconds
                }
                
                # Cache profile
                if self.cache:
                    cache_key = f"expert_profile:{expert_id}"
                    await self.cache.setex(cache_key, self.expert_cache_ttl, profile)
                
                return profile
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get expert profile: {e}")
            return None
    
    async def _store_validation_record(self, validation_result: Dict[str, Any]) -> None:
        """Store validation record in database"""
        
        try:
            validation = ExpertValidation(
                query_id=UUID(validation_result.get('query_id', str(uuid4()))),
                validation_type='single_expert',
                complexity_level=3,  # Default medium complexity
                assigned_experts=[validation_result.get('expert_id', '')],
                completed_validations=1,
                required_validations=1,
                consensus_reached=validation_result.get('is_valid', False),
                consensus_confidence=validation_result.get('quality_score', 0.0),
                final_confidence_score=validation_result.get('quality_score', 0.0),
                expert_agreement_score=1.0,  # Single expert = 100% agreement
                target_completion=datetime.utcnow() + timedelta(hours=24),
                completed_at=datetime.utcnow(),
                status='completed'
            )
            
            self.db.add(validation)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to store validation record: {e}")
            await self.db.rollback()
    
    async def _store_feedback_loop_record(self, loop_result: Dict[str, Any]) -> None:
        """Store feedback loop record for analysis"""
        
        # This would store the feedback loop results for analysis
        # Implementation depends on specific requirements
        logger.info(f"Feedback loop completed: {loop_result.get('query_id', 'unknown')} - satisfaction: {loop_result.get('expert_satisfaction', 0):.2f}")
    
    async def _log_learning_application(self, query_id: str, correction: Dict[str, Any], iteration: int) -> None:
        """Log learning application for audit"""
        
        logger.info(f"Learning applied: {query_id} - iteration {iteration} by expert {correction.get('expert_id', 'unknown')}")
    
    async def _update_expert_performance(self, expert_id: str, correction_quality: float) -> None:
        """Update expert performance metrics based on correction quality"""
        
        try:
            query = select(ExpertProfile).where(ExpertProfile.id == UUID(expert_id))
            result = await self.db.execute(query)
            expert = result.scalar_one_or_none()
            
            if expert:
                # Update feedback accuracy rate (running average)
                current_rate = expert.feedback_accuracy_rate
                feedback_count = expert.feedback_count
                
                new_rate = ((current_rate * feedback_count) + correction_quality) / (feedback_count + 1)
                
                expert.feedback_accuracy_rate = new_rate
                expert.feedback_count += 1
                
                # Recalculate trust score
                profile_data = {
                    'credentials': expert.credentials,
                    'experience_years': expert.experience_years,
                    'feedback_accuracy_history': new_rate,
                    'response_time_avg_seconds': expert.average_response_time_seconds,
                    'specializations': expert.specializations
                }
                
                expert.trust_score = await self.calculate_expert_trust_score(profile_data)
                
                await self.db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update expert performance: {e}")
            await self.db.rollback()
    
    async def get_validation_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get validation workflow analytics"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Query validation records
            validations_query = select(ExpertValidation).where(
                ExpertValidation.requested_at >= start_date
            ).order_by(desc(ExpertValidation.requested_at))
            
            result = await self.db.execute(validations_query)
            validations = result.scalars().all()
            
            # Calculate analytics
            total_validations = len(validations)
            completed_validations = len([v for v in validations if v.status == 'completed'])
            consensus_reached = len([v for v in validations if v.consensus_reached])
            
            # Average completion time
            completed_times = []
            for validation in validations:
                if validation.completed_at and validation.requested_at:
                    completion_time = (validation.completed_at - validation.requested_at).total_seconds() / 3600
                    completed_times.append(completion_time)
            
            avg_completion_time = sum(completed_times) / len(completed_times) if completed_times else 0
            
            return {
                'period_days': days,
                'total_validations': total_validations,
                'completed_validations': completed_validations,
                'completion_rate': completed_validations / total_validations if total_validations > 0 else 0,
                'consensus_reached': consensus_reached,
                'consensus_rate': consensus_reached / completed_validations if completed_validations > 0 else 0,
                'avg_completion_time_hours': avg_completion_time,
                'session_stats': self.stats,
                'expert_participation_metrics': {
                    'total_experts_active': len(set(v.assigned_experts[0] if v.assigned_experts else '' for v in validations)),
                    'avg_experts_per_validation': sum(len(v.assigned_experts) for v in validations) / max(total_validations, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get validation analytics: {e}")
            return {'error': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current workflow statistics"""
        
        return {
            'session_stats': self.stats,
            'configuration': {
                'min_expert_trust_score': self.min_expert_trust_score,
                'consensus_threshold': self.consensus_threshold,
                'validation_timeout_hours': self.validation_timeout_hours
            },
            'credential_weights': {
                cred_type.value: weight 
                for cred_type, weight in self.credential_weights.items()
            },
            'performance_metrics': {
                'validation_success_rate': self.stats['validations_completed'] / max(self.stats['validations_requested'], 1),
                'consensus_success_rate': self.stats['consensus_reached'] / max(self.stats['validations_completed'], 1),
                'avg_validation_time': self.stats['avg_validation_time_hours']
            }
        }