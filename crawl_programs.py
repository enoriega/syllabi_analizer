#!/usr/bin/env python3
"""
Script to crawl University of Arizona catalog and enumerate all programs.
Saves program name, type, and URL to a JSON file.
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options


def setup_driver(headless=False):
    """Set up Chrome driver with appropriate options."""
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless")  # Run in headless mode

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


def scroll_to_load_all(driver):
    """Scroll to the bottom of the page to trigger lazy loading."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    max_attempts = 20

    while scroll_attempts < max_attempts:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for content to load

        # Calculate new scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")

        # If heights are the same, we might be at the bottom
        if new_height == last_height:
            # Try scrolling a bit more and wait
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

            # Check one more time
            final_height = driver.execute_script("return document.body.scrollHeight")
            if final_height == new_height:
                break

        last_height = new_height
        scroll_attempts += 1
        print(f"Scroll attempt {scroll_attempts}, height: {new_height}")

    print(f"Finished scrolling after {scroll_attempts} attempts")


def extract_programs_from_page(driver, page_num=1):
    """Extract all program information from the current page."""
    programs = []

    try:
        # Wait for initial content to load
        time.sleep(2)

        # Try multiple strategies to find program elements
        selectors_to_try = [
            "a[href*='/programs/']",
            "div.card a",
            "a.card",
            "div[class*='program'] a",
            ".programs-list a",
        ]

        program_links = []
        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    program_links = elements
                    print(f"Found {len(elements)} elements with selector: {selector}")
                    break
            except Exception:
                continue

        if not program_links:
            # Try XPath as fallback
            try:
                program_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/programs/')]")
                print(f"Found {len(program_links)} elements with XPath")
            except Exception:
                pass

        # Get page source for debugging
        if not program_links and page_num == 1:
            page_source = driver.page_source
            with open("page_source_debug.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            print("Saved page source to page_source_debug.html for debugging")

        for link in program_links:
            try:
                # Extract URL
                program_url = link.get_attribute("href")

                # Skip if not a program URL
                if not program_url or "/programs/" not in program_url:
                    continue

                # Skip pagination links
                if "page=" in program_url or "#" in program_url:
                    continue

                # Extract program name from text content
                program_name = link.text.strip()

                # Try to get from title attribute if text is empty
                if not program_name:
                    program_name = link.get_attribute("title")

                # Try to get from child elements
                if not program_name:
                    try:
                        program_name = link.find_element(By.CSS_SELECTOR, "h3, h2, h4, .title, .program-name").text.strip()
                    except NoSuchElementException:
                        pass

                # Extract program type (if available)
                program_type = ""
                try:
                    type_elem = link.find_element(By.CSS_SELECTOR, ".subtitle, .program-type, .degree-type")
                    program_type = type_elem.text.strip()
                except NoSuchElementException:
                    pass

                # Try to extract type from the program name if it contains parentheses
                if not program_type and program_name:
                    if "(" in program_name and ")" in program_name:
                        start = program_name.rfind("(")
                        end = program_name.rfind(")")
                        program_type = program_name[start+1:end].strip()

                if program_name and program_url:
                    programs.append({
                        "program_name": program_name,
                        "program_type": program_type,
                        "catalog_url": program_url
                    })

            except (StaleElementReferenceException, NoSuchElementException) as e:
                continue
            except Exception as e:
                print(f"Error extracting program info: {e}")
                continue

    except TimeoutException:
        print("Timeout waiting for programs to load")
    except Exception as e:
        print(f"Error in extract_programs_from_page: {e}")

    return programs


def navigate_to_page(driver, page_num):
    """Navigate to a specific page number."""
    try:
        # Use the correct URL format with page parameter and pq parameter
        url = f"https://catalog.arizona.edu/programs?page={page_num}&pq="
        print(f"  Navigating to: {url}")
        driver.get(url)

        # Wait longer for page to fully load and JS to execute
        time.sleep(5)

        # Wait for program links to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/programs/']"))
            )
        except TimeoutException:
            print(f"  Timeout waiting for programs to load on page {page_num}")

        # Debug: check if CAPTCHA reappeared
        if "Human Verification" in driver.title or "captcha" in driver.page_source.lower():
            print(f"  WARNING: CAPTCHA detected on page {page_num}!")
            return False

        current_url = driver.current_url
        print(f"  Current URL: {current_url}")

        # Check if we actually navigated to the requested page
        if f"page={page_num}" not in current_url:
            print(f"  WARNING: URL doesn't contain page={page_num}, might be redirected")

        return True

    except Exception as e:
        print(f"Error navigating to page {page_num}: {e}")
        return False


def get_page_numbers(driver):
    """Get all available page numbers from pagination."""
    try:
        time.sleep(2)

        # Try to find pagination elements
        page_selectors = [
            "a[href*='page=']",
            ".pagination a",
            "nav a[href*='page']",
            "button[data-page]"
        ]

        page_numbers = set()

        for selector in page_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    # Try to extract page number from href
                    href = elem.get_attribute("href")
                    if href and "page=" in href:
                        try:
                            page_num = int(href.split("page=")[1].split("&")[0])
                            page_numbers.add(page_num)
                        except (ValueError, IndexError):
                            pass

                    # Try to extract from text
                    text = elem.text.strip()
                    if text.isdigit():
                        page_numbers.add(int(text))
            except Exception:
                continue

        return sorted(list(page_numbers))

    except Exception as e:
        print(f"Error getting page numbers: {e}")
        return []


def try_letter_filters(driver):
    """Try to find and click letter filter buttons (A-Z navigation)."""
    letters_found = []

    try:
        # Look for letter filter buttons
        letter_selectors = [
            "button[data-letter]",
            "a[data-letter]",
            ".letter-filter button",
            ".letter-filter a",
            "button.letter",
            "a.letter"
        ]

        for selector in letter_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for elem in elements:
                        letter = elem.text.strip()
                        if len(letter) == 1 and letter.isalpha():
                            letters_found.append(letter)
                    if letters_found:
                        print(f"Found letter filters: {', '.join(sorted(set(letters_found)))}")
                        return sorted(set(letters_found))
            except Exception:
                continue

        # Try finding "All" button and see if there are letter options
        try:
            all_button = driver.find_element(By.XPATH, "//button[contains(text(), 'All')]")
            parent = all_button.find_element(By.XPATH, "..")
            letter_buttons = parent.find_elements(By.TAG_NAME, "button")
            for btn in letter_buttons:
                text = btn.text.strip()
                if len(text) == 1 and text.isalpha():
                    letters_found.append(text)
            if letters_found:
                return sorted(set(letters_found))
        except Exception:
            pass

    except Exception as e:
        print(f"Error finding letter filters: {e}")

    return []


def click_letter_filter(driver, letter):
    """Click on a letter filter button."""
    try:
        # Try different ways to click the letter
        selectors = [
            f"button[data-letter='{letter}']",
            f"a[data-letter='{letter}']",
            f"//button[text()='{letter}']",
            f"//a[text()='{letter}']"
        ]

        for selector in selectors[:2]:  # CSS selectors
            try:
                elem = driver.find_element(By.CSS_SELECTOR, selector)
                elem.click()
                time.sleep(2)
                return True
            except Exception:
                continue

        for selector in selectors[2:]:  # XPath selectors
            try:
                elem = driver.find_element(By.XPATH, selector)
                elem.click()
                time.sleep(2)
                return True
            except Exception:
                continue

        return False

    except Exception as e:
        print(f"Error clicking letter {letter}: {e}")
        return False


def crawl_programs(headless=False, skip_captcha_check=False):
    """Main function to crawl all programs."""
    driver = setup_driver(headless=headless)
    all_programs = []

    try:
        print("Loading programs page...")
        driver.get("https://catalog.arizona.edu/programs?page=1&pq=")

        # Wait for page to load
        time.sleep(5)

        # Check if CAPTCHA is present
        if not skip_captcha_check and ("Human Verification" in driver.title or "captcha" in driver.page_source.lower()):
            if not headless:
                print("\n" + "="*60)
                print("CAPTCHA DETECTED!")
                print("Please solve the CAPTCHA in the browser window.")
                print("After solving it, press Enter here to continue...")
                print("="*60 + "\n")
                try:
                    input("Press Enter after solving the CAPTCHA...")
                except EOFError:
                    print("Running in non-interactive mode, continuing anyway...")
                time.sleep(3)
            else:
                print("ERROR: CAPTCHA detected, but running in headless mode.")
                print("Please run with headless=False to solve the CAPTCHA manually.")
                return []

        # Check for letter filters
        letters = try_letter_filters(driver)

        if letters:
            print(f"Found {len(letters)} letter filters, will iterate through each")
            for letter in letters:
                print(f"\nScraping programs starting with '{letter}'...")
                if click_letter_filter(driver, letter):
                    time.sleep(2)
                    programs = extract_programs_from_page(driver, 1)
                    print(f"Found {len(programs)} programs for letter '{letter}'")
                    all_programs.extend(programs)
        else:
            # No letter filters, iterate through pages sequentially
            print("No letter filters found, iterating through pages...")

            page_num = 1
            consecutive_empty = 0
            max_consecutive_empty = 3  # Stop after 3 consecutive empty pages

            while consecutive_empty < max_consecutive_empty:
                print(f"Scraping page {page_num}...")

                if navigate_to_page(driver, page_num):
                    programs = extract_programs_from_page(driver, page_num)

                    if programs:
                        print(f"Found {len(programs)} programs on page {page_num}")
                        all_programs.extend(programs)
                        consecutive_empty = 0  # Reset counter when we find programs
                    else:
                        consecutive_empty += 1
                        print(f"No programs found on page {page_num} (empty count: {consecutive_empty})")

                    page_num += 1
                    time.sleep(1.5)  # Be respectful with requests

                    # Safety limit
                    if page_num > 100:
                        print("Reached maximum page limit (100)")
                        break
                else:
                    print(f"Failed to navigate to page {page_num}")
                    break

        print(f"\nTotal programs found: {len(all_programs)}")

        # Remove duplicates based on URL
        unique_programs = []
        seen_urls = set()
        for program in all_programs:
            if program["catalog_url"] not in seen_urls:
                unique_programs.append(program)
                seen_urls.add(program["catalog_url"])

        print(f"Unique programs: {len(unique_programs)}")

        # Save to JSON file
        output_file = "ua_programs.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_programs, f, indent=2, ensure_ascii=False)

        print(f"\nPrograms saved to {output_file}")

        return unique_programs

    except Exception as e:
        print(f"Error in crawl_programs: {e}")
        import traceback
        traceback.print_exc()
        return all_programs
    finally:
        driver.quit()


if __name__ == "__main__":
    import sys

    # Check if user wants visible browser mode
    headless_mode = "--headless" in sys.argv
    skip_captcha = "--skip-captcha" in sys.argv

    print(f"Running in {'headless' if headless_mode else 'visible browser'} mode")
    if not headless_mode and not skip_captcha:
        print("A browser window will open. You may need to solve a CAPTCHA.")

    programs = crawl_programs(headless=headless_mode, skip_captcha_check=skip_captcha)

    # Print some sample programs
    if programs:
        print("\nSample programs:")
        for program in programs[:5]:
            print(f"  - {program['program_name']}")
            if program['program_type']:
                print(f"    Type: {program['program_type']}")
            print(f"    URL: {program['catalog_url']}")
