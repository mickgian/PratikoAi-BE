"""
CCNL Update Service for real-time contract renewals and notifications.

This service manages automatic updates of CCNL data when contracts are renewed,
sends alerts for expiring agreements, and maintains data consistency.
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

from app.models.ccnl_data import CCNLAgreement, CCNLSector
from app.services.ccnl_service import ccnl_service

logger = logging.getLogger(__name__)


class UpdateType(str, Enum):
    """Types of CCNL updates."""
    RENEWAL = "renewal"  # Contract renewed with new terms
    EXTENSION = "extension"  # Contract validity extended
    SALARY_REVISION = "salary_revision"  # Salary tables updated
    WORKING_HOURS_CHANGE = "working_hours_change"  # Working hours modified
    ALLOWANCE_UPDATE = "allowance_update"  # Special allowances modified
    COMPLETE_RENEWAL = "complete_renewal"  # Full contract renewal


class AlertType(str, Enum):
    """Types of alerts for CCNL management."""
    EXPIRING_SOON = "expiring_soon"  # Contract expires within 90 days
    EXPIRED = "expired"  # Contract has expired
    RENEWAL_AVAILABLE = "renewal_available"  # New version available
    CRITICAL_UPDATE = "critical_update"  # Important changes requiring attention
    VALIDATION_ERROR = "validation_error"  # Data validation issues


@dataclass
class CCNLUpdate:
    """Represents a CCNL update event."""
    sector: CCNLSector
    update_type: UpdateType
    effective_date: date
    previous_version: str
    new_version: str
    changes_summary: str
    updated_fields: List[str]
    impact_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    notification_sent: bool = False
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class CCNLAlert:
    """Represents an alert for CCNL management."""
    id: str
    sector: CCNLSector
    alert_type: AlertType
    title: str
    message: str
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    expires_at: Optional[datetime] = None
    acknowledged: bool = False
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class RenewalNotification:
    """Notification for CCNL renewal."""
    sector: CCNLSector
    current_expiry: date
    days_until_expiry: int
    renewal_status: str  # PENDING, IN_PROGRESS, COMPLETED, OVERDUE
    notification_recipients: List[str]
    last_notified: Optional[datetime] = None


class CCNLUpdateService:
    """Service for managing CCNL updates and notifications."""
    
    def __init__(self):
        self.pending_updates: List[CCNLUpdate] = []
        self.active_alerts: List[CCNLAlert] = []
        self.renewal_notifications: Dict[CCNLSector, RenewalNotification] = {}
    
    async def check_for_updates(self) -> List[CCNLUpdate]:
        """Check for available CCNL updates from official sources."""
        logger.info("Checking for CCNL updates from official sources")
        
        # In a real implementation, this would connect to:
        # - Ministry of Labor databases
        # - Union websites
        # - Employer association feeds
        # - CNEL (National Council for Economics and Labor)
        
        updates = []
        
        # Check each sector for potential updates
        all_agreements = await ccnl_service.get_all_ccnl_data()
        
        for agreement in all_agreements:
            # Check if contract is approaching expiry
            days_until_expiry = (agreement.valid_to - date.today()).days
            
            if days_until_expiry <= 90 and days_until_expiry > 0:
                # Check if renewal information is available
                renewal_info = await self._check_renewal_availability(agreement.sector)
                if renewal_info:
                    update = CCNLUpdate(
                        sector=agreement.sector,
                        update_type=UpdateType.RENEWAL,
                        effective_date=renewal_info.get("effective_date", agreement.valid_to),
                        previous_version=f"{agreement.valid_from}-{agreement.valid_to}",
                        new_version=renewal_info.get("new_version", "TBD"),
                        changes_summary=renewal_info.get("changes", "Renewal in progress"),
                        updated_fields=renewal_info.get("updated_fields", []),
                        impact_level=renewal_info.get("impact_level", "MEDIUM")
                    )
                    updates.append(update)
            
        self.pending_updates.extend(updates)
        return updates
    
    async def _check_renewal_availability(self, sector: CCNLSector) -> Optional[Dict[str, Any]]:
        """Check if renewal information is available for a sector."""
        # Simulate checking external sources
        # In reality, this would query government/union APIs
        
        renewal_sources = {
            CCNLSector.METALMECCANICI_INDUSTRIA: {
                "effective_date": date(2024, 3, 1),
                "new_version": "2024-2027",
                "changes": "Salary increase 3.2%, new remote work provisions",
                "updated_fields": ["salary_tables", "working_hours", "special_allowances"],
                "impact_level": "HIGH"
            },
            CCNLSector.COMMERCIO_TERZIARIO: {
                "effective_date": date(2024, 4, 1),
                "new_version": "2024-2026",
                "changes": "Updated leave entitlements, digital skills training",
                "updated_fields": ["leave_entitlements", "job_levels"],
                "impact_level": "MEDIUM"
            }
        }
        
        return renewal_sources.get(sector)
    
    async def generate_expiration_alerts(self) -> List[CCNLAlert]:
        """Generate alerts for expiring CCNL agreements."""
        logger.info("Generating expiration alerts for CCNL agreements")
        
        alerts = []
        all_agreements = await ccnl_service.get_all_ccnl_data()
        
        for agreement in all_agreements:
            days_until_expiry = (agreement.valid_to - date.today()).days
            
            # Alert for agreements expiring within 90 days
            if 0 < days_until_expiry <= 90:
                alert = CCNLAlert(
                    id=f"exp_{agreement.sector.value}_{date.today().isoformat()}",
                    sector=agreement.sector,
                    alert_type=AlertType.EXPIRING_SOON,
                    title=f"CCNL {agreement.sector.italian_name()} scade presto",
                    message=f"Il contratto scade il {agreement.valid_to.strftime('%d/%m/%Y')} ({days_until_expiry} giorni)",
                    severity="WARNING" if days_until_expiry > 30 else "ERROR"
                )
                alerts.append(alert)
            
            # Alert for expired agreements
            elif days_until_expiry <= 0:
                alert = CCNLAlert(
                    id=f"exp_{agreement.sector.value}_{date.today().isoformat()}",
                    sector=agreement.sector,
                    alert_type=AlertType.EXPIRED,
                    title=f"CCNL {agreement.sector.italian_name()} scaduto",
                    message=f"Il contratto è scaduto il {agreement.valid_to.strftime('%d/%m/%Y')} ({abs(days_until_expiry)} giorni fa)",
                    severity="CRITICAL"
                )
                alerts.append(alert)
        
        self.active_alerts.extend(alerts)
        return alerts
    
    async def apply_ccnl_update(self, update: CCNLUpdate) -> bool:
        """Apply a CCNL update to the system."""
        logger.info(f"Applying CCNL update for sector {update.sector.value}")
        
        try:
            # Get current agreement
            current_agreement = await ccnl_service.get_current_ccnl_by_sector(update.sector)
            if not current_agreement:
                logger.error(f"No current agreement found for sector {update.sector.value}")
                return False
            
            # Create updated agreement based on update type
            updated_agreement = await self._create_updated_agreement(current_agreement, update)
            
            # Basic validation of updated agreement
            if not updated_agreement or not updated_agreement.sector:
                logger.error(f"Invalid updated agreement for sector {update.sector.value}")
                
                # Create validation error alert
                alert = CCNLAlert(
                    id=f"val_error_{update.sector.value}_{datetime.utcnow().timestamp()}",
                    sector=update.sector,
                    alert_type=AlertType.VALIDATION_ERROR,
                    title=f"Errore validazione aggiornamento CCNL {update.sector.italian_name()}",
                    message="Agreement validation failed - invalid structure",
                    severity="ERROR"
                )
                self.active_alerts.append(alert)
                return False
            
            # Store updated agreement (simplified - in reality would update database)
            logger.info(f"Would store updated agreement for {update.sector.value}")
            
            # Send notification
            await self._send_update_notification(update)
            update.notification_sent = True
            
            logger.info(f"Successfully applied CCNL update for sector {update.sector.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying CCNL update: {str(e)}")
            return False
    
    async def _create_updated_agreement(self, current: CCNLAgreement, update: CCNLUpdate) -> CCNLAgreement:
        """Create updated agreement based on update information."""
        # This is a simplified version - in reality, this would parse
        # detailed update information and apply specific changes
        
        updated = current
        
        if update.update_type == UpdateType.SALARY_REVISION:
            # Apply salary increases (example: 3.2% increase)
            for salary_table in updated.salary_tables:
                salary_table.base_monthly_salary *= Decimal('1.032')
                salary_table.valid_from = update.effective_date
        
        elif update.update_type == UpdateType.COMPLETE_RENEWAL:
            # Update validity dates
            updated.valid_from = update.effective_date
            updated.valid_to = update.effective_date.replace(year=update.effective_date.year + 3)
            
            # Apply all changes specified in update
            if "salary_tables" in update.updated_fields:
                for salary_table in updated.salary_tables:
                    salary_table.base_monthly_salary *= Decimal('1.032')
                    salary_table.valid_from = update.effective_date
        
        return updated
    
    async def _send_update_notification(self, update: CCNLUpdate):
        """Send notification about CCNL update."""
        # In a real implementation, this would:
        # - Send emails to HR managers
        # - Post to company Slack/Teams channels
        # - Update company intranet
        # - Log to audit system
        
        logger.info(f"Sending update notification for {update.sector.value}: {update.changes_summary}")
    
    async def setup_renewal_monitoring(self, sector: CCNLSector, recipients: List[str]):
        """Set up monitoring for CCNL renewal."""
        agreement = await ccnl_service.get_current_ccnl_by_sector(sector)
        if not agreement:
            return
        
        days_until_expiry = (agreement.valid_to - date.today()).days
        
        notification = RenewalNotification(
            sector=sector,
            current_expiry=agreement.valid_to,
            days_until_expiry=days_until_expiry,
            renewal_status="PENDING" if days_until_expiry > 0 else "OVERDUE",
            notification_recipients=recipients
        )
        
        self.renewal_notifications[sector] = notification
        logger.info(f"Set up renewal monitoring for {sector.value}")
    
    async def get_active_alerts(self) -> List[CCNLAlert]:
        """Get all active alerts."""
        # Filter out expired alerts
        current_time = datetime.utcnow()
        active = [
            alert for alert in self.active_alerts 
            if not alert.expires_at or alert.expires_at > current_time
        ]
        return active
    
    async def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alert {alert_id} acknowledged")
                break
    
    async def get_update_statistics(self) -> Dict[str, Any]:
        """Get statistics about CCNL updates."""
        return {
            "total_pending_updates": len(self.pending_updates),
            "active_alerts_count": len(await self.get_active_alerts()),
            "sectors_with_renewals": len(self.renewal_notifications),
            "last_update_check": datetime.utcnow().isoformat(),
            "updates_by_type": {
                update_type.value: len([u for u in self.pending_updates if u.update_type == update_type])
                for update_type in UpdateType
            },
            "alerts_by_severity": {
                severity: len([a for a in self.active_alerts if a.severity == severity])
                for severity in ["INFO", "WARNING", "ERROR", "CRITICAL"]
            }
        }


# Global instance
ccnl_update_service = CCNLUpdateService()


async def start_ccnl_monitoring():
    """Start the CCNL monitoring background task."""
    logger.info("Starting CCNL monitoring service")
    
    while True:
        try:
            # Check for updates every 4 hours
            await ccnl_update_service.check_for_updates()
            
            # Generate expiration alerts every day
            await ccnl_update_service.generate_expiration_alerts()
            
            # Wait 4 hours before next check
            await asyncio.sleep(4 * 60 * 60)
            
        except Exception as e:
            logger.error(f"Error in CCNL monitoring: {str(e)}")
            # Wait 30 minutes before retrying on error
            await asyncio.sleep(30 * 60)