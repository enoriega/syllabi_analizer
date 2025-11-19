#!/usr/bin/env python3
"""
Script to classify AI/DS programs into more specific categories.
Classifies programs as: Core AI, Applied AI, Core DS, Applied DS, or Other.
Scrapes program description and requirements from catalog URLs.
"""

import json
import time
import os
import argparse
import random
from multiprocessing import Pool, Manager
from functools import partial
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global driver instance for session reuse (single-threaded mode only)
_global_driver = None


CLASSIFICATION_PROMPT = """You are an expert in classifying academic programs in AI and Data Science. Given a program's information, classify it into ONE of these categories:

1. **Core AI** - The program where AI, Machine Learning, Deep Learning, Neural Networks, Computer Vision, Natural Language Processing, or Robotics with AI are FUNDAMENTAL and PRIMARY subjects of the program. The program's main focus is teaching AI concepts and techniques.

2. **Applied AI** - The program where AI/ML techniques are being APPLIED to solve problems or address challenges in a SPECIFIC field or domain of knowledge (e.g., AI for Business, AI in Healthcare, AI in Agriculture). AI is a major component but serves as a tool for a domain-specific application.

3. **Core DS** - The program where Data Science, Data Analytics, Statistics, Data Mining, Data Visualization, or Big Data are FUNDAMENTAL and PRIMARY subjects of the program. The program's main focus is teaching data science principles and methodologies.

4. **Applied DS** - The program where Data Science techniques are being APPLIED in a PARTICULAR field or niche (e.g., Health Data Science, Business Analytics, Biosystems Analytics). Data Science is a major component but serves as a tool for a domain-specific application.

5. **Other** - The program is related to computing, information systems, or quantitative fields but does NOT primarily focus on AI or Data Science as core or applied subjects. This includes general computer science, software engineering, information systems, statistics (without explicit DS focus), or programs where AI/DS are only minor/tangential components.

Program Information:
- Name: {program_name}
- Type: {program_type}
- Description: {description}
- Requirements: {requirements}

Classification Guidelines:
- Focus on the PRIMARY purpose and core curriculum of the program
- "Core" means AI/DS is the main subject being taught
- "Applied" means AI/DS is being used as a tool in a specific domain
- If AI and DS are equally prominent, prefer the AI category
- If unclear or insufficient information, classify as "Other"

Provide your classification and a detailed justification (3-5 sentences) explaining:
1. Why this category was chosen
2. What key aspects of the program led to this decision
3. What distinguishes it from other categories

Respond in JSON format:
{{
    "classification": "one of: Core AI, Applied AI, Core DS, Applied DS, Other",
    "justification": "your detailed justification here (3-5 sentences)"
}}
"""


def setup_chrome_options():
    """Setup Chrome options with anti-detection measures."""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-position=-2400,-2400")  # Move off-screen
    chrome_options.add_argument("--start-maximized")

    # Additional anti-detection measures
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins-discovery")

    # Rotate user agents
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    selected_ua = random.choice(user_agents)
    chrome_options.add_argument(f"--user-agent={selected_ua}")

    return chrome_options, selected_ua


def fetch_program_content(url, max_retries=3, reuse_driver=False):
    """
    Fetch program description AND program requirements from catalog URL.
    Uses Selenium with anti-detection measures.

    Args:
        url: The catalog URL to fetch
        max_retries: Maximum number of retry attempts
        reuse_driver: If True, reuse global driver session (single-threaded mode only)

    Returns:
        dict with 'description' and 'requirements' keys
    """
    global _global_driver

    chrome_options, selected_ua = setup_chrome_options()

    # Reuse driver if requested (single-threaded mode)
    if reuse_driver and _global_driver is not None:
        driver = _global_driver
        # Random delay to simulate human browsing
        time.sleep(random.uniform(3, 6))
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        # Extract content without creating new driver
        try:
            return extract_content_from_page(driver)
        except Exception:
            return {"description": "N/A", "requirements": "N/A"}

    # Create new driver for each request (multiprocessing mode)
    driver = None
    for attempt in range(max_retries):
        try:
            # Random delay before opening browser
            time.sleep(random.uniform(3, 6))

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

            # Extract content
            result = extract_content_from_page(driver)

            if not reuse_driver and driver:
                driver.quit()

            return result

        except Exception as e:
            if driver and not reuse_driver:
                try:
                    driver.quit()
                except:
                    pass
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"  Failed to fetch {url}: {e}")
                return {"description": "N/A", "requirements": "N/A"}

    return {"description": "N/A", "requirements": "N/A"}


def extract_content_from_page(driver):
    """
    Extract both program description and program requirements from page source.

    Returns:
        dict with 'description' and 'requirements' keys
    """
    result = {"description": "N/A", "requirements": "N/A"}

    try:
        # Wait a bit for JavaScript to render
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Extract Program Description
        description_label = soup.find('h3', class_='field-label',
                                     string=lambda text: text and 'program description' in text.lower())
        if description_label:
            value_div = description_label.find_next_sibling('div', class_='field-value')
            if value_div:
                text = value_div.get_text(strip=True)
                text = ' '.join(text.split())  # Clean up whitespace
                if len(text) > 50:
                    result["description"] = text[:3000]  # Limit to 3000 chars

        # Extract Program Requirements
        # Look for various requirement section headers
        requirement_keywords = [
            'program requirements', 'degree requirements', 'major requirements',
            'curriculum requirements', 'course requirements'
        ]

        for keyword in requirement_keywords:
            req_label = soup.find('h3', class_='field-label',
                                string=lambda text: text and keyword in text.lower())
            if req_label:
                value_div = req_label.find_next_sibling('div', class_='field-value')
                if value_div:
                    text = value_div.get_text(strip=True)
                    text = ' '.join(text.split())
                    if len(text) > 50:
                        result["requirements"] = text[:5000]  # Limit to 5000 chars
                        break

        # If still N/A, try to find any list of courses or requirements
        if result["requirements"] == "N/A":
            # Look for course lists or requirement tables
            all_labels = soup.find_all('h3', class_='field-label')
            for label in all_labels:
                label_text = label.get_text().lower()
                if any(kw in label_text for kw in ['requirement', 'course', 'curriculum']):
                    value_div = label.find_next_sibling('div', class_='field-value')
                    if value_div:
                        text = value_div.get_text(strip=True)
                        text = ' '.join(text.split())
                        if len(text) > 100:  # Require more substantial content for requirements
                            result["requirements"] = text[:5000]
                            break

    except Exception as e:
        print(f"  Error extracting content: {e}")

    return result


def classify_program_with_llm(program_info, description, requirements):
    """
    Use LLM to classify the program into one of the five categories.
    """
    try:
        # Initialize LLM
        llm = ChatOpenAI(
            model=os.getenv('LLM_MODEL_NAME', 'gpt-4o'),
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
            description=description if description != "N/A" else "No description available",
            requirements=requirements if requirements != "N/A" else "No requirements information available"
        )

        # Get response from LLM
        response = llm.invoke(formatted_prompt)

        # Parse JSON response
        content = response.content if hasattr(response, 'content') else str(response)

        # Try to extract JSON from markdown code blocks if present
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)

        return {
            "classification": result.get("classification", "Other"),
            "justification": result.get("justification", "Unable to classify")
        }

    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return {
            "classification": "Other",
            "justification": "Failed to parse LLM response"
        }
    except Exception as e:
        print(f"  LLM error for {program_info.get('program_name', 'Unknown')}: {e}")
        return {
            "classification": "Other",
            "justification": f"Error during classification: {str(e)}"
        }


def process_single_program_simple(program, progress_info=None):
    """
    Process a single program without multiprocessing.
    Allows CAPTCHA interaction and reuses browser session.
    """
    program_name = program.get('program_name', 'Unknown')
    catalog_url = program.get('catalog_url', '')

    if progress_info:
        idx, total = progress_info
        print(f"\n[{idx}/{total}] Processing: {program_name}")
    else:
        print(f"\nProcessing: {program_name}")

    # Fetch description and requirements
    content = fetch_program_content(catalog_url, reuse_driver=True)
    description = content["description"]
    requirements = content["requirements"]

    print(f"  Description: {'✓' if description != 'N/A' else '✗'} ({len(description)} chars)")
    print(f"  Requirements: {'✓' if requirements != 'N/A' else '✗'} ({len(requirements)} chars)")

    # Classify with LLM
    classification_result = classify_program_with_llm(program, description, requirements)

    print(f"  → Classification: {classification_result['classification']}")

    # Create clean output without unwanted fields
    result = {
        'program_name': program.get('program_name'),
        'program_type': program.get('program_type'),
        'catalog_url': program.get('catalog_url'),
        'program_description': description,
        'program_requirements': requirements,
        'ai_ds_classification': classification_result['classification'],
        'classification_justification': classification_result['justification']
    }

    return result


def cleanup_global_driver():
    """Clean up the global driver if it exists."""
    global _global_driver
    if _global_driver is not None:
        try:
            _global_driver.quit()
        except:
            pass
        _global_driver = None


def process_programs(input_file, output_file, limit=None):
    """
    Main function to process all programs.
    Uses single-threaded mode to allow CAPTCHA interaction and session reuse.
    Resumes from existing output file if it exists.
    """
    print("="*70)
    print("AI/DS Program Classifier")
    print("="*70)
    print(f"\nInput: {input_file}")
    print(f"Output: {output_file}")
    if limit:
        print(f"Limit: {limit} programs (testing mode)")
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

    # Load existing results if output file exists
    existing_results = []
    processed_urls = set()

    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                raw_results = json.load(f)
                # Clean existing results by removing unwanted fields
                for prog in raw_results:
                    cleaned = {
                        'program_name': prog.get('program_name'),
                        'program_type': prog.get('program_type'),
                        'catalog_url': prog.get('catalog_url'),
                        'program_description': prog.get('program_description', 'N/A'),
                        'program_requirements': prog.get('program_requirements', 'N/A'),
                        'ai_ds_classification': prog.get('ai_ds_classification', 'Unknown'),
                        'classification_justification': prog.get('classification_justification', '')
                    }
                    existing_results.append(cleaned)
                processed_urls = {p.get('catalog_url') for p in existing_results if p.get('catalog_url')}
                print(f"Found existing output file with {len(existing_results)} processed programs")
                print(f"Resuming from where we left off...\n")
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not read existing output file, starting fresh\n")
            existing_results = []
            processed_urls = set()

    # Filter out already processed programs
    programs_to_process = [p for p in programs if p.get('catalog_url') not in processed_urls]

    if not programs_to_process:
        print("All programs have already been processed!")
        return

    # Apply limit if specified (to remaining programs)
    if limit and limit > 0:
        programs_to_process = programs_to_process[:limit]
        print(f"Processing {len(programs_to_process)} programs (limit applied)\n")
    else:
        print(f"Processing {len(programs_to_process)} remaining programs")
        print(f"Already completed: {len(existing_results)}\n")

    # Check for LLM API key
    if not os.getenv('LLM_API_KEY'):
        print("Warning: LLM_API_KEY not found in environment!")
        print("Make sure it's set in your .env file or environment.\n")

    # Process programs
    print("Starting classification...")
    print("\nNOTE: Running in single-threaded mode with browser session reuse.")
    print("If you see a CAPTCHA, solve it in the browser window.\n")
    print("="*70)

    start_time = time.time()

    try:
        newly_classified = []
        for i, program in enumerate(programs_to_process, 1):
            result = process_single_program_simple(program, (i, len(programs_to_process)))
            newly_classified.append(result)

        # Clean up browser
        cleanup_global_driver()

        elapsed_time = time.time() - start_time

        # Combine existing and new results
        all_classified = existing_results + newly_classified

        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_classified, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print("Classification Complete!")
        print(f"{'='*70}")
        print(f"Newly processed: {len(newly_classified)}")
        print(f"Total programs: {len(all_classified)}")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        if len(programs_to_process) > 0:
            print(f"Average time per program: {elapsed_time/len(programs_to_process):.2f} seconds")
        print(f"\nResults saved to: {output_file}")

        # Print summary statistics
        classifications = {}
        for prog in all_classified:
            cat = prog.get('ai_ds_classification', 'Unknown')
            classifications[cat] = classifications.get(cat, 0) + 1

        print("\nClassification Summary (all programs):")
        for category, count in sorted(classifications.items()):
            percentage = (count / len(all_classified)) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")

        # Show data quality stats for newly processed
        if newly_classified:
            desc_count = sum(1 for p in newly_classified if p.get('program_description', 'N/A') != 'N/A')
            req_count = sum(1 for p in newly_classified if p.get('program_requirements', 'N/A') != 'N/A')

            print("\nData Quality (newly processed):")
            print(f"  Programs with descriptions: {desc_count} ({desc_count/len(newly_classified)*100:.1f}%)")
            print(f"  Programs with requirements: {req_count} ({req_count/len(newly_classified)*100:.1f}%)")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user!")
        cleanup_global_driver()

        # Save partial results if any
        if newly_classified:
            print(f"Saving partial results...")
            all_classified = existing_results + newly_classified
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_classified, f, indent=2, ensure_ascii=False)
            print(f"Progress saved to: {output_file}")
            print(f"  Previously completed: {len(existing_results)}")
            print(f"  Newly processed: {len(newly_classified)}")
            print(f"  Total: {len(all_classified)}")

    except Exception as e:
        print(f"\nError during processing: {e}")
        import traceback
        traceback.print_exc()
        cleanup_global_driver()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Classify AI/DS programs into Core AI, Applied AI, Core DS, Applied DS, or Other.'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='ai_ds_programs_verified.json',
        help='Input JSON file with programs (default: ai_ds_programs_verified.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='ai_ds_programs_classified.json',
        help='Output JSON file for classified programs (default: ai_ds_programs_classified.json)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of programs to process for testing (default: process all)'
    )

    args = parser.parse_args()

    process_programs(args.input, args.output, args.limit)
