"""
Answer Generation Service.

This module handles the core logic of generating answers to prior authorization
questions using LLMs with few-shot prompting and optional actor-critic refinement.
"""

import logfire
from openai import AsyncOpenAI

from app.actor_critic import refine_answer_with_critic
from app.env import get_openrouter_model
from app.examples import format_few_shot_examples

from .models import BooleanAnswerResponse, Question, TextAnswerResponse


def build_patient_context(patient) -> str:
    """
    Build a comprehensive patient context string for the LLM.

    Args:
        patient: Patient object with demographics and medical history

    Returns:
        Formatted string with patient information
    """
    context = f"""Patient Information:
- Name: {patient.first_name} {patient.last_name}
- Date of Birth: {patient.date_of_birth}
- Gender: {patient.gender}

Prescription:
- Medication: {patient.prescription.medication}
- Dosage: {patient.prescription.dosage}
- Frequency: {patient.prescription.frequency}
- Duration: {patient.prescription.duration}

Visit Notes:
"""
    for i, note in enumerate(patient.visit_notes, 1):
        context += f"{i}. {note}\n"

    return context


async def answer_question(
    openrouter_client: AsyncOpenAI,
    patient_context: str,
    question: Question,
    use_actor_critic: bool = True,
) -> tuple[str | bool, float, str]:
    """
    Use LLM with Pydantic structured outputs to answer a single question based on patient context.
    Uses few-shot prompting to improve answer quality.

    Actor-Critic System (when use_actor_critic=True):
    - Actor generates initial answer with confidence score
    - If confidence < 0.7, Critic evaluates and identifies issues
    - Actor regenerates improved answer based on criticism
    - Results in higher quality answers for ambiguous cases

    Args:
        openrouter_client: OpenAI client configured for OpenRouter
        patient_context: Formatted string with patient information
        question: Question object with type, key, and content
        use_actor_critic: Enable actor-critic refinement for low-confidence answers

    Returns:
        Tuple of (answer_value, confidence, reasoning)
    """
    model = get_openrouter_model()

    # Start Logfire span for tracking
    with logfire.span(
        "answer_question",
        question_key=question.key,
        question_type=question.type,
        model=model,
    ):
        # Determine the appropriate response model based on question type
        if question.type == "boolean":
            # Get few-shot examples for boolean questions
            few_shot_examples = format_few_shot_examples("boolean")

            system_prompt = f"""You are a medical assistant helping to complete prior authorization forms.
Answer the question based on the provided patient information.
Provide a true or false answer with confidence score and reasoning.

{few_shot_examples}"""

            user_prompt = f"""{patient_context}

Question: {question.content}

Based on the patient information above, determine if the answer is true or false.
Provide your confidence level and explain your reasoning."""

            response_model = BooleanAnswerResponse

        else:
            # Text question - get few-shot examples
            few_shot_examples = format_few_shot_examples("text")

            system_prompt = f"""You are a medical assistant helping to complete prior authorization forms.
Answer the question based on the provided patient information.
Be concise and specific. Provide confidence score and reasoning.

{few_shot_examples}"""

            user_prompt = f"""{patient_context}

Question: {question.content}

Provide a concise, specific answer based on the patient information.
Include your confidence level and explain your reasoning."""

            response_model = TextAnswerResponse

        try:
            # Use OpenAI's structured output feature with Pydantic models
            # This ensures type-safe responses that always match our schema
            completion = await openrouter_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_model,
                temperature=0.3,  # Lower temperature for more consistent/factual responses
                max_tokens=500,  # Sufficient for gpt-4o-mini (no reasoning token overhead)
            )

            # Extract the parsed Pydantic model - already validated!
            parsed_response = completion.choices[0].message.parsed

            # Log initial answer metrics to Logfire
            logfire.info(
                "answer_generated",
                question_key=question.key,
                answer_type=type(parsed_response.answer).__name__,
                confidence=parsed_response.confidence,
                has_reasoning=bool(parsed_response.reasoning),
            )

            # Actor-Critic: If confidence is low (< 0.7) and actor-critic is enabled,
            # use critic to identify issues and refine the answer
            if use_actor_critic and parsed_response.confidence < 0.7:
                return await refine_answer_with_critic(
                    openrouter_client,
                    patient_context,
                    question,
                    parsed_response.answer,
                    parsed_response.confidence,
                    parsed_response.reasoning,
                    system_prompt,
                    user_prompt,
                    response_model,
                )

            return (
                parsed_response.answer,
                parsed_response.confidence,
                parsed_response.reasoning,
            )

        except Exception as e:
            logfire.error(
                "answer_generation_failed",
                question_key=question.key,
                error=str(e),
            )
            raise
