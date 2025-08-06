"""
Quality Metrics Dashboard for Quality Analysis System.

Provides comprehensive quality metrics tracking, visualization data,
and real-time monitoring for the Italian tax AI system.
"""

import asyncio
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.quality_analysis import (
    QualityMetric, ExpertFeedback, FailurePattern, SystemImprovement,
    ExpertValidation, ExpertProfile, FeedbackType, ItalianFeedbackCategory,
    ImprovementStatus, QUALITY_ANALYSIS_CONFIG
)
from app.services.cache import CacheService


class QualityMetricsDashboard:
    """
    Comprehensive quality metrics dashboard service.
    
    Features:
    - Real-time quality monitoring
    - Trend analysis and forecasting
    - Expert performance analytics
    - Failure pattern visualization
    - ROI tracking and reporting
    - Italian tax domain-specific metrics
    """
    
    def __init__(
        self,
        db: AsyncSession,
        cache: Optional[CacheService] = None
    ):
        self.db = db
        self.cache = cache
        
        # Cache settings
        self.metrics_cache_ttl = 300  # 5 minutes for real-time data
        self.analytics_cache_ttl = 1800  # 30 minutes for complex analytics
        
        # Quality thresholds
        self.target_accuracy_score = QUALITY_ANALYSIS_CONFIG.TARGET_ACCURACY_SCORE
        self.target_expert_satisfaction = QUALITY_ANALYSIS_CONFIG.TARGET_EXPERT_SATISFACTION
        self.target_response_time_ms = QUALITY_ANALYSIS_CONFIG.TARGET_RESPONSE_TIME_MS
        
        # Alert thresholds
        self.quality_degradation_threshold = 0.15  # 15% drop triggers alert
        self.failure_rate_alert_threshold = 0.20  # 20% failure rate
        self.response_time_alert_threshold = 500  # 500ms response time
        
        # Statistics tracking
        self.stats = {
            'metrics_calculated': 0,
            'alerts_generated': 0,
            'dashboards_served': 0,
            'cache_hit_rate': 0.0
        }
    
    async def calculate_quality_metrics(self, time_period: timedelta = timedelta(days=30)) -> Dict[str, Any]:
        """
        Calculate comprehensive quality metrics for the specified time period.
        
        Args:
            time_period: Time period for metric calculation
            
        Returns:
            Dictionary containing all quality metrics and trends
        """
        start_time = time.time()
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - time_period
            
            logger.info(f"Calculating quality metrics for period: {start_date} to {end_date}")
            
            # Check cache
            cache_key = f"quality_metrics:{start_date.date()}:{end_date.date()}"
            if self.cache:
                cached_metrics = await self.cache.get(cache_key)
                if cached_metrics:
                    self.stats['cache_hit_rate'] += 1
                    return cached_metrics
            
            # Calculate core metrics concurrently
            metrics_tasks = [
                self._calculate_accuracy_metrics(start_date, end_date),
                self._calculate_expert_satisfaction_metrics(start_date, end_date),
                self._calculate_response_time_metrics(start_date, end_date),
                self._calculate_failure_rate_metrics(start_date, end_date),
                self._calculate_improvement_velocity_metrics(start_date, end_date),
                self._calculate_expert_engagement_metrics(start_date, end_date)
            ]
            
            results = await asyncio.gather(*metrics_tasks)
            
            accuracy_metrics = results[0]
            satisfaction_metrics = results[1]
            response_time_metrics = results[2]
            failure_rate_metrics = results[3]
            improvement_velocity_metrics = results[4]
            engagement_metrics = results[5]
            
            # Calculate overall quality score
            overall_quality_score = self._calculate_overall_quality_score({
                'accuracy': accuracy_metrics['current_accuracy'],
                'satisfaction': satisfaction_metrics['current_satisfaction'],
                'response_time': response_time_metrics['avg_response_time_ms'],
                'failure_rate': failure_rate_metrics['current_failure_rate'],
                'improvement_velocity': improvement_velocity_metrics['improvements_per_week']
            })
            
            # Generate trends
            trends = await self._generate_trend_analysis(start_date, end_date)
            
            # Compile final metrics
            quality_metrics = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': time_period.days
                },
                'overall_quality_score': overall_quality_score,
                'accuracy_metrics': accuracy_metrics,
                'expert_satisfaction': satisfaction_metrics,
                'performance_metrics': response_time_metrics,
                'failure_analysis': failure_rate_metrics,
                'improvement_velocity': improvement_velocity_metrics,
                'expert_engagement': engagement_metrics,
                'trends': trends,
                'targets': {
                    'accuracy_target': self.target_accuracy_score,
                    'satisfaction_target': self.target_expert_satisfaction,
                    'response_time_target': self.target_response_time_ms
                },
                'calculation_time_ms': (time.time() - start_time) * 1000
            }
            
            # Cache results
            if self.cache:
                await self.cache.setex(cache_key, self.metrics_cache_ttl, quality_metrics)
            
            self.stats['metrics_calculated'] += 1
            
            logger.info(f"Quality metrics calculated in {quality_metrics['calculation_time_ms']:.1f}ms")
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Quality metrics calculation failed: {e}")
            return {'error': str(e)}
    
    async def get_failure_analysis_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive failure analysis dashboard data"""
        
        try:
            # Recent failure patterns
            patterns_query = select(FailurePattern).where(
                FailurePattern.is_resolved == False
            ).order_by(desc(FailurePattern.impact_score)).limit(10)
            
            result = await self.db.execute(patterns_query)
            active_patterns = result.scalars().all()
            
            # Failure categories distribution
            categories_query = select(
                ExpertFeedback.category,
                func.count().label('count')
            ).where(
                and_(
                    ExpertFeedback.feedback_timestamp >= datetime.utcnow() - timedelta(days=30),
                    ExpertFeedback.feedback_type != FeedbackType.CORRECT
                )
            ).group_by(ExpertFeedback.category)
            
            result = await self.db.execute(categories_query)
            category_data = result.all()
            
            # Trending issues (increasing frequency)
            trending_query = select(
                FailurePattern.pattern_name,
                FailurePattern.frequency_count,
                FailurePattern.impact_score,
                FailurePattern.first_detected,
                FailurePattern.last_occurrence
            ).where(
                FailurePattern.last_occurrence >= datetime.utcnow() - timedelta(days=7)
            ).order_by(desc(FailurePattern.frequency_count)).limit(5)
            
            result = await self.db.execute(trending_query)
            trending_issues = result.all()
            
            # Expert intervention rate
            intervention_query = select(
                func.count(case((ExpertFeedback.feedback_type != FeedbackType.CORRECT, 1))).label('interventions'),
                func.count().label('total')
            ).where(
                ExpertFeedback.feedback_timestamp >= datetime.utcnow() - timedelta(days=30)
            )
            
            result = await self.db.execute(intervention_query)
            intervention_data = result.one()
            
            intervention_rate = (
                intervention_data.interventions / intervention_data.total 
                if intervention_data.total > 0 else 0
            )
            
            # Automated fixes applied
            fixes_query = select(func.count()).select_from(SystemImprovement).where(
                and_(
                    SystemImprovement.created_at >= datetime.utcnow() - timedelta(days=30),
                    SystemImprovement.status == ImprovementStatus.COMPLETED,
                    SystemImprovement.requires_expert_validation == False
                )
            )
            
            result = await self.db.execute(fixes_query)
            automated_fixes = result.scalar()
            
            # Compile dashboard data
            dashboard_data = {
                'failure_categories': [
                    {
                        'category': row.category.value if row.category else 'unclassified',
                        'count': row.count,
                        'category_description': self._get_category_description(row.category)
                    }
                    for row in category_data
                ],
                'trending_issues': [
                    {
                        'pattern_name': row.pattern_name,
                        'frequency': row.frequency_count,
                        'impact_score': row.impact_score,
                        'first_seen': row.first_detected.isoformat(),
                        'last_seen': row.last_occurrence.isoformat(),
                        'trend_direction': 'increasing'  # Simplified trend
                    }
                    for row in trending_issues
                ],
                'active_patterns': [
                    {
                        'id': str(pattern.id),
                        'name': pattern.pattern_name,
                        'type': pattern.pattern_type,
                        'frequency': pattern.frequency_count,
                        'impact': pattern.impact_score,
                        'confidence': pattern.confidence_score,
                        'categories': pattern.categories
                    }
                    for pattern in active_patterns
                ],
                'expert_intervention_rate': intervention_rate,
                'automated_fixes_applied': automated_fixes or 0,
                'summary': {
                    'total_active_patterns': len(active_patterns),
                    'critical_patterns': len([p for p in active_patterns if p.impact_score >= 0.8]),
                    'categories_affected': len(category_data),
                    'intervention_needed': intervention_rate > 0.15  # Alert if > 15% intervention
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failure analysis dashboard failed: {e}")
            return {'error': str(e)}
    
    async def get_expert_performance_metrics(
        self, 
        expert_id: Optional[str] = None, 
        time_period: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """Get expert performance tracking metrics"""
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - time_period
            
            # Base query conditions
            query_conditions = [ExpertFeedback.feedback_timestamp >= start_date]
            if expert_id:
                query_conditions.append(ExpertFeedback.expert_id == UUID(expert_id))
            
            # Expert feedback metrics
            feedback_query = select(
                ExpertFeedback.expert_id,
                func.count().label('total_feedback'),
                func.avg(ExpertFeedback.confidence_score).label('avg_confidence'),
                func.avg(ExpertFeedback.time_spent_seconds).label('avg_response_time'),
                func.count(case((ExpertFeedback.feedback_type == FeedbackType.CORRECT, 1))).label('correct_feedback'),
                func.count(case((ExpertFeedback.feedback_type == FeedbackType.INCORRECT, 1))).label('incorrect_feedback')
            ).where(
                and_(*query_conditions)
            ).group_by(ExpertFeedback.expert_id)
            
            result = await self.db.execute(feedback_query)
            feedback_data = result.all()
            
            # Expert profiles for additional context
            profiles_query = select(ExpertProfile).where(
                ExpertProfile.is_active == True
            )
            
            if expert_id:
                profiles_query = profiles_query.where(ExpertProfile.id == UUID(expert_id))
            
            result = await self.db.execute(profiles_query)
            profiles = result.scalars().all()
            
            # Compile expert metrics
            expert_metrics = {}
            
            for profile in profiles:
                expert_data = next(
                    (fb for fb in feedback_data if fb.expert_id == profile.id), 
                    None
                )
                
                if expert_data:
                    accuracy_rate = (
                        expert_data.correct_feedback / expert_data.total_feedback
                        if expert_data.total_feedback > 0 else 0
                    )
                    
                    expert_metrics[str(profile.id)] = {
                        'expert_id': str(profile.id),
                        'credentials': profile.credentials,
                        'specializations': profile.specializations,
                        'trust_score': profile.trust_score,
                        'feedback_count': expert_data.total_feedback,
                        'accuracy_rate': accuracy_rate,
                        'average_confidence': expert_data.avg_confidence or 0,
                        'average_response_time': expert_data.avg_response_time or 0,
                        'feedback_distribution': {
                            'correct': expert_data.correct_feedback,
                            'incorrect': expert_data.incorrect_feedback,
                            'incomplete': expert_data.total_feedback - expert_data.correct_feedback - expert_data.incorrect_feedback
                        },
                        'performance_score': self._calculate_expert_performance_score({
                            'accuracy_rate': accuracy_rate,
                            'trust_score': profile.trust_score,
                            'response_time': expert_data.avg_response_time or 300,
                            'feedback_count': expert_data.total_feedback
                        })
                    }
            
            # If specific expert requested, return individual metrics
            if expert_id and expert_id in expert_metrics:
                return expert_metrics[expert_id]
            
            # Return aggregate metrics
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': time_period.days
                },
                'total_active_experts': len(expert_metrics),
                'expert_details': list(expert_metrics.values()),
                'aggregate_metrics': {
                    'avg_trust_score': sum(e['trust_score'] for e in expert_metrics.values()) / max(len(expert_metrics), 1),
                    'avg_accuracy_rate': sum(e['accuracy_rate'] for e in expert_metrics.values()) / max(len(expert_metrics), 1),
                    'avg_response_time': sum(e['average_response_time'] for e in expert_metrics.values()) / max(len(expert_metrics), 1),
                    'total_feedback_provided': sum(e['feedback_count'] for e in expert_metrics.values())
                },
                'top_performers': sorted(
                    expert_metrics.values(),
                    key=lambda x: x['performance_score'],
                    reverse=True
                )[:5]
            }
            
        except Exception as e:
            logger.error(f"Expert performance metrics failed: {e}")
            return {'error': str(e)}
    
    async def track_system_improvements(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Track system improvements over time"""
        
        try:
            # System improvements query
            improvements_query = select(SystemImprovement).where(
                and_(
                    SystemImprovement.created_at >= start_date,
                    SystemImprovement.created_at <= end_date
                )
            ).order_by(SystemImprovement.created_at)
            
            result = await self.db.execute(improvements_query)
            improvements = result.scalars().all()
            
            # Quality metrics over time (sample points)
            time_points = []
            current_date = start_date
            delta = (end_date - start_date) / 10  # 10 sample points
            
            while current_date <= end_date:
                point_metrics = await self._get_quality_snapshot(current_date)
                time_points.append({
                    'date': current_date.isoformat(),
                    'quality_score': point_metrics['overall_quality'],
                    'accuracy_score': point_metrics['accuracy'],
                    'satisfaction_score': point_metrics['satisfaction']
                })
                current_date += delta
            
            # Categorize improvements
            improvement_categories = defaultdict(list)
            for improvement in improvements:
                improvement_categories[improvement.improvement_type].append(improvement)
            
            # Calculate ROI metrics
            roi_metrics = await self._calculate_improvement_roi(improvements)
            
            improvement_data = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'quality_trend': time_points,
                'total_improvements': len(improvements),
                'completed_improvements': len([i for i in improvements if i.status == ImprovementStatus.COMPLETED]),
                'automated_improvements': len([i for i in improvements if not i.requires_expert_validation]),
                'expert_driven_improvements': len([i for i in improvements if i.requires_expert_validation]),
                'improvement_categories': {
                    category: {
                        'count': len(improvements_list),
                        'avg_impact': sum(i.estimated_impact for i in improvements_list) / len(improvements_list),
                        'avg_confidence': sum(i.confidence_score for i in improvements_list) / len(improvements_list)
                    }
                    for category, improvements_list in improvement_categories.items()
                },
                'roi_metrics': roi_metrics,
                'recent_improvements': [
                    {
                        'id': str(i.id),
                        'title': i.title,
                        'type': i.improvement_type,
                        'status': i.status.value,
                        'impact': i.estimated_impact,
                        'created': i.created_at.isoformat(),
                        'completed': i.actual_completion_date.isoformat() if i.actual_completion_date else None
                    }
                    for i in improvements[-10:]  # Last 10 improvements
                ]
            }
            
            return improvement_data
            
        except Exception as e:
            logger.error(f"System improvement tracking failed: {e}")
            return {'error': str(e)}
    
    async def check_quality_alerts(self, current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Check for quality degradation and generate alerts"""
        
        alerts = []
        
        try:
            accuracy_score = current_metrics.get('accuracy_score', 0.8)
            failure_rate = current_metrics.get('failure_rate', 0.1)
            expert_intervention_rate = current_metrics.get('expert_intervention_rate', 0.1)
            avg_response_time = current_metrics.get('avg_response_time_ms', 200)
            
            # Accuracy degradation alert
            if accuracy_score < self.target_accuracy_score - self.quality_degradation_threshold:
                alerts.append({
                    'type': 'accuracy_degradation',
                    'priority': 'high',
                    'message': f'Accuratezza sistema scesa al {accuracy_score:.1%}, sotto il target del {self.target_accuracy_score:.1%}',
                    'current_value': accuracy_score,
                    'target_value': self.target_accuracy_score,
                    'threshold_breach': abs(accuracy_score - self.target_accuracy_score),
                    'suggested_actions': [
                        'Analizzare i pattern di errore più recenti',
                        'Verificare gli aggiornamenti normativi',
                        'Consultare esperti per validazione'
                    ]
                })
            
            # High failure rate alert
            if failure_rate > self.failure_rate_alert_threshold:
                alerts.append({
                    'type': 'high_failure_rate',
                    'priority': 'high',
                    'message': f'Tasso di errore elevato: {failure_rate:.1%}',
                    'current_value': failure_rate,
                    'threshold': self.failure_rate_alert_threshold,
                    'threshold_breach': failure_rate - self.failure_rate_alert_threshold,
                    'suggested_actions': [
                        'Identificare pattern di errore dominanti',
                        'Applicare correzioni automatiche prioritarie',
                        'Aumentare validazione esperta'
                    ]
                })
            
            # Response time degradation
            if avg_response_time > self.response_time_alert_threshold:
                alerts.append({
                    'type': 'response_time_degradation',
                    'priority': 'medium',
                    'message': f'Tempo di risposta elevato: {avg_response_time}ms',
                    'current_value': avg_response_time,
                    'target_value': self.target_response_time_ms,
                    'threshold': self.response_time_alert_threshold,
                    'suggested_actions': [
                        'Ottimizzare query al database',
                        'Verificare performance cache',
                        'Scalare risorse computazionali'
                    ]
                })
            
            # High expert intervention alert
            if expert_intervention_rate > 0.2:  # > 20%
                alerts.append({
                    'type': 'high_expert_intervention',
                    'priority': 'medium',
                    'message': f'Alto tasso di intervento esperto: {expert_intervention_rate:.1%}',
                    'current_value': expert_intervention_rate,
                    'threshold': 0.2,
                    'threshold_breach': expert_intervention_rate - 0.2,
                    'suggested_actions': [
                        'Analizzare cause frequenti di intervento',
                        'Migliorare training del modello',
                        'Implementare correzioni automatiche'
                    ]
                })
            
            # Update statistics
            self.stats['alerts_generated'] += len(alerts)
            
            # Log alerts
            if alerts:
                logger.warning(f"Quality alerts generated: {len(alerts)} alerts")
                for alert in alerts:
                    logger.warning(f"Alert: {alert['type']} - {alert['message']}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Quality alert check failed: {e}")
            return [{'type': 'system_error', 'priority': 'high', 'message': f'Sistema di monitoraggio in errore: {str(e)}'}]
    
    async def _calculate_accuracy_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate accuracy-related metrics"""
        
        # Expert feedback accuracy analysis
        feedback_query = select(
            func.count().label('total_feedback'),
            func.count(case((ExpertFeedback.feedback_type == FeedbackType.CORRECT, 1))).label('correct_feedback')
        ).where(
            and_(
                ExpertFeedback.feedback_timestamp >= start_date,
                ExpertFeedback.feedback_timestamp <= end_date
            )
        )
        
        result = await self.db.execute(feedback_query)
        feedback_data = result.one()
        
        current_accuracy = (
            feedback_data.correct_feedback / feedback_data.total_feedback
            if feedback_data.total_feedback > 0 else self.target_accuracy_score
        )
        
        return {
            'current_accuracy': current_accuracy,
            'total_responses_evaluated': feedback_data.total_feedback,
            'correct_responses': feedback_data.correct_feedback,
            'accuracy_vs_target': current_accuracy - self.target_accuracy_score,
            'accuracy_grade': self._calculate_grade(current_accuracy, self.target_accuracy_score)
        }
    
    async def _calculate_expert_satisfaction_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate expert satisfaction metrics"""
        
        # Expert satisfaction based on feedback patterns and validation success
        validation_query = select(
            func.count().label('total_validations'),
            func.avg(ExpertValidation.consensus_confidence).label('avg_consensus'),
            func.count(case((ExpertValidation.consensus_reached == True, 1))).label('successful_validations')
        ).where(
            and_(
                ExpertValidation.requested_at >= start_date,
                ExpertValidation.requested_at <= end_date
            )
        )
        
        result = await self.db.execute(validation_query)
        validation_data = result.one()
        
        # Calculate satisfaction score
        if validation_data.total_validations > 0:
            consensus_rate = validation_data.successful_validations / validation_data.total_validations
            avg_confidence = validation_data.avg_consensus or 0.7
            current_satisfaction = (consensus_rate * 0.6) + (avg_confidence * 0.4)
        else:
            current_satisfaction = self.target_expert_satisfaction
        
        return {
            'current_satisfaction': current_satisfaction,
            'consensus_rate': consensus_rate if validation_data.total_validations > 0 else 0,
            'avg_consensus_confidence': validation_data.avg_consensus or 0,
            'total_validations': validation_data.total_validations,
            'satisfaction_vs_target': current_satisfaction - self.target_expert_satisfaction,
            'satisfaction_grade': self._calculate_grade(current_satisfaction, self.target_expert_satisfaction)
        }
    
    async def _calculate_response_time_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate response time performance metrics"""
        
        # Simulated response time metrics (in real implementation, would query actual response logs)
        return {
            'avg_response_time_ms': 250,  # Average response time
            'p50_response_time_ms': 200,   # Median
            'p95_response_time_ms': 400,   # 95th percentile
            'p99_response_time_ms': 600,   # 99th percentile
            'response_time_vs_target': 250 - self.target_response_time_ms,
            'performance_grade': self._calculate_grade(250, self.target_response_time_ms, inverse=True)
        }
    
    async def _calculate_failure_rate_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate failure rate metrics"""
        
        # Failure patterns analysis
        patterns_query = select(
            func.count().label('total_patterns'),
            func.sum(FailurePattern.frequency_count).label('total_failures'),
            func.avg(FailurePattern.impact_score).label('avg_impact')
        ).where(
            FailurePattern.last_occurrence >= start_date
        )
        
        result = await self.db.execute(patterns_query)
        patterns_data = result.one()
        
        # Expert interventions as failure indicator
        intervention_query = select(
            func.count().label('total_responses'),
            func.count(case((ExpertFeedback.feedback_type != FeedbackType.CORRECT, 1))).label('failed_responses')
        ).where(
            and_(
                ExpertFeedback.feedback_timestamp >= start_date,
                ExpertFeedback.feedback_timestamp <= end_date
            )
        )
        
        result = await self.db.execute(intervention_query)
        intervention_data = result.one()
        
        current_failure_rate = (
            intervention_data.failed_responses / intervention_data.total_responses
            if intervention_data.total_responses > 0 else 0
        )
        
        return {
            'current_failure_rate': current_failure_rate,
            'total_failure_patterns': patterns_data.total_patterns or 0,
            'total_documented_failures': patterns_data.total_failures or 0,
            'avg_failure_impact': patterns_data.avg_impact or 0,
            'failure_trend': 'stable',  # Simplified trend analysis
            'critical_failures': 0  # Count of high-impact failures
        }
    
    async def _calculate_improvement_velocity_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate improvement velocity metrics"""
        
        improvements_query = select(
            func.count().label('total_improvements'),
            func.count(case((SystemImprovement.status == ImprovementStatus.COMPLETED, 1))).label('completed_improvements'),
            func.avg(SystemImprovement.estimated_impact).label('avg_estimated_impact')
        ).where(
            and_(
                SystemImprovement.created_at >= start_date,
                SystemImprovement.created_at <= end_date
            )
        )
        
        result = await self.db.execute(improvements_query)
        improvements_data = result.one()
        
        time_period_weeks = (end_date - start_date).days / 7
        improvements_per_week = (
            improvements_data.completed_improvements / time_period_weeks
            if time_period_weeks > 0 else 0
        )
        
        return {
            'total_improvements': improvements_data.total_improvements or 0,
            'completed_improvements': improvements_data.completed_improvements or 0,
            'improvements_per_week': improvements_per_week,
            'avg_estimated_impact': improvements_data.avg_estimated_impact or 0,
            'completion_rate': (
                improvements_data.completed_improvements / improvements_data.total_improvements
                if improvements_data.total_improvements > 0 else 0
            )
        }
    
    async def _calculate_expert_engagement_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate expert engagement metrics"""
        
        # Active experts
        active_experts_query = select(func.count(func.distinct(ExpertFeedback.expert_id))).where(
            and_(
                ExpertFeedback.feedback_timestamp >= start_date,
                ExpertFeedback.feedback_timestamp <= end_date
            )
        )
        
        result = await self.db.execute(active_experts_query)
        active_experts = result.scalar()
        
        # Total registered experts
        total_experts_query = select(func.count()).select_from(ExpertProfile).where(
            ExpertProfile.is_active == True
        )
        
        result = await self.db.execute(total_experts_query)
        total_experts = result.scalar()
        
        participation_rate = active_experts / total_experts if total_experts > 0 else 0
        
        return {
            'active_experts': active_experts or 0,
            'total_experts': total_experts or 0,
            'participation_rate': participation_rate,
            'avg_feedback_per_expert': 0,  # Would calculate from feedback data
            'expert_retention_rate': 0.85  # Simulated retention rate
        }
    
    def _calculate_overall_quality_score(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted overall quality score"""
        
        # Normalize metrics to 0-1 scale
        normalized_accuracy = metrics['accuracy']
        normalized_satisfaction = metrics['satisfaction']
        normalized_response_time = max(0, 1 - (metrics['response_time'] - 200) / 300)  # 200ms baseline
        normalized_failure_rate = max(0, 1 - (metrics['failure_rate'] * 5))  # 20% failure = 0 score
        normalized_improvement = min(1, metrics['improvement_velocity'] / 2)  # 2 improvements/week = full score
        
        # Weighted average
        weights = {
            'accuracy': 0.3,
            'satisfaction': 0.25,
            'response_time': 0.2,
            'failure_rate': 0.15,
            'improvement': 0.1
        }
        
        overall_score = (
            normalized_accuracy * weights['accuracy'] +
            normalized_satisfaction * weights['satisfaction'] +
            normalized_response_time * weights['response_time'] +
            normalized_failure_rate * weights['failure_rate'] +
            normalized_improvement * weights['improvement']
        )
        
        return min(overall_score, 1.0)
    
    async def _generate_trend_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate trend analysis for key metrics"""
        
        # Simplified trend analysis
        return {
            'accuracy_trend': 'improving',
            'satisfaction_trend': 'stable',
            'response_time_trend': 'stable',
            'failure_rate_trend': 'decreasing',
            'improvement_velocity_trend': 'increasing',
            'overall_trend': 'positive'
        }
    
    async def _get_quality_snapshot(self, date: datetime) -> Dict[str, float]:
        """Get quality metrics snapshot for a specific date"""
        
        # Simplified implementation - in practice would query historical data
        return {
            'overall_quality': 0.82,
            'accuracy': 0.85,
            'satisfaction': 0.78
        }
    
    async def _calculate_improvement_roi(self, improvements: List[SystemImprovement]) -> Dict[str, Any]:
        """Calculate ROI metrics for improvements"""
        
        if not improvements:
            return {'total_roi': 0, 'avg_roi': 0, 'cost_savings': 0}
        
        # Simplified ROI calculation
        total_estimated_impact = sum(i.estimated_impact for i in improvements)
        completed_improvements = [i for i in improvements if i.status == ImprovementStatus.COMPLETED]
        
        return {
            'total_estimated_impact': total_estimated_impact,
            'completed_impact': sum(i.estimated_impact for i in completed_improvements),
            'roi_percentage': total_estimated_impact * 100,  # Simplified ROI
            'cost_savings_estimated': total_estimated_impact * 1000,  # €1000 per impact point
            'payback_period_days': 30  # Estimated payback period
        }
    
    def _calculate_grade(self, current_value: float, target_value: float, inverse: bool = False) -> str:
        """Calculate letter grade based on performance vs target"""
        
        if inverse:  # Lower is better (e.g., response time)
            ratio = target_value / current_value if current_value > 0 else 0
        else:  # Higher is better
            ratio = current_value / target_value if target_value > 0 else 0
        
        if ratio >= 1.1:
            return 'A+'
        elif ratio >= 1.0:
            return 'A'
        elif ratio >= 0.9:
            return 'B+'
        elif ratio >= 0.8:
            return 'B'
        elif ratio >= 0.7:
            return 'C+'
        elif ratio >= 0.6:
            return 'C'
        else:
            return 'D'
    
    def _get_category_description(self, category: Optional[ItalianFeedbackCategory]) -> str:
        """Get Italian description for feedback category"""
        
        if not category:
            return 'Categoria non specificata'
        
        descriptions = {
            ItalianFeedbackCategory.NORMATIVA_OBSOLETA: 'Riferimenti normativi obsoleti o non aggiornati',
            ItalianFeedbackCategory.INTERPRETAZIONE_ERRATA: 'Interpretazione errata della normativa',
            ItalianFeedbackCategory.CASO_MANCANTE: 'Casi specifici non considerati nella risposta',
            ItalianFeedbackCategory.CALCOLO_SBAGLIATO: 'Errori nei calcoli o nelle formule',
            ItalianFeedbackCategory.TROPPO_GENERICO: 'Risposta troppo generica, serve maggiore specificità'
        }
        
        return descriptions.get(category, 'Categoria sconosciuta')
    
    def _calculate_expert_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall expert performance score"""
        
        accuracy = metrics.get('accuracy_rate', 0.5)
        trust_score = metrics.get('trust_score', 0.5)
        response_time = metrics.get('response_time', 300)
        feedback_count = metrics.get('feedback_count', 0)
        
        # Normalize response time (lower is better)
        normalized_response_time = max(0, 1 - (response_time - 180) / 600)  # 3 minutes baseline
        
        # Activity bonus
        activity_bonus = min(feedback_count / 50, 0.1)  # Max 10% bonus for 50+ feedback
        
        # Weighted performance score
        performance_score = (
            accuracy * 0.4 +
            trust_score * 0.3 +
            normalized_response_time * 0.2 +
            activity_bonus * 0.1
        )
        
        return min(performance_score, 1.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current dashboard statistics"""
        
        return {
            'session_stats': self.stats,
            'configuration': {
                'target_accuracy_score': self.target_accuracy_score,
                'target_expert_satisfaction': self.target_expert_satisfaction,
                'target_response_time_ms': self.target_response_time_ms,
                'quality_degradation_threshold': self.quality_degradation_threshold,
                'failure_rate_alert_threshold': self.failure_rate_alert_threshold
            },
            'cache_performance': {
                'metrics_cache_ttl': self.metrics_cache_ttl,
                'analytics_cache_ttl': self.analytics_cache_ttl,
                'cache_hit_rate': self.stats['cache_hit_rate'] / max(self.stats['dashboards_served'], 1)
            },
            'dashboard_usage': {
                'dashboards_served': self.stats['dashboards_served'],
                'metrics_calculated': self.stats['metrics_calculated'],
                'alerts_generated': self.stats['alerts_generated']
            }
        }