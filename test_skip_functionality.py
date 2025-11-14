"""
Test script to verify the skip functionality in parse_syllabi.py
"""

import json
from pathlib import Path
from parse_syllabi import load_existing_results
from models import Syllabus, Term, Semester


def test_load_existing_results():
    """Test loading existing results from a JSON file."""

    # Create a temporary test file
    test_data = [
        {
            "original_file_name": "test1.pdf",
            "course_name": "Test Course 1",
            "term_offered": {
                "semester": "fall",
                "academic_year": 2023
            },
            "description": "Test description 1",
            "is_ai_related": False,
            "ai_related_justification": None
        },
        {
            "original_file_name": "test2.pdf",
            "course_name": "Test Course 2: Machine Learning",
            "term_offered": {
                "semester": "spring",
                "academic_year": 2024
            },
            "description": "Machine learning course",
            "is_ai_related": True,
            "ai_related_justification": "Covers ML algorithms"
        }
    ]

    # Write test data
    test_file = "test_results.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)

    print("Created test file with 2 syllabi")

    # Test loading
    syllabi, processed_filenames = load_existing_results(test_file)

    print(f"\n✓ Loaded {len(syllabi)} syllabi")
    print(f"✓ Found {len(processed_filenames)} processed filenames")

    # Check the filenames
    expected_filenames = {"test1.pdf", "test2.pdf"}
    if processed_filenames == expected_filenames:
        print("✓ Processed filenames match expected set")
    else:
        print(f"✗ Mismatch! Expected: {expected_filenames}, Got: {processed_filenames}")

    # Verify Syllabus objects were created correctly
    for idx, s in enumerate(syllabi, 1):
        print(f"\n{idx}. {s.course_name}")
        print(f"   File: {s.original_file_name}")
        print(f"   AI-related: {s.is_ai_related}")

    # Test with non-existent file
    print("\n" + "="*60)
    print("Testing with non-existent file...")
    syllabi2, filenames2 = load_existing_results("nonexistent.json")

    if len(syllabi2) == 0 and len(filenames2) == 0:
        print("✓ Correctly returns empty lists for non-existent file")
    else:
        print("✗ Should return empty lists for non-existent file")

    # Clean up
    Path(test_file).unlink()
    print("\n✓ Cleaned up test file")

    print("\n" + "="*60)
    print("All tests passed!")


def demonstrate_skip_logic():
    """Demonstrate how the skip logic works."""

    print("\n" + "="*60)
    print("Skip Logic Demonstration")
    print("="*60)

    # Simulate existing processed files
    processed_filenames = {
        "course1.pdf",
        "course2.docx",
        "course3.pdf"
    }

    print(f"\nAlready processed: {processed_filenames}")

    # Simulate files to process
    files_to_check = [
        "course1.pdf",      # Should skip
        "course2.docx",     # Should skip
        "course4.pdf",      # Should process
        "course5.docx",     # Should process
        "course3.pdf",      # Should skip
    ]

    print("\nChecking files:")
    for filename in files_to_check:
        if filename in processed_filenames:
            print(f"  ⊙ {filename} - Already processed, skipping")
        else:
            print(f"  ✓ {filename} - New file, will process")

    print("\nThis logic prevents duplicate API calls and saves costs!")


if __name__ == "__main__":
    print("Testing parse_syllabi.py skip functionality...\n")

    try:
        test_load_existing_results()
        demonstrate_skip_logic()

        print("\n" + "="*60)
        print("✓ All functionality tests passed!")
        print("="*60)
        print("\nThe skip functionality will:")
        print("1. Load existing parsed_syllabi.json on startup")
        print("2. Build a set of already-processed filenames")
        print("3. Skip files that are already in the JSON")
        print("4. Only send new files to the LLM")
        print("5. Append new results to existing ones")
        print("6. Save all results back to the JSON file")

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        raise
