"""
FAQTool for LangGraph - On-demand FAQ/Golden Set Queries

This tool provides semantic FAQ matching for the RAG pipeline, enabling the LLM
to query the Golden Set (FAQ database) when needed.

Note: Currently uses a mock implementation for testing. In production, this will
integrate with SemanticFAQMatcher and IntelligentFAQService via proper dependency
injection.
"""

import json
from typing import Optional
from langchain_core.tools import BaseTool

from app.core.logging import logger


class FAQTool(BaseTool):
    """
    Tool for querying the FAQ/Golden Set with semantic search.

    Provides semantic FAQ matching using the SemanticFAQMatcher service,
    supporting Italian language queries with confidence-based filtering.
    """

    name: str = "FAQTool"
    description: str = """
    Query the FAQ/Golden Set database for answers to common questions.

    Use this tool when:
    - User asks a question that might be in the FAQ database
    - Looking for standard answers to common tax/legal questions
    - Need high-confidence pre-approved answers

    Args:
        query: The user's question in Italian
        max_results: Maximum number of FAQ matches to return (default: 3)
        min_confidence: Minimum confidence level: 'low', 'medium', 'high', or 'exact' (default: 'medium')
        include_outdated: Include FAQs that may need updates (default: False)

    Returns:
        JSON with FAQ matches, each containing question, answer, similarity score, and confidence level.
    """

    async def _arun(
        self,
        query: str,
        max_results: Optional[int] = 3,
        min_confidence: Optional[str] = 'medium',
        include_outdated: Optional[bool] = False,
        **kwargs
    ) -> str:
        """
        Execute FAQ query asynchronously.

        Args:
            query: User query in Italian
            max_results: Maximum number of FAQ matches to return
            min_confidence: Minimum confidence level ('low', 'medium', 'high', 'exact')
            include_outdated: Include FAQs that may need updates

        Returns:
            JSON string with FAQ matches and metadata
        """
        try:
            logger.info(f"FAQTool: Executing FAQ query: '{query[:100]}...'")

            # For now, return a mock response since the actual services aren't wired
            # In production, this would use SemanticFAQMatcher with proper dependency injection

            # Mock response for testing
            matches = []

            # Simulate finding some FAQ matches based on query
            if query and len(query) > 0:
                # Create a mock match for demonstration
                matches = [{
                    "faq_id": "mock_faq_001",
                    "question": f"Mock FAQ question related to: {query[:50]}",
                    "answer": "Questa è una risposta FAQ di esempio. In produzione, questo utilizzerebbe il SemanticFAQMatcher per trovare FAQ corrispondenti.",
                    "similarity_score": 0.85,
                    "confidence": min_confidence or "medium",
                    "needs_update": False,
                    "matched_concepts": ["test", "mock"],
                    "source_metadata": {}
                }]

            # Format results
            if not matches:
                response = {
                    "success": True,
                    "matches": [],
                    "match_count": 0,
                    "message": "Nessuna FAQ corrispondente trovata. Posso aiutarti con una ricerca più ampia."
                }
            else:
                # Matches are already formatted as dictionaries
                response = {
                    "success": True,
                    "matches": matches,
                    "match_count": len(matches),
                    "query": query,
                    "min_confidence": min_confidence,
                    "message": f"Trovate {len(matches)} FAQ corrispondenti."
                }

            logger.info(f"FAQTool: Found {len(matches)} FAQ matches for query")
            return json.dumps(response, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"FAQTool error: {e}", exc_info=True)
            error_response = {
                "success": False,
                "error": str(e),
                "matches": [],
                "match_count": 0,
                "message": "Si è verificato un errore durante la ricerca FAQ."
            }
            return json.dumps(error_response, ensure_ascii=False, indent=2)

    def _run(self, *args, **kwargs) -> str:
        """Synchronous version (not implemented, use async)."""
        raise NotImplementedError("FAQTool only supports async execution. Use _arun instead.")


# Global tool instance for easy import
faq_tool = FAQTool()