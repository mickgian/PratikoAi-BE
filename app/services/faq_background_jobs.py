"""
FAQ Background Jobs Service.

Handles background job processing for automated FAQ generation system
including scheduled analysis, batch generation, and RSS monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.faq_automation import (
    FAQGenerationJob, QueryCluster, FAQCandidate, GeneratedFAQ,
    RSSFAQImpact, FAQ_AUTOMATION_CONFIG
)
from app.services.query_pattern_analyzer import QueryPatternAnalyzer
from app.services.auto_faq_generator import AutomatedFAQGenerator
from app.services.faq_rss_integration import FAQRSSIntegration
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.query_normalizer import QueryNormalizer
from app.core.database import get_db


class FAQBackgroundJobProcessor:
    """
    Processes background jobs for FAQ automation system.
    
    Handles:
    - Scheduled pattern analysis
    - Batch FAQ generation
    - RSS feed monitoring
    - System maintenance tasks
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Initialize services
        self.llm_service = LLMService()
        self.embedding_service = EmbeddingService()
        self.normalizer = QueryNormalizer()
        
        # Configuration
        self.config = FAQ_AUTOMATION_CONFIG
        
        # Job processing limits
        self.max_concurrent_jobs = 3
        self.job_timeout_minutes = 30
        self.retry_delay_minutes = 15
    
    async def process_pending_jobs(self) -> Dict[str, Any]:
        """
        Process all pending jobs in priority order.
        
        Returns:
            Summary of job processing results
        """
        logger.info("Starting background job processing")
        
        try:
            # Get pending jobs ordered by priority
            jobs_query = select(FAQGenerationJob).where(
                FAQGenerationJob.status == "pending"
            ).order_by(
                desc(FAQGenerationJob.priority),
                FAQGenerationJob.created_at
            ).limit(self.max_concurrent_jobs)
            
            result = await self.db.execute(jobs_query)
            pending_jobs = result.scalars().all()
            
            if not pending_jobs:
                logger.info("No pending jobs found")
                return {"processed": 0, "results": []}
            
            logger.info(f"Processing {len(pending_jobs)} pending jobs")
            
            # Process jobs concurrently
            processing_tasks = []
            for job in pending_jobs:
                task = asyncio.create_task(self._process_single_job(job))
                processing_tasks.append(task)
            
            # Wait for all jobs to complete
            job_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
            
            # Collect results
            results = {
                "processed": len(pending_jobs),
                "successful": 0,
                "failed": 0,
                "results": []
            }
            
            for i, result in enumerate(job_results):
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["results"].append({
                        "job_id": str(pending_jobs[i].id),
                        "status": "failed",
                        "error": str(result)
                    })
                else:
                    results["successful"] += 1
                    results["results"].append(result)
            
            logger.info(
                f"Job processing completed: {results['successful']} successful, "
                f"{results['failed']} failed"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Job processing failed: {e}")
            return {"error": str(e), "processed": 0}
    
    async def _process_single_job(self, job: FAQGenerationJob) -> Dict[str, Any]:
        """Process a single background job"""
        
        logger.info(f"Processing job {job.id}: {job.job_type}")
        
        try:
            # Mark job as started
            job.status = "processing"
            job.started_at = datetime.utcnow()
            job.progress_percentage = 0
            await self.db.commit()
            
            # Process based on job type
            if job.job_type == "pattern_analysis":
                result = await self._process_pattern_analysis_job(job)
            elif job.job_type == "faq_generation":
                result = await self._process_faq_generation_job(job)
            elif job.job_type == "rss_monitoring":
                result = await self._process_rss_monitoring_job(job)
            elif job.job_type == "batch_generation":
                result = await self._process_batch_generation_job(job)
            elif job.job_type == "system_maintenance":
                result = await self._process_maintenance_job(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # Mark job as completed
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100
            job.result_data = result
            
            if job.started_at:
                execution_time = (job.completed_at - job.started_at).total_seconds()
                job.execution_time_seconds = int(execution_time)
            
            await self.db.commit()
            
            logger.info(f"Job {job.id} completed successfully")
            
            return {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": "completed",
                "execution_time_seconds": job.execution_time_seconds,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            
            # Mark job as failed
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            
            # Increment retry count
            job.retry_count += 1
            
            await self.db.commit()
            
            return {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": "failed",
                "error": str(e),
                "retry_count": job.retry_count,
                "can_retry": job.can_retry()
            }
    
    async def _process_pattern_analysis_job(self, job: FAQGenerationJob) -> Dict[str, Any]:
        """Process pattern analysis job"""
        
        analyzer = QueryPatternAnalyzer(
            self.db,
            self.embedding_service,
            self.normalizer
        )
        
        # Update progress
        job.progress_percentage = 10
        job.progress_description = "Starting query pattern analysis"
        await self.db.commit()
        
        # Find FAQ candidates
        candidates = await analyzer.find_faq_candidates()
        
        job.progress_percentage = 50
        job.progress_description = f"Found {len(candidates)} candidates"
        await self.db.commit()
        
        # Save candidates to database
        saved_candidates = []
        for candidate in candidates:
            self.db.add(candidate)
            saved_candidates.append(str(candidate.id))
        
        await self.db.commit()
        
        job.progress_percentage = 100
        job.progress_description = "Analysis completed"
        job.items_processed = len(candidates)
        job.items_successful = len(candidates)
        job.output_references = saved_candidates
        
        return {
            "candidates_found": len(candidates),
            "candidates_saved": len(saved_candidates),
            "total_potential_savings": sum(float(c.estimated_monthly_savings) for c in candidates),
            "avg_roi_score": sum(float(c.roi_score) for c in candidates) / len(candidates) if candidates else 0
        }
    
    async def _process_faq_generation_job(self, job: FAQGenerationJob) -> Dict[str, Any]:
        """Process FAQ generation job"""
        
        generator = AutomatedFAQGenerator(
            self.llm_service,
            # FAQ quality validator would be injected here
            self.db
        )
        
        # Get candidate ID from job parameters
        candidate_id = job.parameters.get("candidate_id")
        if not candidate_id:
            raise ValueError("Missing candidate_id in job parameters")
        
        # Get candidate
        candidate_query = select(FAQCandidate).where(
            FAQCandidate.id == UUID(candidate_id)
        )
        result = await self.db.execute(candidate_query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        
        if not candidate.can_generate():
            raise ValueError(f"Candidate {candidate_id} cannot be generated")
        
        # Update progress
        job.progress_percentage = 20
        job.progress_description = f"Generating FAQ for: {candidate.suggested_question[:50]}..."
        await self.db.commit()
        
        # Generate FAQ
        generated_faq = await generator.generate_faq_from_candidate(candidate)
        
        job.progress_percentage = 80
        job.progress_description = "FAQ generated, saving to database"
        await self.db.commit()
        
        # Save to database
        self.db.add(generated_faq)
        await self.db.commit()
        
        job.progress_percentage = 100
        job.progress_description = "Generation completed"
        job.items_processed = 1
        job.items_successful = 1
        job.total_cost_cents = generated_faq.generation_cost_cents
        job.output_references = [str(generated_faq.id)]
        
        return {
            "faq_id": str(generated_faq.id),
            "quality_score": float(generated_faq.quality_score),
            "generation_model": generated_faq.generation_model,
            "cost_cents": generated_faq.generation_cost_cents,
            "approval_status": generated_faq.approval_status,
            "estimated_savings": float(generated_faq.estimated_monthly_savings)
        }
    
    async def _process_rss_monitoring_job(self, job: FAQGenerationJob) -> Dict[str, Any]:
        """Process RSS monitoring job"""
        
        rss_integration = FAQRSSIntegration(
            self.db,
            self.llm_service,
            self.embedding_service
        )
        
        # Update progress
        job.progress_percentage = 10
        job.progress_description = "Starting RSS feed monitoring"
        await self.db.commit()
        
        # Check for updates
        update_results = await rss_integration.check_for_updates()
        
        job.progress_percentage = 100
        job.progress_description = "RSS monitoring completed"
        job.items_processed = update_results.get("total_updates", 0)
        job.items_successful = update_results.get("faqs_affected", 0)
        
        return update_results
    
    async def _process_batch_generation_job(self, job: FAQGenerationJob) -> Dict[str, Any]:
        """Process batch FAQ generation job"""
        
        generator = AutomatedFAQGenerator(
            self.llm_service,
            # FAQ quality validator would be injected here
            self.db
        )
        
        # Get candidate IDs from job parameters
        candidate_ids = job.parameters.get("candidate_ids", [])
        if not candidate_ids:
            raise ValueError("Missing candidate_ids in job parameters")
        
        # Get candidates
        candidates_query = select(FAQCandidate).where(
            FAQCandidate.id.in_([UUID(cid) for cid in candidate_ids])
        )
        result = await self.db.execute(candidates_query)
        candidates = result.scalars().all()
        
        valid_candidates = [c for c in candidates if c.can_generate()]
        
        if not valid_candidates:
            raise ValueError("No valid candidates found for batch generation")
        
        # Update progress
        job.progress_percentage = 10
        job.progress_description = f"Starting batch generation for {len(valid_candidates)} candidates"
        await self.db.commit()
        
        # Process batch generation
        batch_results = await generator.batch_generate_faqs(
            valid_candidates,
            max_concurrent=2  # Limit concurrency
        )
        
        job.progress_percentage = 100
        job.progress_description = "Batch generation completed"
        job.items_processed = batch_results["total_candidates"]
        job.items_successful = batch_results["successful"]
        job.items_failed = batch_results["failed"]
        job.total_cost_cents = batch_results["total_cost_cents"]
        
        return batch_results
    
    async def _process_maintenance_job(self, job: FAQGenerationJob) -> Dict[str, Any]:
        """Process system maintenance job"""
        
        maintenance_tasks = job.parameters.get("tasks", [])
        results = {}
        
        for task in maintenance_tasks:
            if task == "cleanup_expired_candidates":
                results[task] = await self._cleanup_expired_candidates()
            elif task == "update_usage_statistics":
                results[task] = await self._update_usage_statistics()
            elif task == "archive_old_jobs":
                results[task] = await self._archive_old_jobs()
            else:
                logger.warning(f"Unknown maintenance task: {task}")
        
        job.progress_percentage = 100
        job.progress_description = f"Completed {len(results)} maintenance tasks"
        
        return results
    
    async def _cleanup_expired_candidates(self) -> Dict[str, Any]:
        """Clean up expired FAQ candidates"""
        try:
            # Find expired candidates
            expired_query = select(FAQCandidate).where(
                and_(
                    FAQCandidate.expires_at < datetime.utcnow(),
                    FAQCandidate.status == "pending"
                )
            )
            
            result = await self.db.execute(expired_query)
            expired_candidates = result.scalars().all()
            
            # Mark as expired
            for candidate in expired_candidates:
                candidate.status = "expired"
            
            await self.db.commit()
            
            logger.info(f"Cleaned up {len(expired_candidates)} expired candidates")
            
            return {
                "candidates_expired": len(expired_candidates),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Candidate cleanup failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _update_usage_statistics(self) -> Dict[str, Any]:
        """Update FAQ usage statistics"""
        try:
            # This would update usage statistics from actual usage logs
            # For now, simulate the process
            
            faqs_query = select(GeneratedFAQ).where(GeneratedFAQ.published == True)
            result = await self.db.execute(faqs_query)
            published_faqs = result.scalars().all()
            
            updated_count = 0
            for faq in published_faqs:
                # In real implementation, would query usage logs
                # For now, just ensure statistics are present
                if faq.usage_count is None:
                    faq.usage_count = 0
                    updated_count += 1
            
            await self.db.commit()
            
            logger.info(f"Updated statistics for {updated_count} FAQs")
            
            return {
                "faqs_updated": updated_count,
                "total_published": len(published_faqs),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Statistics update failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _archive_old_jobs(self) -> Dict[str, Any]:
        """Archive completed jobs older than 30 days"""
        try:
            # Find old completed jobs
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            old_jobs_query = select(FAQGenerationJob).where(
                and_(
                    FAQGenerationJob.completed_at < cutoff_date,
                    FAQGenerationJob.status.in_(["completed", "failed"])
                )
            )
            
            result = await self.db.execute(old_jobs_query)
            old_jobs = result.scalars().all()
            
            # In a real system, would move to archive table
            # For now, just count them
            
            logger.info(f"Found {len(old_jobs)} jobs ready for archiving")
            
            return {
                "jobs_ready_for_archive": len(old_jobs),
                "cutoff_date": cutoff_date.isoformat(),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Job archiving failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def schedule_routine_jobs(self) -> List[str]:
        """Schedule routine maintenance and analysis jobs"""
        
        scheduled_jobs = []
        
        try:
            # Schedule daily pattern analysis
            pattern_analysis_job = FAQGenerationJob(
                id=uuid4(),
                job_type="pattern_analysis",
                job_name="Daily Query Pattern Analysis",
                parameters={
                    "scheduled": True,
                    "analysis_window_days": 1
                },
                priority=7
            )
            
            self.db.add(pattern_analysis_job)
            scheduled_jobs.append(str(pattern_analysis_job.id))
            
            # Schedule RSS monitoring
            rss_monitoring_job = FAQGenerationJob(
                id=uuid4(),
                job_type="rss_monitoring",
                job_name="RSS Feed Monitoring",
                parameters={
                    "scheduled": True,
                    "check_all_feeds": True
                },
                priority=6
            )
            
            self.db.add(rss_monitoring_job)
            scheduled_jobs.append(str(rss_monitoring_job.id))
            
            # Schedule weekly maintenance
            maintenance_job = FAQGenerationJob(
                id=uuid4(),
                job_type="system_maintenance",
                job_name="Weekly System Maintenance",
                parameters={
                    "scheduled": True,
                    "tasks": [
                        "cleanup_expired_candidates",
                        "update_usage_statistics",
                        "archive_old_jobs"
                    ]
                },
                priority=3
            )
            
            self.db.add(maintenance_job)
            scheduled_jobs.append(str(maintenance_job.id))
            
            await self.db.commit()
            
            logger.info(f"Scheduled {len(scheduled_jobs)} routine jobs")
            
            return scheduled_jobs
            
        except Exception as e:
            logger.error(f"Job scheduling failed: {e}")
            await self.db.rollback()
            return []
    
    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        try:
            job_query = select(FAQGenerationJob).where(FAQGenerationJob.id == job_id)
            result = await self.db.execute(job_query)
            job = result.scalar_one_or_none()
            
            if not job:
                return None
            
            return job.to_dict()
            
        except Exception as e:
            logger.error(f"Get job status failed: {e}")
            return None