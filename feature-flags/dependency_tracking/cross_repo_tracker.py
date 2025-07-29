#!/usr/bin/env python3
"""
PratikoAI Cross-Repository Feature Flag Dependency Tracker

Advanced system for tracking and managing feature flag dependencies across 
multiple repositories, ensuring coordinated rollouts and preventing conflicts.
"""

import os
import json
import yaml
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

import httpx
from github import Github
import networkx as nx
import matplotlib.pyplot as plt
from pydantic import BaseModel
import click

logger = logging.getLogger(__name__)


class DependencyType(str, Enum):
    """Types of flag dependencies."""
    REQUIRES = "requires"
    CONFLICTS = "conflicts"
    ENHANCES = "enhances"
    REPLACES = "replaces"
    DEPENDS_ON = "depends_on"


class RolloutStatus(str, Enum):
    """Status of flag rollout."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class FlagDependency:
    """Represents a dependency between two flags."""
    source_flag: str
    source_repository: str
    target_flag: str
    target_repository: str
    dependency_type: DependencyType
    description: str
    required: bool = True
    version_constraint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepositoryInfo:
    """Information about a repository."""
    name: str
    url: str
    default_branch: str = "main"
    flag_config_path: str = "flag-dependencies.yaml"
    maintainers: List[str] = field(default_factory=list)
    last_sync: Optional[datetime] = None


@dataclass
class FlagInfo:
    """Information about a feature flag."""
    flag_id: str
    repository: str
    name: str
    description: str
    created_at: datetime
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rollout_status: Dict[str, RolloutStatus] = field(default_factory=dict)
    dependencies: List[FlagDependency] = field(default_factory=list)
    dependents: List[FlagDependency] = field(default_factory=list)


@dataclass
class CoordinatedRollout:
    """Represents a coordinated rollout across repositories."""
    rollout_id: str
    name: str
    description: str
    primary_flag: str
    primary_repository: str
    dependent_flags: List[Dict[str, str]]
    environments: List[str]
    rollout_steps: List[Dict[str, Any]]
    status: RolloutStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str = "system"


class CrossRepositoryDependencyTracker:
    """Main class for tracking cross-repository flag dependencies."""
    
    def __init__(
        self,
        github_token: str,
        feature_flag_api_url: str,
        feature_flag_api_key: str,
        repositories: List[RepositoryInfo] = None
    ):
        self.github_token = github_token
        self.api_url = feature_flag_api_url.rstrip('/')
        self.api_key = feature_flag_api_key
        
        # GitHub client
        self.github = Github(github_token)
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(
            timeout=30,
            headers={
                "Authorization": f"Bearer {feature_flag_api_key}",
                "Content-Type": "application/json"
            }
        )
        
        # Repository configuration
        self.repositories = {repo.name: repo for repo in (repositories or [])}
        
        # Dependency graph
        self.dependency_graph = nx.DiGraph()
        
        # Cached data
        self.flags_cache: Dict[str, FlagInfo] = {}
        self.dependencies_cache: List[FlagDependency] = []
        
        # Active rollouts
        self.active_rollouts: Dict[str, CoordinatedRollout] = {}
    
    async def discover_repositories(self, organization: str = None, user: str = None):
        """Discover repositories with feature flag configurations."""
        repositories = []
        
        if organization:
            org = self.github.get_organization(organization)
            repos = org.get_repos()
        elif user:
            user_obj = self.github.get_user(user)
            repos = user_obj.get_repos()
        else:
            repos = self.github.get_user().get_repos()
        
        for repo in repos:
            try:
                # Check if repository has flag dependencies configuration
                try:
                    repo.get_contents("flag-dependencies.yaml")
                    has_flag_config = True
                except:
                    has_flag_config = False
                
                if has_flag_config:
                    repo_info = RepositoryInfo(
                        name=repo.full_name,
                        url=repo.html_url,
                        default_branch=repo.default_branch,
                        maintainers=[c.author.login for c in repo.get_contributors()[:3]]
                    )
                    repositories.append(repo_info)
                    
            except Exception as e:
                logger.warning(f"Failed to process repository {repo.full_name}: {e}")
        
        # Update repositories
        for repo in repositories:
            self.repositories[repo.name] = repo
        
        logger.info(f"Discovered {len(repositories)} repositories with flag configurations")
        return repositories
    
    async def load_dependencies_from_repositories(self):
        """Load flag dependencies from all configured repositories."""
        all_dependencies = []
        
        for repo_name, repo_info in self.repositories.items():
            try:
                dependencies = await self._load_repo_dependencies(repo_name, repo_info)
                all_dependencies.extend(dependencies)
                
                # Update last sync time
                repo_info.last_sync = datetime.now(timezone.utc)
                
            except Exception as e:
                logger.error(f"Failed to load dependencies from {repo_name}: {e}")
        
        self.dependencies_cache = all_dependencies
        await self._build_dependency_graph()
        
        logger.info(f"Loaded {len(all_dependencies)} dependencies from {len(self.repositories)} repositories")
        return all_dependencies
    
    async def _load_repo_dependencies(self, repo_name: str, repo_info: RepositoryInfo) -> List[FlagDependency]:
        """Load dependencies from a specific repository."""
        try:
            repo = self.github.get_repo(repo_name)
            config_content = repo.get_contents(repo_info.flag_config_path)
            
            # Parse YAML configuration
            config_data = yaml.safe_load(config_content.decoded_content.decode('utf-8'))
            
            dependencies = []
            
            # Process outgoing dependencies
            for dep_config in config_data.get("dependencies", {}).get("outgoing", []):
                dependency = FlagDependency(
                    source_flag=dep_config["flag"],
                    source_repository=repo_name,
                    target_flag=dep_config.get("target_flag", dep_config["flag"]),
                    target_repository=dep_config.get("target_repository", repo_name),
                    dependency_type=DependencyType(dep_config.get("type", "requires")),
                    description=dep_config.get("description", ""),
                    required=dep_config.get("required", True),
                    version_constraint=dep_config.get("version_constraint"),
                    metadata=dep_config.get("metadata", {})
                )
                dependencies.append(dependency)
            
            # Process incoming dependencies
            for dep_config in config_data.get("dependencies", {}).get("incoming", []):
                dependency = FlagDependency(
                    source_flag=dep_config["flag"],
                    source_repository=dep_config["repository"],
                    target_flag=dep_config.get("target_flag", dep_config["flag"]),
                    target_repository=repo_name,
                    dependency_type=DependencyType(dep_config.get("type", "depends_on")),
                    description=dep_config.get("description", ""),
                    required=dep_config.get("required", True),
                    version_constraint=dep_config.get("version_constraint"),
                    metadata=dep_config.get("metadata", {})
                )
                dependencies.append(dependency)
            
            return dependencies
            
        except Exception as e:
            logger.error(f"Failed to load dependencies from {repo_name}: {e}")
            return []
    
    async def _build_dependency_graph(self):
        """Build networkx graph from dependencies."""
        self.dependency_graph.clear()
        
        # Add nodes (flags)
        flags = set()
        for dep in self.dependencies_cache:
            flags.add(f"{dep.source_repository}:{dep.source_flag}")
            flags.add(f"{dep.target_repository}:{dep.target_flag}")
        
        self.dependency_graph.add_nodes_from(flags)
        
        # Add edges (dependencies)
        for dep in self.dependencies_cache:
            source_node = f"{dep.source_repository}:{dep.source_flag}"
            target_node = f"{dep.target_repository}:{dep.target_flag}"
            
            self.dependency_graph.add_edge(
                source_node,
                target_node,
                dependency_type=dep.dependency_type.value,
                required=dep.required,
                description=dep.description
            )
    
    async def analyze_dependency_impact(self, flag_id: str, repository: str) -> Dict[str, Any]:
        """Analyze the impact of changing a specific flag."""
        node_id = f"{repository}:{flag_id}"
        
        if node_id not in self.dependency_graph:
            return {
                "flag_id": flag_id,
                "repository": repository,
                "direct_dependencies": [],
                "transitive_dependencies": [],
                "dependent_flags": [],
                "impact_score": 0
            }
        
        # Find direct dependencies (what this flag depends on)
        direct_dependencies = []
        for pred in self.dependency_graph.predecessors(node_id):
            edge_data = self.dependency_graph[pred][node_id]
            direct_dependencies.append({
                "flag": pred.split(':', 1)[1],
                "repository": pred.split(':', 1)[0],
                "dependency_type": edge_data["dependency_type"],
                "required": edge_data["required"]
            })
        
        # Find transitive dependencies
        transitive_deps = set()
        for dep in direct_dependencies:
            dep_node = f"{dep['repository']}:{dep['flag']}"
            transitive_deps.update(nx.ancestors(self.dependency_graph, dep_node))
        
        transitive_dependencies = []
        for trans_dep in transitive_deps:
            if trans_dep != node_id:
                transitive_dependencies.append({
                    "flag": trans_dep.split(':', 1)[1],
                    "repository": trans_dep.split(':', 1)[0]
                })
        
        # Find dependent flags (what depends on this flag)
        dependent_flags = []
        for succ in self.dependency_graph.successors(node_id):
            edge_data = self.dependency_graph[node_id][succ]
            dependent_flags.append({
                "flag": succ.split(':', 1)[1],
                "repository": succ.split(':', 1)[0],
                "dependency_type": edge_data["dependency_type"],
                "required": edge_data["required"]
            })
        
        # Calculate impact score
        impact_score = len(direct_dependencies) + len(transitive_dependencies) + len(dependent_flags) * 2
        
        return {
            "flag_id": flag_id,
            "repository": repository,
            "direct_dependencies": direct_dependencies,
            "transitive_dependencies": transitive_dependencies,
            "dependent_flags": dependent_flags,
            "impact_score": impact_score,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def validate_rollout_order(self, flags: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate and suggest optimal rollout order for multiple flags."""
        flag_nodes = []
        for flag_info in flags:
            node_id = f"{flag_info['repository']}:{flag_info['flag_id']}"
            flag_nodes.append(node_id)
        
        # Create subgraph with only specified flags
        subgraph = self.dependency_graph.subgraph(flag_nodes)
        
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(subgraph))
            has_cycles = len(cycles) > 0
        except:
            has_cycles = False
            cycles = []
        
        # Generate topological order if no cycles
        if not has_cycles:
            try:
                topo_order = list(nx.topological_sort(subgraph))
                rollout_order = []
                for node in topo_order:
                    repo, flag = node.split(':', 1)
                    rollout_order.append({"repository": repo, "flag_id": flag})
            except:
                rollout_order = flags  # Fallback to original order
        else:
            rollout_order = flags
        
        # Calculate rollout complexity
        complexity_score = len(subgraph.edges()) + len(cycles) * 10
        
        return {
            "valid": not has_cycles,
            "cycles": cycles,
            "suggested_order": rollout_order,
            "complexity_score": complexity_score,
            "total_flags": len(flags),
            "total_dependencies": len(subgraph.edges()),
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def create_coordinated_rollout(
        self,
        name: str,
        description: str,
        primary_flag: str,
        primary_repository: str,
        environments: List[str] = None,
        rollout_percentages: List[int] = None
    ) -> CoordinatedRollout:
        """Create a coordinated rollout plan."""
        
        if environments is None:
            environments = ["staging", "production"]
        
        if rollout_percentages is None:
            rollout_percentages = [10, 25, 50, 100]
        
        # Analyze dependencies
        impact_analysis = await self.analyze_dependency_impact(primary_flag, primary_repository)
        
        # Include all dependent flags
        dependent_flags = []
        for dep in impact_analysis["dependent_flags"]:
            dependent_flags.append({
                "flag_id": dep["flag"],
                "repository": dep["repository"],
                "dependency_type": dep["dependency_type"]
            })
        
        # Create rollout steps
        rollout_steps = []
        for env in environments:
            for percentage in rollout_percentages:
                step = {
                    "step_id": f"{env}_{percentage}",
                    "environment": env,
                    "percentage": percentage,
                    "flags": [
                        {"flag_id": primary_flag, "repository": primary_repository}
                    ] + dependent_flags,
                    "wait_time_minutes": 30 if percentage < 100 else 0,
                    "validation_required": percentage >= 50
                }
                rollout_steps.append(step)
        
        # Create rollout
        rollout = CoordinatedRollout(
            rollout_id=f"rollout_{primary_flag}_{int(datetime.now().timestamp())}",
            name=name,
            description=description,
            primary_flag=primary_flag,
            primary_repository=primary_repository,
            dependent_flags=dependent_flags,
            environments=environments,
            rollout_steps=rollout_steps,
            status=RolloutStatus.NOT_STARTED,
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_rollouts[rollout.rollout_id] = rollout
        
        logger.info(f"Created coordinated rollout: {rollout.rollout_id}")
        return rollout
    
    async def execute_coordinated_rollout(self, rollout_id: str) -> Dict[str, Any]:
        """Execute a coordinated rollout."""
        if rollout_id not in self.active_rollouts:
            raise ValueError(f"Rollout {rollout_id} not found")
        
        rollout = self.active_rollouts[rollout_id]
        rollout.status = RolloutStatus.IN_PROGRESS
        rollout.started_at = datetime.now(timezone.utc)
        
        execution_results = []
        
        try:
            for step in rollout.rollout_steps:
                logger.info(f"Executing rollout step: {step['step_id']}")
                
                step_results = []
                
                # Execute all flags in this step
                for flag_config in step["flags"]:
                    try:
                        result = await self._update_flag_rollout(
                            flag_config["repository"],
                            flag_config["flag_id"],
                            step["environment"],
                            step["percentage"]
                        )
                        step_results.append({
                            "flag_id": flag_config["flag_id"],
                            "repository": flag_config["repository"],
                            "success": True,
                            "result": result
                        })
                    except Exception as e:
                        step_results.append({
                            "flag_id": flag_config["flag_id"],
                            "repository": flag_config["repository"],
                            "success": False,
                            "error": str(e)
                        })
                
                execution_results.append({
                    "step_id": step["step_id"],
                    "results": step_results,
                    "executed_at": datetime.now(timezone.utc).isoformat()
                })
                
                # Check for failures
                failures = [r for r in step_results if not r["success"]]
                if failures:
                    logger.error(f"Step {step['step_id']} had failures: {failures}")
                    rollout.status = RolloutStatus.FAILED
                    break
                
                # Wait before next step
                if step["wait_time_minutes"] > 0:
                    logger.info(f"Waiting {step['wait_time_minutes']} minutes before next step")
                    await asyncio.sleep(step["wait_time_minutes"] * 60)
            
            if rollout.status == RolloutStatus.IN_PROGRESS:
                rollout.status = RolloutStatus.COMPLETED
                rollout.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Rollout execution failed: {e}")
            rollout.status = RolloutStatus.FAILED
        
        return {
            "rollout_id": rollout_id,
            "status": rollout.status.value,
            "execution_results": execution_results,
            "completed_at": rollout.completed_at.isoformat() if rollout.completed_at else None
        }
    
    async def _update_flag_rollout(self, repository: str, flag_id: str, 
                                  environment: str, percentage: int):
        """Update flag rollout percentage via API."""
        config = {
            "flag_id": flag_id,
            "environment": environment,
            "rollout_percentage": percentage,
            "enabled": True
        }
        
        response = await self.http_client.put(
            f"{self.api_url}/api/v1/flags/{flag_id}/environments/{environment}",
            json=config
        )
        response.raise_for_status()
        return response.json()
    
    async def generate_dependency_report(self, output_format: str = "json") -> str:
        """Generate comprehensive dependency report."""
        # Analyze all flags
        flag_analyses = {}
        all_flags = set()
        
        for dep in self.dependencies_cache:
            all_flags.add((dep.source_repository, dep.source_flag))
            all_flags.add((dep.target_repository, dep.target_flag))
        
        for repo, flag_id in all_flags:
            analysis = await self.analyze_dependency_impact(flag_id, repo)
            flag_analyses[f"{repo}:{flag_id}"] = analysis
        
        # Create comprehensive report
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_repositories": len(self.repositories),
            "total_flags": len(all_flags),
            "total_dependencies": len(self.dependencies_cache),
            "repositories": {name: asdict(info) for name, info in self.repositories.items()},
            "dependency_summary": self._analyze_dependency_patterns(),
            "flag_analyses": flag_analyses,
            "high_impact_flags": self._identify_high_impact_flags(flag_analyses),
            "dependency_cycles": await self._find_dependency_cycles(),
            "recommendations": self._generate_recommendations(flag_analyses)
        }
        
        if output_format == "json":
            report_file = f"dependency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        elif output_format == "yaml":
            report_file = f"dependency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            with open(report_file, 'w') as f:
                yaml.dump(report, f, default_flow_style=False)
        
        logger.info(f"Generated dependency report: {report_file}")
        return report_file
    
    def _analyze_dependency_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in dependencies."""
        patterns = {
            "dependency_types": {},
            "repository_connections": {},
            "complexity_metrics": {}
        }
        
        # Count dependency types
        for dep in self.dependencies_cache:
            dep_type = dep.dependency_type.value
            patterns["dependency_types"][dep_type] = patterns["dependency_types"].get(dep_type, 0) + 1
        
        # Analyze repository connections
        for dep in self.dependencies_cache:
            connection = f"{dep.source_repository} -> {dep.target_repository}"
            patterns["repository_connections"][connection] = patterns["repository_connections"].get(connection, 0) + 1
        
        # Calculate complexity metrics
        patterns["complexity_metrics"] = {
            "average_dependencies_per_flag": len(self.dependencies_cache) / max(len(self.dependency_graph.nodes()), 1),
            "max_dependency_chain_length": self._calculate_max_chain_length(),
            "strongly_connected_components": len(list(nx.strongly_connected_components(self.dependency_graph)))
        }
        
        return patterns
    
    def _calculate_max_chain_length(self) -> int:
        """Calculate the maximum dependency chain length."""
        if not self.dependency_graph.nodes():
            return 0
        
        try:
            return max(len(nx.shortest_path(self.dependency_graph, source, target)) - 1
                      for source in self.dependency_graph.nodes()
                      for target in self.dependency_graph.nodes()
                      if nx.has_path(self.dependency_graph, source, target))
        except:
            return 0
    
    def _identify_high_impact_flags(self, flag_analyses: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify flags with high impact scores."""
        high_impact = [
            {
                "flag": flag_key,
                "impact_score": analysis["impact_score"],
                "dependent_flags_count": len(analysis["dependent_flags"]),
                "total_dependencies": len(analysis["direct_dependencies"]) + len(analysis["transitive_dependencies"])
            }
            for flag_key, analysis in flag_analyses.items()
            if analysis["impact_score"] >= 5
        ]
        
        return sorted(high_impact, key=lambda x: x["impact_score"], reverse=True)
    
    async def _find_dependency_cycles(self) -> List[List[str]]:
        """Find dependency cycles in the graph."""
        try:
            return list(nx.simple_cycles(self.dependency_graph))
        except:
            return []
    
    def _generate_recommendations(self, flag_analyses: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on dependency analysis."""
        recommendations = []
        
        # Check for high impact flags
        high_impact_flags = self._identify_high_impact_flags(flag_analyses)
        if high_impact_flags:
            recommendations.append(
                f"Consider extra caution when modifying these high-impact flags: "
                f"{', '.join([f['flag'] for f in high_impact_flags[:3]])}"
            )
        
        # Check for cycles
        cycles = list(nx.simple_cycles(self.dependency_graph))
        if cycles:
            recommendations.append(
                f"Found {len(cycles)} dependency cycles that should be resolved to prevent deadlocks"
            )
        
        # Check for orphaned flags
        orphaned = [node for node in self.dependency_graph.nodes() 
                   if self.dependency_graph.degree(node) == 0]
        if orphaned:
            recommendations.append(
                f"Found {len(orphaned)} flags with no dependencies - consider if they're still needed"
            )
        
        return recommendations
    
    async def visualize_dependencies(self, output_file: str = "dependency_graph.png", 
                                   repository_filter: List[str] = None):
        """Create visual representation of dependency graph."""
        # Filter graph if requested
        if repository_filter:
            filtered_nodes = [
                node for node in self.dependency_graph.nodes()
                if any(node.startswith(f"{repo}:") for repo in repository_filter)
            ]
            graph = self.dependency_graph.subgraph(filtered_nodes)
        else:
            graph = self.dependency_graph
        
        if not graph.nodes():
            logger.warning("No nodes to visualize")
            return
        
        # Create visualization
        plt.figure(figsize=(16, 12))
        
        # Calculate layout
        pos = nx.spring_layout(graph, k=1, iterations=50)
        
        # Color nodes by repository
        repositories = set(node.split(':', 1)[0] for node in graph.nodes())
        colors = plt.cm.Set3(range(len(repositories)))
        repo_colors = {repo: colors[i] for i, repo in enumerate(repositories)}
        
        node_colors = [repo_colors[node.split(':', 1)[0]] for node in graph.nodes()]
        
        # Draw graph
        nx.draw(graph, pos, 
                node_color=node_colors,
                node_size=1000,
                font_size=8,
                font_weight='bold',
                arrows=True,
                arrowsize=20,
                edge_color='gray',
                alpha=0.7)
        
        # Add labels
        labels = {node: node.split(':', 1)[1] for node in graph.nodes()}
        nx.draw_networkx_labels(graph, pos, labels, font_size=6)
        
        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', 
                      markerfacecolor=repo_colors[repo], markersize=10, label=repo)
            for repo in repositories
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.title("Feature Flag Dependencies", fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Dependency visualization saved to: {output_file}")
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# CLI Interface
@click.group()
@click.option('--github-token', envvar='GITHUB_TOKEN', required=True)
@click.option('--api-url', envvar='FEATURE_FLAG_API_URL', required=True)
@click.option('--api-key', envvar='FEATURE_FLAG_API_KEY', required=True)
@click.pass_context
def cli(ctx, github_token, api_url, api_key):
    """Cross-Repository Feature Flag Dependency Tracker CLI"""
    ctx.ensure_object(dict)
    ctx.obj['tracker'] = CrossRepositoryDependencyTracker(
        github_token=github_token,
        feature_flag_api_url=api_url,
        feature_flag_api_key=api_key
    )


@cli.command()
@click.option('--organization', help='GitHub organization to scan')
@click.option('--user', help='GitHub user to scan')
@click.pass_context
def discover(ctx, organization, user):
    """Discover repositories with flag configurations."""
    async def run():
        tracker = ctx.obj['tracker']
        repos = await tracker.discover_repositories(organization, user)
        click.echo(f"Discovered {len(repos)} repositories:")
        for repo in repos:
            click.echo(f"  - {repo.name}")
        await tracker.close()
    
    asyncio.run(run())


@cli.command()
@click.pass_context
def sync(ctx):
    """Sync dependencies from all repositories."""
    async def run():
        tracker = ctx.obj['tracker']
        dependencies = await tracker.load_dependencies_from_repositories()
        click.echo(f"Synced {len(dependencies)} dependencies")
        await tracker.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--flag-id', required=True, help='Flag ID to analyze')
@click.option('--repository', required=True, help='Repository name')
@click.pass_context
def analyze(ctx, flag_id, repository):
    """Analyze dependency impact of a flag."""
    async def run():
        tracker = ctx.obj['tracker']
        await tracker.load_dependencies_from_repositories()
        
        analysis = await tracker.analyze_dependency_impact(flag_id, repository)
        
        click.echo(f"Impact analysis for {repository}:{flag_id}:")
        click.echo(f"Impact Score: {analysis['impact_score']}")
        click.echo(f"Direct Dependencies: {len(analysis['direct_dependencies'])}")
        click.echo(f"Dependent Flags: {len(analysis['dependent_flags'])}")
        
        if analysis['dependent_flags']:
            click.echo("\nDependent flags:")
            for dep in analysis['dependent_flags']:
                click.echo(f"  - {dep['repository']}:{dep['flag']} ({dep['dependency_type']})")
        
        await tracker.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--format', type=click.Choice(['json', 'yaml']), default='json')
@click.pass_context
def report(ctx, format):
    """Generate dependency report."""
    async def run():
        tracker = ctx.obj['tracker']
        await tracker.load_dependencies_from_repositories()
        
        report_file = await tracker.generate_dependency_report(format)
        click.echo(f"Report generated: {report_file}")
        
        await tracker.close()
    
    asyncio.run(run())


@cli.command()
@click.option('--output', default='dependency_graph.png', help='Output file')
@click.option('--repos', help='Comma-separated list of repositories to include')
@click.pass_context
def visualize(ctx, output, repos):
    """Create dependency visualization."""
    async def run():
        tracker = ctx.obj['tracker']
        await tracker.load_dependencies_from_repositories()
        
        repo_filter = repos.split(',') if repos else None
        await tracker.visualize_dependencies(output, repo_filter)
        
        click.echo(f"Visualization saved: {output}")
        await tracker.close()
    
    asyncio.run(run())


if __name__ == '__main__':
    cli()