#!/usr/bin/env python3
"""
Helper script to analyze parsed syllabi results.
"""

import json
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any


def load_syllabi(json_file: str) -> List[Dict[str, Any]]:
    """Load parsed syllabi from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_summary(syllabi: List[Dict[str, Any]]):
    """Print summary statistics about the syllabi collection."""

    print("=" * 70)
    print("SYLLABI COLLECTION SUMMARY")
    print("=" * 70)

    total = len(syllabi)
    print(f"\nTotal Syllabi: {total}")

    # AI-related statistics
    ai_related = [s for s in syllabi if s['is_ai_related']]
    non_ai = [s for s in syllabi if not s['is_ai_related']]

    print(f"\nAI-Related Courses: {len(ai_related)} ({len(ai_related)/total*100:.1f}%)")
    print(f"Non-AI Courses: {len(non_ai)} ({len(non_ai)/total*100:.1f}%)")

    # Semester distribution
    semesters = []
    years = []
    for s in syllabi:
        if s.get('term_offered'):
            if s['term_offered'].get('semester'):
                semesters.append(s['term_offered']['semester'])
            if s['term_offered'].get('academic_year'):
                years.append(s['term_offered']['academic_year'])

    if semesters:
        print("\nSemester Distribution:")
        semester_counts = Counter(semesters)
        for semester, count in semester_counts.most_common():
            print(f"  {semester.capitalize()}: {count}")

    if years:
        print("\nAcademic Year Distribution:")
        year_counts = Counter(years)
        for year, count in sorted(year_counts.items()):
            print(f"  {year}: {count}")

    print("\n" + "=" * 70)


def print_ai_courses(syllabi: List[Dict[str, Any]]):
    """Print details of AI-related courses."""

    ai_related = [s for s in syllabi if s['is_ai_related']]

    if not ai_related:
        print("\nNo AI-related courses found.")
        return

    print("\n" + "=" * 70)
    print("AI-RELATED COURSES")
    print("=" * 70)

    for idx, syllabus in enumerate(ai_related, 1):
        print(f"\n{idx}. {syllabus['course_name']}")
        print(f"   File: {syllabus['original_file_name']}")

        if syllabus.get('term_offered'):
            term = syllabus['term_offered']
            semester = term.get('semester', 'Unknown').capitalize()
            year = term.get('academic_year', 'Unknown')
            print(f"   Term: {semester} {year}")

        if syllabus.get('ai_related_justification'):
            print(f"   Justification: {syllabus['ai_related_justification']}")

    print("\n" + "=" * 70)


def search_courses(syllabi: List[Dict[str, Any]], keyword: str):
    """Search for courses by keyword in name or description."""

    keyword_lower = keyword.lower()
    matches = []

    for s in syllabi:
        if (keyword_lower in s['course_name'].lower() or
            keyword_lower in s['description'].lower()):
            matches.append(s)

    print(f"\nFound {len(matches)} courses matching '{keyword}':")
    print("=" * 70)

    for idx, syllabus in enumerate(matches, 1):
        print(f"\n{idx}. {syllabus['course_name']}")
        print(f"   File: {syllabus['original_file_name']}")
        print(f"   AI-Related: {'Yes' if syllabus['is_ai_related'] else 'No'}")
        print(f"   Description: {syllabus['description'][:200]}...")

    print("\n" + "=" * 70)


def export_ai_courses(syllabi: List[Dict[str, Any]], output_file: str):
    """Export only AI-related courses to a separate JSON file."""

    ai_related = [s for s in syllabi if s['is_ai_related']]

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ai_related, f, indent=2, ensure_ascii=False)

    print(f"\nExported {len(ai_related)} AI-related courses to {output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze parsed syllabi results"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="parsed_syllabi.json",
        help="Input JSON file with parsed syllabi (default: parsed_syllabi.json)"
    )
    parser.add_argument(
        "--show-ai",
        action="store_true",
        help="Show detailed list of AI-related courses"
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search for courses by keyword"
    )
    parser.add_argument(
        "--export-ai",
        type=str,
        help="Export AI-related courses to a separate JSON file"
    )

    args = parser.parse_args()

    # Check if input file exists
    if not Path(args.input_file).exists():
        print(f"Error: Input file '{args.input_file}' not found")
        print("\nRun parse_syllabi.py first to generate the JSON file:")
        print("  uv run python parse_syllabi.py")
        return

    # Load syllabi
    syllabi = load_syllabi(args.input_file)

    # Always show summary
    print_summary(syllabi)

    # Show AI courses if requested
    if args.show_ai:
        print_ai_courses(syllabi)

    # Search if requested
    if args.search:
        search_courses(syllabi, args.search)

    # Export AI courses if requested
    if args.export_ai:
        export_ai_courses(syllabi, args.export_ai)


if __name__ == "__main__":
    main()
