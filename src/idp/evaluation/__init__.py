"""Evaluation framework for document processing."""

from idp.evaluation.framework import (
    EvaluationFramework,
    EvaluationReport,
    TestCase,
    TestResult,
)
from idp.evaluation.metrics import (
    AccuracyMetric,
    F1Metric,
    LatencyMetric,
    Metric,
)

__all__ = [
    "EvaluationFramework",
    "TestCase",
    "TestResult",
    "EvaluationReport",
    "Metric",
    "AccuracyMetric",
    "F1Metric",
    "LatencyMetric",
]
