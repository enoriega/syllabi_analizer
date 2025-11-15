# Progress Updates Feature

## Overview

The `parse_syllabi.py` script now provides real-time progress updates every 100 files, giving visibility into long-running LLM processing tasks.

## What You'll See

During processing, you'll see updates like this:

```
[1/350] Processing: Spring 2024/course1.pdf.txt
  ℹ Year detected: 2024
  ✓ Successfully parsed
    Course: CS 101: Introduction to Computer Science
    AI-related: False

[2/350] Processing: Fall 2023/course2.pdf.txt
  ⊙ Year 2023 < 2024, skipping

... (processing continues) ...

[100/350] Processing: Spring 2024/course100.pdf.txt
  ✓ Successfully parsed

============================================================
Progress Update: Processed 100/350 files
  Successfully parsed: 30
  Skipped (already processed): 45
  Filtered by year: 20
  Errors: 5
  AI-related so far: 4/30 (13.3%)
============================================================

... (processing continues) ...
```

## Information Provided

Each progress update shows:

1. **Files Processed**: `100/350` - Current position in the queue
2. **Successfully Parsed**: New syllabi processed by the LLM
3. **Skipped**: Files already in the output JSON (cost savings!)
4. **Filtered by Year**: Files excluded by year filter (cost savings!)
5. **Errors**: Failed extractions or LLM errors
6. **AI-Related Percentage**: Running count of AI-related courses

## Benefits

### 1. Visibility
- Confirms the script is still running
- Long processes (hundreds of files) can take hours
- Without updates, it might seem frozen

### 2. Time Estimation
```
Example:
- 100 files processed in 8 minutes
- Total: 500 files
- Estimated time: 40 minutes (5 × 8)
```

### 3. Early Problem Detection
- High error rate? Something might be wrong
- No AI courses found? Check classification criteria
- Many filtered? Adjust `--min-year` parameter

### 4. Cost Monitoring
- See how many files are actually being sent to LLM
- Skipped + Filtered = API calls saved
- Estimate total cost mid-processing

### 5. Decision Making
```
After 100 files:
- 60 filtered by year? Maybe adjust --min-year
- 30 errors? Stop and investigate
- Good progress? Let it run to completion
```

## Frequency

**Default**: Every 100 files

This works well for most collections:
- Small (<200 files): See 1-2 updates
- Medium (200-1000 files): See 2-10 updates
- Large (>1000 files): See 10+ updates

### Customizing Frequency

Edit `parse_syllabi.py` line 359:

```python
# Current (every 100 files)
if idx % 100 == 0:

# More frequent (every 50 files)
if idx % 50 == 0:

# Less frequent (every 200 files)
if idx % 200 == 0:
```

**Recommendations**:
- **Small collections** (<200 files): 25-50 files
- **Medium collections** (200-1000): 100 files (default)
- **Large collections** (>1000): 200-500 files

## Example Session

### Processing 350 Files

```bash
$ uv run python parse_syllabi.py

Checking for existing results in parsed_syllabi.json...
No existing results found, starting fresh

Setting up LLM...
Using model: gpt-4

Found 350 syllabus files to process
Filtering for courses from 2024 onwards

[1/350] Processing: Spring 2024/CS101.pdf.txt
  ℹ Year detected: 2024
  ✓ Successfully parsed
    Course: CS 101: Introduction to Computer Science
    AI-related: False

[2/350] Processing: Fall 2023/CS102.pdf.txt
  ⊙ Year 2023 < 2024, skipping

... (98 more files) ...

============================================================
Progress Update: Processed 100/350 files
  Successfully parsed: 35
  Skipped (already processed): 0
  Filtered by year: 60
  Errors: 5
  AI-related so far: 5/35 (14.3%)
============================================================

[101/350] Processing: ...

... (100 more files) ...

============================================================
Progress Update: Processed 200/350 files
  Successfully parsed: 68
  Skipped (already processed): 0
  Filtered by year: 125
  Errors: 7
  AI-related so far: 10/68 (14.7%)
============================================================

... (continues) ...

============================================================
Progress Update: Processed 300/350 files
  Successfully parsed: 100
  Skipped (already processed): 0
  Filtered by year: 190
  Errors: 10
  AI-related so far: 15/100 (15.0%)
============================================================

... (final 50 files) ...

Saving results to parsed_syllabi.json...
✓ Saved 105 parsed syllabi

============================================================
Processing Summary:
  Total files: 350
  Successfully parsed (new): 105
  Skipped (already processed): 0
  Filtered by year (< 2024): 235
  Errors: 10
  Total in output file: 105

AI-Related Courses: 16/105 (15.2%)
============================================================
```

## Cost Analysis from Updates

From the example above:

**Without year filter** (all 350 files):
- API calls: 350
- Estimated cost: $35 (at $0.10/call)

**With year filter** (2024+ only):
- API calls: 105 (successfully parsed)
- Actual cost: ~$10.50
- **Savings: 70% ($24.50)**

**Progress updates helped you**:
- Confirm 235 files were filtered (expected)
- See 105 files actually processed (API calls)
- Estimate cost mid-processing
- Verify AI classification working (~15%)

## Integration with Other Features

Progress updates work with all features:

### With Skip Logic
```
Progress Update: Processed 200/500 files
  Successfully parsed: 45
  Skipped (already processed): 150  ← From previous runs
  Filtered by year: 5
  Errors: 0
```

### With `--max-files`
```bash
$ uv run python parse_syllabi.py --max-files 250

Progress Update: Processed 100/250 files
  ...

Progress Update: Processed 200/250 files
  ...

# No update at 300 (only processing 250)
```

### With Different Years
```bash
$ uv run python parse_syllabi.py --min-year 2023

Progress Update: Processed 100/350 files
  Successfully parsed: 75
  Skipped (already processed): 0
  Filtered by year: 20  ← Less filtering with 2023+
  Errors: 5
```

## Troubleshooting

### Update Not Appearing

**Q**: Processed 50 files, no update yet?

**A**: Updates appear every 100 files. With 50 files, you'll only see the final summary.

**Solution**: For small collections, reduce update frequency:
```python
if idx % 25 == 0:  # Update every 25 files
```

### Skipped Count Seems High

**Q**: Why are so many files skipped?

**A**: Files already in `parsed_syllabi.json` are skipped. This is expected behavior for resuming processing.

**To start fresh**: Delete or rename `parsed_syllabi.json`

### Filtered Count Unexpected

**Q**: Too many/few files filtered?

**A**: Check the year detection:
- Progress updates show detected years
- Adjust `--min-year` if needed
- Files without years are processed (conservative)

## Performance Impact

Progress updates have **minimal performance impact**:
- Simple calculations (counters, percentages)
- Runs every 100 files (not every file)
- Total overhead: <0.1% of processing time
- Benefits far outweigh tiny overhead

## Future Enhancements

Potential improvements:
- Time estimation (ETA)
- Progress bar visualization
- Configurable update frequency via CLI
- Real-time token/cost tracking
- Periodic JSON saves (every N files)
