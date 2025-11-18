#!/usr/bin/env python3
"""
Script to crawl University of Arizona catalog using saved browser session/cookies.
This approach bypasses CAPTCHA by using a valid browser session.
"""

import json
import time
import pickle
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options


COOKIES_FILE = "ua_catalog_cookies.pkl"


def setup_driver(headless=False):
    """Set up Chrome driver with appropriate options."""
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)

    # Remove webdriver property to avoid detection
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def save_cookies(driver, filepath=COOKIES_FILE):
    """Save cookies to a file."""
    with open(filepath, 'wb') as f:
        pickle.dump(driver.get_cookies(), f)
    print(f"Cookies saved to {filepath}")


def load_cookies(driver, filepath=COOKIES_FILE):
    """Load cookies from a file."""
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                # Add domain if not present
                if 'domain' not in cookie:
                    cookie['domain'] = '.arizona.edu'
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Could not add cookie: {cookie.get('name', 'unknown')}, error: {e}")
        print(f"Cookies loaded from {filepath}")
        return True
    return False


def manual_session_setup():
    """
    Step 1: Manual setup to solve CAPTCHA and save session.
    User will manually solve CAPTCHA and navigate through a few pages.
    """
    print("\n" + "="*70)
    print("MANUAL SESSION SETUP")
    print("="*70)
    print("\nThis will open a browser window. Please:")
    print("1. Solve any CAPTCHA that appears")
    print("2. Navigate to page 2 or 3 to verify the site works")
    print("3. Return here and press Enter to save the session")
    print("\nA browser window will open in 3 seconds...")
    print("="*70 + "\n")

    time.sleep(3)

    driver = setup_driver(headless=False)

    try:
        # Load the main page
        print("Loading https://catalog.arizona.edu/programs...")
        driver.get("https://catalog.arizona.edu/programs?page=1&pq=")

        print("\n" + "="*70)
        print("BROWSER WINDOW OPENED")
        print("="*70)
        print("\nPlease complete these steps in the browser:")
        print("  1. If CAPTCHA appears, solve it")
        print("  2. Once the page loads, click to page 2 or 3")
        print("  3. Verify you can see different programs on each page")
        print("  4. Come back here and press Enter when done")
        print("="*70 + "\n")

        input("Press Enter after you've verified the site works in the browser...")

        # Save cookies
        save_cookies(driver)

        print("\n✓ Session saved successfully!")
        print("You can now close the browser and run the automated crawl.\n")

        return True

    except Exception as e:
        print(f"Error during manual setup: {e}")
        return False
    finally:
        driver.quit()


def get_total_pages(driver):
    """Get the total number of pages from pagination buttons."""
    try:
        # Look for pagination buttons
        pagination_selectors = [
            "button[aria-label*='page']",
            "a[aria-label*='page']",
            ".pagination button",
            ".pagination a",
            "nav button",
            "button[class*='page']",
            "[role='navigation'] button"
        ]

        page_numbers = []

        for selector in pagination_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    text = button.text.strip()
                    aria_label = button.get_attribute('aria-label')

                    # Try to extract page number from text
                    if text.isdigit():
                        page_numbers.append(int(text))

                    # Try to extract from aria-label
                    if aria_label and 'page' in aria_label.lower():
                        import re
                        match = re.search(r'\d+', aria_label)
                        if match:
                            page_numbers.append(int(match.group()))

                if page_numbers:
                    break
            except Exception:
                continue

        if page_numbers:
            max_page = max(page_numbers)
            print(f"  Found pagination: max page = {max_page}")
            return max_page

        return 1

    except Exception as e:
        print(f"  Error getting total pages: {e}")
        return 1


def click_page_button(driver, page_num):
    """Click the pagination button for a specific page number."""
    try:
        # Try different strategies to find the page button

        # Strategy 1: Find by exact text match
        try:
            button = driver.find_element(By.XPATH, f"//button[text()='{page_num}']")
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(0.5)
            button.click()
            print(f"  ✓ Clicked page button: {page_num} (text match)")
            return True
        except NoSuchElementException:
            pass

        # Strategy 2: Find by aria-label
        try:
            button = driver.find_element(By.CSS_SELECTOR, f"button[aria-label='Go to page {page_num}']")
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(0.5)
            button.click()
            print(f"  ✓ Clicked page button: {page_num} (aria-label)")
            return True
        except NoSuchElementException:
            pass

        # Strategy 3: Find in pagination area and match text
        try:
            pagination = driver.find_element(By.CSS_SELECTOR, ".pagination, nav[role='navigation'], [class*='pagination']")
            buttons = pagination.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if button.text.strip() == str(page_num):
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(0.5)
                    button.click()
                    print(f"  ✓ Clicked page button: {page_num} (pagination area)")
                    return True
        except NoSuchElementException:
            pass

        # Strategy 4: Try <a> tags instead of buttons
        try:
            link = driver.find_element(By.XPATH, f"//a[text()='{page_num}']")
            driver.execute_script("arguments[0].scrollIntoView(true);", link)
            time.sleep(0.5)
            link.click()
            print(f"  ✓ Clicked page link: {page_num}")
            return True
        except NoSuchElementException:
            pass

        print(f"  ✗ Could not find page button: {page_num}")
        return False

    except Exception as e:
        print(f"  Error clicking page button {page_num}: {e}")
        return False


def extract_programs_from_page(driver):
    """Extract all program information from the current page."""
    programs = []

    try:
        # Wait for content to load
        time.sleep(2)

        # Wait for program links
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/programs/']"))
            )
        except TimeoutException:
            print("  Timeout waiting for programs to load")
            return programs

        # Find all program links
        program_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/programs/']")

        for link in program_links:
            try:
                program_url = link.get_attribute("href")

                # Skip if not a program detail URL
                if not program_url or "/programs/" not in program_url:
                    continue

                # Skip pagination links
                if "page=" in program_url or "#" in program_url:
                    continue

                # Extract program name
                program_name = link.text.strip()
                if not program_name:
                    continue

                # Extract program type (if in the text)
                program_type = ""
                if "\n" in program_name:
                    parts = program_name.split("\n")
                    if len(parts) == 2:
                        program_name = parts[0].strip()
                        program_type = parts[1].strip()

                programs.append({
                    "program_name": program_name,
                    "program_type": program_type,
                    "catalog_url": program_url
                })

            except Exception as e:
                continue

    except Exception as e:
        print(f"  Error extracting programs: {e}")

    return programs


def crawl_with_session(start_page=1, max_pages=None):
    """
    Step 2: Automated crawl using saved session.
    """
    print("\n" + "="*70)
    print("AUTOMATED CRAWL WITH SAVED SESSION")
    print("="*70 + "\n")

    if not os.path.exists(COOKIES_FILE):
        print(f"ERROR: Cookie file '{COOKIES_FILE}' not found!")
        print("Please run manual setup first: python crawl_programs_with_cookies.py --setup\n")
        return []

    driver = setup_driver(headless=False)  # Keep visible to monitor progress
    all_programs = []

    try:
        # First, navigate to the domain
        print("Initializing session...")
        driver.get("https://catalog.arizona.edu/")
        time.sleep(2)

        # Load saved cookies
        load_cookies(driver)

        # Navigate to programs page with cookies
        print(f"Loading programs page...")
        driver.get("https://catalog.arizona.edu/programs")
        time.sleep(3)

        # Check for CAPTCHA on initial load
        if "captcha" in driver.page_source.lower() or "Human Verification" in driver.title:
            print("  ⚠️  CAPTCHA detected on initial load!")
            print("  Please solve the CAPTCHA in the browser window, then press Enter...")
            input("  Press Enter after solving CAPTCHA...")
            time.sleep(2)

        # Get total number of pages
        total_pages = get_total_pages(driver)
        if max_pages is None or max_pages > total_pages:
            max_pages = total_pages

        print(f"\nStarting crawl from page {start_page} to page {max_pages}...")
        print("="*70 + "\n")

        # If start_page > 1, click to that page
        if start_page > 1:
            print(f"Navigating to starting page {start_page}...")
            if not click_page_button(driver, start_page):
                print(f"  Failed to click page {start_page}, starting from page 1")
                start_page = 1
            else:
                time.sleep(2)  # Wait for page to load

        page_num = start_page
        consecutive_empty = 0
        max_consecutive_empty = 3

        while consecutive_empty < max_consecutive_empty and page_num <= max_pages:
            print(f"\nPage {page_num}/{max_pages}:")

            # Check for CAPTCHA
            if "captcha" in driver.page_source.lower() or "Human Verification" in driver.title:
                print("  ⚠️  CAPTCHA detected!")
                print("  Please solve the CAPTCHA in the browser window, then press Enter...")
                try:
                    input("  Press Enter after solving CAPTCHA...")
                except EOFError:
                    print("  Non-interactive mode, continuing...")
                time.sleep(2)

            # Extract programs
            programs = extract_programs_from_page(driver)

            if programs:
                print(f"  ✓ Found {len(programs)} programs")
                all_programs.extend(programs)
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                print(f"  ✗ No programs found (empty count: {consecutive_empty})")

            # Navigate to next page by clicking button
            page_num += 1
            if consecutive_empty < max_consecutive_empty and page_num <= max_pages:
                print(f"  Navigating to page {page_num}...")
                if click_page_button(driver, page_num):
                    time.sleep(2)  # Wait for page to load
                else:
                    print(f"  Could not click to page {page_num}, stopping.")
                    break

        print(f"\n{'='*70}")
        print(f"Crawl complete! Total programs found: {len(all_programs)}")
        print(f"{'='*70}\n")

        # Deduplicate
        unique_programs = []
        seen_urls = set()
        for program in all_programs:
            if program["catalog_url"] not in seen_urls:
                unique_programs.append(program)
                seen_urls.add(program["catalog_url"])

        print(f"Unique programs: {len(unique_programs)}")

        # Save to JSON
        output_file = "ua_programs.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_programs, f, indent=2, ensure_ascii=False)

        print(f"Programs saved to {output_file}\n")

        return unique_programs

    except Exception as e:
        print(f"Error during automated crawl: {e}")
        import traceback
        traceback.print_exc()
        return all_programs
    finally:
        driver.quit()


if __name__ == "__main__":
    import sys

    if "--setup" in sys.argv:
        # Manual session setup
        success = manual_session_setup()
        if success:
            print("\nNow run the automated crawl:")
            print("  python crawl_programs_with_cookies.py --crawl\n")
    elif "--crawl" in sys.argv:
        # Automated crawl
        start_page = 1
        max_pages = None

        # Check for start page argument
        if "--start" in sys.argv:
            idx = sys.argv.index("--start")
            if idx + 1 < len(sys.argv):
                try:
                    start_page = int(sys.argv[idx + 1])
                except ValueError:
                    print("Invalid start page number, using 1")

        # Check for max pages argument
        if "--max" in sys.argv:
            idx = sys.argv.index("--max")
            if idx + 1 < len(sys.argv):
                try:
                    max_pages = int(sys.argv[idx + 1])
                except ValueError:
                    print("Invalid max page number, will crawl all pages")

        programs = crawl_with_session(start_page=start_page, max_pages=max_pages)

        if programs:
            print("\nSample programs:")
            for program in programs[:5]:
                print(f"  - {program['program_name']}")
                if program['program_type']:
                    print(f"    Type: {program['program_type']}")
                print(f"    URL: {program['catalog_url']}")
    else:
        # Show usage
        print("\n" + "="*70)
        print("UA Catalog Programs Crawler (Cookie-Based)")
        print("="*70)
        print("\nUsage:")
        print("  1. Setup (run once to save session):")
        print("     python crawl_programs_with_cookies.py --setup")
        print("\n  2. Crawl (automated, uses saved session):")
        print("     python crawl_programs_with_cookies.py --crawl")
        print("\n  3. Resume from specific page:")
        print("     python crawl_programs_with_cookies.py --crawl --start 5")
        print("\n  4. Crawl specific range:")
        print("     python crawl_programs_with_cookies.py --crawl --start 10 --max 20")
        print("\n" + "="*70 + "\n")
