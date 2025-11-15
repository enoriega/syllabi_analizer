#!/usr/bin/env python3
"""
Test script to demonstrate parallel parsing functionality.
"""

from pathlib import Path
from parse_syllabi import process_syllabi_directory

def test_parallel_parsing():
    """
    Test parallel parsing with a small number of files.
    """
    print("="*60)
    print("Testing Parallel Parsing")
    print("="*60)
    print()

    # Check if .env exists
    if not Path(".env").exists():
        print("Error: .env file not found!")
        print("This test requires a .env file with LLM configuration.")
        print("Please create a .env file based on .env.example")
        return

    # Test with max 10 files, 3 workers
    print("Testing with 3 workers, max 10 files")
    print("-"*60)

    try:
        results = process_syllabi_directory(
            input_dir="data",
            output_file="test_parallel_results.json",
            max_files=10,
            min_year=2024,
            num_workers=3,
            use_parallel=True
        )

        print()
        print("="*60)
        print("Test Results:")
        print(f"  Processed {len(results)} syllabi successfully")
        print(f"  AI-related: {sum(1 for s in results if s.is_ai_related)}")
        print("="*60)

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_parallel_parsing()
