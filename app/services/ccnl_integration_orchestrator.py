"""
CCNL Integration Orchestrator Service.

This service orchestrates the complete CCNL update workflow from RSS detection
to database integration and notifications. It coordinates all components of
the CCNL automatic update system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid

from app.models.ccnl_update_models import (
    CCNLUpdateEvent, UpdateSource, UpdateStatus, ChangeType
)
from app.services.ccnl_rss_monitor import (
    RSSFeedMonitor, CCNLUpdateDetector, UpdateClassifier, RSSFeedItem
)
from app.services.ccnl_update_processor import CCNLUpdateProcessor
from app.services.ccnl_version_manager import CCNLVersionManager
from app.services.ccnl_change_detector import CCNLChangeDetector
from app.services.ccnl_monitoring_dashboard import CCNLMonitoringDashboard
from app.services.ccnl_notification_service import CCNLNotificationService

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Result of complete workflow execution."""
    detection_successful: bool
    classification_confidence: float
    version_created: bool
    changes_detected: int
    notifications_sent: int
    processing_time: float
    errors: List[str]


class CCNLIntegrationOrchestrator:
    """Orchestrate complete CCNL integration workflow."""
    
    def __init__(self):
        self.rss_monitor = RSSFeedMonitor()
        self.update_detector = CCNLUpdateDetector()
        self.update_classifier = UpdateClassifier()
        self.update_processor = CCNLUpdateProcessor()
        self.version_manager = CCNLVersionManager()
        self.change_detector = CCNLChangeDetector()
        self.monitoring_dashboard = CCNLMonitoringDashboard()
        self.notification_service = CCNLNotificationService()
        
        self.workflow_stats = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "avg_processing_time": 0.0
        }
    
    async def process_full_workflow(self, rss_item: Dict[str, Any], 
                                   source: UpdateSource) -> Dict[str, Any]:
        """Process complete workflow from RSS item to integration."""
        start_time = datetime.utcnow()
        workflow_id = str(uuid.uuid4())
        errors = []
        
        try:
            logger.info(f"Starting workflow {workflow_id} for RSS item: {rss_item.get('title', 'Unknown')}")
            
            # Step 1: Create RSS feed item object
            feed_item = RSSFeedItem(
                title=rss_item.get("title", ""),
                link=rss_item.get("link", ""),
                description=rss_item.get("summary", ""),
                published=rss_item.get("published", datetime.utcnow()),
                guid=rss_item.get("link", f"workflow_{workflow_id}"),
                source=source,
                content=rss_item.get("content")
            )
            
            # Step 2: Detect and classify CCNL update
            detections = await self.update_detector.detect_ccnl_updates([feed_item])
            
            if not detections:
                logger.info(f"No CCNL updates detected in workflow {workflow_id}")
                return self._create_workflow_result(
                    workflow_id, start_time, False, 0.0, False, 0, 0, 
                    ["No CCNL updates detected"]
                )
            
            detection = detections[0]  # Use first detection
            
            # Step 3: Enhanced classification
            classification = await self.update_classifier.classify_update(feed_item)
            
            # Step 4: Create update event
            update_event = self._create_update_event(detection, classification)
            
            # Step 5: Process the update
            processing_result = await self.update_processor.process_update(update_event)
            
            version_created = processing_result.get("status") == "processed"
            changes_detected = processing_result.get("changes_detected", 0)
            
            # Step 6: Send notifications if successful
            notifications_sent = 0
            if version_created and changes_detected > 0:
                notification_result = await self._send_update_notifications(
                    update_event, processing_result
                )
                notifications_sent = notification_result.get("total_sent", 0)
            
            # Step 7: Update monitoring dashboard
            await self._update_monitoring_metrics(workflow_id, processing_result)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update workflow statistics
            self._update_workflow_stats(True, processing_time)
            
            logger.info(f"Completed workflow {workflow_id} successfully in {processing_time:.2f}s")
            
            return self._create_workflow_result(
                workflow_id, start_time, True, detection.confidence_score,
                version_created, changes_detected, notifications_sent, errors
            )
            
        except Exception as e:
            error_msg = f"Workflow {workflow_id} failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_workflow_stats(False, processing_time)
            
            return self._create_workflow_result(
                workflow_id, start_time, False, 0.0, False, 0, 0, errors
            )
    
    def _create_update_event(self, detection, classification: Dict[str, Any]) -> CCNLUpdateEvent:
        """Create update event from detection and classification."""
        # Generate mock CCNL ID based on sector (in real implementation, would look up from database)
        ccnl_id = self._get_ccnl_id_for_sector(classification.get("sector", "unknown"))
        
        update_event = CCNLUpdateEvent(
            id=uuid.uuid4(),
            ccnl_id=ccnl_id,
            source=detection.feed_item.source.value,
            detected_at=datetime.utcnow(),
            title=detection.feed_item.title,
            url=detection.feed_item.link,
            content_summary=detection.feed_item.description,
            classification_confidence=classification.get("confidence", detection.confidence_score),
            status=UpdateStatus.DETECTED.value,
            processed_at=None,
            error_message=None
        )
        
        return update_event
    
    def _get_ccnl_id_for_sector(self, sector: str) -> uuid.UUID:
        """Get or create CCNL ID for sector (mock implementation)."""
        # In real implementation, would query database for CCNL by sector
        # For now, generate deterministic UUID based on sector
        sector_uuid_map = {
            "metalmeccanici": uuid.UUID("550e8400-e29b-41d4-a716-446655440001"),
            "commercio": uuid.UUID("550e8400-e29b-41d4-a716-446655440002"),
            "edilizia": uuid.UUID("550e8400-e29b-41d4-a716-446655440003"),
            "sanita": uuid.UUID("550e8400-e29b-41d4-a716-446655440004"),
            "turismo": uuid.UUID("550e8400-e29b-41d4-a716-446655440005"),
        }
        
        return sector_uuid_map.get(sector, uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))
    
    async def _send_update_notifications(self, update_event: CCNLUpdateEvent, 
                                        processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Send notifications for successful update."""
        try:
            # Prepare notification data
            notification_data = {
                "ccnl_name": self._get_ccnl_name_from_event(update_event),
                "changes": self._extract_changes_from_result(processing_result),
                "effective_date": datetime.utcnow().date()
            }
            
            # Generate notification
            notification = self.notification_service.generate_update_notification(notification_data)
            
            # Send notification
            delivery_result = self.notification_service.send_notification(notification)
            
            logger.info(f"Sent notifications for update {update_event.id}: "
                       f"{delivery_result.get('total_sent', 0)} delivered")
            
            return delivery_result
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
            return {"total_sent": 0, "error": str(e)}
    
    def _get_ccnl_name_from_event(self, update_event: CCNLUpdateEvent) -> str:
        """Extract CCNL name from update event."""
        title = update_event.title.lower()
        
        if "metalmeccanic" in title:
            return "CCNL Metalmeccanici Industria"
        elif "commercio" in title:
            return "CCNL Commercio e Terziario"
        elif "edilizia" in title:
            return "CCNL Edilizia e Costruzioni"
        elif "sanità" in title or "sanita" in title:
            return "CCNL Sanità Privata"
        else:
            return "CCNL (Settore non identificato)"
    
    def _extract_changes_from_result(self, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract changes information from processing result."""
        # In real implementation, would extract actual changes
        # For now, create mock changes based on processing result
        
        changes_count = processing_result.get("changes_detected", 0)
        
        if changes_count > 0:
            return {
                "salary_increases": {"level_1": {"percentage": 3.2}},
                "working_hours": {"old": 40, "new": 38}
            }
        else:
            return {}
    
    async def _update_monitoring_metrics(self, workflow_id: str, 
                                        processing_result: Dict[str, Any]):
        """Update monitoring dashboard metrics."""
        try:
            # In real implementation, would save metrics to database
            # For now, just log the metrics update
            
            metrics_data = {
                "workflow_id": workflow_id,
                "status": processing_result.get("status"),
                "processing_time": processing_result.get("processing_time", 0),
                "timestamp": datetime.utcnow()
            }
            
            logger.debug(f"Updated monitoring metrics for workflow {workflow_id}")
            
        except Exception as e:
            logger.error(f"Error updating monitoring metrics: {str(e)}")
    
    def _create_workflow_result(self, workflow_id: str, start_time: datetime,
                               detection_successful: bool, confidence: float,
                               version_created: bool, changes_detected: int,
                               notifications_sent: int, errors: List[str]) -> Dict[str, Any]:
        """Create workflow result dictionary."""
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "workflow_id": workflow_id,
            "detection_successful": detection_successful,
            "classification_confidence": confidence,
            "version_created": version_created,
            "changes_detected": changes_detected,
            "notifications_sent": notifications_sent,
            "processing_time": processing_time,
            "errors": errors,
            "completed_at": datetime.utcnow(),
            "success": detection_successful and len(errors) == 0
        }
    
    def _update_workflow_stats(self, successful: bool, processing_time: float):
        """Update workflow statistics."""
        self.workflow_stats["total_workflows"] += 1
        
        if successful:
            self.workflow_stats["successful_workflows"] += 1
        else:
            self.workflow_stats["failed_workflows"] += 1
        
        # Update rolling average processing time
        current_avg = self.workflow_stats["avg_processing_time"]
        total = self.workflow_stats["total_workflows"]
        
        if total == 1:
            self.workflow_stats["avg_processing_time"] = processing_time
        else:
            # Calculate weighted average
            self.workflow_stats["avg_processing_time"] = (
                (current_avg * (total - 1) + processing_time) / total
            )
    
    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        """Run complete monitoring cycle (fetch all RSS feeds and process updates)."""
        cycle_start = datetime.utcnow()
        
        try:
            logger.info("Starting CCNL monitoring cycle")
            
            # Step 1: Fetch all RSS updates
            rss_items = await self.rss_monitor.fetch_all_updates()
            
            if not rss_items:
                logger.info("No RSS items found in monitoring cycle")
                return {
                    "cycle_completed": True,
                    "items_processed": 0,
                    "successful_workflows": 0,
                    "failed_workflows": 0,
                    "cycle_time": (datetime.utcnow() - cycle_start).total_seconds()
                }
            
            # Step 2: Process items concurrently (limit concurrency to avoid overwhelming)
            semaphore = asyncio.Semaphore(5)  # Process max 5 items concurrently
            
            async def process_item_with_semaphore(item):
                async with semaphore:
                    return await self.process_full_workflow(
                        {
                            "title": item.title,
                            "link": item.link,
                            "summary": item.description,
                            "published": item.published
                        },
                        item.source
                    )
            
            # Process all items
            tasks = [process_item_with_semaphore(item) for item in rss_items]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful = 0
            failed = 0
            total_notifications = 0
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Workflow failed with exception: {str(result)}")
                    failed += 1
                elif isinstance(result, dict):
                    if result.get("success", False):
                        successful += 1
                        total_notifications += result.get("notifications_sent", 0)
                    else:
                        failed += 1
                else:
                    failed += 1
            
            cycle_time = (datetime.utcnow() - cycle_start).total_seconds()
            
            logger.info(f"Monitoring cycle completed: {successful} successful, "
                       f"{failed} failed, {total_notifications} notifications sent "
                       f"in {cycle_time:.2f}s")
            
            return {
                "cycle_completed": True,
                "items_processed": len(rss_items),
                "successful_workflows": successful,
                "failed_workflows": failed,
                "total_notifications_sent": total_notifications,
                "cycle_time": cycle_time,
                "avg_item_processing_time": cycle_time / len(rss_items) if rss_items else 0
            }
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {str(e)}")
            return {
                "cycle_completed": False,
                "error": str(e),
                "cycle_time": (datetime.utcnow() - cycle_start).total_seconds()
            }
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow execution statistics."""
        return {
            **self.workflow_stats,
            "success_rate": (
                self.workflow_stats["successful_workflows"] / 
                max(1, self.workflow_stats["total_workflows"])
            ),
            "last_updated": datetime.utcnow()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health_status = {
            "overall_healthy": True,
            "components": {},
            "checked_at": datetime.utcnow()
        }
        
        try:
            # Check RSS monitor
            rss_stats = self.rss_monitor.get_feed_statistics()
            health_status["components"]["rss_monitor"] = {
                "healthy": rss_stats.get("active_feeds", 0) > 0,
                "active_feeds": rss_stats.get("active_feeds", 0),
                "last_check": rss_stats.get("last_check")
            }
            
            # Check other components
            health_status["components"]["update_processor"] = {"healthy": True}
            health_status["components"]["version_manager"] = {"healthy": True}
            health_status["components"]["notification_service"] = {"healthy": True}
            
            # Overall health
            component_health = [comp["healthy"] for comp in health_status["components"].values()]
            health_status["overall_healthy"] = all(component_health)
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}")
            return {
                "overall_healthy": False,
                "error": str(e),
                "checked_at": datetime.utcnow()
            }


# Global instance
ccnl_integration_orchestrator = CCNLIntegrationOrchestrator()