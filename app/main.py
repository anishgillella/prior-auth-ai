from pathlib import Path

import logfire
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

from app.env import get_openrouter_api_key, get_openrouter_model, setup_env
from app.examples import format_few_shot_examples

from .models import (
    Answer,
    AnswerInput,
    AnswerOutput,
    BooleanAnswerResponse,
    TextAnswerResponse,
)

setup_env()

# Configure Logfire for observability
logfire.configure()
logfire.instrument_openai(AsyncOpenAI)

# Initialize the FastAPI application
app = FastAPI(
    title="Pharmacy Prior Authorization API",
    description="API for generating answers to prior authorization questions using patient data",
    version="1.0.0",
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with Logfire
logfire.instrument_fastapi(app)

# Get project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Mount static files for frontend
app.mount(
    "/sample_data",
    StaticFiles(directory=str(BASE_DIR / "sample_data")),
    name="sample_data",
)

# Initialize OpenRouter client (OpenAI-compatible)
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)


@app.get("/")
async def root():
    """Serve the frontend UI."""
    frontend_path = BASE_DIR / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {
        "message": "Pharmacy Prior Authorization API is running",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
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


async def answer_question(
    patient_context: str, question
) -> tuple[str | bool, float, str]:
    """
    Use LLM with Pydantic structured outputs to answer a single question based on patient context.
    Uses few-shot prompting to improve answer quality.

    Args:
        patient_context: Formatted string with patient information
        question: Question object with type, key, and content

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

            # Log answer metrics to Logfire
            logfire.info(
                "answer_generated",
                question_key=question.key,
                answer_type=type(parsed_response.answer).__name__,
                confidence=parsed_response.confidence,
                has_reasoning=bool(parsed_response.reasoning),
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
            raise HTTPException(
                status_code=500,
                detail=f"Error generating answer for question '{question.key}': {str(e)}",
            ) from e


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

    # Track the entire request with Logfire
    with logfire.span(
        "generate_all_answers",
        patient_name=f"{data.patient.first_name} {data.patient.last_name}",
        question_count=len(data.question_set.questions),
        medication=data.patient.prescription.medication,
    ):
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

        # Log summary statistics
        avg_confidence = sum(a.confidence for a in answers) / len(answers)
        logfire.info(
            "answers_complete",
            total_questions=len(answers),
            average_confidence=avg_confidence,
            question_set_name=data.question_set.name,
        )

        return AnswerOutput(answers=answers)
