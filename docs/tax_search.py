from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from .law_pipeline import clean_persian_text
except ImportError:
    from law_pipeline import clean_persian_text


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = BASE_DIR / "data" / "processed" / "tax_laws.jsonl"


@dataclass(frozen=True)
class SearchResult:
    score: float
    article_number: str
    document_title: str
    content: str
    source_url: str


class TaxLawSearchEngine:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        if not documents:
            raise ValueError("No documents were loaded.")

        self.documents = documents
        self.vectorizer = TfidfVectorizer(
            preprocessor=normalize_query_text,
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
            min_df=1,
        )
        self.matrix = self.vectorizer.fit_transform(
            document_to_search_text(document) for document in documents
        )

    def search(self, query: str, *, top_k: int = 5) -> list[SearchResult]:
        query = query.strip()
        if not query:
            return []

        query_vector = self.vectorizer.transform([query])
        scores = (self.matrix @ query_vector.T).toarray().ravel()
        ranked_indexes = scores.argsort()[::-1][:top_k]

        results: list[SearchResult] = []
        for index in ranked_indexes:
            score = float(scores[index])
            if score <= 0:
                continue
            document = self.documents[index]
            results.append(
                SearchResult(
                    score=score,
                    article_number=str(document.get("article_number", "")),
                    document_title=str(document.get("document_title", "")),
                    content=str(document.get("content", "")),
                    source_url=str(document.get("source_url", "")),
                )
            )
        return results


def normalize_query_text(text: str) -> str:
    return clean_persian_text(text, preserve_lines=False).lower()


def document_to_search_text(document: dict[str, Any]) -> str:
    parts = [
        document.get("document_title", ""),
        f"ماده {document.get('article_number', '')}",
        document.get("content", ""),
    ]
    return " ".join(str(part) for part in parts if part)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                documents.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at line {line_number}: {path}") from error
    return documents


def summarize_text(text: str, *, max_chars: int = 360) -> str:
    text = clean_persian_text(text, preserve_lines=False)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def format_answer(query: str, results: list[SearchResult]) -> str:
    if not results:
        return (
            "پاسخ کوتاه:\n"
            "برای این سوال ماده مرتبطی در دیتاست پیدا نشد.\n\n"
            "منابع:\n"
            "- منبعی یافت نشد."
        )

    top_results = results[:3]
    source_numbers = "، ".join(
        f"ماده {result.article_number}" for result in top_results
    )
    evidence_lines = [
        f"- ماده {result.article_number}: {summarize_text(result.content, max_chars=220)}"
        for result in top_results
    ]
    source_lines = [
        f"- ماده {result.article_number} | امتیاز: {result.score:.3f} | {result.source_url}"
        for result in top_results
    ]

    return "\n".join(
        [
            "پاسخ کوتاه:",
            f"برای سوال «{query}»، مرتبط‌ترین بخش‌های قانون در {source_numbers} پیدا شد. این پاسخ یک جمع‌بندی ماشینی از همان مواد است؛ برای تصمیم حقوقی متن کامل ماده‌ها باید بررسی شود.",
            "",
            "نکات مرتبط:",
            *evidence_lines,
            "",
            "منابع:",
            *source_lines,
        ]
    )


def format_results(results: list[SearchResult]) -> str:
    if not results:
        return "نتیجه مرتبطی پیدا نشد."

    blocks: list[str] = []
    for number, result in enumerate(results, start=1):
        blocks.append(
            "\n".join(
                [
                    f"{number}. ماده {result.article_number} | امتیاز: {result.score:.3f}",
                    summarize_text(result.content),
                    f"منبع: {result.source_url}",
                ]
            )
        )
    return "\n\n".join(blocks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="جست‌وجوی ساده در مواد قانون مالیات‌های مستقیم"
    )
    parser.add_argument("query", nargs="*", help="سوال یا عبارت جست‌وجو")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--raw",
        action="store_true",
        help="نمایش فقط نتایج جست‌وجو بدون پاسخ کوتاه",
    )
    return parser


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def run_interactive(engine: TaxLawSearchEngine, *, top_k: int) -> None:
    print("سوال مالیاتی را بنویس. برای خروج Enter خالی بزن.")
    while True:
        query = input("\nسوال: ").strip()
        if not query:
            break
        print(format_answer(query, engine.search(query, top_k=top_k)))


def main() -> int:
    configure_console()
    args = build_parser().parse_args()
    documents = load_jsonl(args.data)
    engine = TaxLawSearchEngine(documents)

    query = " ".join(args.query).strip()
    if query:
        results = engine.search(query, top_k=args.top_k)
        print(format_results(results) if args.raw else format_answer(query, results))
    else:
        run_interactive(engine, top_k=args.top_k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


