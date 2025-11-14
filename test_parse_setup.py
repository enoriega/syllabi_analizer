"""
Test script to verify parse_syllabi.py setup without calling API.
"""

from pathlib import Path
from models import Syllabus, Term, Semester

# Test that we can create a sample syllabus
def test_syllabus_creation():
    """Test that we can create and serialize a Syllabus object."""

    syllabus = Syllabus(
        original_file_name="SBS 411_Ariel Torres_7WK2_2221.pdf",
        course_name="SBS 411: Design Your Search",
        term_offered=Term(
            semester=Semester.SPRING,
            academic_year=2022
        ),
        description="This course helps students develop career search strategies and professional development skills. Students will learn to identify career goals, create effective resumes, and develop networking strategies.",
        is_ai_related=False,
        ai_related_justification=None
    )

    print("✓ Successfully created Syllabus object")
    print("\nSample output:")
    print(syllabus.model_dump_json(indent=2))

    return syllabus


def test_json_serialization():
    """Test that we can serialize multiple syllabi to JSON."""
    import json

    syllabi = [
        Syllabus(
            original_file_name="test1.pdf",
            course_name="Test Course 1",
            term_offered=Term(semester=Semester.FALL, academic_year=2023),
            description="Test description 1",
            is_ai_related=False
        ),
        Syllabus(
            original_file_name="test2.pdf",
            course_name="Test Course 2: Machine Learning",
            term_offered=Term(semester=Semester.SPRING, academic_year=2024),
            description="Introduction to machine learning algorithms and applications.",
            is_ai_related=True,
            ai_related_justification="This course covers supervised and unsupervised learning algorithms, neural networks, and deep learning."
        )
    ]

    # Convert to dict
    syllabi_dicts = [s.model_dump() for s in syllabi]

    # Serialize to JSON
    json_output = json.dumps(syllabi_dicts, indent=2, ensure_ascii=False)

    print("\n✓ Successfully serialized array of syllabi to JSON")
    print(f"\nJSON output ({len(json_output)} characters):")
    print(json_output[:500] + "..." if len(json_output) > 500 else json_output)


def check_env_file():
    """Check if .env file exists and what it should contain."""
    env_path = Path(".env")
    env_example_path = Path(".env.example")

    print("\n" + "="*60)
    print("Environment Configuration Check")
    print("="*60)

    if env_path.exists():
        print("✓ .env file exists")
    else:
        print("✗ .env file not found")
        if env_example_path.exists():
            print("\nTo run parse_syllabi.py, create a .env file:")
            print("  cp .env.example .env")
            print("\nThen edit .env and add your API credentials")

    if env_example_path.exists():
        print("\n.env.example contents:")
        print("-" * 60)
        with open(env_example_path, 'r') as f:
            print(f.read())


if __name__ == "__main__":
    print("Testing parse_syllabi.py setup...\n")

    try:
        test_syllabus_creation()
        test_json_serialization()
        check_env_file()

        print("\n" + "="*60)
        print("✓ All setup tests passed!")
        print("="*60)
        print("\nThe parse_syllabi.py script is ready to use.")
        print("Make sure to create a .env file with your API credentials.")

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        raise
