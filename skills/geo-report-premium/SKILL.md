---
name: geo-report-premium
description: >
  Premium co-branded PDF report generator. Extracts client brand colors
  from their website, combines with consultant brand, and produces a
  professional co-branded GEO audit report. Use when user says
  "premium report", "branded report", "co-branded", "client report",
  "white-label report", or "report-premium".
allowed-tools: Read, Bash, WebFetch, Write
---

# Premium Co-Branded GEO Report Skill

## Purpose
Generate a professional, co-branded PDF report that uses the client's
brand colors (auto-extracted from their website) alongside the consultant's
brand identity.

## What Makes It "Premium"

| Feature | Standard Report | Premium Report |
|---------|----------------|----------------|
| Color scheme | Fixed navy/coral | Client brand colors (auto-extracted) |
| Branding | Generic header | Co-branded: consultant + client names |
| Cover page | Basic title | Consultant brand top-right, client name in accent color |
| Accent bars | None | Top + bottom of every page in client brand color |
| Charts | Fixed colors | Score gauges/bars adapt to client palette |
| Footer | Generic | "Prepared for [Client] by [Consultant]" |
| Color source | Hardcoded | Extracted from theme-color, CSS vars, header BG, or frequent hex |

## Executable Commands

### Basic usage (auto-extract client colors)
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf
```

### With consultant name
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf \
  --consultant-name "Your Brand Name"
```

### Extract colors from specific URL
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf \
  --client-url https://example.com \
  --consultant-name "Your Brand Name"
```

### Override colors manually
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf \
  --client-color "#2563eb" \
  --consultant-color "#1a1a2e" \
  --consultant-name "Your Brand Name"
```

### Generate sample report
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py
```

## Brand Color Extraction

The script extracts the client's primary brand color by checking (in order):
1. `<meta name="theme-color">` tag
2. `<meta name="msapplication-TileColor">` tag
3. CSS custom properties (`--primary-color`, `--brand-color`, `--main-color`)
4. Inline `background-color` on `<header>` or `<nav>` elements
5. Most frequently used non-grey hex color in the page (minimum 3 occurrences)

If extraction fails, it falls back to a professional blue default (#2563eb).

## Theme Generation

From a single primary color, the script derives a complete palette:
- **Dark variant** — darkened 20% (for header backgrounds)
- **Light variant** — lightened 35% (for highlights and hover states)
- **Background variant** — lightened 45% (for table row alternation)
- **Text color** — automatically white or dark based on luminance contrast

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--client-url` | URL to extract brand colors from | Uses `url` from JSON data |
| `--client-color` | Override client primary color (hex) | Auto-extracted or #2563eb |
| `--consultant-name` | Your brand name for co-branding | (none) |
| `--consultant-color` | Override consultant primary color (hex) | #1a1a2e (navy) |

## Input JSON Structure

Same as `generate_pdf_report.py` — accepts the standard audit data JSON:
```json
{
  "url": "https://example.com",
  "brand_name": "Example Co",
  "date": "2026-03-09",
  "geo_score": 58,
  "scores": { "ai_citability": 45, ... },
  "platforms": { "ChatGPT": 52, ... },
  "findings": [ ... ],
  "crawler_access": { ... },
  "quick_wins": [ ... ],
  "medium_term": [ ... ],
  "strategic": [ ... ]
}
```

## Output

`GEO-PREMIUM-REPORT.pdf` — Professional PDF with:
- Co-branded cover page
- Dynamic color theme matching client brand
- Score gauge and bar charts in brand colors
- Platform readiness horizontal bars
- Color-coded crawler access table
- Severity-tagged findings
- Prioritized action plan (Quick Wins / Medium-Term / Strategic)
- Methodology appendix with glossary

## Workflow

1. Run `/geo audit <url>` first to collect all data
2. Run `/geo report-premium <url>` to generate the premium PDF
3. The tool compiles audit data into JSON, fetches client colors, generates PDF
4. Output: `GEO-PREMIUM-REPORT.pdf` in the current directory

## Dependencies

- `reportlab` (already in requirements.txt)
- No additional dependencies
