"""Compare the existing rule-based detector with an NLP detection-only model."""

import argparse
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import sklearn
from sklearn.model_selection import StratifiedKFold

from engines.detection_engine import DetectionEngine
from engines.nlp_classifier import (
    BENIGN_LABEL,
    INJECTION_LABEL,
    PromptInjectionClassifier,
)


DEFAULT_DATASET = (
    Path(__file__).parent.parent / "datasets" / "prompt_injection.jsonl"
)
EXPERIMENTS = ("baseline", "detection_only")


@dataclass(frozen=True)
class Sample:
    sample_id: str
    text: str
    label: str


def load_dataset(path: Path) -> List[Sample]:
    """Load and validate the JSONL samples used by both experiment arms."""
    samples: List[Sample] = []
    seen_ids = set()
    with path.open(encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: each row must be a JSON object")

            sample_id = row.get("id")
            text = row.get("text")
            label = row.get("label")
            if not isinstance(sample_id, str) or not sample_id.strip():
                raise ValueError(f"{path}:{line_number}: id must be a non-empty string")
            if sample_id in seen_ids:
                raise ValueError(f"{path}:{line_number}: duplicate id {sample_id!r}")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{path}:{line_number}: text must be a non-empty string")
            if not isinstance(label, str) or label not in {BENIGN_LABEL, INJECTION_LABEL}:
                raise ValueError(f"{path}:{line_number}: unsupported label {label!r}")

            expected_action = row.get("expected_action")
            expected_label = "flag" if label == INJECTION_LABEL else "allow"
            if expected_action is not None and expected_action != expected_label:
                raise ValueError(
                    f"{path}:{line_number}: expected_action conflicts with label"
                )
            samples.append(Sample(sample_id, text, label))
            seen_ids.add(sample_id)

    if not samples:
        raise ValueError(f"{path}: dataset has no samples")
    return samples


def load_outcomes(path: Optional[Path], samples: Sequence[Sample]) -> Dict[str, Dict[str, bool]]:
    """Load optional human-adjudicated end-to-end outcomes by sample and arm."""
    if path is None:
        return {}

    known_ids = {sample.sample_id: sample.label for sample in samples}
    outcomes: Dict[str, Dict[str, bool]] = {}
    with path.open(encoding="utf-8") as outcomes_file:
        for line_number, line in enumerate(outcomes_file, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: each row must be a JSON object")

            sample_id = row.get("id")
            experiment = row.get("experiment")
            succeeded = row.get("injection_succeeded")
            if not isinstance(sample_id, str) or sample_id not in known_ids:
                raise ValueError(f"{path}:{line_number}: unknown sample id {sample_id!r}")
            if known_ids[sample_id] != INJECTION_LABEL:
                raise ValueError(
                    f"{path}:{line_number}: outcomes are only valid for injection samples"
                )
            if experiment not in EXPERIMENTS:
                raise ValueError(f"{path}:{line_number}: unsupported experiment {experiment!r}")
            if not isinstance(succeeded, bool):
                raise ValueError(
                    f"{path}:{line_number}: injection_succeeded must be a boolean"
                )
            experiment_outcomes = outcomes.setdefault(sample_id, {})
            if experiment in experiment_outcomes:
                raise ValueError(
                    f"{path}:{line_number}: duplicate outcome for {sample_id!r}/{experiment}"
                )
            experiment_outcomes[experiment] = succeeded
    return outcomes


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _metrics(
    samples: Sequence[Sample],
    predictions: Sequence[str],
    latencies_ms: Sequence[float],
    fit_latencies_ms: Sequence[float],
    outcomes: Dict[str, Dict[str, bool]],
    experiment: str,
) -> Dict[str, object]:
    actual = [sample.label for sample in samples]
    true_positive = sum(
        expected == INJECTION_LABEL and predicted == INJECTION_LABEL
        for expected, predicted in zip(actual, predictions)
    )
    false_positive = sum(
        expected == BENIGN_LABEL and predicted == INJECTION_LABEL
        for expected, predicted in zip(actual, predictions)
    )
    false_negative = sum(
        expected == INJECTION_LABEL and predicted == BENIGN_LABEL
        for expected, predicted in zip(actual, predictions)
    )
    true_negative = sum(
        expected == BENIGN_LABEL and predicted == BENIGN_LABEL
        for expected, predicted in zip(actual, predictions)
    )

    positives = true_positive + false_negative
    negatives = true_negative + false_positive
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / positives if positives else 0.0
    injection_outcomes = [
        sample_outcomes[experiment]
        for sample_outcomes in outcomes.values()
        if experiment in sample_outcomes
    ]

    return {
        "accuracy": round((true_positive + true_negative) / len(actual), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "fpr": round(false_positive / negatives, 4) if negatives else 0.0,
        "injection_pass_through_rate": round(false_negative / positives, 4) if positives else 0.0,
        "injection_success_rate": round(sum(injection_outcomes) / len(injection_outcomes), 4)
        if injection_outcomes
        else None,
        "injection_success_samples": len(injection_outcomes),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies_ms), 4) if latencies_ms else 0.0,
            "p50": round(_percentile(latencies_ms, 0.50), 4),
            "p95": round(_percentile(latencies_ms, 0.95), 4),
        },
        "fit_latency_ms_mean": round(statistics.fmean(fit_latencies_ms), 4)
        if fit_latencies_ms
        else 0.0,
        "samples": len(actual),
        "confusion_matrix": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_negative": true_negative,
        },
    }


def run_experiments(
    samples: Sequence[Sample],
    folds: int = 5,
    seed: int = 42,
    outcomes: Optional[Dict[str, Dict[str, bool]]] = None,
) -> Dict[str, object]:
    """Run stratified cross-validation for baseline and detection-only arms."""
    if folds < 2:
        raise ValueError("folds must be at least 2")
    class_counts = {
        label: sum(sample.label == label for sample in samples)
        for label in (BENIGN_LABEL, INJECTION_LABEL)
    }
    if min(class_counts.values()) < folds:
        raise ValueError("each label must have at least as many samples as folds")

    actual_labels = [sample.label for sample in samples]
    texts = [sample.text for sample in samples]
    baseline_predictions: List[Optional[str]] = [None] * len(samples)
    classifier_predictions: List[Optional[str]] = [None] * len(samples)
    baseline_latencies: List[float] = []
    classifier_latencies: List[float] = []
    fit_latencies: List[float] = []

    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for train_indices, test_indices in splitter.split(texts, actual_labels):
        classifier = PromptInjectionClassifier(random_state=seed)
        fit_start = time.perf_counter_ns()
        classifier.fit(
            [texts[index] for index in train_indices],
            [actual_labels[index] for index in train_indices],
        )
        fit_latencies.append((time.perf_counter_ns() - fit_start) / 1_000_000)
        baseline = DetectionEngine()

        for index in test_indices:
            start = time.perf_counter_ns()
            result = baseline.analyze(texts[index], conversation_history=[])
            baseline_latencies.append((time.perf_counter_ns() - start) / 1_000_000)
            baseline_predictions[index] = (
                INJECTION_LABEL if result.is_suspicious else BENIGN_LABEL
            )

            start = time.perf_counter_ns()
            predicted_label, _ = classifier.predict(texts[index])
            classifier_latencies.append((time.perf_counter_ns() - start) / 1_000_000)
            classifier_predictions[index] = predicted_label

    if any(prediction is None for prediction in baseline_predictions + classifier_predictions):
        raise RuntimeError("cross-validation did not generate exactly one prediction per sample")

    baseline_predictions_complete = [
        prediction for prediction in baseline_predictions if prediction is not None
    ]
    classifier_predictions_complete = [
        prediction for prediction in classifier_predictions if prediction is not None
    ]
    validated_outcomes = outcomes or {}
    baseline = _metrics(
        samples,
        baseline_predictions_complete,
        baseline_latencies,
        [],
        validated_outcomes,
        "baseline",
    )
    detection_only = _metrics(
        samples,
        classifier_predictions_complete,
        classifier_latencies,
        fit_latencies,
        validated_outcomes,
        "detection_only",
    )
    return {
        "protocol": "stratified cross-validation",
        "folds": folds,
        "seed": seed,
        "dataset_samples": len(samples),
        "class_counts": class_counts,
        "evaluation_scope": (
            "Single-turn synthetic text samples with empty conversation history; "
            "no LLM calls or defense actions."
        ),
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
        },
        "baseline_definition": "Existing DetectionEngine rule and heuristic detector; no mitigation.",
        "detection_only_definition": "TF-IDF word unigram/bigram logistic-regression classifier; no mitigation.",
        "injection_success_definition": (
            "Observed end-to-end success requires human-adjudicated outcomes. "
            "Without outcome annotations, injection_success_rate is null; "
            "injection_pass_through_rate is only the detector false-negative rate."
        ),
        "metrics": {
            "baseline": baseline,
            "detection_only": detection_only,
        },
    }


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--outcomes",
        type=Path,
        help="Optional JSONL with human-adjudicated end-to-end injection outcomes.",
    )
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        samples = load_dataset(args.dataset)
        outcomes = load_outcomes(args.outcomes, samples)
        report = run_experiments(samples, args.folds, args.seed, outcomes)
        report["dataset_sha256"] = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
        serialized = json.dumps(report, indent=2)
        if args.output:
            args.output.write_text(serialized + "\n", encoding="utf-8")
        else:
            print(serialized)
    except (OSError, ValueError) as exc:
        print(f"Experiment failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
