# Langfuse Debugging Guide for PratikoAI RAG Pipeline

This guide explains how to set up and use Langfuse for debugging the LangGraph RAG pipeline.

## Table of Contents

1. [Langfuse Setup](#langfuse-setup)
2. [Configuration](#configuration)
3. [Using the Langfuse UI](#using-the-langfuse-ui)
4. [Filtering and Searching](#filtering-and-searching)
5. [Custom Spans](#custom-spans)
6. [Troubleshooting](#troubleshooting)

---

## Langfuse Setup

### 1. Create a Langfuse Account

1. Go to [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Click "Sign Up" and create an account (you can use Google, GitHub, or email)
3. Verify your email if required

### 2. Create a Project

1. After logging in, click "New Project"
2. Name it something like "PratikoAI-DEV" or "PratikoAI-Local"
3. Click "Create"

### 3. Generate API Keys

1. In your project, go to **Settings** > **API Keys**
2. Click "Create new API keys"
3. Copy both keys:
   - **Public Key**: Starts with `pk-lf-...`
   - **Secret Key**: Starts with `sk-lf-...`

### 4. Configure Environment Variables

Add these to your `.env.development.local` file:

```bash
# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional: Override sampling rate (default: 100% for DEV, 10% for PROD)
# LANGFUSE_SAMPLING_RATE=1.0
```

---

## Configuration

### Environment-Aware Sampling

The integration automatically adjusts sampling based on environment:

| Environment | Default Sampling | Rationale |
|------------|------------------|-----------|
| DEVELOPMENT | 100% | Full visibility for debugging |
| QA | 100% | Full visibility for testing |
| PRODUCTION | 10% | Cost optimization |

Override with `LANGFUSE_SAMPLING_RATE` environment variable (0.0 to 1.0).

### Session and User Tracking

Every trace automatically includes:
- **Session ID**: Links all interactions in a conversation
- **User ID**: Groups traces by user (defaults to "anonymous")
- **Environment**: development/qa/production tag

---

## Using the Langfuse UI

### Viewing Traces

1. Go to your Langfuse project
2. Click **Traces** in the sidebar
3. You'll see a list of all captured traces

Each trace shows:
- **Timestamp**: When the request occurred
- **User ID**: Who made the request
- **Session ID**: Conversation identifier
- **Latency**: Total request time
- **Cost**: Estimated token cost

### Trace Details

Click on a trace to see:
- **Input**: The user's question
- **Output**: The AI response
- **Steps/Spans**: Breakdown of operations (LLM calls, retrievals, etc.)
- **Tokens**: Input/output token counts
- **Metadata**: Environment, tags, custom data

### Timeline View

The timeline shows the sequence and duration of operations:
- LLM calls (model, tokens, latency)
- Embedding calls
- Custom spans (retrieval, node execution)

---

## Filtering and Searching

### By Session

To follow a conversation:
1. Copy the Session ID from a trace
2. Use the filter: `session_id = "your-session-id"`
3. See all messages in that conversation

### By User

To see all activity for a user:
1. Filter: `user_id = "user-123"`

### By Environment

To filter by environment:
1. Click on **Metadata** filters
2. Add filter: `environment = "development"`

### By Tags

Traces are tagged automatically:
- `rag`: All RAG pipeline traces
- `ainvoke`: Synchronous invocations
- `stream`: Streaming invocations

Filter with: `tags CONTAINS "rag"`

### By Time Range

Use the date picker to narrow down to specific time periods.

---

## Custom Spans

### Using Node Spans

For debugging specific LangGraph nodes:

```python
from app.observability import node_span

async def my_node(state: RAGState) -> dict:
    with node_span(
        node_name="build_context",
        step_number="S040",
        trace_id=state.get("trace_id", ""),
    ) as span:
        # Your node logic here
        context = await build_context(state)
        span.set_output({"chunks_count": len(context.chunks)})
        return {"context": context}
```

### Using Retrieval Spans

For debugging search operations:

```python
from app.observability import retrieval_span

async def search_knowledge_base(query: str, trace_id: str):
    with retrieval_span(
        query=query,
        trace_id=trace_id,
        search_type="hybrid",
    ) as span:
        results = await hybrid_search(query)
        span.set_output({
            "results_count": len(results),
            "top_score": results[0].score if results else 0,
        })
        return results
```

### Using Generic Spans

For any custom operation:

```python
from app.observability import span_context

async def process_documents(docs: list, trace_id: str):
    with span_context(
        name="document_processing",
        trace_id=trace_id,
        input_data={"doc_count": len(docs)},
        metadata={"processor": "pdf"},
    ) as span:
        processed = await process_all(docs)
        span.set_output({"processed_count": len(processed)})
        return processed
```

---

## Troubleshooting

### Traces Not Appearing

1. **Check credentials**: Verify `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set
2. **Check host**: Ensure `LANGFUSE_HOST` is correct (default: `https://cloud.langfuse.com`)
3. **Check sampling**: In DEV/QA, sampling should be 100%. Check logs for "skipping handler creation"
4. **Wait a moment**: Traces can take a few seconds to appear in the UI

### Missing Session/User IDs

- Session ID is generated automatically if not provided
- User ID defaults to "anonymous" if not passed

### High Costs in Production

- Set `LANGFUSE_SAMPLING_RATE=0.05` for 5% sampling
- Use tags to filter what gets tracked

### Spans Not Showing

- Ensure you're passing the correct `trace_id`
- Check that the Langfuse client is initialized (credentials present)
- Spans degrade gracefully - check logs for warnings

### Performance Issues

- Handler creation is <1ms
- Sampling decision is <0.1ms
- Tracing is async and shouldn't impact request latency

---

## Best Practices

1. **Use meaningful session IDs**: Match your conversation/chat session IDs
2. **Pass user IDs when available**: Helps with user-level debugging
3. **Use tags for categorization**: Makes filtering easier
4. **Add custom spans sparingly**: Focus on key operations
5. **Review costs periodically**: Adjust sampling rates as needed

---

## Related Documentation

- [Langfuse Documentation](https://langfuse.com/docs)
- [LangGraph Integration](https://langfuse.com/docs/integrations/langchain)
- [ADR-004: LangGraph for RAG](../architecture/decisions/ADR-004-langgraph-rag-pipeline.md)
