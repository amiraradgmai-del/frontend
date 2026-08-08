import json
import tempfile
import unittest
from pathlib import Path

from docs.tax_search import (
    TaxLawSearchEngine,
    format_answer,
    load_jsonl,
    summarize_text,
)


class TaxSearchTests(unittest.TestCase):
    def test_search_returns_relevant_article_first(self) -> None:
        documents = [
            {
                "document_title": "قانون مالیات‌های مستقیم",
                "article_number": "1",
                "content": "اشخاص مشمول پرداخت مالیات مشخص می‌شوند.",
                "source_url": "https://example.test/1",
            },
            {
                "document_title": "قانون مالیات‌های مستقیم",
                "article_number": "100",
                "content": "مودیان باید اظهارنامه مالیاتی خود را در موعد مقرر تسلیم کنند.",
                "source_url": "https://example.test/100",
            },
        ]

        engine = TaxLawSearchEngine(documents)
        results = engine.search("اظهارنامه مالیاتی", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].article_number, "100")

    def test_load_jsonl_reads_records(self) -> None:
        record = {"article_number": "238", "content": "اعتراض مالیاتی"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.jsonl"
            path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

            self.assertEqual(load_jsonl(path), [record])

    def test_summarize_text_limits_length(self) -> None:
        summary = summarize_text("مالیات " * 100, max_chars=30)

        self.assertLessEqual(len(summary), 30)
        self.assertTrue(summary.endswith("…"))

    def test_format_answer_includes_answer_and_sources(self) -> None:
        documents = [
            {
                "document_title": "قانون مالیات‌های مستقیم",
                "article_number": "100",
                "content": "مودیان باید اظهارنامه مالیاتی خود را در موعد مقرر تسلیم کنند.",
                "source_url": "https://example.test/100",
            }
        ]
        engine = TaxLawSearchEngine(documents)

        answer = format_answer(
            "اظهارنامه مالیاتی",
            engine.search("اظهارنامه مالیاتی"),
        )

        self.assertIn("پاسخ کوتاه:", answer)
        self.assertIn("منابع:", answer)
        self.assertIn("ماده 100", answer)


if __name__ == "__main__":
    unittest.main()
