FROM python:3.13.2-slim

# Set working directory
WORKDIR /app

# Set non-sensitive environment variables
ARG APP_ENV=production
ARG POSTGRES_URL
ARG HF_INTENT_MODEL=mdeberta

ENV APP_ENV=${APP_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POSTGRES_URL=${POSTGRES_URL}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libmagic1 \
    && pip install --upgrade pip \
    && pip install uv \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first to leverage Docker cache
COPY pyproject.toml .
RUN uv venv && . .venv/bin/activate && uv pip install -e .

# Copy the application
COPY . .

# Make entrypoint script executable - do this before changing user
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Create log directory
RUN mkdir -p /app/logs

# DEV-251: Pre-download HuggingFace mDeBERTa model during build
# This prevents 30-120s model download on first query after container start
# Model is cached in /home/appuser/.cache/huggingface (can be volume-mounted)
RUN . /app/.venv/bin/activate && python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='MoritzLaurer/mDeBERTa-v3-base-mnli-xnli')"

# DEV-253: Optionally pre-download a fine-tuned model if HF_INTENT_MODEL is set
# to a HuggingFace Hub path (not "mdeberta" or "bart" which are already handled above)
RUN if [ "${HF_INTENT_MODEL}" != "mdeberta" ] && [ "${HF_INTENT_MODEL}" != "bart" ]; then \
      . /app/.venv/bin/activate && python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; AutoTokenizer.from_pretrained('${HF_INTENT_MODEL}'); AutoModelForSequenceClassification.from_pretrained('${HF_INTENT_MODEL}')" 2>/dev/null || true; \
    fi

# Default port
EXPOSE 8000

# Log the environment we're using
RUN echo "Using ${APP_ENV} environment"

# Command to run the application
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
