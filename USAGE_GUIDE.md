# Syllabi Analyzer - Usage Guide

This guide walks you through the complete workflow for analyzing syllabi using LLM-powered extraction.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Extract text from documents
uv run python extract_text.py

# 3. Setup API credentials
cp .env.example .env
# Edit .env and add your API key

# 4. Parse syllabi with LLM
uv run python parse_syllabi.py --max-files 5  # Start with a small test

# 5. Analyze results
uv run python analyze_results.py --show-ai
```

## Detailed Workflow

### 1. Text Extraction (`extract_text.py`)

**Purpose**: Extract plain text from PDF, Word, PowerPoint, and HTML files.

**Input**: Original document files in various formats
**Output**: `.txt` files with extracted text

```bash
# Process all files in data directory
uv run python extract_text.py --data-dir data

# Use a separate output directory
uv run python extract_text.py --data-dir data --output-dir output
```

**Features**:
- Recursively processes all files in subdirectories
- Preserves directory structure
- Skips already-processed files (checks if `.txt` file exists)
- Supports: PDF, DOC, DOCX, PPT, PPTX, HTML

**Output format**: `original_filename.ext.txt`
- Example: `CS229_ML_2023.pdf` → `CS229_ML_2023.pdf.txt`

### 2. API Configuration

**Create `.env` file**:

```bash
cp .env.example .env
```

**Edit `.env` with your credentials**:

```bash
# For OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
LLM_API_KEY=sk-...your-key...

# For Azure OpenAI
LLM_BASE_URL=https://your-resource.openai.azure.com/
LLM_MODEL_NAME=gpt-4
LLM_API_KEY=your-azure-key

# For other OpenAI-compatible APIs
LLM_BASE_URL=https://your-custom-endpoint.com/v1
LLM_MODEL_NAME=your-model-name
LLM_API_KEY=your-api-key
```

### 3. LLM-Powered Parsing (`parse_syllabi.py`)

**Purpose**: Use an LLM to extract structured information from syllabi.

**Input**: `.txt` files from step 1
**Output**: JSON file with structured syllabus data

```bash
# Process all files
uv run python parse_syllabi.py

# Custom paths
uv run python parse_syllabi.py --input-dir data --output-file results.json

# Test with limited files
uv run python parse_syllabi.py --max-files 5
```

**What it extracts**:
1. **Course Name**: Official course name and code (e.g., "CS 229: Machine Learning")
2. **Term Offered**: Semester and year (extracted from filename, path, or text)
3. **Description**: Comprehensive course description including objectives
4. **AI Classification**: Boolean flag indicating if course is AI-related
5. **Justification**: Explanation of why course is classified as AI-related

**AI Classification Criteria**:

A course is marked as AI-related if AI plays a **substantial role** in the curriculum.

✅ **AI-Related Examples**:
- Machine Learning
- Deep Learning
- Natural Language Processing
- Computer Vision
- Autonomous Systems
- Expert Systems
- Neural Networks
- Data Mining (with ML focus)
- AI Ethics

❌ **Not AI-Related**:
- Courses that only *use* AI tools
- Courses with a single AI lecture
- General statistics without ML focus
- General programming courses

### 4. Results Analysis (`analyze_results.py`)

**Purpose**: Analyze and query the parsed syllabi.

**Input**: JSON file from step 3
**Output**: Summary statistics and filtered data

```bash
# Show summary statistics
uv run python analyze_results.py

# Show all AI-related courses
uv run python analyze_results.py --show-ai

# Search for specific keywords
uv run python analyze_results.py --search "neural network"
uv run python analyze_results.py --search "statistics"

# Export AI courses to separate file
uv run python analyze_results.py --export-ai ai_courses.json
```

**Summary Statistics**:
- Total syllabi count
- AI vs Non-AI breakdown
- Semester distribution
- Academic year distribution

## Data Model

The parsed data follows this structure:

```json
{
  "original_file_name": "CS229_ML_Fall_2023.pdf",
  "course_name": "CS 229: Machine Learning",
  "term_offered": {
    "semester": "fall",
    "academic_year": 2023
  },
  "description": "This course provides a broad introduction to machine learning...",
  "is_ai_related": true,
  "ai_related_justification": "This course covers core ML algorithms including supervised learning, unsupervised learning, and neural networks."
}
```

## Tips and Best Practices

### Cost Management

1. **Test with small batches**: Use `--max-files 5` to test before processing all files
2. **Use cheaper models for testing**: Try `gpt-3.5-turbo` before switching to `gpt-4`
3. **Check output quality**: Review a few results before processing the entire collection
4. **Resume interrupted processing**: The script automatically skips already-processed files, so you can safely re-run it without duplicate API costs
5. **Incremental processing**: Process new syllabi by simply adding them to the data directory and re-running the script

### Accuracy

1. **Use better models for final run**: GPT-4 or Claude Opus for production quality
2. **Verify AI classification**: Spot-check AI-related courses to ensure accuracy
3. **Iterate on prompts**: The prompt in `parse_syllabi.py` can be customized

### File Organization

```
syllabi_analizer/
├── data/                     # Original documents
│   └── subfolder/
│       ├── course1.pdf
│       └── course1.pdf.txt   # Generated by extract_text.py
├── parsed_syllabi.json       # Generated by parse_syllabi.py
└── ai_courses.json          # Exported by analyze_results.py
```

## Troubleshooting

### "No module named 'langchain'"
```bash
uv sync
```

### ".env file not found"
```bash
cp .env.example .env
# Then edit .env with your credentials
```

### "Empty file" warnings
Some PDFs may have text extraction issues. Check:
1. Is the PDF text-based or image-based?
2. Try opening the file manually to verify it has readable text

### API Rate Limits
If you hit rate limits:
1. Add delays between requests (modify `parse_syllabi.py`)
2. Use `--max-files` to process in smaller batches
3. Check your API tier/quota

### Parsing Errors
If the LLM returns invalid JSON:
1. Try a more capable model (e.g., GPT-4)
2. Check if the syllabus text is corrupted
3. Review the prompt template in `parse_syllabi.py`

## Example Session

```bash
# Complete workflow example
$ uv sync
$ uv run python extract_text.py --data-dir data
Found 150 files to process
...
Processing complete: 145 succeeded, 5 errors

$ cp .env.example .env
$ vim .env  # Add API key

$ uv run python parse_syllabi.py --max-files 10
Setting up LLM...
Using model: gpt-4

Found 10 syllabus files to process

[1/10] Processing: folder1/course1.pdf.txt
  ✓ Successfully parsed
    Course: CS 101: Introduction to Computer Science
    AI-related: False
...

Processing Summary:
  Successfully parsed: 8
  Errors: 2

AI-Related Courses: 3/8 (37.5%)

$ uv run python analyze_results.py --show-ai
============================================================
AI-RELATED COURSES
============================================================

1. CS 229: Machine Learning
   File: CS229_ML_Fall_2023.pdf
   Term: Fall 2023
   Justification: Covers supervised learning, neural networks...

2. CS 224N: Natural Language Processing
   File: CS224N_NLP_Spring_2023.pdf
   Term: Spring 2023
   Justification: Focuses on NLP techniques including transformers...
```

## Advanced Usage

### Custom Prompts

Edit `parse_syllabi.py` to customize the extraction logic:
- Modify the `create_parsing_prompt()` function
- Add additional fields to the Syllabus model
- Adjust AI classification criteria

### Batch Processing

For large collections, process in batches:

```bash
# Process 50 at a time
for i in {0..5}; do
  uv run python parse_syllabi.py --max-files 50 --output-file "batch_${i}.json"
done

# Merge results (you'll need to write a merge script)
```

### Database Integration

Load parsed JSON into a database:

```python
import json
from sqlalchemy import create_engine
from models import Syllabus

# Load data
with open('parsed_syllabi.json') as f:
    data = json.load(f)

# Create Syllabus objects
syllabi = [Syllabus(**item) for item in data]

# Insert into database (example)
# ... your database code here ...
```
