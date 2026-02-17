# =============================================================================
# PratikoAI Backend - Multi-stage Docker Build
# =============================================================================
# Stage 1 (builder): Install system deps + Python deps + build wheels
# Stage 2 (runtime): Slim image with only runtime deps + app code
# Target: ~800MB (down from ~2GB+ single-stage)
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM python:3.13.2-slim AS builder

WORKDIR /app

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && pip install --no-cache-dir uv \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first (Docker layer cache)
COPY pyproject.toml .

# Create venv and install all dependencies
RUN uv venv && . .venv/bin/activate && uv pip install -e .

# Copy application code
COPY . .

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.13.2-slim AS runtime

ARG APP_ENV=production
ARG HF_INTENT_MODEL=mdeberta

ENV APP_ENV=${APP_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install only runtime system dependencies (no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv and app code from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Make entrypoint script executable
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Create log directory
RUN mkdir -p /app/logs

# DEV-251: Pre-download HuggingFace mDeBERTa model during build
# Prevents 30-120s model download on first query after container start
RUN . /app/.venv/bin/activate && python -c \
    "from transformers import pipeline; pipeline('zero-shot-classification', model='MoritzLaurer/mDeBERTa-v3-base-mnli-xnli')"

# DEV-253: Optionally pre-download a fine-tuned model from HF Hub
RUN if [ "${HF_INTENT_MODEL}" != "mdeberta" ] && [ "${HF_INTENT_MODEL}" != "bart" ]; then \
      . /app/.venv/bin/activate && python -c \
        "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
         AutoTokenizer.from_pretrained('${HF_INTENT_MODEL}'); \
         AutoModelForSequenceClassification.from_pretrained('${HF_INTENT_MODEL}')" 2>/dev/null || true; \
    fi

EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
