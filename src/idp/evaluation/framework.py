"""Evaluation framework for measuring system performance."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from idp.core.logging import get_logger
from idp.models.document import Document, DocumentType
from idp.orchestration import WorkflowEngine

logger = get_logger(__name__)


class TestCase(BaseModel):
    """A test case for evaluation."""

    id: str = Field(..., description="Unique test case ID")
    document: Document
    expected_type: DocumentType
    expected_fields: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    description: str = ""


class TestResult(BaseModel):
    """Result of running a single test case."""

    test_case_id: str
    passed: bool
    classification_correct: bool
    extraction_score: float = 0.0
    validation_passed: bool = True
    latency_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


@dataclass
class EvaluationReport:
    """Aggregated evaluation report."""

    total_tests: int
    passed_tests: int
    failed_tests: int
    classification_accuracy: float
    extraction_f1: float
    average_latency_ms: float
    results: list[TestResult]
    started_at: datetime
    completed_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "pass_rate": self.pass_rate,
            "classification_accuracy": self.classification_accuracy,
            "extraction_f1": self.extraction_f1,
            "average_latency_ms": self.average_latency_ms,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
        }


class EvaluationFramework:
    """Framework for evaluating document processing performance."""

    def __init__(self, engine: WorkflowEngine) -> None:
        """Initialize the evaluation framework.

        Args:
            engine: Workflow engine to evaluate
        """
        self._engine = engine

    def _calculate_field_score(
        self,
        expected: dict[str, Any],
        actual: dict[str, Any] | None,
    ) -> float:
        """Calculate field-level extraction score."""
        if not expected or actual is None:
            return 1.0 if not expected else 0.0

        matches = 0
        total = len(expected)

        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if actual_value == expected_value:
                matches += 1
            elif (
                isinstance(expected_value, str)
                and isinstance(actual_value, str)
                and expected_value.lower().strip() == actual_value.lower().strip()
            ):
                # Fuzzy string matching
                matches += 1

        return matches / total if total > 0 else 1.0

    async def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case.

        Args:
            test_case: Test case to run

        Returns:
            Test result
        """
        import time

        start_time = time.perf_counter()
        errors: list[str] = []

        try:
            result = await self._engine.process(test_case.document)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Check classification
            actual_type = result.state.context.get("document_type")
            classification_correct = actual_type == test_case.expected_type.value

            # Check extraction
            actual_data = result.state.context.get("extracted_data", {})
            extraction_score = self._calculate_field_score(
                test_case.expected_fields,
                actual_data,
            )

            # Check validation
            validation_passed = result.state.context.get("validation_valid", True)

            # Determine overall pass
            passed = classification_correct and extraction_score >= 0.8

            if not result.success:
                errors.append(f"Workflow failed: {result.error}")

            return TestResult(
                test_case_id=test_case.id,
                passed=passed,
                classification_correct=classification_correct,
                extraction_score=extraction_score,
                validation_passed=validation_passed,
                latency_ms=latency_ms,
                errors=errors,
                details={
                    "expected_type": test_case.expected_type.value,
                    "actual_type": actual_type,
                    "workflow_success": result.success,
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return TestResult(
                test_case_id=test_case.id,
                passed=False,
                classification_correct=False,
                extraction_score=0.0,
                validation_passed=False,
                latency_ms=latency_ms,
                errors=[str(e)],
            )

    async def run_evaluation(
        self,
        test_cases: list[TestCase],
    ) -> EvaluationReport:
        """Run evaluation on a set of test cases.

        Args:
            test_cases: Test cases to evaluate

        Returns:
            Evaluation report
        """
        started_at = datetime.utcnow()
        results: list[TestResult] = []

        logger.info("Starting evaluation", test_count=len(test_cases))

        for test_case in test_cases:
            logger.debug("Running test case", test_id=test_case.id)
            result = await self.run_test(test_case)
            results.append(result)

        completed_at = datetime.utcnow()

        # Calculate aggregate metrics
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        classification_correct = sum(1 for r in results if r.classification_correct)
        total_extraction_score = sum(r.extraction_score for r in results)
        total_latency = sum(r.latency_ms for r in results)

        report = EvaluationReport(
            total_tests=total,
            passed_tests=passed,
            failed_tests=total - passed,
            classification_accuracy=classification_correct / total if total > 0 else 0.0,
            extraction_f1=total_extraction_score / total if total > 0 else 0.0,
            average_latency_ms=total_latency / total if total > 0 else 0.0,
            results=results,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            "Evaluation completed",
            total=total,
            passed=passed,
            accuracy=report.classification_accuracy,
            f1=report.extraction_f1,
        )

        return report
