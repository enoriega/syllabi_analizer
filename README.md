# Syllabi Analyzer

A tool to extract text from various document formats using LangChain and provide structured representations of syllabi data.

## Features

- Extracts text from PDF, Word (DOC/DOCX), PowerPoint (PPT/PPTX), and HTML files
- Recursively processes all files in a directory and its subdirectories
- Preserves directory structure in output
- Creates output files with format: `original_filename.original_ext.txt`
- Skips already processed files for efficient re-runs
- Structured Pydantic models for representing syllabus data

## Installation

Install dependencies using uv:

```bash
uv sync
```

Or using pip:

```bash
pip install -r requirements.txt
```

## Complete Workflow

Here's the complete workflow for processing syllabi:

### Step 1: Extract Text from Documents

```bash
# Extract text from all documents in the data directory
uv run python extract_text.py --data-dir data
```

This creates `.txt` files alongside the original documents.

### Step 2: Setup API Credentials

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API credentials
# Required: LLM_BASE_URL, LLM_MODEL_NAME, LLM_API_KEY
```

### Step 3: Parse Syllabi with LLM

```bash
# Parse all syllabi and create structured JSON output
uv run python parse_syllabi.py --input-dir data --output-file parsed_syllabi.json

# For testing, process only a few files:
uv run python parse_syllabi.py --max-files 5
```

### Step 4: Analyze Results

The output JSON file contains an array of structured syllabus objects that you can analyze, query, or import into a database.

```bash
# View summary statistics
uv run python analyze_results.py

# Show detailed list of AI-related courses
uv run python analyze_results.py --show-ai

# Search for specific topics
uv run python analyze_results.py --search "machine learning"

# Export only AI-related courses to a separate file
uv run python analyze_results.py --export-ai ai_courses.json
```

## Text Extraction Usage

The `extract_text.py` script supports parallel processing for faster extraction.

### Basic Usage

Process files with parallel processing (default, uses all CPU cores):

```bash
uv run python extract_text.py --data-dir data
```

### Parallel Processing Options

Limit the number of worker processes:

```bash
# Use 4 workers
uv run python extract_text.py --workers 4
```

Disable parallel processing (sequential):

```bash
uv run python extract_text.py --no-parallel
```

Specify a separate output directory:

```bash
uv run python extract_text.py --data-dir data --output-dir output
```

**Performance**: On a system with N CPU cores, parallel processing can provide up to N× speedup for CPU-bound operations. Actual performance depends on I/O speed and file complexity.

## Output Format

For each input file, the script creates a corresponding `.txt` file containing the extracted plain text:

- Input: `data/folder/document.pdf`
- Output: `data/folder/document.pdf.txt`

The output preserves the original filename and extension, then appends `.txt` to make it clear which file the text came from.

## Supported File Types

- PDF (`.pdf`)
- Microsoft Word (`.doc`, `.docx`)
- Microsoft PowerPoint (`.ppt`, `.pptx`)
- HTML (`.html`, `.htm`)

## Syllabus Data Model

The project includes a structured Pydantic model (`models.py`) for representing syllabus information:

### Syllabus Model

```python
from models import Syllabus, Term, Semester

syllabus = Syllabus(
    original_file_name="CS229_ML_Fall_2023.pdf",
    course_name="CS 229: Machine Learning",
    term_offered=Term(
        semester=Semester.FALL,
        academic_year=2023
    ),
    description="Introduction to machine learning...",
    is_ai_related=True,
    ai_related_justification="Covers ML algorithms and neural networks..."
)
```

### Fields

- **original_file_name**: The original filename of the syllabus document
- **course_name**: The name/title of the course
- **term_offered**: Optional structured object with:
  - `semester`: One of spring, summer, fall, winter (optional)
  - `academic_year`: The year (e.g., 2023) (optional)
- **description**: Course description including objectives and learning outcomes
- **is_ai_related**: Boolean flag indicating if the course is related to AI
- **ai_related_justification**: Optional explanation of why the course is AI-related

### Example Usage

See `test_models.py` for complete examples:

```bash
uv run python test_models.py
```

## Parsing Syllabi with LLM

The `parse_syllabi.py` script uses a language model to automatically extract structured information from syllabus text files.

### Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API credentials:
```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
LLM_API_KEY=your-api-key-here
```

### Usage

Basic usage (processes all .txt files in `data/` directory):
```bash
uv run python parse_syllabi.py
```

Specify custom input directory and output file:
```bash
uv run python parse_syllabi.py --input-dir data --output-file results.json
```

Process only a limited number of files (useful for testing):
```bash
uv run python parse_syllabi.py --max-files 5
```

### What It Does

The script:
1. Loads existing results from the output JSON file (if it exists) to avoid reprocessing
2. Reads all `.txt` files from the input directory (generated by `extract_text.py`)
3. Filters by year (default: 2024+) to process only recent courses
4. Skips files that have already been processed (based on filename)
5. Uses an LLM to analyze each new syllabus and extract:
   - Course name and code
   - Term offered (semester and year)
   - Course description and objectives
   - Whether the course is AI-related
   - Justification for AI classification
6. Shows progress updates every 100 files with current statistics
7. Appends new results to existing ones and saves all parsed syllabi as JSON array

**Features**:
- Automatically skips already-processed files (no duplicate API costs)
- Progress updates every 100 files show current success/skip/error counts
- Year filtering saves costs by processing only recent syllabi

### AI Classification Criteria

A course is considered AI-related if AI plays a **substantial role** in the course content. This includes:
- Machine Learning and Deep Learning
- Natural Language Processing
- Computer Vision
- Autonomous Systems and Robotics
- Expert Systems and Knowledge Representation
- AI Ethics and Responsible AI
- And other core AI topics

Courses that merely *use* AI tools or have a single AI lecture are **not** classified as AI-related.
