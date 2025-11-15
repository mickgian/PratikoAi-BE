"""CCNL Change Detector Service.

This service detects and analyzes changes between CCNL versions,
calculating significance scores and providing detailed change analysis.
Follows TDD methodology and integrates with the CCNL update system.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SalaryChange:
    """Represents a salary change between versions."""

    level: str
    old_amount: Decimal
    new_amount: Decimal
    change_amount: Decimal
    change_percentage: float


@dataclass
class WorkingConditionsChange:
    """Represents a working conditions change."""

    field: str
    old_value: Any
    new_value: Any
    change: Any
    change_type: str  # "increased", "decreased", "modified"


class CCNLChangeDetector:
    """Detect and analyze changes between CCNL versions."""

    def __init__(self):
        # Significance weights for different types of changes
        self.significance_weights = {
            "salary_increases": 0.4,
            "working_hours_changes": 0.25,
            "new_benefits": 0.2,
            "leave_changes": 0.1,
            "other_changes": 0.05,
        }

        # Thresholds for significant changes
        self.significant_salary_increase_threshold = 5.0  # 5% increase
        self.significant_hours_change_threshold = 2  # 2 hour change

    def detect_salary_changes(
        self, old_salary_data: dict[str, Any], new_salary_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Detect changes in salary data between versions."""
        try:
            changes = {"increased": {}, "decreased": {}, "unchanged": {}, "added": {}, "removed": {}}

            old_wages = old_salary_data.get("minimum_wages", {})
            new_wages = new_salary_data.get("minimum_wages", {})

            all_levels = set(old_wages.keys()) | set(new_wages.keys())

            for level in all_levels:
                old_amount = old_wages.get(level)
                new_amount = new_wages.get(level)

                if old_amount is None:
                    # New level added
                    changes["added"][level] = new_amount
                elif new_amount is None:
                    # Level removed
                    changes["removed"][level] = old_amount
                else:
                    # Compare amounts
                    old_decimal = Decimal(str(old_amount))
                    new_decimal = Decimal(str(new_amount))

                    if new_decimal > old_decimal:
                        changes["increased"][level] = {
                            "old": old_amount,
                            "new": new_amount,
                            "change": float(new_decimal - old_decimal),
                            "percentage": float((new_decimal - old_decimal) / old_decimal * 100),
                        }
                    elif new_decimal < old_decimal:
                        changes["decreased"][level] = {
                            "old": old_amount,
                            "new": new_amount,
                            "change": float(old_decimal - new_decimal),
                            "percentage": float((old_decimal - new_decimal) / old_decimal * 100),
                        }
                    else:
                        changes["unchanged"][level] = new_amount

            logger.info(
                f"Detected salary changes: {len(changes['increased'])} increases, "
                f"{len(changes['decreased'])} decreases, {len(changes['added'])} added"
            )

            return changes

        except Exception as e:
            logger.error(f"Error detecting salary changes: {str(e)}")
            return {"increased": {}, "decreased": {}, "unchanged": {}, "added": {}, "removed": {}}

    def detect_working_conditions_changes(
        self, old_conditions: dict[str, Any], new_conditions: dict[str, Any]
    ) -> dict[str, Any]:
        """Detect changes in working conditions between versions."""
        try:
            changes = {"modified": {}, "added": {}, "removed": {}}

            all_fields = set(old_conditions.keys()) | set(new_conditions.keys())

            for field in all_fields:
                old_value = old_conditions.get(field)
                new_value = new_conditions.get(field)

                if old_value is None:
                    # New field added
                    changes["added"][field] = new_value
                elif new_value is None:
                    # Field removed
                    changes["removed"][field] = old_value
                elif old_value != new_value:
                    # Field modified
                    change_info = {"old": old_value, "new": new_value}

                    # Calculate change for numeric fields
                    if isinstance(old_value, int | float) and isinstance(new_value, int | float):
                        change_info["change"] = new_value - old_value
                        change_info["change_type"] = "increased" if new_value > old_value else "decreased"
                    else:
                        change_info["change_type"] = "modified"

                    changes["modified"][field] = change_info

            logger.info(
                f"Detected working conditions changes: {len(changes['modified'])} modified, "
                f"{len(changes['added'])} added, {len(changes['removed'])} removed"
            )

            return changes

        except Exception as e:
            logger.error(f"Error detecting working conditions changes: {str(e)}")
            return {"modified": {}, "added": {}, "removed": {}}

    def detect_leave_provision_changes(self, old_leave: dict[str, Any], new_leave: dict[str, Any]) -> dict[str, Any]:
        """Detect changes in leave provisions between versions."""
        try:
            changes = {"modified": {}, "added": {}, "removed": {}}

            all_types = set(old_leave.keys()) | set(new_leave.keys())

            for leave_type in all_types:
                old_provision = old_leave.get(leave_type)
                new_provision = new_leave.get(leave_type)

                if old_provision is None:
                    changes["added"][leave_type] = new_provision
                elif new_provision is None:
                    changes["removed"][leave_type] = old_provision
                elif old_provision != new_provision:
                    changes["modified"][leave_type] = {"old": old_provision, "new": new_provision}

                    # Calculate change for numeric provisions
                    if isinstance(old_provision, int | float) and isinstance(new_provision, int | float):
                        changes["modified"][leave_type]["change"] = new_provision - old_provision

            return changes

        except Exception as e:
            logger.error(f"Error detecting leave provision changes: {str(e)}")
            return {"modified": {}, "added": {}, "removed": {}}

    def calculate_significance_score(self, changes: dict[str, Any]) -> float:
        """Calculate significance score for changes (0.0 to 1.0)."""
        try:
            score = 0.0

            # Salary changes significance
            salary_increases = changes.get("salary_increases", {})
            if salary_increases:
                max_increase_percentage = 0.0
                for _level, increase_info in salary_increases.items():
                    if isinstance(increase_info, dict) and "percentage" in increase_info:
                        percentage = increase_info["percentage"]
                        max_increase_percentage = max(max_increase_percentage, percentage)

                # Scale significance based on percentage increase
                if max_increase_percentage >= self.significant_salary_increase_threshold:
                    salary_significance = min(1.0, max_increase_percentage / 10.0)  # Cap at 10%
                    score += self.significance_weights["salary_increases"] * salary_significance

            # Working hours changes significance
            working_hours_reduction = changes.get("working_hours_reduction", {})
            if working_hours_reduction:
                hours_change = working_hours_reduction.get("hours", 0)
                if abs(hours_change) >= self.significant_hours_change_threshold:
                    hours_significance = min(1.0, abs(hours_change) / 10.0)  # Scale by 10 hours
                    score += self.significance_weights["working_hours_changes"] * hours_significance

            # New benefits significance
            new_benefits = changes.get("new_benefits", [])
            if new_benefits:
                benefits_significance = min(1.0, len(new_benefits) / 5.0)  # Scale by 5 benefits
                score += self.significance_weights["new_benefits"] * benefits_significance

            # Leave changes significance (if any leave provisions changed)
            leave_changes = changes.get("leave_changes", {})
            if leave_changes and any(leave_changes.values()):
                score += self.significance_weights["leave_changes"] * 0.5

            # Other changes
            other_changes = changes.get("other_changes", [])
            if other_changes:
                other_significance = min(1.0, len(other_changes) / 10.0)  # Scale by 10 changes
                score += self.significance_weights["other_changes"] * other_significance

            return min(1.0, score)  # Cap at 1.0

        except Exception as e:
            logger.error(f"Error calculating significance score: {str(e)}")
            return 0.5  # Return neutral score on error

    def analyze_salary_progression(self, old_wages: dict[str, Any], new_wages: dict[str, Any]) -> dict[str, Any]:
        """Analyze salary progression patterns."""
        try:
            analysis = {
                "average_increase_percentage": 0.0,
                "total_levels_affected": 0,
                "highest_increase_level": None,
                "highest_increase_percentage": 0.0,
                "consistent_increase": True,
            }

            increases = []
            highest_increase = 0.0
            highest_level = None

            for level in old_wages:
                if level in new_wages:
                    old_amount = Decimal(str(old_wages[level]))
                    new_amount = Decimal(str(new_wages[level]))

                    if new_amount > old_amount:
                        increase_percentage = float((new_amount - old_amount) / old_amount * 100)
                        increases.append(increase_percentage)

                        if increase_percentage > highest_increase:
                            highest_increase = increase_percentage
                            highest_level = level

            if increases:
                analysis["average_increase_percentage"] = sum(increases) / len(increases)
                analysis["total_levels_affected"] = len(increases)
                analysis["highest_increase_level"] = highest_level
                analysis["highest_increase_percentage"] = highest_increase

                # Check if increases are consistent (within 1% of each other)
                if len({round(inc, 0) for inc in increases}) > 2:
                    analysis["consistent_increase"] = False

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing salary progression: {str(e)}")
            return {"average_increase_percentage": 0.0, "total_levels_affected": 0}

    def detect_structural_changes(self, old_data: dict[str, Any], new_data: dict[str, Any]) -> list[str]:
        """Detect structural changes in CCNL agreement."""
        structural_changes = []

        try:
            # Check for new sections
            old_sections = set(old_data.keys())
            new_sections = set(new_data.keys())

            added_sections = new_sections - old_sections
            removed_sections = old_sections - new_sections

            for section in added_sections:
                structural_changes.append(f"Added new section: {section}")

            for section in removed_sections:
                structural_changes.append(f"Removed section: {section}")

            # Check for significant restructuring within sections
            common_sections = old_sections & new_sections
            for section in common_sections:
                old_structure = old_data.get(section, {})
                new_structure = new_data.get(section, {})

                if isinstance(old_structure, dict) and isinstance(new_structure, dict):
                    old_keys = set(old_structure.keys())
                    new_keys = set(new_structure.keys())

                    # If more than 50% of keys changed, consider it structural
                    total_keys = len(old_keys | new_keys)
                    changed_keys = len((old_keys | new_keys) - (old_keys & new_keys))

                    if total_keys > 0 and changed_keys / total_keys > 0.5:
                        structural_changes.append(f"Major restructuring in section: {section}")

            return structural_changes

        except Exception as e:
            logger.error(f"Error detecting structural changes: {str(e)}")
            return []

    def generate_change_summary(self, changes: dict[str, Any]) -> str:
        """Generate a human-readable summary of changes."""
        try:
            summary_parts = []

            # Salary changes
            salary_increases = changes.get("salary_increases", {})
            if salary_increases:
                levels_count = len(salary_increases)
                if levels_count == 1:
                    level = list(salary_increases.keys())[0]
                    percentage = salary_increases[level].get("percentage", 0)
                    summary_parts.append(f"Salary increase of {percentage:.1f}% for {level}")
                else:
                    avg_percentage = (
                        sum(info.get("percentage", 0) for info in salary_increases.values()) / levels_count
                    )
                    summary_parts.append(
                        f"Salary increases averaging {avg_percentage:.1f}% across {levels_count} levels"
                    )

            # Working hours changes
            hours_reduction = changes.get("working_hours_reduction", {})
            if hours_reduction:
                hours = hours_reduction.get("hours", 0)
                summary_parts.append(f"Working hours reduced by {hours} hours per week")

            # New benefits
            new_benefits = changes.get("new_benefits", [])
            if new_benefits:
                if len(new_benefits) == 1:
                    summary_parts.append(f"Added new benefit: {new_benefits[0]}")
                else:
                    summary_parts.append(f"Added {len(new_benefits)} new benefits")

            # Leave changes
            leave_changes = changes.get("leave_changes", {})
            if leave_changes:
                summary_parts.append("Updated leave provisions")

            if not summary_parts:
                return "Minor administrative updates"

            return "; ".join(summary_parts)

        except Exception as e:
            logger.error(f"Error generating change summary: {str(e)}")
            return "Changes detected (details unavailable)"


# Global instance
ccnl_change_detector = CCNLChangeDetector()
