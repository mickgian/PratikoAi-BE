"""RAG quality evaluation with Langfuse tracking.

Runs golden dataset evaluations and stores results in Langfuse for
time-series quality tracking across deployments.

Usage:
    uv run python tests/evals/eval_with_langfuse.py

Requires:
    - LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST env vars
    - OPENAI_API_KEY for the RAG pipeline
    - Running database with indexed documents
"""

import asyncio
import os
import sys

# Golden dataset: Italian CCNL/labor law queries with expected answers
GOLDEN_DATASET = [
    {
        "input": "Qual e' il periodo di preavviso per un impiegato del CCNL Metalmeccanici con 5 anni di anzianita'?",
        "expected_keywords": ["preavviso", "mesi", "metalmeccanici"],
    },
    {
        "input": "Come funziona il TFR per un dipendente a tempo determinato?",
        "expected_keywords": ["TFR", "trattamento", "fine rapporto"],
    },
    {
        "input": "Quali sono le aliquote IRPEF per il 2024?",
        "expected_keywords": ["aliquot", "scaglion", "IRPEF"],
    },
    {
        "input": "Cosa prevede la rottamazione quater per le cartelle esattoriali?",
        "expected_keywords": ["rottamazione", "cartell", "rate"],
    },
    {
        "input": "Qual e' la procedura per il licenziamento per giusta causa?",
        "expected_keywords": ["licenziamento", "giusta causa", "disciplinare"],
    },
]


def _check_langfuse_available() -> bool:
    """Check if Langfuse credentials are configured."""
    return bool(os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"))


async def run_evaluation():
    """Run golden dataset evaluation and track in Langfuse."""
    if not _check_langfuse_available():
        print("LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY required. Skipping.")
        sys.exit(0)

    try:
        from langfuse import Langfuse
    except ImportError:
        print("langfuse not installed. Run: uv add langfuse")
        sys.exit(1)

    langfuse = Langfuse()

    # Try to use existing Langfuse dataset, or create evaluation traces directly
    dataset_name = "pratiko-rag-golden-set"

    try:
        dataset = langfuse.get_dataset(dataset_name)
        items = dataset.items
        print(f"Using Langfuse dataset '{dataset_name}' with {len(items)} items")
    except Exception:
        # Dataset doesn't exist yet - use local golden dataset
        print(f"Dataset '{dataset_name}' not found in Langfuse. Using local golden dataset.")
        items = None

    results = []
    eval_items = items if items else GOLDEN_DATASET

    for i, item in enumerate(eval_items):
        query = item.get("input") if isinstance(item, dict) else item.input
        expected = item.get("expected_keywords", []) if isinstance(item, dict) else []

        print(f"[{i + 1}/{len(eval_items)}] Evaluating: {query[:60]}...")

        # Create a trace for this evaluation
        trace = langfuse.trace(
            name="rag-eval",
            metadata={
                "eval_run": True,
                "dataset": dataset_name,
                "item_index": i,
            },
            tags=["evaluation", "golden-dataset"],
        )

        try:
            # Import RAG pipeline (requires running app context)
            from app.core.langgraph.graph import build_graph

            graph = build_graph()
            result = await graph.ainvoke(
                {
                    "messages": [{"role": "user", "content": query}],
                    "user_id": "eval_system",
                },
            )

            response_text = ""
            if result.get("messages"):
                last_msg = result["messages"][-1]
                response_text = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

            # Score: keyword coverage (simple heuristic)
            if expected:
                response_lower = response_text.lower()
                hits = sum(1 for kw in expected if kw.lower() in response_lower)
                keyword_score = hits / len(expected)
            else:
                keyword_score = None

            # Record scores in Langfuse
            if keyword_score is not None:
                langfuse.score(
                    trace_id=trace.id,
                    name="keyword_coverage",
                    value=keyword_score,
                    comment=f"Matched {hits}/{len(expected)} expected keywords",
                )

            langfuse.score(
                trace_id=trace.id,
                name="has_response",
                value=1.0 if len(response_text) > 50 else 0.0,
            )

            results.append(
                {
                    "query": query,
                    "response_length": len(response_text),
                    "keyword_score": keyword_score,
                    "success": True,
                }
            )

            print(f"  -> Response: {len(response_text)} chars, keyword_score: {keyword_score}")

        except Exception as e:
            langfuse.score(
                trace_id=trace.id,
                name="has_response",
                value=0.0,
                comment=f"Error: {type(e).__name__}: {str(e)[:200]}",
            )
            results.append(
                {
                    "query": query,
                    "error": str(e),
                    "success": False,
                }
            )
            print(f"  -> ERROR: {e}")

    # Flush all events to Langfuse
    langfuse.flush()

    # Summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    keyword_scores = [r["keyword_score"] for r in successful if r.get("keyword_score") is not None]

    print("\n--- Evaluation Summary ---")
    print(f"Total: {len(results)}, Success: {len(successful)}, Failed: {len(failed)}")
    if keyword_scores:
        avg_score = sum(keyword_scores) / len(keyword_scores)
        print(f"Avg keyword coverage: {avg_score:.2f}")
    print(f"Results tracked in Langfuse dataset: {dataset_name}")

    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())
