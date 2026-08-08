import csv
import json
import tempfile
import unittest
from pathlib import Path

from docs.rag_dataset import (
    SourceArticle,
    build_chunks,
    build_quality_report,
    infer_lifecycle_status,
    load_source_articles,
    normalize_article_number,
    save_jsonl,
    split_into_chunks,
)


class RagDatasetTests(unittest.TestCase):
    def test_normalize_article_number_converts_persian_digits(self) -> None:
        self.assertEqual(normalize_article_number(" ۱۶۹ مکرر "), "169 مکرر")

    def test_repealed_marker_only_record_is_detected(self) -> None:
        self.assertEqual(infer_lifecycle_status("[حذفی ۱۳۹۴/۴/۳۱]"), "repealed")
        self.assertEqual(
            infer_lifecycle_status("[اصلاحی ۱۳۹۴/۴/۳۱] متن معتبر ماده"), "unknown"
        )

    def test_long_article_is_split_into_bounded_chunks(self) -> None:
        text = " ".join(f"جمله شماره {number}." for number in range(200))
        chunks = split_into_chunks(text, max_chars=300, overlap_chars=30)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 300 for chunk in chunks))

    def test_build_chunks_is_deterministic_and_not_eligible_before_review(self) -> None:
        article = SourceArticle(
            "قانون نمونه", "۱", "این متن ماده آزمایشی و معتبر نشده است.",
            "https://example.test/law", "2026-07-14T00:00:00+00:00",
        )
        first = build_chunks([article])
        second = build_chunks([article])
        self.assertEqual(first, second)
        self.assertFalse(first[0].retrieval_eligible)
        self.assertIn("pending_expert_review", first[0].quality_flags)

    def test_csv_to_jsonl_preserves_identity_and_produces_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            output = Path(directory) / "output.jsonl"
            with source.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=["document_title", "article_number", "article_text", "source_url", "fetched_at"],
                )
                writer.writeheader()
                writer.writerow({
                    "document_title": "قانون نمونه", "article_number": "۱",
                    "article_text": "متن ماده نمونه برای آزمون پردازش داده است.",
                    "source_url": "https://example.test/law", "fetched_at": "2026-07-14",
                })
            articles = load_source_articles(source)
            chunks = build_chunks(articles)
            self.assertEqual(save_jsonl(chunks, output), 1)
            record = json.loads(output.read_text(encoding="utf-8"))
            report = build_quality_report(articles, chunks)
            self.assertEqual(record["article_number"], "1")
            self.assertEqual(report["unique_chunk_count"], 1)
            self.assertTrue(report["requires_expert_review"])


if __name__ == "__main__":
    unittest.main()

