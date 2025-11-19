# Faculty Profile Scraper

This script scrapes faculty profile information from University of Arizona profiles website.

## What it extracts

- Faculty name
- Titles and departments
- Contact information (email, phone, office)
- Biography
- Research interests
- Teaching interests
- Scholarly contributions (publications, books, etc.)

## Requirements

The script requires the following Python packages:
- requests
- beautifulsoup4

These are already installed in your project environment.

## Usage

### Single URL

```bash
uv run python scrape_faculty_profiles.py <url>
```

Example:
```bash
uv run python scrape_faculty_profiles.py https://profiles.arizona.edu/person/aaronmason
```

### Multiple URLs (command line)

```bash
uv run python scrape_faculty_profiles.py <url1> <url2> <url3>
```

### Multiple URLs (from file)

Create a text file with one URL per line:

```bash
uv run python scrape_faculty_profiles.py --file urls.txt
```

### Advanced Options

**Custom output file:**
```bash
uv run python scrape_faculty_profiles.py --file urls.txt --output custom_output.json
```

**Adjust number of parallel workers (default: 5):**
```bash
uv run python scrape_faculty_profiles.py --file urls.txt --workers 10
```

**Combine options:**
```bash
uv run python scrape_faculty_profiles.py --file urls.txt --output results.json --workers 8
```

## Output

The script outputs a JSON file (default: `faculty_profiles.json`) containing an array of profile objects. Each profile includes all extracted information.

## Example URLs File Format

Create a file named `urls.txt`:

```
https://profiles.arizona.edu/person/aaronmason
https://profiles.arizona.edu/person/johndoe
https://profiles.arizona.edu/person/janedoe
# Comments starting with # are ignored
https://profiles.arizona.edu/person/anotherprofile
```

## Parallel Processing

**The script uses parallel workers for fast scraping!**

- Default: 5 parallel workers
- Each worker scrapes profiles independently
- Results are saved incrementally to temporary files
- All results are merged at the end
- Use `--workers` to adjust the number of parallel workers

**Benefits:**
- Much faster scraping of large lists
- Progress updates in real-time
- Resilient to individual failures
- Safe incremental saving

Example:
```bash
# Scrape 100 profiles using 10 workers
uv run python scrape_faculty_profiles.py --file urls.txt --workers 10
```

**How it works:**
1. URLs are distributed across workers
2. Each worker saves results to its own temporary file
3. Progress updates show completion status
4. After all workers finish, results are merged
5. Temporary files are cleaned up automatically

## Resume Capability

**The script automatically resumes from where it left off!**

- If the output file already exists, the script loads existing profiles
- URLs that have already been scraped are automatically skipped
- Only new URLs are fetched from the web
- This allows you to:
  - Add new URLs to your list and re-run without re-scraping
  - Resume if the script was interrupted
  - Incrementally build your dataset over time

Example:
```bash
# First run - scrapes 5 profiles
uv run python scrape_faculty_profiles.py --file urls.txt

# Add 3 more URLs to urls.txt
# Second run - only scrapes the 3 new profiles, keeps the original 5
uv run python scrape_faculty_profiles.py --file urls.txt
```

## Error Handling

- If a profile fails to scrape, the script continues with the next one
- Errors are logged to stderr
- Failed profiles are still saved to the output with an 'error' field
- The final summary shows successful and failed scrapes
