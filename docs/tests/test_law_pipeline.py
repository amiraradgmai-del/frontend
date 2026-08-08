import csv
import tempfile
import unittest
from pathlib import Path

from docs.law_pipeline import (
    clean_persian_text,
    extract_articles,
    html_to_text,
    save_articles_csv,
)


class LawPipelineTests(unittest.TestCase):
    def test_clean_persian_text_normalizes_characters_and_spaces(self) -> None:
        dirty = "  ماليات\u064e   بر كسب  "
        self.assertEqual(clean_persian_text(dirty, preserve_lines=False), "مالیات بر کسب")

    def test_extract_articles_supports_persian_digits_and_repeat(self) -> None:
        text = """
        عنوان قانون
        ‌ماده ۱- متن ماده اول است.
        تبصره- توضیح ماده اول.
        ماده ۲ مکرر: متن ماده دوم است.
        """
        articles = extract_articles(
            text,
            document_title="قانون نمونه",
            source_url="https://example.test/law",
            fetched_at="2026-07-13T00:00:00+00:00",
        )

        self.assertEqual([article.article_number for article in articles], ["1", "2 مکرر"])
        self.assertIn("تبصره", articles[0].article_text)
        self.assertEqual(articles[1].article_text, "متن ماده دوم است.")

    def test_html_is_converted_and_scripts_are_ignored(self) -> None:
        html = "<script>ماده 99 جعلی</script><p>ماده ۱</p><div>متن معتبر</div>"
        text = html_to_text(html)
        articles = extract_articles(text, document_title="نمونه")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].article_text, "متن معتبر")

    def test_save_csv_uses_expected_columns(self) -> None:
        articles = extract_articles("ماده واحده: متن", document_title="قانون")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "articles.csv"
            count = save_articles_csv(articles, output)
            with output.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(count, 1)
        self.assertEqual(rows[0]["article_number"], "واحده")
        self.assertEqual(rows[0]["article_text"], "متن")


if __name__ == "__main__":
    unittest.main()
