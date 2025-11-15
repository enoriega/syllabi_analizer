# Parallel Processing for Syllabus Parsing

## Overview

The `parse_syllabi.py` script now supports parallel processing using Python's `multiprocessing` module. This significantly speeds up the processing of large collections of syllabi by utilizing multiple CPU cores to make concurrent LLM API calls.

## Key Features

### 1. Configurable Worker Pool
- **Default**: 5 parallel workers
- **Customizable**: Use `--workers N` to set any number of workers
- **Sequential mode**: Use `--no-parallel` to process files one at a time

### 2. Progress Tracking
- Real-time progress updates as files are processed
- Updates every 100 files showing:
  - Files processed (e.g., 200/500)
  - Successfully parsed count
  - Error count
  - AI-related percentage

### 3. Resume Capability
- All existing functionality preserved:
  - Skips already-processed files
  - Year filtering (default: 2024+)
  - Incremental results saving

## Usage Examples

### Basic Usage (5 workers, default)
```bash
uv run python parse_syllabi.py
```

### Custom Worker Count
```bash
# Use 10 workers for faster processing
uv run python parse_syllabi.py --workers 10

# Use 2 workers to reduce API load
uv run python parse_syllabi.py --workers 2
```

### Sequential Processing
```bash
# Disable parallel processing
uv run python parse_syllabi.py --no-parallel
```

### Testing with Limited Files
```bash
# Process only 20 files with 3 workers
uv run python parse_syllabi.py --max-files 20 --workers 3
```

## Performance Considerations

### Benefits
- **Throughput**: Process multiple files simultaneously
- **API Efficiency**: Make better use of API rate limits by sending multiple concurrent requests
- **Time Savings**: N workers can process up to N times faster (where N is worker count)

### Considerations
- **API Rate Limits**: More workers = more concurrent API calls
  - If you hit rate limits, reduce worker count with `--workers 2` or `--workers 3`
- **Memory Usage**: Each worker loads its own LLM instance
  - For very large collections, moderate worker counts (5-10) are recommended
- **Cost**: Parallel processing doesn't increase API costs, just speeds up processing

## Implementation Details

### Architecture

The parallel implementation uses the following approach:

1. **Task Preparation Phase**
   - Reads all text files
   - Applies filters (year, already-processed, empty files)
   - Creates a list of `ProcessingTask` objects

2. **Parallel Processing Phase**
   - Uses `multiprocessing.Pool` with N workers
   - Each worker gets its own LLM instance
   - Tasks are distributed using `pool.imap()` for ordered results

3. **Results Collection Phase**
   - Results arrive in order
   - Progress displayed in real-time
   - All results saved to JSON

### Key Components

```python
@dataclass
class ProcessingTask:
    """Task to be processed by a worker."""
    txt_file: Path
    original_filename: str
    relative_path: str
    content: str
    extracted_year: Optional[int]
    input_path: Path

@dataclass
class ProcessingResult:
    """Result from processing a single file."""
    txt_file: Path
    syllabus: Optional[Syllabus]
    success: bool
    skipped: bool
    year_filtered: bool
    error_message: str = ""
```

### Worker Function

Each worker process executes `process_single_file()`:
- Sets up its own LLM instance
- Parses the syllabus using LangChain
- Returns a `ProcessingResult`

## Example Output

```
Found 350 syllabus files to process
Filtering for courses from 2024 onwards
Using parallel processing with 5 workers

Preparing tasks...
Tasks prepared: 200 files to process
  Skipped (already processed): 100
  Filtered by year (< 2024): 50

Processing 200 files...
Using model: gpt-4

[1/200] ✓ Spring_2024/CS229_ML.pdf.txt
  ✓ Successfully parsed
    Course: CS 229: Machine Learning
    AI-related: True

[2/200] ✓ Spring_2024/PHIL101.pdf.txt
  ✓ Successfully parsed
    Course: PHIL 101: Introduction to Philosophy
    AI-related: False

...

============================================================
Progress Update: Processed 100/200 files
  Successfully parsed: 95
  Errors: 5
  AI-related so far: 23/95 (24.2%)
============================================================

[200/200] ✓ Fall_2024/DATA301.pdf.txt
  ✓ Successfully parsed
    Course: DATA 301: Data Science
    AI-related: True

Saving results to parsed_syllabi.json...
✓ Saved 295 parsed syllabi

============================================================
Processing Summary:
  Total files: 350
  Successfully parsed (new): 195
  Skipped (already processed): 100
  Filtered by year (< 2024): 50
  Errors: 5
  Total in output file: 295

AI-Related Courses: 71/295 (24.1%)
============================================================
```

## Comparison: Sequential vs Parallel

### Sequential Processing (`--no-parallel`)
- **Pros**:
  - Lower memory usage
  - Easier to debug
  - No risk of rate limiting
- **Cons**:
  - Slower processing
  - One file at a time

### Parallel Processing (default, 5 workers)
- **Pros**:
  - Much faster (up to 5× with 5 workers)
  - Better API utilization
  - Progress updates in real-time
- **Cons**:
  - More memory usage
  - May hit API rate limits

## Troubleshooting

### Rate Limit Errors

If you see rate limit errors:
```bash
# Reduce worker count
uv run python parse_syllabi.py --workers 2

# Or use sequential processing
uv run python parse_syllabi.py --no-parallel
```

### Memory Issues

If you run out of memory:
```bash
# Reduce worker count
uv run python parse_syllabi.py --workers 3
```

### Testing

Test with a small number of files first:
```bash
uv run python parse_syllabi.py --max-files 10 --workers 3
```

## Command-Line Options

```
--workers WORKERS     Number of parallel workers (default: 5)
--no-parallel         Disable parallel processing and process files sequentially
--input-dir DIR       Directory containing .txt syllabus files (default: data)
--output-file FILE    Output JSON file path (default: parsed_syllabi.json)
--max-files N         Maximum number of files to process (useful for testing)
--min-year YEAR       Minimum academic year to process (default: 2024)
```

## Best Practices

1. **Start Conservative**: Begin with 5 workers (default) and adjust based on results
2. **Monitor Progress**: Watch for rate limit errors in the output
3. **Test First**: Use `--max-files 10` to test your configuration
4. **Adjust Workers**:
   - Increase for faster processing (if no rate limits)
   - Decrease if hitting rate limits
5. **Use Year Filtering**: Keep `--min-year 2024` to reduce costs and processing time
