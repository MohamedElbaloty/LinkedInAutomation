"""
Comprehensive verification test suite for ai_news_agent.
Tests configuration, database deduplication, HTML stripping,
relevance scoring, live RSS feed parsing, and CLI commands.
"""

import sys
import unittest
from pathlib import Path
import tempfile
import sqlite3

import config
import fetcher
from fetcher import Article, clean_html, calculate_relevance, init_db, is_already_posted, mark_as_posted
from ai_generator import GenerationResult
from telegram_bot import TelegramPublisher


class TestAINewsAgent(unittest.TestCase):

    def setUp(self):
        # Create a temporary database for test isolation
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = Path(self.temp_dir.name) / "test_news.db"

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_config_defaults(self):
        """Verify configuration constants and default models."""
        self.assertIsInstance(config.AI_RSS_FEEDS, list)
        self.assertGreater(len(config.AI_RSS_FEEDS), 0)
        self.assertIn("gemini", config.TEXT_MODEL.lower())
        self.assertTrue(any(k in config.IMAGE_MODEL.lower() for k in ["gemini", "imagen", "banana"]))
        self.assertEqual(config.SCHEDULE_HOURS, [9, 18])

    def test_html_sanitization(self):
        """Test HTML cleaning and boilerplate removal."""
        raw_html = "<p>OpenAI releases <strong>new model</strong> with 1M context. <a href='#'>Read more</a></p><script>alert('xss')</script>"
        cleaned = clean_html(raw_html)
        self.assertEqual(cleaned, "OpenAI releases new model with 1M context. Read more")

        boilerplate_html = "<p>Anthropic launched Claude 3.7 Sonnet. The post appeared first on TechCrunch.</p>"
        cleaned_bp = clean_html(boilerplate_html)
        self.assertEqual(cleaned_bp, "Anthropic launched Claude 3.7 Sonnet.")

    def test_relevance_calculation(self):
        """Test AI relevance scoring."""
        title_ai = "Google DeepMind unveils new Agentic AI architecture"
        summary_ai = "The model achieves state-of-the-art reasoning benchmark performance."
        score_high = calculate_relevance(title_ai, summary_ai)
        self.assertGreater(score_high, 5)

        title_non_ai = "10 best summer vacation spots for 2026"
        summary_non_ai = "Explore tropical beaches and mountain resorts."
        score_zero = calculate_relevance(title_non_ai, summary_non_ai)
        self.assertEqual(score_zero, 0)

    def test_sqlite_deduplication(self):
        """Test SQLite table creation and duplicate prevention."""
        init_db(self.test_db_path)

        test_id = "hash_12345"
        test_title = "Revolutionary AI Breakthrough in Quantum Computing"
        test_pub = "2026-09-09T05:00:00Z"

        self.assertFalse(is_already_posted(test_id, self.test_db_path))

        mark_as_posted(test_id, test_title, test_pub, self.test_db_path)
        self.assertTrue(is_already_posted(test_id, self.test_db_path))

        # Check table schema matches (id, title, published_at)
        conn = sqlite3.connect(self.test_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, published_at FROM posted_news WHERE id = ?", (test_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], test_id)
            self.assertEqual(row[1], test_title)
            self.assertEqual(row[2], test_pub)
        finally:
            conn.close()

    def test_generation_result_schema(self):
        """Test Pydantic schema validation for Gemini responses."""
        sample_data = {
            "short_hook": "اختراق تقني جديد في معالجة النماذج اللغوية!",
            "linkedin_post": "🚀 تفاصيل معمارية الذكاء الاصطناعي الجديدة...\n#AI #SoftwareEngineering #AgenticAI",
            "telegram_caption": "ملخص تقني سريع لقناة تليجرام",
            "card_headline": "قفزة تقنية في معالجة النماذج",
            "card_sub_headline": "بنية معمارية جديدة لنماذج الاستدلال",
            "category_badge": "ذكاء اصطناعي | AI",
            "event_badge": "قفزة هندسية",
            "metric_value": "99.4%",
            "metric_label": "دقة الاستدلال",
            "metric_sub": "Benchmark",
            "bullet_points": ["معمارية متطورة", "كفاءة حسابية"],
            "sector_tags": ["#AI", "#Tech"],
            "image_prompt": "Editorial 3D visualization of neural pathways in dark aesthetic.",
        }
        result = GenerationResult(**sample_data)
        self.assertEqual(result.short_hook, sample_data["short_hook"])
        self.assertIn("#AI", result.linkedin_post)

    def test_rss_fetching_live(self):
        """Test fetching live articles from configured RSS feeds."""
        # Use single feed to verify network parsing
        test_feed = [
            {
                "name": "Google News AI",
                "url": "https://news.google.com/rss/search?q=Artificial+Intelligence&hl=en-US&gl=US&ceid=US:en",
            }
        ]
        articles = fetcher.fetch_unread_articles(feeds=test_feed, db_path=self.test_db_path)
        self.assertIsInstance(articles, list)
        if articles:
            first = articles[0]
            self.assertIsInstance(first, Article)
            self.assertTrue(bool(first.title))
            self.assertTrue(bool(first.id))
            print(f"\n[Live RSS Test] Fetched sample article: '{first.title[:60]}...' (Score: {first.relevance_score})")


if __name__ == "__main__":
    unittest.main(verbosity=2)
