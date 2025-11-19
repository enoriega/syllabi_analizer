import json
from typing import Dict, List
import anthropic
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def classify_course(course: Dict) -> str:
    """
    Classify a course as 'Responsible/Ethical AI', 'Philosophy of AI', or 'other'
    based on catalog description and syllabus description.
    """
    catalog_desc = course.get('catalog_description', '')
    syllabus_desc = course.get('syllabus_description', '')
    course_name = course.get('course_name', '')

    # Create prompt for classification
    prompt = f"""Based on the following course information, classify the course into one of these categories:
1. "Responsible/Ethical AI" - courses related to ethical implications of applying AI to society
2. "Philosophy of AI" - courses related to socio-cultural or philosophical studies of AI
3. "other" - if there is no clear fit

Course Name: {course_name}

Catalog Description: {catalog_desc}

Syllabus Description: {syllabus_desc}

Return ONLY one of these exact strings: "Responsible/Ethical AI", "Philosophy of AI", or "other"
"""

    try:
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        classification = message.content[0].text.strip().strip('"').strip("'")

        # Validate the classification
        valid_types = ["Responsible/Ethical AI", "Philosophy of AI", "other"]
        if classification in valid_types:
            return classification
        else:
            # Try to match partial responses
            classification_lower = classification.lower()
            if "responsible" in classification_lower or "ethical" in classification_lower:
                return "Responsible/Ethical AI"
            elif "philosophy" in classification_lower:
                return "Philosophy of AI"
            else:
                return "other"
    except Exception as e:
        print(f"Error classifying course {course_name}: {e}")
        return "other"

def main():
    # Load the data
    print("Loading classified courses...")
    with open('classified_courses_with_topics.json', 'r') as f:
        courses = json.load(f)

    # Filter courses with course_type == "other"
    other_courses = [c for c in courses if c.get('course_type') == 'other']
    print(f"Found {len(other_courses)} courses classified as 'other'")

    # Process courses in parallel
    updated_courses = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all classification tasks
        future_to_course = {
            executor.submit(classify_course, course): course
            for course in other_courses
        }

        # Collect results as they complete
        for i, future in enumerate(as_completed(future_to_course), 1):
            course = future_to_course[future]
            try:
                new_type = future.result()
                course['course_type'] = new_type
                updated_courses.append(course)
                print(f"[{i}/{len(other_courses)}] {course.get('course_name', 'Unknown')}: {new_type}")
            except Exception as e:
                print(f"Error processing course: {e}")
                updated_courses.append(course)

    # Create updated full dataset
    # Replace the old "other" courses with updated ones
    other_course_ids = {c.get('course_id', c.get('course_name')) for c in other_courses}
    final_courses = []

    for course in courses:
        course_id = course.get('course_id', course.get('course_name'))
        if course_id in other_course_ids:
            # Find the updated version
            updated = next((c for c in updated_courses if c.get('course_id', c.get('course_name')) == course_id), course)
            final_courses.append(updated)
        else:
            final_courses.append(course)

    # Save results
    output_file = 'reclassified_courses_with_topics.json'
    with open(output_file, 'w') as f:
        json.dump(final_courses, f, indent=2)

    print(f"\nReclassification complete!")
    print(f"Results saved to {output_file}")

    # Print summary
    type_counts = {}
    for course in updated_courses:
        course_type = course.get('course_type', 'unknown')
        type_counts[course_type] = type_counts.get(course_type, 0) + 1

    print("\nReclassification Summary:")
    for course_type, count in sorted(type_counts.items()):
        print(f"  {course_type}: {count}")

if __name__ == "__main__":
    main()
