"""FAQ Quality Validator Service.

This service validates the quality of generated FAQs using multiple metrics
including semantic similarity, completeness, professional language, and
regulatory compliance for Italian tax/accounting context.
"""

import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.config import settings
from app.core.logging import logger
from app.models.faq_automation import FAQ_AUTOMATION_CONFIG
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService

# Custom Exceptions


class ValidationError(Exception):
    """Raised when FAQ validation fails"""

    pass


class FAQQualityValidator:
    """Validates the quality of generated FAQs using semantic analysis,
    completeness checks, and Italian professional language validation.

    Uses a multi-criteria scoring system to ensure FAQ quality meets
    professional standards for Italian tax and accounting professionals.
    """

    def __init__(self, llm_service: LLMService, embedding_service: EmbeddingService):
        self.llm = llm_service
        self.embeddings = embedding_service

        # Configuration
        config = FAQ_AUTOMATION_CONFIG["generation"]
        self.quality_threshold = config["quality_threshold"]
        self.auto_approve_threshold = config["auto_approve_threshold"]

        # Quality scoring weights
        self.scoring_weights = {
            "semantic_similarity": 0.25,
            "completeness": 0.20,
            "professional_language": 0.20,
            "regulatory_compliance": 0.15,
            "clarity": 0.10,
            "accuracy": 0.10,
        }

    async def validate_faq(
        self,
        question: str,
        answer: str,
        original_response: str,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> Decimal:
        """Validate FAQ quality using comprehensive scoring.

        Args:
            question: Generated FAQ question
            answer: Generated FAQ answer
            original_response: Original LLM response for comparison
            category: FAQ category for context validation
            tags: FAQ tags for relevance checking

        Returns:
            Quality score between 0.0 and 1.0

        Raises:
            ValidationError: If validation process fails
        """
        logger.info("Starting FAQ quality validation")

        try:
            # Initialize quality scores
            quality_scores = {}

            # 1. Semantic similarity with original response
            quality_scores["semantic_similarity"] = await self._check_semantic_similarity(answer, original_response)

            # 2. Content completeness
            quality_scores["completeness"] = await self._check_completeness(question, answer, original_response)

            # 3. Professional language quality
            quality_scores["professional_language"] = await self._check_professional_language(question, answer)

            # 4. Regulatory compliance (Italian tax context)
            quality_scores["regulatory_compliance"] = await self._check_regulatory_compliance(answer, category, tags)

            # 5. Clarity and readability
            quality_scores["clarity"] = await self._check_clarity(question, answer)

            # 6. Technical accuracy
            quality_scores["accuracy"] = await self._check_accuracy(answer, original_response)

            # Calculate weighted final score
            final_score = self._calculate_weighted_score(quality_scores)

            logger.info(f"FAQ quality validation completed: {final_score:.3f} - Details: {quality_scores}")

            return final_score

        except Exception as e:
            logger.error(f"FAQ quality validation failed: {e}")
            raise ValidationError(f"Quality validation failed: {e}")

    async def _check_semantic_similarity(self, faq_answer: str, original_response: str) -> Decimal:
        """Check semantic similarity between FAQ answer and original response"""
        try:
            # Get embeddings for both texts
            faq_embedding = await self.embeddings.embed_text(faq_answer)
            original_embedding = await self.embeddings.embed_text(original_response)

            # Calculate cosine similarity
            similarity = self.embeddings.cosine_similarity(faq_embedding, original_embedding)

            # Convert to quality score (similarity should be high but not identical)
            if similarity >= 0.9:
                return Decimal("1.0")  # Very high similarity
            elif similarity >= 0.8:
                return Decimal("0.9")  # Good similarity
            elif similarity >= 0.7:
                return Decimal("0.7")  # Acceptable similarity
            elif similarity >= 0.6:
                return Decimal("0.5")  # Low similarity
            else:
                return Decimal("0.2")  # Poor similarity

        except Exception as e:
            logger.error(f"Semantic similarity check failed: {e}")
            return Decimal("0.5")  # Default moderate score

    async def _check_completeness(self, question: str, answer: str, original_response: str) -> Decimal:
        """Check if FAQ answer covers all important points from original"""
        try:
            # Use LLM to assess completeness
            prompt = f"""Valuta la completezza di questa risposta FAQ rispetto alla risposta originale.

DOMANDA FAQ: {question}

RISPOSTA FAQ: {answer}

RISPOSTA ORIGINALE COMPLETA: {original_response}

Assegna un punteggio da 0 a 10 dove:
- 10: La FAQ copre tutti i punti essenziali della risposta originale
- 8-9: La FAQ copre la maggior parte dei punti importanti
- 6-7: La FAQ copre i punti principali ma mancano alcuni dettagli
- 4-5: La FAQ copre solo parte delle informazioni importanti
- 0-3: La FAQ è incompleta o manca informazioni cruciali

Rispondi SOLO con il numero del punteggio (es: 8)."""

            response = await self.llm.complete_cheap(prompt, max_tokens=10, temperature=0.1)

            # Extract numeric score
            score_match = re.search(r"\b([0-9]|10)\b", response.strip())
            if score_match:
                score = int(score_match.group(1))
                return Decimal(str(score / 10.0))

            return Decimal("0.7")  # Default if parsing fails

        except Exception as e:
            logger.error(f"Completeness check failed: {e}")
            return Decimal("0.7")

    async def _check_professional_language(self, question: str, answer: str) -> Decimal:
        """Check professional language quality for Italian context"""
        try:
            score = Decimal("1.0")

            # Check question format
            if not question.strip().endswith("?"):
                score -= Decimal("0.1")

            # Check for professional Italian terms
            professional_indicators = [
                "calcolo",
                "calcolare",
                "imposta",
                "tassa",
                "aliquota",
                "dichiarazione",
                "detrazione",
                "deduzione",
                "normativa",
                "contributo",
                "fattura",
                "reddito",
                "regime",
            ]

            answer_lower = answer.lower()
            professional_count = sum(1 for term in professional_indicators if term in answer_lower)

            if professional_count >= 3:
                score += Decimal("0.0")  # Good professional language
            elif professional_count >= 1:
                score -= Decimal("0.1")  # Some professional terms
            else:
                score -= Decimal("0.2")  # Lacks professional terminology

            # Check for informal language (negative indicators)
            informal_terms = ["ciao", "ok", "ecco", "bene", "tipo", "roba"]
            informal_count = sum(1 for term in informal_terms if term in answer_lower)

            if informal_count > 0:
                score -= Decimal(str(informal_count * 0.1))

            # Check sentence structure
            sentences = answer.split(".")
            if len(sentences) < 2:
                score -= Decimal("0.1")  # Too short
            elif len(sentences) > 10:
                score -= Decimal("0.1")  # Too verbose

            return max(score, Decimal("0.0"))

        except Exception as e:
            logger.error(f"Professional language check failed: {e}")
            return Decimal("0.8")

    async def _check_regulatory_compliance(self, answer: str, category: str | None, tags: list[str] | None) -> Decimal:
        """Check regulatory compliance for Italian tax context"""
        try:
            score = Decimal("0.8")  # Base score

            # Check for regulatory references
            regulatory_patterns = [
                r"D\.Lgs\.?\s*\d+/\d+",  # Decreto Legislativo
                r"D\.P\.R\.?\s*\d+/\d+",  # DPR
                r"L\.?\s*\d+/\d+",  # Legge
                r"Art\.?\s*\d+",  # Articolo
                r"TUIR",  # Testo Unico
                r"Circolare\s*\d+",  # Circolari
                r"Risoluzione\s*\d+",  # Risoluzioni
            ]

            ref_count = 0
            for pattern in regulatory_patterns:
                if re.search(pattern, answer, re.IGNORECASE):
                    ref_count += 1

            if ref_count >= 2:
                score += Decimal("0.2")  # Multiple references
            elif ref_count >= 1:
                score += Decimal("0.1")  # Some references

            # Category-specific compliance checks
            if category:
                category_lower = category.lower()

                if "iva" in category_lower:
                    if any(term in answer.lower() for term in ["22%", "10%", "4%", "aliquota", "imposta"]):
                        score += Decimal("0.1")

                elif "irpef" in category_lower:
                    if any(term in answer.lower() for term in ["scaglioni", "aliquote", "reddito", "dichiarazione"]):
                        score += Decimal("0.1")

                elif "fattura" in category_lower:
                    if any(term in answer.lower() for term in ["sdi", "elettronica", "xml", "codice"]):
                        score += Decimal("0.1")

            # Check for disclaimers or professional advice recommendations
            disclaimer_terms = ["consulta", "professionista", "commercialista", "verifica", "specifica"]
            if any(term in answer.lower() for term in disclaimer_terms):
                score += Decimal("0.1")  # Good practice

            return min(score, Decimal("1.0"))

        except Exception as e:
            logger.error(f"Regulatory compliance check failed: {e}")
            return Decimal("0.8")

    async def _check_clarity(self, question: str, answer: str) -> Decimal:
        """Check clarity and readability of FAQ"""
        try:
            score = Decimal("0.8")  # Base score

            # Question clarity
            if len(question.split()) < 5:
                score -= Decimal("0.1")  # Too short
            elif len(question.split()) > 20:
                score -= Decimal("0.1")  # Too long

            # Answer structure
            answer_sentences = [s.strip() for s in answer.split(".") if s.strip()]

            if len(answer_sentences) < 2:
                score -= Decimal("0.2")  # Too brief
            elif len(answer_sentences) > 8:
                score -= Decimal("0.1")  # Too verbose

            # Check for examples or concrete information
            example_indicators = ["esempio", "ad esempio", "per esempio", "€", "%", "euro"]
            if any(indicator in answer.lower() for indicator in example_indicators):
                score += Decimal("0.2")  # Contains examples

            # Check for lists or structured information
            if any(marker in answer for marker in ["1.", "2.", "-", "•"]):
                score += Decimal("0.1")  # Well structured

            return min(score, Decimal("1.0"))

        except Exception as e:
            logger.error(f"Clarity check failed: {e}")
            return Decimal("0.8")

    async def _check_accuracy(self, faq_answer: str, original_response: str) -> Decimal:
        """Check technical accuracy against original response"""
        try:
            # Use LLM to check for factual consistency
            prompt = f"""Confronta queste due risposte per verificare la precisione tecnica.

RISPOSTA ORIGINALE: {original_response}

RISPOSTA FAQ: {faq_answer}

Verifica se la risposta FAQ mantiene la stessa precisione tecnica e informazioni corrette della risposta originale.

Assegna un punteggio da 0 a 10 dove:
- 10: Perfetta accuratezza tecnica, tutte le informazioni sono corrette
- 8-9: Accuratezza molto buona, informazioni principali corrette
- 6-7: Accuratezza accettabile, possibili semplificazioni minori
- 4-5: Alcune informazioni potrebbero essere imprecise
- 0-3: Significative imprecisioni o errori tecnici

Rispondi SOLO con il numero del punteggio (es: 9)."""

            response = await self.llm.complete_expensive(prompt, max_tokens=10, temperature=0.1)

            # Extract numeric score
            score_match = re.search(r"\b([0-9]|10)\b", response.strip())
            if score_match:
                score = int(score_match.group(1))
                return Decimal(str(score / 10.0))

            return Decimal("0.8")  # Default if parsing fails

        except Exception as e:
            logger.error(f"Accuracy check failed: {e}")
            return Decimal("0.8")

    def _calculate_weighted_score(self, quality_scores: dict[str, Decimal]) -> Decimal:
        """Calculate final weighted quality score"""
        try:
            total_score = Decimal("0")
            total_weight = Decimal("0")

            for criterion, score in quality_scores.items():
                if criterion in self.scoring_weights:
                    weight = Decimal(str(self.scoring_weights[criterion]))
                    total_score += score * weight
                    total_weight += weight

            if total_weight > 0:
                final_score = total_score / total_weight
            else:
                final_score = Decimal("0.5")  # Default fallback

            return min(max(final_score, Decimal("0")), Decimal("1"))

        except Exception as e:
            logger.error(f"Score calculation failed: {e}")
            return Decimal("0.5")

    async def get_quality_details(
        self,
        question: str,
        answer: str,
        original_response: str,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get detailed quality assessment breakdown.

        Returns:
            Detailed quality assessment with scores for each criterion
        """
        try:
            # Get individual quality scores
            quality_scores = {}

            quality_scores["semantic_similarity"] = await self._check_semantic_similarity(answer, original_response)
            quality_scores["completeness"] = await self._check_completeness(question, answer, original_response)
            quality_scores["professional_language"] = await self._check_professional_language(question, answer)
            quality_scores["regulatory_compliance"] = await self._check_regulatory_compliance(answer, category, tags)
            quality_scores["clarity"] = await self._check_clarity(question, answer)
            quality_scores["accuracy"] = await self._check_accuracy(answer, original_response)

            # Calculate final score
            final_score = self._calculate_weighted_score(quality_scores)

            # Generate recommendations
            recommendations = self._generate_recommendations(quality_scores)

            return {
                "final_score": float(final_score),
                "individual_scores": {criterion: float(score) for criterion, score in quality_scores.items()},
                "scoring_weights": self.scoring_weights,
                "meets_threshold": final_score >= Decimal(str(self.quality_threshold)),
                "auto_approve_eligible": final_score >= Decimal(str(self.auto_approve_threshold)),
                "recommendations": recommendations,
                "assessment_timestamp": "2024-01-15T10:30:00Z",  # Current timestamp in practice
            }

        except Exception as e:
            logger.error(f"Quality details generation failed: {e}")
            return {
                "error": str(e),
                "final_score": 0.0,
                "individual_scores": {},
                "meets_threshold": False,
                "auto_approve_eligible": False,
            }

    def _generate_recommendations(self, quality_scores: dict[str, Decimal]) -> list[str]:
        """Generate improvement recommendations based on quality scores"""
        recommendations = []

        for criterion, score in quality_scores.items():
            if score < Decimal("0.7"):
                if criterion == "semantic_similarity":
                    recommendations.append("Migliorare la coerenza semantica con la risposta originale")
                elif criterion == "completeness":
                    recommendations.append("Aggiungere informazioni mancanti dalla risposta originale")
                elif criterion == "professional_language":
                    recommendations.append("Utilizzare un linguaggio più professionale e terminologia tecnica")
                elif criterion == "regulatory_compliance":
                    recommendations.append("Aggiungere riferimenti normativi pertinenti")
                elif criterion == "clarity":
                    recommendations.append("Migliorare la chiarezza e struttura della risposta")
                elif criterion == "accuracy":
                    recommendations.append("Verificare la precisione tecnica delle informazioni")

        if not recommendations:
            recommendations.append("La qualità della FAQ è buona, nessun miglioramento necessario")

        return recommendations

    async def validate_batch(self, faq_items: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate multiple FAQs in batch.

        Args:
            faq_items: List of FAQ dictionaries to validate

        Returns:
            Batch validation results with statistics
        """
        results = {
            "total_items": len(faq_items),
            "passed": 0,
            "failed": 0,
            "auto_approve": 0,
            "validations": [],
            "avg_score": 0.0,
        }

        total_score = Decimal("0")

        for item in faq_items:
            try:
                score = await self.validate_faq(
                    question=item["question"],
                    answer=item["answer"],
                    original_response=item["original_response"],
                    category=item.get("category"),
                    tags=item.get("tags"),
                )

                passed = score >= Decimal(str(self.quality_threshold))
                auto_approve = score >= Decimal(str(self.auto_approve_threshold))

                results["validations"].append(
                    {
                        "question": item["question"][:100] + "..."
                        if len(item["question"]) > 100
                        else item["question"],
                        "score": float(score),
                        "passed": passed,
                        "auto_approve": auto_approve,
                    }
                )

                if passed:
                    results["passed"] += 1
                else:
                    results["failed"] += 1

                if auto_approve:
                    results["auto_approve"] += 1

                total_score += score

            except Exception as e:
                logger.error(f"Batch validation item failed: {e}")
                results["failed"] += 1
                results["validations"].append(
                    {
                        "question": item.get("question", "Unknown")[:100],
                        "score": 0.0,
                        "passed": False,
                        "auto_approve": False,
                        "error": str(e),
                    }
                )

        # Calculate statistics
        if results["total_items"] > 0:
            results["avg_score"] = float(total_score / results["total_items"])
            results["pass_rate"] = results["passed"] / results["total_items"]
            results["auto_approve_rate"] = results["auto_approve"] / results["total_items"]

        return results
