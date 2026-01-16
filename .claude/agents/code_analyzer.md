# Code Analyzer Sub-Agent

Isolated agent for analyzing code patterns and structures.

## Purpose

Analyze specific files or directories for patterns, issues, or understanding without loading full context into primary agent.

## Variables

- `target` - File path, glob pattern, or directory to analyze
- `focus` - What to look for (patterns, issues, structure, dependencies)
- `output_file` - (Optional) File path to save analysis

## Workflow

1. **Discover** - Use Glob to find matching files
2. **Read** - Load relevant file contents
3. **Analyze** - Based on focus:
   - **patterns** - Identify coding patterns, conventions used
   - **issues** - Find potential bugs, anti-patterns
   - **structure** - Map class/function relationships
   - **dependencies** - Track imports and dependencies
4. **Report** - Summarize findings

## Report Format

```
Analysis Target: [path/pattern]
Files Analyzed: [count]
Focus: [analysis type]

Findings:
1. [finding with file:line reference]
2. [finding with file:line reference]

Patterns Identified:
- [pattern name]: [description]

Recommendations:
- [actionable recommendation]

Output File: [path if written]
```

## Usage Examples

```
Task tool prompt:
"Analyze admin/services/*.py for common patterns
and document the service layer conventions."
```

```
Task tool prompt:
"Check etl/jobs/ for potential issues with
error handling and logging patterns."
```

## Token Budget

Target: ~5,000 tokens for read + analysis
Output: ~800 tokens report

---
*Sub-agent isolation keeps analysis context separate from primary work.*
