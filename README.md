<p align="center">
  <img src="assets/banner.svg" alt="GEO-SEO Claude Code Skill" width="900"/>
</p>

<p align="center">
  <strong>GEO-first, SEO-supported.</strong> Optimize websites for AI-powered search engines<br/>
  (ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews) while maintaining traditional SEO foundations.
</p>

<p align="center">
  AI search is eating traditional search. This tool optimizes for where traffic is going, not where it was.
</p>

---

## Why GEO Matters (2026)

| Metric | Value |
|--------|-------|
| GEO services market | $850M+ (projected $7.3B by 2031) |
| AI-referred traffic growth | +527% year-over-year |
| AI traffic converts vs organic | 4.4x higher |
| Gartner: search traffic drop by 2028 | -50% |
| Brand mentions vs backlinks for AI | 3x stronger correlation |
| Marketers investing in GEO | Only 23% |

---

## Quick Start

### One-Command Install (macOS/Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/mysquishy/geo-seo-claude/main/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/mysquishy/geo-seo-claude.git
cd geo-seo-claude
./install.sh
```

### Requirements

- Python 3.8+
- Claude Code CLI
- Git
- Optional: Playwright (for screenshots)

---

## Commands

Open Claude Code and use these commands:

| Command | What It Does |
|---------|-------------|
| `/geo audit <url>` | Full GEO + SEO audit with parallel subagents |
| `/geo quick <url>` | 60-second GEO visibility snapshot |
| `/geo citability <url>` | Score content for AI citation readiness |
| `/geo crawlers <url>` | Check AI crawler access (robots.txt) |
| `/geo llmstxt <url>` | Analyze or generate llms.txt |
| `/geo brands <url>` | Scan brand mentions across AI-cited platforms |
| `/geo platforms <url>` | Platform-specific optimization |
| `/geo schema <url>` | Structured data analysis & generation |
| `/geo technical <url>` | Technical SEO audit |
| `/geo content <url>` | Content quality & E-E-A-T assessment |
| `/geo report <url>` | Generate client-ready GEO report |
| `/geo report-pdf` | Generate professional PDF report with charts & visualizations |

---

## Architecture

```
geo-seo-claude/
├── geo/                          # Main skill orchestrator
│   └── SKILL.md                  # Primary skill file with commands & routing
├── skills/                       # 11 specialized sub-skills
│   ├── geo-audit/                # Full audit orchestration & scoring
│   ├── geo-citability/           # AI citation readiness scoring
│   ├── geo-crawlers/             # AI crawler access analysis
│   ├── geo-llmstxt/              # llms.txt standard analysis & generation
│   ├── geo-brand-mentions/       # Brand presence on AI-cited platforms
│   ├── geo-platform-optimizer/   # Platform-specific AI search optimization
│   ├── geo-schema/               # Structured data for AI discoverability
│   ├── geo-technical/            # Technical SEO foundations
│   ├── geo-content/              # Content quality & E-E-A-T
│   ├── geo-report/               # Client-ready markdown report generation
│   └── geo-report-pdf/           # Professional PDF report with charts
├── agents/                       # 5 parallel subagents
│   ├── geo-ai-visibility.md      # GEO audit, citability, crawlers, brands
│   ├── geo-platform-analysis.md  # Platform-specific optimization
│   ├── geo-technical.md          # Technical SEO analysis
│   ├── geo-content.md            # Content & E-E-A-T analysis
│   └── geo-schema.md             # Schema markup analysis
├── scripts/                      # Python utilities
│   ├── fetch_page.py             # Page fetching & parsing
│   ├── citability_scorer.py      # AI citability scoring engine
│   ├── brand_scanner.py          # Brand mention detection
│   ├── llmstxt_generator.py      # llms.txt validation & generation
│   ├── generate_pdf_report.py    # PDF report generator (ReportLab)
│   ├── security_headers_fix.py   # Security header audit + server-specific fix configs
│   ├── robots_fix.py             # robots.txt AI crawler access fixer & merger
│   ├── meta_tags_fix.py          # Meta/OG/Twitter tag audit + HTML snippet generator
│   ├── image_audit_fix.py        # Image optimization audit + corrected tags & WebP commands
│   ├── sitemap_generator.py      # XML sitemap generator from crawled pages
│   └── indexnow_generator.py     # IndexNow key file, submission scripts & n8n config
├── tests/                        # Test suite (167 tests)
│   ├── test_citability_scorer.py # Scoring logic, grades, year pattern tests
│   ├── test_fetch_page.py        # Sitemap URL parsing, content extraction tests
│   ├── test_brand_scanner.py     # Brand mention scanning, Wikipedia API mocking
│   ├── test_llmstxt_generator.py # llms.txt validation and generation tests
│   ├── test_generate_pdf_report.py # PDF report data structures, color logic
│   └── test_fix_generators.py    # All 6 fix generators: headers, robots, meta, images, sitemap, indexnow
├── schema/                       # JSON-LD templates
│   ├── organization.json         # Organization schema (with sameAs)
│   ├── local-business.json       # LocalBusiness schema
│   ├── article-author.json       # Article + Person schema (E-E-A-T)
│   ├── software-saas.json        # SoftwareApplication schema
│   ├── product-ecommerce.json    # Product schema with offers
│   └── website-searchaction.json # WebSite + SearchAction schema
├── install.sh                    # One-command installer
├── uninstall.sh                  # Uninstaller
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## How It Works

### Full Audit Flow

When you run `/geo audit https://example.com`:

1. **Discovery** — Fetches homepage, detects business type, crawls sitemap
2. **Parallel Analysis** — Launches 5 subagents simultaneously:
   - AI Visibility (citability, crawlers, llms.txt, brand mentions)
   - Platform Analysis (ChatGPT, Perplexity, Google AIO readiness)
   - Technical SEO (Core Web Vitals, SSR, security, mobile)
   - Content Quality (E-E-A-T, readability, freshness)
   - Schema Markup (detection, validation, generation)
3. **Resilience** — If any agent fails, the orchestrator continues with available results, re-weights the composite score proportionally, and flags incomplete sections (see Agent Failure Handling in `geo/SKILL.md`)
4. **Synthesis** — Aggregates scores, generates composite GEO Score (0-100)
5. **Report** — Outputs prioritized action plan with quick wins

### Scoring Methodology

| Category | Weight |
|----------|--------|
| AI Citability & Visibility | 25% |
| Brand Authority Signals | 20% |
| Content Quality & E-E-A-T | 20% |
| Technical Foundations | 15% |
| Structured Data | 10% |
| Platform Optimization | 10% |

---

## Key Features

### Citability Scoring
Analyzes content blocks for AI citation readiness. Optimal AI-cited passages are 134-167 words, self-contained, fact-rich, and directly answer questions.

### AI Crawler Analysis
Checks robots.txt for 14+ AI crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.) and provides specific allow/block recommendations.

### Brand Mention Scanning
Brand mentions correlate 3x more strongly with AI visibility than backlinks. Scans YouTube, Reddit, Wikipedia, LinkedIn, and 7+ other platforms.

### Platform-Specific Optimization
Only 11% of domains are cited by both ChatGPT and Google AI Overviews for the same query. Provides tailored recommendations per platform.

### llms.txt Generation
Generates the emerging llms.txt standard file that helps AI crawlers understand your site structure.

### Client-Ready Reports
Generates professional GEO reports in markdown or PDF format. PDF reports include score gauges, bar charts, platform readiness visualizations, color-coded tables, and prioritized action plans — ready to deliver to clients.

### Agent Failure Resilience
Full audits gracefully handle agent failures with automatic retry, proportional score re-weighting, and Data Completeness reporting. See the detailed specification in `geo/SKILL.md`.

---

## Testing

Run the test suite (167 tests) from the repo root:

```bash
python3 -m pytest tests/ -v
```

Tests cover citability scoring logic, grade boundaries, dynamic year pattern matching, sitemap URL parsing (regression tests for a fixed bug), HTML content block extraction, brand mention scanning (with mocked Wikipedia/Wikidata APIs), llms.txt validation and generation (page categorization, format checks), PDF report data structures (color logic, score mapping, action plan tiers), and all 6 fix generators (security headers with server detection, robots.txt parsing and merging, meta tag auditing, image optimization, sitemap XML generation, and IndexNow implementation).

---

## Use Cases

- **GEO Agencies** — Run client audits and generate deliverables
- **Marketing Teams** — Monitor and improve AI search visibility
- **Content Creators** — Optimize content for AI citations
- **Local Businesses** — Get found by AI assistants
- **SaaS Companies** — Improve entity recognition across AI platforms
- **E-commerce** — Optimize product pages for AI shopping recommendations

---

## Uninstall

```bash
./uninstall.sh
```

Or manually:
```bash
rm -rf ~/.claude/skills/geo ~/.claude/skills/geo-* ~/.claude/agents/geo-*.md
```

---

## Fork Changes

This fork includes the following improvements over the [original repo](https://github.com/zubair-trabzada/geo-seo-claude):

- **Bug fix:** Sitemap URL parsing in `fetch_page.py` — HTTPS URLs were being corrupted during robots.txt parsing
- **Bug fix:** Dynamic year regex in `citability_scorer.py` — replaced hardcoded 2013-2026 range with auto-adjusting pattern
- **Perf fix:** Eliminated triple BeautifulSoup re-parse in `fetch_page.py` — reordered operations so JSON-LD and SSR checks run before the destructive `decompose()`, reducing from 4 HTML parses to 1
- **Bug fix:** Silent exception swallowing in `crawl_sitemap()` — changed return type from bare list to structured dict with `pages`, `count`, and `errors` keys so failures are surfaced instead of silently dropped
- **Feature:** Agent Failure Handling specification in `geo/SKILL.md` — recovery strategy, re-weighting formula, retry logic, Data Completeness reporting
- **Feature:** Test suite — 167 tests covering citability scoring, content extraction, brand scanning, llms.txt generation, PDF report logic, fix generators, and the fixed bugs
- **Feature:** 6 code-level fix generators that produce deployable artifacts:
  - `security_headers_fix.py` — detects server type (Nginx/Apache/Vercel/Netlify/Cloudflare/Express) and generates copy-paste config snippets for all missing security headers
  - `robots_fix.py` — parses existing robots.txt, preserves all current rules, and merges in AI crawler Allow directives (3 strategies: allow_all, search_only, minimal)
  - `meta_tags_fix.py` — audits title, description, canonical, Open Graph, and Twitter Card tags; generates a complete HTML snippet to paste into `<head>`
  - `image_audit_fix.py` — detects missing alt text, dimensions, lazy loading, and legacy formats; generates corrected `<img>` tags, WebP conversion commands, and `<picture>` elements
  - `sitemap_generator.py` — crawls the site, classifies pages by type, and generates a valid XML sitemap with priority and changefreq values
  - `indexnow_generator.py` — generates the IndexNow key file, cURL commands, a Python submission script, and an n8n webhook config for instant Bing indexing

---

## License

MIT License

---

## Contributing

Contributions welcome! Please read the contribution guidelines in `docs/CONTRIBUTING.md` before submitting a PR.

---

Built for the AI search era.
