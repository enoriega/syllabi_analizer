#!/usr/bin/env python3
"""
Text extraction script using LangChain document loaders.
Processes PDF, Word, PowerPoint, and HTML files from the data directory.
"""

import os
from pathlib import Path
from typing import List, Tuple

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredHTMLLoader,
)


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


def process_directory(data_dir: str, output_dir: str = None):
    """
    Recursively processes all supported files in the data directory.

    Args:
        data_dir: Root directory containing files to process
        output_dir: Optional output directory (defaults to same as data_dir)
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

    print(f"Found {len(files_to_process)} files to process\n")

    success_count = 0
    error_count = 0
    skipped_count = 0

    for file_path in files_to_process:
        print(f"Processing: {file_path.relative_to(data_path)}")

        # Create output file path preserving directory structure
        relative_path = file_path.relative_to(data_path)

        # Create output filename: original_name.original_ext.txt
        output_filename = f"{file_path.name}.txt"
        output_file_path = output_path / relative_path.parent / output_filename

        # Check if output file already exists
        if output_file_path.exists():
            print(f"  ⊙ Already processed, skipping")
            skipped_count += 1
            print()
            continue

        # Extract text
        text, success, error_msg = extract_text_from_file(str(file_path))

        if success:
            # Create output directory if needed
            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write extracted text
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(text)

            print(f"  ✓ Saved to: {output_file_path.relative_to(output_path)}")
            success_count += 1
        else:
            print(f"  ✗ Error: {error_msg}")
            error_count += 1

        print()

    print(f"\nProcessing complete:")
    print(f"  Successfully processed: {success_count}")
    print(f"  Skipped (already exists): {skipped_count}")
    print(f"  Errors: {error_count}")


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract text from documents using LangChain"
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

    args = parser.parse_args()

    process_directory(args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
