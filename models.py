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


class CourseType(str, Enum):
    """Enumeration of course classification types."""
    CORE_AI = "core_ai"
    APPLIED_AI = "applied_ai"
    CORE_DATA_SCIENCE = "core_data_science"
    APPLIED_DATA_SCIENCE = "applied_data_science"
    OTHER = "other"


class ClassifiedCourse(BaseModel):
    """
    Represents a classified course with all its information and classification.
    """

    course_id: str = Field(
        ...,
        description="The unique course ID from the CSV"
    )

    subject_codes: str = Field(
        ...,
        description="Subject code(s) for the course"
    )

    offering_unit: str = Field(
        ...,
        description="The unit offering the course"
    )

    course_title: str = Field(
        ...,
        description="The title of the course"
    )

    max_units: str = Field(
        ...,
        description="Maximum units for the course"
    )

    course_url: str = Field(
        ...,
        description="URL to the course catalog page"
    )

    is_graduate: str = Field(
        ...,
        description="Whether the course is graduate level"
    )

    catalog_description: Optional[str] = Field(
        None,
        description="Course description fetched from the catalog URL"
    )

    syllabus_description: Optional[str] = Field(
        None,
        description="Course description from the matched syllabus"
    )

    course_type: CourseType = Field(
        ...,
        description="The classification of the course"
    )

    classification_justification: str = Field(
        ...,
        description="Plain English justification for the classification decision"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "course_id": "9850",
                "subject_codes": "CSC 477",
                "offering_unit": "Computer Science",
                "course_title": "Introduction to Computer Vision",
                "max_units": "3",
                "course_url": "https://catalog.arizona.edu/courses/0098501",
                "is_graduate": "No",
                "catalog_description": "Introduction to computer vision...",
                "syllabus_description": "This course covers...",
                "course_type": "core_ai",
                "classification_justification": "This is a core AI course because..."
            }
        }
