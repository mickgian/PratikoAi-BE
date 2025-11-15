#!/usr/bin/env python3
"""PratikoAI Monitoring Integration Script

This script provides a unified interface for all monitoring automation tasks:
- Run daily reports with multiple output formats
- Execute cost optimization analysis
- Perform health checks and system validation
- Backup dashboards and configurations
- Schedule and coordinate monitoring tasks

Usage:
    python monitoring/scripts/run_monitoring.py daily-report
    python monitoring/scripts/run_monitoring.py optimize-costs --threshold 2.5
    python monitoring/scripts/run_monitoring.py health-check --critical-only
    python monitoring/scripts/run_monitoring.py backup-dashboards
    python monitoring/scripts/run_monitoring.py full-suite
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MonitoringOrchestrator:
    """Orchestrates all monitoring automation tasks"""

    def __init__(self, base_dir: str = "monitoring"):
        self.base_dir = Path(base_dir)
        self.scripts_dir = self.base_dir / "scripts"
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)

        # Ensure all scripts exist and are executable
        self._verify_scripts()

    def _verify_scripts(self):
        """Verify all required scripts exist"""
        required_scripts = ["daily_report.py", "optimize_costs.py", "health_check.py", "backup_dashboards.py"]

        missing_scripts = []
        for script in required_scripts:
            script_path = self.scripts_dir / script
            if not script_path.exists():
                missing_scripts.append(script)
            else:
                # Make executable
                os.chmod(script_path, 0o755)

        if missing_scripts:
            logger.error(f"Missing required scripts: {missing_scripts}")
            sys.exit(1)

        logger.info("✅ All monitoring scripts verified")

    def run_daily_report(
        self, email: bool = False, webhook: bool = False, format_type: str = "text", output_file: str | None = None
    ) -> bool:
        """Run daily monitoring report"""
        logger.info("🚀 Running daily monitoring report...")

        cmd = [sys.executable, str(self.scripts_dir / "daily_report.py")]

        if email:
            cmd.append("--email")
        if webhook:
            cmd.append("--webhook")
        if format_type != "text":
            cmd.extend(["--format", format_type])

        # Set output file if not specified
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(self.results_dir / f"daily_report_{timestamp}.{format_type}")

        cmd.extend(["--output", output_file])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("✅ Daily report completed successfully")
            logger.info(f"   Output saved to: {output_file}")

            if email:
                logger.info("   📧 Email notifications sent")
            if webhook:
                logger.info("   🔗 Webhook notifications sent")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Daily report failed: {e}")
            if e.stderr:
                logger.error(f"   Error details: {e.stderr}")
            return False

    def run_cost_optimization(
        self, threshold: float = 2.0, detailed: bool = False, export_file: str | None = None
    ) -> bool:
        """Run cost optimization analysis"""
        logger.info("💰 Running cost optimization analysis...")

        cmd = [sys.executable, str(self.scripts_dir / "optimize_costs.py")]
        cmd.extend(["--threshold", str(threshold)])

        if detailed:
            cmd.append("--detailed")

        # Set export file if not specified
        if not export_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = str(self.results_dir / f"cost_analysis_{timestamp}.json")

        cmd.extend(["--export", export_file])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("✅ Cost optimization analysis completed")
            logger.info(f"   Analysis saved to: {export_file}")

            # Parse and show key insights
            if Path(export_file).exists():
                with open(export_file) as f:
                    analysis = json.load(f)

                savings = analysis.get("potential_monthly_savings", 0)
                insights_count = len(analysis.get("insights", []))

                logger.info(f"   Potential savings: €{savings:.2f}/month")
                logger.info(f"   Optimization insights: {insights_count}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Cost optimization failed: {e}")
            if e.stderr:
                logger.error(f"   Error details: {e.stderr}")
            return False

    def run_health_check(self, critical_only: bool = False, export_file: str | None = None) -> bool:
        """Run comprehensive health check"""
        logger.info("🏥 Running system health check...")

        cmd = [sys.executable, str(self.scripts_dir / "health_check.py")]

        if critical_only:
            cmd.append("--critical-only")

        # Set export file if not specified
        if not export_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = str(self.results_dir / f"health_check_{timestamp}.json")

        cmd.extend(["--export", export_file])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("✅ Health check completed")
            logger.info(f"   Results saved to: {export_file}")

            # Parse and show health summary
            if Path(export_file).exists():
                with open(export_file) as f:
                    health_data = json.load(f)

                overall_status = health_data.get("overall_status", "unknown")
                checks_passed = len([c for c in health_data.get("service_checks", []) if c.get("status") == "healthy"])
                total_checks = len(health_data.get("service_checks", []))

                status_icon = {"healthy": "✅", "warning": "⚠️", "critical": "🔴"}.get(overall_status, "❓")
                logger.info(f"   Overall status: {status_icon} {overall_status.upper()}")
                logger.info(f"   Checks passed: {checks_passed}/{total_checks}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Health check failed: {e}")
            if e.stderr:
                logger.error(f"   Error details: {e.stderr}")
            return False

    def run_dashboard_backup(self, compare: bool = False, cleanup_days: int | None = None) -> bool:
        """Run dashboard backup"""
        logger.info("💾 Running dashboard backup...")

        cmd = [sys.executable, str(self.scripts_dir / "backup_dashboards.py")]

        if compare:
            cmd.append("--compare")
        elif cleanup_days:
            cmd.extend(["--cleanup", str(cleanup_days)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("✅ Dashboard backup completed")

            # Show backup summary from output
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "Dashboards:" in line or "Size:" in line or "Git commit:" in line:
                        logger.info(f"   {line.strip()}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Dashboard backup failed: {e}")
            if e.stderr:
                logger.error(f"   Error details: {e.stderr}")
            return False

    def run_full_monitoring_suite(self, email: bool = False, webhook: bool = False) -> dict[str, bool]:
        """Run complete monitoring suite"""
        logger.info("🎯 Running full monitoring suite...")

        results = {}

        # 1. Health check first (validates system state)
        logger.info("\n" + "=" * 50)
        logger.info("STEP 1: System Health Check")
        logger.info("=" * 50)
        results["health_check"] = self.run_health_check()

        # 2. Dashboard backup (preserve current state)
        logger.info("\n" + "=" * 50)
        logger.info("STEP 2: Dashboard Backup")
        logger.info("=" * 50)
        results["backup"] = self.run_dashboard_backup()

        # 3. Cost optimization analysis
        logger.info("\n" + "=" * 50)
        logger.info("STEP 3: Cost Optimization Analysis")
        logger.info("=" * 50)
        results["cost_optimization"] = self.run_cost_optimization(detailed=True)

        # 4. Daily report (comprehensive summary)
        logger.info("\n" + "=" * 50)
        logger.info("STEP 4: Daily Report Generation")
        logger.info("=" * 50)
        results["daily_report"] = self.run_daily_report(email=email, webhook=webhook, format_type="html")

        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("MONITORING SUITE SUMMARY")
        logger.info("=" * 50)

        successful_tasks = sum(1 for success in results.values() if success)
        total_tasks = len(results)

        for task, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{task.replace('_', ' ').title()}: {status}")

        logger.info(f"\nOverall: {successful_tasks}/{total_tasks} tasks completed successfully")

        if successful_tasks == total_tasks:
            logger.info("🎉 Full monitoring suite completed successfully!")
        else:
            logger.warning("⚠️ Some monitoring tasks failed - check logs above")

        return results

    def schedule_monitoring_tasks(self, cron_mode: bool = False) -> bool:
        """Generate cron jobs or systemd timers for monitoring tasks"""
        logger.info("⏰ Setting up monitoring task scheduling...")

        # Generate crontab entries
        cron_entries = [
            "# PratikoAI Monitoring Automation",
            "# Daily report at 9:00 AM with email notifications",
            "0 9 * * * cd /Users/micky/PycharmProjects/PratikoAi-BE && python monitoring/scripts/run_monitoring.py daily-report --email",
            "",
            "# Cost optimization analysis every Monday at 10:00 AM",
            "0 10 * * 1 cd /Users/micky/PycharmProjects/PratikoAi-BE && python monitoring/scripts/run_monitoring.py optimize-costs --detailed",
            "",
            "# Health check every 6 hours",
            "0 */6 * * * cd /Users/micky/PycharmProjects/PratikoAi-BE && python monitoring/scripts/run_monitoring.py health-check",
            "",
            "# Dashboard backup daily at 2:00 AM",
            "0 2 * * * cd /Users/micky/PycharmProjects/PratikoAi-BE && python monitoring/scripts/run_monitoring.py backup-dashboards",
            "",
            "# Full monitoring suite weekly on Sundays at 8:00 AM",
            "0 8 * * 0 cd /Users/micky/PycharmProjects/PratikoAi-BE && python monitoring/scripts/run_monitoring.py full-suite --email --webhook",
            "",
        ]

        # Save cron file
        cron_file = self.base_dir / "crontab.monitoring"
        with open(cron_file, "w") as f:
            f.write("\n".join(cron_entries))

        logger.info(f"✅ Cron configuration generated: {cron_file}")
        logger.info("To install: crontab monitoring/crontab.monitoring")

        # Generate systemd timer files if requested
        if cron_mode:
            self._generate_systemd_timers()

        return True

    def _generate_systemd_timers(self):
        """Generate systemd timer files for monitoring"""
        logger.info("Generating systemd timer configuration...")

        systemd_dir = self.base_dir / "systemd"
        systemd_dir.mkdir(exist_ok=True)

        # Daily report service
        daily_service = """[Unit]
Description=PratikoAI Daily Monitoring Report
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/Users/micky/PycharmProjects/PratikoAi-BE
ExecStart=/usr/bin/python3 monitoring/scripts/run_monitoring.py daily-report --email
User=micky
"""

        daily_timer = """[Unit]
Description=Run PratikoAI Daily Report
Requires=pratikoai-daily-report.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
"""

        with open(systemd_dir / "pratikoai-daily-report.service", "w") as f:
            f.write(daily_service)

        with open(systemd_dir / "pratikoai-daily-report.timer", "w") as f:
            f.write(daily_timer)

        logger.info(f"✅ Systemd configuration generated: {systemd_dir}")


def main():
    parser = argparse.ArgumentParser(description="PratikoAI Monitoring Automation Orchestrator")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Daily report command
    daily_parser = subparsers.add_parser("daily-report", help="Generate daily monitoring report")
    daily_parser.add_argument("--email", action="store_true", help="Send via email")
    daily_parser.add_argument("--webhook", action="store_true", help="Send via webhook")
    daily_parser.add_argument("--format", choices=["text", "html", "json"], default="text", help="Output format")
    daily_parser.add_argument("--output", help="Output file path")

    # Cost optimization command
    cost_parser = subparsers.add_parser("optimize-costs", help="Run cost optimization analysis")
    cost_parser.add_argument("--threshold", type=float, default=2.0, help="Cost threshold per user")
    cost_parser.add_argument("--detailed", action="store_true", help="Include detailed analysis")
    cost_parser.add_argument("--export", help="Export results to file")

    # Health check command
    health_parser = subparsers.add_parser("health-check", help="Run system health check")
    health_parser.add_argument("--critical-only", action="store_true", help="Show only critical issues")
    health_parser.add_argument("--export", help="Export results to file")

    # Backup command
    backup_parser = subparsers.add_parser("backup-dashboards", help="Backup Grafana dashboards")
    backup_parser.add_argument("--compare", action="store_true", help="Compare with previous backups")
    backup_parser.add_argument("--cleanup", type=int, help="Clean up backups older than days")

    # Full suite command
    suite_parser = subparsers.add_parser("full-suite", help="Run complete monitoring suite")
    suite_parser.add_argument("--email", action="store_true", help="Enable email notifications")
    suite_parser.add_argument("--webhook", action="store_true", help="Enable webhook notifications")

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Set up monitoring task scheduling")
    schedule_parser.add_argument("--cron", action="store_true", help="Generate systemd timers too")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create orchestrator
    orchestrator = MonitoringOrchestrator()

    # Execute command
    success = True

    if args.command == "daily-report":
        success = orchestrator.run_daily_report(
            email=args.email, webhook=args.webhook, format_type=args.format, output_file=args.output
        )

    elif args.command == "optimize-costs":
        success = orchestrator.run_cost_optimization(
            threshold=args.threshold, detailed=args.detailed, export_file=args.export
        )

    elif args.command == "health-check":
        success = orchestrator.run_health_check(critical_only=args.critical_only, export_file=args.export)

    elif args.command == "backup-dashboards":
        success = orchestrator.run_dashboard_backup(compare=args.compare, cleanup_days=args.cleanup)

    elif args.command == "full-suite":
        results = orchestrator.run_full_monitoring_suite(email=args.email, webhook=args.webhook)
        success = all(results.values())

    elif args.command == "schedule":
        success = orchestrator.schedule_monitoring_tasks(cron_mode=args.cron)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
