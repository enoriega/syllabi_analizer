#!/usr/bin/env python3
"""
Script to classify courses from a CSV file into different categories:
- Core AI: Where AI is the subject of focus
- Applied AI: Where AI is applied to a domain or problem
- Core Data Science: Where data science (pipelines, cleaning, dashboards, statistics) is the focus
- Applied Data Science: Where data science is applied to a domain or problem

The script:
1. Reads a CSV file with course information
2. Fetches course descriptions from catalog URLs
3. Matches courses with syllabi from parsed_syllabi_dedup.json
4. Uses an LLM to classify courses based on all available information
5. Outputs a JSON file with classifications and justifications
"""

import os
import csv
import json
import re
import argparse
import multiprocessing as mp
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models import ClassifiedCourse, CourseType


# Load environment variables
load_dotenv()


@dataclass
class CourseInfo:
    """Raw course information from CSV."""
    course_id: str
    subject_codes: str
    offering_unit: str
    course_title: str
    max_units: str
    course_url: str
    is_graduate: str


@dataclass
class ClassificationTask:
    """Task to be processed by a worker."""
    course: CourseInfo
    catalog_description: Optional[str]
    syllabus: Optional[Dict[str, Any]]
    index: int
    total: int


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
        "temperature": 0.0,  # Use deterministic output
    }

    if base_url:
        llm_kwargs["base_url"] = base_url

    return ChatOpenAI(**llm_kwargs)


def read_courses_csv(csv_path: Path) -> List[CourseInfo]:
    """
    Read courses from CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        List of CourseInfo objects
    """
    courses = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows
            if not row.get('Course ID'):
                continue

            courses.append(CourseInfo(
                course_id=row['Course ID'].strip(),
                subject_codes=row['Subject Code(s)'].strip(),
                offering_unit=row['Offering Unit'].strip(),
                course_title=row['Course Title'].strip(),
                max_units=row['Max Units'].strip(),
                course_url=row['Course URL'].strip(),
                is_graduate=row['Graduate'].strip()
            ))

    return courses


def fetch_catalog_description(url: str) -> Optional[str]:
    """
    Fetch course description from catalog URL using web scraping.
    Extracts only the course description content, filtering out navigation,
    headers, footers, and metadata.

    Args:
        url: URL to the course catalog page

    Returns:
        Course description text or None if fetch fails
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements (navigation, headers, footers, etc.)
        for element in soup.find_all(['nav', 'header', 'footer', 'script', 'style']):
            element.decompose()

        # Remove common navigation and UI elements
        for element in soup.find_all(class_=re.compile(r'(nav|menu|header|footer|sidebar|breadcrumb)', re.I)):
            element.decompose()

        description = None

        # Strategy 1: Look for specific course description container
        # This selector targets the actual course description section
        course_desc_selectors = [
            'div.courseblock',
            'div.course-description',
            'div#course-description',
            'div.course_desc',
            'section.course-description',
            'div[class*="course"][class*="desc"]'
        ]

        for selector in course_desc_selectors:
            element = soup.select_one(selector)
            if element:
                description = element.get_text(strip=True)
                break

        # Strategy 2: Look for "Course Description" heading and extract following content
        if not description:
            # Find heading that contains "Course Description" or just "Description"
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'dt', 'strong']):
                heading_text = heading.get_text(strip=True).lower()
                if 'course description' in heading_text or heading_text == 'description':
                    # Get the next sibling or parent's next sibling that contains text
                    next_elem = heading.find_next_sibling(['p', 'div', 'dd'])
                    if next_elem:
                        desc_text = next_elem.get_text(strip=True)
                        # Ensure it's a substantial description
                        if len(desc_text) > 30 and not desc_text.startswith(('Min Units', 'Max Units', 'Repeatable')):
                            description = desc_text
                            break

        # Strategy 3: Filter out metadata and extract the main description paragraph
        if not description:
            # Look for paragraphs or divs that contain course information
            # Filter out common metadata patterns
            exclude_patterns = [
                r'^(Min|Max) Units:?\s*\d+',
                r'^Repeatable for Credit',
                r'^Grading Basis',
                r'^Career:?\s*\w+',
                r'^Enrollment Requirements',
                r'^Course Requisites',
                r'^May be convened with',
                r'^Component:?\s*\w+',
                r'^Optional Component',
                r'^Typically Offered',
                r'^Powered by',
                r'University of Arizona',
                r'^Home.*Courses.*Policies',
                r'Skip to Main Content',
            ]

            for tag in soup.find_all(['p', 'div']):
                text = tag.get_text(strip=True)

                # Skip empty or very short text
                if len(text) < 30:
                    continue

                # Skip if it matches any exclude pattern
                if any(re.match(pattern, text, re.I) for pattern in exclude_patterns):
                    continue

                # Skip if it's mostly navigation/metadata
                if any(keyword in text.lower() for keyword in ['skip to', 'powered by', 'catalog', 'home/courses', 'search . . .']):
                    continue

                # Skip if it contains too many links (likely navigation)
                links = tag.find_all('a')
                if len(links) > 5:
                    continue

                # This is likely the description
                description = text
                break

        # Clean up the description if found
        if description:
            # Remove common prefixes
            description = re.sub(r'^(Course Description:?|Description:?)\s*', '', description, flags=re.I)

            # Remove metadata that might have been captured
            # Stop at common metadata markers
            for marker in ['Min Units', 'Max Units', 'Repeatable for Credit', 'Grading Basis',
                          'Course Requisites', 'May be convened', 'Component', 'Typically Offered']:
                if marker in description:
                    description = description.split(marker)[0].strip()

            # Ensure we have a substantial description
            if len(description) < 20:
                description = None

        return description

    except Exception as e:
        print(f"  Warning: Failed to fetch description from {url}: {str(e)}")
        return None


def load_syllabi(syllabi_path: Path) -> List[Dict[str, Any]]:
    """
    Load parsed syllabi from JSON file.

    Args:
        syllabi_path: Path to the parsed syllabi JSON file

    Returns:
        List of syllabus dictionaries
    """
    with open(syllabi_path, 'r') as f:
        return json.load(f)


def normalize_subject_code(code: str) -> str:
    """
    Normalize a subject code for matching.
    Removes spaces, converts to uppercase.

    Args:
        code: Subject code to normalize

    Returns:
        Normalized subject code
    """
    return re.sub(r'\s+', '', code.upper())


def extract_subject_codes(subject_codes_str: str) -> List[str]:
    """
    Extract individual subject codes from a string that may contain multiple codes.
    Example: "CSC 438 / LING 438 / PSY 438" -> ["CSC438", "LING438", "PSY438"]

    Args:
        subject_codes_str: String containing one or more subject codes

    Returns:
        List of normalized subject codes
    """
    # Split by '/' and extract codes
    parts = subject_codes_str.split('/')
    codes = []

    for part in parts:
        part = part.strip()
        # Extract subject code (letters followed by numbers)
        match = re.search(r'([A-Z]+)\s*(\d+)', part)
        if match:
            code = normalize_subject_code(match.group(0))
            codes.append(code)

    return codes


def match_syllabus(course: CourseInfo, syllabi: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find a matching syllabus for a course based on subject codes.
    Uses fuzzy matching to handle variations in subject code formatting.

    Args:
        course: CourseInfo object
        syllabi: List of syllabus dictionaries

    Returns:
        Matching syllabus dict or None if no match found
    """
    course_codes = extract_subject_codes(course.subject_codes)

    for syllabus in syllabi:
        # Extract subject codes from course name in syllabus
        course_name = syllabus.get('course_name', '')

        # Look for patterns like "CSC 477", "ISTA-450", "CSC477", etc.
        syllabus_codes = []
        matches = re.finditer(r'([A-Z]+)[\s\-]*(\d+)', course_name)
        for match in matches:
            code = normalize_subject_code(match.group(0))
            syllabus_codes.append(code)

        # Check if any course code matches any syllabus code
        for course_code in course_codes:
            if course_code in syllabus_codes:
                return syllabus

    return None


def process_classification_task(task: ClassificationTask) -> Dict[str, Any]:
    """
    Worker function to process a single classification task.
    This function runs in a separate process.

    Args:
        task: ClassificationTask to process

    Returns:
        Dictionary with classification result or error information
    """
    try:
        # Setup LLM in worker process (each worker needs its own instance)
        llm = setup_llm()

        # Classify the course
        classified = classify_course(
            task.course,
            task.catalog_description,
            task.syllabus,
            llm
        )

        print(f"  [{task.index}/{task.total}] ✓ {task.course.course_title} -> {classified.course_type}")

        return {
            "success": True,
            "result": classified.model_dump()
        }

    except Exception as e:
        print(f"  [{task.index}/{task.total}] ✗ {task.course.course_title} -> Error: {str(e)}")

        return {
            "success": False,
            "result": {
                "course_id": task.course.course_id,
                "subject_codes": task.course.subject_codes,
                "offering_unit": task.course.offering_unit,
                "course_title": task.course.course_title,
                "max_units": task.course.max_units,
                "course_url": task.course.course_url,
                "is_graduate": task.course.is_graduate,
                "catalog_description": task.catalog_description,
                "syllabus_description": task.syllabus.get('description') if task.syllabus else None,
                "course_type": "other",
                "classification_justification": f"Classification failed: {str(e)}"
            }
        }


def classify_course(
    course: CourseInfo,
    catalog_description: Optional[str],
    syllabus: Optional[Dict[str, Any]],
    llm: ChatOpenAI
) -> ClassifiedCourse:
    """
    Classify a course using an LLM based on all available information.

    Args:
        course: CourseInfo object
        catalog_description: Description from catalog URL
        syllabus: Matched syllabus dict (if any)
        llm: Configured ChatOpenAI instance

    Returns:
        ClassifiedCourse object with classification and justification
    """
    # Create parser for structured output
    parser = PydanticOutputParser(pydantic_object=ClassifiedCourse)

    # Build context for classification
    context_parts = [
        f"Course Title: {course.course_title}",
        f"Subject Code(s): {course.subject_codes}",
        f"Offering Unit: {course.offering_unit}",
    ]

    if catalog_description:
        context_parts.append(f"\nCatalog Description:\n{catalog_description}")

    syllabus_description = None
    if syllabus:
        syllabus_description = syllabus.get('description', '')
        if syllabus_description:
            context_parts.append(f"\nDetailed Syllabus Description:\n{syllabus_description}")

    context = "\n".join(context_parts)

    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert in classifying academic courses into the following categories:

1. **core_ai**: A core AI course where artificial intelligence is the primary subject of focus.
   - Examples: Machine Learning, Neural Networks, Deep Learning, Natural Language Processing, Computer Vision
   - These courses teach AI concepts, algorithms, and techniques directly

2. **applied_ai**: An applied AI course where AI techniques are applied to a specific domain or to solve domain-specific problems.
   - Examples: AI in Healthcare, AI for Robotics, AI in Finance, Medical Image Analysis using AI
   - These courses use AI as a tool to solve problems in another field

3. **core_data_science**: A core data science course where the broader field of data science is the primary subject.
   - Includes: data pipelines, data cleaning, data warehousing, dashboards, visualization, basic statistics
   - Does NOT include: deep learning, generative AI, or advanced machine learning (those are AI)
   - Examples: Data Mining, Data Warehousing, Statistical Methods, Data Visualization, Data Engineering

4. **applied_data_science**: An applied data science course where data science techniques are applied to a domain or problem.
   - Examples: Health Data Science, Data Analytics for Business, Biosystems Analytics, Econometrics
   - These courses use data science as a tool to solve problems in another field

5. **other**: Courses that don't fit the above categories.

Important distinctions:
- Machine Learning, Deep Learning, Neural Networks, NLP, Computer Vision are AI (not data science)
- Statistics, data pipelines, data cleaning, visualization without ML are data science
- If both AI and DS concepts are present, classify based on the primary focus
- "Applied" means the course is focused on a specific domain (healthcare, business, biology, etc.)

{format_instructions}

Provide a clear, concise justification for your classification decision."""),
        ("human", """Classify the following course:

{context}

Required output fields:
- course_id: {course_id}
- subject_codes: {subject_codes}
- offering_unit: {offering_unit}
- course_title: {course_title}
- max_units: {max_units}
- course_url: {course_url}
- is_graduate: {is_graduate}
- catalog_description: {catalog_description}
- syllabus_description: {syllabus_description}
- course_type: (one of: core_ai, applied_ai, core_data_science, applied_data_science, other)
- classification_justification: (explain your reasoning)

Classify this course and provide your response in the required JSON format.""")
    ])

    # Format the prompt
    formatted_prompt = prompt.format_messages(
        format_instructions=parser.get_format_instructions(),
        context=context,
        course_id=course.course_id,
        subject_codes=course.subject_codes,
        offering_unit=course.offering_unit,
        course_title=course.course_title,
        max_units=course.max_units,
        course_url=course.course_url,
        is_graduate=course.is_graduate,
        catalog_description=catalog_description or "Not available",
        syllabus_description=syllabus_description or "Not available"
    )

    # Call LLM
    response = llm.invoke(formatted_prompt)

    # Parse response
    classified = parser.parse(response.content)

    return classified


def load_existing_output(output_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load existing output file if it exists.

    Args:
        output_path: Path to the output JSON file

    Returns:
        Dictionary mapping course_id to course data
    """
    if not output_path.exists():
        return {}

    try:
        with open(output_path, 'r') as f:
            data = json.load(f)

        # Create lookup by course_id
        return {course['course_id']: course for course in data}

    except Exception as e:
        print(f"  Warning: Failed to load existing output: {str(e)}")
        return {}


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Classify courses from CSV into AI/DS categories"
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/courses.csv"),
        help="Path to input CSV file (default: data/courses.csv)"
    )
    parser.add_argument(
        "--syllabi-json",
        type=Path,
        default=Path("parsed_syllabi_dedup.json"),
        help="Path to parsed syllabi JSON file (default: parsed_syllabi_dedup.json)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("classified_courses.json"),
        help="Path to output JSON file (default: classified_courses.json)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of courses to process (useful for testing)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of worker processes for parallel classification (default: 10)"
    )
    parser.add_argument(
        "--retry-missing",
        action="store_true",
        help="Retry fetching catalog descriptions for courses missing them in existing output"
    )

    args = parser.parse_args()

    # Validate input files
    if not args.input_csv.exists():
        print(f"Error: Input CSV file not found: {args.input_csv}")
        return 1

    if not args.syllabi_json.exists():
        print(f"Error: Syllabi JSON file not found: {args.syllabi_json}")
        return 1

    print("=" * 80)
    print("COURSE CLASSIFICATION")
    print("=" * 80)
    print(f"Input CSV: {args.input_csv}")
    print(f"Syllabi JSON: {args.syllabi_json}")
    print(f"Output: {args.output}")
    if args.limit:
        print(f"Limit: {args.limit} courses")
    print(f"Workers: {args.workers}")
    if args.retry_missing:
        print(f"Mode: Retry missing catalog descriptions")
    print()

    # Load existing output if retry mode
    existing_courses = {}
    if args.retry_missing:
        print("Loading existing output...")
        existing_courses = load_existing_output(args.output)
        if existing_courses:
            print(f"  Found {len(existing_courses)} existing classifications")

            # Count how many are missing catalog descriptions
            missing_count = sum(
                1 for course in existing_courses.values()
                if not course.get('catalog_description') or course['catalog_description'] == 'Not available'
            )
            print(f"  {missing_count} courses missing catalog descriptions")
        else:
            print(f"  No existing output found at {args.output}")
            print(f"  Running in normal mode instead")
            args.retry_missing = False
        print()

    # Validate LLM setup (only if not just retrying catalog descriptions)
    if not args.retry_missing:
        print("Validating LLM configuration...")
        try:
            setup_llm()
            print(f"  Using model: {os.getenv('LLM_MODEL_NAME')}")
        except Exception as e:
            print(f"  Error: {str(e)}")
            return 1
        print()

    # Load data
    print("Loading courses from CSV...")
    courses = read_courses_csv(args.input_csv)

    # Apply limit if specified
    if args.limit and args.limit < len(courses):
        courses = courses[:args.limit]
        print(f"  Limited to {len(courses)} courses")
    else:
        print(f"  Loaded {len(courses)} courses")
    print()

    print("Loading syllabi...")
    syllabi = load_syllabi(args.syllabi_json)
    print(f"  Loaded {len(syllabi)} syllabi")
    print()

    # Prepare tasks - fetch catalog descriptions and match syllabi first
    print("Preparing classification tasks...")

    if args.retry_missing:
        print(f"  Retrying catalog descriptions for courses with missing data...")

        tasks = []
        courses_to_update = []

        for i, course in enumerate(courses, 1):
            existing = existing_courses.get(course.course_id)

            # Check if this course needs catalog description retry
            needs_retry = (
                existing and
                (not existing.get('catalog_description') or
                 existing['catalog_description'] == 'Not available')
            )

            if needs_retry:
                # Retry fetching catalog description
                catalog_description = fetch_catalog_description(course.course_url)

                if catalog_description:
                    print(f"    [{i}/{len(courses)}] {course.course_title}: catalog✓ (retried)")

                    # Update existing course data with new description
                    existing['catalog_description'] = catalog_description
                    courses_to_update.append(existing)
                else:
                    print(f"    [{i}/{len(courses)}] {course.course_title}: catalog✗ (retry failed)")
                    courses_to_update.append(existing)
            elif existing:
                # Keep existing data as-is
                courses_to_update.append(existing)

        # Update the existing courses dictionary with retried data
        classified_courses = courses_to_update

        print(f"  Processed {len(courses_to_update)} courses")
        print()

    else:
        print(f"  Fetching catalog descriptions and matching syllabi...")

        tasks = []
        for i, course in enumerate(courses, 1):
            # Check if we have existing data for this course
            existing = existing_courses.get(course.course_id)

            # Fetch catalog description (or use existing if available and valid)
            if existing and existing.get('catalog_description') and existing['catalog_description'] != 'Not available':
                catalog_description = existing['catalog_description']
                print(f"    [{i}/{len(courses)}] {course.course_title}: catalog✓ (cached)")
            else:
                catalog_description = fetch_catalog_description(course.course_url)
                status = "catalog✓" if catalog_description else "catalog✗"

            # Match with syllabus
            matched_syllabus = match_syllabus(course, syllabi)

            # Create task
            task = ClassificationTask(
                course=course,
                catalog_description=catalog_description,
                syllabus=matched_syllabus,
                index=i,
                total=len(courses)
            )
            tasks.append(task)

            # Print progress (if not cached)
            if not (existing and existing.get('catalog_description') and existing['catalog_description'] != 'Not available'):
                status_parts = []
                if catalog_description:
                    status_parts.append("catalog✓")
                else:
                    status_parts.append("catalog✗")

                if matched_syllabus:
                    status_parts.append("syllabus✓")
                else:
                    status_parts.append("syllabus✗")

                print(f"    [{i}/{len(courses)}] {course.course_title}: {', '.join(status_parts)}")

        print(f"  Prepared {len(tasks)} classification tasks")
        print()

        # Process classifications in parallel
        print(f"Classifying courses using {args.workers} workers...")
        print("-" * 80)

        classified_courses = []

        with mp.Pool(processes=args.workers) as pool:
            results = pool.map(process_classification_task, tasks)

        # Extract results
        for result in results:
            classified_courses.append(result["result"])

    print("\n" + "=" * 80)

    # Save results
    print(f"\nSaving results to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(classified_courses, f, indent=2)

    print(f"  Saved {len(classified_courses)} classified courses")

    # Print summary statistics
    print("\nClassification Summary:")
    print("-" * 40)
    type_counts = {}
    for course in classified_courses:
        course_type = course['course_type']
        type_counts[course_type] = type_counts.get(course_type, 0) + 1

    for course_type, count in sorted(type_counts.items()):
        print(f"  {course_type:25s}: {count:3d} courses")

    print("\n" + "=" * 80)
    print("DONE!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
