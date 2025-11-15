"""Advanced Prompt Engineering Service for Quality Analysis System.

Implements structured reasoning approach for Italian tax queries with:
- Template-based prompt generation with variables
- Quality metrics and A/B testing
- Automatic improvement based on expert feedback
- Italian tax domain optimization
"""

import asyncio
import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.quality_analysis import QUALITY_ANALYSIS_CONFIG, ExpertFeedback, PromptTemplate
from app.services.cache import CacheService


class PromptEngineeringError(Exception):
    """Custom exception for prompt engineering operations"""

    pass


class AdvancedPromptEngineer:
    """Advanced prompt engineering service with structured reasoning.

    Features:
    - Template-based prompt generation with variable substitution
    - Italian tax domain-specific prompt optimization
    - Quality metrics calculation and tracking
    - A/B testing for prompt templates
    - Automatic improvement based on expert feedback
    - Performance monitoring and analytics
    """

    def __init__(self, db: AsyncSession, cache: CacheService | None = None):
        self.db = db
        self.cache = cache

        # Cache settings
        self.template_cache_ttl = 7200  # 2 hours
        self.prompt_cache_ttl = 3600  # 1 hour

        # Quality thresholds
        self.min_quality_score = 0.7
        self.target_quality_score = 0.85

        # A/B testing settings
        self.ab_test_split_ratio = 0.5  # 50/50 split

        # Italian tax domain templates
        self.base_templates = self._initialize_base_templates()

        # Statistics tracking
        self.stats = {
            "templates_created": 0,
            "prompts_generated": 0,
            "improvements_applied": 0,
            "avg_quality_score": 0.0,
        }

    async def create_prompt_template(self, template_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new prompt template with quality validation"""
        try:
            # Validate template data
            self._validate_template_data(template_data)

            # Calculate initial quality metrics
            quality_metrics = await self._calculate_template_quality(template_data["template_text"])

            # Create template record
            template = PromptTemplate(
                name=template_data["name"],
                version=template_data.get("version", "1.0"),
                template_text=template_data["template_text"],
                variables=template_data.get("variables", []),
                description=template_data.get("description"),
                category=template_data.get("category", "general"),
                specialization_areas=template_data.get("specialization_areas", []),
                complexity_level=template_data.get("complexity_level", "medium"),
                clarity_score=quality_metrics["clarity_score"],
                completeness_score=quality_metrics["completeness_score"],
                accuracy_score=quality_metrics.get("accuracy_score", 0.8),
                overall_quality_score=quality_metrics["overall_score"],
                variant_group=template_data.get("variant_group"),
                created_by=template_data.get("created_by"),
            )

            # Store in database
            self.db.add(template)
            await self.db.commit()
            await self.db.refresh(template)

            # Cache template
            if self.cache:
                cache_key = f"prompt_template:{template.id}"
                await self.cache.setex(cache_key, self.template_cache_ttl, template_data)

            # Update statistics
            self.stats["templates_created"] += 1

            logger.info(f"Created prompt template: {template.name} (quality: {quality_metrics['overall_score']:.2f})")

            return {
                "success": True,
                "template_id": str(template.id),
                "template_name": template.name,
                "quality_score": quality_metrics["overall_score"],
                "quality_metrics": quality_metrics,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create prompt template: {e}")
            return {"success": False, "error": str(e)}

    async def generate_enhanced_prompt(self, template_id: str, context_data: dict[str, Any]) -> str:
        """Generate enhanced prompt using template and context data"""
        try:
            # Retrieve template
            template = await self._get_template(template_id)
            if not template:
                raise PromptEngineeringError(f"Template not found: {template_id}")

            # Generate prompt with context
            enhanced_prompt = await self._process_template(template, context_data)

            # Apply Italian tax domain enhancements
            enhanced_prompt = self._apply_italian_tax_enhancements(enhanced_prompt, context_data)

            # Cache generated prompt
            if self.cache:
                cache_key = (
                    f"generated_prompt:{hashlib.md5(f'{template_id}:{str(context_data)}'.encode()).hexdigest()}"
                )
                await self.cache.setex(cache_key, self.prompt_cache_ttl, enhanced_prompt)

            # Update usage statistics
            await self._update_template_usage(template)
            self.stats["prompts_generated"] += 1

            return enhanced_prompt

        except Exception as e:
            logger.error(f"Failed to generate enhanced prompt: {e}")
            raise PromptEngineeringError(f"Prompt generation failed: {e}")

    async def calculate_prompt_quality(self, prompt_text: str) -> dict[str, float]:
        """Calculate quality metrics for a prompt"""
        return await self._calculate_template_quality(prompt_text)

    async def select_template_variant(self, query_category: str) -> dict[str, Any]:
        """Select template variant for A/B testing"""
        try:
            # Find available variants for category
            variants_query = (
                select(PromptTemplate)
                .where(
                    and_(
                        PromptTemplate.category == query_category,
                        PromptTemplate.is_active is True,
                        PromptTemplate.variant_group.isnot(None),
                    )
                )
                .order_by(PromptTemplate.usage_count.asc())
            )

            result = await self.db.execute(variants_query)
            variants = result.scalars().all()

            if not variants:
                # Return default template
                default_query = (
                    select(PromptTemplate)
                    .where(and_(PromptTemplate.category == query_category, PromptTemplate.is_active is True))
                    .order_by(PromptTemplate.overall_quality_score.desc())
                )

                result = await self.db.execute(default_query)
                default_template = result.scalar_one_or_none()

                if default_template:
                    return {
                        "template_id": str(default_template.id),
                        "variant": "default",
                        "name": default_template.name,
                    }
                else:
                    raise PromptEngineeringError(f"No templates found for category: {query_category}")

            # Select variant for A/B testing (simple round-robin)
            import random

            selected_variant = random.choice(variants)

            return {
                "template_id": str(selected_variant.id),
                "variant": selected_variant.variant_group or "A",
                "name": selected_variant.name,
                "quality_score": selected_variant.overall_quality_score,
            }

        except Exception as e:
            logger.error(f"Failed to select template variant: {e}")
            raise PromptEngineeringError(f"Template variant selection failed: {e}")

    async def improve_template_from_feedback(self, improvement_data: dict[str, Any]) -> dict[str, Any]:
        """Improve template based on expert feedback"""
        try:
            template_id = improvement_data["template_id"]
            feedback_data = improvement_data["feedback_data"]
            performance_metrics = improvement_data.get("performance_metrics", {})

            # Retrieve template
            template = await self._get_template(template_id)
            if not template:
                return {"success": False, "error": f"Template not found: {template_id}"}

            # Analyze feedback patterns
            improvement_suggestions = await self._analyze_feedback_patterns(feedback_data)

            # Generate improved template version
            improved_template_text = await self._generate_improved_template(
                template.template_text, improvement_suggestions, performance_metrics
            )

            # Create new version
            new_version = f"{float(template.version) + 0.1:.1f}"
            new_template_data = {
                "name": f"{template.name}_v{new_version}",
                "version": new_version,
                "template_text": improved_template_text,
                "variables": template.variables,
                "category": template.category,
                "specialization_areas": template.specialization_areas,
                "variant_group": template.variant_group,
            }

            # Create improved template
            result = await self.create_prompt_template(new_template_data)

            if result["success"]:
                # Deactivate old template
                template.is_active = False
                await self.db.commit()

                self.stats["improvements_applied"] += 1

                logger.info(f"Template improved: {template.name} -> {new_template_data['name']}")

                return {
                    "success": True,
                    "old_template_id": template_id,
                    "new_template_id": result["template_id"],
                    "improvements_made": len(improvement_suggestions),
                    "enhanced_sections": improvement_suggestions,
                }

            return result

        except Exception as e:
            logger.error(f"Failed to improve template from feedback: {e}")
            return {"success": False, "error": str(e)}

    def _validate_template_data(self, template_data: dict[str, Any]) -> None:
        """Validate template data structure"""
        required_fields = ["name", "template_text"]

        for field in required_fields:
            if field not in template_data:
                raise PromptEngineeringError(f"Missing required field: {field}")

        # Validate template text
        if len(template_data["template_text"]) < 50:
            raise PromptEngineeringError("Template text too short (minimum 50 characters)")

        # Validate variables format
        variables = template_data.get("variables", [])
        if not isinstance(variables, list):
            raise PromptEngineeringError("Variables must be a list")

        # Check for variable placeholders in template
        template_text = template_data["template_text"]
        for variable in variables:
            if f"{{{variable}}}" not in template_text:
                logger.warning(f"Variable '{variable}' not found in template text")

    async def _calculate_template_quality(self, template_text: str) -> dict[str, float]:
        """Calculate quality metrics for template text"""
        # Clarity score based on structure and readability
        clarity_score = self._calculate_clarity_score(template_text)

        # Completeness score based on comprehensive coverage
        completeness_score = self._calculate_completeness_score(template_text)

        # Structure score based on organized sections
        structure_score = self._calculate_structure_score(template_text)

        # Italian tax domain score
        domain_score = self._calculate_italian_tax_domain_score(template_text)

        # Overall score (weighted average)
        overall_score = clarity_score * 0.25 + completeness_score * 0.25 + structure_score * 0.25 + domain_score * 0.25

        return {
            "clarity_score": clarity_score,
            "completeness_score": completeness_score,
            "structure_score": structure_score,
            "domain_score": domain_score,
            "overall_score": min(overall_score, 1.0),
        }

    def _calculate_clarity_score(self, text: str) -> float:
        """Calculate clarity score based on readability metrics"""
        # Basic readability metrics
        sentences = len(re.findall(r"[.!?]+", text))
        words = len(text.split())

        if sentences == 0:
            return 0.0

        avg_sentence_length = words / sentences

        # Ideal range: 15-25 words per sentence
        if 15 <= avg_sentence_length <= 25:
            length_score = 1.0
        elif 10 <= avg_sentence_length < 15 or 25 < avg_sentence_length <= 30:
            length_score = 0.8
        else:
            length_score = 0.6

        # Check for structured elements
        structure_elements = ["**", "##", "*", "-", "1.", "2.", "•"]
        structure_bonus = 0.2 if any(elem in text for elem in structure_elements) else 0.0

        return min(length_score + structure_bonus, 1.0)

    def _calculate_completeness_score(self, text: str) -> float:
        """Calculate completeness score based on comprehensive coverage"""
        # Essential components for tax queries
        essential_components = [
            "domanda",
            "quesito",
            "problema",  # Question identification
            "normativa",
            "legge",
            "decreto",  # Regulatory references
            "interpretazione",
            "analisi",  # Analysis section
            "conclusione",
            "risposta",  # Conclusion
        ]

        components_found = sum(1 for component in essential_components if component.lower() in text.lower())

        completeness_score = components_found / len(essential_components)

        # Bonus for comprehensive structure
        if len(text) > 500:  # Substantial content
            completeness_score += 0.1

        return min(completeness_score, 1.0)

    def _calculate_structure_score(self, text: str) -> float:
        """Calculate structure score based on organization"""
        structure_score = 0.0

        # Check for headers/sections
        if re.search(r"#+\s*\w+", text):
            structure_score += 0.3

        # Check for numbered lists
        if re.search(r"\d+\.\s+\w+", text):
            structure_score += 0.2

        # Check for bullet points
        if re.search(r"[•\-\*]\s+\w+", text):
            structure_score += 0.2

        # Check for emphasis formatting
        if "**" in text or "*" in text:
            structure_score += 0.1

        # Check for variable placeholders
        if re.search(r"\{[^}]+\}", text):
            structure_score += 0.2

        return min(structure_score, 1.0)

    def _calculate_italian_tax_domain_score(self, text: str) -> float:
        """Calculate score for Italian tax domain relevance"""
        # Italian tax terminology
        tax_terms = [
            "iva",
            "irpef",
            "ires",
            "irap",
            "partita iva",
            "dichiarazione",
            "fattura",
            "regime forfettario",
            "detrazione",
            "deduzione",
            "contributi",
            "codice fiscale",
            "f24",
            "modello 730",
            "commercialista",
            "consulente",
        ]

        text_lower = text.lower()
        domain_terms_found = sum(1 for term in tax_terms if term in text_lower)

        domain_score = min(domain_terms_found / 5.0, 1.0)  # Max 5 terms for full score

        # Check for Italian professional language
        professional_phrases = [
            "ai sensi dell'art",
            "in base alla normativa",
            "secondo quanto previsto",
            "come stabilito dal",
            "ai fini dell'applicazione",
        ]

        professional_bonus = 0.2 if any(phrase in text_lower for phrase in professional_phrases) else 0.0

        return min(domain_score + professional_bonus, 1.0)

    async def _get_template(self, template_id: str) -> PromptTemplate | None:
        """Retrieve template by ID with caching"""
        try:
            # Check cache first
            if self.cache:
                cache_key = f"prompt_template:{template_id}"
                cached_template = await self.cache.get(cache_key)
                if cached_template:
                    return cached_template

            # Query database
            template_uuid = UUID(template_id)
            query = select(PromptTemplate).where(PromptTemplate.id == template_uuid)

            result = await self.db.execute(query)
            template = result.scalar_one_or_none()

            # Cache if found
            if template and self.cache:
                cache_key = f"prompt_template:{template_id}"
                await self.cache.setex(cache_key, self.template_cache_ttl, template)

            return template

        except Exception as e:
            logger.error(f"Failed to retrieve template {template_id}: {e}")
            return None

    async def _process_template(self, template: PromptTemplate, context_data: dict[str, Any]) -> str:
        """Process template with context data substitution"""
        processed_text = template.template_text

        # Substitute variables
        for variable in template.variables:
            placeholder = f"{{{variable}}}"
            value = context_data.get(variable, f"[{variable}]")  # Default to placeholder if not provided
            processed_text = processed_text.replace(placeholder, str(value))

        # Apply context-specific enhancements
        processed_text = self._apply_contextual_enhancements(processed_text, context_data)

        return processed_text

    def _apply_contextual_enhancements(self, text: str, context_data: dict[str, Any]) -> str:
        """Apply context-specific enhancements to the prompt"""
        enhanced_text = text

        # Add complexity-based instructions
        complexity = context_data.get("complexity_level", "medium")
        if complexity == "advanced":
            enhanced_text += (
                "\n\n**Nota:** Fornire un'analisi tecnica dettagliata con riferimenti normativi specifici."
            )
        elif complexity == "basic":
            enhanced_text += (
                "\n\n**Nota:** Fornire una spiegazione semplice e comprensibile, evitando eccessivi tecnicismi."
            )

        # Add user profile adaptations
        user_profile = context_data.get("user_profile", "")
        if "commercialista" in user_profile.lower():
            enhanced_text += "\n\n**Contesto:** Risposta per professionista del settore fiscale."
        elif "imprenditore" in user_profile.lower():
            enhanced_text += "\n\n**Contesto:** Risposta per imprenditore, includere aspetti pratici applicativi."

        return enhanced_text

    def _apply_italian_tax_enhancements(self, prompt: str, context_data: dict[str, Any]) -> str:
        """Apply Italian tax domain-specific enhancements"""
        enhanced_prompt = prompt

        # Add regulatory context if not present
        if "normativa" not in enhanced_prompt.lower() and "decreto" not in enhanced_prompt.lower():
            enhanced_prompt += "\n\n**Riferimenti Normativi:** Indicare la normativa di riferimento applicabile."

        # Add practical application note
        if context_data.get("include_practical_examples", True):
            enhanced_prompt += "\n\n**Esempi Pratici:** Quando possibile, fornire esempi concreti di applicazione."

        # Add disclaimer for professional advice
        enhanced_prompt += "\n\n---\n*Questa risposta ha carattere informativo. Per situazioni specifiche consultare un commercialista qualificato.*"

        return enhanced_prompt

    async def _update_template_usage(self, template: PromptTemplate) -> None:
        """Update template usage statistics"""
        try:
            template.usage_count += 1
            template.updated_at = datetime.utcnow()
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update template usage: {e}")

    async def _analyze_feedback_patterns(self, feedback_data: list[dict[str, Any]]) -> list[str]:
        """Analyze expert feedback to identify improvement patterns"""
        improvement_suggestions = []

        # Analyze common feedback themes
        feedback_text = " ".join(
            [
                fb.get("expert_answer", "") + " " + " ".join(fb.get("improvement_suggestions", []))
                for fb in feedback_data
            ]
        )

        # Pattern analysis
        if "normativa" in feedback_text.lower() and (
            "obsoleta" in feedback_text.lower() or "aggiorna" in feedback_text.lower()
        ):
            improvement_suggestions.append("Update regulatory references to current legislation")

        if "esempio" in feedback_text.lower() or "pratico" in feedback_text.lower():
            improvement_suggestions.append("Add practical examples and case studies")

        if "generico" in feedback_text.lower() or "specifico" in feedback_text.lower():
            improvement_suggestions.append("Increase specificity and reduce generic statements")

        if "calcolo" in feedback_text.lower() and "errore" in feedback_text.lower():
            improvement_suggestions.append("Review and verify calculation methods")

        return improvement_suggestions

    async def _generate_improved_template(
        self, original_template: str, suggestions: list[str], performance_metrics: dict[str, Any]
    ) -> str:
        """Generate improved template based on suggestions and metrics"""
        improved_template = original_template

        # Apply improvements based on suggestions
        for suggestion in suggestions:
            if "regulatory references" in suggestion.lower():
                if "**Normativa:" not in improved_template:
                    improved_template = improved_template.replace(
                        "**Ragionamento Strutturato:**",
                        "**Normativa di Riferimento:** {regulatory_references}\n\n**Ragionamento Strutturato:**",
                    )

            elif "practical examples" in suggestion.lower():
                if "**Esempi" not in improved_template:
                    improved_template += "\n\n**Esempi Pratici:** {practical_examples}"

            elif "increase specificity" in suggestion.lower():
                # Add specificity prompts
                improved_template = improved_template.replace(
                    "**Risposta Finale:**", "**Risposta Specifica e Dettagliata:**"
                )

        # Add performance-based improvements
        accuracy_score = performance_metrics.get("accuracy_score", 0.8)
        if accuracy_score < 0.75:
            improved_template += (
                "\n\n**Verifica:** Controllare attentamente tutti i riferimenti normativi e i calcoli."
            )

        return improved_template

    def _initialize_base_templates(self) -> dict[str, str]:
        """Initialize base templates for Italian tax domain"""
        return {
            "structured_reasoning": """
## Analisi del Quesito Fiscale

**Domanda del Cliente:** {query}

**Contesto:** {context}

**Ragionamento Strutturato:**
1. **Identificazione del Problema:** {problem_identification}
2. **Normativa Applicabile:** {applicable_regulations}
3. **Interpretazione e Analisi:** {interpretation}
4. **Calcoli e Verifiche:** {calculations}
5. **Conclusioni:** {conclusions}

**Risposta Finale:** {final_answer}

**Fonti e Riferimenti:** {sources}
            """,
            "quick_answer": """
**Domanda:** {query}

**Risposta Diretta:** {direct_answer}

**Motivazione:** {rationale}

**Riferimenti:** {references}
            """,
            "complex_analysis": """
# Analisi Fiscale Complessa

## Quesito
{query}

## Analisi Preliminare
{preliminary_analysis}

## Normativa di Riferimento
{regulatory_framework}

## Casistica e Precedenti
{case_studies}

## Interpretazione Tecnica
{technical_interpretation}

## Conclusioni e Raccomandazioni
{conclusions_recommendations}

## Documenti da Consultare
{additional_resources}
            """,
        }

    async def get_template_analytics(self, template_id: str | None = None, days: int = 30) -> dict[str, Any]:
        """Get analytics for template performance"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Build query
            query = select(
                PromptTemplate.id,
                PromptTemplate.name,
                PromptTemplate.usage_count,
                PromptTemplate.success_rate,
                PromptTemplate.overall_quality_score,
                PromptTemplate.created_at,
            ).where(PromptTemplate.created_at >= start_date)

            if template_id:
                query = query.where(PromptTemplate.id == UUID(template_id))

            result = await self.db.execute(query)
            templates = result.all()

            # Calculate analytics
            analytics = {
                "period_days": days,
                "total_templates": len(templates),
                "total_usage": sum(t.usage_count for t in templates),
                "avg_quality_score": sum(t.overall_quality_score for t in templates) / len(templates)
                if templates
                else 0,
                "avg_success_rate": sum(t.success_rate for t in templates) / len(templates) if templates else 0,
                "template_details": [],
            }

            for template in templates:
                analytics["template_details"].append(
                    {
                        "id": str(template.id),
                        "name": template.name,
                        "usage_count": template.usage_count,
                        "success_rate": template.success_rate,
                        "quality_score": template.overall_quality_score,
                    }
                )

            return analytics

        except Exception as e:
            logger.error(f"Failed to get template analytics: {e}")
            return {"error": str(e)}

    def get_statistics(self) -> dict[str, Any]:
        """Get current service statistics"""
        return {
            "session_stats": self.stats,
            "quality_thresholds": {"minimum": self.min_quality_score, "target": self.target_quality_score},
            "base_templates": list(self.base_templates.keys()),
            "performance_metrics": {
                "templates_per_improvement": self.stats["improvements_applied"]
                / max(self.stats["templates_created"], 1),
                "avg_quality_achieved": self.stats["avg_quality_score"],
            },
        }
