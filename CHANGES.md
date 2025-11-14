# Recent Changes

## Skip Already-Processed Files Feature

### Overview

The `parse_syllabi.py` script now automatically skips files that have already been processed, preventing duplicate API calls and saving costs.

### How It Works

1. **Load Existing Results**: On startup, the script loads the output JSON file (if it exists)
2. **Build Skip Set**: Creates a set of filenames that have already been processed
3. **Check Before Processing**: Before sending each file to the LLM, checks if it's already in the set
4. **Skip or Process**:
   - If already processed: Skips the file (no API call)
   - If new: Processes with LLM and adds to results
5. **Save Combined Results**: Saves all results (existing + new) back to the JSON file

### Benefits

- **Cost Savings**: Avoids duplicate API calls for already-processed files
- **Resume Capability**: If processing is interrupted, you can resume without reprocessing
- **Incremental Processing**: Add new syllabi to your collection and rerun the script - only new files are processed
- **Safe Re-runs**: You can safely rerun the script multiple times

### Example Output

```bash
$ uv run python parse_syllabi.py

Checking for existing results in parsed_syllabi.json...
Found 50 already processed syllabi

Setting up LLM...
Using model: gpt-4

Found 75 syllabus files to process

[1/75] Processing: folder/course1.pdf.txt
  ⊙ Already processed, skipping

[2/75] Processing: folder/course2.pdf.txt
  ⊙ Already processed, skipping

[3/75] Processing: folder/new_course.pdf.txt
  ✓ Successfully parsed
    Course: CS 101: Introduction to CS
    AI-related: False

...

Processing Summary:
  Total files: 75
  Successfully parsed (new): 25
  Skipped (already processed): 50
  Errors: 0
  Total in output file: 75

AI-Related Courses: 12/75 (16.0%)
```

### Implementation Details

**New Function**: `load_existing_results(output_file: str)`
- Returns: `tuple[List[Syllabus], set[str]]`
- Loads existing JSON file
- Converts to Syllabus objects
- Extracts filenames into a set for fast lookup

**Modified**: `process_syllabi_directory()`
- Calls `load_existing_results()` at startup
- Checks `if original_filename in processed_filenames` before processing
- Tracks skipped count separately
- Reports all counts in summary

### Code Changes

**Before**:
```python
for txt_file in txt_files:
    # Read file
    # Process with LLM
    # Save result
```

**After**:
```python
# Load existing results
parsed_syllabi, processed_filenames = load_existing_results(output_file)

for txt_file in txt_files:
    original_filename = get_filename(txt_file)

    # Check if already processed
    if original_filename in processed_filenames:
        print("Already processed, skipping")
        skipped_count += 1
        continue

    # Read file
    # Process with LLM
    # Append to results
```

### Testing

Run the test script to verify functionality:

```bash
uv run python test_skip_functionality.py
```

This will:
1. Create a test JSON file with sample data
2. Load it using `load_existing_results()`
3. Verify the skip logic works correctly
4. Demonstrate the filename checking process

### Migration Notes

**No breaking changes** - The script works exactly the same way for new users. For existing users:

1. If you have an existing `parsed_syllabi.json`, the script will automatically load and use it
2. Previously processed files will be skipped
3. New files will be processed and appended
4. The final JSON will contain all results (old + new)

### Use Cases

**Use Case 1: Interrupted Processing**
```bash
# Start processing 1000 files
$ uv run python parse_syllabi.py

# ... processes 500 files, then crashes or is interrupted ...

# Resume - will skip the 500 already done
$ uv run python parse_syllabi.py
```

**Use Case 2: Adding New Syllabi**
```bash
# Initial processing
$ uv run python parse_syllabi.py
# Processes 100 files

# Later, add 20 more syllabi to the data directory
# Rerun - will skip the 100 and only process the 20 new ones
$ uv run python parse_syllabi.py
```

**Use Case 3: Fixing Errors**
```bash
# First run with some errors
$ uv run python parse_syllabi.py
# Successfully parsed: 90, Errors: 10

# Fix the problematic files (e.g., OCR issues)
# Rerun - will skip the 90 successful ones and retry the 10
$ uv run python parse_syllabi.py
```

## Other Recent Updates

### Extract Text Script
- Added skip functionality for `.txt` files that already exist
- Prevents re-extracting text from documents

### Documentation
- Updated README.md with skip functionality details
- Updated USAGE_GUIDE.md with resume and incremental processing tips
- Added cost-saving tips in documentation

### Models
- Created Pydantic models for structured syllabus data
- Added `Syllabus`, `Term`, and `Semester` models
- Full validation and type checking

### Analysis Tools
- Created `analyze_results.py` for result analysis
- Summary statistics
- AI course filtering
- Search functionality
- Export capabilities
