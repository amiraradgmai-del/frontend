import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from tax_search import TaxLawSearchEngine, format_answer
from user_login import create_user_profile, prompt_user_profile, save_user_profile


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "data" / "direct_tax_articles.csv"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "tax_laws.jsonl"
USERS_DB_PATH = BASE_DIR / "data" / "users.db"


def save_jsonl(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def load_documents() -> list[dict]:
    dataset = pd.read_csv(DATASET_PATH, encoding="utf-8-sig")
    return dataset.rename(columns={"article_text": "content"}).to_dict(
        orient="records"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="آماده‌سازی داده، ورود کاربر و جست‌وجو در قانون مالیات‌های مستقیم"
    )
    parser.add_argument("--query", help="سوال یا عبارت جست‌وجو")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--name", help="نام کاربر")
    parser.add_argument("--last-name", help="نام خانوادگی کاربر")
    parser.add_argument("--kod-meli", help="کد ملی کاربر")
    parser.add_argument(
        "--skip-login",
        action="store_true",
        help="اجرای برنامه بدون دریافت اطلاعات ورود",
    )
    return parser


def login_user(args: argparse.Namespace) -> None:
    if args.skip_login:
        return

    has_cli_profile = bool(args.name or args.last_name or args.kod_meli)
    if has_cli_profile:
        profile = create_user_profile(
            args.name or "",
            args.last_name or "",
            args.kod_meli or "",
        )
    elif sys.stdin.isatty():
        profile = prompt_user_profile()
    else:
        return

    saved_profile = save_user_profile(profile, USERS_DB_PATH)
    print(f"سلام {saved_profile.full_name}، ورود شما با شناسه {saved_profile.id} ثبت شد.")


def main() -> int:
    configure_console()
    args = build_parser().parse_args()
    login_user(args)

    documents = load_documents()
    save_jsonl(documents, OUTPUT_PATH)
    print(f"{len(documents)} records saved to {OUTPUT_PATH}")

    if args.query:
        engine = TaxLawSearchEngine(documents)
        print()
        print(format_answer(args.query, engine.search(args.query, top_k=args.top_k)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
