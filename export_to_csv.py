import json
import csv

def main():
    # Load the reclassified data
    print("Loading reclassified courses...")
    with open('reclassified_courses_with_topics.json', 'r') as f:
        courses = json.load(f)

    print(f"Found {len(courses)} courses")

    # Prepare CSV output
    output_file = 'reclassified_courses.csv'

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['subject_codes', 'offering_unit', 'course_title', 'course_type', 'topics']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for course in courses:
            # Get subject codes
            subject_codes = course.get('subject_codes', '')

            # Get offering unit
            offering_unit = course.get('offering_unit', '')

            # Get course title
            course_title = course.get('course_title', '')

            # Get course type
            course_type = course.get('course_type', '')

            # Get topics and merge with semicolons
            topics_list = course.get('topics', [])
            topics = '; '.join(topics_list) if topics_list else ''

            writer.writerow({
                'subject_codes': subject_codes,
                'offering_unit': offering_unit,
                'course_title': course_title,
                'course_type': course_type,
                'topics': topics
            })

    print(f"\nExport complete!")
    print(f"Saved to {output_file}")

    # Print summary statistics
    print(f"\n{'='*60}")
    print("Summary Statistics:")
    print(f"{'='*60}")

    type_counts = {}
    for course in courses:
        ctype = course.get('course_type', 'unknown')
        type_counts[ctype] = type_counts.get(ctype, 0) + 1

    for ctype, count in sorted(type_counts.items()):
        print(f"{ctype}: {count} courses")

if __name__ == "__main__":
    main()
