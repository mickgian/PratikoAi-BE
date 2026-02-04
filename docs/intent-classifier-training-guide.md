# Intent Classifier Training Guide

Guide for training and deploying fine-tuned intent classification models.

## What is an ML Model?

Think of a trained ML model like **compiled code**:

```
Source Code  →  Compiler  →  Binary Executable
Labeled Data →  Training  →  Model Files (~280MB)
```

| Concept       | Software Analogy       |
|---------------|------------------------|
| Labeled Data  | Source code             |
| Training      | Compilation             |
| Model Files   | Compiled binary         |
| Inference     | Running the binary      |
| Deployment    | Deploying the binary    |

A model is a static artifact. It does not learn or update at runtime.
To improve it, you retrain with new data and deploy the new model.

---

## Zero-Shot vs Fine-Tuned

### Zero-Shot (Current)

Uses a general-purpose NLI model (mDeBERTa) to classify text into
arbitrary categories described in natural language.

- **No training data needed**: Works out of the box
- **Flexible**: Categories can be changed at any time
- **Less accurate**: ~70-80% accuracy on domain-specific tasks
- **How it works**: "Does this text match the hypothesis 'questa domanda riguarda calculator'?"

### Fine-Tuned (Target)

Takes a pre-trained model and trains it specifically on our labeled data.

- **Requires labeled data**: Minimum ~200 examples per category
- **Fixed categories**: Changing categories requires retraining
- **More accurate**: ~90-95% accuracy on domain-specific tasks
- **How it works**: Direct text → category mapping learned from examples

---

## Training Lifecycle

```
┌──────────────────────────────────────────────────────────────────────┐
│                        TRAINING LIFECYCLE                            │
│                                                                      │
│  1. COLLECT      2. LABEL        3. EXPORT       4. TRAIN           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ Low-conf │    │ Expert  │    │  JSONL   │    │Training │         │
│  │ queries  │───▶│ labels  │───▶│  file    │───▶│ script  │         │
│  │ captured │    │ via UI  │    │ exported │    │ runs    │         │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘         │
│                                                      │              │
│  7. MONITOR      6. DEPLOY       5. VALIDATE         │              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────▼────┐        │
│  │Langfuse │    │ Change  │    │ Eval on  │    │  Model   │        │
│  │ metrics │◀───│ env var │◀───│ test set │◀───│  files   │        │
│  │ tracked │    │ restart │    │  ≥90%    │    │ on Hub   │        │
│  └─────────┘    └─────────┘    └─────────┘    └──────────┘        │
│                                                                      │
│  ROLLBACK: Change HF_INTENT_MODEL back to "mdeberta" and restart    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Differences from Databases

| Database                          | ML Model                        |
|-----------------------------------|---------------------------------|
| Stores individual records         | Stores learned patterns         |
| Update one row at a time          | Retrain on entire dataset       |
| Changes are immediate             | Changes require retraining      |
| Scales with hardware              | Quality scales with data        |
| Backup = copy files               | Rollback = point to old model   |
| Schema defines structure          | Training defines behavior       |

**Important**: Adding one label does NOT improve the model. You must:
1. Collect enough new labels
2. Export all labeled data
3. Retrain the model
4. Deploy the new model

---

## Step-by-Step Deployment Playbook

### Prerequisites

- At least 200 labeled examples per intent category (1000+ recommended)
- A HuggingFace Hub account (for model storage)
- GPU access for training (optional, CPU works but slower)

### Step 1: Export Training Data

```bash
# Via API (admin only)
curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/api/v1/labeling/export?format=jsonl" \
     -o intent_training_data.jsonl

# Or via the UI: /expert/labeling → "Esporta Dati" → JSONL
```

### Step 2: Verify Data Quality

```bash
# Count examples per label
cat intent_training_data.jsonl | \
  python -c "import sys,json,collections; \
  c=collections.Counter(json.loads(l)['label'] for l in sys.stdin); \
  print(dict(c))"

# Expected: each label should have 200+ examples
```

### Step 3: Train the Model

```bash
# Install training dependencies
uv pip install -e ".[training]"

# Train (CPU, ~30-60 minutes)
uv run python scripts/train_intent_classifier.py \
    --data intent_training_data.jsonl \
    --output ./intent-classifier-v1

# Train and push to HuggingFace Hub
uv run python scripts/train_intent_classifier.py \
    --data intent_training_data.jsonl \
    --push-to-hub pratikoai/intent-classifier-v1

# Optional: use GPU for faster training (~5 minutes)
uv run python scripts/train_intent_classifier.py \
    --data intent_training_data.jsonl \
    --push-to-hub pratikoai/intent-classifier-v1 \
    --device cuda
```

### Step 4: Evaluate Results

The training script outputs evaluation metrics automatically:

```
Evaluation Results:
  Accuracy: 0.923
  F1 (weighted): 0.921
  Per-class:
    chitchat: P=0.95 R=0.93 F1=0.94
    technical_research: P=0.90 R=0.92 F1=0.91
    calculator: P=0.93 R=0.91 F1=0.92
    theoretical_definition: P=0.89 R=0.88 F1=0.89
    golden_set: P=0.94 R=0.96 F1=0.95
```

**Minimum acceptable accuracy**: 90% overall, 85% per class.

### Step 5: Deploy

```bash
# Option A: Local model path
HF_INTENT_MODEL=./intent-classifier-v1 docker-compose up -d app

# Option B: HuggingFace Hub model (recommended)
HF_INTENT_MODEL=pratikoai/intent-classifier-v1 docker-compose up -d app
```

The classifier auto-detects whether the model is zero-shot or fine-tuned
and uses the appropriate pipeline.

### Step 6: Monitor

Check Langfuse for classification accuracy after deployment.
Compare confidence distributions: fine-tuned models should show
higher average confidence (>0.85) vs zero-shot (~0.5-0.7).

### Rollback

If the fine-tuned model performs worse:

```bash
# Revert to zero-shot
HF_INTENT_MODEL=mdeberta docker-compose up -d app
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **Zero-shot** | Classification without task-specific training |
| **Fine-tuned** | Model trained on task-specific labeled data |
| **NLI** | Natural Language Inference - determining text relationships |
| **Epoch** | One complete pass through all training data |
| **Learning rate** | How much the model updates per training step |
| **Overfitting** | Model memorizes training data, poor on new data |
| **Stratified split** | Train/test split preserving label proportions |
| **F1 score** | Harmonic mean of precision and recall |
| **HuggingFace Hub** | Repository for ML models (like GitHub for code) |
| **Safetensors** | Efficient model weight storage format |
| **id2label** | Model config mapping integer IDs to label strings |
| **Pipeline** | HuggingFace abstraction for model inference |
