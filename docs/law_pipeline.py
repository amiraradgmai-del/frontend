"""Download Iranian law text, extract articles, clean Persian text, and save CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

import requests


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "هٔ",
    }
)
_PERSIAN_AND_ARABIC_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)
_DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_ARTICLE_RE = re.compile(
    r"(?m)^[\s\u200c\ufeff]*ماده\s*(?:[\(\[\-–—:]\s*)?"
    r"(?P<number>[0-9۰-۹٠-٩]+|واحده)"
    r"(?:\s*(?P<repeat>مکرر))?"
    r"(?:\s*[\)\]\-–—:ـ\.])?\s*"
)


@dataclass(frozen=True)
class Article:
    document_title: str
    article_number: str
    article_text: str
    source_url: str
    fetched_at: str


class _VisibleTextParser(HTMLParser):
    """Extract visible text while retaining block boundaries."""

    _BLOCK_TAGS = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "p",
        "section",
        "table",
        "td",
        "tr",
    }
    _IGNORED_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def html_to_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return parser.text()


def clean_persian_text(text: str, *, preserve_lines: bool = True) -> str:
    """Normalize Persian characters and whitespace without changing meaning."""

    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_ARABIC_TO_PERSIAN)
    text = _DIACRITICS_RE.sub("", text).replace("ـ", "")
    text = text.replace("\u200f", "").replace("\u200e", "")
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r" *\u200c *", "\u200c", text)

    if preserve_lines:
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
    return re.sub(r"\s+", " ", text).strip()


def extract_articles(
    text: str,
    *,
    document_title: str,
    source_url: str = "",
    fetched_at: str | None = None,
) -> list[Article]:
    """Split normalized law text at article headings such as ``ماده ۱۰``."""

    cleaned = clean_persian_text(text, preserve_lines=True)
    matches = list(_ARTICLE_RE.finditer(cleaned))
    if not matches:
        raise ValueError("هیچ عنوان ماده‌ای مانند «ماده ۱» در متن پیدا نشد.")

    timestamp = fetched_at or datetime.now(timezone.utc).isoformat()
    articles: list[Article] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        number = match.group("number").translate(_PERSIAN_AND_ARABIC_DIGITS)
        if match.group("repeat"):
            number = f"{number} مکرر"
        body = clean_persian_text(cleaned[match.end() : end], preserve_lines=False)
        if not body:
            continue
        articles.append(
            Article(
                document_title=clean_persian_text(document_title, preserve_lines=False),
                article_number=number,
                article_text=body,
                source_url=source_url,
                fetched_at=timestamp,
            )
        )

    if not articles:
        raise ValueError("عنوان ماده پیدا شد، اما متن همه ماده‌ها خالی بود.")
    return articles


def download_document(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
) -> tuple[str, str]:
    """Download a text/HTML document with a size limit."""

    headers = {"User-Agent": "TaxAIAdvisor-LawPipeline/1.0"}
    with requests.get(url, headers=headers, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError(f"حجم سند از حد مجاز {max_bytes} بایت بیشتر است.")
            chunks.append(chunk)

        content_type = response.headers.get("content-type", "").lower()
        charset_match = re.search(r"charset\s*=\s*[\"']?([^;\s\"']+)", content_type)
        declared_encoding = charset_match.group(1) if charset_match else None
        return _decode_document_bytes(b"".join(chunks), declared_encoding), content_type


def _decode_document_bytes(raw: bytes, declared_encoding: str | None = None) -> str:
    encodings = [declared_encoding] if declared_encoding else []
    encodings.extend(["utf-8-sig", "utf-8", "windows-1256"])
    for encoding in dict.fromkeys(encodings):
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    raise ValueError("رمزگذاری متن سند قابل تشخیص نیست.")


def read_local_document(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    try:
        text = _decode_document_bytes(raw)
    except ValueError as error:
        raise ValueError(f"رمزگذاری فایل قابل تشخیص نیست: {path}") from error

    content_type = "text/html" if path.suffix.lower() in {".html", ".htm"} else "text/plain"
    return text, content_type


def prepare_text(content: str, content_type: str) -> str:
    if "html" in content_type or re.search(r"<\s*(?:html|body|div|p)\b", content, re.I):
        return html_to_text(content)
    return content


def save_articles_csv(articles: Iterable[Article], output_path: Path) -> int:
    rows = [asdict(article) for article in articles]
    if not rows:
        raise ValueError("هیچ ماده‌ای برای ذخیره وجود ندارد.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="دریافت قانون، استخراج ماده‌ها، پاک‌سازی متن و ذخیره در CSV"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="نشانی سند رسمی HTML یا متنی")
    source.add_argument("--input", type=Path, help="مسیر فایل محلی HTML یا TXT")
    parser.add_argument("--title", required=True, help="عنوان قانون")
    parser.add_argument("--output", type=Path, required=True, help="مسیر CSV خروجی")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="backslashreplace")

    args = build_parser().parse_args()
    if args.url:
        content, content_type = download_document(args.url, timeout=args.timeout)
        source_url = args.url
    else:
        content, content_type = read_local_document(args.input)
        source_url = args.input.resolve().as_uri()

    text = prepare_text(content, content_type)
    articles = extract_articles(
        text,
        document_title=args.title,
        source_url=source_url,
    )
    count = save_articles_csv(articles, args.output)
    print(f"{count} ماده در {args.output} ذخیره شد.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
