---
name: geo-report-premium
description: >
  Premium co-branded PDF report generator with dark mode. Extracts client
  brand colors from their website, combines with consultant brand, and
  produces a professional co-branded GEO audit report. Supports light and
  dark themes. Use when user says "premium report", "branded report",
  "co-branded", "client report", "white-label report", "dark report",
  "dark mode report", or "report-premium".
allowed-tools: Read, Bash, WebFetch, Write
---

# Premium Co-Branded GEO Report Skill (v2)

## Purpose
Generate a professional, co-branded PDF report that uses the client's
brand colors (auto-extracted from their website) alongside the consultant's
brand identity. Supports both light and dark themes.

## What Makes It "Premium"

| Feature | Standard Report | Premium Report |
|---------|----------------|----------------|
| Color scheme | Fixed navy/coral | Client brand colors (auto-extracted) |
| Branding | Generic header | Co-branded: consultant + client names |
| Cover page | Basic title + gauge | 2-column: gauge + key highlights |
| Dark mode | No | Full dark theme with `--dark` flag |
| Accent bars | None | Top + bottom of every page in brand color |
| Charts | Fixed colors | Score gauges/bars adapt to client palette |
| Footer | Generic | "Prepared for [Client] by [Consultant]" |
| Executive summary | 1 sentence | 4 auto-generated paragraphs |
| Findings | Description only | + business impact explanation per finding |
| Action plan | Items only | + effort, score impact, difficulty per item |
| Forecast | None | Score Improvement Forecast table |
| Next steps | None | CTA section with consultant contact |
| Layout | Page breaks everywhere | KeepTogether — headers never orphaned |

## Executable Commands

### Light mode (default)
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf \
  --consultant-name "Your Brand Name"
```

### Dark mode
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf \
  --consultant-name "Your Brand Name" --dark
```

### Extract colors from client website
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf \
  --client-url https://example.com --consultant-name "Your Brand Name"
```

### Override colors manually
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py data.json GEO-PREMIUM-REPORT.pdf \
  --client-color "#2563eb" --consultant-name "Your Brand Name" --dark
```

### Generate sample report
```bash
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py
python3 ~/.claude/skills/geo/scripts/generate_premium_report.py --dark
```

## CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `--client-url` | URL to extract brand colors from | Uses `url` from JSON data |
| `--client-color` | Override client primary color (hex) | Auto-extracted or #2563eb |
| `--consultant-name` | Your brand name for co-branding | (none) |
| `--consultant-color` | Override consultant primary color (hex) | #1a1a2e (navy) |
| `--dark` | Enable dark mode (dark background, light text) | Light mode |

## Dark Mode

The `--dark` flag produces a stunning dark-themed report:
- Page background: `#0d1117` (GitHub-dark near-black)
- Text: `#e8eaed` (light grey-white)
- Table headers: `#1e2a3a` (dark slate) with accent-colored text
- Table rows: Alternating `#0d1117` and `#1e2530`
- Grid lines: `#2d3748` (subtle dark borders)
- Accent colors: Brighter variant of client color for dark-bg contrast
- Gauge: Dark inner circle, glowing accent ring
- Charts: Dark axis lines with light text labels

## Brand Color Extraction

Checks (in priority order):
1. `<meta name="theme-color">` tag
2. CSS custom properties (`--primary-color`, `--brand-color`, `--main-color`)
3. Inline `background-color` on `<header>` or `<nav>` elements
4. Most frequently used non-grey hex color (min 3 occurrences)

Falls back to professional blue (#2563eb) if extraction fails.

## Report Sections

1. **Cover page** — 2-column: gauge + key stats (website, score, strongest/weakest, critical issues, blocked crawlers)
2. **Key Highlights** — One-line summary bar with projected score
3. **Executive Summary** — 4 auto-generated paragraphs (score context, strongest/weakest, platforms, improvement estimate)
4. **Score Breakdown** — Table + bar chart (KeepTogether)
5. **AI Platform Readiness** — Horizontal bars with platform insights
6. **Crawler Access** — Status table with color-coded Allow/Block
7. **Key Findings** — Each with severity tag, description, and "Why this matters" business impact
8. **Score Improvement Forecast** — Current → Quick Wins → Medium-Term → Strategic projected scores
9. **Action Plan** — Three tiers with effort/score/difficulty estimates per item
10. **Next Steps** — CTA with consultant contact
11. **Methodology + Glossary** — Compact appendix

## Workflow

1. Run `/geo audit <url>` first to collect all data
2. Run `/geo report-premium <url>` or `/geo report-premium <url> --dark`
3. Output: `GEO-PREMIUM-REPORT.pdf`
