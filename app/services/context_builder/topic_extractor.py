"""Topic and value extraction from documents.

Extracts key topics and values for action relevance.
"""

import re


def extract_topics(doc: dict) -> list[str]:
    """Extract key topics from document for action relevance.

    Args:
        doc: Document dictionary with title and content

    Returns:
        List of extracted topic keywords
    """
    topics = []
    title = doc.get("title", "")
    content = doc.get("content", "")

    # Extract from title - split on common separators
    if title:
        # Remove article references like "Art. 16" and legal refs
        clean_title = re.sub(r"Art\.?\s*\d+", "", title)
        clean_title = re.sub(r"D\.?Lgs\.?\s*\d+/\d+", "", clean_title)
        clean_title = re.sub(r"DPR\s*\d+/\d+", "", clean_title)
        clean_title = re.sub(r"n\.\s*\d+", "", clean_title)

        # Split on separators and filter
        words = re.split(r"[-–—,;:/()]+", clean_title)
        for word in words:
            word = word.strip()
            if len(word) > 3:  # Skip short words
                topics.append(word)

    # Extract key terms from content (first 500 chars)
    if content:
        content_preview = content[:500]
        # Look for capitalized terms (likely important)
        capitalized = re.findall(r"\b[A-Z][A-Za-z]{3,}\b", content_preview)
        topics.extend(capitalized[:5])  # Limit to 5 from content

    # Deduplicate while preserving order
    seen = set()
    unique_topics = []
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower not in seen:
            seen.add(topic_lower)
            unique_topics.append(topic)

    return unique_topics[:10]  # Cap at 10 topics


def extract_values(doc: dict) -> list[str]:
    """Extract specific values (percentages, dates, amounts) for action prompts.

    Args:
        doc: Document dictionary with content

    Returns:
        List of extracted values (percentages, euro amounts, dates)
    """
    content = doc.get("content", "")
    if not content:
        return []

    values = []

    # Extract percentages (e.g., 22%, 10,5%)
    percentages = re.findall(r"\b\d+(?:[,\.]\d+)?%", content)
    values.extend(percentages)

    # Extract euro amounts (e.g., €1.000, 5.000 euro, € 10.000)
    euro_amounts = re.findall(r"€\s*[\d.,]+|\b[\d.]+(?:,\d+)?\s*euro\b", content, re.IGNORECASE)
    values.extend(euro_amounts[:5])  # Limit euro amounts

    # Extract dates in Italian format (e.g., 15/03/2024, 15 marzo 2024)
    dates = re.findall(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", content)
    values.extend(dates[:3])  # Limit dates

    # Extract article numbers (e.g., Art. 16, articolo 2)
    articles = re.findall(r"Art\.?\s*\d+|articolo\s+\d+", content, re.IGNORECASE)
    values.extend(articles[:3])  # Limit articles

    # Deduplicate
    return list(dict.fromkeys(values))[:15]  # Cap at 15 values
