#!/usr/bin/env python3
"""
Automatic Roadmap Timeline Updater

This script:
1. Parses ARCHITECTURE_ROADMAP.md (backend and frontend) to extract all DEV tasks
2. Calculates deployment timeline estimates based on effort and dependencies
3. Updates the Deployment Timeline section
4. Triggers email notification if new tasks detected or timelines changed

Email Notification Rules:
- Maximum 1 email per day
- Only sent at 6:00 AM or later
- Only sent if there are actual changes (new/removed tasks or timeline changes)

Usage:
    python scripts/update_roadmap_timeline.py [--notify] [--dry-run]

Arguments:
    --notify: Send email notification to ROADMAP_NOTIFICATION_EMAIL (subject to daily limit)
    --dry-run: Print changes without modifying files
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Load environment variables from .env.development
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / ".env.development"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"📝 Loaded environment from {env_file}")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment only")


def calculate_date_range(weeks_from_now: float, buffer_weeks: float = 0) -> tuple[str, str]:
    """
    Calculate date range from current date + weeks estimate.

    Args:
        weeks_from_now: Number of weeks from today
        buffer_weeks: Additional buffer to add to end date

    Returns:
        Tuple of (start_date, end_date) as strings in "DD MMM" format
    """
    today = datetime.now()
    start_date = today + timedelta(weeks=weeks_from_now)
    end_date = today + timedelta(weeks=weeks_from_now + buffer_weeks)

    # Format as "DD MMM" (e.g., "15 Dec")
    months_italian = {
        1: "Gen",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "Mag",
        6: "Giu",
        7: "Lug",
        8: "Ago",
        9: "Set",
        10: "Ott",
        11: "Nov",
        12: "Dic",
    }

    start_str = f"{start_date.day} {months_italian[start_date.month]}"
    end_str = f"{end_date.day} {months_italian[end_date.month]}"

    return start_str, end_str


@dataclass
class Task:
    """Represents a DEV task from the roadmap."""

    id: str  # e.g., "DEV-67"
    title: str
    priority: str
    effort_days_min: float
    effort_days_max: float
    dependencies: list[str]
    is_deployment: bool = False
    is_gdpr_audit: bool = False

    @property
    def effort_days_avg(self) -> float:
        """Average effort in days."""
        return (self.effort_days_min + self.effort_days_max) / 2.0


class RoadmapParser:
    """Parser for ARCHITECTURE_ROADMAP.md file."""

    EFFORT_PATTERN = re.compile(r"\*\*Effort:\*\*\s+(.+?)\s+\(")
    DEPENDENCY_PATTERN = re.compile(r"\*\*Dependencies:\*\*\s+(.+?)(?:\n|$)")
    PRIORITY_PATTERN = re.compile(r"\*\*Priority:\*\*\s+(\w+)")

    def __init__(self, roadmap_path: str):
        self.roadmap_path = Path(roadmap_path)
        if not self.roadmap_path.exists():
            raise FileNotFoundError(f"Roadmap file not found: {roadmap_path}")

    def parse(self) -> dict[str, Task]:
        """Parse roadmap and return dictionary of tasks."""
        content = self.roadmap_path.read_text(encoding="utf-8")
        tasks = {}

        # Find all DEV task sections (DEV-BE-XX or DEV-FE-XX format)
        task_pattern = re.compile(r"### (DEV-(?:BE|FE)-\d+): (.+?)\n\*\*Priority:\*\*(.+?)(?=\n###|\Z)", re.DOTALL)

        for match in task_pattern.finditer(content):
            task_id = match.group(1)
            title = match.group(2).strip()
            section = match.group(3)

            # Extract effort
            effort_min, effort_max = self._parse_effort(section)

            # Extract dependencies
            dependencies = self._parse_dependencies(section, task_id)

            # Extract priority
            priority = self._parse_priority(section)

            # Detect special task types
            is_deployment = "Deploy" in title and ("QA" in title or "Preprod" in title or "Production" in title)
            is_gdpr_audit = "GDPR Compliance Audit" in title

            task = Task(
                id=task_id,
                title=title,
                priority=priority,
                effort_days_min=effort_min,
                effort_days_max=effort_max,
                dependencies=dependencies,
                is_deployment=is_deployment,
                is_gdpr_audit=is_gdpr_audit,
            )

            tasks[task_id] = task

        return tasks

    def _parse_effort(self, section: str) -> tuple[float, float]:
        """Parse effort estimate and convert to days."""
        match = self.EFFORT_PATTERN.search(section)
        if not match:
            return (0.0, 0.0)

        effort_str = match.group(1).strip()

        # Parse different formats
        # "3-5 days" → (3, 5)
        # "1 week" → (7, 7)
        # "2-3 weeks" → (14, 21)
        # "1-2 days" → (1, 2)

        # Try range format first: "X-Y [days|weeks]"
        range_match = re.match(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\s*(day|week|month)", effort_str, re.IGNORECASE)
        if range_match:
            min_val = float(range_match.group(1))
            max_val = float(range_match.group(2))
            unit = range_match.group(3).lower()

            if "week" in unit:
                return (min_val * 7, max_val * 7)
            elif "month" in unit:
                return (min_val * 30, max_val * 30)
            else:  # days
                return (min_val, max_val)

        # Try single value: "X [days|weeks]"
        single_match = re.match(r"(\d+(?:\.\d+)?)\s*(day|week|month)", effort_str, re.IGNORECASE)
        if single_match:
            val = float(single_match.group(1))
            unit = single_match.group(2).lower()

            if "week" in unit:
                return (val * 7, val * 7)
            elif "month" in unit:
                return (val * 30, val * 30)
            else:  # days
                return (val, val)

        # Default fallback
        return (0.0, 0.0)

    def _parse_dependencies(self, section: str, current_task_id: str) -> list[str]:
        """Parse task dependencies."""
        match = self.DEPENDENCY_PATTERN.search(section)
        if not match:
            return []

        deps_str = match.group(1).strip()

        # Handle "None"
        if deps_str.lower() == "none":
            return []

        # Extract all DEV-BE-XX or DEV-FE-XX references
        dep_pattern = re.compile(r"DEV-(?:BE|FE)-\d+")
        dependencies = dep_pattern.findall(deps_str)

        # Filter out self-reference
        return [dep for dep in dependencies if dep != current_task_id]

    def _parse_priority(self, section: str) -> str:
        """Parse task priority."""
        match = self.PRIORITY_PATTERN.search(section)
        if match:
            return match.group(1).strip()
        return "MEDIUM"


class TimelineCalculator:
    """Calculate deployment timeline estimates based on tasks and dependencies."""

    def __init__(self, tasks: dict[str, Task]):
        self.tasks = tasks
        # Store task IDs in roadmap order for sequential calculation
        self.task_order = list(tasks.keys())

    def calculate_deployment_timelines(self) -> dict[str, dict[str, any]]:
        """
        Calculate timeline estimates for QA, Preprod, and Production deployments.

        Returns dict with keys: 'qa', 'preprod', 'production'
        Each containing: optimistic, conservative, prerequisites, critical_path
        """
        timelines = {}

        # Auto-detect repository type by checking which deployment tasks exist
        # Backend: DEV-BE-75, DEV-BE-88, DEV-BE-90
        # Frontend: DEV-FE-005, DEV-FE-010
        if "DEV-BE-75" in self.tasks:
            qa_task_id = "DEV-BE-75"
            preprod_task_id = "DEV-BE-88"
            prod_task_id = "DEV-BE-90"
        elif "DEV-FE-005" in self.tasks:
            qa_task_id = "DEV-FE-005"
            preprod_task_id = "DEV-FE-010"
            prod_task_id = "DEV-FE-010"  # Frontend uses same task for preprod/prod
        else:
            # No deployment tasks found
            return {}

        # QA Environment - Sequential sum of ALL tasks before deployment
        qa_prereqs = self._get_prerequisites(qa_task_id)
        qa_sequential_sum = self._calculate_sequential_sum(qa_task_id)
        qa_optimistic = qa_sequential_sum
        qa_conservative = qa_optimistic * 1.3  # 30% buffer for delays/blockers

        # Calculate date ranges
        qa_opt_start, qa_opt_end = calculate_date_range(0, qa_optimistic / 7 + 1)
        qa_cons_start, qa_cons_end = calculate_date_range(0, qa_conservative / 7 + 1)

        timelines["qa"] = {
            "optimistic_weeks": qa_optimistic / 7,
            "conservative_weeks": qa_conservative / 7,
            "prerequisites": qa_prereqs,
            "sequential_sum_days": qa_sequential_sum,
            "task_id": qa_task_id,
            "optimistic_date_range": f"{qa_opt_start} - {qa_opt_end}",
            "conservative_date_range": f"{qa_cons_start} - {qa_cons_end}",
        }

        # Preprod Environment - Sequential sum of ALL tasks before deployment
        preprod_prereqs = self._get_prerequisites(preprod_task_id)
        preprod_sequential_sum = self._calculate_sequential_sum(preprod_task_id)
        preprod_optimistic = preprod_sequential_sum
        preprod_conservative = preprod_optimistic * 1.4  # 40% buffer

        # Calculate date ranges
        preprod_opt_start, preprod_opt_end = calculate_date_range(0, preprod_optimistic / 7 + 2)
        preprod_cons_start, preprod_cons_end = calculate_date_range(0, preprod_conservative / 7 + 2)

        timelines["preprod"] = {
            "optimistic_weeks": preprod_optimistic / 7,
            "conservative_weeks": preprod_conservative / 7,
            "prerequisites": preprod_prereqs,
            "sequential_sum_days": preprod_sequential_sum,
            "task_id": preprod_task_id,
            "optimistic_date_range": f"{preprod_opt_start} - {preprod_opt_end}",
            "conservative_date_range": f"{preprod_cons_start} - {preprod_cons_end}",
        }

        # Production Environment - Sequential sum of ALL tasks before deployment
        prod_prereqs = self._get_prerequisites(prod_task_id)
        prod_sequential_sum = self._calculate_sequential_sum(prod_task_id)
        prod_optimistic = prod_sequential_sum
        prod_conservative = prod_optimistic * 1.5  # 50% buffer for production

        # Calculate date ranges
        prod_opt_start, prod_opt_end = calculate_date_range(0, prod_optimistic / 7 + 1.5)
        prod_cons_start, prod_cons_end = calculate_date_range(0, prod_conservative / 7 + 3)

        timelines["production"] = {
            "optimistic_weeks": prod_optimistic / 7,
            "conservative_weeks": prod_conservative / 7,
            "prerequisites": prod_prereqs,
            "sequential_sum_days": prod_sequential_sum,
            "task_id": prod_task_id,
            "optimistic_date_range": f"{prod_opt_start} - {prod_opt_end}",
            "conservative_date_range": f"{prod_cons_start} - {prod_cons_end}",
        }

        return timelines

    def _get_prerequisites(self, task_id: str) -> list[str]:
        """Get all prerequisite tasks (recursive dependency resolution)."""
        if task_id not in self.tasks:
            return []

        # Hard-coded logical prerequisites for deployment tasks
        # These represent the actual deployment flow dependencies
        DEPLOYMENT_PREREQUISITES = {
            # Backend deployment tasks
            "DEV-BE-75": ["DEV-BE-67", "DEV-BE-68", "DEV-BE-69", "DEV-BE-70", "DEV-BE-71", "DEV-BE-72", "DEV-BE-74"],
            "DEV-BE-88": ["DEV-BE-75", "DEV-BE-87"],  # QA + Payment System
            "DEV-BE-90": ["DEV-BE-88", "DEV-BE-89", "DEV-BE-91"],  # Preprod + GDPR Audits
            # Frontend deployment tasks
            "DEV-FE-005": ["DEV-FE-002", "DEV-FE-003", "DEV-FE-004"],  # QA
            "DEV-FE-010": ["DEV-FE-005", "DEV-FE-006", "DEV-FE-007", "DEV-FE-008", "DEV-FE-009"],  # Preprod/Production
        }

        # If this is a deployment task with known prerequisites, use those
        if task_id in DEPLOYMENT_PREREQUISITES:
            direct_prereqs = DEPLOYMENT_PREREQUISITES[task_id]
            # Recursively expand all prerequisites
            all_prereqs = set()
            for prereq in direct_prereqs:
                all_prereqs.add(prereq)
                # Add transitive dependencies
                if prereq in DEPLOYMENT_PREREQUISITES:
                    all_prereqs.update(self._get_prerequisites(prereq))
            return list(all_prereqs)

        # Otherwise, use standard dependency resolution
        visited = set()
        prerequisites = []

        def visit(tid: str):
            if tid in visited or tid not in self.tasks:
                return
            visited.add(tid)

            task = self.tasks[tid]
            for dep in task.dependencies:
                visit(dep)

            if tid != task_id:  # Don't include the target task itself
                prerequisites.append(tid)

        # Visit all dependencies
        task = self.tasks[task_id]
        for dep in task.dependencies:
            visit(dep)

        return prerequisites

    def _calculate_critical_path(self, task_ids: list[str]) -> float:
        """
        Calculate critical path (longest path) through task dependencies.
        Uses average effort estimates.
        """
        if not task_ids:
            return 0.0

        # Build dependency graph
        graph = {}
        for tid in task_ids:
            if tid in self.tasks:
                graph[tid] = self.tasks[tid].dependencies

        # Calculate longest path using dynamic programming
        memo = {}

        def longest_path(tid: str) -> float:
            if tid in memo:
                return memo[tid]

            if tid not in self.tasks:
                memo[tid] = 0.0
                return 0.0

            task = self.tasks[tid]

            # Base case: task with no dependencies
            if not task.dependencies:
                result = task.effort_days_avg
            else:
                # Recursive case: task effort + max of all dependency paths
                dep_paths = [longest_path(dep) for dep in task.dependencies if dep in self.tasks]
                result = task.effort_days_avg + (max(dep_paths) if dep_paths else 0)

            memo[tid] = result
            return result

        # Find longest path among all tasks
        max_path = max(longest_path(tid) for tid in task_ids if tid in self.tasks)
        return max_path

    def _calculate_sequential_sum(self, deployment_task_id: str) -> float:
        """
        Calculate TOTAL effort by summing ALL tasks that appear BEFORE
        the deployment task in roadmap order (sequential completion).

        This gives realistic timeline: "How long until we can deploy to X environment?"
        assuming we complete all tasks in order (no parallelization).
        """
        if deployment_task_id not in self.task_order:
            return 0.0

        # Find index of deployment task
        deploy_index = self.task_order.index(deployment_task_id)

        # Sum effort of ALL tasks before this deployment task
        total_effort = 0.0
        for i in range(deploy_index):
            task_id = self.task_order[i]
            if task_id in self.tasks:
                task = self.tasks[task_id]
                total_effort += task.effort_days_avg

        # Add the deployment task itself
        if deployment_task_id in self.tasks:
            total_effort += self.tasks[deployment_task_id].effort_days_avg

        return total_effort

    def identify_blockers(self) -> list[dict[str, any]]:
        """Identify critical blocker tasks."""
        blockers = []

        # Payment System (Backend: DEV-BE-87, Frontend: DEV-FE-009)
        payment_task_id = "DEV-BE-87" if "DEV-BE-87" in self.tasks else "DEV-FE-009" if "DEV-FE-009" in self.tasks else None
        if payment_task_id:
            task = self.tasks[payment_task_id]
            blockers.append(
                {
                    "id": payment_task_id,
                    "title": task.title,
                    "reason": "Blocks Preprod/Production deployment",
                    "effort_weeks": task.effort_days_avg / 7,
                }
            )

        # Expert Feedback (Backend: DEV-BE-72, Frontend: DEV-FE-004)
        expert_task_id = "DEV-BE-72" if "DEV-BE-72" in self.tasks else "DEV-FE-004" if "DEV-FE-004" in self.tasks else None
        if expert_task_id:
            task = self.tasks[expert_task_id]
            blockers.append(
                {
                    "id": expert_task_id,
                    "title": task.title,
                    "reason": "Blocks QA deployment (longest task)",
                    "effort_weeks": task.effort_days_avg / 7,
                }
            )

        # GDPR Audits
        gdpr_tasks = [t for t in self.tasks.values() if t.is_gdpr_audit]
        if gdpr_tasks:
            blockers.append(
                {
                    "id": "GDPR Audits",
                    "title": "DEV-74, DEV-89, DEV-91",
                    "reason": "Required before each environment launch",
                    "effort_weeks": sum(t.effort_days_avg for t in gdpr_tasks) / 7,
                }
            )

        return blockers


class RoadmapUpdater:
    """Update ARCHITECTURE_ROADMAP.md with new timeline estimates."""

    TIMELINE_START_MARKER = "**Deployment Timeline Estimates:**"
    TIMELINE_END_MARKER = "## Development Standards"

    def __init__(self, roadmap_path: str):
        self.roadmap_path = Path(roadmap_path)

    def update(self, timelines: dict[str, dict], blockers: list[dict]) -> bool:
        """Update roadmap file with new timeline estimates."""
        content = self.roadmap_path.read_text(encoding="utf-8")

        # Find timeline section
        start_idx = content.find(self.TIMELINE_START_MARKER)
        end_idx = content.find(self.TIMELINE_END_MARKER)

        if start_idx == -1 or end_idx == -1:
            print("ERROR: Could not find timeline section in roadmap", file=sys.stderr)
            return False

        # Generate new timeline content
        new_timeline = self._generate_timeline_content(timelines, blockers)

        # Replace section
        new_content = content[:start_idx] + new_timeline + "\n---\n\n" + content[end_idx:]

        # Write back
        self.roadmap_path.write_text(new_content, encoding="utf-8")
        return True

    def _generate_timeline_content(self, timelines: dict[str, dict], blockers: list[dict]) -> str:
        """Generate formatted timeline content."""
        qa = timelines["qa"]
        preprod = timelines["preprod"]
        prod = timelines["production"]

        content = f"""**Deployment Timeline Estimates:**

📅 **Time to QA Environment ({qa["task_id"]}):**
- **Optimistic (parallel work):** ~{qa["optimistic_weeks"]:.0f}-{qa["optimistic_weeks"] + 1:.0f} weeks ({qa["optimistic_date_range"]})
- **Conservative (sequential):** ~{qa["conservative_weeks"]:.0f}-{qa["conservative_weeks"] + 1:.0f} weeks ({qa["conservative_date_range"]})
- **Prerequisites:** {", ".join(qa["prerequisites"][:5])}{"..." if len(qa["prerequisites"]) > 5 else ""}
- **Total effort (sequential):** {qa["sequential_sum_days"]:.0f} days ({qa["sequential_sum_days"] / 7:.1f} weeks)

📅 **Time to Preprod Environment ({preprod["task_id"]}):**
- **Optimistic:** ~{preprod["optimistic_weeks"]:.0f}-{preprod["optimistic_weeks"] + 2:.0f} weeks from now ({preprod["optimistic_date_range"]})
- **Conservative:** ~{preprod["conservative_weeks"]:.0f}-{preprod["conservative_weeks"] + 2:.0f} weeks from now ({preprod["conservative_date_range"]})
- **Prerequisites:** Path to QA + {", ".join(preprod["prerequisites"][-3:])}
- **Total effort (sequential):** {preprod["sequential_sum_days"]:.0f} days ({preprod["sequential_sum_days"] / 7:.1f} weeks)

📅 **Time to Production Environment ({prod["task_id"]}):**
- **Optimistic:** ~{prod["optimistic_weeks"]:.0f}-{prod["optimistic_weeks"] + 1.5:.1f} weeks from now ({prod["optimistic_date_range"]})
- **Conservative:** ~{prod["conservative_weeks"]:.0f}-{prod["conservative_weeks"] + 3:.0f} weeks from now ({prod["conservative_date_range"]})
- **Prerequisites:** Path to Preprod + {", ".join(prod["prerequisites"][-3:])}
- **Total effort (sequential):** {prod["sequential_sum_days"]:.0f} days ({prod["sequential_sum_days"] / 7:.1f} weeks)
- **Note:** Production launch requires full GDPR compliance and payment system validation

**Key Dependencies:**
"""

        # Add blockers
        for blocker in blockers:
            content += f"- ⚠️ **{blocker['id']}** - {blocker['title']}: {blocker['reason']}\n"

        return content


def load_cache() -> dict | None:
    """Load previous timeline estimates from cache file."""
    cache_path = Path(__file__).parent.parent / ".roadmap_timeline_cache.json"
    if cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Failed to load cache: {e}")
    return None


def save_cache(data: dict) -> None:
    """Save current timeline estimates to cache file."""
    cache_path = Path(__file__).parent.parent / ".roadmap_timeline_cache.json"
    try:
        # Preserve last_email_sent field if it exists
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    old_cache = json.load(f)
                    if "last_email_sent" in old_cache:
                        data["last_email_sent"] = old_cache["last_email_sent"]
            except Exception:
                pass  # If we can't read old cache, just continue

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved cache to {cache_path}")
    except Exception as e:
        print(f"⚠️  Failed to save cache: {e}")


def should_send_email() -> bool:
    """
    Check if we should send an email based on daily limit and time.

    Email sending rules:
    - Maximum 1 email per day
    - Only send at 6:00 AM (or later if script runs after 6 AM)
    - Track last send time in cache

    Returns:
        True if we should send email, False otherwise
    """
    cache_path = Path(__file__).parent.parent / ".roadmap_timeline_cache.json"

    # Get current time
    now = datetime.now()
    current_date = now.date()
    current_hour = now.hour

    # Load last send time from cache
    if cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)
                last_email_sent = cache.get("last_email_sent")

                if last_email_sent:
                    last_send_date = datetime.fromisoformat(last_email_sent).date()

                    # If already sent today, skip
                    if last_send_date == current_date:
                        print(f"ℹ️  Email already sent today at {last_email_sent}")
                        return False
        except Exception as e:
            print(f"⚠️  Failed to check last email send time: {e}")

    # Check if current time is 6 AM or later
    if current_hour < 6:
        print(f"ℹ️  Too early to send email (current time: {now.strftime('%H:%M')}). Email will be sent at 6:00 AM or later.")
        return False

    return True


def record_email_sent() -> None:
    """Record the timestamp of the last email sent."""
    cache_path = Path(__file__).parent.parent / ".roadmap_timeline_cache.json"

    try:
        # Load existing cache
        cache = {}
        if cache_path.exists():
            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)

        # Update last email sent timestamp
        cache["last_email_sent"] = datetime.now().isoformat()

        # Save back to cache
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

        print(f"📝 Recorded email send time: {cache['last_email_sent']}")
    except Exception as e:
        print(f"⚠️  Failed to record email send time: {e}")


def detect_changes(old_data: dict | None, new_data: dict) -> dict[str, any]:
    """
    Detect changes between old and new timeline data.

    Returns dict with:
        - new_tasks: List of newly added task IDs
        - removed_tasks: List of removed task IDs
        - timeline_changes: Dict of timeline changes per environment
    """
    changes = {"new_tasks": [], "removed_tasks": [], "timeline_changes": {}}

    if not old_data:
        return changes

    # Detect new/removed tasks
    old_tasks = set(old_data.get("backend", {}).get("tasks", {}).keys())
    old_tasks.update(old_data.get("frontend", {}).get("tasks", {}).keys())
    new_tasks = set(new_data.get("backend", {}).get("tasks", {}).keys())
    new_tasks.update(new_data.get("frontend", {}).get("tasks", {}).keys())

    changes["new_tasks"] = list(new_tasks - old_tasks)
    changes["removed_tasks"] = list(old_tasks - new_tasks)

    # Detect timeline changes for each environment
    for repo in ["backend", "frontend"]:
        if repo not in new_data:
            continue

        old_timelines = old_data.get(repo, {}).get("timelines", {})
        new_timelines = new_data.get(repo, {}).get("timelines", {})

        for env in ["qa", "preprod", "production"]:
            if env not in new_timelines:
                continue

            old_env = old_timelines.get(env, {})
            new_env = new_timelines[env]

            # Calculate differences
            opt_diff = new_env["optimistic_weeks"] - old_env.get("optimistic_weeks", 0)
            cons_diff = new_env["conservative_weeks"] - old_env.get("conservative_weeks", 0)

            if abs(opt_diff) > 0.1 or abs(cons_diff) > 0.1:  # Only significant changes
                key = f"{repo}_{env}"
                changes["timeline_changes"][key] = {
                    "environment": env,
                    "repository": repo,
                    "optimistic_change": opt_diff,
                    "conservative_change": cons_diff,
                    "old_optimistic": old_env.get("optimistic_weeks", 0),
                    "new_optimistic": new_env["optimistic_weeks"],
                    "old_conservative": old_env.get("conservative_weeks", 0),
                    "new_conservative": new_env["conservative_weeks"],
                }

    return changes


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update roadmap deployment timeline estimates")
    parser.add_argument("--notify", action="store_true", help="Send email notification")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without modifying files")
    args = parser.parse_args()

    # Find backend and frontend roadmap files
    backend_roadmap_path = Path(__file__).parent.parent / "ARCHITECTURE_ROADMAP.md"
    # Frontend path: /Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md
    frontend_roadmap_path = Path("/Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md")

    if not backend_roadmap_path.exists():
        print(f"ERROR: Backend roadmap not found at {backend_roadmap_path}", file=sys.stderr)
        return 1

    print(f"📖 Parsing backend roadmap: {backend_roadmap_path}")

    # Load previous cache for change detection
    old_cache = load_cache()

    # Parse backend tasks
    backend_parser = RoadmapParser(str(backend_roadmap_path))
    backend_tasks = backend_parser.parse()
    print(f"✅ Found {len(backend_tasks)} backend tasks")

    # Calculate backend timelines
    backend_calculator = TimelineCalculator(backend_tasks)
    backend_timelines = backend_calculator.calculate_deployment_timelines()
    backend_blockers = backend_calculator.identify_blockers()

    # Parse frontend tasks (if exists)
    frontend_tasks = {}
    frontend_timelines = {}
    frontend_blockers = []

    if frontend_roadmap_path.exists():
        print(f"📖 Parsing frontend roadmap: {frontend_roadmap_path}")
        try:
            frontend_parser = RoadmapParser(str(frontend_roadmap_path))
            frontend_tasks = frontend_parser.parse()
            print(f"✅ Found {len(frontend_tasks)} frontend tasks")

            # Calculate frontend timelines
            frontend_calculator = TimelineCalculator(frontend_tasks)
            frontend_timelines = frontend_calculator.calculate_deployment_timelines()
            frontend_blockers = frontend_calculator.identify_blockers()
        except Exception as e:
            print(f"⚠️  Failed to parse frontend roadmap: {e}")
    else:
        print(f"⚠️  Frontend roadmap not found at {frontend_roadmap_path}")

    # Prepare new cache data
    new_cache = {
        "timestamp": datetime.now().isoformat(),
        "backend": {
            "tasks": {
                tid: {"title": t.title, "effort_days_avg": t.effort_days_avg} for tid, t in backend_tasks.items()
            },
            "timelines": backend_timelines,
        },
    }

    if frontend_tasks:
        new_cache["frontend"] = {
            "tasks": {
                tid: {"title": t.title, "effort_days_avg": t.effort_days_avg} for tid, t in frontend_tasks.items()
            },
            "timelines": frontend_timelines,
        }

    # Detect changes
    changes = detect_changes(old_cache, new_cache)

    # Print summary
    print("\n📅 Backend Timeline Estimates:")
    for env, data in backend_timelines.items():
        print(
            f"  {env.upper()}: {data['optimistic_weeks']:.1f}-{data['conservative_weeks']:.1f} weeks ({data.get('optimistic_date_range', 'N/A')})"
        )

    if frontend_timelines:
        print("\n📅 Frontend Timeline Estimates:")
        for env, data in frontend_timelines.items():
            print(
                f"  {env.upper()}: {data['optimistic_weeks']:.1f}-{data['conservative_weeks']:.1f} weeks ({data.get('optimistic_date_range', 'N/A')})"
            )

    print(f"\n⚠️  Backend Critical Blockers: {len(backend_blockers)}")
    for blocker in backend_blockers:
        print(f"  - {blocker['id']}: {blocker['reason']}")

    # Print changes
    if changes["new_tasks"]:
        print(f"\n🆕 New tasks: {', '.join(changes['new_tasks'])}")
    if changes["removed_tasks"]:
        print(f"\n❌ Removed tasks: {', '.join(changes['removed_tasks'])}")
    if changes["timeline_changes"]:
        print("\n📊 Timeline changes detected:")
        for _key, change in changes["timeline_changes"].items():
            opt_dir = "🔴" if change["optimistic_change"] > 0 else "🟢"
            "🔴" if change["conservative_change"] > 0 else "🟢"
            print(
                f"  {opt_dir} {change['repository'].upper()} {change['environment'].upper()}: "
                f"Opt {change['optimistic_change']:+.1f}w, Cons {change['conservative_change']:+.1f}w"
            )

    if args.dry_run:
        print("\n🔍 Dry run - no files modified")
        return 0

    # Update backend roadmap
    backend_updater = RoadmapUpdater(str(backend_roadmap_path))
    success = backend_updater.update(backend_timelines, backend_blockers)

    if success:
        print(f"\n✅ Updated {backend_roadmap_path}")
    else:
        print("\n❌ Failed to update backend roadmap", file=sys.stderr)
        return 1

    # Update frontend roadmap if exists
    if frontend_roadmap_path.exists() and frontend_timelines:
        frontend_updater = RoadmapUpdater(str(frontend_roadmap_path))
        if frontend_updater.update(frontend_timelines, frontend_blockers):
            print(f"✅ Updated {frontend_roadmap_path}")
        else:
            print("⚠️  Failed to update frontend roadmap")

    # Save cache
    save_cache(new_cache)

    # Send notification if requested AND there are actual changes AND within time window
    has_changes = bool(changes["new_tasks"] or changes["removed_tasks"] or changes["timeline_changes"])

    if args.notify and has_changes:
        # Check daily email limit and time window
        if should_send_email():
            try:
                from roadmap_email_notifier import send_timeline_notification

                # Pass both backend and frontend data to email notifier
                combined_data = {
                    "backend": {"timelines": backend_timelines, "blockers": backend_blockers, "tasks": backend_tasks},
                    "frontend": {"timelines": frontend_timelines, "blockers": frontend_blockers, "tasks": frontend_tasks},
                    "changes": changes,
                }
                send_timeline_notification(combined_data)
                print("📧 Email notification sent")

                # Record that we sent an email
                record_email_sent()
            except Exception as e:
                import traceback

                print(f"⚠️  Email notification failed: {e}", file=sys.stderr)
                print(f"Traceback: {traceback.format_exc()}")
        else:
            print("ℹ️  Email sending skipped (daily limit or time window)")
    elif args.notify and not has_changes:
        print("ℹ️  No changes detected - skipping email notification")

    return 0


if __name__ == "__main__":
    sys.exit(main())
