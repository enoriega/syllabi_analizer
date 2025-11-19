#!/usr/bin/env python3
"""
Script to add topic tags to classified courses.
Reads classified_courses.json and adds a 'topics' field containing acronyms
for detected topics based on catalog and syllabus descriptions.

Topics:
- AI: Artificial Intelligence
- ML: Machine Learning
- DL: Deep Learning
- STAT: Statistics
- NLP: Natural Language Processing
- CV: Computer Vision
- DM: Data Mining
- BI: Business Intelligence
"""

import json
import os
import argparse
import re
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()


# Topic mapping
TOPICS = {
    'AI': 'Artificial Intelligence',
    'ML': 'Machine Learning',
    'DL': 'Deep Learning',
    'STAT': 'Statistics',
    'NLP': 'Natural Language Processing',
    'CV': 'Computer Vision',
    'DM': 'Data Mining',
    'BI': 'Business Intelligence'
}


TOPIC_DETECTION_PROMPT = """You are an expert in identifying topics covered in academic courses related to AI, Data Science, and related fields.

Given a course's information, identify which of the following topics are EXPLICITLY mentioned or CLEARLY implied in the course descriptions:

Topics to identify:
1. **AI** (Artificial Intelligence) - General AI concepts, intelligent systems, AI theory, reasoning, AI agents
2. **ML** (Machine Learning) - Machine learning algorithms, supervised/unsupervised learning, classification, regression, model training
3. **DL** (Deep Learning) - Neural networks, deep neural networks, CNNs, RNNs, transformers, deep learning architectures
4. **STAT** (Statistics) - Statistical methods, probability, statistical inference, hypothesis testing, statistical modeling
5. **NLP** (Natural Language Processing) - Text processing, language models, text mining, computational linguistics, sentiment analysis
6. **CV** (Computer Vision) - Image processing, object detection, image recognition, visual analysis, computer graphics for vision
7. **DM** (Data Mining) - Pattern discovery, knowledge discovery, mining algorithms, association rules, clustering for mining
8. **BI** (Business Intelligence) - Business analytics, dashboards, reporting, data warehousing, decision support systems

Course Information:
- Title: {course_title}
- Subject: {subject_codes}
- Offering Unit: {offering_unit}
- Course Type: {course_type}
- Catalog Description: {catalog_description}
- Syllabus Description: {syllabus_description}

Guidelines:
- Only include topics that are CLEARLY present in the descriptions
- If a topic is a major component of the course, include it
- If descriptions mention specific techniques or methods from a topic, include it
- Be conservative - when in doubt, don't include the topic
- Deep Learning (DL) is a subset of Machine Learning (ML), but tag both if neural networks/deep learning are explicitly mentioned
- Computer Vision (CV) and NLP are application areas that often use ML/DL, tag all relevant topics
- Statistics (STAT) should be tagged when statistical methods are a core component, not just mentioned in passing

Respond with a JSON object containing only the list of applicable topic acronyms:
{{
    "topics": ["acronym1", "acronym2", ...]
}}

Examples:
- "Introduction to Machine Learning" with content about classification and regression → ["ML"]
- "Deep Learning for Computer Vision" → ["ML", "DL", "CV"]
- "Natural Language Processing" with neural networks → ["ML", "DL", "NLP"]
- "Statistical Data Mining" → ["STAT", "DM"]
- "Business Intelligence and Analytics" → ["BI", "STAT"]
"""


def load_courses(json_file: str) -> List[Dict[str, Any]]:
    """Load classified courses from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_topics_with_llm(course: Dict[str, Any]) -> List[str]:
    """
    Use LLM to extract relevant topics from course information.

    Args:
        course: Course dictionary with all course information

    Returns:
        List of topic acronyms
    """
    try:
        # Initialize LLM
        llm = ChatOpenAI(
            model=os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini'),
            temperature=0,  # Deterministic responses
            api_key=os.getenv('LLM_API_KEY'),
            base_url=os.getenv('LLM_BASE_URL'),
        )

        # Prepare course information
        catalog_desc = course.get('catalog_description', 'Not available')
        syllabus_desc = course.get('syllabus_description', 'Not available')

        # Handle None values
        if catalog_desc is None:
            catalog_desc = 'Not available'
        if syllabus_desc is None:
            syllabus_desc = 'Not available'

        # Limit description length to avoid token limits
        if len(catalog_desc) > 1000:
            catalog_desc = catalog_desc[:1000] + "..."
        if len(syllabus_desc) > 2000:
            syllabus_desc = syllabus_desc[:2000] + "..."

        # Create prompt
        prompt = ChatPromptTemplate.from_template(TOPIC_DETECTION_PROMPT)

        # Format the prompt
        formatted_prompt = prompt.format(
            course_title=course.get('course_title', 'Unknown'),
            subject_codes=course.get('subject_codes', 'Unknown'),
            offering_unit=course.get('offering_unit', 'Unknown'),
            course_type=course.get('course_type', 'unknown'),
            catalog_description=catalog_desc,
            syllabus_description=syllabus_desc
        )

        # Get response from LLM
        response = llm.invoke(formatted_prompt)

        # Parse JSON response
        content = response.content if hasattr(response, 'content') else str(response)

        # Handle None content
        if content is None:
            print(f"    LLM returned None content")
            return []

        # Try to extract JSON from markdown code blocks if present
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)
        topics = result.get("topics", [])

        # Validate topics
        valid_topics = [t for t in topics if t in TOPICS]

        return sorted(valid_topics)  # Sort for consistency

    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"    LLM error: {e}")
        return []


def extract_topics_rule_based(course: Dict[str, Any]) -> List[str]:
    """
    Extract topics using rule-based keyword matching as fallback.

    Args:
        course: Course dictionary with all course information

    Returns:
        List of topic acronyms
    """
    topics = set()

    # Combine all text fields
    text_fields = [
        course.get('course_title', ''),
        course.get('catalog_description', ''),
        course.get('syllabus_description', ''),
        course.get('classification_justification', '')
    ]
    combined_text = ' '.join(text_fields).lower()

    # Define keywords for each topic
    keywords = {
        'AI': [
            r'\bartificial intelligence\b', r'\bai\b', r'\bintelligent systems?\b',
            r'\bai agents?\b', r'\breasoning systems?\b', r'\bexpert systems?\b',
            r'\bknowledge representation\b'
        ],
        'ML': [
            r'\bmachine learning\b', r'\bml\b', r'\bsupervised learning\b',
            r'\bunsupervised learning\b', r'\bclassification\b', r'\bregression\b',
            r'\bmodel training\b', r'\bpredictive model', r'\breinforcement learning\b'
        ],
        'DL': [
            r'\bdeep learning\b', r'\bneural networks?\b', r'\bcnn\b', r'\brnn\b',
            r'\bconvolutional neural\b', r'\brecurrent neural\b', r'\btransformers?\b',
            r'\bdeep neural\b', r'\blstm\b', r'\bgan\b'
        ],
        'STAT': [
            r'\bstatistics\b', r'\bstatistical\b', r'\bprobability\b',
            r'\binference\b', r'\bhypothesis testing\b', r'\bstatistical model',
            r'\bbayesian\b', r'\bregression analysis\b'
        ],
        'NLP': [
            r'\bnatural language processing\b', r'\bnlp\b', r'\btext processing\b',
            r'\blanguage model', r'\btext mining\b', r'\bcomputational linguistics?\b',
            r'\bsentiment analysis\b', r'\btext analysis\b'
        ],
        'CV': [
            r'\bcomputer vision\b', r'\bimage processing\b', r'\bobject detection\b',
            r'\bimage recognition\b', r'\bvisual\b', r'\bimage analysis\b',
            r'\bpattern recognition\b', r'\bimage classification\b'
        ],
        'DM': [
            r'\bdata mining\b', r'\bpattern discovery\b', r'\bknowledge discovery\b',
            r'\bassociation rules?\b', r'\bmining algorithms?\b'
        ],
        'BI': [
            r'\bbusiness intelligence\b', r'\bbi\b', r'\bbusiness analytics\b',
            r'\bdashboards?\b', r'\breporting\b', r'\bdata warehous', r'\bdecision support\b'
        ]
    }

    # Check for each topic
    for topic, patterns in keywords.items():
        for pattern in patterns:
            if re.search(pattern, combined_text):
                topics.add(topic)
                break  # Found this topic, move to next

    return sorted(list(topics))


def add_topics_to_courses(courses: List[Dict[str, Any]],
                          use_llm: bool = True,
                          use_rules: bool = False) -> List[Dict[str, Any]]:
    """
    Add topics field to each course.

    Args:
        courses: List of course dictionaries
        use_llm: Whether to use LLM for topic extraction
        use_rules: Whether to use rule-based extraction as fallback

    Returns:
        List of courses with added 'topics' field
    """
    results = []

    print(f"\nProcessing {len(courses)} courses...")
    print(f"Method: {'LLM' if use_llm else 'Rule-based'}\n")

    for i, course in enumerate(courses, 1):
        course_title = course.get('course_title', 'Unknown')
        subject_codes = course.get('subject_codes', 'Unknown')

        print(f"[{i}/{len(courses)}] {subject_codes}: {course_title}")

        topics = []

        # Try LLM first if enabled
        if use_llm:
            topics = extract_topics_with_llm(course)
            if topics:
                print(f"  Topics (LLM): {', '.join(topics)}")

        # Fall back to rules if LLM failed or not enabled
        if not topics and use_rules:
            topics = extract_topics_rule_based(course)
            if topics:
                print(f"  Topics (Rules): {', '.join(topics)}")

        if not topics:
            print(f"  Topics: None detected")

        # Create new course dict with topics
        course_with_topics = course.copy()
        course_with_topics['topics'] = topics
        results.append(course_with_topics)

    return results


def print_topic_statistics(courses: List[Dict[str, Any]]):
    """Print statistics about topic distribution."""
    print("\n" + "="*70)
    print("Topic Distribution Statistics")
    print("="*70)

    topic_counts = {topic: 0 for topic in TOPICS.keys()}
    courses_with_topics = 0
    total_courses = len(courses)

    for course in courses:
        course_topics = course.get('topics', [])
        if course_topics:
            courses_with_topics += 1
            for topic in course_topics:
                if topic in topic_counts:
                    topic_counts[topic] += 1

    print(f"\nCourses with at least one topic: {courses_with_topics}/{total_courses} "
          f"({courses_with_topics/total_courses*100:.1f}%)")
    print(f"\nTopic Counts:")

    for topic in sorted(topic_counts.keys()):
        count = topic_counts[topic]
        pct = (count / total_courses * 100) if total_courses > 0 else 0
        full_name = TOPICS[topic]
        print(f"  {topic:4s} ({full_name:30s}): {count:3d} courses ({pct:5.1f}%)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add topic tags to classified courses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Topics detected:
  AI    - Artificial Intelligence
  ML    - Machine Learning
  DL    - Deep Learning
  STAT  - Statistics
  NLP   - Natural Language Processing
  CV    - Computer Vision
  DM    - Data Mining
  BI    - Business Intelligence

Examples:
  # Add topics using LLM
  python add_course_topics.py

  # Use rule-based extraction only (faster, no API costs)
  python add_course_topics.py --no-llm --use-rules

  # Custom input/output files
  python add_course_topics.py -i my_courses.json -o courses_with_topics.json
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
        default="classified_courses_with_topics.json",
        help="Output JSON file (default: classified_courses_with_topics.json)"
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Don't use LLM for topic extraction"
    )

    parser.add_argument(
        "--use-rules",
        action="store_true",
        help="Use rule-based extraction (as fallback or primary method with --no-llm)"
    )

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found")
        return 1

    # Check for LLM API key if using LLM
    if not args.no_llm and not os.getenv('LLM_API_KEY'):
        print("Warning: LLM_API_KEY not found in environment!")
        print("Either set it in your .env file or use --no-llm --use-rules")
        return 1

    print("="*70)
    print("Course Topic Extraction")
    print("="*70)
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Method: {'LLM' if not args.no_llm else 'Rule-based'}")
    if not args.no_llm and args.use_rules:
        print("Fallback: Rule-based extraction enabled")

    # Load courses
    print("\nLoading courses...")
    courses = load_courses(args.input)
    print(f"Loaded {len(courses)} courses")

    # Add topics
    courses_with_topics = add_topics_to_courses(
        courses,
        use_llm=not args.no_llm,
        use_rules=args.use_rules or args.no_llm
    )

    # Save results
    print(f"\nSaving results to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(courses_with_topics, f, indent=2, ensure_ascii=False)

    # Print statistics
    print_topic_statistics(courses_with_topics)

    print(f"\n✓ Complete! Results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    exit(main())
