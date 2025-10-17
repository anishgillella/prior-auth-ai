from typing import Literal

from pydantic import BaseModel, Field


class Question(BaseModel):
    type: Literal["text", "boolean"]
    key: str
    content: str
    visible_if: str | None = None


class QuestionSet(BaseModel):
    name: str
    questions: list[Question]


class Answer(BaseModel):
    question: Question
    value: str | bool
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0 and 1"
    )
    reasoning: str = Field(
        description="Brief explanation of how the answer was derived from patient data"
    )


class Prescription(BaseModel):
    medication: str
    dosage: str
    frequency: str
    duration: str


class Patient(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    prescription: Prescription
    visit_notes: list[str]


class AnswerInput(BaseModel):
    patient: Patient
    question_set: QuestionSet


class AnswerOutput(BaseModel):
    answers: list[Answer]


# Pydantic models for LLM structured outputs
class TextAnswerResponse(BaseModel):
    """Structured response for text-based questions with confidence and reasoning."""

    answer: str = Field(
        description="A concise, specific answer to the question based on patient information. If information is not available, state 'Information not available in patient records'."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1. Use 1.0 for explicit information, 0.7-0.9 for inferred information, 0.3-0.6 for uncertain, and 0.0-0.2 when information is not available.",
    )
    reasoning: str = Field(
        description="Brief explanation (1-2 sentences) of how the answer was derived from the patient data, citing specific information from visit notes or patient details."
    )


class BooleanAnswerResponse(BaseModel):
    """Structured response for boolean questions with confidence and reasoning."""

    answer: bool = Field(
        description="True or False answer to the question based on patient information."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1. Use 1.0 for explicit statements, 0.7-0.9 for strong inference, 0.5-0.6 for weak inference.",
    )
    reasoning: str = Field(
        description="Brief explanation of the evidence in patient data that supports this true/false answer."
    )


# Annotation models for clinical staff review
class Annotation(BaseModel):
    """Clinical staff annotation for a generated answer."""

    id: str = Field(description="Unique annotation ID")
    timestamp: str = Field(description="ISO format timestamp")
    reviewer_id: str = Field(description="ID of clinical staff reviewer")
    patient_name: str = Field(description="Patient name for reference")
    question_key: str = Field(description="Question key")
    question_content: str = Field(description="Question text")
    original_answer: str | bool = Field(description="AI-generated answer")
    original_confidence: float = Field(description="Original confidence score")
    original_reasoning: str = Field(description="Original reasoning")
    status: Literal["approved", "rejected", "corrected"] = Field(
        description="Review status"
    )
    corrected_answer: str | bool | None = Field(
        None, description="Corrected answer if status is 'corrected'"
    )
    notes: str = Field(description="Reviewer notes and feedback")


class AnnotationInput(BaseModel):
    """Input for creating an annotation."""

    reviewer_id: str
    patient_name: str
    question_key: str
    question_content: str
    original_answer: str | bool
    original_confidence: float
    original_reasoning: str
    status: Literal["approved", "rejected", "corrected"]
    corrected_answer: str | bool | None = None
    notes: str


class AnnotationList(BaseModel):
    """List of annotations."""

    annotations: list[Annotation]
    total: int
