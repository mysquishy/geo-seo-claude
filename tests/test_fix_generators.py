#!/usr/bin/env python3
"""Tests for the fix generator scripts: security_headers_fix, robots_fix,
meta_tags_fix, image_audit_fix, sitemap_generator, indexnow_generator.

All HTTP calls are mocked — no network required.
"""

import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from security_headers_fix import (
    detect_server, audit_headers, generate_fixes, _check_weakness,
    RECOMMENDED_HEADERS,
)
from robots_fix import (
    parse_robots_txt, analyze_ai_access, generate_fixed_robots, AI_CRAWLERS_ALLOW,
)
from meta_tags_fix import audit_meta_tags, generate_meta_fixes
from image_audit_fix import audit_images, generate_fixes as generate_image_fixes
from sitemap_generator import (
    _classify_page, generate_sitemap_xml, PAGE_PATTERNS,
)
from indexnow_generator import generate_key, generate_implementation


# ============================================================
# Security Headers Fix
# ============================================================

class TestDetectServer(unittest.TestCase):
    def test_nginx_detected(self):
        r = detect_server({"Server": "nginx/1.21.0"})
        self.assertEqual(r["server"], "nginx")

    def test_apache_detected(self):
        r = detect_server({"Server": "Apache/2.4.52"})
        self.assertEqual(r["server"], "apache")

    def test_cloudflare_detected(self):
        r = detect_server({"Server": "cloudflare", "CF-Ray": "abc123"})
        self.assertEqual(r["cdn"], "cloudflare")

    def test_vercel_detected(self):
        r = detect_server({"X-Vercel-Id": "iad1::abc"})
        self.assertEqual(r["platform"], "vercel")

    def test_netlify_detected(self):
        r = detect_server({"X-NF-Request-ID": "abc123"})
        self.assertEqual(r["platform"], "netlify")

    def test_express_detected(self):
        r = detect_server({"X-Powered-By": "Express"})
        self.assertEqual(r["framework"], "express")

    def test_unknown_server(self):
        r = detect_server({})
        self.assertEqual(r["server"], "unknown")


class TestCheckWeakness(unittest.TestCase):
    def test_hsts_too_short(self):
        result = _check_weakness("Strict-Transport-Security", "max-age=3600")
        self.assertIn("too short", result)

    def test_hsts_disabled(self):
        result = _check_weakness("Strict-Transport-Security", "max-age=0")
        self.assertIn("disables", result)

    def test_hsts_good(self):
        result = _check_weakness("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.assertEqual(result, "")

    def test_xframe_allowall(self):
        result = _check_weakness("X-Frame-Options", "ALLOWALL")
        self.assertIn("insecure", result)

    def test_referrer_unsafe(self):
        result = _check_weakness("Referrer-Policy", "unsafe-url")
        self.assertIn("leaks", result)


class TestGenerateFixes(unittest.TestCase):
    def test_nginx_fix_generated(self):
        audit = {
            "missing": {"X-Content-Type-Options": {"recommended": "nosniff", "impact": "test"}},
            "weak": {},
            "server_info": {"server": "nginx", "platform": None, "framework": None, "cdn": None},
        }
        fixes = generate_fixes(audit)
        self.assertIn("nginx", fixes["fixes"])
        self.assertIn("nosniff", fixes["fixes"]["nginx"]["config"])

    def test_vercel_fix_generated(self):
        audit = {
            "missing": {"X-Frame-Options": {"recommended": "SAMEORIGIN", "impact": "test"}},
            "weak": {},
            "server_info": {"server": "unknown", "platform": "vercel", "framework": None, "cdn": None},
        }
        fixes = generate_fixes(audit)
        self.assertIn("vercel_json", fixes["fixes"])
        self.assertIn("SAMEORIGIN", fixes["fixes"]["vercel_json"]["config"])

    def test_no_fixes_needed(self):
        audit = {"missing": {}, "weak": {}, "server_info": {}}
        fixes = generate_fixes(audit)
        self.assertIn("message", fixes)
        self.assertIn("properly configured", fixes["message"])

    def test_all_platforms_generated_for_unknown(self):
        audit = {
            "missing": {"X-Content-Type-Options": {"recommended": "nosniff", "impact": "test"}},
            "weak": {},
            "server_info": {"server": "unknown", "platform": None, "framework": None, "cdn": None},
        }
        fixes = generate_fixes(audit)
        for key in ["nginx", "apache", "express_nodejs", "vercel_json", "netlify_toml"]:
            self.assertIn(key, fixes["fixes"], f"Missing {key} for unknown server")


# ============================================================
# Robots.txt Fix
# ============================================================

class TestParseRobotsTxt(unittest.TestCase):
    def test_basic_parse(self):
        content = "User-agent: *\nDisallow: /admin\n\nSitemap: https://example.com/sitemap.xml"
        parsed = parse_robots_txt(content)
        self.assertEqual(len(parsed["blocks"]), 1)
        self.assertEqual(parsed["blocks"][0]["agents"], ["*"])
        self.assertEqual(parsed["sitemaps"], ["https://example.com/sitemap.xml"])

    def test_ai_crawler_block_detected(self):
        content = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /"
        parsed = parse_robots_txt(content)
        self.assertEqual(len(parsed["blocks"]), 2)

    def test_empty_robots(self):
        parsed = parse_robots_txt("")
        self.assertEqual(parsed["blocks"], [])
        self.assertEqual(parsed["sitemaps"], [])

    def test_comments_preserved(self):
        content = "# This is a comment\nUser-agent: *\nDisallow: /"
        parsed = parse_robots_txt(content)
        self.assertIn("# This is a comment", parsed["comments"])


class TestAnalyzeAiAccess(unittest.TestCase):
    def test_blocked_crawler_detected(self):
        parsed = parse_robots_txt("User-agent: GPTBot\nDisallow: /")
        status = analyze_ai_access(parsed)
        self.assertEqual(status["GPTBot"], "BLOCKED")

    def test_wildcard_block_detected(self):
        parsed = parse_robots_txt("User-agent: *\nDisallow: /")
        status = analyze_ai_access(parsed)
        self.assertEqual(status["GPTBot"], "BLOCKED_BY_WILDCARD")

    def test_allowed_by_default(self):
        parsed = parse_robots_txt("User-agent: *\nAllow: /")
        status = analyze_ai_access(parsed)
        self.assertEqual(status["GPTBot"], "ALLOWED_BY_DEFAULT")


class TestGenerateFixedRobots(unittest.TestCase):
    def test_blocked_crawler_unblocked(self):
        content = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /"
        result = generate_fixed_robots("https://example.com", content)
        self.assertIn("new_robots_txt", result)
        self.assertIn("GPTBot", result["new_robots_txt"])
        self.assertIn("Allow: /", result["new_robots_txt"])
        new_lines = result["new_robots_txt"].split("\n")
        gptbot_idx = None
        for i, line in enumerate(new_lines):
            if "User-agent: GPTBot" in line:
                gptbot_idx = i
                break
        if gptbot_idx is not None:
            for line in new_lines[gptbot_idx + 1:]:
                if line.strip() and not line.startswith("#"):
                    self.assertIn("Allow", line)
                    break

    def test_existing_rules_preserved(self):
        content = "User-agent: *\nDisallow: /admin\nDisallow: /private\n\nSitemap: https://example.com/sitemap.xml"
        result = generate_fixed_robots("https://example.com", content)
        self.assertIn("/admin", result["new_robots_txt"])
        self.assertIn("/private", result["new_robots_txt"])
        self.assertIn("sitemap.xml", result["new_robots_txt"])

    def test_empty_generates_new(self):
        result = generate_fixed_robots("https://example.com", "")
        self.assertIn("GPTBot", result["new_robots_txt"])
        self.assertIn("ClaudeBot", result["new_robots_txt"])


# ============================================================
# Meta Tags Fix
# ============================================================

class TestMetaTagsFix(unittest.TestCase):
    def _mock_response(self, html, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.text = html
        resp.headers = {}
        return resp

    @patch("meta_tags_fix.requests.get")
    def test_missing_tags_detected(self, mock_get):
        html = "<html><head><title>Test</title></head><body></body></html>"
        mock_get.return_value = self._mock_response(html)

        audit = audit_meta_tags("https://example.com")
        self.assertIn("description", audit["missing"])
        self.assertIn("canonical", audit["missing"])
        self.assertIn("og:title", audit["missing"])

    @patch("meta_tags_fix.requests.get")
    def test_present_tags_recorded(self, mock_get):
        html = '''<html lang="en"><head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>My Page</title>
            <meta name="description" content="A great page about things.">
            <link rel="canonical" href="https://example.com/page">
        </head><body></body></html>'''
        mock_get.return_value = self._mock_response(html)

        audit = audit_meta_tags("https://example.com/page")
        self.assertIn("title", audit["present"])
        self.assertIn("description", audit["present"])
        self.assertIn("canonical", audit["present"])

    @patch("meta_tags_fix.requests.get")
    def test_fixes_generate_html(self, mock_get):
        html = "<html><head></head><body></body></html>"
        mock_get.return_value = self._mock_response(html)

        audit = audit_meta_tags("https://example.com")
        fixes = generate_meta_fixes(audit)
        self.assertIn("<meta", fixes["html_snippet"])
        self.assertIn("canonical", fixes["html_snippet"])
        self.assertGreater(fixes["missing_count"], 0)


# ============================================================
# Image Audit Fix
# ============================================================

class TestImageAuditFix(unittest.TestCase):
    @patch("image_audit_fix.requests.get")
    def test_missing_alt_detected(self, mock_get):
        html = '<html><body><img src="/photo.jpg"></body></html>'
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        resp.headers = {"Content-Type": "text/html"}
        mock_get.return_value = resp

        audit = audit_images("https://example.com")
        self.assertEqual(audit["total_images"], 1)
        self.assertEqual(len(audit["issues"]["missing_alt"]), 1)

    @patch("image_audit_fix.requests.get")
    def test_missing_dimensions_detected(self, mock_get):
        html = '<html><body><img src="/photo.jpg" alt="test"></body></html>'
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        resp.headers = {"Content-Type": "text/html"}
        mock_get.return_value = resp

        audit = audit_images("https://example.com")
        self.assertEqual(len(audit["issues"]["missing_dimensions"]), 1)

    @patch("image_audit_fix.requests.get")
    def test_legacy_format_flagged(self, mock_get):
        html = '<html><body><img src="/photo.jpg" alt="x" width="100" height="100"></body></html>'
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        resp.headers = {"Content-Type": "text/html"}
        mock_get.return_value = resp

        audit = audit_images("https://example.com")
        self.assertEqual(len(audit["issues"]["legacy_format"]), 1)
        self.assertEqual(audit["issues"]["legacy_format"][0]["recommended_format"], ".webp")

    def test_fix_generation_produces_tags(self):
        audit = {
            "issues": {
                "missing_alt": [{"index": 0, "src": "/hero.jpg", "current_tag": '<img src="/hero.jpg">'}],
                "missing_dimensions": [{"index": 0, "src": "/hero.jpg", "current_tag": '<img src="/hero.jpg">'}],
                "missing_lazy_loading": [],
                "legacy_format": [{"index": 0, "src": "/hero.jpg", "current_format": ".jpg", "recommended_format": ".webp", "current_tag": '<img src="/hero.jpg">'}],
                "empty_alt_non_decorative": [],
                "no_src": [],
            }
        }
        fixes = generate_image_fixes(audit)
        self.assertGreater(len(fixes["fixed_tags"]), 0)
        self.assertGreater(len(fixes["conversion_commands"]), 0)
        self.assertIn("cwebp", "\n".join(fixes["conversion_commands"]))


# ============================================================
# Sitemap Generator
# ============================================================

class TestSitemapGenerator(unittest.TestCase):
    def test_homepage_classified(self):
        result = _classify_page("https://example.com/", "https://example.com")
        self.assertEqual(result["type"], "homepage")
        self.assertEqual(result["priority"], "1.0")

    def test_blog_post_classified(self):
        result = _classify_page("https://example.com/blog/my-post", "https://example.com")
        self.assertEqual(result["type"], "blog")

    def test_pricing_classified(self):
        result = _classify_page("https://example.com/pricing", "https://example.com")
        self.assertEqual(result["type"], "product")

    def test_about_classified(self):
        result = _classify_page("https://example.com/about", "https://example.com")
        self.assertEqual(result["type"], "about")

    def test_legal_classified(self):
        result = _classify_page("https://example.com/privacy-policy", "https://example.com")
        self.assertEqual(result["type"], "legal")

    def test_sitemap_xml_valid(self):
        pages = [
            {"url": "https://example.com/", "lastmod": "2026-03-01", "changefreq": "daily", "priority": "1.0", "page_type": "homepage"},
            {"url": "https://example.com/about", "lastmod": None, "changefreq": "monthly", "priority": "0.6", "page_type": "about"},
        ]
        xml = generate_sitemap_xml(pages)
        self.assertIn('<?xml version="1.0"', xml)
        self.assertIn("<urlset", xml)
        self.assertIn("<loc>https://example.com/</loc>", xml)
        self.assertIn("<priority>1.0</priority>", xml)
        self.assertIn("</urlset>", xml)

    def test_sitemap_xml_homepage_first(self):
        pages = [
            {"url": "https://example.com/about", "lastmod": None, "changefreq": "monthly", "priority": "0.6", "page_type": "about"},
            {"url": "https://example.com/", "lastmod": None, "changefreq": "daily", "priority": "1.0", "page_type": "homepage"},
        ]
        xml = generate_sitemap_xml(pages)
        home_pos = xml.index("https://example.com/</loc>")
        about_pos = xml.index("https://example.com/about</loc>")
        self.assertLess(home_pos, about_pos)

    def test_empty_pages_produces_valid_xml(self):
        xml = generate_sitemap_xml([])
        self.assertIn("<urlset", xml)
        self.assertIn("</urlset>", xml)


# ============================================================
# IndexNow Generator
# ============================================================

class TestIndexNowGenerator(unittest.TestCase):
    def test_key_generation(self):
        key = generate_key()
        self.assertEqual(len(key), 32)
        self.assertTrue(key.isalnum())

    def test_keys_are_unique(self):
        keys = {generate_key() for _ in range(100)}
        self.assertEqual(len(keys), 100)

    @patch("indexnow_generator.requests.get")
    def test_implementation_generated(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)

        result = generate_implementation("https://example.com")
        self.assertIn("key", result)
        self.assertIn("files", result)
        self.assertIn("scripts", result)
        self.assertIn("key_file", result["files"])
        self.assertIn("curl_single", result["scripts"])
        self.assertIn("python", result["scripts"])
        self.assertIn("n8n_webhook", result["scripts"])

    @patch("indexnow_generator.requests.get")
    def test_key_in_all_outputs(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)

        result = generate_implementation("https://example.com")
        key = result["key"]
        self.assertIn(key, result["files"]["key_file"]["content"])
        self.assertIn(key, result["scripts"]["curl_single"]["command"])

    @patch("indexnow_generator.requests.get")
    def test_existing_key_reused(self, mock_get):
        existing_key = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        resp = MagicMock()
        resp.status_code = 200
        resp.text = existing_key
        mock_get.return_value = resp

        result = generate_implementation("https://example.com")
        self.assertEqual(result["key"], existing_key)
        self.assertTrue(result["existing_check"]["implemented"])


if __name__ == "__main__":
    unittest.main()
