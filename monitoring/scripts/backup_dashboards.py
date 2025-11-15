#!/usr/bin/env python3
"""PratikoAI Dashboard Backup and Version Control Script

This script backs up Grafana dashboards, settings, and configurations:
- Export all dashboards to JSON files
- Version control dashboard changes with Git
- Backup Grafana settings and data sources
- Create dashboard snapshots for disaster recovery
- Compare dashboard versions and track changes

Usage:
    python monitoring/scripts/backup_dashboards.py
    python monitoring/scripts/backup_dashboards.py --export
    python monitoring/scripts/backup_dashboards.py --restore dashboard_id
    python monitoring/scripts/backup_dashboards.py --compare
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DashboardInfo:
    """Data class for dashboard information"""

    id: int
    uid: str
    title: str
    url: str
    type: str
    version: int
    created: str
    updated: str
    folder_title: str
    tags: list[str]


@dataclass
class BackupMetadata:
    """Data class for backup metadata"""

    backup_date: str
    backup_type: str
    grafana_version: str
    dashboard_count: int
    datasource_count: int
    backup_size_mb: float
    git_commit_hash: str | None
    dashboards: list[DashboardInfo]


class GrafanaClient:
    """Client for Grafana API operations"""

    def __init__(self, base_url: str = "http://localhost:3000", username: str = "admin", password: str = "admin"):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def test_connection(self) -> bool:
        """Test connection to Grafana"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Cannot connect to Grafana: {e}")
            return False

    def get_grafana_version(self) -> str:
        """Get Grafana version"""
        try:
            response = self.session.get(f"{self.base_url}/api/admin/settings")
            if response.status_code == 200:
                data = response.json()
                return data.get("buildInfo", {}).get("version", "unknown")
        except Exception:
            pass
        return "unknown"

    def get_all_dashboards(self) -> list[dict[str, Any]]:
        """Get list of all dashboards"""
        try:
            response = self.session.get(f"{self.base_url}/api/search?type=dash-db")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get dashboard list: {e}")
            return []

    def get_dashboard_by_uid(self, uid: str) -> dict[str, Any] | None:
        """Get dashboard by UID"""
        try:
            response = self.session.get(f"{self.base_url}/api/dashboards/uid/{uid}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get dashboard {uid}: {e}")
            return None

    def get_all_datasources(self) -> list[dict[str, Any]]:
        """Get all data sources"""
        try:
            response = self.session.get(f"{self.base_url}/api/datasources")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get datasources: {e}")
            return []

    def get_folders(self) -> list[dict[str, Any]]:
        """Get all folders"""
        try:
            response = self.session.get(f"{self.base_url}/api/folders")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get folders: {e}")
            return []

    def create_dashboard(self, dashboard_data: dict[str, Any]) -> bool:
        """Create or update dashboard"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/dashboards/db", json=dashboard_data, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            logger.info("Dashboard created/updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return False


class DashboardBackupManager:
    """Main dashboard backup manager"""

    def __init__(
        self,
        grafana_url: str = "http://localhost:3000",
        backup_dir: str = "monitoring/backups",
        git_enabled: bool = True,
    ):
        self.grafana = GrafanaClient(grafana_url)
        self.backup_dir = Path(backup_dir)
        self.git_enabled = git_enabled
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create backup directory structure
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        (self.backup_dir / "dashboards").mkdir(exist_ok=True)
        (self.backup_dir / "datasources").mkdir(exist_ok=True)
        (self.backup_dir / "snapshots").mkdir(exist_ok=True)
        (self.backup_dir / "metadata").mkdir(exist_ok=True)

    def create_full_backup(self) -> tuple[bool, BackupMetadata]:
        """Create complete backup of Grafana configuration"""
        logger.info("Starting full Grafana backup...")

        if not self.grafana.test_connection():
            logger.error("Cannot connect to Grafana")
            return False, None

        # Get Grafana version
        grafana_version = self.grafana.get_grafana_version()
        logger.info(f"Backing up Grafana version: {grafana_version}")

        # Backup dashboards
        dashboard_success, dashboard_infos = self.backup_dashboards()
        if not dashboard_success:
            return False, None

        # Backup datasources
        datasource_success, datasource_count = self.backup_datasources()
        if not datasource_success:
            return False, None

        # Calculate backup size
        backup_size = self._calculate_backup_size()

        # Create git commit if enabled
        git_commit = None
        if self.git_enabled:
            git_commit = self._create_git_backup()

        # Create metadata
        metadata = BackupMetadata(
            backup_date=datetime.now().isoformat(),
            backup_type="full",
            grafana_version=grafana_version,
            dashboard_count=len(dashboard_infos),
            datasource_count=datasource_count,
            backup_size_mb=backup_size,
            git_commit_hash=git_commit,
            dashboards=dashboard_infos,
        )

        # Save metadata
        metadata_file = self.backup_dir / "metadata" / f"backup_{self.timestamp}.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, indent=2, default=str)

        logger.info("✅ Full backup completed successfully")
        logger.info(f"   Dashboards: {len(dashboard_infos)}")
        logger.info(f"   Datasources: {datasource_count}")
        logger.info(f"   Size: {backup_size:.2f} MB")
        if git_commit:
            logger.info(f"   Git commit: {git_commit[:8]}")

        return True, metadata

    def backup_dashboards(self) -> tuple[bool, list[DashboardInfo]]:
        """Backup all dashboards"""
        logger.info("Backing up dashboards...")

        dashboards = self.grafana.get_all_dashboards()
        if not dashboards:
            logger.warning("No dashboards found")
            return True, []

        dashboard_infos = []
        successful_backups = 0

        for dash_summary in dashboards:
            uid = dash_summary.get("uid")
            title = dash_summary.get("title", "Untitled")

            if not uid:
                logger.warning(f"Dashboard '{title}' has no UID, skipping")
                continue

            # Get full dashboard data
            dashboard_data = self.grafana.get_dashboard_by_uid(uid)
            if not dashboard_data:
                logger.error(f"Failed to get dashboard data for '{title}'")
                continue

            # Create dashboard info
            dashboard_info = DashboardInfo(
                id=dash_summary.get("id", 0),
                uid=uid,
                title=title,
                url=dash_summary.get("url", ""),
                type=dash_summary.get("type", ""),
                version=dashboard_data.get("dashboard", {}).get("version", 0),
                created=str(dash_summary.get("created", "")),
                updated=str(dash_summary.get("updated", "")),
                folder_title=dash_summary.get("folderTitle", "General"),
                tags=dashboard_data.get("dashboard", {}).get("tags", []),
            )
            dashboard_infos.append(dashboard_info)

            # Save dashboard JSON
            filename = self._sanitize_filename(f"{title}_{uid}.json")
            dashboard_file = self.backup_dir / "dashboards" / filename

            # Save with metadata
            backup_data = {
                "meta": dashboard_data.get("meta", {}),
                "dashboard": dashboard_data.get("dashboard", {}),
                "backup_info": {
                    "backup_date": datetime.now().isoformat(),
                    "grafana_url": self.grafana.base_url,
                    "original_uid": uid,
                },
            }

            with open(dashboard_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, default=str)

            successful_backups += 1
            logger.info(f"  ✓ Backed up: {title}")

        logger.info(f"Backed up {successful_backups}/{len(dashboards)} dashboards")
        return True, dashboard_infos

    def backup_datasources(self) -> tuple[bool, int]:
        """Backup all data sources"""
        logger.info("Backing up datasources...")

        datasources = self.grafana.get_all_datasources()
        if not datasources:
            logger.warning("No datasources found")
            return True, 0

        # Save all datasources
        datasources_file = self.backup_dir / "datasources" / f"datasources_{self.timestamp}.json"

        # Clean sensitive data
        clean_datasources = []
        for ds in datasources:
            clean_ds = ds.copy()
            # Remove sensitive fields
            for sensitive_field in ["password", "secureJsonData", "basicAuthPassword"]:
                if sensitive_field in clean_ds:
                    clean_ds[sensitive_field] = "***REDACTED***"
            clean_datasources.append(clean_ds)

        backup_data = {
            "datasources": clean_datasources,
            "backup_info": {
                "backup_date": datetime.now().isoformat(),
                "count": len(datasources),
                "note": "Sensitive data has been redacted for security",
            },
        }

        with open(datasources_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, default=str)

        logger.info(f"Backed up {len(datasources)} datasources")
        return True, len(datasources)

    def restore_dashboard(self, dashboard_file: str, overwrite: bool = False) -> bool:
        """Restore dashboard from backup file"""
        logger.info(f"Restoring dashboard from {dashboard_file}")

        try:
            with open(dashboard_file, encoding="utf-8") as f:
                backup_data = json.load(f)

            dashboard = backup_data.get("dashboard", {})
            if not dashboard:
                logger.error("Invalid backup file: no dashboard data found")
                return False

            # Prepare for restore
            restore_data = {
                "dashboard": dashboard,
                "overwrite": overwrite,
                "message": f"Restored from backup {datetime.now().isoformat()}",
            }

            # Remove ID for new creation, keep UID for update
            if not overwrite:
                restore_data["dashboard"].pop("id", None)

            success = self.grafana.create_dashboard(restore_data)
            if success:
                logger.info(f"✅ Dashboard '{dashboard.get('title')}' restored successfully")

            return success

        except Exception as e:
            logger.error(f"Failed to restore dashboard: {e}")
            return False

    def compare_dashboards(self, days_back: int = 7) -> dict[str, Any]:
        """Compare current dashboards with previous backups"""
        logger.info(f"Comparing dashboards with backups from last {days_back} days...")

        # Get current dashboards
        current_dashboards = self.grafana.get_all_dashboards()
        current_by_uid = {d["uid"]: d for d in current_dashboards}

        # Find recent backup files
        cutoff_date = datetime.now() - timedelta(days=days_back)
        backup_files = []

        metadata_dir = self.backup_dir / "metadata"
        if metadata_dir.exists():
            for file in metadata_dir.glob("backup_*.json"):
                try:
                    timestamp_str = file.stem.split("_", 1)[1]
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    if file_date >= cutoff_date:
                        backup_files.append((file_date, file))
                except ValueError:
                    continue

        if not backup_files:
            logger.warning(f"No backup files found from last {days_back} days")
            return {"changes": [], "summary": "No backups to compare"}

        # Get most recent backup
        backup_files.sort(reverse=True)
        most_recent_backup = backup_files[0][1]

        with open(most_recent_backup, encoding="utf-8") as f:
            backup_metadata = json.load(f)

        # Compare dashboards
        changes = []
        backup_dashboards = {d["uid"]: d for d in backup_metadata["dashboards"]}

        # Check for new dashboards
        for uid, current in current_by_uid.items():
            if uid not in backup_dashboards:
                changes.append(
                    {"type": "added", "uid": uid, "title": current["title"], "description": "New dashboard added"}
                )

        # Check for deleted dashboards
        for uid, backup in backup_dashboards.items():
            if uid not in current_by_uid:
                changes.append(
                    {"type": "deleted", "uid": uid, "title": backup["title"], "description": "Dashboard deleted"}
                )

        # Check for modified dashboards
        for uid in set(current_by_uid.keys()) & set(backup_dashboards.keys()):
            current_dash = current_by_uid[uid]
            backup_dash = backup_dashboards[uid]

            # Compare versions
            current_version = self._get_dashboard_version(uid)
            backup_version = backup_dash.get("version", 0)

            if current_version > backup_version:
                changes.append(
                    {
                        "type": "modified",
                        "uid": uid,
                        "title": current_dash["title"],
                        "description": f"Version changed from {backup_version} to {current_version}",
                        "version_change": current_version - backup_version,
                    }
                )

        summary = f"Found {len(changes)} changes since {most_recent_backup.stem}"

        logger.info(f"Dashboard comparison complete: {len(changes)} changes found")
        return {"changes": changes, "summary": summary, "backup_date": backup_files[0][0].isoformat()}

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """Clean up old backup files"""
        logger.info(f"Cleaning up backups older than {keep_days} days...")

        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_count = 0

        # Clean up metadata files
        metadata_dir = self.backup_dir / "metadata"
        if metadata_dir.exists():
            for file in metadata_dir.glob("backup_*.json"):
                try:
                    timestamp_str = file.stem.split("_", 1)[1]
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    if file_date < cutoff_date:
                        file.unlink()
                        deleted_count += 1
                        logger.info(f"  Deleted old backup: {file.name}")
                except ValueError:
                    continue

        # Clean up old dashboard files (keep only latest versions)
        self._cleanup_duplicate_dashboards()

        logger.info(f"Cleaned up {deleted_count} old backup files")
        return deleted_count

    def _get_dashboard_version(self, uid: str) -> int:
        """Get current version of a dashboard"""
        dashboard_data = self.grafana.get_dashboard_by_uid(uid)
        if dashboard_data:
            return dashboard_data.get("dashboard", {}).get("version", 0)
        return 0

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for cross-platform compatibility"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        return filename[:200]  # Limit length

    def _calculate_backup_size(self) -> float:
        """Calculate total backup size in MB"""
        total_size = 0
        for root, _dirs, files in os.walk(self.backup_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)  # Convert to MB

    def _create_git_backup(self) -> str | None:
        """Create git commit for backup"""
        try:
            # Check if git repo exists
            git_dir = self.backup_dir / ".git"
            if not git_dir.exists():
                subprocess.run(["git", "init"], cwd=self.backup_dir, check=True)
                logger.info("Initialized git repository for backups")

            # Add all files
            subprocess.run(["git", "add", "."], cwd=self.backup_dir, check=True)

            # Create commit
            commit_message = f"Grafana backup {self.timestamp}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message], cwd=self.backup_dir, capture_output=True, text=True
            )

            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=self.backup_dir, capture_output=True, text=True
                )

                if hash_result.returncode == 0:
                    commit_hash = hash_result.stdout.strip()
                    logger.info(f"Created git commit: {commit_hash[:8]}")
                    return commit_hash

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git backup failed: {e}")
        except Exception as e:
            logger.warning(f"Git backup error: {e}")

        return None

    def _cleanup_duplicate_dashboards(self):
        """Remove duplicate dashboard files, keep only latest"""
        dashboard_dir = self.backup_dir / "dashboards"
        if not dashboard_dir.exists():
            return

        # Group files by dashboard UID
        dashboard_files = {}
        for file in dashboard_dir.glob("*.json"):
            try:
                parts = file.stem.split("_")
                if len(parts) >= 2:
                    uid = parts[-1]
                    if uid not in dashboard_files:
                        dashboard_files[uid] = []
                    dashboard_files[uid].append(file)
            except Exception:
                continue

        # Keep only latest file for each UID
        for uid, files in dashboard_files.items():
            if len(files) > 1:
                # Sort by modification time, keep newest
                files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                for old_file in files[1:]:
                    old_file.unlink()
                    logger.info(f"  Removed duplicate: {old_file.name}")


def format_comparison_report(comparison: dict[str, Any]) -> str:
    """Format dashboard comparison report"""
    output = f"""
Grafana Dashboard Comparison Report
{"=" * 50}

Backup Date: {comparison.get("backup_date", "Unknown")}
Summary: {comparison["summary"]}

"""

    changes = comparison.get("changes", [])
    if not changes:
        output += "✅ No changes detected - all dashboards are up to date.\n"
        return output

    # Group changes by type
    by_type = {}
    for change in changes:
        change_type = change["type"]
        if change_type not in by_type:
            by_type[change_type] = []
        by_type[change_type].append(change)

    # Format each type
    type_icons = {"added": "➕", "deleted": "➖", "modified": "📝"}

    for change_type, type_changes in by_type.items():
        icon = type_icons.get(change_type, "📄")
        output += f"{icon} {change_type.upper()} DASHBOARDS ({len(type_changes)})\n"
        output += "-" * 30 + "\n"

        for change in type_changes:
            output += f"  • {change['title']} ({change['uid']})\n"
            output += f"    {change['description']}\n"

        output += "\n"

    return output


def main():
    parser = argparse.ArgumentParser(description="Backup and restore Grafana dashboards")
    parser.add_argument("--export", action="store_true", help="Export all dashboards")
    parser.add_argument("--restore", help="Restore dashboard from file")
    parser.add_argument("--compare", action="store_true", help="Compare with previous backups")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Clean up backups older than DAYS")
    parser.add_argument("--backup-dir", default="monitoring/backups", help="Backup directory")
    parser.add_argument("--grafana-url", default="http://localhost:3000", help="Grafana URL")
    parser.add_argument("--no-git", action="store_true", help="Disable git version control")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing dashboards on restore")

    args = parser.parse_args()

    # Create backup manager
    backup_manager = DashboardBackupManager(
        grafana_url=args.grafana_url, backup_dir=args.backup_dir, git_enabled=not args.no_git
    )

    # Execute requested operation
    if args.restore:
        success = backup_manager.restore_dashboard(args.restore, args.overwrite)
        exit(0 if success else 1)

    elif args.compare:
        comparison = backup_manager.compare_dashboards()
        print(format_comparison_report(comparison))

    elif args.cleanup:
        deleted_count = backup_manager.cleanup_old_backups(args.cleanup)
        logger.info(f"Cleanup complete: removed {deleted_count} old files")

    else:
        # Default: create full backup
        success, metadata = backup_manager.create_full_backup()
        if success:
            logger.info("✅ Backup completed successfully")
            logger.info(f"Location: {args.backup_dir}")
            if metadata:
                logger.info(f"Dashboards: {metadata.dashboard_count}")
                logger.info(f"Size: {metadata.backup_size_mb:.2f} MB")
        else:
            logger.error("❌ Backup failed")
            exit(1)


if __name__ == "__main__":
    main()
