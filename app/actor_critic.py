"""
Actor-Critic System for Answer Refinement.

This module implements an actor-critic pattern where:
- Actor: Generates initial answers based on patient data
- Critic: Evaluates answers and identifies issues
- Actor (refined): Regenerates improved answers based on criticism

The system is automatically invoked for low-confidence answers (< 0.7).
"""

import logfire
from openai import AsyncOpenAI

from app.env import get_openrouter_model

from .models import BooleanAnswerResponse, Question, TextAnswerResponse


async def critique_answer(
    openrouter_client: AsyncOpenAI,
    patient_context: str,
    question: Question,
    answer: str | bool,
    confidence: float,
    reasoning: str,
) -> str:
    """
    Critic: Evaluates an answer and provides constructive feedback for improvement.

    This is part of the Actor-Critic system where the critic identifies
    issues with the initial answer to help the actor generate a better response.

    Args:
        openrouter_client: OpenAI client configured for OpenRouter
        patient_context: Full patient information
        question: The question being answered
        answer: The generated answer
        confidence: Confidence score of the answer
        reasoning: Reasoning provided for the answer

    Returns:
        Criticism with specific suggestions for improvement
    """
    with logfire.span(
        "critique_answer", question_key=question.key, initial_confidence=confidence
    ):
        critique_prompt = f"""You are a medical expert critic reviewing an AI-generated answer for a prior authorization form.

Patient Information:
{patient_context}

Question: {question.content}
Generated Answer: {answer}
Confidence: {confidence:.2f}
Reasoning: {reasoning}

Your task is to critique this answer and provide specific, actionable feedback:
1. What information is missing or unclear in the answer?
2. What assumptions were made that might be incorrect?
3. What additional patient data would strengthen this answer?
4. How could the reasoning be more precise or cite specific evidence?

The confidence is {confidence:.2f}, indicating some uncertainty. Identify why the confidence is low and what could make it higher.

Provide constructive criticism in 2-3 sentences. Be specific and actionable."""

        try:
            response = await openrouter_client.chat.completions.create(
                model=get_openrouter_model(),
                messages=[{"role": "user", "content": critique_prompt}],
                max_tokens=300,
                temperature=0.3,
            )

            criticism = (
                response.choices[0].message.content or "No specific issues identified."
            )

            logfire.info(
                "criticism_generated",
                question_key=question.key,
                criticism_length=len(criticism),
            )

            return criticism

        except Exception as e:
            logfire.error("critique_failed", error=str(e))
            return "Unable to generate criticism."


async def refine_answer_with_critic(
    openrouter_client: AsyncOpenAI,
    patient_context: str,
    question: Question,
    initial_answer: str | bool,
    initial_confidence: float,
    initial_reasoning: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[TextAnswerResponse | BooleanAnswerResponse],
) -> tuple[str | bool, float, str]:
    """
    Refine an answer using the actor-critic system.

    Args:
        openrouter_client: OpenAI client
        patient_context: Patient information
        question: Question being answered
        initial_answer: Initial answer from actor
        initial_confidence: Initial confidence score
        initial_reasoning: Initial reasoning
        system_prompt: System prompt for the actor
        user_prompt: User prompt for the actor
        response_model: Pydantic model for structured output

    Returns:
        Tuple of (refined_answer, refined_confidence, refined_reasoning)
    """
    logfire.info(
        "invoking_actor_critic",
        question_key=question.key,
        initial_confidence=initial_confidence,
    )

    # Get criticism from the critic
    criticism = await critique_answer(
        openrouter_client,
        patient_context,
        question,
        initial_answer,
        initial_confidence,
        initial_reasoning,
    )

    # Actor refines answer based on criticism
    refined_prompt = f"""{user_prompt}

Previous attempt:
Answer: {initial_answer}
Confidence: {initial_confidence:.2f}
Reasoning: {initial_reasoning}

Critic's feedback:
{criticism}

Based on the critic's feedback, provide an improved answer that addresses the identified issues.
Review the patient information again carefully and provide a more confident, well-supported answer."""

    # Generate refined answer
    refined_completion = await openrouter_client.beta.chat.completions.parse(
        model=get_openrouter_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": refined_prompt},
        ],
        response_format=response_model,
        temperature=0.3,
        max_tokens=500,
    )

    refined_response = refined_completion.choices[0].message.parsed

    # Log refinement results
    confidence_improvement = refined_response.confidence - initial_confidence
    logfire.info(
        "answer_refined",
        question_key=question.key,
        initial_confidence=initial_confidence,
        refined_confidence=refined_response.confidence,
        improvement=confidence_improvement,
    )

    return (
        refined_response.answer,
        refined_response.confidence,
        f"[Refined via Actor-Critic] {refined_response.reasoning}",
    )
