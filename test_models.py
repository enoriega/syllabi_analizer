"""
Test script to demonstrate the Syllabus Pydantic model usage.
"""

from models import Syllabus, Term, Semester
import json


def test_syllabus_model():
    """Demonstrate creating and validating Syllabus instances."""

    # Example 1: AI-related course
    ai_course = Syllabus(
        original_file_name="CS229_Machine_Learning_Fall_2023.pdf",
        course_name="CS 229: Machine Learning",
        term_offered=Term(
            semester=Semester.FALL,
            academic_year=2023
        ),
        description="This course provides a broad introduction to machine learning and statistical pattern recognition. Topics include supervised learning, unsupervised learning, deep learning, and reinforcement learning.",
        is_ai_related=True,
        ai_related_justification="This course directly covers machine learning algorithms and techniques, which are core components of artificial intelligence. The curriculum includes neural networks, deep learning, and other AI methodologies."
    )

    print("Example 1: AI-Related Course")
    print("=" * 60)
    print(ai_course.model_dump_json(indent=2))
    print("\n")

    # Example 2: Non-AI course
    non_ai_course = Syllabus(
        original_file_name="ENGL101_Writing_Spring_2022.docx",
        course_name="ENGL 101: Introduction to Writing",
        term_offered=Term(
            semester=Semester.SPRING,
            academic_year=2022
        ),
        description="An introduction to academic writing focusing on critical reading, argumentation, and research skills. Students will develop their ability to construct well-organized essays.",
        is_ai_related=False,
        ai_related_justification=None
    )

    print("Example 2: Non-AI Course")
    print("=" * 60)
    print(non_ai_course.model_dump_json(indent=2))
    print("\n")

    # Example 3: Course with incomplete term information
    partial_course = Syllabus(
        original_file_name="MATH201_Calculus.pdf",
        course_name="MATH 201: Calculus II",
        term_offered=Term(
            semester=None,
            academic_year=2023
        ),
        description="Continuation of calculus including integration techniques, sequences, series, and applications.",
        is_ai_related=False,
        ai_related_justification=None
    )

    print("Example 3: Partial Term Information")
    print("=" * 60)
    print(partial_course.model_dump_json(indent=2))
    print("\n")

    # Example 4: Course with no term information
    no_term_course = Syllabus(
        original_file_name="CS544_NLP_Unknown.pdf",
        course_name="CS 544: Natural Language Processing",
        term_offered=None,
        description="Introduction to computational linguistics and natural language processing. Topics include text processing, language models, parsing, machine translation, and sentiment analysis.",
        is_ai_related=True,
        ai_related_justification="Natural Language Processing is a subfield of AI that deals with the interaction between computers and human language. This course covers AI techniques like language models, neural networks for text processing, and machine learning for NLP tasks."
    )

    print("Example 4: No Term Information")
    print("=" * 60)
    print(no_term_course.model_dump_json(indent=2))
    print("\n")

    # Demonstrate validation
    print("Validation Example")
    print("=" * 60)
    try:
        # This should work
        valid = Syllabus(
            original_file_name="test.pdf",
            course_name="Test Course",
            description="Test description",
            is_ai_related=False
        )
        print("✓ Valid syllabus created successfully")
    except Exception as e:
        print(f"✗ Validation error: {e}")

    # Demonstrate field validation
    print("\nField Validation Example")
    print("=" * 60)
    try:
        # This should fail due to invalid year
        invalid_year = Syllabus(
            original_file_name="test.pdf",
            course_name="Test Course",
            term_offered=Term(semester=Semester.FALL, academic_year=2500),
            description="Test",
            is_ai_related=False
        )
    except Exception as e:
        print(f"✓ Caught validation error for invalid year: {type(e).__name__}")
        print(f"  Message: {e}")


if __name__ == "__main__":
    test_syllabus_model()
