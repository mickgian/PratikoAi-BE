"""Model-based graders using LLM-as-judge.

This package contains graders that use LLMs to evaluate responses:
- OllamaJudge: Local LLM evaluation via Ollama
"""

from evals.graders.model_graders.ollama_judge import OllamaJudge

__all__ = [
    "OllamaJudge",
]
