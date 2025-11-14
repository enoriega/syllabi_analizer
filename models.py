"""
Pydantic models for representing syllabi data.
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class Semester(str, Enum):
    """Enumeration of academic semesters."""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


class Term(BaseModel):
    """Represents an academic term with semester and year."""

    semester: Optional[Semester] = Field(
        None,
        description="The semester when the course is offered (spring, summer, fall, winter)"
    )

    academic_year: Optional[int] = Field(
        None,
        description="The academic year (e.g., 2022, 2023)",
        ge=1900,
        le=2100
    )

    class Config:
        use_enum_values = True


class Syllabus(BaseModel):
    """
    Structured representation of a course syllabus.

    This model captures key information from academic syllabi including
    course details, scheduling, and AI-relevance classification.
    """

    original_file_name: str = Field(
        ...,
        description="The original filename of the syllabus document"
    )

    course_name: str = Field(
        ...,
        description="The name/title of the course"
    )

    term_offered: Optional[Term] = Field(
        None,
        description="The academic term when the course is offered"
    )

    description: str = Field(
        ...,
        description="Course description including objectives and learning outcomes"
    )

    is_ai_related: bool = Field(
        ...,
        description="Whether this course is related to artificial intelligence"
    )

    ai_related_justification: Optional[str] = Field(
        None,
        description="Explanation of why this course is AI-related (required if is_ai_related is True)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_file_name": "CS229_Machine_Learning_Fall_2023.pdf",
                "course_name": "CS 229: Machine Learning",
                "term_offered": {
                    "semester": "fall",
                    "academic_year": 2023
                },
                "description": "This course provides a broad introduction to machine learning and statistical pattern recognition. Topics include supervised learning, unsupervised learning, deep learning, and reinforcement learning.",
                "is_ai_related": True,
                "ai_related_justification": "This course directly covers machine learning algorithms and techniques, which are core components of artificial intelligence. The curriculum includes neural networks, deep learning, and other AI methodologies."
            }
        }
