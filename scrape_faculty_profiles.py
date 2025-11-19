#!/usr/bin/env python3
"""
Script to scrape faculty profile information from University of Arizona profiles.
Extracts bio, interests, and scholarly contributions.
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
import os
from typing import Dict, List, Optional
from urllib.parse import urljoin
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import tempfile
import shutil


def scrape_faculty_profile(url: str) -> Dict:
    """
    Scrape a single faculty profile from UA profiles website.

    Args:
        url: URL of the faculty profile page

    Returns:
        Dictionary containing scraped profile information
    """
    print(f"Scraping: {url}")

    try:
        # Fetch the page
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Initialize result dictionary
        profile = {
            'url': url,
            'name': None,
            'titles': [],
            'contact': {},
            'bio': None,
            'research_interests': [],
            'teaching_interests': [],
            'scholarly_contributions': []
        }

        # Extract name - try multiple possible selectors
        name_elem = soup.find('h1', class_='page-title') or soup.find('h1') or soup.select_one('.person-name')
        if name_elem:
            profile['name'] = name_elem.get_text(strip=True)

        # Extract titles/departments - look for any element containing title/role info
        titles_section = soup.find('div', class_=lambda x: x and 'title' in x.lower())
        if titles_section:
            title_items = titles_section.find_all('div', class_='field-item')
            profile['titles'] = [item.get_text(strip=True) for item in title_items if item.get_text(strip=True)]

        # Alternative: look for title in metadata or structured data
        if not profile['titles']:
            # Try finding titles in list items or other common structures
            title_list = soup.find_all('li', class_=lambda x: x and 'title' in x.lower())
            profile['titles'] = [item.get_text(strip=True) for item in title_list if item.get_text(strip=True)]

        # Extract contact information
        # Phone
        phone_elem = soup.find('a', href=lambda x: x and x.startswith('tel:'))
        if phone_elem:
            profile['contact']['phone'] = phone_elem.get_text(strip=True)

        # Office
        office_elem = soup.find('div', class_=lambda x: x and 'office' in x.lower())
        if office_elem:
            profile['contact']['office'] = office_elem.get_text(strip=True)

        # Email
        email_elem = soup.find('a', href=lambda x: x and x.startswith('mailto:'))
        if email_elem:
            profile['contact']['email'] = email_elem.get('href').replace('mailto:', '') if email_elem.get('href') else email_elem.get_text(strip=True)

        # Extract biography - look for bio section by id or class
        bio_section = soup.find('div', id='bio') or soup.find('section', id='bio') or soup.find('div', class_=lambda x: x and 'bio' in x.lower())
        if bio_section:
            # Get all paragraphs and join them
            paragraphs = bio_section.find_all('p')
            if paragraphs:
                profile['bio'] = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            else:
                profile['bio'] = bio_section.get_text(strip=True)

        # Extract research interests - look for interests section
        research_section = soup.find('div', id='interests') or soup.find('section', id='interests') or soup.find('div', class_=lambda x: x and 'research' in x.lower() and 'interest' in x.lower())
        if research_section:
            # Look for list items or paragraphs
            interest_items = research_section.find_all(['li', 'p', 'div'])
            profile['research_interests'] = [item.get_text(strip=True) for item in interest_items if item.get_text(strip=True) and len(item.get_text(strip=True)) > 10]

        # Extract teaching interests
        teaching_section = soup.find('div', class_=lambda x: x and 'teaching' in x.lower())
        if teaching_section:
            interest_items = teaching_section.find_all(['li', 'p'])
            profile['teaching_interests'] = [item.get_text(strip=True) for item in interest_items if item.get_text(strip=True) and len(item.get_text(strip=True)) > 10]

        # Extract scholarly contributions/publications
        scholarly_section = soup.find('div', id='scholarly-contributions') or soup.find('section', id='scholarly-contributions')
        if scholarly_section:
            # Find all publication entries - look for common patterns
            # Try different structures
            pub_items = scholarly_section.find_all(['li', 'p', 'div'], class_=lambda x: not x or 'item' in x.lower() or 'publication' in x.lower() or 'citation' in x.lower())

            for pub_item in pub_items:
                # Skip containers and headers
                if pub_item.name == 'div' and (pub_item.find('li') or pub_item.find('p')):
                    continue

                pub_text = pub_item.get_text(strip=True)
                # Filter out headers and short non-publication text
                if pub_text and len(pub_text) > 30 and pub_text not in profile['scholarly_contributions']:
                    profile['scholarly_contributions'].append(pub_text)

        print(f"✓ Successfully scraped profile for {profile['name']}")
        return profile

    except requests.RequestException as e:
        print(f"✗ Error fetching {url}: {e}", file=sys.stderr)
        return {'url': url, 'error': str(e)}
    except Exception as e:
        print(f"✗ Error parsing {url}: {e}", file=sys.stderr)
        return {'url': url, 'error': str(e)}


def load_existing_profiles(output_file: str) -> Dict[str, Dict]:
    """
    Load existing profiles from output file.

    Args:
        output_file: Path to existing profiles JSON file

    Returns:
        Dictionary mapping URLs to profile data
    """
    if not os.path.exists(output_file):
        return {}

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            profiles = json.load(f)

        # Create URL to profile mapping
        url_map = {profile['url']: profile for profile in profiles}
        print(f"Loaded {len(url_map)} existing profile(s) from {output_file}")
        return url_map
    except Exception as e:
        print(f"Warning: Could not load existing profiles from {output_file}: {e}", file=sys.stderr)
        return {}


def scrape_and_save_profile(url: str, worker_id: int, temp_dir: str, lock: Lock) -> Dict:
    """
    Scrape a single profile and save it to a worker-specific temp file.

    Args:
        url: URL to scrape
        worker_id: Worker identifier
        temp_dir: Temporary directory for worker files
        lock: Thread lock for file operations

    Returns:
        Scraped profile dictionary
    """
    profile = scrape_faculty_profile(url)

    # Save to worker-specific file
    worker_file = os.path.join(temp_dir, f'worker_{worker_id}.json')

    with lock:
        # Read existing profiles from worker file
        worker_profiles = []
        if os.path.exists(worker_file):
            try:
                with open(worker_file, 'r', encoding='utf-8') as f:
                    worker_profiles = json.load(f)
            except:
                worker_profiles = []

        # Append new profile
        worker_profiles.append(profile)

        # Write back to worker file
        with open(worker_file, 'w', encoding='utf-8') as f:
            json.dump(worker_profiles, f, indent=2, ensure_ascii=False)

    return profile


def scrape_multiple_profiles(urls: List[str], output_file: str, num_workers: int = 5) -> List[Dict]:
    """
    Scrape multiple faculty profiles in parallel using multiple workers.
    Skips URLs that have already been scraped in the output file.
    Each worker saves results incrementally to temporary files.

    Args:
        urls: List of profile URLs to scrape
        output_file: Path to output file (used to check for existing profiles)
        num_workers: Number of parallel workers (default: 5)

    Returns:
        List of profile dictionaries (including existing ones)
    """
    # Load existing profiles
    existing_profiles = load_existing_profiles(output_file)

    # Separate URLs into already scraped and new
    urls_to_scrape = []
    skipped_count = 0

    for url in urls:
        if url in existing_profiles:
            skipped_count += 1
        else:
            urls_to_scrape.append(url)

    if skipped_count > 0:
        print(f"Skipping {skipped_count} already-scraped profile(s)")

    # Start with existing profiles
    all_profiles = list(existing_profiles.values())

    # Scrape new profiles
    if urls_to_scrape:
        print(f"Scraping {len(urls_to_scrape)} new profile(s) using {num_workers} workers...\n")

        # Create temporary directory for worker files
        temp_dir = tempfile.mkdtemp(prefix='faculty_scraper_')
        lock = Lock()

        try:
            # Use ThreadPoolExecutor for parallel scraping
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all tasks
                future_to_url = {}
                for i, url in enumerate(urls_to_scrape):
                    worker_id = i % num_workers
                    future = executor.submit(scrape_and_save_profile, url, worker_id, temp_dir, lock)
                    future_to_url[future] = url

                # Process completed tasks as they finish
                completed = 0
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        profile = future.result()
                        completed += 1
                        print(f"Progress: {completed}/{len(urls_to_scrape)} completed")
                    except Exception as e:
                        print(f"✗ Exception processing {url}: {e}", file=sys.stderr)
                        completed += 1

            # Merge all worker files
            print("\nMerging results from all workers...")
            for worker_file in os.listdir(temp_dir):
                if worker_file.endswith('.json'):
                    worker_path = os.path.join(temp_dir, worker_file)
                    try:
                        with open(worker_path, 'r', encoding='utf-8') as f:
                            worker_profiles = json.load(f)
                            all_profiles.extend(worker_profiles)
                    except Exception as e:
                        print(f"Warning: Could not read worker file {worker_file}: {e}", file=sys.stderr)

        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory: {e}", file=sys.stderr)

    else:
        print("No new profiles to scrape. All URLs already processed.")

    return all_profiles


def save_profiles(profiles: List[Dict], output_file: str):
    """
    Save scraped profiles to a JSON file.

    Args:
        profiles: List of profile dictionaries
        output_file: Output file path
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(profiles)} profiles to {output_file}")


def main():
    """Main execution function."""
    # Test URL
    test_url = "https://profiles.arizona.edu/person/aaronmason"

    # Default values
    num_workers = 5
    output_file = 'faculty_profiles.json'
    urls = []

    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == '--file':
            # Read URLs from file
            if i + 1 >= len(sys.argv):
                print("Error: --file requires a filename")
                print("Usage: python scrape_faculty_profiles.py --file <urls_file> [--output <output_file>] [--workers <num>]")
                sys.exit(1)
            urls_file = sys.argv[i + 1]
            i += 2

            with open(urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        elif arg == '--output':
            if i + 1 >= len(sys.argv):
                print("Error: --output requires a filename")
                sys.exit(1)
            output_file = sys.argv[i + 1]
            i += 2

        elif arg == '--workers':
            if i + 1 >= len(sys.argv):
                print("Error: --workers requires a number")
                sys.exit(1)
            try:
                num_workers = int(sys.argv[i + 1])
                if num_workers < 1:
                    print("Error: --workers must be at least 1")
                    sys.exit(1)
            except ValueError:
                print("Error: --workers must be a number")
                sys.exit(1)
            i += 2

        elif arg.startswith('http'):
            # Direct URL argument
            urls.append(arg)
            i += 1

        else:
            print(f"Unknown argument: {arg}")
            print("Usage:")
            print("  python scrape_faculty_profiles.py <url1> <url2> ...")
            print("  python scrape_faculty_profiles.py --file <urls_file> [--output <output_file>] [--workers <num>]")
            sys.exit(1)

    # If no URLs provided, use test URL
    if not urls:
        print("No URLs provided. Using test URL.")
        print("Usage:")
        print("  python scrape_faculty_profiles.py <url1> <url2> ...")
        print("  python scrape_faculty_profiles.py --file <urls_file> [--output <output_file>] [--workers <num>]")
        print("\nRunning test with sample URL...\n")
        urls = [test_url]

    # Scrape profiles
    print(f"Processing {len(urls)} URL(s) with {num_workers} worker(s)...\n")
    profiles = scrape_multiple_profiles(urls, output_file, num_workers)

    # Save to JSON
    save_profiles(profiles, output_file)

    # Print summary
    print(f"\nSummary:")
    print(f"  Total profiles: {len(profiles)}")
    print(f"  Successful: {len([p for p in profiles if 'error' not in p])}")
    print(f"  Failed: {len([p for p in profiles if 'error' in p])}")


if __name__ == '__main__':
    main()
