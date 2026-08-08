from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

try:
    from .law_pipeline import clean_persian_text
except ImportError:
    from law_pipeline import clean_persian_text


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = BASE_DIR / "data" / "direct_tax_articles.csv"
DEFAULT_OUTPUT_PATH = BASE_DIR / "data" / "processed" / "tax_laws_v2.jsonl"
DEFAULT_REPORT_PATH = BASE_DIR / "data" / "processed" / "dataset_quality_report.json"
SCHEMA_VERSION = "2.0"

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_REPEALED_MARKER = re.compile(r"\[(?:حذف|حذفی)\s+[^\]]+\]")
_ONLY_METADATA = re.compile(
    r"^(?:\s*\[[^\]]+\]\s*[-–—]?\s*)+(?:فصل\s+[^\n]{1,80})?$"
)


@dataclass(frozen=True, slots=True)
class SourceArticle:
    document_title: str
    article_number: str
    article_text: str
    source_url: str
    fetched_at: str


@dataclass(frozen=True, slots=True)
class RagChunk:
    schema_version: str
    document_id: str
    document_version_id: str
    chunk_id: str
    document_title: str
    document_type: str
    topic: str
    article_number: str
    chunk_index: int
    content: str
    content_hash: str
    source_url: str
    source_domain: str
    source_tier: str
    fetched_at: str
    valid_from: str | None
    valid_to: str | None
    lifecycle_status: str
    review_status: str
    retrieval_eligible: bool
    language: str
    quality_flags: tuple[str, ...]


def stable_id(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:24]}"


def normalize_article_number(value: str) -> str:
    return clean_persian_text(value.translate(_PERSIAN_DIGITS), preserve_lines=False)


def load_source_articles(path: Path) -> list[SourceArticle]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {
            "document_title", "article_number", "article_text", "source_url", "fetched_at"
        }
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
        articles = [
            SourceArticle(
                document_title=clean_persian_text(row["document_title"], preserve_lines=False),
                article_number=normalize_article_number(row["article_number"]),
                article_text=clean_persian_text(row["article_text"], preserve_lines=False),
                source_url=row["source_url"].strip(),
                fetched_at=row["fetched_at"].strip(),
            )
            for row in reader
        ]
    return [article for article in articles if article.article_text]


def infer_lifecycle_status(text: str) -> str:
    if _REPEALED_MARKER.search(text) and _ONLY_METADATA.fullmatch(text):
        return "repealed"
    return "unknown"


def split_into_chunks(text: str, *, max_chars: int = 1400, overlap_chars: int = 160) -> list[str]:
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    if not 0 <= overlap_chars < max_chars:
        raise ValueError("overlap_chars must be between zero and max_chars")
    text = clean_persian_text(text, preserve_lines=False)
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        hard_end = min(start + max_chars, len(text))
        end = hard_end
        if hard_end < len(text):
            search_start = start + max_chars // 2
            candidates = [
                text.rfind(mark, search_start, hard_end)
                for mark in (". ", "؟ ", "؛ ", " ")
            ]
            boundary = max(candidates)
            if boundary >= search_start:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        next_start = max(0, end - overlap_chars)
        start = next_start if next_start > start else end
    return chunks


def infer_source_tier(source_url: str) -> str:
    hostname = (urlparse(source_url).hostname or "").lower()
    return "official" if hostname == "gov.ir" or hostname.endswith(".gov.ir") else "secondary"


def build_chunks(
    articles: Iterable[SourceArticle], *, max_chars: int = 1400, overlap_chars: int = 160
) -> list[RagChunk]:
    article_list = list(articles)
    number_counts = Counter(
        (item.document_title, item.article_number) for item in article_list
    )
    chunks: list[RagChunk] = []
    for article in article_list:
        source_domain = (urlparse(article.source_url).hostname or "").lower()
        source_tier = infer_source_tier(article.source_url)
        lifecycle_status = infer_lifecycle_status(article.article_text)
        document_id = stable_id("doc", article.document_title, article.source_url)
        version_id = stable_id("ver", document_id, article.fetched_at)
        flags: list[str] = ["missing_validity_dates", "pending_expert_review"]
        if source_tier != "official":
            flags.append("non_official_source")
        if lifecycle_status == "repealed":
            flags.append("repealed_marker")
        if len(article.article_text) < 40:
            flags.append("very_short_text")
        if len(article.article_text) > max_chars:
            flags.append("article_split_into_chunks")
        if number_counts[(article.document_title, article.article_number)] > 1:
            flags.append("duplicate_article_number")

        for index, content in enumerate(
            split_into_chunks(article.article_text, max_chars=max_chars, overlap_chars=overlap_chars)
        ):
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            chunk_id = stable_id(
                "chk", version_id, article.article_number, str(index), content_hash
            )
            chunks.append(
                RagChunk(
                    schema_version=SCHEMA_VERSION,
                    document_id=document_id,
                    document_version_id=version_id,
                    chunk_id=chunk_id,
                    document_title=article.document_title,
                    document_type="law",
                    topic="مالیات‌های مستقیم",
                    article_number=article.article_number,
                    chunk_index=index,
                    content=content,
                    content_hash=content_hash,
                    source_url=article.source_url,
                    source_domain=source_domain,
                    source_tier=source_tier,
                    fetched_at=article.fetched_at,
                    valid_from=None,
                    valid_to=None,
                    lifecycle_status=lifecycle_status,
                    review_status="pending_review",
                    retrieval_eligible=False,
                    language="fa",
                    quality_flags=tuple(sorted(flags)),
                )
            )
    return chunks


def save_jsonl(chunks: Iterable[RagChunk], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for chunk in chunks:
            file.write(json.dumps(asdict(chunk), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def build_quality_report(articles: list[SourceArticle], chunks: list[RagChunk]) -> dict:
    flag_counts = Counter(flag for chunk in chunks for flag in chunk.quality_flags)
    lifecycle_counts = Counter(chunk.lifecycle_status for chunk in chunks)
    source_tier_counts = Counter(chunk.source_tier for chunk in chunks)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_article_count": len(articles),
        "chunk_count": len(chunks),
        "unique_document_count": len({chunk.document_id for chunk in chunks}),
        "unique_chunk_count": len({chunk.chunk_id for chunk in chunks}),
        "retrieval_eligible_count": sum(chunk.retrieval_eligible for chunk in chunks),
        "lifecycle_status_counts": dict(sorted(lifecycle_counts.items())),
        "source_tier_counts": dict(sorted(source_tier_counts.items())),
        "quality_flag_counts": dict(sorted(flag_counts.items())),
        "max_chunk_chars": max((len(chunk.content) for chunk in chunks), default=0),
        "requires_expert_review": True,
        "notes": [
            "No record is retrieval-eligible until an expert approves its source and validity dates.",
            "Repeated article numbers are preserved because they can represent repealed and amended versions.",
        ],
    }


def save_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the versioned RAG dataset")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--max-chars", type=int, default=1400)
    parser.add_argument("--overlap-chars", type=int, default=160)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    articles = load_source_articles(args.input)
    chunks = build_chunks(
        articles, max_chars=args.max_chars, overlap_chars=args.overlap_chars
    )
    count = save_jsonl(chunks, args.output)
    save_report(build_quality_report(articles, chunks), args.report)
    print(f"Saved {count} chunks to {args.output}")
    print(f"Quality report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
