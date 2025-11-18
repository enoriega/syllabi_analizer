#!/usr/bin/env python3
"""
Script to classify UA programs as AI-focused, Data Science-focused, or unrelated.
Crawls program catalog pages, extracts descriptions, and uses LLM for classification.
"""

import json
import time
import os
import argparse
from multiprocessing import Pool, Manager
from functools import partial
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global driver instance for session reuse (single-threaded mode only)
_global_driver = None


CLASSIFICATION_PROMPT = """You are an expert in classifying academic programs. Given a program's information, classify it into one of these categories:

1. **AI focused** - The program primarily focuses on artificial intelligence, machine learning, deep learning, neural networks, computer vision, natural language processing, or robotics with AI components.

2. **Data Science focused** - The program primarily focuses on data science, data analytics, statistics, data mining, data visualization, or big data (without heavy AI/ML focus).

3. **Unrelated to AI/DS** - The program is not primarily focused on AI or Data Science, though it may mention them tangentially.

4. **I don't know** - There's insufficient information to make a classification, or the program description is missing/unclear.

Program Information:
- Name: {program_name}
- Type: {program_type}
- Description: {description}

Provide your classification and a brief justification (2-3 sentences max).

Respond in JSON format:
{{
    "classification": "one of: AI focused, Data Science focused, Unrelated to AI/DS, I don't know",
    "justification": "your justification here"
}}
"""


def fetch_program_description(url, max_retries=3, reuse_driver=False):
    """
    Fetch and extract the program description from the catalog URL using Selenium.
    Looks for text under "Program Description" heading only.
    Runs in non-headless mode to avoid CAPTCHA.

    Args:
        url: The URL to fetch
        max_retries: Maximum number of retry attempts
        reuse_driver: If True, reuse global driver session (single-threaded mode only)
    """
    global _global_driver
    chrome_options = Options()
    # Don't run headless to avoid CAPTCHA
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-position=-2400,-2400")  # Move off-screen

    # Additional anti-detection measures
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins-discovery")
    chrome_options.add_argument("--start-maximized")

    # Rotate user agents to appear more natural
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    import random
    selected_ua = random.choice(user_agents)
    chrome_options.add_argument(f"--user-agent={selected_ua}")

    import random

    # Reuse driver if requested (single-threaded mode)
    if reuse_driver and _global_driver is not None:
        driver = _global_driver
        # Random delay to simulate human browsing
        time.sleep(random.uniform(2, 5))
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        # Extract description without creating new driver
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            description_label = soup.find('h3', class_='field-label',
                                         string=lambda text: text and 'program description' in text.lower())
            if description_label:
                value_div = description_label.find_next_sibling('div', class_='field-value')
                if value_div:
                    text = value_div.get_text(strip=True)
                    text = ' '.join(text.split())
                    if len(text) > 50:
                        return text[:2000]
            return "N/A"
        except Exception:
            return "N/A"

    # Create new driver for each request (multiprocessing mode)
    driver = None
    for attempt in range(max_retries):
        try:
            # Random delay before opening browser (between 2-5 seconds)
            time.sleep(random.uniform(2, 5))

            driver = webdriver.Chrome(options=chrome_options)

            # Store as global if reuse_driver enabled
            if reuse_driver and _global_driver is None:
                _global_driver = driver

            # Hide automation indicators using CDP commands
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": selected_ua
            })
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Additional stealth techniques
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'MacIntel'
                });
                window.chrome = { runtime: {} };
            """)

            driver.get(url)

            # Random wait time to simulate human behavior
            time.sleep(random.uniform(2, 4))

            # Try to find "Program Description" section using multiple strategies
            try:
                # Wait a bit more for JavaScript to render
                time.sleep(1)

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # Strategy 1: Look for "Program Description" heading and following content
                description_label = soup.find('h3', class_='field-label', string=lambda text: text and 'program description' in text.lower())

                if description_label:
                    # Get the next sibling which should be the field-value
                    value_div = description_label.find_next_sibling('div', class_='field-value')
                    if value_div:
                        text = value_div.get_text(strip=True)
                        text = ' '.join(text.split())  # Clean up whitespace

                        if len(text) > 50:  # Minimum viable content
                            if not reuse_driver:
                                driver.quit()
                            return text[:2000]  # Limit to 2000 chars

                # Strategy 2: Find all field-label/field-value pairs and match
                all_labels = soup.find_all('h3', class_='field-label')
                for label in all_labels:
                    if 'program description' in label.get_text().lower():
                        value_div = label.find_next_sibling('div', class_='field-value')
                        if value_div:
                            text = value_div.get_text(strip=True)
                            text = ' '.join(text.split())

                            if len(text) > 50:
                                if not reuse_driver:
                                    driver.quit()
                                return text[:2000]

                # Strategy 3: Look in the parent div containing both label and value
                field_components = soup.find_all('div', class_='field-component')
                for component in field_components:
                    label = component.find('h3', class_='field-label')
                    if label and 'program description' in label.get_text().lower():
                        value_div = component.find('div', class_='field-value')
                        if value_div:
                            text = value_div.get_text(strip=True)
                            text = ' '.join(text.split())

                            if len(text) > 50:
                                if not reuse_driver:
                                    driver.quit()
                                return text[:2000]

            except Exception as e:
                pass

            # If we couldn't find program description, return N/A
            if not reuse_driver and driver:
                driver.quit()
            return "N/A"

        except Exception as e:
            if driver and not reuse_driver:
                driver.quit()
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"  Failed to fetch {url}: {e}")
                return "N/A"

    return "N/A"


def classify_program_with_llm(program_info, description):
    """
    Use LLM to classify the program based on its information and description.
    """
    try:
        # Initialize LLM
        llm = ChatOpenAI(
            model=os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini'),
            temperature=0,  # Deterministic responses
            api_key=os.getenv('LLM_API_KEY'),
            base_url=os.getenv('LLM_BASE_URL'),
        )

        # Create prompt
        prompt = ChatPromptTemplate.from_template(CLASSIFICATION_PROMPT)

        # Format the prompt
        formatted_prompt = prompt.format(
            program_name=program_info.get('program_name', 'Unknown'),
            program_type=program_info.get('program_type', 'Unknown'),
            description=description
        )

        # Get response from LLM
        response = llm.invoke(formatted_prompt)

        # Parse JSON response
        # Handle different response formats
        content = response.content if hasattr(response, 'content') else str(response)

        # Try to extract JSON from markdown code blocks if present
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)

        return {
            "classification": result.get("classification", "I don't know"),
            "justification": result.get("justification", "Unable to classify")
        }

    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "classification": "I don't know",
            "justification": "Failed to parse LLM response"
        }
    except Exception as e:
        print(f"  LLM error for {program_info.get('program_name', 'Unknown')}: {e}")
        return {
            "classification": "I don't know",
            "justification": f"Error during classification: {str(e)}"
        }


def process_single_program(program, progress_dict):
    """
    Process a single program: fetch description, classify with LLM.
    This is the unit of work for multiprocessing.
    """
    program_name = program.get('program_name', 'Unknown')
    catalog_url = program.get('catalog_url', '')

    # Fetch description (runs in non-headless mode to avoid CAPTCHA)
    description = fetch_program_description(catalog_url)

    # Classify with LLM (no additional delay needed, already have 1s delay in fetch)
    classification_result = classify_program_with_llm(program, description)

    # Update progress
    with progress_dict['lock']:
        progress_dict['completed'] += 1
        total = progress_dict['total']
        completed = progress_dict['completed']
        print(f"[{completed}/{total}] {program_name[:50]}: {classification_result['classification']}")

    # Return enriched program data
    return {
        **program,
        'description': description,
        'classification': classification_result['classification'],
        'justification': classification_result['justification']
    }


def process_single_program_simple(program):
    """
    Process a single program without multiprocessing.
    This allows CAPTCHA interaction in terminal and reuses browser session.
    """
    program_name = program.get('program_name', 'Unknown')
    catalog_url = program.get('catalog_url', '')

    # Fetch description with session reuse (runs in non-headless mode, can show CAPTCHA prompts)
    description = fetch_program_description(catalog_url, reuse_driver=True)

    # Classify with LLM (no additional delay needed, already have delays in fetch)
    classification_result = classify_program_with_llm(program, description)

    # Return enriched program data
    return {
        **program,
        'description': description,
        'classification': classification_result['classification'],
        'justification': classification_result['justification']
    }


def process_programs(input_file, output_file, num_workers=10, limit=None):
    """
    Main function to process all programs with multiprocessing.
    Uses single-threaded mode (workers=1) to allow CAPTCHA interaction.
    """
    print("="*70)
    print("UA Program Classifier")
    print("="*70)
    print(f"\nInput: {input_file}")
    print(f"Output: {output_file}")
    print(f"Workers: {num_workers}")
    if limit:
        print(f"Limit: {limit} programs")
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

    # Apply limit if specified
    if limit and limit > 0:
        programs = programs[:limit]
        print(f"Limited to first {len(programs)} programs\n")
    else:
        print(f"Loaded {len(programs)} programs\n")

    # Check for LLM API key
    if not os.getenv('LLM_API_KEY'):
        print("Warning: LLM_API_KEY not found in environment!")
        print("Make sure it's set in your .env file or environment.\n")

    # Process programs
    print("Starting classification...\n")
    start_time = time.time()

    if num_workers == 1:
        # Single-threaded mode - allows CAPTCHA interaction
        classified_programs = []
        for i, program in enumerate(programs, 1):
            print(f"[{i}/{len(programs)}] Processing: {program.get('program_name', 'Unknown')[:50]}")
            result = process_single_program_simple(program)
            classified_programs.append(result)
            print(f"  → {result['classification']}")
    else:
        # Multi-threaded mode - faster but no CAPTCHA interaction
        print("Note: Using multiprocessing. If you encounter CAPTCHAs, run with --workers 1\n")
        manager = Manager()
        progress_dict = manager.dict()
        progress_dict['completed'] = 0
        progress_dict['total'] = len(programs)
        progress_dict['lock'] = manager.Lock()

        with Pool(processes=num_workers) as pool:
            # Use partial to pass progress_dict to each worker
            process_func = partial(process_single_program, progress_dict=progress_dict)
            classified_programs = pool.map(process_func, programs)

    elapsed_time = time.time() - start_time

    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(classified_programs, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print("Classification Complete!")
    print(f"{'='*70}")
    print(f"Total programs: {len(classified_programs)}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    print(f"Average time per program: {elapsed_time/len(programs):.2f} seconds")
    print(f"\nResults saved to: {output_file}")

    # Print summary statistics
    classifications = {}
    for prog in classified_programs:
        cat = prog.get('classification', 'Unknown')
        classifications[cat] = classifications.get(cat, 0) + 1

    print("\nClassification Summary:")
    for category, count in sorted(classifications.items()):
        percentage = (count / len(classified_programs)) * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Classify UA programs as AI-focused, Data Science-focused, or unrelated.'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='ua_programs.json',
        help='Input JSON file with programs (default: ua_programs.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='ua_programs_classified.json',
        help='Output JSON file for classified programs (default: ua_programs_classified.json)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=10,
        help='Number of worker processes (default: 10)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of programs to process (useful for testing, default: process all)'
    )

    args = parser.parse_args()

    process_programs(args.input, args.output, args.workers, args.limit)
