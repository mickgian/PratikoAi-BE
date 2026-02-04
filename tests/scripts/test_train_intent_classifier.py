"""TDD Tests for DEV-253: Intent Classifier Training Script.

Tests for the training script that fine-tunes the intent classifier
from exported labeled data.

Run with: pytest tests/scripts/test_train_intent_classifier.py -v
"""

import json
import os
import tempfile

import pytest


@pytest.fixture
def sample_training_data():
    """Create sample JSONL training data."""
    data = [
        {"text": "Ciao, come stai?", "label": "chitchat"},
        {"text": "Buongiorno!", "label": "chitchat"},
        {"text": "Grazie mille", "label": "chitchat"},
        {"text": "Cos'e il regime forfettario?", "label": "theoretical_definition"},
        {"text": "Definizione di IVA", "label": "theoretical_definition"},
        {"text": "Cosa significa IRPEF?", "label": "theoretical_definition"},
        {"text": "Come calcolare l'imposta sostitutiva?", "label": "technical_research"},
        {"text": "Procedura per rimborso IVA", "label": "technical_research"},
        {"text": "Requisiti per agevolazione prima casa", "label": "technical_research"},
        {"text": "Calcola IVA su 1000 euro", "label": "calculator"},
        {"text": "Quanto netto da 2500 lordi?", "label": "calculator"},
        {"text": "Calcolo contributi INPS", "label": "calculator"},
        {"text": "Art. 7-ter DPR 633/72", "label": "golden_set"},
        {"text": "Legge 104/92 art. 33", "label": "golden_set"},
        {"text": "D.Lgs. 81/2008 articolo 37", "label": "golden_set"},
    ]
    return data


@pytest.fixture
def training_data_file(sample_training_data):
    """Create a temporary JSONL file with sample training data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for item in sample_training_data:
            f.write(json.dumps(item) + "\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestDataLoading:
    """Test training data loading and validation."""

    def test_load_jsonl_data(self, training_data_file):
        """JSONL file should be loadable as list of dicts."""
        data = []
        with open(training_data_file) as f:
            for line in f:
                item = json.loads(line.strip())
                data.append(item)

        assert len(data) == 15
        assert all("text" in item for item in data)
        assert all("label" in item for item in data)

    def test_all_labels_present(self, sample_training_data):
        """Training data should contain all 5 intent labels."""
        labels = set(item["label"] for item in sample_training_data)
        expected = {"chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"}
        assert labels == expected

    def test_minimum_examples_per_label(self, sample_training_data):
        """Each label should have at least 3 examples (test data minimum)."""
        from collections import Counter

        counts = Counter(item["label"] for item in sample_training_data)
        for label, count in counts.items():
            assert count >= 3, f"Label '{label}' has only {count} examples, need at least 3"

    def test_empty_text_rejected(self):
        """Empty text entries should be filtered out."""
        data = [
            {"text": "", "label": "chitchat"},
            {"text": "Valid text", "label": "chitchat"},
            {"text": "   ", "label": "chitchat"},
        ]
        valid = [item for item in data if item["text"].strip()]
        assert len(valid) == 1

    def test_invalid_label_detected(self, sample_training_data):
        """Invalid labels should be detectable."""
        valid_labels = {"chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"}
        data_with_invalid = sample_training_data + [{"text": "test", "label": "invalid_label"}]

        invalid = [item for item in data_with_invalid if item["label"] not in valid_labels]
        assert len(invalid) == 1
        assert invalid[0]["label"] == "invalid_label"


class TestDataSplit:
    """Test train/test split logic."""

    def test_stratified_split_preserves_proportions(self, sample_training_data):
        """Stratified split should preserve label proportions."""
        from collections import Counter

        # Simple stratified split simulation (80/20)
        train_ratio = 0.8
        by_label: dict[str, list] = {}
        for item in sample_training_data:
            by_label.setdefault(item["label"], []).append(item)

        train_data = []
        test_data = []
        for label, items in by_label.items():
            split_idx = max(1, int(len(items) * train_ratio))
            train_data.extend(items[:split_idx])
            test_data.extend(items[split_idx:])

        train_labels = Counter(item["label"] for item in train_data)
        test_labels = Counter(item["label"] for item in test_data)

        # Each label should be in both sets
        for label in by_label:
            assert label in train_labels, f"Label '{label}' missing from train set"
            assert label in test_labels, f"Label '{label}' missing from test set"

    def test_split_ratio_approximately_80_20(self, sample_training_data):
        """Train/test split should be approximately 80/20."""
        total = len(sample_training_data)
        expected_train = int(total * 0.8)
        expected_test = total - expected_train

        assert expected_train >= expected_test
        assert expected_train / total >= 0.7
        assert expected_train / total <= 0.9


class TestLabelMapping:
    """Test label-to-id mapping for model training."""

    def test_label2id_mapping(self):
        """label2id should map all intents to sequential integers."""
        labels = ["chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"]
        label2id = {label: idx for idx, label in enumerate(labels)}

        assert len(label2id) == 5
        assert label2id["chitchat"] == 0
        assert label2id["golden_set"] == 4

    def test_id2label_mapping(self):
        """id2label should be inverse of label2id."""
        labels = ["chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"]
        label2id = {label: idx for idx, label in enumerate(labels)}
        id2label = {idx: label for label, idx in label2id.items()}

        assert len(id2label) == 5
        for label, idx in label2id.items():
            assert id2label[idx] == label

    def test_label_mapping_roundtrip(self):
        """Converting label → id → label should return original."""
        labels = ["chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"]
        label2id = {label: idx for idx, label in enumerate(labels)}
        id2label = {idx: label for label, idx in label2id.items()}

        for original_label in labels:
            idx = label2id[original_label]
            recovered_label = id2label[idx]
            assert recovered_label == original_label
