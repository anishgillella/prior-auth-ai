"""
Evaluation pipeline for assessing answer quality.

This module provides automated evaluation of the /answers endpoint
to measure accuracy, confidence calibration, and reasoning quality.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.models import AnswerInput, Patient, Question, QuestionSet

client = TestClient(app)


class EvaluationMetrics:
    """Container for evaluation metrics."""

    def __init__(self):
        self.total_cases = 0
        self.passed_cases = 0
        self.failed_cases = 0
        self.confidence_scores = []
        self.failures = []

    def add_result(self, case_name: str, passed: bool, confidence: float, details: str = ""):
        """Add a test case result."""
        self.total_cases += 1
        self.confidence_scores.append(confidence)

        if passed:
            self.passed_cases += 1
        else:
            self.failed_cases += 1
            self.failures.append({
                "case": case_name,
                "confidence": confidence,
                "details": details
            })

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        return {
            "total_cases": self.total_cases,
            "passed": self.passed_cases,
            "failed": self.failed_cases,
            "pass_rate": self.passed_cases / self.total_cases if self.total_cases > 0 else 0,
            "average_confidence": sum(self.confidence_scores) / len(self.confidence_scores) if self.confidence_scores else 0,
            "min_confidence": min(self.confidence_scores) if self.confidence_scores else 0,
            "max_confidence": max(self.confidence_scores) if self.confidence_scores else 0,
        }


def load_test_cases() -> list[dict]:
    """Load evaluation test cases from JSON file."""
    fixtures_path = Path(__file__).parent / "fixtures" / "eval_test_cases.json"
    with open(fixtures_path) as f:
        return json.load(f)


def evaluate_answer(answer: dict, expected: dict, case_name: str) -> tuple[bool, str]:
    """
    Evaluate a single answer against expected criteria.

    Args:
        answer: The actual answer from the API
        expected: Expected answer criteria
        case_name: Name of test case for logging

    Returns:
        Tuple of (passed, details)
    """
    details = []
    passed = True

    # Check answer content
    if "answer_contains" in expected:
        expected_text = expected["answer_contains"].lower()
        actual_answer = str(answer["value"]).lower()

        if expected_text not in actual_answer:
            passed = False
            details.append(f"Answer should contain '{expected['answer_contains']}' but got '{answer['value']}'")

    # Check exact boolean answer
    if "answer" in expected:
        if answer["value"] != expected["answer"]:
            passed = False
            details.append(f"Expected {expected['answer']} but got {answer['value']}")

    # Check minimum confidence
    if "min_confidence" in expected:
        if answer["confidence"] < expected["min_confidence"]:
            passed = False
            details.append(f"Confidence {answer['confidence']:.2f} below minimum {expected['min_confidence']}")

    # Check maximum confidence (for uncertain cases)
    if "max_confidence" in expected:
        if answer["confidence"] > expected["max_confidence"]:
            passed = False
            details.append(f"Confidence {answer['confidence']:.2f} above maximum {expected['max_confidence']}")

    # Check reasoning is provided
    if expected.get("must_cite_source", False):
        if not answer.get("reasoning") or len(answer["reasoning"]) < 10:
            passed = False
            details.append("Reasoning is missing or too short")

    return passed, "; ".join(details) if details else "All checks passed"


def run_evaluation() -> EvaluationMetrics:
    """
    Run the full evaluation pipeline.

    Returns:
        EvaluationMetrics with results
    """
    print("=" * 80)
    print("Starting Evaluation Pipeline")
    print("=" * 80)
    print()

    test_cases = load_test_cases()
    metrics = EvaluationMetrics()

    for i, test_case in enumerate(test_cases, 1):
        case_name = test_case["name"]
        print(f"[{i}/{len(test_cases)}] Running: {case_name}")

        # Prepare request
        patient = Patient(**test_case["patient"])
        question = Question(**test_case["question"])
        question_set = QuestionSet(name="Evaluation", questions=[question])
        request_data = AnswerInput(patient=patient, question_set=question_set)

        # Call API
        response = client.post("/answers", json=request_data.model_dump())

        if response.status_code != 200:
            print(f"  ❌ API Error: {response.json()}")
            metrics.add_result(case_name, False, 0.0, "API call failed")
            continue

        # Get answer
        result = response.json()
        answer = result["answers"][0]

        # Evaluate
        passed, details = evaluate_answer(answer, test_case["expected"], case_name)

        # Record result
        metrics.add_result(case_name, passed, answer["confidence"], details)

        # Print result
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}")
        print(f"  Answer: {answer['value']}")
        print(f"  Confidence: {answer['confidence']:.2f}")

        if not passed:
            print(f"  Details: {details}")

        print()

    return metrics


def print_summary(metrics: EvaluationMetrics):
    """Print evaluation summary."""
    summary = metrics.get_summary()

    print("=" * 80)
    print("Evaluation Summary")
    print("=" * 80)
    print()
    print(f"Total Test Cases:     {summary['total_cases']}")
    print(f"Passed:               {summary['passed']} ({summary['pass_rate']:.1%})")
    print(f"Failed:               {summary['failed']}")
    print()
    print("Confidence Scores:")
    print(f"  Average:            {summary['average_confidence']:.2f}")
    print(f"  Min:                {summary['min_confidence']:.2f}")
    print(f"  Max:                {summary['max_confidence']:.2f}")
    print()

    if metrics.failures:
        print("Failed Cases:")
        for failure in metrics.failures:
            print(f"  • {failure['case']}")
            print(f"    Confidence: {failure['confidence']:.2f}")
            print(f"    {failure['details']}")
        print()

    # Overall grade
    if summary['pass_rate'] >= 0.9:
        grade = "🎉 EXCELLENT"
    elif summary['pass_rate'] >= 0.75:
        grade = "✅ GOOD"
    elif summary['pass_rate'] >= 0.5:
        grade = "⚠️  NEEDS IMPROVEMENT"
    else:
        grade = "❌ POOR"

    print(f"Overall Grade: {grade}")
    print("=" * 80)


if __name__ == "__main__":
    metrics = run_evaluation()
    print_summary(metrics)

