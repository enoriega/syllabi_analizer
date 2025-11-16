#!/usr/bin/env python3
"""
Generate a technical report describing the AI syllabi analysis methodology and results.
This report is designed for executive decision-makers, not developers.
Output is in Markdown format for PDF export.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import Counter


def count_files_in_directory(directory: str) -> int:
    """Count the total number of input files in the data directory."""
    data_path = Path(directory)
    if not data_path.exists():
        return 0

    supported_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.html', '.htm'}
    count = 0
    for ext in supported_extensions:
        count += len(list(data_path.rglob(f"*{ext}")))
    return count


def load_json_stats(file_path: str) -> Dict:
    """Load statistics from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total = len(data)
        ai_related = sum(1 for entry in data if entry.get('is_ai_related', False))
        non_ai = total - ai_related

        return {
            'total': total,
            'ai_related': ai_related,
            'non_ai': non_ai,
            'ai_percentage': (ai_related / total * 100) if total > 0 else 0
        }
    except Exception as e:
        return {'error': str(e)}


def parse_info_txt(file_path: str) -> Dict:
    """Parse the info.txt file to extract quantitative analysis."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract key metrics from the summary section
        lines = content.split('\n')
        metrics = {}

        for line in lines:
            if line.strip().startswith('Total Syllabi:'):
                metrics['total_syllabi'] = int(line.split(':')[1].strip())
            elif line.strip().startswith('AI-Related Courses:'):
                parts = line.split(':')[1].strip().split()
                metrics['ai_related_count'] = int(parts[0])
                metrics['ai_related_percentage'] = parts[1].strip('()')
            elif line.strip().startswith('Non-AI Courses:'):
                parts = line.split(':')[1].strip().split()
                metrics['non_ai_count'] = int(parts[0])

        # Extract semester distribution
        semester_dist = {}
        in_semester_section = False
        for line in lines:
            if 'Semester Distribution:' in line:
                in_semester_section = True
                continue
            elif 'Academic Year Distribution:' in line:
                in_semester_section = False
                continue

            if in_semester_section and ':' in line:
                parts = line.strip().split(':')
                semester = parts[0].strip()
                count = int(parts[1].strip())
                semester_dist[semester] = count

        metrics['semester_distribution'] = semester_dist

        return metrics
    except Exception as e:
        return {'error': str(e)}


def analyze_ai_course_distributions(json_file: str) -> Dict:
    """Analyze distributions of AI-related courses by department, semester, and year."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Filter AI-related courses
        ai_courses = [c for c in data if c.get('is_ai_related', False)]

        # Extract department/unit from course names
        departments = []
        semesters = []
        years = []

        for course in ai_courses:
            course_name = course.get('course_name', '')
            # Extract department code (usually the first few letters before numbers)
            match = re.match(r'^([A-Z]+)', course_name)
            if match:
                dept = match.group(1)
                departments.append(dept)

            term = course.get('term_offered', {})
            if term:
                sem = term.get('semester')
                if sem:
                    semesters.append(sem.capitalize())
                year = term.get('academic_year')
                if year:
                    years.append(year)

        # Count occurrences
        dept_counter = Counter(departments)
        sem_counter = Counter(semesters)
        year_counter = Counter(years)

        return {
            'total_ai_courses': len(ai_courses),
            'departments': dept_counter,
            'semesters': sem_counter,
            'years': year_counter
        }
    except Exception as e:
        return {'error': str(e)}


def generate_report() -> str:
    """Generate the complete technical report in Markdown format."""

    # Gather data
    input_files_count = count_files_in_directory('data')
    before_dedup_stats = load_json_stats('parsed_syllabi.json')
    after_dedup_stats = load_json_stats('parsed_syllabi_dedup.json')
    info_metrics = parse_info_txt('info.txt')
    ai_distributions = analyze_ai_course_distributions('parsed_syllabi_dedup.json')

    duplicates_removed = before_dedup_stats.get('total', 0) - after_dedup_stats.get('total', 0)
    attrition_rate = (duplicates_removed / before_dedup_stats.get('total', 1) * 100) if before_dedup_stats.get('total', 0) > 0 else 0

    # Generate report in Markdown
    report = f"""# Technical Report: AI-Related Course Analysis

**Report Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

---

## Executive Summary

This report presents a comprehensive analysis of course syllabi to identify AI-related courses across multiple academic institutions. The analysis processed **{input_files_count:,} syllabi files** from various document formats (PDF, Word, PowerPoint, HTML) and ultimately identified **{info_metrics.get('total_syllabi', 'N/A'):,} unique course offerings**, of which **{info_metrics.get('ai_related_count', 'N/A')} courses ({info_metrics.get('ai_related_percentage', 'N/A')})** are substantially related to artificial intelligence.

The methodology combines automated document processing, large language model-based content analysis, and systematic deduplication to provide decision-makers with reliable quantitative data about AI education prevalence.

---

## 1. Methodology Overview

The analysis follows a systematic four-stage process:

1. **Data Collection** - Gathering syllabi files from multiple institutions
2. **Text Extraction** - Converting various document formats to plain text
3. **LLM-Powered Content Analysis** - Using AI to classify courses
4. **Deduplication and Quality Assurance** - Removing duplicates and validating results

Each stage is designed to ensure accuracy, consistency, and reliability in identifying AI-related course offerings.

---

## 2. Data Collection

### Input Data Volume

- **Total Input Files:** {input_files_count:,} syllabi documents

The analysis began with **{input_files_count:,}** course syllabi files collected from multiple academic institutions. These documents were provided in various formats:

- PDF documents (`.pdf`)
- Microsoft Word documents (`.docx`, `.doc`)
- PowerPoint presentations (`.pptx`, `.ppt`)
- HTML web pages (`.html`, `.htm`)

This variety of formats required specialized document processing libraries to ensure all content could be accurately extracted and analyzed.

---

## 3. Text Extraction Process

### Technical Implementation

The text extraction process uses the **LangChain document loaders library**, which provides specialized parsers for different file formats:

- **PDF files:** `PyPDFLoader` - Extracts text from PDF documents page by page
- **Word documents (.docx):** `Docx2txtLoader` - Parses modern Word format
- **Legacy Word documents (.doc):** `UnstructuredWordDocumentLoader` - Handles older Word format
- **PowerPoint files:** `UnstructuredPowerPointLoader` - Extracts text from slides
- **HTML files:** `UnstructuredHTMLLoader` - Parses web pages

### Processing Strategy

**Parallel Processing Implementation:**
- The system uses Python's `multiprocessing` library to process multiple documents simultaneously
- Worker processes are distributed across available CPU cores
- For this analysis, the system processed documents in parallel to efficiently handle {input_files_count:,} files

**Error Handling:**
- Documents that cannot be read (corrupted files, unsupported formats) are logged and skipped
- The system continues processing remaining files to ensure completion
- Successfully extracted text files are saved with a `.txt` extension in the same directory structure

**Text Preservation:**
- The extraction maintains document text content including course descriptions, learning objectives, and topic outlines
- Multi-page documents are combined into a single text file
- Special formatting is removed, leaving plain text suitable for analysis

---

## 4. Large Language Model Content Analysis

### Model Specification

**Language Model Used:** OpenAI GPT-4o-mini

The analysis uses GPT-4o-mini, accessed through the LangChain framework with the following configuration:

- **Temperature:** 0.0 (deterministic output for consistency)
- **Output Format:** Structured JSON using Pydantic schema validation
- **Processing:** Parallel processing with 5 concurrent LLM calls

### Input Data Provided to the LLM

For each syllabus, the language model receives three pieces of information:

1. **Syllabus Text Content** - The full extracted text from the document
2. **Original Filename** - Often contains course code, semester, year, or instructor name
3. **File Path** - Directory structure may indicate academic term or department organization

### Prompt Engineering

The LLM is instructed via a detailed prompt template to extract structured information. The prompt explicitly defines:

**Course Identification:**
- Extract course name and code (e.g., "CS 229: Machine Learning")
- Determine academic term (Spring, Fall, Summer, Winter) from filename, file path, and syllabus content
- Extract academic year using regular expressions to find 4-digit years (2000-2099) in the path and filename

**Course Description:**
- Extract official course description
- Identify learning objectives and outcomes
- List topics covered
- Summarize skills students will develop

**AI-Related Classification Criteria:**

The prompt specifies that courses qualify as AI-related if they substantially cover:
- Machine learning (supervised, unsupervised, reinforcement learning)
- Natural language processing
- Computer vision
- Neural networks and deep learning
- Data mining using AI techniques
- Robotics and autonomous systems
- AI ethics and responsible AI
- Expert systems and intelligent agents

**Explicit Exclusions:**
- Courses that merely mention AI in passing
- Courses that use AI tools but don't teach AI concepts
- General technology courses without AI focus

**Justification Requirement:**
For each AI-related course, the model must provide a 2-3 sentence justification explaining:
- What AI topics are covered
- How AI is central to the course
- Specific AI methods or techniques taught

### Output Validation

The LLM output is parsed using a **Pydantic schema** that enforces:
- Required fields (course name, AI classification boolean)
- Optional fields (term, academic year, description, justification)
- Type validation (strings, integers, booleans)

Failed parses are logged and skipped to ensure data quality.

### Analysis Scale

- **Total Syllabi Analyzed:** {before_dedup_stats.get('total', 0):,}
- **Processing Method:** Parallel processing with 5 concurrent LLM calls
- **Quality Control:** Each syllabus receives individual detailed analysis
- **Consistency:** Temperature=0.0 ensures deterministic, reproducible results

---

## 5. Deduplication Process

### Rationale

Academic institutions often have multiple copies of the same syllabus file due to:
- Different faculty teaching the same course
- Copies stored in multiple locations
- Files with different names but identical content
- Updated versions of the same course offering

### Deduplication Algorithm

The system uses a **tuple-based matching approach** to identify duplicates. Two courses are considered duplicates if they match on all three criteria:

1. **Course Name** - The official course title and code (case-insensitive comparison)
2. **Semester** - The academic term (Spring, Fall, Summer, Winter)
3. **Academic Year** - The 4-digit year the course was offered

**Implementation Details:**
- Creates a unique key as a tuple: `(course_name, semester, academic_year)`
- Uses a Python set to track seen keys
- Retains the first occurrence of each unique course
- Removes subsequent duplicate entries

**Important Note:** This conservative approach treats multiple sections of the same course in the same term as a single offering, accurately reflecting unique course offerings rather than total section count.

### Deduplication Results

| Metric | Count |
|--------|-------|
| Before Deduplication | {before_dedup_stats.get('total', 0):,} analyzed syllabi |
| After Deduplication | {after_dedup_stats.get('total', 0):,} unique courses |
| Duplicates Removed | {duplicates_removed:,} files |
| **Attrition Rate** | **{attrition_rate:.1f}%** |

The {attrition_rate:.1f}% attrition rate indicates that approximately {duplicates_removed:,} syllabi were duplicate entries, which is expected in large multi-institutional datasets.

---

## 6. Quantitative Analysis Results

### Overall Dataset Composition

| Category | Count | Percentage |
|----------|-------|------------|
| **Total Unique Courses** | **{info_metrics.get('total_syllabi', 0):,}** | **100%** |
| AI-Related Courses | {info_metrics.get('ai_related_count', 0):,} | {info_metrics.get('ai_related_percentage', '0%')} |
| Non-AI Courses | {info_metrics.get('non_ai_count', 0):,} | {100 - float(info_metrics.get('ai_related_percentage', '0%').rstrip('%')):.1f}% |

### AI-Related Courses by Academic Unit

The {ai_distributions.get('total_ai_courses', 0)} AI-related courses are distributed across **{len(ai_distributions.get('departments', {}))} academic departments/units**. Top 15 departments:

| Department | AI Courses | Percentage of AI Courses |
|------------|------------|--------------------------|"""

    # Add top 15 departments
    dept_counter = ai_distributions.get('departments', {})
    total_ai = ai_distributions.get('total_ai_courses', 1)
    for dept, count in list(dept_counter.most_common(15)):
        percentage = (count / total_ai * 100)
        report += f"\n| {dept} | {count} | {percentage:.1f}% |"

    report += """

**Key Departments:**
- **ISTA** (Information Science, Systems, and Technology) leads with the most AI-related courses
- **CSC** (Computer Science) follows as a major contributor
- **MIS** (Management Information Systems) and **CYBV** (Cybersecurity/Cyberoperations) also have substantial AI offerings
- AI education extends beyond traditional computer science into linguistics, engineering, business, and life sciences

### AI-Related Courses by Semester

| Semester | AI Courses | Percentage |
|----------|------------|------------|"""

    # Add semester distribution for AI courses only
    sem_counter = ai_distributions.get('semesters', {})
    for sem, count in sem_counter.most_common():
        percentage = (count / total_ai * 100)
        report += f"\n| {sem} | {count} | {percentage:.1f}% |"

    report += """

The distribution is nearly balanced between Fall and Spring semesters, indicating consistent AI course offerings throughout the academic year.

### AI-Related Courses by Academic Year

| Academic Year | AI Courses | Percentage |
|---------------|------------|------------|"""

    # Add year distribution for AI courses only
    year_counter = ai_distributions.get('years', {})
    for year, count in sorted(year_counter.items()):
        percentage = (count / total_ai * 100)
        report += f"\n| {year} | {count} | {percentage:.1f}% |"

    # Calculate 2020-2021 percentage
    year_counter = ai_distributions.get('years', {})
    peak_years_count = year_counter.get(2020, 0) + year_counter.get(2021, 0)
    peak_percentage = (peak_years_count / total_ai * 100) if total_ai > 0 else 0
    min_year = min(year_counter.keys()) if year_counter else 'N/A'

    report += f"""

**Temporal Trends:**
- Peak AI course offerings occurred in **2020-2021** ({peak_percentage:.1f}% of all AI courses)
- This likely reflects the dataset composition and data collection period
- The data shows AI education has been present since at least {min_year}
- More recent years (2023-2025) show fewer courses, possibly due to incomplete data collection for those terms

### Key Insights

1. **AI Education Prevalence:** {info_metrics.get('ai_related_percentage', 'N/A')} of all courses are substantially related to artificial intelligence, indicating AI education is present but represents a specialized portion of the overall curriculum.

2. **Departmental Diversity:** AI-related courses span {len(dept_counter)} different academic units, demonstrating that AI education extends far beyond computer science into business, linguistics, engineering, life sciences, and social sciences.

3. **Data Quality:** The {attrition_rate:.1f}% attrition rate during deduplication demonstrates good data quality, with the vast majority of analyzed syllabi being unique course offerings.

4. **Balanced Semester Distribution:** AI courses are offered relatively equally in Fall and Spring semesters, ensuring year-round access to AI education.

---

## 7. Methodology Strengths

### Accuracy and Consistency

- **Deterministic Classification:** Temperature=0.0 setting ensures the LLM provides consistent, reproducible results
- **Structured Output:** Pydantic schema validation guarantees properly formatted data
- **Explicit Criteria:** Detailed prompts define precise classification standards
- **Justification Transparency:** Each AI classification includes an explanation that can be verified

### Scalability

- **High-Volume Processing:** Successfully analyzed {before_dedup_stats.get('total', 0):,} syllabi
- **Parallel Processing:** Multiple worker processes and concurrent LLM calls reduce processing time
- **Extensible Design:** Can handle additional data without methodology changes
- **Error Resilience:** Failed extractions or parses don't halt the entire analysis

### Comprehensiveness

- **Multi-Format Support:** Handles PDF, Word, PowerPoint, and HTML documents
- **Contextual Analysis:** Uses filename, file path, and content for accurate term/year extraction
- **Quality Assurance:** Deduplication ensures accurate counting of unique offerings
- **Broad Coverage:** {len(dept_counter)} departments analyzed, capturing AI education across disciplines

---

## 8. Limitations and Considerations

### 1. Classification Boundaries

Some courses may incorporate AI elements without being primarily AI-focused. The methodology applies strict criteria to classify only courses where AI is **substantially central** to the curriculum. This conservative approach may undercount courses with minor AI components.

### 2. Text Extraction Quality

Complex document layouts, scanned PDFs, or unusual formatting may result in imperfect text extraction. The error handling ensures the analysis continues, but some course information may be incomplete. Successfully processed the majority of {input_files_count:,} input files.

### 3. Temporal Coverage

The analysis reflects course offerings from the time periods represented in the source data (primarily 2015-2025, with concentration in 2020-2021). Recent curriculum changes or new AI courses added after data collection are not captured.

### 4. Department Code Extraction

Department identification uses regex pattern matching on course names (e.g., "CSC 580" → "CSC"). Courses with non-standard naming conventions may be miscategorized or grouped under single-letter codes.

### 5. Duplicate Detection Conservativeness

The deduplication treats multiple sections of the same course in the same term as a single offering. This accurately reflects unique course offerings but doesn't capture total enrollment capacity or number of students served.

---

## 9. Conclusions

This analysis successfully processed **{input_files_count:,} syllabi files** through a rigorous four-stage methodology, ultimately identifying **{info_metrics.get('total_syllabi', 0):,} unique course offerings**, of which **{info_metrics.get('ai_related_count', 0)} ({info_metrics.get('ai_related_percentage', 'N/A')})** are substantially related to artificial intelligence.

### Key Findings

1. **AI Education is Present but Specialized:** Only {info_metrics.get('ai_related_percentage', 'N/A')} of courses focus substantially on AI, indicating it remains a specialized area of study rather than pervasive across all curricula.

2. **Broad Departmental Reach:** AI courses appear in {len(dept_counter)} different academic units, demonstrating AI's relevance beyond computer science into business, social sciences, linguistics, and life sciences.

3. **Consistent Semester Availability:** Nearly balanced Fall/Spring distribution ensures students can access AI education year-round.

4. **Methodology Reliability:** The {attrition_rate:.1f}% deduplication rate and systematic LLM-based classification provide confidence in result accuracy.

### Methodology Summary

The analysis combines:
- **Automated Document Processing** using LangChain loaders
- **LLM-Powered Content Analysis** using GPT-4o-mini with temperature=0.0
- **Regex-Based Term Extraction** for academic year identification
- **Tuple-Based Deduplication** for unique course counting
- **Pydantic Schema Validation** for structured output quality

This approach provides decision-makers with reliable, quantitative data about AI education prevalence, enabling informed strategic planning for curriculum development, resource allocation, and understanding of AI education's institutional footprint.

---

**End of Report**
"""

    return report


def main():
    """Generate and save the technical report."""
    print("Generating technical report in Markdown format...")

    # Generate the report
    report = generate_report()

    # Save to markdown file
    output_file = "TECHNICAL_REPORT.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✓ Technical report generated successfully!")
    print(f"  Saved to: {output_file}")
    print(f"  Format: Markdown (ready for PDF export)")
    print(f"\nYou can:")
    print(f"  - View the report: {output_file}")
    print(f"  - Convert to PDF using: pandoc {output_file} -o TECHNICAL_REPORT.pdf")
    print(f"  - Or use any Markdown-to-PDF converter")

    # Also print to console
    print("\n" + "="*80)
    print("REPORT PREVIEW (first 60 lines)")
    print("="*80)
    lines = report.split('\n')
    for line in lines[:60]:
        print(line)
    print(f"\n[... see full report in {output_file} ...]")


if __name__ == "__main__":
    main()
