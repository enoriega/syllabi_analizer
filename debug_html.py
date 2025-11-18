#!/usr/bin/env python3
"""Quick debug script to see HTML structure"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

chrome_options = Options()
# Don't use headless to avoid CAPTCHA
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-position=-2400,-2400")  # Move off-screen

driver = webdriver.Chrome(options=chrome_options)
driver.get("https://catalog.arizona.edu/programs/ISCBS")

time.sleep(5)  # Wait for JS to render

# Print a sample of what we can see
print("Sample of page text:")
body_text = driver.find_element("tag name", "body").text
print(body_text[:800])
print("\n" + "="*50 + "\n")

soup = BeautifulSoup(driver.page_source, 'html.parser')

# Find all h3 tags with class field-label
print("All field labels found:")
all_labels = soup.find_all('h3', class_='field-label')
for label in all_labels:
    print(f"  - {label.get_text()}")

print("\nLooking for Program Description specifically:")
for label in all_labels:
    if 'description' in label.get_text().lower():
        print(f"Found: {label.get_text()}")
        value = label.find_next_sibling('div')
        if value:
            print(f"Value div class: {value.get('class')}")
            print(f"Text: {value.get_text()[:300]}")

driver.quit()
