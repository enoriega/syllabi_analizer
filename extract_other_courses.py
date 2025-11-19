import json

# Load the data
with open('classified_courses_with_topics.json', 'r') as f:
    courses = json.load(f)

# Filter courses with course_type == "other"
other_courses = [c for c in courses if c.get('course_type') == 'other']

print(f"Found {len(other_courses)} courses classified as 'other'\n")

# Display each course for manual review
for i, course in enumerate(other_courses, 1):
    print(f"\n{'='*80}")
    print(f"Course {i}/{len(other_courses)}")
    print(f"{'='*80}")
    print(f"Course Name: {course.get('course_name', 'N/A')}")
    print(f"Course Code: {course.get('course_code', 'N/A')}")
    print(f"\nCatalog Description:")
    print(course.get('catalog_description', 'N/A'))
    print(f"\nSyllabus Description:")
    syllabus = course.get('syllabus_description', 'N/A')
    if syllabus and len(syllabus) > 500:
        print(syllabus[:500] + "...")
    else:
        print(syllabus if syllabus else 'N/A')
    print(f"\nTopics: {course.get('topics', [])}")

# Save just the other courses for easier viewing
with open('other_courses_only.json', 'w') as f:
    json.dump(other_courses, f, indent=2)

print(f"\n\nExtracted {len(other_courses)} 'other' courses to other_courses_only.json")
