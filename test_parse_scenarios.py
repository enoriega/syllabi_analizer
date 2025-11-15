#!/usr/bin/env python3
"""
Comprehensive test script for parse_syllabi.py scenarios.
Tests various edge cases and configurations.
"""

import sys
import subprocess
from pathlib import Path


def run_test(description, args, expect_success=True):
    """Run a test case with parse_syllabi.py"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")

    cmd = ["uv", "run", "python", "parse_syllabi.py"] + args
    print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✓ Test passed (exit code 0)")
            if "error" in result.stderr.lower() and "Error:" not in result.stdout:
                print("⚠ Warning: stderr contains error messages")
                print(result.stderr[:200])
            return True
        else:
            print(f"✗ Test failed (exit code {result.returncode})")
            print(f"STDERR: {result.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ Test failed (timeout)")
        return False
    except Exception as e:
        print(f"✗ Test failed (exception): {e}")
        return False


def main():
    """Run all test scenarios"""

    print("="*60)
    print("parse_syllabi.py - Comprehensive Test Suite")
    print("="*60)

    # Check if .env exists
    if not Path(".env").exists():
        print("\n⚠ WARNING: .env file not found")
        print("Some tests will fail without LLM configuration")
        print("This is expected if you haven't set up API credentials yet\n")

    tests_passed = 0
    tests_total = 0

    # Test 1: Help command
    tests_total += 1
    if run_test(
        "Display help message",
        ["--help"]
    ):
        tests_passed += 1

    # Test 2: No files (parallel mode)
    tests_total += 1
    if run_test(
        "Parallel mode with no files to process",
        ["--max-files", "2", "--workers", "2", "--min-year", "2020"]
    ):
        tests_passed += 1

    # Test 3: No files (sequential mode)
    tests_total += 1
    if run_test(
        "Sequential mode with no files to process",
        ["--max-files", "1", "--no-parallel", "--min-year", "2020"]
    ):
        tests_passed += 1

    # Test 4: High year filter (should skip all)
    tests_total += 1
    if run_test(
        "High year filter (2099) should skip all files",
        ["--max-files", "10", "--min-year", "2099", "--workers", "2"]
    ):
        tests_passed += 1

    # Test 5: Different worker counts
    tests_total += 1
    if run_test(
        "Custom worker count (3 workers)",
        ["--max-files", "5", "--workers", "3", "--min-year", "2025"]
    ):
        tests_passed += 1

    # Test 6: Single worker
    tests_total += 1
    if run_test(
        "Single worker mode",
        ["--max-files", "2", "--workers", "1", "--min-year", "2025"]
    ):
        tests_passed += 1

    # Clean up test output
    try:
        Path("parsed_syllabi.json").unlink(missing_ok=True)
        print("\n✓ Cleaned up test files")
    except Exception as e:
        print(f"\n⚠ Could not clean up: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    print(f"Success rate: {tests_passed/tests_total*100:.1f}%")
    print(f"{'='*60}\n")

    if tests_passed == tests_total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {tests_total - tests_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
