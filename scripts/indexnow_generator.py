#!/usr/bin/env python3
"""IndexNow Implementation Generator — Key file, submission scripts, n8n config."""

import sys, json, secrets
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: pip install requests"); sys.exit(1)

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def generate_key() -> str:
    return secrets.token_hex(16)


def check_existing(url: str, timeout: int = 10) -> dict:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    result = {"implemented": False, "key_file_found": False, "key_value": None, "checks": []}
    for path in ["/.well-known/indexnow", "/indexnow.txt"]:
        try:
            resp = requests.get(base + path, headers=DEFAULT_HEADERS, timeout=timeout)
            if resp.status_code == 200 and resp.text.strip():
                key = resp.text.strip()
                if len(key) >= 8 and key.isalnum():
                    result.update({"implemented": True, "key_file_found": True, "key_value": key})
                    result["checks"].append(f"Found at {base + path}")
                    return result
            result["checks"].append(f"{base + path}: {resp.status_code}")
        except Exception as e:
            result["checks"].append(f"{base + path}: {e}")
    return result


def generate_implementation(url: str) -> dict:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc
    existing = check_existing(url)
    key = existing["key_value"] if existing["implemented"] else generate_key()
    return {
        "existing_check": existing, "key": key,
        "files": {
            "key_file": {"filename": f"{key}.txt", "location": f"{base}/{key}.txt", "content": key},
            "well_known": {"filename": ".well-known/indexnow", "location": f"{base}/.well-known/indexnow", "content": key},
        },
        "scripts": {
            "curl_single": {"description": "Submit single URL", "command": f'curl -X POST "https://api.indexnow.org/indexnow" -H "Content-Type: application/json" -d \'{{"host":"{domain}","key":"{key}","urlList":["{base}/your-page"]}}\''},
            "curl_batch": {"description": "Submit multiple URLs", "command": f'curl -X POST "https://api.indexnow.org/indexnow" -H "Content-Type: application/json" -d \'{{"host":"{domain}","key":"{key}","urlList":["{base}/page1","{base}/page2"]}}\''},
            "python": {"description": "Python submission script", "code": f'import requests\nrequests.post("https://api.indexnow.org/indexnow", json={{"host": "{domain}", "key": "{key}", "urlList": ["URL_HERE"]}})'},
            "n8n_webhook": {"description": "n8n HTTP Request node", "config": {"method": "POST", "url": "https://api.indexnow.org/indexnow", "body": {"host": domain, "key": key, "urlList": ["{{ $json.url }}"]}}},
        },
        "instructions": [
            f"1. Upload {key}.txt to {base}/{key}.txt",
            f"2. Verify: curl {base}/{key}.txt",
            "3. Submit URLs using scripts above on publish/update",
            "4. Bing indexes within minutes (ChatGPT uses Bing's index)",
        ],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python indexnow_generator.py <url>"); sys.exit(1)
    print(json.dumps(generate_implementation(sys.argv[1]), indent=2, default=str))
