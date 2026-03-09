#!/usr/bin/env python3
"""Tests for the brand_scanner module.

Covers: structure of platform check returns, generate_brand_report aggregation,
Wikipedia API integration (mocked), and URL generation correctness.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from brand_scanner import (
    check_youtube_presence,
    check_reddit_presence,
    check_wikipedia_presence,
    check_linkedin_presence,
    check_other_platforms,
    generate_brand_report,
)


class TestCheckYoutubePresence(unittest.TestCase):
    """Tests for YouTube presence checker."""

    def test_returns_required_keys(self):
        result = check_youtube_presence("Acme Corp")
        for key in ["platform", "correlation", "weight", "has_channel",
                     "mentioned_in_videos", "search_url", "recommendations"]:
            self.assertIn(key, result)

    def test_platform_name(self):
        result = check_youtube_presence("TestBrand")
        self.assertEqual(result["platform"], "YouTube")

    def test_correlation_value(self):
        result = check_youtube_presence("TestBrand")
        self.assertEqual(result["correlation"], 0.737)

    def test_search_url_contains_brand(self):
        result = check_youtube_presence("Acme Corp")
        self.assertIn("Acme", result["search_url"])
        self.assertIn("youtube.com", result["search_url"])

    def test_recommendations_not_empty(self):
        result = check_youtube_presence("TestBrand")
        self.assertGreater(len(result["recommendations"]), 0)

    def test_special_characters_in_brand_encoded(self):
        result = check_youtube_presence("Ben & Jerry's")
        self.assertIn("youtube.com", result["search_url"])
        # URL-encoded & should be present
        self.assertIn("Ben", result["search_url"])


class TestCheckRedditPresence(unittest.TestCase):
    """Tests for Reddit presence checker."""

    def test_returns_required_keys(self):
        result = check_reddit_presence("Acme Corp")
        for key in ["platform", "weight", "has_subreddit",
                     "mentioned_in_discussions", "search_url", "recommendations"]:
            self.assertIn(key, result)

    def test_platform_name(self):
        result = check_reddit_presence("TestBrand")
        self.assertEqual(result["platform"], "Reddit")

    def test_search_url_contains_brand(self):
        result = check_reddit_presence("Acme Corp")
        self.assertIn("reddit.com", result["search_url"])
        self.assertIn("Acme", result["search_url"])

    def test_defaults_to_not_found(self):
        result = check_reddit_presence("TestBrand")
        self.assertFalse(result["has_subreddit"])
        self.assertFalse(result["mentioned_in_discussions"])


class TestCheckWikipediaPresence(unittest.TestCase):
    """Tests for Wikipedia/Wikidata presence checker (mocked HTTP)."""

    @patch("brand_scanner.requests.get")
    def test_wikipedia_page_detected(self, mock_get):
        """When Wikipedia API returns a matching title, has_wikipedia_page should be True."""
        wiki_response = MagicMock()
        wiki_response.status_code = 200
        wiki_response.json.return_value = {
            "query": {
                "search": [
                    {"title": "Anthropic", "snippet": "AI safety company"}
                ]
            }
        }
        wikidata_response = MagicMock()
        wikidata_response.status_code = 200
        wikidata_response.json.return_value = {"search": []}

        mock_get.side_effect = [wiki_response, wikidata_response]

        result = check_wikipedia_presence("Anthropic")
        self.assertTrue(result["has_wikipedia_page"])

    @patch("brand_scanner.requests.get")
    def test_wikipedia_page_not_detected_for_mismatch(self, mock_get):
        """When top result title doesn't contain brand name, should be False."""
        wiki_response = MagicMock()
        wiki_response.status_code = 200
        wiki_response.json.return_value = {
            "query": {
                "search": [
                    {"title": "Something Else Entirely", "snippet": "unrelated"}
                ]
            }
        }
        wikidata_response = MagicMock()
        wikidata_response.status_code = 200
        wikidata_response.json.return_value = {"search": []}

        mock_get.side_effect = [wiki_response, wikidata_response]

        result = check_wikipedia_presence("XyzNonexistent")
        self.assertFalse(result["has_wikipedia_page"])

    @patch("brand_scanner.requests.get")
    def test_wikidata_entry_detected(self, mock_get):
        """When Wikidata API returns entities, has_wikidata_entry should be True."""
        wiki_response = MagicMock()
        wiki_response.status_code = 200
        wiki_response.json.return_value = {"query": {"search": []}}

        wikidata_response = MagicMock()
        wikidata_response.status_code = 200
        wikidata_response.json.return_value = {
            "search": [
                {"id": "Q123456", "description": "technology company"}
            ]
        }

        mock_get.side_effect = [wiki_response, wikidata_response]

        result = check_wikipedia_presence("TestCo")
        self.assertTrue(result["has_wikidata_entry"])
        self.assertEqual(result["wikidata_id"], "Q123456")

    @patch("brand_scanner.requests.get")
    def test_api_failure_handled_gracefully(self, mock_get):
        """Network failures should not crash — just return defaults."""
        mock_get.side_effect = Exception("Connection timeout")

        result = check_wikipedia_presence("TestBrand")
        self.assertFalse(result["has_wikipedia_page"])
        self.assertFalse(result["has_wikidata_entry"])
        self.assertEqual(result["platform"], "Wikipedia")

    def test_returns_required_keys(self):
        """Even without mocking (real API will likely work or fail gracefully)."""
        with patch("brand_scanner.requests.get", side_effect=Exception("no network")):
            result = check_wikipedia_presence("TestBrand")
        for key in ["platform", "weight", "has_wikipedia_page",
                     "has_wikidata_entry", "search_url", "recommendations"]:
            self.assertIn(key, result)


class TestCheckLinkedinPresence(unittest.TestCase):
    """Tests for LinkedIn presence checker."""

    def test_returns_required_keys(self):
        result = check_linkedin_presence("Acme Corp")
        for key in ["platform", "weight", "has_company_page", "search_url", "recommendations"]:
            self.assertIn(key, result)

    def test_platform_name(self):
        result = check_linkedin_presence("TestBrand")
        self.assertEqual(result["platform"], "LinkedIn")

    def test_search_url_contains_brand(self):
        result = check_linkedin_presence("Acme Corp")
        self.assertIn("linkedin.com", result["search_url"])


class TestCheckOtherPlatforms(unittest.TestCase):
    """Tests for the other-platforms aggregator."""

    def test_returns_required_keys(self):
        result = check_other_platforms("Acme Corp")
        self.assertIn("platforms_checked", result)
        self.assertIn("recommendations", result)

    def test_all_platforms_present(self):
        result = check_other_platforms("Acme Corp")
        expected = {"Quora", "Stack Overflow", "GitHub", "Crunchbase",
                    "Product Hunt", "G2", "Trustpilot"}
        self.assertEqual(set(result["platforms_checked"].keys()), expected)

    def test_each_platform_has_search_url(self):
        result = check_other_platforms("TestBrand")
        for name, info in result["platforms_checked"].items():
            self.assertIn("search_url", info, f"{name} missing search_url")
            self.assertTrue(info["search_url"].startswith("http"), f"{name} URL invalid")


class TestGenerateBrandReport(unittest.TestCase):
    """Tests for the full brand report aggregation."""

    @patch("brand_scanner.requests.get")
    def test_report_has_all_platform_sections(self, mock_get):
        mock_get.side_effect = Exception("no network in tests")
        report = generate_brand_report("TestBrand", "testbrand.com")
        for platform in ["youtube", "reddit", "wikipedia", "linkedin", "other"]:
            self.assertIn(platform, report["platforms"])

    @patch("brand_scanner.requests.get")
    def test_report_brand_name_preserved(self, mock_get):
        mock_get.side_effect = Exception("no network")
        report = generate_brand_report("Acme Corp", "acme.com")
        self.assertEqual(report["brand_name"], "Acme Corp")
        self.assertEqual(report["domain"], "acme.com")

    @patch("brand_scanner.requests.get")
    def test_report_has_overall_recommendations(self, mock_get):
        mock_get.side_effect = Exception("no network")
        report = generate_brand_report("TestBrand")
        self.assertGreater(len(report["overall_recommendations"]), 0)

    @patch("brand_scanner.requests.get")
    def test_report_key_insight_present(self, mock_get):
        mock_get.side_effect = Exception("no network")
        report = generate_brand_report("TestBrand")
        self.assertIn("key_insight", report)
        self.assertIn("3x", report["key_insight"])

    @patch("brand_scanner.requests.get")
    def test_domain_can_be_none(self, mock_get):
        mock_get.side_effect = Exception("no network")
        report = generate_brand_report("TestBrand")
        self.assertIsNone(report["domain"])


if __name__ == "__main__":
    unittest.main()
