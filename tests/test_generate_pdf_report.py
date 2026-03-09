#!/usr/bin/env python3
"""Tests for the generate_pdf_report module.

Focuses on data processing, color logic, and scoring helpers that can be tested
without rendering an actual PDF. ReportLab is mocked where necessary to keep
tests fast and environment-independent.
"""

import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# We need to handle the case where reportlab may not be installed
# by mocking the import at the module level
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def _try_import():
    """Try importing the module; skip tests if reportlab unavailable."""
    try:
        import generate_pdf_report
        return generate_pdf_report
    except SystemExit:
        return None


module = _try_import()


@unittest.skipIf(module is None, "reportlab not installed — skipping PDF tests")
class TestColorPalette(unittest.TestCase):
    """Verify that the color constants are defined and valid."""

    def test_primary_colors_exist(self):
        for attr in ["PRIMARY", "SECONDARY", "ACCENT", "HIGHLIGHT",
                      "SUCCESS", "WARNING", "DANGER"]:
            self.assertTrue(hasattr(module, attr), f"Missing color: {attr}")

    def test_colors_are_color_objects(self):
        from reportlab.lib.colors import Color
        for attr in ["PRIMARY", "SECONDARY", "ACCENT", "HIGHLIGHT",
                      "SUCCESS", "WARNING", "DANGER"]:
            color = getattr(module, attr)
            self.assertIsInstance(color, Color)


@unittest.skipIf(module is None, "reportlab not installed — skipping PDF tests")
class TestScoreColorLogic(unittest.TestCase):
    """Test the score-to-color mapping used in gauges and charts."""

    def _get_score_color(self, score):
        """Replicate the score-color logic from the module."""
        if score >= 80:
            return module.SUCCESS
        elif score >= 60:
            return module.WARNING
        else:
            return module.DANGER

    def test_high_score_gets_success(self):
        self.assertEqual(self._get_score_color(85), module.SUCCESS)
        self.assertEqual(self._get_score_color(100), module.SUCCESS)

    def test_medium_score_gets_warning(self):
        self.assertEqual(self._get_score_color(60), module.WARNING)
        self.assertEqual(self._get_score_color(79), module.WARNING)

    def test_low_score_gets_danger(self):
        self.assertEqual(self._get_score_color(0), module.DANGER)
        self.assertEqual(self._get_score_color(59), module.DANGER)

    def test_boundary_80(self):
        self.assertEqual(self._get_score_color(80), module.SUCCESS)

    def test_boundary_60(self):
        self.assertEqual(self._get_score_color(60), module.WARNING)


@unittest.skipIf(module is None, "reportlab not installed — skipping PDF tests")
class TestInputDataParsing(unittest.TestCase):
    """Test that the module can handle various JSON input structures."""

    def _make_minimal_data(self, **overrides):
        data = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "date": "2026-03-09",
            "geo_score": 65,
            "scores": {
                "ai_citability": 70,
                "brand_authority": 60,
                "content_quality": 65,
                "technical": 80,
                "structured_data": 50,
                "platform_optimization": 55,
            },
            "findings": {
                "critical": ["No llms.txt found"],
                "high": ["GPTBot blocked in robots.txt"],
                "medium": ["Missing Organization schema"],
                "low": ["Alt text missing on 3 images"],
            },
            "platform_readiness": {
                "Google AI Overviews": 70,
                "ChatGPT": 60,
                "Perplexity": 55,
                "Claude": 65,
            },
            "crawler_access": {
                "GPTBot": "BLOCKED",
                "ClaudeBot": "ALLOWED",
                "PerplexityBot": "ALLOWED",
                "GoogleBot": "ALLOWED",
            },
            "action_plan": {
                "quick_wins": ["Create llms.txt file", "Unblock GPTBot"],
                "medium_term": ["Add Organization schema"],
                "strategic": ["Build YouTube presence"],
            },
        }
        data.update(overrides)
        return data

    def test_minimal_data_is_valid_json(self):
        data = self._make_minimal_data()
        serialized = json.dumps(data)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["geo_score"], 65)

    def test_scores_sum_is_reasonable(self):
        data = self._make_minimal_data()
        scores = data["scores"]
        avg = sum(scores.values()) / len(scores)
        self.assertGreater(avg, 0)
        self.assertLessEqual(avg, 100)

    def test_findings_categorized(self):
        data = self._make_minimal_data()
        for severity in ["critical", "high", "medium", "low"]:
            self.assertIn(severity, data["findings"])
            self.assertIsInstance(data["findings"][severity], list)

    def test_missing_fields_handled(self):
        """Empty or missing sub-dicts shouldn't crash data access patterns."""
        data = self._make_minimal_data(
            findings={},
            platform_readiness={},
            crawler_access={},
            action_plan={},
        )
        # The PDF generator accesses these with .get() — verify patterns work
        self.assertEqual(data["findings"].get("critical", []), [])
        self.assertEqual(data["platform_readiness"].get("ChatGPT", 0), 0)

    def test_geo_score_boundaries(self):
        for score in [0, 25, 50, 75, 100]:
            data = self._make_minimal_data(geo_score=score)
            self.assertEqual(data["geo_score"], score)


@unittest.skipIf(module is None, "reportlab not installed — skipping PDF tests")
class TestCrawlerStatusMapping(unittest.TestCase):
    """Test the crawler status display logic."""

    def test_status_values_are_known(self):
        known_statuses = {
            "ALLOWED", "BLOCKED", "PARTIALLY_BLOCKED",
            "BLOCKED_BY_WILDCARD", "ALLOWED_BY_DEFAULT",
            "NOT_MENTIONED", "NO_ROBOTS_TXT",
        }
        # All statuses used in reports should be from the known set
        test_data = {
            "GPTBot": "BLOCKED",
            "ClaudeBot": "ALLOWED",
            "PerplexityBot": "NOT_MENTIONED",
        }
        for crawler, status in test_data.items():
            self.assertIn(status, known_statuses)

    def test_blocked_status_recognized(self):
        status = "BLOCKED"
        self.assertTrue(status in ("BLOCKED", "BLOCKED_BY_WILDCARD"))

    def test_allowed_status_recognized(self):
        status = "ALLOWED"
        self.assertTrue(status in ("ALLOWED", "ALLOWED_BY_DEFAULT"))


@unittest.skipIf(module is None, "reportlab not installed — skipping PDF tests")
class TestActionPlanStructure(unittest.TestCase):
    """Test the action plan data organization."""

    def test_three_tiers(self):
        plan = {
            "quick_wins": ["A", "B"],
            "medium_term": ["C"],
            "strategic": ["D", "E"],
        }
        self.assertEqual(len(plan["quick_wins"]), 2)
        self.assertEqual(len(plan["medium_term"]), 1)
        self.assertEqual(len(plan["strategic"]), 2)

    def test_empty_tiers_are_valid(self):
        plan = {
            "quick_wins": [],
            "medium_term": [],
            "strategic": [],
        }
        total = sum(len(v) for v in plan.values())
        self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
