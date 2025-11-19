import json

# Manual classification based on catalog and syllabus descriptions
# Course index -> new classification
classifications = {
    0: "Philosophy of AI",  # "Interdisciplinary problems lying at the interface of philosophy and artificial intelligence"
    1: "Philosophy of AI",  # "philosophical foundations of cognitive science... artificial intelligence"
    2: "other",  # Social information theory, not specifically AI ethics or philosophy
    3: "other",  # Neuroeconomics - brain decision making, not AI-focused
    4: "other",  # Multimodal communication/digital literacies with AI intro
    5: "Responsible/Ethical AI",  # "ethical challenges stemming from data-driven decision making... bias, fairness, privacy, surveillance, discrimination"
    6: "Responsible/Ethical AI",  # "False and misleading information online... role of generative AI in both problems and solutions... support trust in science, civic dialogue"
    7: "other",  # Human factors/UX design with AI as one application area
    8: "other",  # Visual content creation with AI tools
    9: "Responsible/Ethical AI",  # "ethics of artificial intelligence... ethical questions raised by recent developments in AI, including... job losses, privacy, algorithmic bias and discrimination"
    10: "other",  # High-performance computing/parallel systems, not AI ethics/philosophy
    11: "Philosophy of AI",  # Graduate version of course 0 - "interface of philosophy and artificial intelligence"
    12: "other",  # Embedded systems design with AI
    13: "other",  # Remote sensing and GIS
    14: "other",  # Legal implications of big data (not specifically AI ethics)
    15: "other",  # Applied mathematics methods
    16: "other",  # Optimization and learning algorithms (technical, not ethics/philosophy)
    17: "Responsible/Ethical AI",  # "responsible technology use, including AI, and the application of professional ethics"
    18: "Responsible/Ethical AI",  # "ethical implications of artificial intelligence systems and AI-enabled processes in law practice"
    19: "other",  # Research dissemination methods
    20: "Responsible/Ethical AI",  # Duplicate of course 5 - "ethical challenges stemming from data-driven decision making"
    21: "Responsible/Ethical AI",  # "Computational propaganda... manipulation using AI algorithms... methods to identify and uncover"
    22: "other",  # Digital media evolution including AI (not focused on ethics/philosophy)
    23: "other",  # AI for instructional design (application, not ethics/philosophy)
    24: "other",  # Digital transformation of macroeconomics
    25: "Responsible/Ethical AI",  # "applied ethics... impact of AI and other technologies" on legal profession
}

def main():
    # Load all courses
    with open('classified_courses_with_topics.json', 'r') as f:
        all_courses = json.load(f)

    # Load just the "other" courses
    with open('other_courses_only.json', 'r') as f:
        other_courses = json.load(f)

    print(f"Reclassifying {len(other_courses)} courses...\n")

    # Apply classifications
    reclassified_count = {'Responsible/Ethical AI': 0, 'Philosophy of AI': 0, 'other': 0}

    for idx, course in enumerate(other_courses):
        new_type = classifications.get(idx, 'other')
        course['course_type'] = new_type
        reclassified_count[new_type] += 1

        catalog = course.get('catalog_description', '')[:100]
        print(f"{idx+1}. {new_type}")
        print(f"   {catalog}...")
        print()

    # Create mapping for quick lookup
    other_catalog_descs = {c.get('catalog_description', ''): c for c in other_courses}

    # Update the full dataset
    updated_courses = []
    for course in all_courses:
        if course.get('course_type') == 'other':
            # Find the updated version
            catalog_desc = course.get('catalog_description', '')
            if catalog_desc in other_catalog_descs:
                updated_courses.append(other_catalog_descs[catalog_desc])
            else:
                updated_courses.append(course)
        else:
            updated_courses.append(course)

    # Save results
    output_file = 'reclassified_courses_with_topics.json'
    with open(output_file, 'w') as f:
        json.dump(updated_courses, f, indent=2)

    print(f"\n{'='*60}")
    print("Reclassification Summary:")
    print(f"{'='*60}")
    for course_type, count in sorted(reclassified_count.items()):
        print(f"{course_type}: {count} courses")
    print(f"\nResults saved to {output_file}")

    # Print overall distribution
    print(f"\n{'='*60}")
    print("Overall Course Type Distribution:")
    print(f"{'='*60}")
    type_distribution = {}
    for course in updated_courses:
        ctype = course.get('course_type', 'unknown')
        type_distribution[ctype] = type_distribution.get(ctype, 0) + 1

    for ctype, count in sorted(type_distribution.items()):
        print(f"{ctype}: {count} courses")

if __name__ == "__main__":
    main()
