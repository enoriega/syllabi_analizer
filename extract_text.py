#!/usr/bin/env python3
"""
Text extraction script using LangChain document loaders.
Processes PDF, Word, PowerPoint, and HTML files from the data directory.
Supports parallel processing using multiprocessing.
"""

import os
import warnings
import multiprocessing as mp
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Suppress PDF parsing warnings (common with malformed PDFs)
warnings.filterwarnings("ignore", message=".*wrong pointing object.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredHTMLLoader,
)


@dataclass
class ProcessingTask:
    """Task for processing a single file."""
    file_path: Path
    output_file_path: Path
    data_path: Path
    output_path: Path


@dataclass
class ProcessingResult:
    """Result of processing a single file."""
    file_path: Path
    output_file_path: Path
    success: bool
    skipped: bool
    error_message: str = ""


def get_loader_for_file(file_path: str):
    """
    Returns the appropriate LangChain loader for a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        A LangChain document loader instance or None if unsupported
    """
    file_extension = Path(file_path).suffix.lower()

    loader_map = {
        '.pdf': PyPDFLoader,
        '.docx': Docx2txtLoader,
        '.doc': UnstructuredWordDocumentLoader,  # Use unstructured for old .doc format
        '.pptx': UnstructuredPowerPointLoader,
        '.ppt': UnstructuredPowerPointLoader,
        '.html': UnstructuredHTMLLoader,
        '.htm': UnstructuredHTMLLoader,
    }

    loader_class = loader_map.get(file_extension)
    if loader_class:
        return loader_class(file_path)
    return None


def extract_text_from_file(file_path: str) -> Tuple[str, bool, str]:
    """
    Extracts text from a file using the appropriate LangChain loader.

    Args:
        file_path: Path to the input file

    Returns:
        Tuple of (extracted_text, success, error_message)
    """
    try:
        loader = get_loader_for_file(file_path)
        if loader is None:
            return "", False, f"Unsupported file type: {Path(file_path).suffix}"

        # Load and extract text from documents
        documents = loader.load()

        # Combine all document pages/sections into a single text
        extracted_text = "\n\n".join([doc.page_content for doc in documents])

        return extracted_text, True, ""

    except Exception as e:
        return "", False, str(e)


def process_single_file(task: ProcessingTask) -> ProcessingResult:
    """
    Process a single file extraction task (worker function for multiprocessing).

    Args:
        task: ProcessingTask containing file and output paths

    Returns:
        ProcessingResult with the outcome
    """
    # Check if output file already exists
    if task.output_file_path.exists():
        return ProcessingResult(
            file_path=task.file_path,
            output_file_path=task.output_file_path,
            success=True,
            skipped=True
        )

    # Extract text
    text, success, error_msg = extract_text_from_file(str(task.file_path))

    if success:
        try:
            # Create output directory if needed
            task.output_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write extracted text
            with open(task.output_file_path, 'w', encoding='utf-8') as f:
                f.write(text)

            return ProcessingResult(
                file_path=task.file_path,
                output_file_path=task.output_file_path,
                success=True,
                skipped=False
            )
        except Exception as e:
            return ProcessingResult(
                file_path=task.file_path,
                output_file_path=task.output_file_path,
                success=False,
                skipped=False,
                error_message=f"Error writing file: {str(e)}"
            )
    else:
        return ProcessingResult(
            file_path=task.file_path,
            output_file_path=task.output_file_path,
            success=False,
            skipped=False,
            error_message=error_msg
        )


def process_directory(
    data_dir: str,
    output_dir: str = None,
    num_workers: Optional[int] = None,
    use_parallel: bool = True
):
    """
    Recursively processes all supported files in the data directory.

    Args:
        data_dir: Root directory containing files to process
        output_dir: Optional output directory (defaults to same as data_dir)
        num_workers: Number of worker processes (defaults to CPU count)
        use_parallel: Whether to use parallel processing (default: True)
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Error: Directory '{data_dir}' does not exist")
        return

    # If no output directory specified, use the data directory
    if output_dir is None:
        output_path = data_path
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    # Supported file extensions
    supported_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.html', '.htm'}

    # Find all supported files recursively
    files_to_process = []
    for ext in supported_extensions:
        files_to_process.extend(data_path.rglob(f"*{ext}"))

    print(f"Found {len(files_to_process)} files to process")

    # Determine number of workers
    if num_workers is None:
        num_workers = mp.cpu_count()

    if use_parallel and len(files_to_process) > 1:
        print(f"Using {num_workers} worker processes for parallel processing\n")
    else:
        print("Using sequential processing\n")

    # Create tasks
    tasks = []
    for file_path in files_to_process:
        # Create output file path preserving directory structure
        relative_path = file_path.relative_to(data_path)

        # Create output filename: original_name.original_ext.txt
        output_filename = f"{file_path.name}.txt"
        output_file_path = output_path / relative_path.parent / output_filename

        tasks.append(ProcessingTask(
            file_path=file_path,
            output_file_path=output_file_path,
            data_path=data_path,
            output_path=output_path
        ))

    # Process files
    if use_parallel and len(tasks) > 1:
        # Parallel processing
        with mp.Pool(processes=num_workers) as pool:
            results = pool.map(process_single_file, tasks)
    else:
        # Sequential processing
        results = [process_single_file(task) for task in tasks]

    # Display results and count statistics
    success_count = 0
    error_count = 0
    skipped_count = 0

    for idx, result in enumerate(results, start=1):
        relative_path = result.file_path.relative_to(data_path)
        print(f"[{idx}/{len(results)}] {'✓' if result.success else '✗'} {relative_path}")

        if result.skipped:
            print(f"  ⊙ Already processed, skipped")
            skipped_count += 1
        elif result.success:
            print(f"  ✓ Saved to: {result.output_file_path.relative_to(output_path)}")
            success_count += 1
        else:
            print(f"  ✗ Error: {result.error_message}")
            error_count += 1

        # Print progress update every 100 files
        if idx % 100 == 0:
            print(f"\n{'='*60}")
            print(f"Progress Update: Processed {idx}/{len(results)} files")
            print(f"  Successfully processed: {success_count}")
            print(f"  Skipped (already exists): {skipped_count}")
            print(f"  Errors: {error_count}")
            print(f"{'='*60}\n")

    print(f"\nProcessing complete:")
    print(f"  Successfully processed: {success_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract text from documents using LangChain with parallel processing"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing files to process (default: data)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for text files (default: same as data-dir)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"Number of worker processes (default: {mp.cpu_count()} = number of CPU cores)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing and use sequential processing"
    )

    args = parser.parse_args()

    process_directory(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        num_workers=args.workers,
        use_parallel=not args.no_parallel
    )


if __name__ == "__main__":
    main()
