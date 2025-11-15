"""Automatic Improvement Engine for Quality Analysis System.

Automatically generates and applies improvements based on failure patterns and expert feedback.
Includes automated prompt updates, knowledge base enhancements, and system optimization.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.quality_analysis import (
    QUALITY_ANALYSIS_CONFIG,
    ExpertFeedback,
    FailurePattern,
    ImprovementStatus,
    PromptTemplate,
    SystemImprovement,
)
from app.services.advanced_prompt_engineer import AdvancedPromptEngineer
from app.services.cache import CacheService
from app.services.failure_pattern_analyzer import FailurePatternAnalyzer


class ImprovementEngineError(Exception):
    """Custom exception for improvement engine operations"""

    pass


class AutomaticImprovementEngine:
    """Automatic improvement engine for continuous system enhancement.

    Features:
    - Automated improvement recommendation generation
    - Prompt template updates based on failure patterns
    - Knowledge base content enhancement
    - Performance optimization suggestions
    - ROI-based improvement prioritization
    - Expert validation integration
    """

    def __init__(
        self,
        db: AsyncSession,
        prompt_engineer: AdvancedPromptEngineer,
        pattern_analyzer: FailurePatternAnalyzer,
        cache: CacheService | None = None,
    ):
        self.db = db
        self.prompt_engineer = prompt_engineer
        self.pattern_analyzer = pattern_analyzer
        self.cache = cache

        # Improvement thresholds
        self.auto_improvement_threshold = QUALITY_ANALYSIS_CONFIG.AUTO_IMPROVEMENT_THRESHOLD
        self.expert_validation_threshold = QUALITY_ANALYSIS_CONFIG.EXPERT_VALIDATION_THRESHOLD
        self.max_concurrent_improvements = QUALITY_ANALYSIS_CONFIG.MAX_CONCURRENT_IMPROVEMENTS

        # Cache settings
        self.recommendations_cache_ttl = 1800  # 30 minutes

        # Improvement strategies
        self.improvement_strategies = self._initialize_improvement_strategies()

        # Statistics tracking
        self.stats = {
            "recommendations_generated": 0,
            "improvements_applied": 0,
            "automatic_updates": 0,
            "expert_validations_requested": 0,
            "success_rate": 0.0,
        }

    async def generate_recommendations(self, failure_analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate improvement recommendations based on failure analysis.

        Args:
            failure_analysis: Analysis results containing patterns, impacts, and suggestions

        Returns:
            List of improvement recommendations with priority and implementation details
        """
        start_time = time.time()

        try:
            primary_patterns = failure_analysis.get("primary_patterns", [])
            affected_areas = failure_analysis.get("affected_areas", [])
            expert_suggestions = failure_analysis.get("expert_suggestions", [])

            logger.info(f"Generating recommendations for {len(primary_patterns)} patterns")

            recommendations = []

            # Generate pattern-based recommendations
            for pattern in primary_patterns:
                pattern_recommendations = await self._generate_pattern_recommendations(pattern)
                recommendations.extend(pattern_recommendations)

            # Generate area-specific recommendations
            for area in affected_areas:
                area_recommendations = await self._generate_area_recommendations(area, failure_analysis)
                recommendations.extend(area_recommendations)

            # Process expert suggestions
            expert_recommendations = await self._process_expert_suggestions(expert_suggestions)
            recommendations.extend(expert_recommendations)

            # Prioritize and rank recommendations
            prioritized_recommendations = self._prioritize_recommendations(recommendations)

            # Filter by feasibility and impact
            final_recommendations = self._filter_recommendations(prioritized_recommendations)

            # Cache recommendations
            if self.cache:
                cache_key = f"improvement_recommendations:{hash(str(failure_analysis))}"
                await self.cache.setex(cache_key, self.recommendations_cache_ttl, final_recommendations)

            # Update statistics
            self.stats["recommendations_generated"] += len(final_recommendations)

            generation_time = (time.time() - start_time) * 1000
            logger.info(f"Generated {len(final_recommendations)} recommendations in {generation_time:.1f}ms")

            return final_recommendations

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            raise ImprovementEngineError(f"Failed to generate recommendations: {e}")

    async def apply_automatic_updates(self, update_request: dict[str, Any]) -> dict[str, Any]:
        """Apply automatic updates that don't require expert validation.

        Args:
            update_request: Update request with template_id, improvement_type, and changes

        Returns:
            Results of the update application
        """
        try:
            improvement_type = update_request.get("improvement_type", "")
            confidence_score = update_request.get("confidence_score", 0.0)

            # Check if automatic application is allowed
            if confidence_score < self.auto_improvement_threshold:
                return {
                    "success": False,
                    "reason": "confidence_too_low",
                    "message": f"Confidence {confidence_score} below threshold {self.auto_improvement_threshold}",
                }

            results = {"success": True, "changes_applied": []}

            # Apply different types of updates
            if improvement_type == "prompt_template_update":
                template_result = await self._apply_template_update(update_request)
                results["changes_applied"].append(template_result)

            elif improvement_type == "knowledge_base_update":
                kb_result = await self._apply_knowledge_base_update(update_request)
                results["changes_applied"].append(kb_result)

            elif improvement_type == "regulatory_reference_update":
                reg_result = await self._apply_regulatory_update(update_request)
                results["changes_applied"].append(reg_result)

            elif improvement_type == "calculation_formula_fix":
                calc_result = await self._apply_calculation_fix(update_request)
                results["changes_applied"].append(calc_result)

            else:
                return {
                    "success": False,
                    "reason": "unknown_improvement_type",
                    "message": f"Unknown improvement type: {improvement_type}",
                }

            # Create improvement record
            await self._create_improvement_record(update_request, results)

            # Update statistics
            self.stats["improvements_applied"] += 1
            self.stats["automatic_updates"] += 1

            logger.info(f"Automatic update applied: {improvement_type}")

            return results

        except Exception as e:
            logger.error(f"Automatic update failed: {e}")
            return {"success": False, "error": str(e)}

    async def update_knowledge_base(self, knowledge_update: dict[str, Any]) -> dict[str, Any]:
        """Update knowledge base with new or corrected information.

        Args:
            knowledge_update: Update data with category, content, source, and confidence

        Returns:
            Results of the knowledge base update
        """
        try:
            category = knowledge_update.get("category", "")
            outdated_content = knowledge_update.get("outdated_content", "")
            updated_content = knowledge_update.get("updated_content", "")
            source = knowledge_update.get("source", "")
            confidence = knowledge_update.get("confidence", 0.0)

            # Validate update data
            if not all([category, updated_content, source]):
                return {"success": False, "error": "Missing required fields: category, updated_content, source"}

            # Check if this is a high-confidence update that can be applied automatically
            if confidence >= self.auto_improvement_threshold:
                # Apply update automatically
                update_result = await self._perform_knowledge_update(
                    category, outdated_content, updated_content, source
                )

                # Log the update
                await self._log_knowledge_update(knowledge_update, "automatic")

                return {
                    "success": True,
                    "updated_items": update_result.get("updated_items", 0),
                    "update_type": "automatic",
                    "confidence": confidence,
                }

            else:
                # Queue for expert validation
                validation_request = await self._queue_for_expert_validation(knowledge_update)

                return {
                    "success": True,
                    "updated_items": 0,
                    "update_type": "pending_validation",
                    "validation_id": validation_request["validation_id"],
                    "confidence": confidence,
                }

        except Exception as e:
            logger.error(f"Knowledge base update failed: {e}")
            return {"success": False, "error": str(e)}

    async def measure_improvement_impact(
        self, before_metrics: dict[str, float], after_metrics: dict[str, float], time_period_days: int = 30
    ) -> dict[str, Any]:
        """Measure the impact of improvements on system performance.

        Args:
            before_metrics: Metrics before improvement
            after_metrics: Metrics after improvement
            time_period_days: Time period for measurement

        Returns:
            Impact analysis with improvement percentages and success indicators
        """
        try:
            impact_analysis = {
                "measurement_period_days": time_period_days,
                "metrics_comparison": {},
                "overall_success": False,
            }

            # Calculate individual metric improvements
            for metric_name in before_metrics:
                if metric_name in after_metrics:
                    before_value = before_metrics[metric_name]
                    after_value = after_metrics[metric_name]

                    if before_value > 0:
                        improvement = (after_value - before_value) / before_value
                        impact_analysis["metrics_comparison"][metric_name] = {
                            "before": before_value,
                            "after": after_value,
                            "improvement_percentage": improvement * 100,
                            "absolute_change": after_value - before_value,
                        }

            # Calculate specific improvements
            accuracy_improvement = (
                impact_analysis["metrics_comparison"].get("accuracy_score", {}).get("improvement_percentage", 0)
            )
            satisfaction_improvement = (
                impact_analysis["metrics_comparison"].get("user_satisfaction", {}).get("improvement_percentage", 0)
            )
            failure_rate_change = (
                impact_analysis["metrics_comparison"].get("failure_rate", {}).get("improvement_percentage", 0)
            )

            # Overall success determination
            success_criteria = [
                accuracy_improvement > 5,  # At least 5% accuracy improvement
                satisfaction_improvement > 3,  # At least 3% satisfaction improvement
                failure_rate_change < -10,  # At least 10% failure rate reduction
            ]

            impact_analysis.update(
                {
                    "accuracy_improvement": accuracy_improvement,
                    "satisfaction_improvement": satisfaction_improvement,
                    "failure_reduction": -failure_rate_change,
                    "overall_success": sum(success_criteria) >= 2,  # At least 2/3 criteria met
                    "success_score": sum(success_criteria) / len(success_criteria),
                    "improvement_summary": self._generate_improvement_summary(impact_analysis["metrics_comparison"]),
                }
            )

            return impact_analysis

        except Exception as e:
            logger.error(f"Impact measurement failed: {e}")
            return {"error": str(e), "overall_success": False}

    async def _generate_pattern_recommendations(self, pattern: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate recommendations based on a specific failure pattern"""
        recommendations = []
        pattern_type = pattern.get("type", "")
        frequency = pattern.get("frequency", 0)
        impact = pattern.get("impact", 0.0)

        if pattern_type == "regulatory_outdated":
            recommendations.append(
                {
                    "action_type": "update_regulatory_references",
                    "priority": "high" if frequency > 10 else "medium",
                    "description": "Aggiorna i riferimenti normativi obsoleti",
                    "implementation_details": {
                        "affected_patterns": [pattern],
                        "update_sources": ["Gazzetta Ufficiale", "Agenzia delle Entrate"],
                        "estimated_effort": "medium",
                    },
                    "confidence_score": 0.9,
                    "expected_impact": impact * 0.8,
                }
            )

        elif pattern_type == "interpretation_error":
            recommendations.append(
                {
                    "action_type": "improve_interpretation_logic",
                    "priority": "high",
                    "description": "Migliora la logica di interpretazione normativa",
                    "implementation_details": {
                        "affected_patterns": [pattern],
                        "improvement_areas": ["context_analysis", "regulatory_mapping"],
                        "estimated_effort": "high",
                    },
                    "confidence_score": 0.85,
                    "expected_impact": impact * 0.7,
                }
            )

        elif pattern_type == "calculation_error":
            recommendations.append(
                {
                    "action_type": "fix_calculation_formulas",
                    "priority": "critical",
                    "description": "Correggi le formule di calcolo errate",
                    "implementation_details": {
                        "affected_patterns": [pattern],
                        "calculation_types": pattern.get("calculation_types", []),
                        "estimated_effort": "high",
                    },
                    "confidence_score": 0.95,
                    "expected_impact": impact * 0.9,
                }
            )

        elif pattern_type == "semantic_cluster":
            recommendations.append(
                {
                    "action_type": "enhance_semantic_understanding",
                    "priority": "medium",
                    "description": "Migliora la comprensione semantica delle query",
                    "implementation_details": {
                        "affected_patterns": [pattern],
                        "semantic_keywords": pattern.get("semantic_keywords", []),
                        "estimated_effort": "medium",
                    },
                    "confidence_score": 0.75,
                    "expected_impact": impact * 0.6,
                }
            )

        return recommendations

    async def _generate_area_recommendations(self, area: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate recommendations for specific affected areas"""
        recommendations = []

        if area == "regime_forfettario":
            recommendations.append(
                {
                    "action_type": "update_regime_forfettario_logic",
                    "priority": "high",
                    "description": "Aggiorna la logica per il regime forfettario 2024",
                    "implementation_details": {
                        "affected_area": area,
                        "specific_updates": ["Soglia €85.000", "Nuove limitazioni", "Codici ATECO aggiornati"],
                        "estimated_effort": "medium",
                    },
                    "confidence_score": 0.9,
                    "expected_impact": 0.6,
                }
            )

        elif area == "iva_calculation":
            recommendations.append(
                {
                    "action_type": "improve_iva_calculation_accuracy",
                    "priority": "high",
                    "description": "Migliora l'accuratezza dei calcoli IVA",
                    "implementation_details": {
                        "affected_area": area,
                        "calculation_improvements": ["Aliquote aggiornate", "Casi di esenzione", "Regime speciali"],
                        "estimated_effort": "medium",
                    },
                    "confidence_score": 0.85,
                    "expected_impact": 0.7,
                }
            )

        return recommendations

    async def _process_expert_suggestions(self, suggestions: list[str]) -> list[dict[str, Any]]:
        """Process expert suggestions into actionable recommendations"""
        recommendations = []

        for suggestion in suggestions:
            suggestion_lower = suggestion.lower()

            if "aggiorna" in suggestion_lower and "normativa" in suggestion_lower:
                recommendations.append(
                    {
                        "action_type": "regulatory_content_update",
                        "priority": "high",
                        "description": f"Implementa suggerimento esperto: {suggestion}",
                        "implementation_details": {
                            "expert_suggestion": suggestion,
                            "suggested_action": "regulatory_update",
                            "estimated_effort": "medium",
                        },
                        "confidence_score": 0.8,
                        "expected_impact": 0.5,
                        "source": "expert_suggestion",
                    }
                )

            elif "esempio" in suggestion_lower:
                recommendations.append(
                    {
                        "action_type": "add_practical_examples",
                        "priority": "medium",
                        "description": f"Implementa suggerimento esperto: {suggestion}",
                        "implementation_details": {
                            "expert_suggestion": suggestion,
                            "suggested_action": "example_enhancement",
                            "estimated_effort": "low",
                        },
                        "confidence_score": 0.75,
                        "expected_impact": 0.4,
                        "source": "expert_suggestion",
                    }
                )

        return recommendations

    def _prioritize_recommendations(self, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prioritize recommendations based on impact, confidence, and effort"""

        def calculate_priority_score(rec):
            impact = rec.get("expected_impact", 0.0)
            confidence = rec.get("confidence_score", 0.0)

            # Effort penalty
            effort = rec.get("implementation_details", {}).get("estimated_effort", "medium")
            effort_penalty = {"low": 0, "medium": 0.1, "high": 0.2}.get(effort, 0.1)

            # Priority boost
            priority = rec.get("priority", "medium")
            priority_boost = {"critical": 0.3, "high": 0.2, "medium": 0.1, "low": 0.0}.get(priority, 0.1)

            return (impact * confidence * (1 - effort_penalty)) + priority_boost

        # Calculate priority scores and sort
        for rec in recommendations:
            rec["priority_score"] = calculate_priority_score(rec)

        return sorted(recommendations, key=lambda x: x["priority_score"], reverse=True)

    def _filter_recommendations(self, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter recommendations by feasibility and impact"""
        filtered = []

        for rec in recommendations:
            # Filter by minimum confidence
            if rec.get("confidence_score", 0) < 0.6:
                continue

            # Filter by minimum expected impact
            if rec.get("expected_impact", 0) < 0.2:
                continue

            # Check for duplicate action types
            if any(existing["action_type"] == rec["action_type"] for existing in filtered):
                continue

            filtered.append(rec)

            # Limit total recommendations
            if len(filtered) >= 10:
                break

        return filtered

    async def _apply_template_update(self, update_request: dict[str, Any]) -> dict[str, Any]:
        """Apply automatic template updates"""
        try:
            template_id = update_request.get("template_id", "")
            specific_changes = update_request.get("specific_changes", [])

            # Get template
            template = await self.prompt_engineer._get_template(template_id)
            if not template:
                return {"success": False, "error": "Template not found"}

            # Apply changes
            updated_template_text = template.template_text

            for change in specific_changes:
                if "Update regime forfettario references to 2024" in change:
                    updated_template_text = updated_template_text.replace("€65.000", "€85.000").replace("2023", "2024")

                elif "Add new IVA calculation examples" in change:
                    if "**Esempi Pratici:**" not in updated_template_text:
                        updated_template_text += "\n\n**Esempi Pratici:** {practical_examples}"

            # Create improved version
            improvement_result = await self.prompt_engineer.improve_template_from_feedback(
                {"template_id": template_id, "feedback_data": [], "performance_metrics": {"accuracy_score": 0.8}}
            )

            return {
                "success": improvement_result.get("success", False),
                "changes": specific_changes,
                "new_template_id": improvement_result.get("new_template_id"),
            }

        except Exception as e:
            logger.error(f"Template update failed: {e}")
            return {"success": False, "error": str(e)}

    async def _apply_knowledge_base_update(self, update_request: dict[str, Any]) -> dict[str, Any]:
        """Apply knowledge base updates"""
        # Simulated knowledge base update
        category = update_request.get("category", "")
        update_request.get("updated_content", "")

        return {"success": True, "category": category, "updated_items": 1, "update_type": "knowledge_base"}

    async def _apply_regulatory_update(self, update_request: dict[str, Any]) -> dict[str, Any]:
        """Apply regulatory reference updates"""
        return {
            "success": True,
            "update_type": "regulatory_references",
            "updated_references": update_request.get("regulatory_references", []),
        }

    async def _apply_calculation_fix(self, update_request: dict[str, Any]) -> dict[str, Any]:
        """Apply calculation formula fixes"""
        return {
            "success": True,
            "update_type": "calculation_formulas",
            "fixed_calculations": update_request.get("calculation_types", []),
        }

    async def _create_improvement_record(self, update_request: dict[str, Any], results: dict[str, Any]) -> None:
        """Create improvement record in database"""
        try:
            improvement = SystemImprovement(
                improvement_type=update_request.get("improvement_type", ""),
                title=f"Automatic improvement: {update_request.get('improvement_type', '')}",
                description="Applied automatic improvement based on pattern analysis",
                category="automatic",
                justification=update_request.get("justification", "Pattern-based automatic improvement"),
                implementation_details=update_request,
                status=ImprovementStatus.COMPLETED,
                confidence_score=update_request.get("confidence_score", 0.0),
                priority_score=0.8,
                estimated_impact=update_request.get("expected_impact", 0.5),
                actual_completion_date=datetime.utcnow(),
                requires_expert_validation=False,
            )

            self.db.add(improvement)
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to create improvement record: {e}")
            await self.db.rollback()

    async def _perform_knowledge_update(
        self, category: str, outdated: str, updated: str, source: str
    ) -> dict[str, Any]:
        """Perform actual knowledge base update"""
        # Simulated implementation
        return {"updated_items": 1, "category": category, "source": source}

    async def _log_knowledge_update(self, update_data: dict[str, Any], update_type: str) -> None:
        """Log knowledge update for audit purposes"""
        logger.info(f"Knowledge update applied: {update_type} - {update_data.get('category', 'unknown')}")

    async def _queue_for_expert_validation(self, knowledge_update: dict[str, Any]) -> dict[str, Any]:
        """Queue update for expert validation"""
        validation_id = str(uuid4())

        # Store validation request (simulated)
        logger.info(f"Queued for expert validation: {validation_id}")

        self.stats["expert_validations_requested"] += 1

        return {"validation_id": validation_id}

    def _generate_improvement_summary(self, metrics_comparison: dict[str, Any]) -> str:
        """Generate human-readable improvement summary"""
        improvements = []

        for metric, data in metrics_comparison.items():
            improvement_pct = data.get("improvement_percentage", 0)
            if improvement_pct > 5:
                improvements.append(f"{metric}: +{improvement_pct:.1f}%")
            elif improvement_pct < -5:
                improvements.append(f"{metric}: {improvement_pct:.1f}%")

        if improvements:
            return f"Miglioramenti significativi: {', '.join(improvements)}"
        else:
            return "Nessun miglioramento significativo rilevato"

    def _initialize_improvement_strategies(self) -> dict[str, dict[str, Any]]:
        """Initialize improvement strategies for different pattern types"""
        return {
            "regulatory_outdated": {
                "action_type": "update_regulatory_references",
                "confidence_threshold": 0.85,
                "auto_apply": True,
                "validation_required": False,
            },
            "calculation_error": {
                "action_type": "fix_calculation_formulas",
                "confidence_threshold": 0.9,
                "auto_apply": True,
                "validation_required": True,
            },
            "interpretation_error": {
                "action_type": "improve_interpretation_logic",
                "confidence_threshold": 0.8,
                "auto_apply": False,
                "validation_required": True,
            },
            "semantic_cluster": {
                "action_type": "enhance_semantic_understanding",
                "confidence_threshold": 0.75,
                "auto_apply": True,
                "validation_required": False,
            },
        }

    async def get_improvement_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get analytics for improvement engine performance"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Query improvement records
            improvements_query = (
                select(SystemImprovement)
                .where(SystemImprovement.created_at >= start_date)
                .order_by(desc(SystemImprovement.created_at))
            )

            result = await self.db.execute(improvements_query)
            improvements = result.scalars().all()

            # Calculate analytics
            total_improvements = len(improvements)
            completed_improvements = len([i for i in improvements if i.status == ImprovementStatus.COMPLETED])

            improvement_types = {}
            impact_distribution = {"low": 0, "medium": 0, "high": 0}

            for improvement in improvements:
                imp_type = improvement.improvement_type
                improvement_types[imp_type] = improvement_types.get(imp_type, 0) + 1

                impact = improvement.estimated_impact
                if impact >= 0.7:
                    impact_distribution["high"] += 1
                elif impact >= 0.4:
                    impact_distribution["medium"] += 1
                else:
                    impact_distribution["low"] += 1

            return {
                "period_days": days,
                "total_improvements": total_improvements,
                "completed_improvements": completed_improvements,
                "completion_rate": completed_improvements / total_improvements if total_improvements > 0 else 0,
                "improvement_types": improvement_types,
                "impact_distribution": impact_distribution,
                "session_stats": self.stats,
                "success_rate": completed_improvements / total_improvements if total_improvements > 0 else 0,
                "recent_improvements": [
                    {
                        "title": i.title,
                        "type": i.improvement_type,
                        "status": i.status.value,
                        "impact": i.estimated_impact,
                        "created": i.created_at.isoformat(),
                    }
                    for i in improvements[:10]
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get improvement analytics: {e}")
            return {"error": str(e)}

    def get_statistics(self) -> dict[str, Any]:
        """Get current engine statistics"""
        return {
            "session_stats": self.stats,
            "configuration": {
                "auto_improvement_threshold": self.auto_improvement_threshold,
                "expert_validation_threshold": self.expert_validation_threshold,
                "max_concurrent_improvements": self.max_concurrent_improvements,
            },
            "improvement_strategies": list(self.improvement_strategies.keys()),
            "performance_metrics": {
                "recommendations_per_analysis": self.stats["recommendations_generated"]
                / max(self.stats["improvements_applied"], 1),
                "automatic_application_rate": self.stats["automatic_updates"]
                / max(self.stats["improvements_applied"], 1),
                "expert_validation_rate": self.stats["expert_validations_requested"]
                / max(self.stats["improvements_applied"], 1),
            },
        }
