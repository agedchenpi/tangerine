# Doc Scraper Sub-Agent

Isolated agent for fetching and summarizing documentation from URLs.

## Purpose

Fetch web documentation and extract key information without bloating primary context.

## Variables

- `url` - Target URL to scrape
- `output_file` - (Optional) File path to save content
- `focus` - (Optional) Specific topics to extract

## Workflow

1. **Fetch** - Use WebFetch tool to retrieve URL content
2. **Extract** - Identify key sections:
   - API endpoints and parameters
   - Configuration options
   - Code examples
   - Installation steps
3. **Summarize** - Condense to essential information
4. **Output** - Write to file if specified, otherwise return summary

## Report Format

```
URL: [fetched url]
Title: [page title]
Word Count: [approximate]

Key Topics:
- [topic 1]
- [topic 2]

Summary:
[2-3 paragraph summary of key information]

Code Examples Found: [count]
Output File: [path if written]
```

## Usage Example

```
Task tool prompt:
"Fetch documentation from https://example.com/docs/api
and summarize the authentication methods.
Save to docs/api-auth-notes.md"
```

## Token Budget

Target: ~3,000 tokens for fetch + analysis
Output: ~500 tokens summary

---
*Sub-agent isolation saves ~3-5k tokens per delegation.*
