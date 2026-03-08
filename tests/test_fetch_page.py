#!/usr/bin/env python3
"""Tests for the fetch_page module — focuses on pure parsing logic (no HTTP)."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fetch_page import _parse_sitemap_url, extract_content_blocks


class TestParseSitemapUrl(unittest.TestCase):
    """Tests for the sitemap URL parser that was previously buggy."""

    def test_https_url_preserved(self):
        line = "Sitemap: https://example.com/sitemap.xml"
        self.assertEqual(_parse_sitemap_url(line), "https://example.com/sitemap.xml")

    def test_http_url_preserved(self):
        line = "Sitemap: http://example.com/sitemap.xml"
        self.assertEqual(_parse_sitemap_url(line), "http://example.com/sitemap.xml")

    def test_leading_whitespace_stripped(self):
        line = "Sitemap:   https://example.com/sitemap.xml  "
        self.assertEqual(_parse_sitemap_url(line), "https://example.com/sitemap.xml")

    def test_complex_sitemap_url(self):
        line = "Sitemap: https://www.example.com/sitemaps/posts-sitemap.xml"
        self.assertEqual(_parse_sitemap_url(line), "https://www.example.com/sitemaps/posts-sitemap.xml")

    def test_sitemap_with_port(self):
        line = "Sitemap: https://example.com:8443/sitemap.xml"
        self.assertEqual(_parse_sitemap_url(line), "https://example.com:8443/sitemap.xml")

    def test_sitemap_with_query_params(self):
        line = "Sitemap: https://example.com/sitemap.xml?page=1"
        self.assertEqual(_parse_sitemap_url(line), "https://example.com/sitemap.xml?page=1")

    def test_case_insensitive_directive(self):
        """The function receives the raw line; the caller lowercases the check."""
        line = "Sitemap: https://example.com/sitemap.xml"
        self.assertEqual(_parse_sitemap_url(line), "https://example.com/sitemap.xml")


class TestExtractContentBlocks(unittest.TestCase):
    """Tests for HTML content block extraction."""

    def test_basic_extraction(self):
        html = """
        <html><body>
            <h2>Section One</h2>
            <p>First paragraph content.</p>
            <p>Second paragraph content.</p>
            <h2>Section Two</h2>
            <p>Third paragraph.</p>
        </body></html>
        """
        blocks = extract_content_blocks(html)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["heading"], "Section One")
        self.assertIn("First paragraph", blocks[0]["content"])

    def test_script_tags_removed(self):
        html = """
        <html><body>
            <script>var x = 1;</script>
            <h2>Real Content</h2>
            <p>Actual text here.</p>
        </body></html>
        """
        blocks = extract_content_blocks(html)
        for block in blocks:
            self.assertNotIn("var x", block["content"])

    def test_nav_footer_removed(self):
        html = """
        <html><body>
            <nav><a href="/">Home</a></nav>
            <h2>Main</h2>
            <p>Body content.</p>
            <footer>Copyright 2025</footer>
        </body></html>
        """
        blocks = extract_content_blocks(html)
        for block in blocks:
            self.assertNotIn("Copyright", block["content"])

    def test_empty_html_returns_empty(self):
        blocks = extract_content_blocks("<html><body></body></html>")
        self.assertEqual(blocks, [])

    def test_no_headings_still_extracts(self):
        html = """
        <html><body>
            <p>Just a standalone paragraph with no heading above it.</p>
        </body></html>
        """
        blocks = extract_content_blocks(html)
        # Should create a block with heading=None
        self.assertEqual(len(blocks), 1)
        self.assertIsNone(blocks[0]["heading"])

    def test_word_count_accurate(self):
        html = """
        <html><body>
            <h2>Test</h2>
            <p>One two three four five.</p>
        </body></html>
        """
        blocks = extract_content_blocks(html)
        self.assertEqual(blocks[0]["word_count"], 5)

    def test_multiple_heading_levels(self):
        html = """
        <html><body>
            <h1>Title</h1>
            <p>Intro text.</p>
            <h2>Subtitle</h2>
            <p>Detail text.</p>
            <h3>Sub-subtitle</h3>
            <p>More detail.</p>
        </body></html>
        """
        blocks = extract_content_blocks(html)
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0]["heading"], "Title")
        self.assertEqual(blocks[1]["heading"], "Subtitle")
        self.assertEqual(blocks[2]["heading"], "Sub-subtitle")

    def test_lists_included_in_content(self):
        html = """
        <html><body>
            <h2>Features</h2>
            <ul>
                <li>Feature one</li>
                <li>Feature two</li>
            </ul>
        </body></html>
        """
        blocks = extract_content_blocks(html)
        self.assertEqual(len(blocks), 1)
        self.assertIn("Feature one", blocks[0]["content"])


class TestRobotsTxtParsing(unittest.TestCase):
    """Tests for the robots.txt parsing logic via integration with _parse_sitemap_url.

    The full fetch_robots_txt function requires HTTP, but we can validate
    the sitemap extraction path that had the original bug.
    """

    def test_old_bug_https_not_corrupted(self):
        """The original code did `line.split(':', 1)[1].strip()` which turned
        'Sitemap: https://example.com/sitemap.xml' into '//example.com/sitemap.xml'
        and then prepended 'http' to get 'http//example.com/sitemap.xml'.
        The fix uses partition() to preserve the full URL."""
        line = "Sitemap: https://example.com/sitemap.xml"
        url = _parse_sitemap_url(line)
        self.assertTrue(url.startswith("https://"))
        self.assertNotEqual(url, "http//example.com/sitemap.xml")

    def test_old_bug_http_url_not_doubled(self):
        """http URLs should not become 'httphttp://...'"""
        line = "Sitemap: http://example.com/sitemap.xml"
        url = _parse_sitemap_url(line)
        self.assertEqual(url.count("http"), 1)


if __name__ == "__main__":
    unittest.main()
