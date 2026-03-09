#!/usr/bin/env python3
"""Meta Tags Fix Generator — Detects missing meta tags and generates HTML snippets."""

import sys, json, re
from urllib.parse import urlparse, urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: pip install requests beautifulsoup4"); sys.exit(1)

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", "Accept": "text/html"}


def audit_meta_tags(url: str, timeout: int = 20) -> dict:
    result = {"url": url, "status_code": None, "present": {}, "missing": [], "issues": [], "errors": []}
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        result["status_code"] = response.status_code
        if response.status_code != 200: result["errors"].append(f"Non-200: {response.status_code}"); return result
        soup = BeautifulSoup(response.text, "lxml")
        parsed = urlparse(url)
        # Title
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            title = title_tag.get_text(strip=True)
            result["present"]["title"] = title
            if len(title) > 60: result["issues"].append({"tag": "title", "issue": f"Too long ({len(title)} chars)", "current": title})
        else: result["missing"].append("title")
        # Description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"): result["present"]["description"] = desc_tag["content"]
        else: result["missing"].append("description")
        # Canonical
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            result["present"]["canonical"] = canonical["href"]
            if not canonical["href"].startswith("http"): result["issues"].append({"tag": "canonical", "issue": "Relative URL", "current": canonical["href"]})
        else: result["missing"].append("canonical")
        # OG tags
        og_tags = {}
        for og in ["og:title", "og:description", "og:image", "og:url", "og:type", "og:site_name"]:
            meta = soup.find("meta", property=og)
            if meta and meta.get("content"): og_tags[og] = meta["content"]
            else: result["missing"].append(og)
        result["present"]["og"] = og_tags
        # Twitter
        tw = {}
        for t in ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]:
            meta = soup.find("meta", attrs={"name": t})
            if meta and meta.get("content"): tw[t] = meta["content"]
            else: result["missing"].append(t)
        result["present"]["twitter"] = tw
        # Viewport
        vp = soup.find("meta", attrs={"name": "viewport"})
        if vp and vp.get("content"): result["present"]["viewport"] = vp["content"]
        else: result["missing"].append("viewport")
        # Lang
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"): result["present"]["lang"] = html_tag["lang"]
        else: result["missing"].append("html lang attribute")
        # Charset
        cs = soup.find("meta", charset=True)
        if not cs: cs = soup.find("meta", attrs={"http-equiv": "Content-Type"})
        if cs: result["present"]["charset"] = cs.get("charset", cs.get("content", ""))
        else: result["missing"].append("charset")
    except Exception as e:
        result["errors"].append(f"Failed: {e}")
    return result


def generate_meta_fixes(audit: dict) -> dict:
    url = audit["url"]
    parsed = urlparse(url)
    present = audit.get("present", {})
    missing = audit.get("missing", [])
    issues = audit.get("issues", [])
    if not missing and not issues: return {"message": "All meta tags properly configured!", "html_snippet": "", "missing_count": 0, "issues_count": 0, "tags_fixed": [], "instructions": []}
    title = present.get("title", parsed.netloc)
    desc = present.get("description", "")
    lines = ["<!-- GEO-SEO Meta Tag Fixes -->"]
    if "charset" in missing: lines.append('<meta charset="UTF-8">')
    if "viewport" in missing: lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    if "title" in missing: lines.append(f"<title>[PAGE_TITLE] | {parsed.netloc}</title>")
    if "description" in missing: lines.append('<meta name="description" content="[120-155 CHAR DESCRIPTION]">')
    if "canonical" in missing: lines.append(f'<link rel="canonical" href="{url}">')
    og_missing = [m for m in missing if m.startswith("og:")]
    if og_missing:
        lines.append("<!-- Open Graph -->")
        if "og:type" in og_missing: lines.append('<meta property="og:type" content="website">')
        if "og:title" in og_missing: lines.append(f'<meta property="og:title" content="{title}">')
        if "og:description" in og_missing: lines.append(f'<meta property="og:description" content="{desc or "[DESCRIPTION]"}">')
        if "og:url" in og_missing: lines.append(f'<meta property="og:url" content="{url}">')
        if "og:image" in og_missing: lines.append(f'<meta property="og:image" content="https://{parsed.netloc}/og-image.jpg">')
        if "og:site_name" in og_missing: lines.append(f'<meta property="og:site_name" content="{title.split("|")[0].strip()}">')
    tw_missing = [m for m in missing if m.startswith("twitter:")]
    if tw_missing:
        lines.append("<!-- Twitter Card -->")
        if "twitter:card" in tw_missing: lines.append('<meta name="twitter:card" content="summary_large_image">')
        if "twitter:title" in tw_missing: lines.append(f'<meta name="twitter:title" content="{title}">')
        if "twitter:description" in tw_missing: lines.append(f'<meta name="twitter:description" content="{desc or "[DESCRIPTION]"}">')
        if "twitter:image" in tw_missing: lines.append(f'<meta name="twitter:image" content="https://{parsed.netloc}/og-image.jpg">')
    if "html lang attribute" in missing: lines.append('<!-- Add to <html>: lang="en" -->')
    for issue in issues:
        if issue["tag"] == "canonical" and "Relative" in issue["issue"]:
            lines.append(f'<link rel="canonical" href="{urljoin(url, issue["current"])}">')
    return {"missing_count": len(missing), "issues_count": len(issues), "tags_fixed": missing + [i["tag"] for i in issues], "html_snippet": "\n".join(lines), "instructions": ["Paste into <head>", "Replace [PLACEHOLDERS]", "Create 1200x630 OG image"]}


def audit_and_fix(url: str) -> dict:
    audit = audit_meta_tags(url)
    return {"audit": audit, "fixes": generate_meta_fixes(audit)}


if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python meta_tags_fix.py <url>"); sys.exit(1)
    print(json.dumps(audit_and_fix(sys.argv[1]), indent=2, default=str))
