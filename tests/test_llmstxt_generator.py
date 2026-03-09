#!/usr/bin/env python3
"""Tests for the llmstxt_generator module.

Covers: validate_llmstxt format parsing (mocked HTTP), generate_llmstxt page
categorization and output format, and edge cases.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from llmstxt_generator import validate_llmstxt, generate_llmstxt


class TestValidateLlmstxt(unittest.TestCase):
    """Tests for llms.txt validation logic."""

    def _mock_response(self, status_code, text=""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        return resp

    @patch("llmstxt_generator.requests.get")
    def test_valid_llmstxt_detected(self, mock_get):
        """A well-formed llms.txt should pass all checks."""
        content = (
            "# Acme Corp\n"
            "> The best widgets on the planet\n"
            "\n"
            "## Products\n"
            "- [Widget Pro](https://acme.com/pro): Our flagship product\n"
            "- [Widget Lite](https://acme.com/lite): Entry level\n"
            "\n"
            "## Contact\n"
            "- [About Us](https://acme.com/about)\n"
        )
        mock_get.side_effect = [
            self._mock_response(200, content),
            self._mock_response(404),  # llms-full.txt
        ]

        result = validate_llmstxt("https://acme.com")
        self.assertTrue(result["exists"])
        self.assertTrue(result["format_valid"])
        self.assertTrue(result["has_title"])
        self.assertTrue(result["has_description"])
        self.assertTrue(result["has_sections"])
        self.assertTrue(result["has_links"])
        self.assertEqual(result["section_count"], 2)
        self.assertEqual(result["link_count"], 3)

    @patch("llmstxt_generator.requests.get")
    def test_missing_title_flagged(self, mock_get):
        content = (
            "> Just a description\n"
            "## Section\n"
            "- [Link](https://example.com)\n"
        )
        mock_get.side_effect = [
            self._mock_response(200, content),
            self._mock_response(404),
        ]

        result = validate_llmstxt("https://example.com")
        self.assertFalse(result["has_title"])
        self.assertFalse(result["format_valid"])
        self.assertTrue(any("title" in i.lower() for i in result["issues"]))

    @patch("llmstxt_generator.requests.get")
    def test_missing_description_flagged(self, mock_get):
        content = (
            "# My Site\n"
            "## Section\n"
            "- [Link](https://example.com)\n"
        )
        mock_get.side_effect = [
            self._mock_response(200, content),
            self._mock_response(404),
        ]

        result = validate_llmstxt("https://example.com")
        self.assertFalse(result["has_description"])
        self.assertFalse(result["format_valid"])

    @patch("llmstxt_generator.requests.get")
    def test_missing_sections_flagged(self, mock_get):
        content = (
            "# My Site\n"
            "> A description\n"
            "- [Link](https://example.com)\n"
        )
        mock_get.side_effect = [
            self._mock_response(200, content),
            self._mock_response(404),
        ]

        result = validate_llmstxt("https://example.com")
        self.assertFalse(result["has_sections"])
        self.assertEqual(result["section_count"], 0)

    @patch("llmstxt_generator.requests.get")
    def test_missing_links_flagged(self, mock_get):
        content = (
            "# My Site\n"
            "> A description\n"
            "## Section\n"
            "Just plain text here.\n"
        )
        mock_get.side_effect = [
            self._mock_response(200, content),
            self._mock_response(404),
        ]

        result = validate_llmstxt("https://example.com")
        self.assertFalse(result["has_links"])
        self.assertEqual(result["link_count"], 0)

    @patch("llmstxt_generator.requests.get")
    def test_404_means_not_exists(self, mock_get):
        mock_get.side_effect = [
            self._mock_response(404),
            self._mock_response(404),
        ]

        result = validate_llmstxt("https://example.com")
        self.assertFalse(result["exists"])
        self.assertTrue(any("404" in str(i) or "status" in i.lower() for i in result["issues"]))

    @patch("llmstxt_generator.requests.get")
    def test_network_error_handled(self, mock_get):
        mock_get.side_effect = Exception("DNS resolution failed")

        result = validate_llmstxt("https://example.com")
        self.assertFalse(result["exists"])
        self.assertGreater(len(result["issues"]), 0)

    @patch("llmstxt_generator.requests.get")
    def test_llms_full_detected(self, mock_get):
        mock_get.side_effect = [
            self._mock_response(404),       # llms.txt
            self._mock_response(200, "# Full version"),  # llms-full.txt
        ]

        result = validate_llmstxt("https://example.com")
        self.assertTrue(result["full_version"]["exists"])

    @patch("llmstxt_generator.requests.get")
    def test_suggestion_for_few_links(self, mock_get):
        content = (
            "# My Site\n"
            "> A description\n"
            "## Section\n"
            "- [Link](https://example.com/page)\n"
        )
        mock_get.side_effect = [
            self._mock_response(200, content),
            self._mock_response(404),
        ]

        result = validate_llmstxt("https://example.com")
        self.assertTrue(any("more key pages" in s.lower() for s in result["suggestions"]))

    @patch("llmstxt_generator.requests.get")
    def test_url_constructed_correctly(self, mock_get):
        mock_get.side_effect = [
            self._mock_response(404),
            self._mock_response(404),
        ]

        result = validate_llmstxt("https://www.example.com/some/path")
        self.assertEqual(result["url"], "https://www.example.com/llms.txt")
        self.assertEqual(result["full_version"]["url"], "https://www.example.com/llms-full.txt")


class TestGenerateLlmstxt(unittest.TestCase):
    """Tests for llms.txt generation from crawled pages."""

    def _mock_homepage(self, title="Acme Corp | Home", desc="Best widgets", links=None):
        """Build a minimal HTML page mock."""
        link_html = ""
        if links:
            for text, href in links:
                link_html += f'<a href="{href}">{text}</a>\n'

        html = f"""
        <html><head>
            <title>{title}</title>
            <meta name="description" content="{desc}">
        </head><body>
            {link_html}
        </body></html>
        """
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        return resp

    @patch("llmstxt_generator.requests.get")
    def test_generated_starts_with_title(self, mock_get):
        mock_get.return_value = self._mock_homepage()

        result = generate_llmstxt("https://acme.com")
        self.assertTrue(result["generated_llmstxt"].startswith("# Acme Corp"))

    @patch("llmstxt_generator.requests.get")
    def test_generated_has_description(self, mock_get):
        mock_get.return_value = self._mock_homepage()

        result = generate_llmstxt("https://acme.com")
        self.assertIn("> Best widgets", result["generated_llmstxt"])

    @patch("llmstxt_generator.requests.get")
    def test_pricing_categorized_as_products(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[("Pricing", "https://acme.com/pricing")]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertIn("Products & Services", result["generated_llmstxt"])

    @patch("llmstxt_generator.requests.get")
    def test_blog_categorized_as_resources(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[("Our Blog", "https://acme.com/blog")]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertIn("Resources & Blog", result["generated_llmstxt"])

    @patch("llmstxt_generator.requests.get")
    def test_about_categorized_as_company(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[("About Us", "https://acme.com/about")]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertIn("Company", result["generated_llmstxt"])

    @patch("llmstxt_generator.requests.get")
    def test_faq_categorized_as_support(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[("FAQ", "https://acme.com/faq")]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertIn("Support", result["generated_llmstxt"])

    @patch("llmstxt_generator.requests.get")
    def test_external_links_excluded(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[("Twitter", "https://twitter.com/acme")]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertNotIn("twitter.com", result["generated_llmstxt"])

    @patch("llmstxt_generator.requests.get")
    def test_contact_section_always_appended(self, mock_get):
        mock_get.return_value = self._mock_homepage()

        result = generate_llmstxt("https://acme.com")
        self.assertIn("## Contact", result["generated_llmstxt"])

    @patch("llmstxt_generator.requests.get")
    def test_pages_analyzed_count(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[
                ("Page A", "https://acme.com/a"),
                ("Page B", "https://acme.com/b"),
                ("Page C", "https://acme.com/c"),
            ]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertEqual(result["pages_analyzed"], 3)

    @patch("llmstxt_generator.requests.get")
    def test_duplicate_links_deduplicated(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[
                ("Page A", "https://acme.com/a"),
                ("Page A Again", "https://acme.com/a"),
            ]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertEqual(result["pages_analyzed"], 1)

    @patch("llmstxt_generator.requests.get")
    def test_fetch_failure_returns_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")

        result = generate_llmstxt("https://example.com")
        self.assertIn("error", result)

    @patch("llmstxt_generator.requests.get")
    def test_file_extensions_excluded(self, mock_get):
        mock_get.return_value = self._mock_homepage(
            links=[
                ("Logo", "https://acme.com/logo.png"),
                ("Style", "https://acme.com/style.css"),
                ("Real Page", "https://acme.com/about"),
            ]
        )

        result = generate_llmstxt("https://acme.com")
        self.assertNotIn(".png", result["generated_llmstxt"])
        self.assertNotIn(".css", result["generated_llmstxt"])
        self.assertEqual(result["pages_analyzed"], 1)

    @patch("llmstxt_generator.requests.get")
    def test_max_pages_respected(self, mock_get):
        links = [(f"Page {i}", f"https://acme.com/p{i}") for i in range(50)]
        mock_get.return_value = self._mock_homepage(links=links)

        result = generate_llmstxt("https://acme.com", max_pages=5)
        self.assertLessEqual(result["pages_analyzed"], 5)


if __name__ == "__main__":
    unittest.main()
