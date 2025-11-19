#!/usr/bin/env python3
"""
Analysis script for course inventory from classified_courses.json.
Generates an executive report with comprehensive statistics and breakdowns by course type.
"""

import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional
from datetime import datetime


def load_courses(json_file: str) -> List[Dict[str, Any]]:
    """Load classified courses from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_header(f, title: str, level: int = 1):
    """Write a markdown header."""
    f.write(f"\n{'#' * level} {title}\n\n")


def write_table_row(f, columns: List[str], header: bool = False):
    """Write a table row in markdown format."""
    f.write("| " + " | ".join(str(c) for c in columns) + " |\n")
    if header:
        f.write("| " + " | ".join("---" for _ in columns) + " |\n")


def analyze_overall_statistics(courses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate overall statistics about the course inventory."""
    total = len(courses)

    # Course type distribution
    type_counts = Counter(c['course_type'] for c in courses)

    # Graduate vs undergraduate
    grad_counts = Counter(c['is_graduate'] for c in courses)

    # Offering units
    unit_counts = Counter(c['offering_unit'] for c in courses)

    # Has syllabus description
    has_syllabus = sum(1 for c in courses
                       if c.get('syllabus_description') and
                       c['syllabus_description'] != "Not available")

    return {
        'total': total,
        'type_counts': type_counts,
        'grad_counts': grad_counts,
        'unit_counts': unit_counts,
        'has_syllabus': has_syllabus,
        'has_syllabus_pct': (has_syllabus / total * 100) if total > 0 else 0
    }


def analyze_by_course_type(courses: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """Analyze courses grouped by their classification type."""
    by_type = defaultdict(list)

    for course in courses:
        by_type[course['course_type']].append(course)

    analysis = {}
    for course_type, type_courses in by_type.items():
        # Graduate level distribution
        grad_dist = Counter(c['is_graduate'] for c in type_courses)

        # Offering units
        unit_dist = Counter(c['offering_unit'] for c in type_courses)

        # Has syllabus
        has_syllabus = sum(1 for c in type_courses
                          if c.get('syllabus_description') and
                          c['syllabus_description'] != "Not available")

        analysis[course_type] = {
            'count': len(type_courses),
            'grad_dist': grad_dist,
            'unit_dist': unit_dist,
            'has_syllabus': has_syllabus,
            'courses': type_courses
        }

    return analysis


def get_type_label(course_type: str) -> str:
    """Convert course type to readable label."""
    return course_type.replace('_', ' ').title()


def write_executive_summary(f, stats: Dict[str, Any], type_analysis: Dict[str, Dict]):
    """Write executive summary section."""
    write_header(f, "Executive Summary", 2)

    total = stats['total']

    # Opening paragraph
    f.write(f"This report analyzes a comprehensive inventory of **{total} courses** classified across five categories: "
            f"Core AI, Applied AI, Core Data Science, Applied Data Science, and Other. ")

    # Course type summary
    type_counts = stats['type_counts']
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

    # Find AI/DS split
    ai_courses = type_counts.get('core_ai', 0) + type_counts.get('applied_ai', 0)
    ds_courses = type_counts.get('core_data_science', 0) + type_counts.get('applied_data_science', 0)
    other_courses = type_counts.get('other', 0)

    ai_pct = (ai_courses / total * 100) if total > 0 else 0
    ds_pct = (ds_courses / total * 100) if total > 0 else 0
    other_pct = (other_courses / total * 100) if total > 0 else 0

    f.write(f"Of these, **{ai_courses} courses ({ai_pct:.1f}%)** are AI-focused, "
            f"**{ds_courses} courses ({ds_pct:.1f}%)** are Data Science-focused, "
            f"and **{other_courses} courses ({other_pct:.1f}%)** fall into other categories.\n\n")

    # Graduate vs Undergraduate
    grad_count = stats['grad_counts'].get('Yes', 0)
    undergrad_count = stats['grad_counts'].get('No', 0)
    grad_pct = (grad_count / total * 100) if total > 0 else 0
    undergrad_pct = (undergrad_count / total * 100) if total > 0 else 0

    f.write(f"The course inventory shows a **{'graduate-heavy' if grad_count > undergrad_count else 'balanced'}** "
            f"distribution with {grad_count} graduate courses ({grad_pct:.1f}%) and {undergrad_count} undergraduate "
            f"courses ({undergrad_pct:.1f}%). ")

    # Syllabus data availability
    syllabus_count = stats['has_syllabus']
    syllabus_pct = stats['has_syllabus_pct']
    f.write(f"Syllabus data is available for **{syllabus_count} courses ({syllabus_pct:.1f}%)**, "
            f"providing detailed information for {'less than half' if syllabus_pct < 50 else 'approximately half' if syllabus_pct < 60 else 'the majority'} "
            f"of the inventory.\n\n")

    # Offering units
    unit_count = len(stats['unit_counts'])
    top_units = stats['unit_counts'].most_common(3)
    f.write(f"Courses are distributed across **{unit_count} different offering units**, with the top three being ")
    unit_descriptions = []
    for unit, count in top_units:
        pct = (count / total * 100) if total > 0 else 0
        unit_descriptions.append(f"{unit} ({count} courses, {pct:.1f}%)")
    f.write(", ".join(unit_descriptions[:-1]) + f", and {unit_descriptions[-1]}.\n\n")


def write_overall_statistics(f, stats: Dict[str, Any]):
    """Write overall statistics section."""
    write_header(f, "Overall Statistics", 2)

    f.write("The following tables provide a high-level overview of the course inventory distribution "
            "by classification type and academic level.\n\n")

    # Course type distribution
    write_header(f, "Course Type Distribution", 3)

    write_table_row(f, ["Course Type", "Count", "Percentage"], header=True)
    for course_type, count in sorted(stats['type_counts'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
        type_label = get_type_label(course_type)
        write_table_row(f, [type_label, count, f"{pct:.1f}%"])

    f.write("\n")

    # Add narrative
    sorted_types = sorted(stats['type_counts'].items(), key=lambda x: x[1], reverse=True)
    top_type = sorted_types[0]
    f.write(f"**{get_type_label(top_type[0])}** represents the largest category with {top_type[1]} courses, "
            f"followed by ")

    if len(sorted_types) > 2:
        second_type = sorted_types[1]
        f.write(f"**{get_type_label(second_type[0])}** ({second_type[1]} courses) and ")
        third_type = sorted_types[2]
        f.write(f"**{get_type_label(third_type[0])}** ({third_type[1]} courses).\n\n")

    # Graduate vs Undergraduate
    write_header(f, "Academic Level Distribution", 3)

    write_table_row(f, ["Level", "Count", "Percentage"], header=True)
    for level, count in sorted(stats['grad_counts'].items()):
        pct = (count / stats['total'] * 100) if stats['total'] > 0 else 0
        level_label = "Graduate" if level == "Yes" else "Undergraduate"
        write_table_row(f, [level_label, count, f"{pct:.1f}%"])

    f.write("\n")


def write_course_type_breakdown(f, analysis: Dict[str, Dict], total: int):
    """Write detailed breakdown by course type with narrative."""
    write_header(f, "Detailed Breakdown by Course Type", 2)

    f.write("This section provides a comprehensive analysis of each course type, including level distribution, "
            "offering unit distribution, and data availability.\n\n")

    # Process in a logical order
    for course_type in ['core_ai', 'applied_ai', 'core_data_science', 'applied_data_science', 'other']:
        if course_type not in analysis:
            continue

        data = analysis[course_type]
        type_label = get_type_label(course_type)
        count = data['count']
        pct = (count / total * 100) if total > 0 else 0

        write_header(f, f"{type_label}", 3)

        # Narrative introduction
        grad_count = data['grad_dist'].get('Yes', 0)
        undergrad_count = data['grad_dist'].get('No', 0)
        grad_pct = (grad_count / count * 100) if count > 0 else 0

        level_desc = "predominantly graduate-level" if grad_pct > 60 else "predominantly undergraduate" if grad_pct < 40 else "balanced between graduate and undergraduate levels"

        f.write(f"This category contains **{count} courses ({pct:.1f}% of total inventory)** and is {level_desc}. ")

        # Top offering units narrative
        top_units = data['unit_dist'].most_common(3)
        if top_units:
            f.write(f"The primary offering units are ")
            unit_list = []
            for unit, unit_count in top_units:
                unit_pct = (unit_count / count * 100) if count > 0 else 0
                unit_list.append(f"**{unit}** ({unit_count} courses, {unit_pct:.1f}%)")
            if len(unit_list) > 1:
                f.write(", ".join(unit_list[:-1]) + f", and {unit_list[-1]}")
            else:
                f.write(unit_list[0])
            f.write(". ")

        # Syllabus availability
        syllabus_count = data['has_syllabus']
        syllabus_pct = (syllabus_count / count * 100) if count > 0 else 0
        f.write(f"Syllabus data is available for {syllabus_count} courses ({syllabus_pct:.1f}%).\n\n")

        # Level Distribution Table
        write_header(f, "Level Distribution", 4)
        write_table_row(f, ["Level", "Count", "Percentage"], header=True)
        for level in ['No', 'Yes']:  # Undergraduate first, then Graduate
            if level in data['grad_dist']:
                count_level = data['grad_dist'][level]
                level_pct = (count_level / count * 100) if count > 0 else 0
                level_label = "Graduate" if level == "Yes" else "Undergraduate"
                write_table_row(f, [level_label, count_level, f"{level_pct:.1f}%"])
        f.write("\n")

        # Offering Units Table (all units, sorted descending)
        write_header(f, "Offering Unit Distribution", 4)
        write_table_row(f, ["Offering Unit", "Count", "Percentage"], header=True)
        for unit, unit_count in sorted(data['unit_dist'].items(), key=lambda x: x[1], reverse=True):
            unit_pct = (unit_count / count * 100) if count > 0 else 0
            write_table_row(f, [unit, unit_count, f"{unit_pct:.1f}%"])
        f.write("\n")


def write_course_listing(f, courses: List[Dict[str, Any]], course_type: Optional[str] = None):
    """Write detailed course listing."""
    if course_type:
        type_label = get_type_label(course_type)
        write_header(f, f"Appendix: Course Listing - {type_label}", 2)
        courses_to_list = [c for c in courses if c['course_type'] == course_type]

        f.write(f"This appendix provides detailed information for all {len(courses_to_list)} courses "
                f"classified as {type_label}.\n\n")
    else:
        write_header(f, "Appendix: Complete Course Listing", 2)
        courses_to_list = courses

        f.write(f"This appendix provides detailed information for all {len(courses_to_list)} courses "
                f"in the inventory.\n\n")

    # Sort by subject code
    courses_to_list = sorted(courses_to_list, key=lambda x: x['subject_codes'])

    for course in courses_to_list:
        f.write(f"### {course['subject_codes']}: {course['course_title']}\n\n")
        f.write(f"- **Course ID**: {course['course_id']}\n")
        f.write(f"- **Offering Unit**: {course['offering_unit']}\n")
        f.write(f"- **Level**: {'Graduate' if course['is_graduate'] == 'Yes' else 'Undergraduate'}\n")
        f.write(f"- **Units**: {course['max_units']}\n")
        f.write(f"- **Course Type**: {get_type_label(course['course_type'])}\n")
        f.write(f"- **URL**: {course['course_url']}\n\n")

        if course.get('catalog_description'):
            f.write("**Catalog Description:**\n\n")
            f.write(f"{course['catalog_description']}\n\n")

        if course.get('syllabus_description') and course['syllabus_description'] != "Not available":
            f.write("**Syllabus Description:**\n\n")
            f.write(f"{course['syllabus_description']}\n\n")

        f.write("**Classification Justification:**\n\n")
        f.write(f"{course['classification_justification']}\n\n")
        f.write("---\n\n")


def generate_report(courses: List[Dict[str, Any]], output_file: str,
                   include_listings: bool = False,
                   listing_type: Optional[str] = None):
    """Generate the complete markdown executive report."""

    stats = analyze_overall_statistics(courses)
    type_analysis = analyze_by_course_type(courses)

    with open(output_file, 'w', encoding='utf-8') as f:
        # Title and metadata
        f.write("# AI and Data Science Course Inventory\n")
        f.write("## Executive Report\n\n")
        f.write(f"**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Data Source**: classified_courses.json\n\n")
        f.write(f"**Total Courses Analyzed**: {stats['total']}\n\n")
        f.write("---\n\n")

        # Table of contents
        write_header(f, "Table of Contents", 2)
        f.write("1. [Executive Summary](#executive-summary)\n")
        f.write("2. [Overall Statistics](#overall-statistics)\n")
        f.write("   - [Course Type Distribution](#course-type-distribution)\n")
        f.write("   - [Academic Level Distribution](#academic-level-distribution)\n")
        f.write("3. [Detailed Breakdown by Course Type](#detailed-breakdown-by-course-type)\n")
        for course_type in ['core_ai', 'applied_ai', 'core_data_science', 'applied_data_science', 'other']:
            if course_type in type_analysis:
                type_label = get_type_label(course_type)
                f.write(f"   - [{type_label}](#{course_type.replace('_', '-')})\n")
        if include_listings:
            if listing_type:
                type_label = get_type_label(listing_type)
                f.write(f"4. [Appendix: Course Listing - {type_label}](#appendix-course-listing---{listing_type.replace('_', '-')})\n")
            else:
                f.write("4. [Appendix: Complete Course Listing](#appendix-complete-course-listing)\n")
        f.write("\n---\n\n")

        # Write sections
        write_executive_summary(f, stats, type_analysis)
        write_overall_statistics(f, stats)
        write_course_type_breakdown(f, type_analysis, stats['total'])

        # Optional course listings
        if include_listings:
            write_course_listing(f, courses, listing_type)

    return output_file


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate executive report for course inventory analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate executive report
  python analyze_course_inventory.py

  # Generate report with custom output file
  python analyze_course_inventory.py -o executive_report.md

  # Include all course listings as appendix
  python analyze_course_inventory.py --include-listings

  # Include only core AI course listings as appendix
  python analyze_course_inventory.py --include-listings --listing-type core_ai

  # Custom input file
  python analyze_course_inventory.py -i my_courses.json
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
        default="course_inventory_report.md",
        help="Output markdown file (default: course_inventory_report.md)"
    )

    parser.add_argument(
        "--include-listings",
        action="store_true",
        help="Include detailed course listings as appendix"
    )

    parser.add_argument(
        "--listing-type",
        type=str,
        choices=['core_ai', 'applied_ai', 'core_data_science', 'applied_data_science', 'other'],
        help="Specific course type to list in appendix (requires --include-listings)"
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' not found")
        print("\nExpected file: classified_courses.json")
        return 1

    # Validate listing-type usage
    if args.listing_type and not args.include_listings:
        print("Warning: --listing-type specified without --include-listings. Adding --include-listings.")
        args.include_listings = True

    print(f"Loading courses from {args.input}...")
    courses = load_courses(args.input)
    print(f"Loaded {len(courses)} courses")

    print("Generating executive report...")
    output_file = generate_report(
        courses,
        args.output,
        include_listings=args.include_listings,
        listing_type=args.listing_type
    )

    print(f"\n✓ Executive report generated: {output_file}")
    print(f"\nSummary:")
    print(f"  Total courses: {len(courses)}")

    type_counts = Counter(c['course_type'] for c in courses)
    for course_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        type_label = get_type_label(course_type)
        pct = (count / len(courses) * 100) if len(courses) > 0 else 0
        print(f"  {type_label}: {count} ({pct:.1f}%)")

    return 0


if __name__ == "__main__":
    exit(main())
