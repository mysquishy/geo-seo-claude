#!/usr/bin/env python3
"""
Robots.txt Fix Generator — Analyzes current robots.txt and generates a merged
version that preserves existing directives while ensuring AI crawlers are allowed.
"""

import sys
import json
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install requests")
    sys.exit(1)

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

AI_CRAWLERS_ALLOW = [
    ("GPTBot", "OpenAI — ChatGPT Search"), ("OAI-SearchBot", "OpenAI — Search-only"),
    ("ChatGPT-User", "OpenAI — User page visits"), ("ClaudeBot", "Anthropic — Claude"),
    ("PerplexityBot", "Perplexity AI"), ("Google-Extended", "Google — AI Overviews"),
    ("GoogleOther", "Google — Supplemental"), ("Applebot-Extended", "Apple Intelligence"),
    ("Amazonbot", "Amazon AI"), ("FacebookBot", "Meta AI"),
]
AI_CRAWLERS_OPTIONAL = [
    ("CCBot", "Common Crawl"), ("anthropic-ai", "Anthropic legacy"),
    ("Bytespider", "ByteDance AI"), ("cohere-ai", "Cohere AI"),
]


def parse_robots_txt(content: str) -> dict:
    blocks, current_agents, current_rules, sitemaps, comments = [], [], [], [], []
    for raw_line in content.split("\n"):
        line = raw_line.strip()
        if not line: continue
        if line.startswith("#"): comments.append(line); continue
        lower = line.lower()
        if lower.startswith("user-agent:"):
            if current_rules and current_agents:
                blocks.append({"agents": list(current_agents), "rules": list(current_rules)})
                current_rules = []
            agent = line.split(":", 1)[1].strip()
            if not current_rules: current_agents.append(agent)
            else: current_agents = [agent]
        elif lower.startswith("sitemap:"):
            _, _, url_part = line.partition(":")
            sitemaps.append(url_part.strip())
        elif lower.startswith(("allow:", "disallow:", "crawl-delay:")):
            directive = line.split(":", 1)[0].strip()
            path = line.split(":", 1)[1].strip()
            current_rules.append({"directive": directive, "path": path, "raw": line})
            if not current_agents: current_agents = ["*"]
    if current_agents and current_rules:
        blocks.append({"agents": list(current_agents), "rules": list(current_rules)})
    return {"blocks": blocks, "sitemaps": sitemaps, "comments": comments}


def analyze_ai_access(parsed: dict) -> dict:
    status = {}
    all_crawlers = AI_CRAWLERS_ALLOW + AI_CRAWLERS_OPTIONAL
    agent_rules = {}
    for block in parsed["blocks"]:
        for agent in block["agents"]:
            agent_rules.setdefault(agent, []).extend(block["rules"])
    for crawler_name, _ in all_crawlers:
        if crawler_name in agent_rules:
            rules = agent_rules[crawler_name]
            if any(r["directive"].lower() == "disallow" and r["path"] == "/" for r in rules):
                status[crawler_name] = "BLOCKED"
            elif any(r["directive"].lower() == "disallow" and r["path"] for r in rules):
                status[crawler_name] = "PARTIALLY_BLOCKED"
            else:
                status[crawler_name] = "ALLOWED"
        elif "*" in agent_rules:
            wildcard = agent_rules["*"]
            if any(r["directive"].lower() == "disallow" and r["path"] == "/" for r in wildcard):
                status[crawler_name] = "BLOCKED_BY_WILDCARD"
            else:
                status[crawler_name] = "ALLOWED_BY_DEFAULT"
        else:
            status[crawler_name] = "NOT_MENTIONED"
    return status


def generate_fixed_robots(url: str, current_content: str, strategy: str = "allow_all_ai") -> dict:
    parsed = parse_robots_txt(current_content)
    current_status = analyze_ai_access(parsed)
    if strategy == "allow_all_ai": target_crawlers = AI_CRAWLERS_ALLOW + AI_CRAWLERS_OPTIONAL
    elif strategy == "allow_search_only": target_crawlers = AI_CRAWLERS_ALLOW
    else: target_crawlers = AI_CRAWLERS_ALLOW[:5]
    crawlers_to_fix = []
    for name, desc in target_crawlers:
        st = current_status.get(name, "NOT_MENTIONED")
        if st in ("BLOCKED", "BLOCKED_BY_WILDCARD"): crawlers_to_fix.append((name, desc, st))
    lines = []
    if parsed["comments"]:
        for c in parsed["comments"]:
            if c.startswith("#"): lines.append(c)
        lines.append("")
    crawlers_to_unblock = {c[0] for c in crawlers_to_fix}
    for block in parsed["blocks"]:
        ai_in = [a for a in block["agents"] if a in crawlers_to_unblock]
        non_ai = [a for a in block["agents"] if a not in crawlers_to_unblock]
        if ai_in and not non_ai: continue
        elif ai_in and non_ai:
            for a in non_ai: lines.append(f"User-agent: {a}")
            for r in block["rules"]: lines.append(r["raw"])
            lines.append("")
        else:
            for a in block["agents"]: lines.append(f"User-agent: {a}")
            for r in block["rules"]: lines.append(r["raw"])
            lines.append("")
    lines.append("# === AI Crawler Access (GEO Optimization) ===")
    lines.append("")
    for name, desc in target_crawlers:
        lines.append(f"# {desc}")
        lines.append(f"User-agent: {name}")
        lines.append("Allow: /")
        lines.append("")
    parsed_url = urlparse(url)
    base = f"{parsed_url.scheme}://{parsed_url.netloc}"
    existing_sitemaps = set(parsed["sitemaps"])
    if existing_sitemaps:
        for sm in sorted(existing_sitemaps): lines.append(f"Sitemap: {sm}")
    else:
        lines.append(f"Sitemap: {base}/sitemap.xml")
    lines.append("")
    return {
        "original_status": current_status,
        "crawlers_fixed": [{"crawler": c, "description": d, "was": s} for c, d, s in crawlers_to_fix],
        "strategy": strategy,
        "new_robots_txt": "\n".join(lines),
        "changes_summary": f"Unblocked {len(crawlers_to_fix)} AI crawlers, preserved all existing rules",
    }


def fetch_and_fix(url: str, strategy: str = "allow_all_ai") -> dict:
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    result = {"robots_url": robots_url, "exists": False, "current_content": "", "fix": None, "errors": []}
    try:
        response = requests.get(robots_url, headers=DEFAULT_HEADERS, timeout=15)
        if response.status_code == 200:
            result["exists"] = True
            result["current_content"] = response.text
            result["fix"] = generate_fixed_robots(url, response.text, strategy)
        elif response.status_code == 404:
            result["fix"] = generate_fixed_robots(url, "", strategy)
        else:
            result["errors"].append(f"Unexpected status: {response.status_code}")
    except Exception as e:
        result["errors"].append(f"Failed to fetch robots.txt: {e}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python robots_fix.py <url> [strategy]"); sys.exit(1)
    print(json.dumps(fetch_and_fix(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "allow_all_ai"), indent=2, default=str))
