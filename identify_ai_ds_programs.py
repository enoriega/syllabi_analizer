#!/usr/bin/env python3
"""
Script to identify AI and Data Science related programs from ua_programs.json.
Uses LLM to classify programs based on program name and type only.
Outputs a candidates JSON file for manual verification.
"""

import json
import os
import time
from multiprocessing import Pool, Manager
from functools import partial
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

CLASSIFICATION_PROMPT = """You are an expert in identifying academic programs related to AI and Data Science.

Given the following program information, determine if this program is likely to be related to:
- Artificial Intelligence (AI), machine learning, deep learning, neural networks, computer vision, NLP, or robotics
- Data Science, data analytics, statistics, data mining, data visualization, or big data

Program Information:
- Name: {program_name}
- Type: {program_type}

Based ONLY on the program name and type, classify this program:

Respond in JSON format:
{{
    "is_ai_or_ds_related": true or false,
    "confidence": "high", "medium", or "low",
    "reasoning": "Brief explanation in one sentence"
}}

Be inclusive rather than exclusive - if there's a reasonable chance this program involves AI or Data Science, mark it as true.
"""


def classify_program(program_name, program_type, api_key, base_url, model_name):
    """
    Use LLM to determine if a program is AI/DS related based on name and type.
    This function is designed to be called by worker processes.
    """
    try:
        # Initialize LLM (each worker creates its own instance)
        llm = ChatOpenAI(
            model=model_name,
            temperature=0,  # Deterministic responses
            api_key=api_key,
            base_url=base_url,
        )

        # Create and format prompt
        prompt = ChatPromptTemplate.from_template(CLASSIFICATION_PROMPT)
        formatted_prompt = prompt.format(
            program_name=program_name,
            program_type=program_type if program_type else "Not specified"
        )

        # Get response from LLM
        response = llm.invoke(formatted_prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        # Extract JSON from markdown code blocks if present
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)

        return {
            "is_ai_or_ds_related": result.get("is_ai_or_ds_related", False),
            "confidence": result.get("confidence", "low"),
            "reasoning": result.get("reasoning", "Unable to classify")
        }

    except json.JSONDecodeError as e:
        print(f"  Warning: JSON parse error for '{program_name}': {e}")
        return {
            "is_ai_or_ds_related": False,
            "confidence": "low",
            "reasoning": "Failed to parse LLM response"
        }
    except Exception as e:
        print(f"  Warning: Error classifying '{program_name}': {e}")
        return {
            "is_ai_or_ds_related": False,
            "confidence": "low",
            "reasoning": f"Error: {str(e)}"
        }


def process_program(program, api_key, base_url, model_name, progress_dict=None):
    """
    Process a single program: extract info and classify.
    This is the worker function for multiprocessing.
    """
    program_name = program.get('program_name', 'Unknown')
    program_type = program.get('program_type', '')

    # Classify the program
    classification = classify_program(program_name, program_type, api_key, base_url, model_name)

    # Update progress counter
    if progress_dict is not None:
        with progress_dict['lock']:
            progress_dict['completed'] += 1
            completed = progress_dict['completed']
            total = progress_dict['total']
            is_candidate = classification["is_ai_or_ds_related"]

            # Print progress with timestamp
            progress_pct = (completed / total) * 100
            status = "✓ CANDIDATE" if is_candidate else "  Not related"
            print(f"[{completed}/{total} - {progress_pct:.1f}%] {program_name[:60]}: {status}")

    # Return enriched program data
    return {
        **program,
        "is_ai_or_ds_related": classification["is_ai_or_ds_related"],
        "confidence": classification["confidence"],
        "reasoning": classification["reasoning"]
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Identify AI/DS related programs')
    parser.add_argument('--sample', type=int, default=None,
                        help='Test with a sample of N programs')
    args = parser.parse_args()

    input_file = 'ua_programs.json'
    output_file = 'ai_ds_program_candidates.json'

    if args.sample:
        output_file = f'ai_ds_program_candidates_sample_{args.sample}.json'

    print("="*70)
    print("AI/DS Program Identifier")
    print("="*70)
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    if args.sample:
        print(f"Sample size: {args.sample}")
    print()

    # Load programs
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            programs = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found!")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in '{input_file}'!")
        return

    if not programs:
        print("No programs found in input file!")
        return

    # Apply sample if specified
    if args.sample and args.sample > 0:
        import random
        programs = random.sample(programs, min(args.sample, len(programs)))
        print(f"Sampling {len(programs)} programs for testing\n")
    else:
        print(f"Loaded {len(programs)} programs\n")

    # Check for LLM API key
    api_key = os.getenv('LLM_API_KEY')
    base_url = os.getenv('LLM_BASE_URL')
    model_name = os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini')

    if not api_key:
        print("Error: LLM_API_KEY not found in environment!")
        print("Make sure it's set in your .env file.")
        return

    # Process all programs with multiprocessing
    print("Analyzing programs with 10 parallel workers...")
    print("=" * 70)

    start_time = time.time()

    # Setup progress tracking with multiprocessing Manager
    manager = Manager()
    progress_dict = manager.dict()
    progress_dict['completed'] = 0
    progress_dict['total'] = len(programs)
    progress_dict['lock'] = manager.Lock()

    # Create a partial function with fixed parameters
    process_func = partial(process_program,
                          api_key=api_key,
                          base_url=base_url,
                          model_name=model_name,
                          progress_dict=progress_dict)

    # Process programs in parallel
    with Pool(processes=10) as pool:
        enriched_programs = pool.map(process_func, programs)

    elapsed_time = time.time() - start_time

    print("=" * 70)
    print(f"Processing completed in {elapsed_time:.1f} seconds")
    print(f"Average: {elapsed_time/len(programs):.2f} seconds per program\n")

    # Separate into candidates and non-candidates
    candidates = []
    non_candidates = []

    for enriched_program in enriched_programs:
        if enriched_program.get('is_ai_or_ds_related', False):
            candidates.append(enriched_program)
        else:
            non_candidates.append(enriched_program)

    # Save candidates for manual verification
    output_data = {
        "metadata": {
            "total_programs": len(programs),
            "candidates_count": len(candidates),
            "non_candidates_count": len(non_candidates),
            "model_used": os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini')
        },
        "candidates": candidates,
        "non_candidates": non_candidates
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*70}")
    print("Analysis Complete!")
    print(f"{'='*70}")
    print(f"Total programs analyzed: {len(programs)}")
    print(f"AI/DS candidates found: {len(candidates)}")
    print(f"Non-related programs: {len(non_candidates)}")
    print(f"\nResults saved to: {output_file}")

    # Print confidence breakdown
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    for candidate in candidates:
        conf = candidate.get("confidence", "low")
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

    print("\nCandidate Confidence Breakdown:")
    for conf_level in ["high", "medium", "low"]:
        count = confidence_counts.get(conf_level, 0)
        if count > 0:
            percentage = (count / len(candidates)) * 100 if candidates else 0
            print(f"  {conf_level.capitalize()}: {count} ({percentage:.1f}%)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Model: {model_name}")
    print(f"Total programs: {len(enriched_programs)}")
    print(f"AI/DS candidates: {len(candidates)} ({len(candidates)/len(enriched_programs)*100:.1f}%)")
    print(f"Non-related: {len(non_candidates)} ({len(non_candidates)/len(enriched_programs)*100:.1f}%)")
    print(f"Processing time: {elapsed_time:.1f}s ({elapsed_time/len(programs):.2f}s per program)")

    print("\nNext steps:")
    print("  1. Review the candidates in the output file")
    print("  2. Focus on 'high' and 'medium' confidence entries first")
    print("  3. Verify and update the is_ai_or_ds_related flag as needed")


if __name__ == "__main__":
    main()
