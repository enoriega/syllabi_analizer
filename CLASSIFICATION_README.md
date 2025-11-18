# Course Classification Script

## Overview

The `classify_courses.py` script classifies courses from a CSV file into different categories based on their content and focus:

- **Core AI**: Courses where artificial intelligence is the primary subject of focus
- **Applied AI**: Courses where AI techniques are applied to a specific domain or problem
- **Core Data Science**: Courses where data science (pipelines, cleaning, dashboards, statistics) is the focus
- **Applied Data Science**: Courses where data science is applied to a domain or problem
- **Other**: Courses that don't fit the above categories

## How It Works

The script performs the following steps:

1. **Reads CSV Input**: Loads course information from a CSV file
2. **Fetches Catalog Descriptions**: Uses web scraping to retrieve course descriptions from catalog URLs
3. **Matches Syllabi**: Intelligently matches courses with detailed syllabi from `parsed_syllabi_dedup.json`
4. **LLM Classification**: Uses an LLM to classify each course based on:
   - Course title
   - Subject code(s)
   - Offering unit
   - Catalog description (if available)
   - Detailed syllabus description (if available)
5. **Generates Output**: Produces a JSON file with classifications and plain English justifications

## Usage

### Basic Usage

```bash
uv run python classify_courses.py
```

This will:
- Read from `data/courses.csv`
- Match with syllabi from `parsed_syllabi_dedup.json`
- Output to `classified_courses.json`

### Custom Paths

```bash
uv run python classify_courses.py \
  --input-csv path/to/courses.csv \
  --syllabi-json path/to/syllabi.json \
  --output path/to/output.json
```

### Test with Limited Courses

```bash
# Process only the first 5 courses (useful for testing)
uv run python classify_courses.py --limit 5
```

### Adjust Worker Processes

```bash
# Use 20 workers for faster parallel processing
uv run python classify_courses.py --workers 20

# Use 1 worker for sequential processing (debugging)
uv run python classify_courses.py --workers 1
```

### Retry Missing Catalog Descriptions

If you have an existing output file where some courses failed to fetch catalog descriptions, you can retry just those courses:

```bash
# Retry fetching catalog descriptions for courses missing them
uv run python classify_courses.py --retry-missing
```

This will:
1. Load the existing output file
2. Identify courses with missing or null catalog descriptions
3. Retry fetching those descriptions
4. Update the output file with the new data
5. Preserve all existing classifications

### Options

- `--input-csv PATH`: Path to input CSV file (default: `data/courses.csv`)
- `--syllabi-json PATH`: Path to parsed syllabi JSON file (default: `parsed_syllabi_dedup.json`)
- `--output PATH`: Path to output JSON file (default: `classified_courses.json`)
- `--limit N`: Limit the number of courses to process (useful for testing)
- `--workers N`: Number of worker processes for parallel classification (default: 10)
- `--retry-missing`: Retry fetching catalog descriptions for courses missing them in existing output

## Input Format

### CSV File

The input CSV should have the following columns:

- `Course ID`: Unique course identifier
- `Subject Code(s)`: Subject code(s) for the course (e.g., "CSC 477" or "CSC 438 / LING 438")
- `Offering Unit`: The unit offering the course
- `Course Title`: Title of the course
- `Max Units`: Maximum units for the course
- `Course URL`: URL to the course catalog page
- `Graduate`: Whether the course is graduate level (Yes/No)

### Syllabi JSON

The syllabi JSON should be an array of objects with at least:

```json
[
  {
    "course_name": "CSC 477 - Course Name",
    "description": "Detailed course description...",
    ...
  }
]
```

## Output Format

The output is a JSON array where each object contains:

```json
{
  "course_id": "9850",
  "subject_codes": "CSC 477",
  "offering_unit": "Computer Science",
  "course_title": "Introduction to Computer Vision",
  "max_units": "3",
  "course_url": "https://catalog.arizona.edu/courses/0098501",
  "is_graduate": "No",
  "catalog_description": "Course description from catalog...",
  "syllabus_description": "Detailed description from syllabus...",
  "course_type": "core_ai",
  "classification_justification": "This is a core AI course because it focuses on computer vision, which is a fundamental area of artificial intelligence..."
}
```

## Classification Criteria

### Core AI
- Machine Learning
- Neural Networks & Deep Learning
- Natural Language Processing
- Computer Vision
- Reinforcement Learning
- AI algorithms and techniques

### Applied AI
- AI in Healthcare
- AI for Robotics
- Medical Image Analysis using AI
- AI in Finance
- Domain-specific AI applications

### Core Data Science
- Data Mining & Discovery
- Data Warehousing
- Statistical Methods (without ML)
- Data Visualization
- Data Engineering & Pipelines
- Business Intelligence
- Basic statistical analysis

**Note**: Machine learning and deep learning are considered AI, not data science.

### Applied Data Science
- Health Data Science
- Business Analytics
- Econometrics
- Biosystems Analytics
- Domain-specific data analysis

## Subject Code Matching

The script intelligently matches courses with syllabi by:

1. Extracting all subject codes from both the course and syllabi
2. Normalizing codes (removing spaces, converting to uppercase)
3. Handling multiple codes (e.g., "CSC 438 / LING 438 / PSY 438")
4. Fuzzy matching to handle variations in formatting

## Configuration

The script uses environment variables from `.env`:

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your-api-key-here
```

## Example Run

```bash
$ uv run python classify_courses.py --limit 5 --workers 2
================================================================================
COURSE CLASSIFICATION
================================================================================
Input CSV: data/courses.csv
Syllabi JSON: parsed_syllabi_dedup.json
Output: classified_courses.json
Limit: 5 courses
Workers: 2

Validating LLM configuration...
  Using model: gpt-4o-mini

Loading courses from CSV...
  Limited to 5 courses

Loading syllabi...
  Loaded 1234 syllabi

Preparing classification tasks...
  Fetching catalog descriptions and matching syllabi...
    [1/5] Introduction to Computer Vision: catalog✓, syllabus✓
    [2/5] Artificial Intelligence: catalog✓, syllabus✗
    [3/5] Principles of Artificial Intelligence: catalog✓, syllabus✓
    [4/5] Introduction to Econometrics: catalog✓, syllabus✗
    [5/5] Data Analytics and Modeling: catalog✓, syllabus✓
  Prepared 5 classification tasks

Classifying courses using 2 workers...
--------------------------------------------------------------------------------
  [1/5] ✓ Introduction to Computer Vision -> core_ai
  [2/5] ✓ Artificial Intelligence -> core_ai
  [3/5] ✓ Principles of Artificial Intelligence -> core_ai
  [4/5] ✓ Introduction to Econometrics -> applied_data_science
  [5/5] ✓ Data Analytics and Modeling -> applied_data_science

================================================================================

Saving results to classified_courses.json...
  Saved 5 classified courses

Classification Summary:
----------------------------------------
  applied_data_science     :   2 courses
  core_ai                  :   3 courses

================================================================================
DONE!
================================================================================
```

## Retry Workflow

The script supports a retry mechanism for failed catalog description fetches:

### When to Use Retry Mode

If you run the classification and notice some courses have `null` or `"Not available"` catalog descriptions, you can retry just those courses without re-running the entire classification.

### How It Works

1. **Initial Run**: First classification may miss some catalog descriptions due to network issues or rate limiting
   ```bash
   uv run python classify_courses.py
   ```

2. **Check Results**: Review the output file and identify courses with missing descriptions
   ```json
   {
     "course_id": "9850",
     "catalog_description": null,  // Missing!
     ...
   }
   ```

3. **Retry Missing**: Run with `--retry-missing` flag
   ```bash
   uv run python classify_courses.py --retry-missing
   ```

4. **Result**: The script will:
   - Load existing classifications
   - Identify courses with missing catalog descriptions
   - Retry fetching only those descriptions
   - Update the output file with new data
   - Preserve all other existing data

### Example Output

```
Loading existing output...
  Found 129 existing classifications
  12 courses missing catalog descriptions

Preparing classification tasks...
  Retrying catalog descriptions for courses with missing data...
    [5/129] Data Mining: catalog✓ (retried)
    [12/129] Machine Learning: catalog✓ (retried)
    ...
```

## Error Handling

The script handles various error conditions gracefully:

- **Failed web scraping**: Continues without catalog description (can be retried later with `--retry-missing`)
- **No syllabus match**: Continues with only catalog description
- **LLM classification errors**: Creates a fallback classification with "other" type
- **Missing files**: Reports clear error messages

## Performance Notes

- **Parallel Processing**: The script uses multiprocessing to classify multiple courses simultaneously
- **Default Workers**: 10 worker processes run in parallel by default
- **Web Scraping**: Catalog descriptions are fetched sequentially before parallel classification begins
- **LLM Calls**: Each worker makes independent LLM calls in parallel
- **Progress Display**: Real-time progress shown as courses are classified
- **Typical Processing Time**:
  - With 10 workers: ~1-2 seconds per course (with parallelization)
  - Sequential (1 worker): ~5-10 seconds per course
- **Testing**: Use `--limit` to test with a small sample before processing all courses

## Dependencies

- `beautifulsoup4`: For web scraping
- `requests`: For HTTP requests
- `langchain-openai`: For LLM integration
- `pydantic`: For data validation
- `python-dotenv`: For environment variables

All dependencies are managed through `pyproject.toml` and installed with `uv sync`.
