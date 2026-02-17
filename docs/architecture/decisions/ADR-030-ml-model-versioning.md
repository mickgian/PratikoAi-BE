# ADR-030: ML Model Versioning

## Status
Accepted

## Date
2026-02-17

## Context

PratikoAI uses machine learning models for intent classification:
- **Base model**: `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (zero-shot classification)
- **Fine-tuned models**: Trained from SUPER_USER feedback on QA (via `scripts/train_intent_classifier.py`)

Models are currently downloaded during Docker build (DEV-251) and cached in a Docker volume. There is no versioning or promotion workflow for fine-tuned models.

## Decision

### Use private HuggingFace Hub for model versioning

1. **Base model** remains public and is downloaded during Docker build (unchanged)

2. **Fine-tuned models** are pushed to private HF Hub repos:
   - Naming: `pratikoai/intent-classifier-v{major}.{minor}`
   - Private repos (requires `HF_TOKEN` for access)
   - Pushed via `huggingface-cli upload --private`

3. **Docker build integration** via `HF_INTENT_MODEL` build arg:
   - Default: `mdeberta` (base model, no HF Hub download needed)
   - Fine-tuned: `pratikoai/intent-classifier-v1.2` (downloaded at build time)
   - Already implemented in Dockerfile (DEV-253)

4. **Promotion workflow**:
   ```
   QA feedback -> train locally -> push to HF Hub -> update compose -> redeploy
   ```

5. **Management script** (`scripts/model_management.sh`):
   - `list`: Show available models on HF Hub
   - `current`: Show configured model in compose files
   - `promote <model-id>`: Update production compose with new model
   - `push <path> <version>`: Upload local model to HF Hub

### Why NOT MLflow/DVC/W&B
- Team of 1-2 developers, single model type
- HF Hub provides versioning, hosting, and access control
- No need for experiment tracking at this stage
- Can migrate to MLflow later if model count grows

## Consequences

### Positive
- Simple versioning with semantic naming
- HF Hub handles storage, access control, and CDN
- Existing Docker build integration works unchanged
- Clear promotion path from QA to production

### Negative
- No experiment tracking (training metrics, hyperparameters)
- Manual promotion workflow (script-assisted but not automated)
- HF Hub dependency for model downloads during build

## Related
- **DEV-251:** Pre-download HuggingFace model during Docker build
- **DEV-253:** Fine-tuned model support via HF_INTENT_MODEL build arg
- **ADR-028:** Deployment Pipeline Architecture
