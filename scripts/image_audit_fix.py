#!/usr/bin/env python3
"""Image Optimization Fix Generator — Audits images and generates corrected tags + conversion commands."""

import sys, json, re
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: pip install requests beautifulsoup4"); sys.exit(1)

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
FORMAT_UPGRADES = {".jpg": ".webp", ".jpeg": ".webp", ".png": ".webp", ".gif": ".webp", ".bmp": ".webp"}


def _is_decorative(img) -> bool:
    src = img.get("src", "").lower()
    classes = " ".join(img.get("class", [])).lower() if img.get("class") else ""
    return any(p in src or p in classes for p in ["spacer", "pixel", "separator", "icon-", "bg-"])


def _get_extension(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in FORMAT_UPGRADES:
        if path.endswith(ext): return ext
    return ""


def _suggest_alt(src: str) -> str:
    path = urlparse(src).path
    name = path.split("/")[-1].rsplit(".", 1)[0] if "." in path.split("/")[-1] else path.split("/")[-1]
    name = re.sub(r"[-_]+", " ", name).strip()
    return f"[VERIFY] {name.title()}" if len(name) >= 3 else "[DESCRIBE_THIS_IMAGE]"


def audit_images(url: str, timeout: int = 20) -> dict:
    result = {"url": url, "total_images": 0, "issues": {"missing_alt": [], "empty_alt_non_decorative": [], "missing_dimensions": [], "missing_lazy_loading": [], "legacy_format": [], "no_src": []}, "summary": {}, "errors": []}
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code != 200: result["errors"].append(f"Status: {resp.status_code}"); return result
        soup = BeautifulSoup(resp.text, "lxml")
        images = soup.find_all("img")
        result["total_images"] = len(images)
        for idx, img in enumerate(images):
            src = img.get("src", img.get("data-src", ""))
            info = {"index": idx, "src": src, "current_tag": str(img), "is_above_fold": idx < 3}
            if not src: result["issues"]["no_src"].append(info); continue
            if img.get("alt") is None: result["issues"]["missing_alt"].append(info)
            elif img.get("alt") == "" and not _is_decorative(img): result["issues"]["empty_alt_non_decorative"].append(info)
            if not img.get("width") or not img.get("height"): result["issues"]["missing_dimensions"].append(info)
            if img.get("loading") != "lazy" and not info["is_above_fold"]: result["issues"]["missing_lazy_loading"].append(info)
            ext = _get_extension(src)
            if ext in FORMAT_UPGRADES: result["issues"]["legacy_format"].append({**info, "current_format": ext, "recommended_format": FORMAT_UPGRADES[ext]})
        result["summary"] = {k: len(v) for k, v in result["issues"].items()}
        result["summary"]["total_images"] = result["total_images"]
    except Exception as e:
        result["errors"].append(f"Failed: {e}")
    return result


def generate_fixes(audit: dict) -> dict:
    fixes = {"fixed_tags": [], "conversion_commands": [], "picture_elements": [], "instructions": []}
    issues = audit.get("issues", {})
    image_fixes = {}
    for img in issues.get("missing_alt", []):
        image_fixes.setdefault(img["index"], {"src": img["src"], "fixes": [], "original": img["current_tag"]})
        image_fixes[img["index"]]["fixes"].append(("alt", _suggest_alt(img["src"])))
    for img in issues.get("missing_dimensions", []):
        image_fixes.setdefault(img["index"], {"src": img["src"], "fixes": [], "original": img.get("current_tag", "")})
        image_fixes[img["index"]]["fixes"].append(("dimensions", None))
    for img in issues.get("missing_lazy_loading", []):
        image_fixes.setdefault(img["index"], {"src": img["src"], "fixes": [], "original": img.get("current_tag", "")})
        image_fixes[img["index"]]["fixes"].append(("loading", "lazy"))
    for idx, fi in sorted(image_fixes.items()):
        parts = [f'<img src="{fi["src"]}"']
        changes = []
        for ft, fv in fi["fixes"]:
            if ft == "alt": parts.append(f'alt="{fv}"'); changes.append(f'Added alt: "{fv}"')
            elif ft == "dimensions": parts.append('width="[W]" height="[H]"'); changes.append("Added dimension placeholders")
            elif ft == "loading": parts.append('loading="lazy"'); changes.append("Added lazy loading")
        parts.append("/>")
        fixes["fixed_tags"].append({"image_index": idx, "src": fi["src"], "original": fi.get("original", ""), "fixed": " ".join(parts), "changes": changes})
    seen = set()
    for img in issues.get("legacy_format", []):
        if img["src"] in seen: continue
        seen.add(img["src"])
        fn = urlparse(img["src"]).path.split("/")[-1]
        base = fn.rsplit(".", 1)[0] if "." in fn else fn
        fixes["conversion_commands"].append(f"cwebp -q 80 {fn} -o {base}.webp")
        fixes["picture_elements"].append(f'<picture>\n  <source srcset="{base}.webp" type="image/webp">\n  <img src="{img["src"]}" alt="[DESC]" loading="lazy">\n</picture>')
    if seen:
        fixes["conversion_commands"].append("# Batch: for f in *.jpg *.png; do cwebp -q 80 \"$f\" -o \"${f%.*}.webp\"; done")
    fixes["instructions"] = ["Replace <img> tags with fixed versions", "Measure actual dimensions for width/height", "Run cwebp commands for WebP conversion", "Use <picture> for progressive enhancement"]
    return fixes


def audit_and_fix(url: str) -> dict:
    audit = audit_images(url)
    return {"audit": audit, "fixes": generate_fixes(audit)}


if __name__ == "__main__":
    if len(sys.argv) < 2: print("Usage: python image_audit_fix.py <url>"); sys.exit(1)
    print(json.dumps(audit_and_fix(sys.argv[1]), indent=2, default=str))
