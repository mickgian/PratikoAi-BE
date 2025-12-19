"""This file contains the prompts for the agent."""

import os
from datetime import datetime

from app.core.config import settings


def load_system_prompt():
    """Load the system prompt from the file."""
    with open(os.path.join(os.path.dirname(__file__), "system.md")) as f:
        return f.read().format(
            agent_name=settings.PROJECT_NAME + " Agent",
            current_date_and_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


def load_document_analysis_prompt():
    """Load document analysis guidelines (injected conditionally for document queries)."""
    path = os.path.join(os.path.dirname(__file__), "document_analysis.md")
    with open(path) as f:
        return f.read()


def load_document_analysis_override():
    """Load short directive override prompt for document analysis (injected at TOP of prompt)."""
    path = os.path.join(os.path.dirname(__file__), "document_analysis_override.md")
    with open(path) as f:
        return f.read()


SYSTEM_PROMPT = load_system_prompt()
DOCUMENT_ANALYSIS_PROMPT = load_document_analysis_prompt()
DOCUMENT_ANALYSIS_OVERRIDE = load_document_analysis_override()
