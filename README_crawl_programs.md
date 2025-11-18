# UA Catalog Programs Crawler

This script crawls the University of Arizona catalog website to enumerate all academic programs and saves them to a JSON file.

## Features

- Extracts program names, types (e.g., Bachelor of Science, Master of Arts), and catalog URLs
- Handles pagination automatically
- Removes duplicate entries
- Saves output to `ua_programs.json`

## Important Note: CAPTCHA Protection & Bot Detection

The UA catalog website (https://catalog.arizona.edu/programs) is protected by AWS WAF with aggressive bot detection:

1. **The script MUST run in visible browser mode** - headless mode will not work
2. **Manual CAPTCHA solving required** - You'll need to solve CAPTCHA challenges
3. **Interactive session required** - The script needs to run in a terminal where you can press Enter
4. **Multiple CAPTCHAs may appear** - The site may show CAPTCHA again after several page requests
5. **Page redirects** - The site may redirect back to page 1 if it detects automation

**Due to these protections, this script works best when:**
- Run on a local machine with display
- Run interactively in a terminal
- User is present to solve CAPTCHAs as they appear

## Installation

The required dependencies are already in `pyproject.toml`. If you need to install them separately:

```bash
uv sync
```

## Usage

### Run with Visible Browser (Recommended)

```bash
uv run python crawl_programs.py
```

This will:
1. Open a Chrome browser window
2. Navigate to https://catalog.arizona.edu/programs
3. If a CAPTCHA appears, you'll be prompted to solve it
4. After solving the CAPTCHA, press Enter in the terminal
5. The script will automatically crawl all pages and extract programs

###Run in Headless Mode (Not Recommended)

```bash
uv run python crawl_programs.py --headless
```

**Note**: This mode will likely fail due to CAPTCHA protection, but it's available if the website changes its security settings.

## Output

The script generates `ua_programs.json` with the following structure:

```json
[
  {
    "program_name": "Applied Behavior Analysis\nGraduate Certificate",
    "program_type": "Graduate Certificate",
    "catalog_url": "https://catalog.arizona.edu/programs/ABACRTG"
  },
  {
    "program_name": "Agribusiness Economics and Management\nBachelor of Science",
    "program_type": "Bachelor of Science",
    "catalog_url": "https://catalog.arizona.edu/programs/ABEMBS"
  }
]
```

## How It Works

1. **Browser Setup**: Configures Chrome with anti-detection settings
2. **CAPTCHA Handling**: Detects CAPTCHA and prompts for manual solving
3. **Content Extraction**: Finds all program links on each page
4. **Pagination**: Tries multiple strategies:
   - Letter filters (A-Z navigation)
   - Page number URL parameters
   - Sequential page iteration
5. **Deduplication**: Removes duplicate programs based on catalog URL
6. **JSON Export**: Saves all unique programs to a JSON file

## Alternative Approach (Recommended)

Due to the aggressive bot protection on the UA catalog website, **manual browsing** may be more reliable:

1. Open https://catalog.arizona.edu/programs in a regular browser
2. Use browser developer tools (F12) to inspect the page structure
3. Look for an API endpoint that the page uses to fetch data
4. Or, use the browser's "Copy as cURL" feature to capture the exact request format

You may also check if UA provides:
- An official API for program data
- A sitemap.xml file with all program URLs
- Bulk data downloads

## Troubleshooting

### "CAPTCHA DETECTED" message appears

This is expected. Follow these steps:
1. Look at the browser window that opened
2. Complete the CAPTCHA puzzle
3. Wait for the page to load
4. Return to the terminal and press Enter

### Browser doesn't open

Make sure you're running the script in an environment with a display (not SSH without X forwarding).

### Script finds only 20 programs or gets stuck

This is due to AWS WAF protection:
- The site may be redirecting all page requests back to page 1
- Try adding longer delays between requests
- The script may need to be run multiple times
- Consider contacting UA to ask if they have an API or data export

### "WARNING: URL doesn't contain page=X"

The website is redirecting you back to page 1. This is a bot detection measure. The script will stop to avoid infinite loops.

### Programs are duplicated

The script automatically deduplicates based on catalog URL, so the final `ua_programs.json` should contain unique programs only.

## Example Run

```bash
$ uv run python crawl_programs.py
Running in visible browser mode
A browser window will open. You may need to solve a CAPTCHA.
Loading programs page...

============================================================
CAPTCHA DETECTED!
Please solve the CAPTCHA in the browser window.
After solving it, press Enter here to continue...
============================================================

[Press Enter after solving CAPTCHA]

No letter filters found, trying pagination...
Scraping page 1...
Found 20 programs on page 1 (first: Applied Behavior Analysis...)
Trying page 2...
Found 20 programs on page 2 (first: Accounting...)
...

Total programs found: 485
Unique programs: 485

Programs saved to ua_programs.json
```

## Output File Location

- `ua_programs.json` - Main output file with all programs
- `page_source_debug.html` - Debug file (only created if no programs are found)

## Notes

- The script is respectful of the server and includes delays between requests
- It stops automatically when no more pages are found or after encountering duplicate content
- The maximum number of pages tried is 50 to prevent infinite loops
