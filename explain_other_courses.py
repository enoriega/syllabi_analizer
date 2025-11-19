#!/usr/bin/env python3
"""
Script to analyze "Other" courses using an LLM to explain why they were classified as "Other"
and identify common patterns or themes among them.
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()


def setup_llm() -> ChatOpenAI:
    """
    Setup the LLM using configuration from .env file.

    Returns:
        Configured ChatOpenAI instance
    """
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL_NAME")
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise ValueError("LLM_API_KEY not found in .env file")
    if not model_name:
        raise ValueError("LLM_MODEL_NAME not found in .env file")

    llm_kwargs = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0.3,  # Slightly creative for analysis
    }

    if base_url:
        llm_kwargs["base_url"] = base_url

    return ChatOpenAI(**llm_kwargs)


def load_courses(json_file: str) -> List[Dict[str, Any]]:
    """Load classified courses from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_other_courses(courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter courses classified as 'other'."""
    return [c for c in courses if c['course_type'] == 'other']


def analyze_other_courses_overview(llm: ChatOpenAI, other_courses: List[Dict[str, Any]]) -> str:
    """
    Use LLM to analyze the overall patterns in "Other" courses.

    Args:
        llm: Configured LLM instance
        other_courses: List of courses classified as "other"

    Returns:
        Analysis text
    """
    # Prepare course summaries
    course_summaries = []
    for i, course in enumerate(other_courses[:50], 1):  # Limit to first 50 for token limits
        summary = f"{i}. {course['subject_codes']} - {course['course_title']}\n"
        summary += f"   Offering Unit: {course['offering_unit']}\n"
        summary += f"   Justification: {course['classification_justification']}\n"
        course_summaries.append(summary)

    courses_text = "\n".join(course_summaries)

    if len(other_courses) > 50:
        courses_text += f"\n\n(Note: Showing first 50 of {len(other_courses)} total 'Other' courses)"

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert in academic curriculum analysis, specializing in AI and Data Science education.

Your task is to analyze courses that were classified as "Other" (meaning they don't fit into Core AI, Applied AI,
Core Data Science, or Applied Data Science categories).

Provide a comprehensive analysis that includes:
1. Common themes or patterns among these "Other" courses
2. Main reasons why they were classified as "Other"
3. Groupings or categories you can identify within the "Other" classification
4. Whether any courses might actually belong in an AI/DS category (and why)
5. The relationship (if any) these courses have to AI/Data Science

Be specific and cite examples from the course list."""),
        ("user", """Here are the courses classified as "Other":

{courses}

Please analyze these courses and provide your insights.""")
    ])

    chain = prompt | llm | StrOutputParser()

    print("Analyzing 'Other' courses with LLM...")
    result = chain.invoke({"courses": courses_text})

    return result


def analyze_by_offering_unit(llm: ChatOpenAI, other_courses: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Analyze "Other" courses grouped by offering unit.

    Args:
        llm: Configured LLM instance
        other_courses: List of courses classified as "other"

    Returns:
        Dictionary mapping offering units to analysis text
    """
    from collections import defaultdict

    by_unit = defaultdict(list)
    for course in other_courses:
        by_unit[course['offering_unit']].append(course)

    # Sort by count and take top units
    top_units = sorted(by_unit.items(), key=lambda x: len(x[1]), reverse=True)[:10]

    analyses = {}

    for unit, courses in top_units:
        print(f"Analyzing {len(courses)} 'Other' courses from {unit}...")

        course_summaries = []
        for i, course in enumerate(courses, 1):
            summary = f"{i}. {course['subject_codes']} - {course['course_title']}\n"
            summary += f"   Justification: {course['classification_justification']}\n"
            course_summaries.append(summary)

        courses_text = "\n".join(course_summaries)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in academic curriculum analysis. Analyze why these courses from a specific
offering unit were classified as "Other" (not Core AI, Applied AI, Core Data Science, or Applied Data Science).

Provide a concise analysis (2-3 paragraphs) that explains:
1. Why these courses don't fit into AI/Data Science categories
2. What these courses have in common
3. Whether any might have been misclassified"""),
            ("user", """Offering Unit: {unit}

Courses classified as "Other":

{courses}

Analyze these courses:""")
        ])

        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({"unit": unit, "courses": courses_text})
        analyses[unit] = result

    return analyses


def generate_markdown_report(output_file: str,
                            total_courses: int,
                            other_courses: List[Dict[str, Any]],
                            overview_analysis: str,
                            unit_analyses: Dict[str, str]):
    """Generate a markdown report of the analysis."""

    from datetime import datetime
    from collections import Counter

    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("# Analysis of 'Other' Courses\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Source**: classified_courses.json\n\n")
        f.write("---\n\n")

        # Statistics
        f.write("## Statistics\n\n")
        f.write(f"- **Total Courses in Dataset**: {total_courses}\n")
        f.write(f"- **Courses Classified as 'Other'**: {len(other_courses)}\n")
        pct = (len(other_courses) / total_courses * 100) if total_courses > 0 else 0
        f.write(f"- **Percentage**: {pct:.1f}%\n\n")

        # Level distribution
        grad_counts = Counter(c['is_graduate'] for c in other_courses)
        f.write("**Level Distribution:**\n\n")
        for level, count in sorted(grad_counts.items()):
            level_label = "Graduate" if level == "Yes" else "Undergraduate"
            level_pct = (count / len(other_courses) * 100) if len(other_courses) > 0 else 0
            f.write(f"- {level_label}: {count} ({level_pct:.1f}%)\n")
        f.write("\n")

        # Offering unit distribution
        unit_counts = Counter(c['offering_unit'] for c in other_courses)
        f.write("**Top Offering Units:**\n\n")
        for unit, count in unit_counts.most_common(10):
            unit_pct = (count / len(other_courses) * 100) if len(other_courses) > 0 else 0
            f.write(f"- {unit}: {count} ({unit_pct:.1f}%)\n")
        f.write("\n---\n\n")

        # Overview analysis
        f.write("## Overall Analysis (LLM-Generated)\n\n")
        f.write(overview_analysis)
        f.write("\n\n---\n\n")

        # Unit-by-unit analysis
        f.write("## Analysis by Offering Unit (LLM-Generated)\n\n")
        for unit, analysis in unit_analyses.items():
            unit_count = len([c for c in other_courses if c['offering_unit'] == unit])
            f.write(f"### {unit} ({unit_count} courses)\n\n")
            f.write(analysis)
            f.write("\n\n")

        f.write("---\n\n")

        # Course listing
        f.write("## Complete Course Listing\n\n")

        # Sort by offering unit then subject code
        sorted_courses = sorted(other_courses,
                              key=lambda x: (x['offering_unit'], x['subject_codes']))

        current_unit = None
        for course in sorted_courses:
            if course['offering_unit'] != current_unit:
                current_unit = course['offering_unit']
                f.write(f"\n### {current_unit}\n\n")

            f.write(f"#### {course['subject_codes']}: {course['course_title']}\n\n")
            f.write(f"- **Level**: {'Graduate' if course['is_graduate'] == 'Yes' else 'Undergraduate'}\n")
            f.write(f"- **Units**: {course['max_units']}\n")
            f.write(f"- **URL**: {course['course_url']}\n\n")

            if course.get('catalog_description'):
                f.write("**Catalog Description:**\n\n")
                f.write(f"{course['catalog_description']}\n\n")

            f.write("**Classification Justification:**\n\n")
            f.write(f"{course['classification_justification']}\n\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze 'Other' courses using LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze 'Other' courses and generate report
  python explain_other_courses.py

  # Use custom input/output files
  python explain_other_courses.py -i my_courses.json -o other_analysis.md

  # Skip unit-by-unit analysis (faster)
  python explain_other_courses.py --skip-unit-analysis
        """
    )

    parser.add_argument(
        "-i", "--input",
        type=str,
        default="classified_courses.json",
        help="Input JSON file with classified courses (default: classified_courses.json)"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default="other_courses_analysis.md",
        help="Output markdown file (default: other_courses_analysis.md)"
    )

    parser.add_argument(
        "--skip-unit-analysis",
        action="store_true",
        help="Skip the unit-by-unit analysis (faster, less detailed)"
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found")
        return 1

    # Setup LLM
    print("Setting up LLM connection...")
    try:
        llm = setup_llm()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nMake sure your .env file contains:")
        print("  LLM_API_KEY=your_api_key")
        print("  LLM_MODEL_NAME=your_model_name")
        print("  LLM_BASE_URL=your_base_url (optional)")
        return 1

    # Load courses
    print(f"Loading courses from {args.input}...")
    courses = load_courses(args.input)
    other_courses = get_other_courses(courses)

    print(f"Found {len(other_courses)} courses classified as 'Other' out of {len(courses)} total courses")
    print(f"That's {len(other_courses)/len(courses)*100:.1f}% of all courses")

    if not other_courses:
        print("No 'Other' courses found. Nothing to analyze.")
        return 0

    # Perform overall analysis
    print("\n" + "="*60)
    print("Step 1: Overall Analysis")
    print("="*60)
    overview_analysis = analyze_other_courses_overview(llm, other_courses)

    # Perform unit-by-unit analysis
    unit_analyses = {}
    if not args.skip_unit_analysis:
        print("\n" + "="*60)
        print("Step 2: Analysis by Offering Unit")
        print("="*60)
        unit_analyses = analyze_by_offering_unit(llm, other_courses)

    # Generate report
    print("\n" + "="*60)
    print("Step 3: Generating Report")
    print("="*60)
    generate_markdown_report(
        args.output,
        len(courses),
        other_courses,
        overview_analysis,
        unit_analyses
    )

    print(f"\n✓ Analysis complete!")
    print(f"✓ Report generated: {args.output}")

    return 0


if __name__ == "__main__":
    exit(main())
