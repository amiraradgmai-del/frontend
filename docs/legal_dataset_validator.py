from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


def load_json(path: Path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at line {line_number}") from error
    return records


def validate(manifest: dict, records: list[dict]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    allowed_domains = set(manifest["policy"]["allowed_domains"])
    required_fields = {
        "record_id",
        "source_id",
        "article_number",
        "official_text",
        "source_url",
        "lifecycle_status",
        "review_status",
    }
    record_ids = Counter()
    text_hashes = Counter()
    articles: dict[str, set[str]] = defaultdict(set)

    for index, record in enumerate(records, start=1):
        missing = required_fields - set(record)
        if missing:
            errors.append(f"record {index}: missing {sorted(missing)}")
            continue
        record_ids[str(record["record_id"])] += 1
        official_text = str(record["official_text"]).strip()
        if len(official_text) < 20:
            errors.append(f"{record['record_id']}: text is too short")
        digest = hashlib.sha256(official_text.encode("utf-8")).hexdigest()
        text_hashes[digest] += 1
        articles[str(record["source_id"])].add(str(record["article_number"]))
        domain = urlparse(str(record["source_url"])).hostname or ""
        if domain.removeprefix("www.") not in allowed_domains:
            errors.append(f"{record['record_id']}: non-official source domain")
        if record.get("retrieval_eligible") and record.get("review_status") != "approved":
            errors.append(f"{record['record_id']}: unapproved record is retrieval eligible")

    for record_id, count in record_ids.items():
        if count > 1:
            errors.append(f"duplicate record_id: {record_id}")
    duplicate_texts = sum(1 for count in text_hashes.values() if count > 1)
    if duplicate_texts:
        warnings.append(f"duplicate text groups: {duplicate_texts}")

    for source in manifest["confirmed_primary_sources"]:
        count = len(articles[source["source_id"]])
        minimum = int(source["minimum_unique_articles"])
        if count < minimum:
            errors.append(
                f"{source['source_id']}: {count} unique articles; minimum is {minimum}"
            )

    return {
        "passed": not errors,
        "record_count": len(records),
        "source_article_counts": {
            source_id: len(numbers) for source_id, numbers in sorted(articles.items())
        },
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the official tax-law dataset")
    parser.add_argument("dataset", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).parents[1]
        / "data"
        / "legal_sources"
        / "official_source_manifest.json",
    )
    args = parser.parse_args()
    report = validate(load_json(args.manifest), load_jsonl(args.dataset))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
