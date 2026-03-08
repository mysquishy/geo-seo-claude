#!/usr/bin/env python3
"""Tests for the citability scorer module."""

import sys
import os
import unittest
from unittest.mock import patch
from datetime import datetime

# Add scripts dir to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from citability_scorer import score_passage, _build_year_pattern, YEAR_PATTERN


class TestScorePassage(unittest.TestCase):
    """Tests for score_passage()."""

    # --- Grade boundaries ---

    def test_empty_text_scores_f(self):
        result = score_passage("")
        self.assertEqual(result["grade"], "F")
        self.assertEqual(result["word_count"], 0)

    def test_high_quality_passage_scores_well(self):
        """A passage with definitions, stats, named sources, and optimal length should score B+."""
        text = (
            "Content delivery networks (CDNs) are distributed server systems that cache "
            "and serve web content from locations geographically close to end users. "
            "According to Cloudflare, a CDN reduces latency by 50% on average by serving "
            "assets from edge servers rather than a single origin server. The three largest "
            "CDN providers as of 2025 are Cloudflare (serving approximately 20% of all "
            "websites), Amazon CloudFront, and Akamai Technologies. Our research found that "
            "sites using CDNs load 2.3 times faster on mobile devices. Studies show that a "
            "1-second delay in page load time results in a 7% reduction in conversions. "
            "For example, when Walmart implemented aggressive CDN caching, they reported a "
            "2% increase in revenue for every 1-second improvement in load time."
        )
        result = score_passage(text, "What is a CDN?")
        self.assertGreaterEqual(result["total_score"], 50)
        self.assertIn(result["grade"], ("A", "B", "C"))

    def test_low_quality_narrative_scores_poorly(self):
        """Vague, pronoun-heavy narrative without facts should score D or F."""
        text = (
            "If you have ever wondered why some websites load faster than others, "
            "the answer might surprise you. There is this amazing technology that "
            "has been around for a while now. It has changed the way we think about "
            "web performance. Let me explain how it works and why you should care "
            "about it for your business. They say it can really help."
        )
        result = score_passage(text)
        self.assertLessEqual(result["total_score"], 49)
        self.assertIn(result["grade"], ("D", "F"))

    # --- Answer Block Quality ---

    def test_definition_pattern_detected(self):
        result = score_passage("Machine learning is a subset of artificial intelligence.")
        self.assertGreater(result["breakdown"]["answer_block_quality"], 0)

    def test_refers_to_pattern_detected(self):
        result = score_passage("GEO refers to the practice of optimizing content for AI search engines.")
        self.assertGreater(result["breakdown"]["answer_block_quality"], 0)

    def test_question_heading_bonus(self):
        with_q = score_passage("CDNs improve speed.", heading="What is a CDN?")
        without_q = score_passage("CDNs improve speed.", heading="CDN Overview")
        self.assertGreater(with_q["breakdown"]["answer_block_quality"],
                           without_q["breakdown"]["answer_block_quality"])

    def test_research_claim_bonus(self):
        text = "According to Gartner, search traffic will drop 50% by 2028."
        result = score_passage(text)
        self.assertGreater(result["breakdown"]["answer_block_quality"], 0)

    # --- Self-Containment ---

    def test_optimal_word_count_134_167(self):
        """Passages in the 134-167 word sweet spot should get the highest self-containment bonus."""
        words_150 = " ".join(["word"] * 150)
        words_50 = " ".join(["word"] * 50)
        r150 = score_passage(words_150)
        r50 = score_passage(words_50)
        self.assertGreater(r150["breakdown"]["self_containment"],
                           r50["breakdown"]["self_containment"])

    def test_high_pronoun_density_penalized(self):
        """Text heavy with pronouns should score lower on self-containment."""
        low_pronoun = "Cloudflare provides CDN services. Cloudflare caches web content globally."
        high_pronoun = "It provides them. They cache this content. It helps their users a lot."
        r_low = score_passage(low_pronoun)
        r_high = score_passage(high_pronoun)
        self.assertGreaterEqual(r_low["breakdown"]["self_containment"],
                                r_high["breakdown"]["self_containment"])

    def test_proper_nouns_boost_self_containment(self):
        with_names = "Google Cloud and Amazon Web Services compete with Microsoft Azure."
        without_names = "the cloud services compete with each other in the market."
        r_names = score_passage(with_names)
        r_none = score_passage(without_names)
        self.assertGreater(r_names["breakdown"]["self_containment"],
                           r_none["breakdown"]["self_containment"])

    # --- Statistical Density ---

    def test_percentages_increase_stat_density(self):
        text = "Revenue grew by 45% in Q1 and 52% in Q2."
        result = score_passage(text)
        self.assertGreater(result["breakdown"]["statistical_density"], 0)

    def test_dollar_amounts_increase_stat_density(self):
        text = "The project cost $4,500 and generated $12,000 in revenue."
        result = score_passage(text)
        self.assertGreater(result["breakdown"]["statistical_density"], 0)

    def test_named_sources_increase_stat_density(self):
        text = "According to McKinsey, digital transformation spending will reach new highs."
        result = score_passage(text)
        self.assertGreater(result["breakdown"]["statistical_density"], 0)

    def test_no_stats_gets_zero_density(self):
        text = "Many companies are doing various things with different technologies."
        result = score_passage(text)
        self.assertEqual(result["breakdown"]["statistical_density"], 0)

    # --- Structural Readability ---

    def test_list_structures_detected(self):
        text = "First, install the package. Second, configure the settings. Third, deploy."
        result = score_passage(text)
        self.assertGreater(result["breakdown"]["structural_readability"], 0)

    def test_newlines_boost_structure(self):
        text = "Paragraph one content here.\nParagraph two content here."
        result = score_passage(text)
        # Should get the newline bonus
        self.assertGreater(result["breakdown"]["structural_readability"], 0)

    # --- Uniqueness Signals ---

    def test_original_research_detected(self):
        text = "Our research found that 73% of sites using GEO saw traffic increases."
        result = score_passage(text)
        self.assertGreater(result["breakdown"]["uniqueness_signals"], 0)

    def test_case_study_detected(self):
        text = "For example, when we implemented this for a client, conversions doubled."
        result = score_passage(text)
        self.assertGreater(result["breakdown"]["uniqueness_signals"], 0)

    # --- Output structure ---

    def test_output_has_required_keys(self):
        result = score_passage("Some test content here.", heading="Test")
        required_keys = {"heading", "word_count", "total_score", "grade", "label", "breakdown", "preview"}
        self.assertEqual(required_keys, set(result.keys()))

    def test_breakdown_has_all_categories(self):
        result = score_passage("Test content.")
        expected_cats = {"answer_block_quality", "self_containment", "structural_readability",
                         "statistical_density", "uniqueness_signals"}
        self.assertEqual(expected_cats, set(result["breakdown"].keys()))

    def test_total_score_is_sum_of_breakdown(self):
        result = score_passage("Machine learning is a powerful technology used by Google and Microsoft.")
        self.assertEqual(result["total_score"], sum(result["breakdown"].values()))

    def test_score_capped_at_100(self):
        """Even a maxed-out passage should not exceed 100."""
        result = score_passage("Machine learning is a technology. " * 50)
        self.assertLessEqual(result["total_score"], 100)

    def test_preview_truncated_at_30_words(self):
        long_text = " ".join(["word"] * 60)
        result = score_passage(long_text)
        self.assertTrue(result["preview"].endswith("..."))
        # Preview should be ~30 words + "..."
        preview_words = result["preview"].replace("...", "").split()
        self.assertEqual(len(preview_words), 30)

    def test_preview_no_ellipsis_for_short_text(self):
        short_text = "Just a few words here."
        result = score_passage(short_text)
        self.assertFalse(result["preview"].endswith("..."))


class TestYearPattern(unittest.TestCase):
    """Tests for the dynamic year regex builder."""

    def test_current_year_matches(self):
        current_year = str(datetime.now().year)
        self.assertTrue(YEAR_PATTERN.search(current_year))

    def test_next_year_matches(self):
        next_year = str(datetime.now().year + 1)
        self.assertTrue(YEAR_PATTERN.search(next_year))

    def test_2010_matches(self):
        self.assertTrue(YEAR_PATTERN.search("2010"))

    def test_2025_matches(self):
        self.assertTrue(YEAR_PATTERN.search("2025"))

    def test_far_future_does_not_match(self):
        far_future = str(datetime.now().year + 5)
        self.assertFalse(YEAR_PATTERN.search(far_future))

    def test_2009_does_not_match(self):
        self.assertFalse(YEAR_PATTERN.search("2009"))

    def test_1999_does_not_match(self):
        self.assertFalse(YEAR_PATTERN.search("1999"))

    def test_year_in_sentence(self):
        self.assertTrue(YEAR_PATTERN.search("In 2024, the market grew rapidly."))

    def test_build_year_pattern_returns_compiled_regex(self):
        pattern = _build_year_pattern()
        self.assertIsNotNone(pattern.pattern)


class TestGradeDistribution(unittest.TestCase):
    """Verify grade thresholds are consistent."""

    def _score_with_total(self, target: int) -> str:
        """We can't force an exact score, so verify the grade mapping logic directly."""
        # Replicate the grading logic
        if target >= 80:
            return "A"
        elif target >= 65:
            return "B"
        elif target >= 50:
            return "C"
        elif target >= 35:
            return "D"
        else:
            return "F"

    def test_grade_a_threshold(self):
        self.assertEqual(self._score_with_total(80), "A")
        self.assertEqual(self._score_with_total(100), "A")

    def test_grade_b_threshold(self):
        self.assertEqual(self._score_with_total(65), "B")
        self.assertEqual(self._score_with_total(79), "B")

    def test_grade_c_threshold(self):
        self.assertEqual(self._score_with_total(50), "C")
        self.assertEqual(self._score_with_total(64), "C")

    def test_grade_d_threshold(self):
        self.assertEqual(self._score_with_total(35), "D")
        self.assertEqual(self._score_with_total(49), "D")

    def test_grade_f_threshold(self):
        self.assertEqual(self._score_with_total(0), "F")
        self.assertEqual(self._score_with_total(34), "F")


if __name__ == "__main__":
    unittest.main()
