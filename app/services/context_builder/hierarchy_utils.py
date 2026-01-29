"""Hierarchy utilities for document prioritization.

Contains functions for getting hierarchy weights and Italian category labels.
"""

from .constants import CATEGORY_LABELS_IT, HIERARCHY_WEIGHTS


def get_hierarchy_weight(doc_type: str) -> float:
    """Return Italian legal hierarchy weight for source prioritization.

    Args:
        doc_type: Document type (e.g., 'legge', 'circolare', 'dpr')

    Returns:
        Hierarchy weight between 0.0 and 1.0
    """
    if not doc_type:
        return 0.5
    return HIERARCHY_WEIGHTS.get(doc_type.lower(), 0.5)


def get_category_label_it(category: str | None) -> str:
    """Return Italian label for category/type for Fonti display (DEV-245).

    Args:
        category: Internal category name (e.g., 'regulatory_documents', 'legge')

    Returns:
        Italian label for display, or empty string if unknown
    """
    if not category:
        return ""
    return CATEGORY_LABELS_IT.get(category.lower(), category.replace("_", " "))
