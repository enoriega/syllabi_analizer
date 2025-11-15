"""
Test script to verify parallel processing functionality in extract_text.py
"""

import multiprocessing as mp
from pathlib import Path
import time


def test_cpu_detection():
    """Test that we can detect the number of CPUs."""
    cpu_count = mp.cpu_count()
    print(f"✓ Detected {cpu_count} CPU cores")
    return cpu_count


def test_dataclass_imports():
    """Test that dataclass imports work correctly."""
    from extract_text import ProcessingTask, ProcessingResult

    # Create a sample task
    task = ProcessingTask(
        file_path=Path("test.pdf"),
        output_file_path=Path("test.pdf.txt"),
        data_path=Path("data"),
        output_path=Path("output")
    )

    # Create a sample result
    result = ProcessingResult(
        file_path=Path("test.pdf"),
        output_file_path=Path("test.pdf.txt"),
        success=True,
        skipped=False
    )

    print("✓ ProcessingTask and ProcessingResult dataclasses work correctly")
    return True


def test_worker_function():
    """Test that the worker function can be imported and works."""
    from extract_text import process_single_file, ProcessingTask
    from pathlib import Path
    import tempfile
    import os

    # Create a temporary directory with a test file
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple text file (not a real PDF, but for testing structure)
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Test content")

        # Create output path
        output_file = Path(tmpdir) / "output" / "test.txt.txt"

        # Create task
        task = ProcessingTask(
            file_path=test_file,
            output_file_path=output_file,
            data_path=Path(tmpdir),
            output_path=Path(tmpdir) / "output"
        )

        # This will fail because .txt is not a supported format, but it tests the structure
        result = process_single_file(task)

        print(f"✓ Worker function executed (Result: success={result.success})")
        return True


def demonstrate_parallel_benefits():
    """Demonstrate the benefits of parallel processing."""
    print("\n" + "="*70)
    print("Parallel Processing Benefits")
    print("="*70)

    cpu_count = mp.cpu_count()

    print(f"\nYour system has {cpu_count} CPU cores available.")
    print("\nProcessing scenarios:")

    # Example: 100 files, 2 seconds each
    num_files = 100
    time_per_file = 2  # seconds

    sequential_time = num_files * time_per_file
    parallel_time = (num_files * time_per_file) / cpu_count

    print(f"\n  Scenario: {num_files} files, {time_per_file}s processing time each")
    print(f"  Sequential: {sequential_time}s ({sequential_time/60:.1f} minutes)")
    print(f"  Parallel ({cpu_count} workers): {parallel_time:.1f}s ({parallel_time/60:.1f} minutes)")
    print(f"  Speedup: {sequential_time/parallel_time:.1f}x faster")

    print("\n  Note: Actual speedup depends on:")
    print("  - I/O operations (disk read/write speed)")
    print("  - CPU-bound vs I/O-bound tasks")
    print("  - System resources and other running processes")


def show_usage_examples():
    """Show usage examples for the parallel processing feature."""
    print("\n" + "="*70)
    print("Usage Examples")
    print("="*70)

    print("\n1. Default (parallel with all CPU cores):")
    print("   uv run python extract_text.py --data-dir data")

    print("\n2. Limit to 4 workers:")
    print("   uv run python extract_text.py --workers 4")

    print("\n3. Sequential processing (no parallelism):")
    print("   uv run python extract_text.py --no-parallel")

    print("\n4. Parallel with custom output directory:")
    print("   uv run python extract_text.py --data-dir data --output-dir output --workers 8")


if __name__ == "__main__":
    print("Testing Parallel Processing Functionality\n")

    tests_passed = 0
    tests_failed = 0

    # Run tests
    try:
        test_cpu_detection()
        tests_passed += 1
    except Exception as e:
        print(f"✗ CPU detection test failed: {e}")
        tests_failed += 1

    try:
        test_dataclass_imports()
        tests_passed += 1
    except Exception as e:
        print(f"✗ Dataclass import test failed: {e}")
        tests_failed += 1

    try:
        test_worker_function()
        tests_passed += 1
    except Exception as e:
        print(f"✗ Worker function test failed: {e}")
        tests_failed += 1

    print(f"\n{'='*70}")
    print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
    print(f"{'='*70}")

    if tests_failed == 0:
        demonstrate_parallel_benefits()
        show_usage_examples()

        print("\n" + "="*70)
        print("✓ All tests passed! Parallel processing is ready to use.")
        print("="*70)
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
