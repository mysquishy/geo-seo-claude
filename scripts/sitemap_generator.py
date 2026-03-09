#!/usr/bin/env python3
"""Sitemap Generator — Crawls a site and generates a valid XML sitemap."""

import sys, json, re
from datetime import datetime
from urllib.parse import urlparse, urljoin
from xml.sax.saxutils import escape

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: pip install requests beautifulsoup4"); sys.exit(1)

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", "Accept": "text/html"}
EXCLUDE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".css", ".js", ".pdf", ".zip", ".mp3", ".mp4", ".woff", ".woff2"}
PAGE_PATTERNS = {
    "homepage": {"patterns": [r"^/$", r"^/index\.html?$"], "priority": "1.0", "changefreq": "daily"},
    "product": {"patterns": [r"/pricing", r"/features", r"/product", r"/solutions"], "priority": "0.9", "changefreq": "weekly"},
    "blog": {"patterns": [r"/blog/[^/]+", r"/article", r"/post/"], "priority": "0.7", "changefreq": "monthly"},
    "blog_index": {"patterns": [r"/blog/?$", r"/articles/?$", r"/news/?$"], "priority": "0.8", "changefreq": "daily"},
    "docs": {"patterns": [r"/docs", r"/documentation", r"/guide", r"/help", r"/faq"], "priority": "0.7", "changefreq": "weekly"},
    "about": {"patterns": [r"/about", r"/team", r"/company", r"/contact", r"/careers"], "priority": "0.6", "changefreq": "monthly"},
    "legal": {"patterns": [r"/privacy", r"/terms", r"/legal", r"/cookie"], "priority": "0.3", "changefreq": "yearly"},
    "default": {"patterns": [], "priority": "0.5", "changefreq": "monthly"},
}


def _classify_page(url: str, base_url: str) -> dict:
    path = urlparse(url).path.lower()
    if url.rstrip("/") == base_url.rstrip("/"): return {"type": "homepage", **PAGE_PATTERNS["homepage"]}
    for ptype, cfg in PAGE_PATTERNS.items():
        if ptype == "default": continue
        for p in cfg["patterns"]:
            if re.search(p, path): return {"type": ptype, "priority": cfg["priority"], "changefreq": cfg["changefreq"]}
    return {"type": "default", **PAGE_PATTERNS["default"]}


def crawl_pages(url: str, max_pages: int = 50, timeout: int = 15) -> list:
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    discovered, to_crawl, crawled, pages = set(), [url, base_url + "/"], set(), []
    while to_crawl and len(pages) < max_pages:
        cur = to_crawl.pop(0).split("#")[0].rstrip("/") or base_url
        if cur in crawled: continue
        if any(urlparse(cur).path.lower().endswith(e) for e in EXCLUDE_EXT): continue
        crawled.add(cur)
        try:
            resp = requests.get(cur, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
            if resp.status_code != 200 or "text/html" not in resp.headers.get("Content-Type", ""): continue
            soup = BeautifulSoup(resp.text, "lxml")
            robots = soup.find("meta", attrs={"name": "robots"})
            if robots and "noindex" in robots.get("content", "").lower(): continue
            lastmod = None
            for prop in ["article:modified_time", "article:published_time"]:
                dm = soup.find("meta", property=prop)
                if dm and dm.get("content"): lastmod = dm["content"][:10]; break
            ptype = _classify_page(cur, base_url)
            if cur not in discovered:
                discovered.add(cur)
                pages.append({"url": cur, "lastmod": lastmod, "changefreq": ptype["changefreq"], "priority": ptype["priority"], "page_type": ptype["type"]})
            for link in soup.find_all("a", href=True):
                href = urljoin(cur, link["href"]).split("#")[0].rstrip("/") or base_url
                if urlparse(href).netloc == parsed.netloc and href not in crawled: to_crawl.append(href)
        except Exception: continue
    return pages


def generate_sitemap_xml(pages: list) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in sorted(pages, key=lambda x: (0 if x["page_type"] == "homepage" else 1, -float(x["priority"]), x["url"])):
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(p['url'])}</loc>")
        if p["lastmod"]: lines.append(f"    <lastmod>{escape(p['lastmod'])}</lastmod>")
        lines.append(f"    <changefreq>{p['changefreq']}</changefreq>")
        lines.append(f"    <priority>{p['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def check_existing_sitemap(url: str, timeout: int = 15) -> dict:
    parsed = urlparse(url)
    sm_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    result = {"url": sm_url, "exists": False, "url_count": 0, "has_lastmod": False, "issues": []}
    try:
        resp = requests.get(sm_url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code == 200:
            result["exists"] = True
            soup = BeautifulSoup(resp.text, "lxml")
            urls = soup.find_all("url")
            result["url_count"] = len(urls)
            result["has_lastmod"] = any(u.find("lastmod") for u in urls)
            if not urls: result["issues"].append("Empty sitemap")
            if not result["has_lastmod"]: result["issues"].append("No lastmod dates")
        elif resp.status_code == 404: result["issues"].append("No sitemap.xml (404)")
    except Exception as e: result["issues"].append(f"Error: {e}")
    return result


def generate_sitemap(url: str, max_pages: int = 50) -> dict:
    existing = check_existing_sitemap(url)
    pages = crawl_pages(url, max_pages=max_pages)
    xml = generate_sitemap_xml(pages) if pages else ""
    types = {}
    for p in pages: types[p["page_type"]] = types.get(p["page_type"], 0) + 1
    pu = urlparse(url)
    return {
        "existing_sitemap": existing, "pages_discovered": len(pages), "page_types": types,
        "sitemap_xml": xml,
        "deployment": {"file": "sitemap.xml", "location": f"{pu.scheme}://{pu.netloc}/sitemap.xml",
                       "robots_txt_line": f"Sitemap: {pu.scheme}://{pu.netloc}/sitemap.xml"},
    }


if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python sitemap_generator.py <url> [max_pages]"); sys.exit(1)
    print(json.dumps(generate_sitemap(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 50), indent=2, default=str))
