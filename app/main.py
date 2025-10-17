"""
FastAPI application for Prior Authorization Answer Generation.

This API provides endpoints for:
- Generating answers to prior authorization questions using LLMs
- Clinical staff annotation and review of generated answers
"""

from pathlib import Path

import logfire
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

from app.annotations import create_annotation, get_annotations
from app.answer_service import answer_question, build_patient_context
from app.env import get_openrouter_api_key, setup_env

from .models import (
    Annotation,
    AnnotationInput,
    AnnotationList,
    Answer,
    AnswerInput,
    AnswerOutput,
)

setup_env()

# Configure Logfire for observability
logfire.configure()

# Initialize FastAPI app
app = FastAPI(
    title="Pharmacy Prior Authorization API",
    description="API for generating answers to prior authorization questions using patient data",
    version="1.0.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with Logfire
logfire.instrument_fastapi(app)

# Mount static files
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount(
    "/sample_data",
    StaticFiles(directory=str(BASE_DIR / "sample_data")),
    name="sample_data",
)

# Initialize OpenRouter client
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

# Instrument OpenAI client with Logfire
logfire.instrument_openai(AsyncOpenAI)


@app.get("/")
async def root():
    """Serve the main frontend application."""
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


@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon to avoid 404."""
    return {}


@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon():
    """Return empty response for apple touch icons to avoid 404."""
    return {}


@app.post("/answers")
async def get_answers(data: AnswerInput) -> AnswerOutput:
    """
    Generate answers to prior authorization questions using patient data.

    This endpoint:
    1. Extracts patient information and questions from the request
    2. Uses LLM with few-shot prompting to generate answers
    3. Applies actor-critic refinement for low-confidence answers
    4. Returns structured answers with confidence scores and reasoning

    Args:
        data: Patient information and question set

    Returns:
        AnswerOutput with list of answers including confidence and reasoning
    """
    if not get_openrouter_api_key():
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not configured. Please set it in your .env file.",
        )

    with logfire.span(
        "generate_all_answers",
        patient_name=f"{data.patient.first_name} {data.patient.last_name}",
        question_count=len(data.question_set.questions),
        medication=data.patient.prescription.medication,
    ):
        # Build patient context once for all questions
        patient_context = build_patient_context(data.patient)

        # Generate answers for each question
        answers = []
        for question in data.question_set.questions:
            answer_value, confidence, reasoning = await answer_question(
                openrouter_client, patient_context, question, use_actor_critic=True
            )
            answers.append(
                Answer(
                    question=question,
                    value=answer_value,
                    confidence=confidence,
                    reasoning=reasoning,
                )
            )

        # Log completion metrics
        avg_confidence = sum(a.confidence for a in answers) / len(answers)
        logfire.info(
            "answers_complete",
            total_questions=len(answers),
            average_confidence=avg_confidence,
            question_set_name=data.question_set.name,
        )

        return AnswerOutput(answers=answers)


@app.post("/annotations", response_model=Annotation)
async def create_annotation_endpoint(annotation_input: AnnotationInput) -> Annotation:
    """
    Create a new annotation for clinical staff review.

    This endpoint allows clinical staff to review AI-generated answers and provide feedback:
    - **Approve**: Answer is correct
    - **Reject**: Answer is incorrect
    - **Correct**: Answer needs modification (provide corrected answer)

    Args:
        annotation_input: Annotation data from clinical staff

    Returns:
        Created annotation with unique ID and timestamp
    """
    return create_annotation(annotation_input)


@app.get("/annotations", response_model=AnnotationList)
async def get_annotations_endpoint(
    reviewer_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> AnnotationList:
    """
    Retrieve annotations with optional filtering.

    Query parameters:
    - **reviewer_id**: Filter by reviewer
    - **status**: Filter by status (approved/rejected/corrected)
    - **limit**: Maximum number of annotations to return (default: 100)

    Returns:
        List of annotations matching the filters
    """
    annotations, total = get_annotations(reviewer_id, status, limit)
    return AnnotationList(annotations=annotations, total=total)


@app.get("/annotate")
async def annotation_ui():
    """Serve the annotation UI for clinical staff."""
    ui_path = BASE_DIR / "frontend" / "annotate.html"
    if ui_path.exists():
        return FileResponse(ui_path)
    return {"message": "Annotation UI not found"}
