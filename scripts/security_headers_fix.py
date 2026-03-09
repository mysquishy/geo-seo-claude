#!/usr/bin/env python3
"""
Security Headers Fix Generator — Detects missing security headers and generates
server-specific configuration snippets to fix them.

Supports: Nginx, Apache (.htaccess), Express/Node.js, Cloudflare, Vercel, Netlify.
"""

import sys
import json
import re
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install requests")
    sys.exit(1)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

RECOMMENDED_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
}

SAFE_CSP = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'self'"


def detect_server(headers: dict) -> dict:
    result = {"server": "unknown", "platform": None, "framework": None, "cdn": None, "confidence": "low"}
    server = headers.get("Server", headers.get("server", "")).lower()
    powered_by = headers.get("X-Powered-By", headers.get("x-powered-by", "")).lower()
    if headers.get("CF-Ray") or headers.get("cf-ray"): result["cdn"] = "cloudflare"
    elif headers.get("X-Cache") or headers.get("x-cache"):
        if "cloudfront" in headers.get("X-Cache", headers.get("x-cache", "")).lower(): result["cdn"] = "aws_cloudfront"
    if headers.get("X-Vercel-Id") or headers.get("x-vercel-id"): result["platform"] = "vercel"; result["confidence"] = "high"
    if headers.get("X-NF-Request-ID") or headers.get("x-nf-request-id"): result["platform"] = "netlify"; result["confidence"] = "high"
    if "nginx" in server: result["server"] = "nginx"; result["confidence"] = "high"
    elif "apache" in server: result["server"] = "apache"; result["confidence"] = "high"
    elif "cloudflare" in server: result["server"] = "cloudflare"; result["cdn"] = "cloudflare"; result["confidence"] = "high"
    elif "microsoft-iis" in server or "iis" in server: result["server"] = "iis"; result["confidence"] = "high"
    if "express" in powered_by: result["framework"] = "express"; result["confidence"] = "high"
    elif "next.js" in powered_by or "next" in powered_by: result["framework"] = "nextjs"; result["confidence"] = "high"
    elif "php" in powered_by: result["framework"] = "php"
    elif "asp.net" in powered_by: result["framework"] = "aspnet"
    return result


def _check_weakness(header: str, value: str) -> str:
    v = value.lower()
    if header == "Strict-Transport-Security":
        if "max-age=0" in v: return "max-age=0 effectively disables HSTS"
        m = re.search(r"max-age=(\d+)", v)
        if m and int(m.group(1)) < 31536000: return f"max-age too short ({m.group(1)}s). Recommend at least 31536000 (1 year)"
    elif header == "X-Frame-Options":
        if v == "allowall" or "allow-from" in v: return "ALLOWALL or ALLOW-FROM are insecure. Use DENY or SAMEORIGIN"
    elif header == "Referrer-Policy":
        if v == "unsafe-url": return "unsafe-url leaks full URL including path and query. Use strict-origin-when-cross-origin"
        if v == "no-referrer-when-downgrade": return "no-referrer-when-downgrade is the old default and leaks info. Use strict-origin-when-cross-origin"
    elif header == "Content-Security-Policy":
        if "unsafe-eval" in v and "unsafe-inline" in v: return "Both unsafe-eval and unsafe-inline present, significantly weakening CSP"
    return ""


def _get_impact(header: str) -> str:
    impacts = {
        "Strict-Transport-Security": "Without HSTS, users can be downgraded to HTTP via MITM attacks.",
        "Content-Security-Policy": "Without CSP, the site is vulnerable to XSS attacks.",
        "X-Content-Type-Options": "Without nosniff, browsers may MIME-sniff and execute malicious content.",
        "X-Frame-Options": "Without frame protection, the site can be clickjacked.",
        "Referrer-Policy": "Without a referrer policy, full URLs leak to third parties.",
        "Permissions-Policy": "Without Permissions-Policy, sensitive browser APIs are unrestricted.",
    }
    return impacts.get(header, "Security best practice")


def audit_headers(url: str, timeout: int = 15) -> dict:
    result = {"url": url, "status_code": None, "server_info": {}, "present": {}, "missing": {}, "weak": {}, "score": 0, "max_score": 0, "errors": []}
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        result["status_code"] = response.status_code
        result["server_info"] = detect_server(dict(response.headers))
        header_scores = {"Strict-Transport-Security": 20, "Content-Security-Policy": 25, "X-Content-Type-Options": 15, "X-Frame-Options": 10, "Referrer-Policy": 15, "Permissions-Policy": 15}
        for header, max_points in header_scores.items():
            result["max_score"] += max_points
            value = response.headers.get(header)
            if value:
                weakness = _check_weakness(header, value)
                if weakness:
                    result["weak"][header] = {"current": value, "issue": weakness, "recommended": RECOMMENDED_HEADERS[header]}
                    result["score"] += max_points // 2
                else:
                    result["present"][header] = value
                    result["score"] += max_points
            else:
                result["missing"][header] = {"recommended": RECOMMENDED_HEADERS[header], "impact": _get_impact(header)}
    except Exception as e:
        result["errors"].append(f"Failed to fetch {url}: {e}")
    return result


def generate_fixes(audit: dict) -> dict:
    headers_to_fix = {}
    for header, info in audit.get("missing", {}).items(): headers_to_fix[header] = info["recommended"]
    for header, info in audit.get("weak", {}).items(): headers_to_fix[header] = info["recommended"]
    if not headers_to_fix: return {"message": "All security headers are properly configured!", "fixes": {}}
    server_info = audit.get("server_info", {})
    server = server_info.get("server", "unknown")
    platform = server_info.get("platform")
    framework = server_info.get("framework")
    if "Content-Security-Policy" in headers_to_fix: headers_to_fix["Content-Security-Policy"] = SAFE_CSP
    fixes = {}
    fixes["nginx"] = {"description": "Nginx", "file": "nginx.conf", "config": "\n".join([f'add_header {h} "{v}" always;' for h, v in headers_to_fix.items()])}
    fixes["apache"] = {"description": "Apache", "file": ".htaccess", "config": "<IfModule mod_headers.c>\n" + "\n".join([f'    Header always set {h} "{v}"' for h, v in headers_to_fix.items()]) + "\n</IfModule>"}
    if framework in ("express", "nextjs") or (server == "unknown" and not platform):
        mid = "\n".join([f"  res.setHeader('{h}', '{v}');" for h, v in headers_to_fix.items()])
        fixes["express_nodejs"] = {"description": "Express.js", "file": "app.js", "config": f"app.use((req, res, next) => {{\n{mid}\n  next();\n}});"}
    if framework == "nextjs" or platform == "vercel" or (server == "unknown" and not platform):
        entries = ",\n".join([f'        {{ key: "{h}", value: "{v}" }}' for h, v in headers_to_fix.items()])
        fixes["nextjs_config"] = {"description": "Next.js", "file": "next.config.js", "config": f"async headers() {{ return [{{ source: '/(.*)', headers: [\n{entries}\n        ] }}]; }}"}
    if platform == "vercel" or (server == "unknown" and not platform):
        import json as j
        fixes["vercel_json"] = {"description": "Vercel", "file": "vercel.json", "config": j.dumps({"headers": [{"source": "/(.*)", "headers": [{"key": h, "value": v} for h, v in headers_to_fix.items()]}]}, indent=2)}
    if platform == "netlify" or (server == "unknown" and not platform):
        fixes["netlify_toml"] = {"description": "Netlify", "file": "netlify.toml", "config": "[[headers]]\n  for = \"/*\"\n  [headers.values]\n" + "\n".join([f'    {h} = "{v}"' for h, v in headers_to_fix.items()])}
    if server_info.get("cdn") == "cloudflare" or server == "cloudflare":
        sets = "\n".join([f"  newHeaders.set('{h}', '{v}');" for h, v in headers_to_fix.items()])
        fixes["cloudflare"] = {"description": "Cloudflare Worker", "file": "worker.js", "config": f"// Cloudflare Worker\n{sets}"}
    return {"detected_server": server_info, "headers_to_fix": list(headers_to_fix.keys()), "fixes": fixes}


def analyze_and_fix(url: str) -> dict:
    audit = audit_headers(url)
    return {"audit": audit, "fixes": generate_fixes(audit)}


if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python security_headers_fix.py <url>"); sys.exit(1)
    print(json.dumps(analyze_and_fix(sys.argv[1]), indent=2, default=str))
