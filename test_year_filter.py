"""
Test script to verify year extraction and filtering functionality.
"""

from parse_syllabi import extract_year_from_path


def test_year_extraction():
    """Test the year extraction function with various path patterns."""

    test_cases = [
        # (file_path, filename, expected_year)
        ("data/Spring 2024/course.pdf.txt", "course.pdf", 2024),
        ("data/Fall2023/folder/file.pdf.txt", "file.pdf", 2023),
        ("data/2022_Spring/course.docx.txt", "course.docx", 2022),
        ("data/courses/2025/file.pdf.txt", "file.pdf", 2025),
        ("data/HLC SBS Syllabi/GLS SBS HRTS Victoria Souksavath/Spring 2022/SBS 411_Ariel Torres_7WK2_2221.pdf.txt",
         "SBS 411_Ariel Torres_7WK2_2221.pdf", 2022),
        ("data/HLC SBS Syllabi/ARB MENA PRS TURK/Spring 2024/course.pdf.txt",
         "course.pdf", 2024),
        ("data/HLC SBS Syllabi/ENGL Sharonne Meyerson/ENGL Fall 2022 Syllabi/course.pdf.txt",
         "course.pdf", 2022),
        ("data/courses/no_year_here/file.pdf.txt", "file_no_year.pdf", None),
        ("data/2024/2023/file.pdf.txt", "file.pdf", 2024),  # Should pick the most recent
    ]

    print("Testing Year Extraction Function")
    print("=" * 70)

    passed = 0
    failed = 0

    for file_path, filename, expected in test_cases:
        result = extract_year_from_path(file_path, filename)

        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} Test:")
        print(f"   Path: {file_path}")
        print(f"   File: {filename}")
        print(f"   Expected: {expected}")
        print(f"   Got: {result}")

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")

    return failed == 0


def demonstrate_filtering():
    """Demonstrate how the year filtering works."""

    print("\n" + "=" * 70)
    print("Year Filtering Demonstration (min_year=2024)")
    print("=" * 70)

    test_files = [
        ("Spring 2024/course1.pdf.txt", "course1.pdf"),
        ("Fall 2023/course2.pdf.txt", "course2.pdf"),
        ("Spring 2022/course3.pdf.txt", "course3.pdf"),
        ("2025/course4.pdf.txt", "course4.pdf"),
        ("unknown/course5.pdf.txt", "course5.pdf"),
    ]

    min_year = 2024

    for file_path, filename in test_files:
        year = extract_year_from_path(file_path, filename)

        print(f"\nFile: {file_path}")
        print(f"  Detected year: {year}")

        if year is None:
            print(f"  Action: Process (cannot determine year)")
        elif year >= min_year:
            print(f"  Action: ✓ Process (year {year} >= {min_year})")
        else:
            print(f"  Action: ⊙ Skip (year {year} < {min_year})")


if __name__ == "__main__":
    print("Testing Year Filtering Functionality\n")

    success = test_year_extraction()

    if success:
        print("\n✓ All year extraction tests passed!")
        demonstrate_filtering()

        print("\n" + "=" * 70)
        print("Year filtering is working correctly!")
        print("=" * 70)
        print("\nUsage:")
        print("  # Process only 2024+ syllabi (default)")
        print("  uv run python parse_syllabi.py")
        print()
        print("  # Process syllabi from 2022 onwards")
        print("  uv run python parse_syllabi.py --min-year 2022")
        print()
        print("  # Process all syllabi (no year filter)")
        print("  uv run python parse_syllabi.py --min-year 2000")
    else:
        print("\n✗ Some tests failed!")
