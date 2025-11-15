# Bug Fix: UnboundLocalError in parse_syllabi.py

## Issue

When running `parse_syllabi.py` with no files to process (e.g., all files already processed or filtered out), the script would crash with:

```
UnboundLocalError: cannot access local variable 'success_count' where it is not associated with a value
```

## Root Cause

The variables `success_count` and `error_count` were only initialized inside the `else` block (when there were tasks to process), but they were used in the summary output section that executes regardless of whether tasks existed.

```python
if not tasks:
    print("No new files to process!")
else:
    # Process files
    ...
    # Collect successful results
    success_count = 0  # Only initialized here
    error_count = 0    # Only initialized here
    ...

# This code runs whether or not there were tasks
print(f"  Successfully parsed (new): {success_count}")  # ERROR if no tasks!
```

## Fix

Moved the initialization of `success_count` and `error_count` before the `if not tasks` check:

```python
# Initialize counters
success_count = 0
error_count = 0

if not tasks:
    print("No new files to process!")
else:
    # Process files
    ...
```

This ensures the variables are always defined, even when there are no tasks to process.

## Testing

Tested both scenarios:

### Scenario 1: No files to process
```bash
uv run python parse_syllabi.py --max-files 2 --workers 2 --min-year 2020
```

Result: ✓ No error, clean summary output

### Scenario 2: Sequential mode with no files
```bash
uv run python parse_syllabi.py --max-files 1 --no-parallel --min-year 2020
```

Result: ✓ No error, clean summary output

## Files Modified

- `parse_syllabi.py` (lines 412-414): Added initialization before conditional block

## Status

✓ Fixed and tested
