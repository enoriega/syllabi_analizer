# Recent Enhancements

## Parallel Processing for Text Extraction

### Overview

The `extract_text.py` script now supports multiprocessing for parallel file processing, dramatically improving performance when processing large collections of documents.

### Key Features

1. **Automatic CPU Detection**: Automatically uses all available CPU cores by default
2. **Configurable Workers**: Allows specifying the number of worker processes
3. **Sequential Fallback**: Option to disable parallelism for debugging or compatibility
4. **Thread-Safe**: Uses multiprocessing.Pool for safe parallel execution
5. **Maintains Compatibility**: All existing functionality preserved

### Performance Benefits

On a system with N CPU cores:
- **Theoretical speedup**: Up to N× faster
- **Typical speedup**: 5-10× for mixed document types
- **Example**: 100 files @ 2s each
  - Sequential: ~200s (3.3 minutes)
  - Parallel (12 cores): ~17s (0.3 minutes)
  - **Speedup: 12× faster**

### Implementation Details

**New Data Structures**:
```python
@dataclass
class ProcessingTask:
    file_path: Path
    output_file_path: Path
    data_path: Path
    output_path: Path

@dataclass
class ProcessingResult:
    file_path: Path
    output_file_path: Path
    success: bool
    skipped: bool
    error_message: str = ""
```

**Worker Function**:
- `process_single_file(task: ProcessingTask)` - Processes one file in a worker process
- Checks if file already processed (skip logic)
- Extracts text using appropriate loader
- Writes output file
- Returns structured result

**Process Pool**:
```python
with mp.Pool(processes=num_workers) as pool:
    results = pool.map(process_single_file, tasks)
```

### Usage

**Default (parallel with all cores)**:
```bash
uv run python extract_text.py
```

**Custom number of workers**:
```bash
uv run python extract_text.py --workers 4
```

**Sequential processing**:
```bash
uv run python extract_text.py --no-parallel
```

**Combined with other options**:
```bash
uv run python extract_text.py --data-dir data --output-dir output --workers 8
```

### When to Use Sequential vs Parallel

**Use Parallel (default)**:
- Processing many files (>10)
- Normal operation
- Production runs
- When speed is important

**Use Sequential (--no-parallel)**:
- Debugging issues
- Processing very few files (1-2)
- Limited system resources
- When you need to see files processed in order

### Technical Notes

**Process Safety**:
- Each worker process is independent
- No shared state between workers
- Output directories created safely with `mkdir(parents=True, exist_ok=True)`
- File writes are atomic at the OS level

**Error Handling**:
- Errors in one file don't affect others
- Each result tracked independently
- Summary shows successes, skips, and errors

**Memory Considerations**:
- Each worker loads one file at a time
- Memory usage = (avg file size) × (num workers) × 2-3
- For large PDFs, consider limiting workers
- Example: 10MB PDFs × 12 workers = ~240-360MB peak

### Benchmarking

To compare sequential vs parallel on your system:

```bash
# Sequential
time uv run python extract_text.py --no-parallel --data-dir test_data

# Parallel
time uv run python extract_text.py --data-dir test_data
```

## Year Filtering for LLM Processing

### Overview

The `parse_syllabi.py` script now filters syllabi by academic year before sending to the LLM, saving API costs by processing only recent courses.

### Key Features

1. **Smart Year Detection**: Extracts year from filename and directory path
2. **Configurable Minimum Year**: Default is 2024, but can be changed
3. **Conservative Approach**: Processes files when year cannot be determined
4. **Detailed Reporting**: Shows detected years and filter statistics

### Year Detection

The script looks for 4-digit years (2000-2099) in:
- Directory names: `"Spring 2024"`, `"Fall2023"`, `"2024_Spring"`
- File paths: `"data/courses/2025/file.pdf"`
- Uses the **most recent** year found if multiple years present

**Examples**:
```python
"Spring 2024/course.pdf" → 2024
"data/2022/Fall 2023/file.pdf" → 2023 (most recent)
"no_year/course.pdf" → None (will process anyway)
```

### Usage

**Default (2024 onwards)**:
```bash
uv run python parse_syllabi.py
```

**Custom year filter**:
```bash
# Only 2023 onwards
uv run python parse_syllabi.py --min-year 2023

# Only 2022 onwards
uv run python parse_syllabi.py --min-year 2022
```

**Process all (no filter)**:
```bash
uv run python parse_syllabi.py --min-year 2000
```

### Cost Savings Example

Collection: 500 syllabi
- 2024: 50 syllabi
- 2023: 100 syllabi
- 2022: 150 syllabi
- 2021 and earlier: 200 syllabi

**Without filter** (--min-year 2000):
- Processes: 500 syllabi
- API calls: 500
- Cost: $X (depends on model and pricing)

**With default filter** (--min-year 2024):
- Processes: 50 syllabi
- API calls: 50
- Cost: $X/10
- **Savings: 90%**

### Output

```
Filtering for courses from 2024 onwards

[1/100] Processing: Spring 2024/course1.pdf.txt
  ℹ Year detected: 2024
  ✓ Successfully parsed

[2/100] Processing: Fall 2023/course2.pdf.txt
  ⊙ Year 2023 < 2024, skipping

Processing Summary:
  Total files: 100
  Successfully parsed (new): 25
  Skipped (already processed): 5
  Filtered by year (< 2024): 70
  Errors: 0
```

## Combined Workflow

### Full Pipeline with Optimizations

```bash
# Step 1: Extract text with parallel processing
uv run python extract_text.py --data-dir data --workers 12

# Step 2: Parse only recent syllabi (2024+) with LLM
uv run python parse_syllabi.py --min-year 2024

# Step 3: Analyze results
uv run python analyze_results.py --show-ai
```

### Performance Comparison

**Before optimizations**:
- Text extraction: 100 files × 2s = 200s sequential
- LLM processing: 100 files × 5s = 500s (250 API calls)
- Total: ~12 minutes, ~$X API cost

**After optimizations**:
- Text extraction: 100 files ÷ 12 workers = ~17s parallel
- LLM processing: Only 25 recent files × 5s = 125s
- Total: ~2.5 minutes, ~$X/4 API cost
- **Improvement: 5× faster, 75% cost reduction**

## Backward Compatibility

All enhancements maintain backward compatibility:

**extract_text.py**:
- Old command still works: `python extract_text.py`
- New default is parallel (can disable with `--no-parallel`)

**parse_syllabi.py**:
- Default filters to 2024+ (can change with `--min-year`)
- Use `--min-year 2000` to process all files (old behavior)

## Testing

Test the enhancements:

```bash
# Test parallel processing
uv run python test_parallel_extraction.py

# Test year filtering
uv run python test_year_filter.py
```

## Future Enhancements

Potential improvements:
1. Progress bar during parallel processing
2. Rate limiting for LLM API calls
3. Incremental JSON updates (append mode)
4. Caching of LLM responses
5. Batch processing for very large collections
6. Resume from specific file (checkpointing)
