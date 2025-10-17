from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI

from app.env import get_openrouter_api_key, get_openrouter_model, setup_env

from .models import (
    Answer,
    AnswerInput,
    AnswerOutput,
    BooleanAnswerResponse,
    TextAnswerResponse,
)

setup_env()


# Initialize the FastAPI application
app = FastAPI(
    title="Pharmacy Prior Authorization API",
    description="API for generating answers to prior authorization questions using patient data",
    version="1.0.0",
)

# Initialize OpenRouter client (OpenAI-compatible)
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Pharmacy Prior Authorization API is running",
        "status": "healthy",
    }


def build_patient_context(patient) -> str:
    """Build a comprehensive patient context string for the LLM."""
    context = f"""Patient Information:
- Name: {patient.first_name} {patient.last_name}
- Date of Birth: {patient.date_of_birth}
- Gender: {patient.gender}

Current Prescription:
- Medication: {patient.prescription.medication}
- Dosage: {patient.prescription.dosage}
- Frequency: {patient.prescription.frequency}
- Duration: {patient.prescription.duration}

Visit Notes:
"""
    for i, note in enumerate(patient.visit_notes, 1):
        context += f"{i}. {note}\n"

    return context


async def answer_question(patient_context: str, question) -> tuple[str | bool, float, str]:
    """
    Use LLM with Pydantic structured outputs to answer a single question based on patient context.

    Args:
        patient_context: Formatted string with patient information
        question: Question object with type, key, and content

    Returns:
        Tuple of (answer_value, confidence, reasoning)
    """
    model = get_openrouter_model()

    # Determine the appropriate response model based on question type
    if question.type == "boolean":
        system_prompt = """You are a medical assistant helping to complete prior authorization forms.
Answer the question based on the provided patient information.
Provide a true or false answer with confidence score and reasoning."""

        user_prompt = f"""{patient_context}

Question: {question.content}

Based on the patient information above, determine if the answer is true or false.
Provide your confidence level and explain your reasoning."""

        response_model = BooleanAnswerResponse

    else:
        # Text question
        system_prompt = """You are a medical assistant helping to complete prior authorization forms.
Answer the question based on the provided patient information.
Be concise and specific. Provide confidence score and reasoning."""

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

        return parsed_response.answer, parsed_response.confidence, parsed_response.reasoning

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating answer for question '{question.key}': {str(e)}",
        )


@app.post("/answers")
async def get_answers(data: AnswerInput) -> AnswerOutput:
    """
    Generate answers to prior authorization questions based on patient data.

    This endpoint accepts patient information and a list of questions,
    then uses LLM to generate appropriate answers based on the patient's
    medical history, current medications, and other relevant data.
    """
    # Validate API key is set
    if not get_openrouter_api_key():
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not configured. Please set it in your .env file.",
        )

    # Build patient context once
    patient_context = build_patient_context(data.patient)

    # Generate answers for each question
    answers = []
    for question in data.question_set.questions:
        # TODO: Handle visible_if conditions in future iteration
        answer_value, confidence, reasoning = await answer_question(
            patient_context, question
        )
        answers.append(
            Answer(
                question=question,
                value=answer_value,
                confidence=confidence,
                reasoning=reasoning,
            )
        )

    return AnswerOutput(answers=answers)
