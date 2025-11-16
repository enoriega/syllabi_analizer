import json
import argparse
from typing import Dict, Any, Tuple

def get_dedup_key(entry: Dict[str, Any]) -> Tuple[str, str, int]:
    """
    Create a unique key for deduplication based on:
    - course_name
    - term_offered (semester and academic_year)

    Ignores file name and justifications for comparison purposes.
    """
    course_name = entry.get("course_name", "").strip().lower()

    term = entry.get("term_offered", {})
    if term and isinstance(term, dict):
        semester_val = term.get("semester", "")
        semester = semester_val.strip().lower() if semester_val else ""
        academic_year = term.get("academic_year", 0) or 0
    else:
        semester = ""
        academic_year = 0

    return (course_name, semester, academic_year)


def remove_duplicates(input_file: str, output_file: str):
    """
    Remove duplicate entries from the JSON file based on
    course name and term offered.
    """
    print(f"Reading from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total entries before deduplication: {len(data)}")

    # Track seen entries and keep only the first occurrence
    seen_keys = set()
    unique_entries = []
    duplicate_count = 0

    for entry in data:
        key = get_dedup_key(entry)

        if key not in seen_keys:
            seen_keys.add(key)
            unique_entries.append(entry)
        else:
            duplicate_count += 1

    print(f"Total entries after deduplication: {len(unique_entries)}")
    print(f"Duplicates removed: {duplicate_count}")

    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_entries, f, indent=2, ensure_ascii=False)

    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Remove duplicate entries from parsed syllabi JSON file based on course name and term offered."
    )
    parser.add_argument(
        "-i", "--input",
        default="parsed_syllabi.json",
        help="Input JSON file path (default: parsed_syllabi.json)"
    )
    parser.add_argument(
        "-o", "--output",
        default="parsed_syllabi_dedup.json",
        help="Output JSON file path (default: parsed_syllabi_dedup.json)"
    )

    args = parser.parse_args()

    remove_duplicates(args.input, args.output)
