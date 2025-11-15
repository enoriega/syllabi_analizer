# Troubleshooting Guide

## Common Issues and Solutions

### PDF Parsing Warnings

#### Issue: "Ignoring wrong pointing object" warnings

**Symptoms**:
```
Ignoring wrong pointing object 187 0 (offset 0)
Ignoring wrong pointing object 200 0 (offset 0)
```

**What it means**:
The PDF file has minor structural issues or was created by software that doesn't perfectly follow the PDF specification. This is very common and usually doesn't affect text extraction.

**Solution**:
These warnings are now automatically suppressed in `extract_text.py` (v1.1+). The text extraction continues normally despite these warnings.

**If you still see them**:
- The PDFs are still being processed correctly
- The warnings are informational only
- Text extraction quality is not affected
- You can safely ignore them

**Root causes**:
- PDFs created by different editing software
- Scanned/OCR PDFs with inconsistent structure
- Combined or edited PDFs
- Annotations or form fields in PDFs

---

### Empty Extracted Text

#### Issue: Extracted `.txt` file is empty or has very little content

**Possible causes**:

1. **Image-based PDF (no text layer)**
   - The PDF is a scan without OCR
   - Solution: Run OCR on the PDF first, or use an OCR-capable extraction tool

2. **Encrypted/Protected PDF**
   - The PDF has security restrictions
   - Solution: Remove protection or use the original unprotected version

3. **Corrupted PDF**
   - The file is damaged
   - Solution: Try opening in a PDF reader to verify, may need to re-download or recover

**How to check**:
```bash
# Try opening the PDF manually
open "path/to/file.pdf"

# Check if text is selectable in the PDF viewer
# If you can't select text, it's likely an image-based PDF
```

---

### Multiprocessing Issues

#### Issue: Script hangs or doesn't complete

**On macOS/Windows**:
The issue might be with multiprocessing module initialization.

**Solution**:
```bash
# Try with fewer workers
uv run python extract_text.py --workers 2

# Or use sequential processing
uv run python extract_text.py --no-parallel
```

#### Issue: "Broken pipe" or "Connection refused" errors

**Cause**: Too many worker processes for available system resources

**Solution**:
```bash
# Reduce number of workers
uv run python extract_text.py --workers 4
```

---

### Memory Issues

#### Issue: Out of memory errors or system slowdown

**Cause**: Processing very large files with too many workers

**Solution**:
```bash
# Reduce workers to lower memory usage
uv run python extract_text.py --workers 2

# Or process specific subdirectories
uv run python extract_text.py --data-dir data/subfolder
```

**Memory estimation**:
- Memory usage ≈ (avg file size) × (num workers) × 3
- Example: 10MB PDFs × 12 workers = ~360MB peak usage
- For 100MB+ files, use fewer workers (2-4)

---

### LLM Parsing Issues

#### Issue: Year not detected correctly

**Example**:
```
⚠ Could not determine year from path, processing anyway
```

**Solution**:
The script uses a conservative approach and processes files when year can't be determined. To skip these:

1. Ensure files are in year-labeled directories: `data/Spring 2024/...`
2. Or include year in filename: `course_2024.pdf`

**Year detection patterns**:
- `Spring 2024`, `Fall2023`, `2024_Spring`
- Directory paths: `data/2024/course.pdf`
- Looks for 4-digit years (2000-2099)

#### Issue: API Rate Limits

**Symptoms**:
```
Error: Rate limit exceeded
Error: Too many requests
```

**Solution**:
```bash
# Process in smaller batches
uv run python parse_syllabi.py --max-files 50

# Wait a few minutes between batches
# Or adjust your API tier/quota
```

#### Issue: LLM returns invalid JSON

**Symptoms**:
```
Error parsing syllabus: Invalid JSON
Error: Validation error
```

**Solutions**:
1. **Use a better model**: GPT-4 is more reliable than GPT-3.5
2. **Check the syllabus text**: Very long or malformed text can cause issues
3. **Retry**: Sometimes transient issues resolve on retry

---

### File Permission Issues

#### Issue: Permission denied when writing files

**Solution**:
```bash
# Check directory permissions
ls -la data/

# Make directories writable
chmod -R u+w data/

# Or specify a different output directory you own
uv run python extract_text.py --output-dir ~/output
```

---

### Environment Setup Issues

#### Issue: Module not found errors

**Solution**:
```bash
# Reinstall dependencies
uv sync

# Or force reinstall
uv sync --reinstall
```

#### Issue: .env file not found

**For parse_syllabi.py**:
```bash
# Create from example
cp .env.example .env

# Edit with your credentials
nano .env
```

---

### Performance Tuning

#### Finding optimal worker count

**Test different configurations**:
```bash
# Time sequential
time uv run python extract_text.py --no-parallel --data-dir test_data

# Time with 4 workers
time uv run python extract_text.py --workers 4 --data-dir test_data

# Time with all cores
time uv run python extract_text.py --data-dir test_data
```

**Guidelines**:
- **CPU-bound tasks** (complex PDFs): Use all cores
- **I/O-bound tasks** (simple files): Use 2× CPU cores
- **Memory-constrained**: Use fewer workers
- **Networked storage**: Use fewer workers (4-6)

---

## Getting More Help

### Enable Debug Mode

For more detailed error information:

```python
# In extract_text.py or parse_syllabi.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Logs

Look for error details in terminal output:
- `✓` = Success
- `⊙` = Skipped
- `✗` = Error (with details)

### Test with Single File

```bash
# Create a test directory with one file
mkdir test_single
cp "data/some_file.pdf" test_single/

# Process just that file
uv run python extract_text.py --data-dir test_single --no-parallel
```

### Report Issues

If you encounter persistent issues:

1. Note the error message
2. Check which file caused the issue
3. Try to reproduce with a single file
4. Check if the file is readable/valid
5. Note your system (OS, Python version, CPU cores)

### Common Error Patterns

**"Cannot find module 'X'"**
→ Run `uv sync` to install dependencies

**"Permission denied"**
→ Check file/directory permissions

**"No such file or directory"**
→ Verify paths are correct and files exist

**"Rate limit exceeded"**
→ Reduce batch size or wait between runs

**"Memory error"**
→ Reduce number of workers or process fewer files
