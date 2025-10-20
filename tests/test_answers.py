import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AnswerInput, Patient, Question, QuestionSet
from app.token_utils import TokenTracker, calculate_cost, count_tokens

client = TestClient(app)

# Global token tracker
token_tracker = TokenTracker()


def print_test_header(test_name, description=""):
    """Print formatted test header."""
    print(f"\n{'═' * 80}")
    print(f"🧪 TEST: {test_name}")
    if description:
        print(f"📝 {description}")
    print(f"{'═' * 80}\n")


def print_answers(
    result, request_data=None, show_reasoning=True, show_per_question_tokens=True
):
    """Print formatted answers with token tracking."""
    print(f"{'─' * 80}")
    print(f"📊 Generated {len(result['answers'])} answers")
    print(f"{'─' * 80}\n")

    question_tokens_list = []

    for i, answer in enumerate(result["answers"], 1):
        question = answer["question"]
        confidence = answer["confidence"]

        # Emoji based on confidence
        if confidence >= 0.7:
            conf_emoji = "🟢"
        elif confidence >= 0.4:
            conf_emoji = "🟡"
        else:
            conf_emoji = "🔴"

        print(f"{i}. [{question['type'].upper()}] {question['content']}")
        print(f"   🔑 Key: {question['key']}")
        print(f"   💬 Answer: {answer['value']}")
        print(f"   {conf_emoji} Confidence: {confidence:.2%}")

        if show_reasoning:
            reasoning = answer["reasoning"]
            # Highlight actor-critic
            if "[Refined via Actor-Critic]" in reasoning:
                print("   🎭 [ACTOR-CRITIC REFINED]")
                reasoning = reasoning.replace("[Refined via Actor-Critic]", "").strip()
            print(f"   🧠 Reasoning: {reasoning}")

        # Calculate tokens for this question-answer pair
        if show_per_question_tokens and request_data:
            q_input_tokens = count_tokens({"question": question})
            q_output_tokens = count_tokens({"answer": answer})
            question_tokens_list.append(q_input_tokens + q_output_tokens)
            print(f"   📥 Input: ~{q_input_tokens:,} tokens")
            print(f"   📤 Output: ~{q_output_tokens:,} tokens")

        print()

    # Calculate and display token usage if request_data provided
    if request_data:
        input_tokens = count_tokens(request_data)
        output_tokens = count_tokens(result)
        cost = calculate_cost(input_tokens, output_tokens)
        token_tracker.add_usage(input_tokens, output_tokens)

        # Print stats for this test
        print(f"{'─' * 80}")
        print("📊 Total Test Token Usage:")
        print(f"   📥 Input:  {input_tokens:,} tokens (patient data + all questions)")
        print(f"   📤 Output: {output_tokens:,} tokens (all answers + reasoning)")
        print(f"   🔢 Total:  {input_tokens + output_tokens:,} tokens")
        print(f"   💰 Cost:   ${cost:.4f}")

        if question_tokens_list:
            avg_tokens = sum(question_tokens_list) / len(question_tokens_list)
            print("\n   Per Question Stats:")
            print(f"   • Avg tokens/question: ~{avg_tokens:.0f}")
            print(f"   • Min tokens: ~{min(question_tokens_list):,}")
            print(f"   • Max tokens: ~{max(question_tokens_list):,}")

        print(f"{'─' * 80}\n")

    return question_tokens_list if show_per_question_tokens else []


# Fixtures
@pytest.fixture
def detailed_patient_data():
    """Load detailed patient data from sample files."""
    with open("sample_data/patient_data.json") as f:
        patients_data = json.load(f)

    with open("sample_data/zepbound_question_set.json") as f:
        questions_data = json.load(f)

    patient = Patient(**patients_data[0])
    questions = [Question(**q) for q in questions_data]
    question_set = QuestionSet(name="Zepbound Prior Authorization", questions=questions)

    return AnswerInput(patient=patient, question_set=question_set)


@pytest.fixture
def simple_patient_data():
    """Simple patient with basic information."""
    return AnswerInput(
        patient=Patient(
            first_name="John",
            last_name="Doe",
            date_of_birth="1970-01-01",
            gender="Male",
            prescription={
                "medication": "Zepbound",
                "dosage": "5 mg",
                "frequency": "once weekly",
                "duration": "ongoing",
            },
            visit_notes=["Patient has BMI of 35 kg/m².", "Weight: 240 lbs."],
        ),
        question_set=QuestionSet(
            name="Simple Test",
            questions=[
                Question(type="text", key="bmi", content="What is the patient's BMI?"),
                Question(
                    type="text",
                    key="weight",
                    content="What is the patient's current weight?",
                ),
            ],
        ),
    )


@pytest.fixture
def actor_critic_data():
    """Load actor-critic demo data."""
    with open("sample_data/actor_critic_example.json") as f:
        data = json.load(f)
    return AnswerInput(**data)


# Test Cases
def test_detailed_patient(detailed_patient_data):
    """Test with comprehensive patient data and full question set."""
    print_test_header(
        "Detailed Patient Test",
        "Full patient record with complete Zepbound prior auth questions",
    )

    request_data = detailed_patient_data.model_dump()
    response = client.post("/answers", json=request_data)

    if response.status_code != 200:
        print(f"\n❌ Error response: {response.json()}")

    assert response.status_code == 200
    result = response.json()
    assert "answers" in result
    assert len(result["answers"]) > 0

    print_answers(result, request_data=request_data, show_reasoning=True)

    # Check for high confidence answers
    high_conf_count = sum(1 for a in result["answers"] if a["confidence"] >= 0.7)
    print(f"✅ High confidence answers: {high_conf_count}/{len(result['answers'])}")


def test_simple_explicit_info(simple_patient_data):
    """Test with simple, explicit patient information."""
    print_test_header(
        "Simple Explicit Information Test",
        "Clear, straightforward patient data - should have high confidence",
    )

    request_data = simple_patient_data.model_dump()
    response = client.post("/answers", json=request_data)

    assert response.status_code == 200
    result = response.json()

    print_answers(result, request_data=request_data, show_reasoning=True)

    # Should have high confidence since info is explicit
    for answer in result["answers"]:
        assert answer["confidence"] > 0.5, (
            f"Expected higher confidence for explicit info, got {answer['confidence']}"
        )


def test_actor_critic_refinement(actor_critic_data):
    """Test Actor-Critic system with ambiguous patient data."""
    print_test_header(
        "Actor-Critic Refinement Test",
        "Ambiguous patient data that triggers automatic answer refinement",
    )

    request_data = actor_critic_data.model_dump()
    response = client.post("/answers", json=request_data)

    assert response.status_code == 200
    result = response.json()

    print_answers(result, request_data=request_data, show_reasoning=True)

    # Check if any answers were refined
    refined_count = sum(
        1 for a in result["answers"] if "[Refined via Actor-Critic]" in a["reasoning"]
    )

    print(f"🎭 Actor-Critic refinements: {refined_count}/{len(result['answers'])}")

    if refined_count > 0:
        print("✅ Actor-Critic system activated as expected!")
    else:
        print("ℹ️  No refinements triggered (confidence was already high)")


def test_missing_information():
    """Test handling of missing patient information."""
    print_test_header(
        "Missing Information Test",
        "Questions about data not available in patient record",
    )

    data = AnswerInput(
        patient=Patient(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1985-03-15",
            gender="Female",
            prescription={
                "medication": "Zepbound",
                "dosage": "5 mg",
                "frequency": "once weekly",
                "duration": "ongoing",
            },
            visit_notes=["Initial consultation for weight management."],
        ),
        question_set=QuestionSet(
            name="Missing Data Test",
            questions=[
                Question(type="text", key="bmi", content="What is the patient's BMI?"),
                Question(
                    type="boolean",
                    key="tried_exercise",
                    content="Has the patient tried a structured exercise program?",
                ),
            ],
        ),
    )

    request_data = data.model_dump()
    response = client.post("/answers", json=request_data)

    assert response.status_code == 200
    result = response.json()

    print_answers(result, request_data=request_data, show_reasoning=True)

    # Should have low confidence or explicit "not available" answers
    low_conf_count = sum(1 for a in result["answers"] if a["confidence"] < 0.3)
    print(
        f"🔴 Low confidence answers (as expected): {low_conf_count}/{len(result['answers'])}"
    )


def test_boolean_questions():
    """Test various boolean question types."""
    print_test_header(
        "Boolean Questions Test",
        "Testing yes/no questions with clear and ambiguous data",
    )

    data = AnswerInput(
        patient=Patient(
            first_name="Bob",
            last_name="Wilson",
            date_of_birth="1975-06-20",
            gender="Male",
            prescription={
                "medication": "Zepbound",
                "dosage": "5 mg",
                "frequency": "once weekly",
                "duration": "ongoing",
            },
            visit_notes=[
                "Patient has tried multiple diets over the past year.",
                "Patient has type 2 diabetes, well-controlled.",
                "No history of cardiovascular disease.",
            ],
        ),
        question_set=QuestionSet(
            name="Boolean Test",
            questions=[
                Question(
                    type="boolean",
                    key="tried_lifestyle",
                    content="Has the patient tried lifestyle modifications?",
                ),
                Question(
                    type="boolean",
                    key="has_diabetes",
                    content="Does the patient have diabetes?",
                ),
                Question(
                    type="boolean",
                    key="has_cvd",
                    content="Does the patient have cardiovascular disease?",
                ),
            ],
        ),
    )

    request_data = data.model_dump()
    response = client.post("/answers", json=request_data)

    assert response.status_code == 200
    result = response.json()

    print_answers(result, request_data=request_data, show_reasoning=True)

    # Should have mix of True/False answers
    true_count = sum(1 for a in result["answers"] if a["value"] is True)
    false_count = sum(1 for a in result["answers"] if a["value"] is False)
    print(f"✅ True: {true_count}, ❌ False: {false_count}")


def test_health_endpoint():
    """Test health check endpoint."""
    print_test_header("Health Check Test", "Verify API is running")

    response = client.get("/health")
    assert response.status_code == 200

    result = response.json()
    print(f"✅ Status: {result['status']}")
    print(f"📝 Message: {result['message']}")


# Run all tests with summary
def test_summary(detailed_patient_data, simple_patient_data, actor_critic_data):
    """Print final test summary with cumulative token stats."""
    print(f"\n{'═' * 80}")
    print("🎉 ALL TESTS COMPLETED!")
    print(f"{'═' * 80}\n")
    print("✅ Tests run:")
    print("   1. Detailed Patient (full question set)")
    print("   2. Simple Explicit Info (high confidence)")
    print("   3. Actor-Critic Refinement (ambiguous data)")
    print("   4. Missing Information (low confidence)")
    print("   5. Boolean Questions (mixed answers)")
    print("   6. Health Check")

    # Print cumulative token statistics
    token_tracker.print_summary()

    print(f"\n{'═' * 80}\n")


@pytest.fixture(scope="session", autouse=True)
def flush_logfire_on_exit():
    """Ensure Logfire logs are flushed after all tests complete."""
    yield
    # This runs after all tests
    import logfire

    logfire.force_flush()
