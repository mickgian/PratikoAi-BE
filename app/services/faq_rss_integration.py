"""
RSS Integration Service for FAQ Updates.

This service monitors RSS feeds from Italian government sources
and identifies when regulatory changes require FAQ updates.
"""

import asyncio
import feedparser
import hashlib
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

import aiohttp
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.faq_automation import (
    GeneratedFAQ, RSSFAQImpact, FAQ_AUTOMATION_CONFIG
)
from app.services.cache import CacheService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService


# Custom Exceptions

class RSSFetchError(Exception):
    """Raised when RSS feed fetching fails"""
    pass


class ImpactAnalysisError(Exception):
    """Raised when impact analysis fails"""
    pass


class FAQRSSIntegration:
    """
    Monitors RSS feeds for regulatory changes and identifies
    FAQs that need updates when regulations change.
    
    Focuses on Italian government sources like Agenzia delle Entrate,
    MEF, and other regulatory bodies.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        cache_service: Optional[CacheService] = None
    ):
        self.db = db
        self.llm = llm_service
        self.embeddings = embedding_service
        self.cache = cache_service
        
        # Configuration
        config = FAQ_AUTOMATION_CONFIG["rss_integration"]
        self.high_impact_threshold = config["high_impact_threshold"]
        self.medium_impact_threshold = config["medium_impact_threshold"]
        self.update_check_hours = config["update_check_hours"]
        self.max_updates_per_batch = config["max_updates_per_batch"]
        
        # Italian government RSS feeds
        self.rss_feeds = {
            "agenzia_entrate": {
                "url": "https://www.agenziaentrate.gov.it/wps/portal/entrate/home",
                "name": "Agenzia delle Entrate",
                "priority": "high",
                "keywords": ["iva", "irpef", "dichiarazione", "fattura", "tasse"]
            },
            "mef": {
                "url": "https://www.mef.gov.it/",
                "name": "Ministero Economia e Finanze",
                "priority": "high", 
                "keywords": ["legge", "decreto", "normativa", "bilancio"]
            },
            "gazzetta_ufficiale": {
                "url": "https://www.gazzettaufficiale.it/",
                "name": "Gazzetta Ufficiale",
                "priority": "critical",
                "keywords": ["decreto", "legge", "regolamento", "dlgs"]
            },
            "inps": {
                "url": "https://www.inps.it/",
                "name": "INPS",
                "priority": "medium",
                "keywords": ["contributi", "previdenza", "gestione"]
            }
        }
    
    async def check_for_updates(self) -> Dict[str, Any]:
        """
        Check all RSS feeds for updates and analyze impact on existing FAQs.
        
        Returns:
            Summary of updates found and impact analysis results
        """
        logger.info("Starting RSS update check")
        
        try:
            results = {
                "check_timestamp": datetime.utcnow().isoformat(),
                "feeds_checked": 0,
                "total_updates": 0,
                "high_impact": 0,
                "medium_impact": 0,
                "low_impact": 0,
                "faqs_affected": 0,
                "updates_processed": [],
                "errors": []
            }
            
            # Get recent updates from all feeds
            all_updates = []
            
            for feed_id, feed_config in self.rss_feeds.items():
                try:
                    logger.info(f"Checking feed: {feed_config['name']}")
                    
                    updates = await self._fetch_feed_updates(feed_id, feed_config)
                    all_updates.extend(updates)
                    
                    results["feeds_checked"] += 1
                    results["total_updates"] += len(updates)
                    
                except Exception as e:
                    logger.error(f"Error fetching feed {feed_id}: {e}")
                    results["errors"].append({
                        "feed": feed_id,
                        "error": str(e)
                    })
            
            # Analyze impact on existing FAQs
            if all_updates:
                impact_results = await self._analyze_faq_impacts(all_updates)
                
                for impact in impact_results:
                    results["updates_processed"].append(impact)
                    
                    if impact["impact_level"] == "high":
                        results["high_impact"] += 1
                    elif impact["impact_level"] == "medium":
                        results["medium_impact"] += 1
                    else:
                        results["low_impact"] += 1
                
                # Count unique FAQs affected
                affected_faqs = set()
                for impact in impact_results:
                    affected_faqs.add(impact["faq_id"])
                
                results["faqs_affected"] = len(affected_faqs)
            
            logger.info(
                f"RSS update check completed: {results['total_updates']} updates found, "
                f"{results['faqs_affected']} FAQs affected"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"RSS update check failed: {e}")
            raise RSSFetchError(f"RSS update check failed: {e}")
    
    async def _fetch_feed_updates(
        self,
        feed_id: str,
        feed_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch recent updates from a specific RSS feed"""
        try:
            # Cache key for this feed
            cache_key = f"rss_updates:{feed_id}:{datetime.utcnow().date()}"
            
            # Check cache first
            if self.cache:
                cached_updates = await self.cache.get(cache_key)
                if cached_updates:
                    return cached_updates
            
            # Fetch from RSS feed (simulated for demo)
            # In production, this would use aiohttp to fetch real RSS feeds
            updates = await self._simulate_rss_fetch(feed_id, feed_config)
            
            # Cache results for 4 hours
            if self.cache:
                await self.cache.set(cache_key, updates, ttl=14400)
            
            return updates
            
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_id}: {e}")
            raise RSSFetchError(f"Feed fetch failed: {e}")
    
    async def _simulate_rss_fetch(
        self,
        feed_id: str,
        feed_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Simulate RSS feed updates for demonstration.
        In production, this would parse real RSS feeds.
        """
        # Simulate regulatory updates
        simulated_updates = []
        
        if feed_id == "agenzia_entrate":
            simulated_updates = [
                {
                    "id": str(uuid4()),
                    "title": "Nuove aliquote IVA per servizi digitali - Circolare 15/E",
                    "summary": "Modifiche alle aliquote IVA per i servizi digitali secondo la Direttiva UE 2021/2042",
                    "published_date": datetime.utcnow() - timedelta(hours=6),
                    "url": "https://www.agenziaentrate.gov.it/portale/documents/circolare-15e-2024",
                    "source": feed_config["name"],
                    "keywords": ["iva", "aliquote", "servizi digitali", "direttiva"],
                    "content": "La circolare introduce nuove aliquote IVA per i servizi digitali..."
                }
            ]
        elif feed_id == "mef":
            simulated_updates = [
                {
                    "id": str(uuid4()),
                    "title": "Decreto Ministeriale - Aggiornamento soglie regime forfettario 2024",
                    "summary": "Modifiche alle soglie di accesso e permanenza nel regime forfettario",
                    "published_date": datetime.utcnow() - timedelta(hours=12),
                    "url": "https://www.mef.gov.it/decreto-forfettario-2024",
                    "source": feed_config["name"],
                    "keywords": ["regime forfettario", "soglie", "partita iva"],
                    "content": "Il decreto modifica i limiti di ricavi per il regime forfettario..."
                }
            ]
        elif feed_id == "gazzetta_ufficiale":
            simulated_updates = [
                {
                    "id": str(uuid4()),
                    "title": "D.Lgs. 142/2024 - Riforma della fatturazione elettronica",
                    "summary": "Nuove disposizioni per la fatturazione elettronica e il Sistema di Interscambio",
                    "published_date": datetime.utcnow() - timedelta(hours=18),
                    "url": "https://www.gazzettaufficiale.it/eli/id/2024/142",
                    "source": feed_config["name"],
                    "keywords": ["fatturazione elettronica", "sdi", "decreto legislativo"],
                    "content": "Il decreto introduce modifiche al sistema di fatturazione elettronica..."
                }
            ]
        
        return simulated_updates
    
    async def _analyze_faq_impacts(
        self,
        updates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze which FAQs are impacted by RSS updates"""
        try:
            impact_results = []
            
            # Get all published FAQs
            faqs_query = select(GeneratedFAQ).where(
                and_(
                    GeneratedFAQ.published == True,
                    GeneratedFAQ.approval_status.in_(["auto_approved", "manually_approved"])
                )
            )
            
            result = await self.db.execute(faqs_query)
            faqs = result.scalars().all()
            
            logger.info(f"Analyzing impact on {len(faqs)} published FAQs")
            
            # Analyze each update against each FAQ
            for update in updates:
                for faq in faqs:
                    impact_analysis = await self._calculate_impact_score(update, faq)
                    
                    if impact_analysis["impact_score"] >= self.medium_impact_threshold:
                        # Create impact record
                        impact_record = await self._create_impact_record(
                            faq, update, impact_analysis
                        )
                        
                        impact_results.append({
                            "faq_id": str(faq.id),
                            "faq_question": faq.question[:100] + "..." if len(faq.question) > 100 else faq.question,
                            "update_title": update["title"],
                            "impact_level": impact_analysis["impact_level"],
                            "impact_score": impact_analysis["impact_score"],
                            "confidence_score": impact_analysis["confidence_score"],
                            "matching_keywords": impact_analysis["matching_keywords"],
                            "action_required": impact_analysis["action_required"],
                            "impact_record_id": str(impact_record.id)
                        })
            
            return impact_results
            
        except Exception as e:
            logger.error(f"Impact analysis failed: {e}")
            raise ImpactAnalysisError(f"Impact analysis failed: {e}")
    
    async def _calculate_impact_score(
        self,
        update: Dict[str, Any],
        faq: GeneratedFAQ
    ) -> Dict[str, Any]:
        """Calculate impact score between an RSS update and a FAQ"""
        try:
            # Initialize scoring components
            keyword_score = 0.0
            semantic_score = 0.0
            regulatory_score = 0.0
            
            # 1. Keyword matching analysis
            update_text = f"{update['title']} {update['summary']} {update.get('content', '')}"
            faq_text = f"{faq.question} {faq.answer}"
            
            # Normalize text for comparison
            update_lower = update_text.lower()
            faq_lower = faq_text.lower()
            
            # Check for keyword matches
            matching_keywords = []
            update_keywords = update.get("keywords", [])
            
            for keyword in update_keywords:
                if keyword.lower() in faq_lower:
                    matching_keywords.append(keyword)
                    keyword_score += 0.2
            
            # Add FAQ tags matching
            if faq.tags:
                for tag in faq.tags:
                    if tag.lower() in update_lower:
                        matching_keywords.append(tag)
                        keyword_score += 0.15
            
            # 2. Semantic similarity analysis
            try:
                update_embedding = await self.embeddings.embed_text(update_text[:1000])  # Limit length
                faq_embedding = await self.embeddings.embed_text(faq_text[:1000])
                
                semantic_score = self.embeddings.cosine_similarity(update_embedding, faq_embedding)
            except Exception as e:
                logger.warning(f"Semantic analysis failed: {e}")
                semantic_score = 0.0
            
            # 3. Regulatory reference matching
            regulatory_patterns = [
                r'D\.Lgs\.?\s*\d+/\d+',
                r'D\.P\.R\.?\s*\d+/\d+',
                r'L\.?\s*\d+/\d+',
                r'Circolare\s*\d+',
                r'Art\.?\s*\d+'
            ]
            
            update_refs = set()
            faq_refs = set(faq.regulatory_refs or [])
            
            for pattern in regulatory_patterns:
                update_matches = re.findall(pattern, update_text, re.IGNORECASE)
                update_refs.update(update_matches)
            
            # Check for regulatory overlap
            if update_refs and faq_refs:
                common_refs = update_refs.intersection(faq_refs)
                if common_refs:
                    regulatory_score = min(len(common_refs) * 0.3, 1.0)
            
            # Calculate composite impact score
            impact_score = (
                keyword_score * 0.4 +
                semantic_score * 0.35 +
                regulatory_score * 0.25
            )
            
            # Determine impact level and action
            if impact_score >= self.high_impact_threshold:
                impact_level = "high"
                action_required = "regenerate"
            elif impact_score >= self.medium_impact_threshold:
                impact_level = "medium"
                action_required = "review"
            else:
                impact_level = "low"
                action_required = "monitor"
            
            # Calculate confidence based on multiple indicators
            confidence_indicators = []
            if matching_keywords:
                confidence_indicators.append(0.3)
            if semantic_score > 0.3:
                confidence_indicators.append(0.4)
            if regulatory_score > 0:
                confidence_indicators.append(0.3)
            
            confidence_score = sum(confidence_indicators) / len(confidence_indicators) if confidence_indicators else 0.2
            
            return {
                "impact_score": impact_score,
                "impact_level": impact_level,
                "confidence_score": confidence_score,
                "action_required": action_required,
                "matching_keywords": matching_keywords,
                "keyword_score": keyword_score,
                "semantic_score": semantic_score,
                "regulatory_score": regulatory_score,
                "analysis_components": {
                    "keyword_matches": len(matching_keywords),
                    "semantic_similarity": semantic_score,
                    "regulatory_overlap": len(update_refs.intersection(faq_refs)) if update_refs and faq_refs else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Impact score calculation failed: {e}")
            return {
                "impact_score": 0.0,
                "impact_level": "low",
                "confidence_score": 0.0,
                "action_required": "ignore",
                "matching_keywords": [],
                "keyword_score": 0.0,
                "semantic_score": 0.0,
                "regulatory_score": 0.0
            }
    
    async def _create_impact_record(
        self,
        faq: GeneratedFAQ,
        update: Dict[str, Any],
        impact_analysis: Dict[str, Any]
    ) -> RSSFAQImpact:
        """Create impact record in database"""
        try:
            impact_record = RSSFAQImpact(
                id=uuid4(),
                faq_id=faq.id,
                rss_update_id=update["id"],
                impact_level=impact_analysis["impact_level"],
                impact_score=Decimal(str(impact_analysis["impact_score"])),
                confidence_score=Decimal(str(impact_analysis["confidence_score"])),
                rss_source=update["source"],
                rss_title=update["title"],
                rss_summary=update["summary"],
                rss_published_date=update["published_date"],
                rss_url=update["url"],
                matching_keywords=impact_analysis["matching_keywords"],
                regulatory_changes=[],  # Would extract from update content
                action_required=impact_analysis["action_required"],
                processed=False,
                analysis_metadata={
                    "keyword_score": impact_analysis["keyword_score"],
                    "semantic_score": impact_analysis["semantic_score"],
                    "regulatory_score": impact_analysis["regulatory_score"],
                    "analysis_components": impact_analysis["analysis_components"],
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            self.db.add(impact_record)
            await self.db.commit()
            
            logger.info(f"Created impact record {impact_record.id} for FAQ {faq.id}")
            
            return impact_record
            
        except Exception as e:
            logger.error(f"Failed to create impact record: {e}")
            await self.db.rollback()
            raise
    
    async def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get FAQs that require action based on RSS updates"""
        try:
            # Query unprocessed high and medium impact updates
            query = select(RSSFAQImpact).where(
                and_(
                    RSSFAQImpact.processed == False,
                    RSSFAQImpact.impact_level.in_(["high", "medium"]),
                    RSSFAQImpact.action_required.in_(["regenerate", "review"])
                )
            ).order_by(
                RSSFAQImpact.impact_score.desc(),
                RSSFAQImpact.rss_published_date.desc()
            )
            
            result = await self.db.execute(query)
            impacts = result.scalars().all()
            
            pending_actions = []
            
            for impact in impacts:
                action_info = {
                    "impact_id": str(impact.id),
                    "faq_id": str(impact.faq_id),
                    "impact_level": impact.impact_level,
                    "impact_score": float(impact.impact_score),
                    "confidence_score": float(impact.confidence_score),
                    "action_required": impact.action_required,
                    "rss_title": impact.rss_title,
                    "rss_source": impact.rss_source,
                    "rss_published_date": impact.rss_published_date.isoformat(),
                    "matching_keywords": impact.matching_keywords,
                    "urgency_score": float(impact.calculate_urgency_score()),
                    "requires_immediate_action": impact.requires_immediate_action()
                }
                
                pending_actions.append(action_info)
            
            return pending_actions
            
        except Exception as e:
            logger.error(f"Failed to get pending actions: {e}")
            return []
    
    async def mark_impact_processed(
        self,
        impact_id: UUID,
        action_taken: str,
        action_by: Optional[UUID] = None,
        processing_notes: Optional[str] = None
    ) -> bool:
        """Mark an RSS impact as processed"""
        try:
            query = select(RSSFAQImpact).where(RSSFAQImpact.id == impact_id)
            result = await self.db.execute(query)
            impact = result.scalar_one_or_none()
            
            if not impact:
                logger.warning(f"Impact record {impact_id} not found")
                return False
            
            impact.processed = True
            impact.action_taken = action_taken
            impact.action_date = datetime.utcnow()
            impact.action_by = action_by
            impact.processing_notes = processing_notes
            
            await self.db.commit()
            
            logger.info(f"Marked impact {impact_id} as processed with action: {action_taken}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark impact as processed: {e}")
            await self.db.rollback()
            return False
    
    async def get_rss_statistics(self) -> Dict[str, Any]:
        """Get RSS integration statistics"""
        try:
            # Get impact statistics
            impacts_query = select(RSSFAQImpact).where(
                RSSFAQImpact.created_at >= datetime.utcnow() - timedelta(days=30)
            )
            
            result = await self.db.execute(impacts_query)
            recent_impacts = result.scalars().all()
            
            stats = {
                "last_30_days": {
                    "total_impacts": len(recent_impacts),
                    "high_impact": len([i for i in recent_impacts if i.impact_level == "high"]),
                    "medium_impact": len([i for i in recent_impacts if i.impact_level == "medium"]),
                    "low_impact": len([i for i in recent_impacts if i.impact_level == "low"]),
                    "processed": len([i for i in recent_impacts if i.processed]),
                    "pending": len([i for i in recent_impacts if not i.processed])
                },
                "by_source": {},
                "by_action": {},
                "avg_response_time_hours": 0,
                "feeds_monitored": len(self.rss_feeds)
            }
            
            # Group by source
            for impact in recent_impacts:
                source = impact.rss_source
                if source not in stats["by_source"]:
                    stats["by_source"][source] = 0
                stats["by_source"][source] += 1
            
            # Group by action required
            for impact in recent_impacts:
                action = impact.action_required
                if action not in stats["by_action"]:
                    stats["by_action"][action] = 0
                stats["by_action"][action] += 1
            
            # Calculate average response time for processed impacts
            processed_impacts = [i for i in recent_impacts if i.processed and i.action_date]
            if processed_impacts:
                total_response_time = sum([
                    (i.action_date - i.created_at).total_seconds() / 3600
                    for i in processed_impacts
                ])
                stats["avg_response_time_hours"] = total_response_time / len(processed_impacts)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get RSS statistics: {e}")
            return {
                "error": str(e),
                "feeds_monitored": len(self.rss_feeds)
            }