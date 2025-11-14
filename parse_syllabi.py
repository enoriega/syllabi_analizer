#!/usr/bin/env python3
"""
Script to parse syllabi text files and extract structured information using an LLM.
Uses LangChain to create a pipeline that processes syllabi and populates Syllabus models.
"""

import os
import json
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models import Syllabus, Term, Semester


# Load environment variables
load_dotenv()


def setup_llm() -> ChatOpenAI:
    """
    Setup the LLM using configuration from .env file.

    Returns:
        Configured ChatOpenAI instance
    """
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL_NAME")
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise ValueError("LLM_API_KEY not found in .env file")
    if not model_name:
        raise ValueError("LLM_MODEL_NAME not found in .env file")

    llm_kwargs = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0.0,  # Use deterministic output
    }

    if base_url:
        llm_kwargs["base_url"] = base_url

    return ChatOpenAI(**llm_kwargs)


def create_parsing_prompt() -> ChatPromptTemplate:
    """
    Create the prompt template for parsing syllabi.

    Returns:
        ChatPromptTemplate for syllabus parsing
    """

    parser = PydanticOutputParser(pydantic_object=Syllabus)

    template = """You are an expert at analyzing academic syllabi. Your task is to extract structured information from a syllabus document.

Given the following information:
- Original filename: {filename}
- File path (directory structure): {file_path}
- Syllabus text content: {content}

Please analyze the syllabus and extract the following information:

1. **Course Name**: Extract the official course name and code (e.g., "CS 229: Machine Learning"). Look for course titles, headers, or official course codes.

2. **Term Offered**: Determine when the course is offered by examining:
   - The filename (which may contain semester/year information)
   - The directory path (which may indicate term structure like "Spring 2023")
   - The syllabus text itself (which may mention the term)
   - Semester should be one of: spring, summer, fall, winter (lowercase)
   - Academic year should be a 4-digit year (e.g., 2023)
   - If you cannot determine semester or year, leave them as null

3. **Course Description**: Extract the course description and learning objectives. Include:
   - The main course description
   - Course objectives
   - Learning outcomes
   - Topics covered
   - Create a comprehensive description (2-4 paragraphs)

4. **AI-Related Classification**: Determine if this course is substantially related to Artificial Intelligence.

   **AI-related topics include but are not limited to:**
   - Machine Learning (supervised, unsupervised, reinforcement learning)
   - Artificial Intelligence (AI fundamentals, AI applications)
   - Neural Networks and Deep Learning
   - Data Mining and Knowledge Discovery
   - Statistical Methods for AI/ML
   - Natural Language Processing (NLP)
   - Computer Vision
   - Autonomous Systems and Robotics
   - Expert Systems and Knowledge Representation
   - Search and Planning Algorithms
   - Intelligent Agents
   - AI Ethics and Responsible AI

   **Important**: AI must play a *substantial* role in the course content to qualify as AI-related.
   - A course that merely uses AI tools is NOT AI-related
   - A course with a single lecture on AI is NOT AI-related
   - A course focused on teaching AI concepts, methods, or applications IS AI-related

   Set `is_ai_related` to true only if AI is a core component of the course.

5. **Justification**: If the course is AI-related, provide a clear 2-3 sentence justification explaining:
   - What AI topics are covered
   - How AI is central to the course
   - Specific AI methods or techniques taught

   If not AI-related, set this to null.

{format_instructions}

Important: Return ONLY the JSON object, with no additional text or explanation.
"""

    prompt = ChatPromptTemplate.from_template(
        template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    return prompt


def parse_syllabus(
    filename: str,
    file_path: str,
    content: str,
    llm: ChatOpenAI,
    prompt: ChatPromptTemplate
) -> Optional[Syllabus]:
    """
    Parse a single syllabus using the LLM pipeline.

    Args:
        filename: The original filename
        file_path: The full file path for context
        content: The text content of the syllabus
        llm: The language model instance
        prompt: The prompt template

    Returns:
        Syllabus object or None if parsing fails
    """
    parser = PydanticOutputParser(pydantic_object=Syllabus)

    try:
        # Create the chain
        chain = prompt | llm | parser

        # Run the chain
        result = chain.invoke({
            "filename": filename,
            "file_path": file_path,
            "content": content
        })

        return result

    except Exception as e:
        print(f"  ✗ Error parsing syllabus: {e}")
        return None


def load_existing_results(output_file: str) -> tuple[List[Syllabus], set[str]]:
    """
    Load existing parsed syllabi from output file if it exists.

    Args:
        output_file: Path to the output JSON file

    Returns:
        Tuple of (list of existing syllabi, set of processed filenames)
    """
    output_path = Path(output_file)

    if not output_path.exists():
        return [], set()

    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert dicts to Syllabus objects
        existing_syllabi = [Syllabus(**item) for item in data]

        # Create set of filenames that have been processed
        processed_filenames = {s.original_file_name for s in existing_syllabi}

        return existing_syllabi, processed_filenames

    except Exception as e:
        print(f"Warning: Could not load existing results from {output_file}: {e}")
        print("Starting fresh...\n")
        return [], set()


def process_syllabi_directory(
    input_dir: str,
    output_file: str = "parsed_syllabi.json",
    max_files: Optional[int] = None
) -> List[Syllabus]:
    """
    Process all .txt files in a directory and extract structured syllabus information.

    Args:
        input_dir: Directory containing .txt syllabus files
        output_file: Output JSON file path
        max_files: Optional limit on number of files to process (for testing)

    Returns:
        List of parsed Syllabus objects
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        raise ValueError(f"Input directory does not exist: {input_dir}")

    # Load existing results to avoid reprocessing
    print(f"Checking for existing results in {output_file}...")
    parsed_syllabi, processed_filenames = load_existing_results(output_file)

    if processed_filenames:
        print(f"Found {len(processed_filenames)} already processed syllabi\n")
    else:
        print("No existing results found, starting fresh\n")

    # Setup LLM and prompt
    print("Setting up LLM...")
    llm = setup_llm()
    prompt = create_parsing_prompt()
    print(f"Using model: {os.getenv('LLM_MODEL_NAME')}\n")

    # Find all .txt files
    txt_files = list(input_path.rglob("*.txt"))

    if max_files:
        txt_files = txt_files[:max_files]

    print(f"Found {len(txt_files)} syllabus files to process\n")

    success_count = 0
    error_count = 0
    skipped_count = 0

    for idx, txt_file in enumerate(txt_files, 1):
        print(f"[{idx}/{len(txt_files)}] Processing: {txt_file.relative_to(input_path)}")

        try:
            # Get the original filename (remove .txt extension)
            original_filename = txt_file.name[:-4] if txt_file.name.endswith('.txt') else txt_file.name

            # Check if already processed
            if original_filename in processed_filenames:
                print(f"  ⊙ Already processed, skipping")
                skipped_count += 1
                print()
                continue

            # Read the syllabus text
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Skip empty files
            if not content.strip():
                print("  ⊙ Skipping empty file")
                print()
                continue

            # Get relative path for context
            relative_path = str(txt_file.relative_to(input_path))

            # Parse the syllabus
            syllabus = parse_syllabus(
                filename=original_filename,
                file_path=relative_path,
                content=content,
                llm=llm,
                prompt=prompt
            )

            if syllabus:
                parsed_syllabi.append(syllabus)
                print(f"  ✓ Successfully parsed")
                print(f"    Course: {syllabus.course_name}")
                print(f"    AI-related: {syllabus.is_ai_related}")
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            error_count += 1

        print()

    # Save results to JSON
    print(f"\nSaving results to {output_file}...")
    output_path = Path(output_file)

    # Convert to dict for JSON serialization
    syllabi_dicts = [s.model_dump() for s in parsed_syllabi]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(syllabi_dicts, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved {len(parsed_syllabi)} parsed syllabi")

    # Print summary
    print(f"\n{'='*60}")
    print("Processing Summary:")
    print(f"  Total files: {len(txt_files)}")
    print(f"  Successfully parsed (new): {success_count}")
    print(f"  Skipped (already processed): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total in output file: {len(parsed_syllabi)}")

    ai_related = sum(1 for s in parsed_syllabi if s.is_ai_related)
    print(f"\nAI-Related Courses: {ai_related}/{len(parsed_syllabi)} ({ai_related/len(parsed_syllabi)*100:.1f}%)" if parsed_syllabi else "\nNo courses parsed")
    print(f"{'='*60}")

    return parsed_syllabi


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse syllabi text files and extract structured information using LLM"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data",
        help="Directory containing .txt syllabus files (default: data)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="parsed_syllabi.json",
        help="Output JSON file path (default: parsed_syllabi.json)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to process (useful for testing)"
    )

    args = parser.parse_args()

    # Check if .env file exists
    if not Path(".env").exists():
        print("Error: .env file not found!")
        print("Please create a .env file based on .env.example")
        print("Required variables: LLM_BASE_URL, LLM_MODEL_NAME, LLM_API_KEY")
        return

    process_syllabi_directory(
        input_dir=args.input_dir,
        output_file=args.output_file,
        max_files=args.max_files
    )


if __name__ == "__main__":
    main()
