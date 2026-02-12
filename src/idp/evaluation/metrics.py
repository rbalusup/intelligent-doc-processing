"""Evaluation metrics for document processing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MetricResult:
    """Result of computing a metric."""

    name: str
    value: float
    details: dict[str, Any]


class Metric(ABC):
    """Abstract base class for evaluation metrics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Metric name."""
        ...

    @abstractmethod
    def compute(
        self,
        predictions: list[Any],
        ground_truth: list[Any],
    ) -> MetricResult:
        """Compute the metric.

        Args:
            predictions: Predicted values
            ground_truth: Ground truth values

        Returns:
            Metric result
        """
        ...


class AccuracyMetric(Metric):
    """Classification accuracy metric."""

    @property
    def name(self) -> str:
        return "accuracy"

    def compute(
        self,
        predictions: list[Any],
        ground_truth: list[Any],
    ) -> MetricResult:
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")

        if not predictions:
            return MetricResult(name=self.name, value=0.0, details={})

        correct = sum(1 for p, g in zip(predictions, ground_truth, strict=True) if p == g)
        total = len(predictions)
        accuracy = correct / total

        return MetricResult(
            name=self.name,
            value=accuracy,
            details={
                "correct": correct,
                "total": total,
            },
        )


class F1Metric(Metric):
    """Field-level F1 score metric."""

    @property
    def name(self) -> str:
        return "f1"

    def compute(
        self,
        predictions: list[dict[str, Any]],
        ground_truth: list[dict[str, Any]],
    ) -> MetricResult:
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")

        if not predictions:
            return MetricResult(name=self.name, value=0.0, details={})

        total_precision = 0.0
        total_recall = 0.0
        count = 0

        for pred, truth in zip(predictions, ground_truth, strict=True):
            if not truth:
                continue

            pred_keys = {k for k, v in pred.items() if v is not None}
            truth_keys = set(truth.keys())

            # Precision: how many predicted fields are correct
            if pred_keys:
                correct_pred = sum(
                    1 for k in pred_keys
                    if k in truth and pred.get(k) == truth.get(k)
                )
                precision = correct_pred / len(pred_keys)
            else:
                precision = 0.0

            # Recall: how many truth fields were found
            if truth_keys:
                found = sum(
                    1 for k in truth_keys
                    if k in pred and pred.get(k) == truth.get(k)
                )
                recall = found / len(truth_keys)
            else:
                recall = 1.0

            total_precision += precision
            total_recall += recall
            count += 1

        if count == 0:
            return MetricResult(name=self.name, value=0.0, details={})

        avg_precision = total_precision / count
        avg_recall = total_recall / count

        if avg_precision + avg_recall > 0:
            f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall)
        else:
            f1 = 0.0

        return MetricResult(
            name=self.name,
            value=f1,
            details={
                "precision": avg_precision,
                "recall": avg_recall,
            },
        )


class LatencyMetric(Metric):
    """Latency metric (average, p50, p95, p99)."""

    @property
    def name(self) -> str:
        return "latency"

    def compute(
        self,
        predictions: list[float],  # latencies in ms
        ground_truth: list[Any],  # noqa: ARG002 - required by interface
    ) -> MetricResult:
        if not predictions:
            return MetricResult(name=self.name, value=0.0, details={})

        sorted_latencies = sorted(predictions)
        n = len(sorted_latencies)

        avg = sum(sorted_latencies) / n
        p50 = sorted_latencies[int(n * 0.5)]
        p95 = sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1]
        p99 = sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]

        return MetricResult(
            name=self.name,
            value=avg,
            details={
                "average_ms": avg,
                "p50_ms": p50,
                "p95_ms": p95,
                "p99_ms": p99,
                "min_ms": sorted_latencies[0],
                "max_ms": sorted_latencies[-1],
            },
        )
