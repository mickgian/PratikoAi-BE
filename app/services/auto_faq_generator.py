"""Automated FAQ Generator Service.

This service generates high-quality FAQ entries from query patterns using
LLMs with quality validation and cost optimization.
"""

import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.faq_automation import FAQ_AUTOMATION_CONFIG, FAQCandidate, GeneratedFAQ, estimate_generation_cost
from app.services.cache import CacheService
from app.services.faq_quality_validator import FAQQualityValidator
from app.services.llm_service import LLMService

# Custom Exceptions


class QualityValidationError(Exception):
    """Raised when FAQ quality validation fails"""

    pass


class GenerationFailedError(Exception):
    """Raised when FAQ generation fails"""

    pass


class AutomatedFAQGenerator:
    """Generates high-quality FAQs from query patterns using LLMs.

    Uses a tiered approach: cheap LLM (GPT-3.5) first, expensive LLM (GPT-4)
    if quality is insufficient. Includes regulatory reference extraction
    and Italian language validation.
    """

    def __init__(
        self,
        llm_service: LLMService,
        quality_validator: FAQQualityValidator,
        db: AsyncSession,
        cache_service: CacheService | None = None,
    ):
        self.llm = llm_service
        self.validator = quality_validator
        self.db = db
        self.cache = cache_service

        # Configuration
        config = FAQ_AUTOMATION_CONFIG["generation"]
        self.quality_threshold = config["quality_threshold"]
        self.auto_approve_threshold = config["auto_approve_threshold"]
        self.max_generation_attempts = config["max_generation_attempts"]
        self.cheap_model = config["cheap_model"]
        self.expensive_model = config["expensive_model"]
        self.max_tokens = config["max_tokens"]

    async def generate_faq_from_candidate(self, candidate: FAQCandidate) -> GeneratedFAQ:
        """Generate high-quality FAQ from a candidate.

        Args:
            candidate: FAQ candidate with query cluster data

        Returns:
            Generated FAQ with quality validation

        Raises:
            GenerationFailedError: If generation fails after all attempts
            QualityValidationError: If quality validation fails
        """
        logger.info(f"Generating FAQ for candidate {candidate.id}")

        try:
            # Build generation prompt
            prompt = self._build_generation_prompt(candidate)

            # Track generation attempts
            generation_metadata = {
                "candidate_id": str(candidate.id),
                "generation_date": datetime.utcnow().isoformat(),
                "attempts": [],
                "total_cost_cents": 0,
                "total_tokens": 0,
            }

            # First attempt with cheap model
            logger.info("Attempting FAQ generation with cheap model")

            faq_data, attempt_metadata = await self._generate_with_model(prompt, self.cheap_model, attempt_number=1)

            generation_metadata["attempts"].append(attempt_metadata)
            generation_metadata["total_cost_cents"] += attempt_metadata["cost_cents"]
            generation_metadata["total_tokens"] += attempt_metadata["tokens"]

            # Validate quality
            quality_score = await self.validator.validate_faq(
                question=faq_data["question"],
                answer=faq_data["answer"],
                original_response=candidate.best_response_content,
            )

            # If quality is insufficient, try with expensive model
            if quality_score < self.quality_threshold:
                logger.info(f"Quality score {quality_score} below threshold, retrying with expensive model")

                faq_data, attempt_metadata = await self._generate_with_model(
                    prompt, self.expensive_model, attempt_number=2
                )

                generation_metadata["attempts"].append(attempt_metadata)
                generation_metadata["total_cost_cents"] += attempt_metadata["cost_cents"]
                generation_metadata["total_tokens"] += attempt_metadata["tokens"]

                # Re-validate with new content
                quality_score = await self.validator.validate_faq(
                    question=faq_data["question"],
                    answer=faq_data["answer"],
                    original_response=candidate.best_response_content,
                )

            # Check final quality
            if quality_score < self.quality_threshold:
                raise QualityValidationError(
                    f"Final quality score {quality_score} below threshold {self.quality_threshold}"
                )

            # Extract regulatory references
            regulatory_refs = await self._extract_regulatory_references(candidate.best_response_content)

            # Determine approval status
            approval_status = "auto_approved" if quality_score >= self.auto_approve_threshold else "pending_review"

            # Create generated FAQ
            generated_faq = GeneratedFAQ(
                id=uuid4(),
                candidate_id=candidate.id,
                question=faq_data["question"],
                answer=faq_data["answer"],
                category=faq_data.get("category", candidate.suggested_category),
                tags=self._merge_tags(candidate.suggested_tags, faq_data.get("additional_tags", [])),
                quality_score=Decimal(str(quality_score)),
                regulatory_refs=regulatory_refs,
                generation_model=generation_metadata["attempts"][-1]["model_used"],
                generation_cost_cents=generation_metadata["total_cost_cents"],
                generation_tokens=generation_metadata["total_tokens"],
                estimated_monthly_savings=candidate.estimated_monthly_savings,
                source_query_count=candidate.frequency,
                approval_status=approval_status,
                generation_metadata=generation_metadata,
                auto_generated=True,
            )

            logger.info(
                f"Successfully generated FAQ: quality={quality_score}, "
                f"cost=€{generation_metadata['total_cost_cents'] / 100:.4f}, "
                f"status={approval_status}"
            )

            return generated_faq

        except Exception as e:
            logger.error(f"FAQ generation failed for candidate {candidate.id}: {e}")
            if isinstance(e, QualityValidationError | GenerationFailedError):
                raise
            raise GenerationFailedError(f"Generation failed: {e}")

    def _build_generation_prompt(self, candidate: FAQCandidate) -> str:
        """Build comprehensive prompt for FAQ generation"""
        # Format query variations for prompt
        variations_text = "\n".join([f"- {var}" for var in candidate.query_cluster.query_variations[:10]])

        # Build context from best response
        context_info = ""
        if len(candidate.best_response_content) > 1000:
            context_info = f"RISPOSTA COMPLETA (da riassumere):\n{candidate.best_response_content[:1000]}...\n\n"
        else:
            context_info = f"RISPOSTA DI ALTA QUALITÀ:\n{candidate.best_response_content}\n\n"

        # Category and tags context
        tags_text = ", ".join(candidate.suggested_tags) if candidate.suggested_tags else "da determinare"

        prompt = f"""Crea una FAQ professionale per commercialisti italiani basata su queste informazioni:

DOMANDE FREQUENTI DEGLI UTENTI:
{variations_text}

{context_info}CATEGORIA SUGGERITA: {candidate.suggested_category or "Generale"}
TAG ATTUALI: {tags_text}

GENERA UNA FAQ SEGUENDO QUESTO FORMATO JSON:
{{
    "question": "Domanda chiara e diretta che cattura l'intento comune di tutte le variazioni",
    "answer": "Risposta completa ma concisa (massimo 200 parole) che mantiene tutte le informazioni importanti",
    "category": "Categoria appropriata (IVA, IRPEF, Detrazioni, Fatturazione, Contributi, etc.)",
    "additional_tags": ["tag1", "tag2", "tag3"]
}}

REQUISITI SPECIFICI:
1. La domanda deve essere in italiano professionale e coprire tutte le variazioni mostrate
2. La risposta deve mantenere TUTTI i riferimenti normativi presenti nella risposta originale
3. Usa un tono professionale ma accessibile per commercialisti
4. Includi esempi pratici se presenti nella risposta originale
5. La risposta deve essere autonoma e completa (non riferimenti esterni come "vedi sopra")
6. Mantieni la precisione tecnica e i dettagli normativi
7. Se ci sono calcoli o formule, mantienili chiari e precisi
8. Aggiungi tag rilevanti per categorizzazione e ricerca

GENERA SOLO IL JSON, SENZA COMMENTI O TESTO AGGIUNTIVO."""

        return prompt

    async def _generate_with_model(
        self, prompt: str, model: str, attempt_number: int
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate FAQ content with specified model"""
        start_time = datetime.utcnow()

        try:
            # Estimate input tokens (rough estimate)
            input_tokens = len(prompt.split()) * 1.3  # Rough token estimation

            # Generate content
            if model == self.expensive_model:
                response = await self.llm.complete_expensive(
                    prompt,
                    max_tokens=self.max_tokens,
                    temperature=0.3,  # Lower temperature for consistency
                )
            else:
                response = await self.llm.complete_cheap(prompt, max_tokens=self.max_tokens, temperature=0.3)

            # Parse JSON response
            faq_data = self._parse_faq_response(response)

            # Estimate output tokens and cost
            output_tokens = len(response.split()) * 1.3
            estimated_cost = estimate_generation_cost(model, int(input_tokens), int(output_tokens))

            # Generation metadata for this attempt
            attempt_metadata = {
                "attempt_number": attempt_number,
                "model_used": model,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "cost_cents": int(estimated_cost * 100),
                "tokens": int(input_tokens + output_tokens),
                "generation_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "timestamp": start_time.isoformat(),
            }

            return faq_data, attempt_metadata

        except Exception as e:
            logger.error(f"Model generation failed (attempt {attempt_number}, model {model}): {e}")
            raise GenerationFailedError(f"Model generation failed: {e}")

    def _parse_faq_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response to extract FAQ data"""
        try:
            # Clean response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # Parse JSON
            faq_data = json.loads(cleaned_response)

            # Validate required fields
            required_fields = ["question", "answer", "category"]
            for field in required_fields:
                if field not in faq_data or not faq_data[field]:
                    raise ValueError(f"Missing required field: {field}")

            # Clean and validate content
            faq_data["question"] = self._clean_question_text(faq_data["question"])
            faq_data["answer"] = self._clean_answer_text(faq_data["answer"])
            faq_data["category"] = self._clean_category_text(faq_data["category"])

            # Ensure additional_tags is a list
            if "additional_tags" not in faq_data:
                faq_data["additional_tags"] = []
            elif isinstance(faq_data["additional_tags"], str):
                faq_data["additional_tags"] = [faq_data["additional_tags"]]

            return faq_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response}")
            raise GenerationFailedError(f"Invalid JSON response: {e}")

        except Exception as e:
            logger.error(f"Failed to parse FAQ response: {e}")
            raise GenerationFailedError(f"Response parsing failed: {e}")

    def _clean_question_text(self, question: str) -> str:
        """Clean and validate question text"""
        question = question.strip()

        # Ensure it ends with a question mark
        if not question.endswith("?"):
            question += "?"

        # Capitalize first letter
        if question:
            question = question[0].upper() + question[1:]

        # Remove excessive whitespace
        question = re.sub(r"\s+", " ", question)

        return question

    def _clean_answer_text(self, answer: str) -> str:
        """Clean and validate answer text"""
        answer = answer.strip()

        # Remove excessive whitespace and normalize
        answer = re.sub(r"\s+", " ", answer)
        answer = re.sub(r"\n\s*\n", "\n\n", answer)  # Normalize paragraph breaks

        # Ensure proper sentence ending
        if answer and not answer.endswith((".", "!", "?")):
            answer += "."

        return answer

    def _clean_category_text(self, category: str) -> str:
        """Clean and validate category text"""
        category = category.strip()

        # Capitalize properly (title case for Italian)
        category = category.title()

        # Handle common Italian category names
        category_mappings = {
            "Iva": "IVA",
            "Irpef": "IRPEF",
            "Partita Iva": "Partita IVA",
            "F24": "F24",
            "Inps": "INPS",
        }

        for old, new in category_mappings.items():
            if category == old:
                category = new
                break

        return category

    def _merge_tags(self, original_tags: list[str], additional_tags: list[str]) -> list[str]:
        """Merge original and additional tags, removing duplicates"""
        all_tags = []

        # Add original tags
        if original_tags:
            all_tags.extend(original_tags)

        # Add additional tags if not already present
        if additional_tags:
            for tag in additional_tags:
                tag_lower = tag.lower().strip()
                if tag_lower and tag_lower not in [t.lower() for t in all_tags]:
                    all_tags.append(tag.strip())

        # Remove empty tags and limit total
        clean_tags = [tag for tag in all_tags if tag.strip()]

        # Limit to 10 tags maximum
        return clean_tags[:10]

    async def _extract_regulatory_references(self, response_content: str) -> list[str]:
        """Extract regulatory references from response content"""
        try:
            # Common Italian regulatory reference patterns
            patterns = [
                r"D\.Lgs\.?\s*\d+/\d+",  # Decreto Legislativo
                r"D\.P\.R\.?\s*\d+/\d+",  # Decreto del Presidente della Repubblica
                r"L\.?\s*\d+/\d+",  # Legge
                r"Art\.?\s*\d+[\w\s-]*(?:TUIR|DPR|Codice|Costituzione)",  # Articoli
                r"Circolare\s*\d+/[A-Z]/\d+",  # Circolari
                r"Risoluzione\s*\d+/[A-Z]/\d+",  # Risoluzioni
                r"TUIR",  # Testo Unico Imposte sui Redditi
                r"Codice Civile",
                r"Costituzione",
                r"Decreto\s+[\w\s]*\d+/\d+",  # Generic Decreto
                r"Regolamento\s+[\w\s]*\d+/\d+",  # Regolamenti
            ]

            references = set()

            for pattern in patterns:
                matches = re.finditer(pattern, response_content, re.IGNORECASE)
                for match in matches:
                    ref = match.group().strip()
                    # Clean up the reference
                    ref = re.sub(r"\s+", " ", ref)
                    references.add(ref)

            # Convert to list and sort
            ref_list = sorted(references)

            # Limit to reasonable number
            return ref_list[:10]

        except Exception as e:
            logger.error(f"Error extracting regulatory references: {e}")
            return []

    async def batch_generate_faqs(self, candidates: list[FAQCandidate], max_concurrent: int = 3) -> dict[str, Any]:
        """Generate FAQs for multiple candidates in batch.

        Args:
            candidates: List of FAQ candidates
            max_concurrent: Maximum concurrent generations

        Returns:
            Batch generation results with statistics
        """
        import asyncio

        logger.info(f"Starting batch FAQ generation for {len(candidates)} candidates")

        results = {
            "total_candidates": len(candidates),
            "successful": 0,
            "failed": 0,
            "auto_approved": 0,
            "pending_review": 0,
            "total_cost_cents": 0,
            "generated_faqs": [],
            "errors": [],
        }

        # Process in batches to avoid overwhelming the LLM service
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_single(candidate: FAQCandidate) -> GeneratedFAQ | None:
            async with semaphore:
                try:
                    faq = await self.generate_faq_from_candidate(candidate)
                    return faq
                except Exception as e:
                    logger.error(f"Batch generation failed for candidate {candidate.id}: {e}")
                    results["errors"].append({"candidate_id": str(candidate.id), "error": str(e)})
                    return None

        # Execute all generations
        tasks = [generate_single(candidate) for candidate in candidates]
        generated_faqs = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for _i, result in enumerate(generated_faqs):
            if isinstance(result, Exception) or result is None:
                results["failed"] += 1
            else:
                results["successful"] += 1
                results["total_cost_cents"] += result.generation_cost_cents
                results["generated_faqs"].append(result.to_dict())

                if result.approval_status == "auto_approved":
                    results["auto_approved"] += 1
                else:
                    results["pending_review"] += 1

        # Calculate statistics
        results["success_rate"] = (
            results["successful"] / results["total_candidates"] if results["total_candidates"] > 0 else 0
        )
        results["avg_cost_cents"] = (
            results["total_cost_cents"] / results["successful"] if results["successful"] > 0 else 0
        )
        results["completion_time"] = datetime.utcnow().isoformat()

        logger.info(
            f"Batch generation completed: {results['successful']}/{results['total_candidates']} successful, "
            f"cost=€{results['total_cost_cents'] / 100:.2f}"
        )

        return results

    async def regenerate_faq_for_rss_update(
        self, existing_faq: GeneratedFAQ, rss_update_context: dict[str, Any]
    ) -> GeneratedFAQ:
        """Regenerate FAQ content based on RSS update information.

        Args:
            existing_faq: Current FAQ to update
            rss_update_context: RSS update information

        Returns:
            Updated FAQ with new content
        """
        logger.info(f"Regenerating FAQ {existing_faq.id} for RSS update")

        try:
            # Build update-specific prompt
            prompt = self._build_update_prompt(existing_faq, rss_update_context)

            # Use expensive model for accuracy in updates
            faq_data, attempt_metadata = await self._generate_with_model(
                prompt, self.expensive_model, attempt_number=1
            )

            # Validate updated content
            quality_score = await self.validator.validate_faq(
                question=faq_data["question"],
                answer=faq_data["answer"],
                original_response=existing_faq.answer,  # Compare to existing
            )

            if quality_score < self.quality_threshold:
                raise QualityValidationError(f"Updated FAQ quality {quality_score} below threshold")

            # Update FAQ with new content
            existing_faq.answer = faq_data["answer"]
            existing_faq.quality_score = Decimal(str(quality_score))
            existing_faq.updated_at = datetime.utcnow()
            existing_faq.generation_cost_cents += attempt_metadata["cost_cents"]

            # Add update metadata
            update_metadata = existing_faq.generation_metadata.copy() if existing_faq.generation_metadata else {}
            update_metadata["rss_updates"] = update_metadata.get("rss_updates", [])
            update_metadata["rss_updates"].append(
                {
                    "update_date": datetime.utcnow().isoformat(),
                    "rss_source": rss_update_context.get("source"),
                    "rss_title": rss_update_context.get("title"),
                    "change_reason": rss_update_context.get("change_reason"),
                    "quality_score": quality_score,
                    "cost_cents": attempt_metadata["cost_cents"],
                }
            )
            existing_faq.generation_metadata = update_metadata

            logger.info(f"Successfully regenerated FAQ {existing_faq.id}")

            return existing_faq

        except Exception as e:
            logger.error(f"FAQ regeneration failed for {existing_faq.id}: {e}")
            raise GenerationFailedError(f"Regeneration failed: {e}")

    def _build_update_prompt(self, existing_faq: GeneratedFAQ, rss_update_context: dict[str, Any]) -> str:
        """Build prompt for updating FAQ based on RSS changes"""
        prompt = f"""Aggiorna questa FAQ a causa di una nuova normativa:

FAQ ATTUALE:
Domanda: {existing_faq.question}
Risposta: {existing_faq.answer}

NUOVO AGGIORNAMENTO NORMATIVO:
Fonte: {rss_update_context.get("source", "N/A")}
Titolo: {rss_update_context.get("title", "N/A")}
Contenuto: {rss_update_context.get("summary", "N/A")}
Data: {rss_update_context.get("published_date", "N/A")}

GENERA UNA VERSIONE AGGIORNATA:
{{
    "question": "{existing_faq.question}",
    "answer": "Risposta aggiornata che incorpora le nuove informazioni mantenendo chiarezza e completezza",
    "category": "{existing_faq.category}",
    "change_note": "Descrizione specifica di cosa è cambiato e perché"
}}

REQUISITI:
1. Mantieni la stessa domanda
2. Aggiorna solo le parti della risposta che sono cambiate
3. Indica chiaramente cosa è nuovo o modificato
4. Mantieni tutti i riferimenti normativi ancora validi
5. Aggiungi nuovi riferimenti normativi se applicabili
6. Mantieni il tono professionale
7. La risposta deve rimanere autonoma e completa

GENERA SOLO IL JSON."""

        return prompt
