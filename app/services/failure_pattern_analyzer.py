"""Failure Pattern Analyzer for Quality Analysis System.

Identifies and analyzes patterns in system failures using machine learning clustering
and expert feedback analysis for Italian tax domain optimization.
"""

import asyncio
import hashlib
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.quality_analysis import (
    QUALITY_ANALYSIS_CONFIG,
    ExpertFeedback,
    FailurePattern,
    ItalianFeedbackCategory,
)
from app.services.cache import CacheService
from app.services.embedding_service import EmbeddingService


class FailureAnalysisError(Exception):
    """Custom exception for failure analysis operations"""

    pass


class FailurePatternAnalyzer:
    """Advanced failure pattern analyzer for quality improvement.

    Features:
    - DBSCAN clustering for semantic similarity analysis
    - Italian tax domain-specific pattern recognition
    - Failure categorization and impact assessment
    - Trend analysis and prediction
    - Expert feedback integration
    - Automated pattern discovery
    """

    def __init__(
        self, db: AsyncSession, embedding_service: EmbeddingService | None = None, cache: CacheService | None = None
    ):
        self.db = db
        self.embeddings = embedding_service
        self.cache = cache

        # Clustering parameters
        self.dbscan_eps = 0.25  # Clustering similarity threshold
        self.dbscan_min_samples = 3  # Minimum samples per cluster

        # Pattern detection thresholds
        self.min_pattern_frequency = QUALITY_ANALYSIS_CONFIG.MIN_PATTERN_FREQUENCY
        self.min_pattern_confidence = QUALITY_ANALYSIS_CONFIG.MIN_PATTERN_CONFIDENCE

        # Cache settings
        self.pattern_cache_ttl = 3600  # 1 hour
        self.analysis_cache_ttl = 1800  # 30 minutes

        # Italian tax domain patterns
        self.italian_tax_patterns = self._initialize_tax_patterns()

        # Statistics tracking
        self.stats = {
            "patterns_identified": 0,
            "clusters_created": 0,
            "failures_analyzed": 0,
            "avg_confidence_score": 0.0,
        }

    async def identify_patterns(self, feedback_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify failure patterns from expert feedback data.

        Args:
            feedback_data: List of feedback records with categories and content

        Returns:
            List of identified patterns with confidence scores and metadata
        """
        start_time = time.time()

        try:
            if not feedback_data:
                return []

            logger.info(f"Analyzing {len(feedback_data)} feedback records for patterns")

            # Categorize feedback by Italian categories
            categorized_feedback = self._categorize_feedback(feedback_data)

            # Cluster similar failures using embeddings
            clustered_patterns = await self._cluster_similar_failures(feedback_data)

            # Analyze category-based patterns
            category_patterns = self._analyze_category_patterns(categorized_feedback)

            # Combine and rank patterns
            all_patterns = clustered_patterns + category_patterns
            ranked_patterns = self._rank_patterns_by_impact(all_patterns)

            # Filter by confidence threshold
            filtered_patterns = [
                pattern for pattern in ranked_patterns if pattern["confidence"] >= self.min_pattern_confidence
            ]

            # Store significant patterns
            await self._store_patterns(filtered_patterns)

            # Update statistics
            self.stats["patterns_identified"] += len(filtered_patterns)
            self.stats["failures_analyzed"] += len(feedback_data)

            analysis_time = (time.time() - start_time) * 1000
            logger.info(
                f"Pattern analysis completed in {analysis_time:.1f}ms: {len(filtered_patterns)} patterns identified"
            )

            return filtered_patterns

        except Exception as e:
            logger.error(f"Pattern identification failed: {e}")
            raise FailureAnalysisError(f"Pattern analysis failed: {e}")

    async def categorize_failures(self, failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Categorize failures using Italian tax domain knowledge"""
        categorized_failures = []

        for failure in failures:
            feedback_text = failure.get("feedback", "").lower()
            query_text = failure.get("query", "").lower()
            category = failure.get("category", "")

            # Apply Italian categorization
            italian_category = self._determine_italian_category(feedback_text, query_text, category)

            # Determine subcategory
            subcategory = self._determine_subcategory(feedback_text, italian_category)

            # Calculate severity
            severity = self._calculate_failure_severity(failure)

            categorized_failure = {
                **failure,
                "italian_category": italian_category,
                "subcategory": subcategory,
                "severity": severity,
                "categorization_confidence": self._calculate_categorization_confidence(
                    feedback_text, italian_category
                ),
            }

            categorized_failures.append(categorized_failure)

        return categorized_failures

    async def cluster_similar_failures(self, failure_texts: list[str]) -> dict[str, Any]:
        """Cluster similar failures using DBSCAN and semantic embeddings"""
        try:
            if not failure_texts or len(failure_texts) < self.dbscan_min_samples:
                return {"clusters": {}, "noise": failure_texts}

            # Generate embeddings for semantic clustering
            embeddings_matrix = await self._get_embeddings_matrix(failure_texts)

            if embeddings_matrix is None:
                # Fallback to TF-IDF clustering
                embeddings_matrix = self._get_tfidf_matrix(failure_texts)

            # Apply DBSCAN clustering
            clustering = DBSCAN(eps=self.dbscan_eps, min_samples=self.dbscan_min_samples, metric="cosine").fit(
                embeddings_matrix
            )

            # Organize results
            clusters = defaultdict(list)
            noise = []

            for i, label in enumerate(clustering.labels_):
                if label == -1:  # Noise point
                    noise.append(failure_texts[i])
                else:
                    clusters[f"cluster_{label}"].append({"text": failure_texts[i], "index": i})

            # Calculate cluster characteristics
            cluster_analysis = {}
            for cluster_id, items in clusters.items():
                if len(items) >= self.dbscan_min_samples:
                    cluster_analysis[cluster_id] = {
                        "items": items,
                        "size": len(items),
                        "representative_text": self._get_cluster_representative(items),
                        "semantic_keywords": self._extract_semantic_keywords([item["text"] for item in items]),
                        "confidence": min(len(items) / 10.0, 1.0),  # Confidence based on cluster size
                    }

            self.stats["clusters_created"] += len(cluster_analysis)

            logger.info(f"Clustering completed: {len(cluster_analysis)} clusters, {len(noise)} noise points")

            return {
                "clusters": cluster_analysis,
                "noise": noise,
                "total_items": len(failure_texts),
                "clustering_params": {"eps": self.dbscan_eps, "min_samples": self.dbscan_min_samples},
            }

        except Exception as e:
            logger.error(f"Failure clustering failed: {e}")
            return {"clusters": {}, "noise": failure_texts, "error": str(e)}

    async def assess_failure_impact(self, failure_pattern: dict[str, Any]) -> float:
        """Assess the impact of a failure pattern on system performance"""
        try:
            # Base impact factors
            frequency = failure_pattern.get("frequency", 0)
            affected_queries = failure_pattern.get("affected_queries", 0)
            expert_corrections = failure_pattern.get("expert_corrections", 0)
            user_satisfaction_impact = failure_pattern.get("user_satisfaction_impact", 0.0)

            # Frequency impact (0-0.4)
            frequency_impact = min(frequency / 50.0, 0.4)  # Max impact at 50+ occurrences

            # Scale impact (0-0.3)
            scale_impact = min(affected_queries / 200.0, 0.3)  # Max impact at 200+ affected queries

            # Expert intervention impact (0-0.2)
            expert_impact = min(expert_corrections / 20.0, 0.2)  # Max impact at 20+ corrections

            # User satisfaction impact (0-0.1)
            satisfaction_impact = min(abs(user_satisfaction_impact), 0.1)

            # Total impact score
            impact_score = frequency_impact + scale_impact + expert_impact + satisfaction_impact

            # Apply domain-specific multipliers
            pattern_type = failure_pattern.get("pattern_type", "")
            if pattern_type == "regulatory_outdated":
                impact_score *= 1.2  # Regulatory issues are more critical
            elif pattern_type == "calculation_error":
                impact_score *= 1.3  # Calculation errors are very critical

            return min(impact_score, 1.0)

        except Exception as e:
            logger.error(f"Impact assessment failed: {e}")
            return 0.5  # Default medium impact

    def _categorize_feedback(self, feedback_data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Categorize feedback by Italian categories"""
        categorized = {category.value: [] for category in ItalianFeedbackCategory}
        categorized["unclassified"] = []

        for feedback in feedback_data:
            category = feedback.get("category", "unclassified")
            if category in categorized:
                categorized[category].append(feedback)
            else:
                categorized["unclassified"].append(feedback)

        return categorized

    async def _cluster_similar_failures(self, feedback_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Cluster similar failures semantically"""
        patterns = []

        # Extract texts for clustering
        texts = []
        for feedback in feedback_data:
            text = f"{feedback.get('query', '')} {feedback.get('feedback', '')}"
            texts.append(text.strip())

        if not texts:
            return patterns

        # Perform clustering
        clustering_result = await self.cluster_similar_failures(texts)

        # Convert clusters to patterns
        for _cluster_id, cluster_data in clustering_result["clusters"].items():
            if cluster_data["size"] >= self.dbscan_min_samples:
                pattern = {
                    "pattern_id": str(uuid4()),
                    "pattern_type": "semantic_cluster",
                    "pattern_name": f"Cluster-based Pattern: {cluster_data['representative_text'][:50]}...",
                    "frequency": cluster_data["size"],
                    "confidence": cluster_data["confidence"],
                    "categories": self._infer_categories_from_cluster(cluster_data["items"]),
                    "example_queries": [item["text"] for item in cluster_data["items"][:3]],
                    "semantic_keywords": cluster_data["semantic_keywords"],
                    "impact_score": await self.assess_failure_impact(
                        {
                            "frequency": cluster_data["size"],
                            "affected_queries": cluster_data["size"] * 5,  # Estimate
                            "pattern_type": "semantic_cluster",
                        }
                    ),
                }
                patterns.append(pattern)

        return patterns

    def _analyze_category_patterns(
        self, categorized_feedback: dict[str, list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Analyze patterns within each Italian category"""
        patterns = []

        for category, feedback_list in categorized_feedback.items():
            if category == "unclassified" or len(feedback_list) < self.min_pattern_frequency:
                continue

            # Analyze common themes within category
            category_texts = [f"{fb.get('query', '')} {fb.get('feedback', '')}" for fb in feedback_list]
            keywords = self._extract_semantic_keywords(category_texts)

            # Create category-based pattern
            pattern = {
                "pattern_id": str(uuid4()),
                "pattern_type": "category_based",
                "pattern_name": f"Frequent {category} Issues",
                "frequency": len(feedback_list),
                "confidence": min(len(feedback_list) / 20.0, 1.0),  # Higher confidence for more frequent issues
                "categories": [category],
                "example_queries": [fb.get("query", "") for fb in feedback_list[:3]],
                "semantic_keywords": keywords,
                "impact_score": len(feedback_list) / 100.0,  # Simple impact based on frequency
            }

            # Apply category-specific analysis
            if category == "normativa_obsoleta":
                pattern["pattern_name"] = "Outdated Regulatory References"
                pattern["impact_score"] *= 1.2  # Higher impact for regulatory issues
                pattern["regulatory_analysis"] = self._analyze_regulatory_patterns(feedback_list)

            elif category == "calcolo_sbagliato":
                pattern["pattern_name"] = "Calculation and Formula Errors"
                pattern["impact_score"] *= 1.3  # Higher impact for calculation errors
                pattern["calculation_analysis"] = self._analyze_calculation_patterns(feedback_list)

            patterns.append(pattern)

        return patterns

    def _rank_patterns_by_impact(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank patterns by their impact score"""
        # Calculate impact scores for patterns that don't have them
        for pattern in patterns:
            if "impact_score" not in pattern or pattern["impact_score"] == 0:
                pattern["impact_score"] = self._calculate_pattern_impact(pattern)

        # Sort by impact score (descending)
        ranked_patterns = sorted(patterns, key=lambda x: x.get("impact_score", 0), reverse=True)

        # Add ranking metadata
        for i, pattern in enumerate(ranked_patterns):
            pattern["rank"] = i + 1
            pattern["impact_tier"] = self._determine_impact_tier(pattern["impact_score"])

        return ranked_patterns

    def _calculate_pattern_impact(self, pattern: dict[str, Any]) -> float:
        """Calculate impact score for a pattern"""
        frequency = pattern.get("frequency", 0)
        confidence = pattern.get("confidence", 0.0)
        categories = pattern.get("categories", [])

        # Base impact from frequency and confidence
        base_impact = min(frequency / 20.0, 0.5) * confidence

        # Category-based impact multipliers
        category_multiplier = 1.0
        if "normativa_obsoleta" in categories:
            category_multiplier = 1.2
        elif "calcolo_sbagliato" in categories:
            category_multiplier = 1.3
        elif "interpretazione_errata" in categories:
            category_multiplier = 1.1

        return min(base_impact * category_multiplier, 1.0)

    def _determine_impact_tier(self, impact_score: float) -> str:
        """Determine impact tier based on score"""
        if impact_score >= 0.8:
            return "critical"
        elif impact_score >= 0.6:
            return "high"
        elif impact_score >= 0.4:
            return "medium"
        else:
            return "low"

    async def _store_patterns(self, patterns: list[dict[str, Any]]) -> None:
        """Store identified patterns in database"""
        try:
            for pattern_data in patterns:
                # Check if similar pattern already exists
                existing_pattern = await self._find_similar_pattern(pattern_data)

                if existing_pattern:
                    # Update existing pattern
                    existing_pattern.frequency_count += pattern_data["frequency"]
                    existing_pattern.last_occurrence = datetime.utcnow()
                    existing_pattern.confidence_score = max(
                        existing_pattern.confidence_score, pattern_data["confidence"]
                    )
                    existing_pattern.updated_at = datetime.utcnow()
                else:
                    # Create new pattern
                    new_pattern = FailurePattern(
                        pattern_name=pattern_data["pattern_name"],
                        pattern_type=pattern_data["pattern_type"],
                        description=pattern_data.get("description", pattern_data["pattern_name"]),
                        categories=pattern_data.get("categories", []),
                        example_queries=pattern_data.get("example_queries", []),
                        frequency_count=pattern_data["frequency"],
                        impact_score=pattern_data.get("impact_score", 0.0),
                        confidence_score=pattern_data["confidence"],
                        detection_algorithm="automated_clustering",
                        cluster_id=pattern_data.get("pattern_id"),
                        first_detected=datetime.utcnow(),
                        last_occurrence=datetime.utcnow(),
                    )
                    self.db.add(new_pattern)

            await self.db.commit()
            logger.info(f"Stored {len(patterns)} failure patterns")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to store patterns: {e}")

    async def _find_similar_pattern(self, pattern_data: dict[str, Any]) -> FailurePattern | None:
        """Find existing similar pattern in database"""
        try:
            # Look for patterns with similar name and type
            query = select(FailurePattern).where(
                and_(FailurePattern.pattern_type == pattern_data["pattern_type"], FailurePattern.is_resolved is False)
            )

            result = await self.db.execute(query)
            existing_patterns = result.scalars().all()

            # Check for semantic similarity
            for existing in existing_patterns:
                similarity = self._calculate_pattern_similarity(
                    pattern_data,
                    {
                        "pattern_name": existing.pattern_name,
                        "categories": existing.categories,
                        "example_queries": existing.example_queries,
                    },
                )

                if similarity > 0.8:  # High similarity threshold
                    return existing

            return None

        except Exception as e:
            logger.error(f"Error finding similar pattern: {e}")
            return None

    def _calculate_pattern_similarity(self, pattern1: dict[str, Any], pattern2: dict[str, Any]) -> float:
        """Calculate similarity between two patterns"""
        # Name similarity
        name1 = pattern1.get("pattern_name", "").lower()
        name2 = pattern2.get("pattern_name", "").lower()
        name_similarity = len(set(name1.split()) & set(name2.split())) / max(
            len(set(name1.split())), len(set(name2.split())), 1
        )

        # Category similarity
        cats1 = set(pattern1.get("categories", []))
        cats2 = set(pattern2.get("categories", []))
        category_similarity = len(cats1 & cats2) / max(len(cats1 | cats2), 1) if cats1 or cats2 else 0

        # Overall similarity (weighted)
        return name_similarity * 0.6 + category_similarity * 0.4

    async def _get_embeddings_matrix(self, texts: list[str]) -> np.ndarray | None:
        """Get embeddings matrix for text clustering"""
        if not self.embeddings:
            return None

        try:
            embeddings = []
            for text in texts:
                embedding = await self.embeddings.embed(text)
                if embedding:
                    embeddings.append(embedding)
                else:
                    return None  # If any embedding fails, fallback to TF-IDF

            return np.array(embeddings)

        except Exception as e:
            logger.warning(f"Embedding generation failed, falling back to TF-IDF: {e}")
            return None

    def _get_tfidf_matrix(self, texts: list[str]) -> np.ndarray:
        """Get TF-IDF matrix for text clustering fallback"""
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=[
                "di",
                "e",
                "il",
                "la",
                "un",
                "una",
                "in",
                "con",
                "per",
                "su",
                "da",
                "del",
                "della",
            ],  # Italian stop words
            ngram_range=(1, 2),
        )

        return vectorizer.fit_transform(texts).toarray()

    def _get_cluster_representative(self, cluster_items: list[dict[str, str]]) -> str:
        """Get representative text for a cluster"""
        if not cluster_items:
            return ""

        # Use the most common words approach
        all_words = []
        for item in cluster_items:
            words = item["text"].lower().split()
            all_words.extend(words)

        # Get most common words
        word_counts = Counter(all_words)
        common_words = [word for word, count in word_counts.most_common(10)]

        # Find the text that contains the most common words
        best_score = 0
        best_text = cluster_items[0]["text"]

        for item in cluster_items:
            score = sum(1 for word in common_words if word in item["text"].lower())
            if score > best_score:
                best_score = score
                best_text = item["text"]

        return best_text[:100]  # Truncate for readability

    def _extract_semantic_keywords(self, texts: list[str]) -> list[str]:
        """Extract semantic keywords from a collection of texts"""
        if not texts:
            return []

        # Simple keyword extraction using TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=20,
            stop_words=["di", "e", "il", "la", "un", "una", "in", "con", "per", "su", "da", "del", "della"],
            ngram_range=(1, 2),
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()

            # Get average TF-IDF scores
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)

            # Get top keywords
            top_indices = np.argsort(mean_scores)[::-1][:10]
            keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0.1]

            return keywords

        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []

    def _determine_italian_category(self, feedback_text: str, query_text: str, current_category: str) -> str:
        """Determine Italian category based on text analysis"""
        if current_category and current_category != "unclassified":
            return current_category

        text = f"{feedback_text} {query_text}".lower()

        # Pattern matching for Italian categories
        if any(word in text for word in ["normativa", "decreto", "legge", "obsoleta", "aggiorna", "modificata"]):
            return "normativa_obsoleta"

        elif any(word in text for word in ["interpretazione", "sbagliata", "errata", "male", "scorretto"]):
            return "interpretazione_errata"

        elif any(word in text for word in ["calcolo", "formula", "numero", "errore", "sbagliato"]):
            return "calcolo_sbagliato"

        elif any(word in text for word in ["generico", "vago", "specifico", "dettaglio", "caso"]):
            if "generico" in text or "vago" in text:
                return "troppo_generico"
            else:
                return "caso_mancante"

        elif any(word in text for word in ["manca", "mancante", "assente", "non considera"]):
            return "caso_mancante"

        return "unclassified"

    def _determine_subcategory(self, feedback_text: str, italian_category: str) -> str:
        """Determine subcategory within Italian category"""
        text = feedback_text.lower()

        if italian_category == "normativa_obsoleta":
            if "decreto" in text:
                return "decreto_legge"
            elif "circolare" in text:
                return "circolare"
            elif "legge" in text:
                return "legge"
            return "normativa_generica"

        elif italian_category == "calcolo_sbagliato":
            if "iva" in text:
                return "calcolo_iva"
            elif "irpef" in text:
                return "calcolo_irpef"
            elif "contributi" in text:
                return "calcolo_contributi"
            return "calcolo_generico"

        return "generale"

    def _calculate_failure_severity(self, failure: dict[str, Any]) -> str:
        """Calculate failure severity based on multiple factors"""
        # Check for critical keywords
        feedback = failure.get("feedback", "").lower()
        failure.get("query", "").lower()

        critical_keywords = ["errore", "sbagliato", "critico", "grave", "importante"]
        medium_keywords = ["problema", "migliora", "correggi", "aggiorna"]

        if any(keyword in feedback for keyword in critical_keywords):
            return "high"
        elif any(keyword in feedback for keyword in medium_keywords):
            return "medium"
        else:
            return "low"

    def _calculate_categorization_confidence(self, feedback_text: str, italian_category: str) -> float:
        """Calculate confidence in categorization"""
        # Simple confidence based on keyword matching strength
        text = feedback_text.lower()
        category_keywords = self.italian_tax_patterns.get(italian_category, [])

        matches = sum(1 for keyword in category_keywords if keyword in text)
        confidence = min(matches / 5.0, 1.0)  # Max confidence at 5 keyword matches

        return confidence

    def _infer_categories_from_cluster(self, cluster_items: list[dict[str, Any]]) -> list[str]:
        """Infer categories from cluster items"""
        category_counts = Counter()

        for item in cluster_items:
            text = item.get("text", "").lower()
            category = self._determine_italian_category(text, "", "")
            if category != "unclassified":
                category_counts[category] += 1

        # Return categories that appear in at least 30% of cluster items
        threshold = max(1, len(cluster_items) * 0.3)
        return [cat for cat, count in category_counts.items() if count >= threshold]

    def _analyze_regulatory_patterns(self, feedback_list: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze patterns specific to regulatory issues"""
        regulatory_terms = []
        years_mentioned = []

        for feedback in feedback_list:
            text = f"{feedback.get('query', '')} {feedback.get('feedback', '')}"

            # Extract regulatory references
            import re

            dl_matches = re.findall(r"D\.?L\.?\s*(\d+/\d{4})", text, re.IGNORECASE)
            law_matches = re.findall(r"[Ll]egge\s*(\d+/\d{4})", text)
            year_matches = re.findall(r"\b(20\d{2})\b", text)

            regulatory_terms.extend(dl_matches + law_matches)
            years_mentioned.extend(year_matches)

        return {
            "regulatory_references": list(set(regulatory_terms)),
            "years_mentioned": list(set(years_mentioned)),
            "most_common_year": Counter(years_mentioned).most_common(1)[0][0] if years_mentioned else None,
            "outdated_references_count": len([year for year in years_mentioned if int(year) < 2022]),
        }

    def _analyze_calculation_patterns(self, feedback_list: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze patterns specific to calculation errors"""
        calculation_types = []
        error_types = []

        for feedback in feedback_list:
            text = f"{feedback.get('query', '')} {feedback.get('feedback', '')}".lower()

            # Identify calculation types
            if "iva" in text:
                calculation_types.append("IVA")
            if "irpef" in text:
                calculation_types.append("IRPEF")
            if "contributi" in text:
                calculation_types.append("Contributi")
            if "percentuale" in text or "%" in text:
                calculation_types.append("Percentuale")

            # Identify error types
            if "formula" in text:
                error_types.append("Formula")
            if "aliquota" in text:
                error_types.append("Aliquota")
            if "base imponibile" in text:
                error_types.append("Base Imponibile")

        return {
            "calculation_types": list(Counter(calculation_types).keys()),
            "error_types": list(Counter(error_types).keys()),
            "most_common_calculation": Counter(calculation_types).most_common(1)[0][0] if calculation_types else None,
            "most_common_error": Counter(error_types).most_common(1)[0][0] if error_types else None,
        }

    def _initialize_tax_patterns(self) -> dict[str, list[str]]:
        """Initialize Italian tax domain patterns"""
        return {
            "normativa_obsoleta": [
                "decreto",
                "legge",
                "circolare",
                "normativa",
                "aggiornamento",
                "modificata",
                "cambiata",
                "nuova",
                "vecchia",
                "obsoleta",
            ],
            "interpretazione_errata": [
                "interpretazione",
                "sbagliata",
                "errata",
                "male",
                "scorretto",
                "comprensione",
                "significato",
                "senso",
            ],
            "calcolo_sbagliato": [
                "calcolo",
                "formula",
                "numero",
                "errore",
                "sbagliato",
                "matematico",
                "aritmetico",
                "percentuale",
                "aliquota",
            ],
            "caso_mancante": [
                "manca",
                "mancante",
                "assente",
                "non considera",
                "caso",
                "situazione",
                "scenario",
                "ipotesi",
            ],
            "troppo_generico": [
                "generico",
                "vago",
                "generale",
                "specifico",
                "dettaglio",
                "particolare",
                "preciso",
                "concreto",
            ],
        }

    async def get_pattern_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get analytics for identified patterns"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Query pattern statistics
            patterns_query = (
                select(FailurePattern)
                .where(FailurePattern.first_detected >= start_date)
                .order_by(desc(FailurePattern.impact_score))
            )

            result = await self.db.execute(patterns_query)
            patterns = result.scalars().all()

            # Calculate analytics
            total_patterns = len(patterns)
            resolved_patterns = len([p for p in patterns if p.is_resolved])

            category_distribution = Counter()
            impact_distribution = Counter()

            for pattern in patterns:
                for category in pattern.categories:
                    category_distribution[category] += 1

                if pattern.impact_score >= 0.8:
                    impact_distribution["critical"] += 1
                elif pattern.impact_score >= 0.6:
                    impact_distribution["high"] += 1
                elif pattern.impact_score >= 0.4:
                    impact_distribution["medium"] += 1
                else:
                    impact_distribution["low"] += 1

            return {
                "period_days": days,
                "total_patterns": total_patterns,
                "resolved_patterns": resolved_patterns,
                "resolution_rate": resolved_patterns / total_patterns if total_patterns > 0 else 0,
                "category_distribution": dict(category_distribution),
                "impact_distribution": dict(impact_distribution),
                "top_patterns": [
                    {
                        "name": p.pattern_name,
                        "frequency": p.frequency_count,
                        "impact": p.impact_score,
                        "confidence": p.confidence_score,
                    }
                    for p in patterns[:10]
                ],
                "clustering_stats": {
                    "clusters_created": self.stats["clusters_created"],
                    "avg_confidence": self.stats["avg_confidence_score"],
                },
            }

        except Exception as e:
            logger.error(f"Failed to get pattern analytics: {e}")
            return {"error": str(e)}

    def get_statistics(self) -> dict[str, Any]:
        """Get current analyzer statistics"""
        return {
            "session_stats": self.stats,
            "clustering_params": {
                "dbscan_eps": self.dbscan_eps,
                "dbscan_min_samples": self.dbscan_min_samples,
                "min_pattern_frequency": self.min_pattern_frequency,
                "min_pattern_confidence": self.min_pattern_confidence,
            },
            "italian_categories": list(self.italian_tax_patterns.keys()),
            "performance_metrics": {
                "patterns_per_analysis": self.stats["patterns_identified"]
                / max(self.stats["failures_analyzed"] / 10, 1),
                "clustering_efficiency": self.stats["clusters_created"] / max(self.stats["failures_analyzed"] / 20, 1),
            },
        }
