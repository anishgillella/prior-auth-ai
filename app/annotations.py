"""
Annotation System for Clinical Staff Review.

This module provides functionality for clinical staff to review and annotate
AI-generated answers. Supports approve/reject/correct workflows with feedback storage.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

import logfire

from .models import Annotation, AnnotationInput


def get_annotations_file() -> Path:
    """Get the path to the annotations JSON file."""
    return Path(__file__).parent.parent / "sample_data" / "annotations.json"


def load_annotations() -> list[Annotation]:
    """
    Load annotations from JSON file.

    Returns:
        List of Annotation objects
    """
    annotations_file = get_annotations_file()
    if not annotations_file.exists():
        return []
    try:
        with open(annotations_file) as f:
            data = json.load(f)
            return [Annotation(**ann) for ann in data]
    except Exception as e:
        logfire.error("failed_to_load_annotations", error=str(e))
        return []


def save_annotations(annotations: list[Annotation]):
    """
    Save annotations to JSON file.

    Args:
        annotations: List of Annotation objects to save
    """
    annotations_file = get_annotations_file()
    try:
        with open(annotations_file, "w") as f:
            json.dump([ann.model_dump() for ann in annotations], f, indent=2)
        logfire.info("annotations_saved", count=len(annotations))
    except Exception as e:
        logfire.error("failed_to_save_annotations", error=str(e))
        raise


def create_annotation(annotation_input: AnnotationInput) -> Annotation:
    """
    Create a new annotation from clinical staff review.

    Args:
        annotation_input: Annotation input data

    Returns:
        Created Annotation with unique ID and timestamp
    """
    # Load existing annotations
    annotations = load_annotations()

    # Create new annotation with unique ID and timestamp
    annotation = Annotation(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        **annotation_input.model_dump(),
    )

    # Add to list and save
    annotations.append(annotation)
    save_annotations(annotations)

    logfire.info(
        "annotation_created",
        annotation_id=annotation.id,
        reviewer_id=annotation.reviewer_id,
        status=annotation.status,
        question_key=annotation.question_key,
    )

    return annotation


def get_annotations(
    reviewer_id: str | None = None, status: str | None = None, limit: int = 100
) -> tuple[list[Annotation], int]:
    """
    Retrieve annotations with optional filtering.

    Args:
        reviewer_id: Filter by reviewer ID
        status: Filter by status (approved/rejected/corrected)
        limit: Maximum number of annotations to return

    Returns:
        Tuple of (filtered annotations list, total count)
    """
    annotations = load_annotations()

    # Apply filters
    if reviewer_id:
        annotations = [a for a in annotations if a.reviewer_id == reviewer_id]
    if status:
        annotations = [a for a in annotations if a.status == status]

    # Sort by timestamp (newest first)
    annotations.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply limit
    annotations = annotations[:limit]

    return annotations, len(annotations)


def get_annotation_stats() -> dict:
    """
    Get statistics about annotations for monitoring.

    Returns:
        Dictionary with annotation statistics
    """
    annotations = load_annotations()

    if not annotations:
        return {
            "total": 0,
            "approved": 0,
            "rejected": 0,
            "corrected": 0,
            "approval_rate": 0.0,
        }

    approved = sum(1 for a in annotations if a.status == "approved")
    rejected = sum(1 for a in annotations if a.status == "rejected")
    corrected = sum(1 for a in annotations if a.status == "corrected")

    return {
        "total": len(annotations),
        "approved": approved,
        "rejected": rejected,
        "corrected": corrected,
        "approval_rate": approved / len(annotations) if len(annotations) > 0 else 0.0,
    }
