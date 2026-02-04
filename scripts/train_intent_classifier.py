"""Intent Classifier Training Script.

DEV-253: Fine-tunes a pre-trained transformer model on labeled intent data
exported from the labeling UI.

Usage:
    # Train locally
    uv run python scripts/train_intent_classifier.py \
        --data intent_training_data.jsonl \
        --output ./intent-classifier-v1

    # Train and push to HuggingFace Hub
    uv run python scripts/train_intent_classifier.py \
        --data intent_training_data.jsonl \
        --push-to-hub pratikoai/intent-classifier-v1

    # With GPU
    uv run python scripts/train_intent_classifier.py \
        --data intent_training_data.jsonl \
        --push-to-hub pratikoai/intent-classifier-v1 \
        --device cuda

Prerequisites:
    uv pip install -e ".[training]"
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

INTENT_LABELS = [
    "chitchat",
    "theoretical_definition",
    "technical_research",
    "calculator",
    "golden_set",
]

LABEL2ID = {label: idx for idx, label in enumerate(INTENT_LABELS)}
ID2LABEL = dict(enumerate(INTENT_LABELS))

# Training defaults
DEFAULT_BASE_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
DEFAULT_EPOCHS = 5
DEFAULT_BATCH_SIZE = 16
DEFAULT_LEARNING_RATE = 2e-5
DEFAULT_TEST_SIZE = 0.2
DEFAULT_MAX_LENGTH = 128


def load_data(path: str) -> list[dict]:
    """Load and validate JSONL training data."""
    data = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"WARNING: Skipping invalid JSON on line {i}")
                continue

            if "text" not in item or "label" not in item:
                print(f"WARNING: Skipping line {i} - missing 'text' or 'label' field")
                continue

            if not item["text"].strip():
                print(f"WARNING: Skipping line {i} - empty text")
                continue

            if item["label"] not in LABEL2ID:
                print(f"WARNING: Skipping line {i} - unknown label '{item['label']}'")
                continue

            data.append({"text": item["text"].strip(), "label": item["label"]})

    return data


def print_data_summary(data: list[dict]) -> None:
    """Print summary of training data distribution."""
    counts = Counter(item["label"] for item in data)
    total = len(data)

    print(f"\nTraining Data Summary ({total} examples):")
    print("-" * 40)
    for label in INTENT_LABELS:
        count = counts.get(label, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {label:30s} {count:4d} ({pct:5.1f}%) {bar}")

    min_count = min(counts.values()) if counts else 0
    if min_count < 50:
        print(f"\nWARNING: Minimum examples per class is {min_count}. Recommend 200+.")
    print()


def train(args: argparse.Namespace) -> None:
    """Run the training pipeline."""
    # Import heavy deps only when training
    try:
        from datasets import Dataset
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
    except ImportError:
        print("ERROR: Training dependencies not installed.")
        print("Run: uv pip install -e '.[training]'")
        sys.exit(1)

    # Load data
    print(f"Loading data from {args.data}...")
    data = load_data(args.data)
    if len(data) < 10:
        print(f"ERROR: Only {len(data)} valid examples. Need at least 10.")
        sys.exit(1)

    print_data_summary(data)

    # Stratified train/test split
    texts = [item["text"] for item in data]
    labels = [item["label"] for item in data]
    label_ids = [LABEL2ID[label] for label in labels]

    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts,
        label_ids,
        test_size=args.test_size,
        stratify=label_ids,
        random_state=42,
    )

    print(f"Train: {len(train_texts)} examples, Test: {len(test_texts)} examples")

    # Load tokenizer and model
    base_model = args.base_model
    print(f"Loading base model: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=len(INTENT_LABELS),
        label2id=LABEL2ID,
        id2label=ID2LABEL,
        ignore_mismatched_sizes=True,
    )

    # Tokenize
    def tokenize(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=args.max_length,
        )

    train_dataset = Dataset.from_dict({"text": train_texts, "label": train_labels})
    test_dataset = Dataset.from_dict({"text": test_texts, "label": test_labels})

    train_dataset = train_dataset.map(tokenize, batched=True)
    test_dataset = test_dataset.map(tokenize, batched=True)

    # Output directory
    output_dir = args.output or "./intent-classifier-output"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_steps=10,
        warmup_ratio=0.1,
        fp16=args.device == "cuda",
        report_to="none",
    )

    # Trainer
    import numpy as np

    def compute_metrics(eval_pred):
        logits, label_ids_batch = eval_pred
        preds = np.argmax(logits, axis=-1)
        accuracy = (preds == label_ids_batch).mean()
        return {"accuracy": accuracy}

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        compute_metrics=compute_metrics,
    )

    # Train
    print(f"\nStarting training ({args.epochs} epochs)...")
    trainer.train()

    # Evaluate
    print("\nEvaluation Results:")
    print("-" * 50)

    predictions = trainer.predict(test_dataset)
    pred_labels = np.argmax(predictions.predictions, axis=-1)
    true_labels = test_labels

    report = classification_report(
        true_labels,
        pred_labels,
        target_names=INTENT_LABELS,
        digits=3,
    )
    print(report)

    # Save model
    if args.push_to_hub:
        print(f"\nPushing model to HuggingFace Hub: {args.push_to_hub}")
        trainer.push_to_hub(args.push_to_hub)
        tokenizer.push_to_hub(args.push_to_hub)
        print(f"Model pushed to: https://huggingface.co/{args.push_to_hub}")
    else:
        save_dir = args.output or output_dir
        print(f"\nSaving model to {save_dir}")
        trainer.save_model(save_dir)
        tokenizer.save_pretrained(save_dir)
        print(f"Model saved. To use: HF_INTENT_MODEL={save_dir}")

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune intent classifier from labeled data")
    parser.add_argument(
        "--data",
        required=True,
        help="Path to JSONL training data (exported from labeling UI)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for trained model (default: ./intent-classifier-output)",
    )
    parser.add_argument(
        "--push-to-hub",
        default=None,
        help="HuggingFace Hub repo to push model (e.g. pratikoai/intent-classifier-v1)",
    )
    parser.add_argument(
        "--base-model",
        default=DEFAULT_BASE_MODEL,
        help=f"Base model to fine-tune (default: {DEFAULT_BASE_MODEL})",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=DEFAULT_EPOCHS,
        help=f"Number of training epochs (default: {DEFAULT_EPOCHS})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Training batch size (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=DEFAULT_LEARNING_RATE,
        help=f"Learning rate (default: {DEFAULT_LEARNING_RATE})",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=DEFAULT_TEST_SIZE,
        help=f"Test set proportion (default: {DEFAULT_TEST_SIZE})",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=DEFAULT_MAX_LENGTH,
        help=f"Max token length (default: {DEFAULT_MAX_LENGTH})",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device for training (default: cpu)",
    )

    args = parser.parse_args()

    if not Path(args.data).exists():
        print(f"ERROR: Data file not found: {args.data}")
        sys.exit(1)

    train(args)


if __name__ == "__main__":
    main()
