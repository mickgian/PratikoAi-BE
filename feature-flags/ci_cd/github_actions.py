#!/usr/bin/env python3
"""
PratikoAI Feature Flag CI/CD Integration

GitHub Actions integration for automated feature flag management,
testing with different flag states, and deployment coordination.
"""

import os
import json
import yaml
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from github import Github
import click

logger = logging.getLogger(__name__)


@dataclass
class FlagScenario:
    """Feature flag test scenario configuration."""
    name: str
    description: str
    flags: Dict[str, Any]
    environment: str = "testing"
    enabled: bool = True


@dataclass
class DeploymentConfig:
    """Deployment-specific flag configuration."""
    environment: str
    flags_to_enable: List[str] = field(default_factory=list)
    flags_to_disable: List[str] = field(default_factory=list)
    flags_to_verify: List[str] = field(default_factory=list)
    rollback_flags: Dict[str, Any] = field(default_factory=dict)


class FeatureFlagCICD:
    """CI/CD integration for feature flags."""
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        github_token: Optional[str] = None,
        repository: Optional[str] = None
    ):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.github_token = github_token
        self.repository = repository
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(
            timeout=30,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "PratikoAI-CICD/1.0.0"
            }
        )
        
        # GitHub client
        self.github = None
        if github_token:
            self.github = Github(github_token)
    
    async def setup_flag_scenarios(self, scenarios_file: str = "flag-scenarios.yaml"):
        """Set up feature flag test scenarios."""
        if not os.path.exists(scenarios_file):
            await self._create_default_scenarios(scenarios_file)
        
        with open(scenarios_file, 'r') as f:
            scenarios_data = yaml.safe_load(f)
        
        scenarios = []
        for scenario_data in scenarios_data.get("scenarios", []):
            scenario = FlagScenario(
                name=scenario_data["name"],
                description=scenario_data["description"],
                flags=scenario_data["flags"],
                environment=scenario_data.get("environment", "testing"),
                enabled=scenario_data.get("enabled", True)
            )
            scenarios.append(scenario)
        
        return scenarios
    
    async def _create_default_scenarios(self, scenarios_file: str):
        """Create default flag scenarios file."""
        default_scenarios = {
            "scenarios": [
                {
                    "name": "all_flags_off",
                    "description": "All feature flags disabled",
                    "environment": "testing",
                    "flags": {},
                    "enabled": True
                },
                {
                    "name": "all_flags_on",
                    "description": "All feature flags enabled",
                    "environment": "testing",
                    "flags": {
                        "new_dashboard_ui": True,
                        "enhanced_api_v2": True,
                        "advanced_analytics": True
                    },
                    "enabled": True
                },
                {
                    "name": "production_flags",
                    "description": "Production flag configuration",
                    "environment": "testing",
                    "flags": {
                        "new_dashboard_ui": False,
                        "enhanced_api_v2": True,
                        "advanced_analytics": False
                    },
                    "enabled": True
                },
                {
                    "name": "beta_user_flags",
                    "description": "Beta user experience",
                    "environment": "testing",
                    "flags": {
                        "new_dashboard_ui": True,
                        "beta_features": True,
                        "experimental_ui": True
                    },
                    "enabled": True
                }
            ]
        }
        
        with open(scenarios_file, 'w') as f:
            yaml.dump(default_scenarios, f, default_flow_style=False)
        
        logger.info(f"Created default scenarios file: {scenarios_file}")
    
    async def apply_flag_scenario(self, scenario: FlagScenario):
        """Apply a flag scenario to the testing environment."""
        logger.info(f"Applying flag scenario: {scenario.name}")
        
        for flag_id, value in scenario.flags.items():
            try:
                await self._update_flag_environment(flag_id, scenario.environment, value, enabled=True)
                logger.info(f"Set flag {flag_id} = {value} in {scenario.environment}")
            except Exception as e:
                logger.error(f"Failed to set flag {flag_id}: {e}")
                raise
    
    async def _update_flag_environment(self, flag_id: str, environment: str, value: Any, enabled: bool = True):
        """Update flag configuration for specific environment."""
        url = f"{self.api_url}/api/v1/flags/{flag_id}/environments/{environment}"
        
        payload = {
            "flag_id": flag_id,
            "environment": environment,
            "value": value,
            "enabled": enabled,
            "targeting_rules": [],
            "rollout_percentage": 100.0
        }
        
        response = await self.http_client.put(url, json=payload)
        response.raise_for_status()
    
    async def toggle_flag(self, flag_id: str, environment: str, enabled: bool):
        """Toggle a flag on/off for an environment."""
        url = f"{self.api_url}/api/v1/flags/{flag_id}/toggle/{environment}"
        params = {"enabled": enabled}
        
        response = await self.http_client.post(url, params=params)
        response.raise_for_status()
        
        logger.info(f"Toggled flag {flag_id} to {'enabled' if enabled else 'disabled'} in {environment}")
    
    async def verify_flags(self, flag_ids: List[str], environment: str, expected_values: Dict[str, Any] = None):
        """Verify that flags are set to expected values."""
        logger.info(f"Verifying flags in {environment}: {flag_ids}")
        
        verification_results = {}
        
        for flag_id in flag_ids:
            try:
                # Get current flag value
                current_value = await self._get_flag_value(flag_id, environment)
                
                if expected_values and flag_id in expected_values:
                    expected = expected_values[flag_id]
                    matches = current_value == expected
                    verification_results[flag_id] = {
                        "current_value": current_value,
                        "expected_value": expected,
                        "matches": matches
                    }
                    
                    if not matches:
                        logger.error(f"Flag {flag_id} verification failed: expected {expected}, got {current_value}")
                else:
                    verification_results[flag_id] = {
                        "current_value": current_value,
                        "verified": True
                    }
                    
            except Exception as e:
                logger.error(f"Failed to verify flag {flag_id}: {e}")
                verification_results[flag_id] = {
                    "error": str(e),
                    "verified": False
                }
        
        return verification_results
    
    async def _get_flag_value(self, flag_id: str, environment: str):
        """Get current flag value for environment."""
        url = f"{self.api_url}/api/v1/flags/{flag_id}"
        response = await self.http_client.get(url)
        response.raise_for_status()
        
        flag_data = response.json()
        env_config = flag_data.get("environments", {}).get(environment, {})
        return env_config.get("value", flag_data.get("default_value"))
    
    async def handle_deployment_flags(self, deployment_config: DeploymentConfig):
        """Handle flag changes during deployment."""
        logger.info(f"Handling deployment flags for {deployment_config.environment}")
        
        # Enable specified flags
        for flag_id in deployment_config.flags_to_enable:
            await self.toggle_flag(flag_id, deployment_config.environment, True)
        
        # Disable specified flags
        for flag_id in deployment_config.flags_to_disable:
            await self.toggle_flag(flag_id, deployment_config.environment, False)
        
        # Verify critical flags
        if deployment_config.flags_to_verify:
            verification_results = await self.verify_flags(
                deployment_config.flags_to_verify,
                deployment_config.environment
            )
            
            # Check if any verifications failed
            failed_verifications = [
                flag_id for flag_id, result in verification_results.items()
                if not result.get("verified", True) or not result.get("matches", True)
            ]
            
            if failed_verifications:
                raise Exception(f"Flag verification failed for: {failed_verifications}")
    
    async def create_flag_backup(self, environment: str, backup_file: str = None):
        """Create backup of current flag states."""
        if not backup_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"flag_backup_{environment}_{timestamp}.json"
        
        # Get all flags for environment
        url = f"{self.api_url}/api/v1/flags"
        params = {"environment": environment}
        response = await self.http_client.get(url, params=params)
        response.raise_for_status()
        
        flags_data = response.json()
        
        backup = {
            "environment": environment,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "flags": flags_data
        }
        
        with open(backup_file, 'w') as f:
            json.dump(backup, f, indent=2)
        
        logger.info(f"Flag backup created: {backup_file}")
        return backup_file
    
    async def restore_flag_backup(self, backup_file: str):
        """Restore flags from backup file."""
        with open(backup_file, 'r') as f:
            backup = json.load(f)
        
        environment = backup["environment"]
        logger.info(f"Restoring flags for {environment} from {backup_file}")
        
        # Restore each flag
        for flag in backup["flags"]["flags"]:
            flag_id = flag["flag_id"]
            env_config = flag.get("environments", {}).get(environment)
            
            if env_config:
                try:
                    await self._update_flag_environment(
                        flag_id,
                        environment,
                        env_config["value"],
                        env_config["enabled"]
                    )
                    logger.info(f"Restored flag {flag_id}")
                except Exception as e:
                    logger.error(f"Failed to restore flag {flag_id}: {e}")
    
    async def generate_flag_dependency_report(self, repository_path: str = "."):
        """Generate report of flag dependencies across repositories."""
        dependencies = {}
        
        # Search for flag usage in code
        for file_path in Path(repository_path).rglob("*.py"):
            await self._scan_file_for_flags(file_path, dependencies)
        
        for file_path in Path(repository_path).rglob("*.kt"):
            await self._scan_file_for_flags(file_path, dependencies)
        
        for file_path in Path(repository_path).rglob("*.js"):
            await self._scan_file_for_flags(file_path, dependencies)
        
        for file_path in Path(repository_path).rglob("*.ts"):
            await self._scan_file_for_flags(file_path, dependencies)
        
        # Generate report
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repository": self.repository or "unknown",
            "flag_dependencies": dependencies,
            "summary": {
                "total_flags_used": len(dependencies),
                "total_file_references": sum(len(refs["files"]) for refs in dependencies.values())
            }
        }
        
        report_file = "flag_dependency_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Flag dependency report generated: {report_file}")
        return report
    
    async def _scan_file_for_flags(self, file_path: Path, dependencies: Dict):
        """Scan file for feature flag usage."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Common patterns for flag usage
            patterns = [
                r'isEnabled\(["\']([^"\']+)["\']',  # isEnabled("flag_name")
                r'getValue\(["\']([^"\']+)["\']',   # getValue("flag_name")
                r'feature_flag\(["\']([^"\']+)["\']',  # @feature_flag("flag_name")
                r'flag_client\..*?\(["\']([^"\']+)["\']',  # flag_client.method("flag_name")
            ]
            
            import re
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for flag_id in matches:
                    if flag_id not in dependencies:
                        dependencies[flag_id] = {
                            "flag_id": flag_id,
                            "files": [],
                            "usage_count": 0
                        }
                    
                    if str(file_path) not in [f["file"] for f in dependencies[flag_id]["files"]]:
                        dependencies[flag_id]["files"].append({
                            "file": str(file_path),
                            "relative_path": str(file_path.relative_to(Path.cwd()))
                        })
                    
                    dependencies[flag_id]["usage_count"] += len(matches)
        
        except Exception as e:
            logger.warning(f"Failed to scan {file_path}: {e}")
    
    async def post_github_comment(self, pr_number: int, comment: str):
        """Post comment to GitHub PR with flag information."""
        if not self.github or not self.repository:
            logger.warning("GitHub integration not configured")
            return
        
        try:
            repo = self.github.get_repo(self.repository)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            
            logger.info(f"Posted comment to PR #{pr_number}")
        except Exception as e:
            logger.error(f"Failed to post GitHub comment: {e}")
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# CLI Interface
@click.group()
@click.option('--api-url', envvar='FEATURE_FLAG_API_URL', required=True)
@click.option('--api-key', envvar='FEATURE_FLAG_API_KEY', required=True)
@click.option('--github-token', envvar='GITHUB_TOKEN')
@click.option('--repository', envvar='GITHUB_REPOSITORY')
@click.pass_context
def cli(ctx, api_url, api_key, github_token, repository):
    """PratikoAI Feature Flag CI/CD CLI"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = FeatureFlagCICD(api_url, api_key, github_token, repository)


@cli.command()
@click.option('--scenario', required=True, help='Scenario name to apply')
@click.option('--scenarios-file', default='flag-scenarios.yaml', help='Scenarios configuration file')
@click.pass_context
def apply_scenario(ctx, scenario, scenarios_file):
    """Apply a feature flag scenario."""
    async def run():
        client = ctx.obj['client']
        scenarios = await client.setup_flag_scenarios(scenarios_file)
        
        target_scenario = next((s for s in scenarios if s.name == scenario), None)
        if not target_scenario:
            click.echo(f"Scenario '{scenario}' not found")
            return
        
        await client.apply_flag_scenario(target_scenario)
        click.echo(f"Applied scenario: {scenario}")
        
        await client.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--flag-id', required=True, help='Flag ID to toggle')
@click.option('--environment', required=True, help='Environment name')
@click.option('--enabled/--disabled', default=True, help='Enable or disable flag')
@click.pass_context
def toggle(ctx, flag_id, environment, enabled):
    """Toggle a feature flag."""
    async def run():
        client = ctx.obj['client']
        await client.toggle_flag(flag_id, environment, enabled)
        click.echo(f"Toggled {flag_id} to {'enabled' if enabled else 'disabled'} in {environment}")
        await client.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--environment', required=True, help='Environment to verify')
@click.option('--flags', required=True, help='Comma-separated list of flag IDs')
@click.pass_context
def verify(ctx, environment, flags):
    """Verify feature flag states."""
    async def run():
        client = ctx.obj['client']
        flag_ids = [f.strip() for f in flags.split(',')]
        
        results = await client.verify_flags(flag_ids, environment)
        
        click.echo(f"Verification results for {environment}:")
        for flag_id, result in results.items():
            if 'error' in result:
                click.echo(f"  ❌ {flag_id}: ERROR - {result['error']}")
            elif result.get('matches', True):
                click.echo(f"  ✅ {flag_id}: {result['current_value']}")
            else:
                click.echo(f"  ❌ {flag_id}: Expected {result['expected_value']}, got {result['current_value']}")
        
        await client.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--environment', required=True, help='Environment to backup')
@click.option('--backup-file', help='Backup file name')
@click.pass_context
def backup(ctx, environment, backup_file):
    """Create flag backup."""
    async def run():
        client = ctx.obj['client']
        backup_path = await client.create_flag_backup(environment, backup_file)
        click.echo(f"Backup created: {backup_path}")
        await client.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--backup-file', required=True, help='Backup file to restore')
@click.pass_context
def restore(ctx, backup_file):
    """Restore flags from backup."""
    async def run():
        client = ctx.obj['client']
        await client.restore_flag_backup(backup_file)
        click.echo(f"Restored flags from: {backup_file}")
        await client.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--repository-path', default='.', help='Repository path to scan')
@click.pass_context
def dependency_report(ctx, repository_path):
    """Generate flag dependency report."""
    async def run():
        client = ctx.obj['client']
        report = await client.generate_flag_dependency_report(repository_path)
        click.echo(f"Dependency report generated with {report['summary']['total_flags_used']} flags")
        await client.close()
    
    asyncio.run(run())


if __name__ == '__main__':
    cli()