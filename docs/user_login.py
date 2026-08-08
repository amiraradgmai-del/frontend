from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


_DIGITS_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)


@dataclass(frozen=True)
class UserProfile:
    id: int | None
    name: str
    last_name: str
    kod_meli: str

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.last_name}".strip()


def normalize_kod_meli(kod_meli: str) -> str:
    return re.sub(r"\D", "", kod_meli.translate(_DIGITS_TRANSLATION))


def validate_kod_meli(kod_meli: str) -> str:
    normalized = normalize_kod_meli(kod_meli)
    if not re.fullmatch(r"\d{10}", normalized):
        raise ValueError("کد ملی باید دقیقاً ۱۰ رقم باشد.")
    if len(set(normalized)) == 1:
        raise ValueError("کد ملی معتبر نیست.")

    total = sum(int(normalized[index]) * (10 - index) for index in range(9))
    remainder = total % 11
    check_digit = int(normalized[9])
    is_valid = check_digit == remainder if remainder < 2 else check_digit == 11 - remainder
    if not is_valid:
        raise ValueError("کد ملی معتبر نیست.")
    return normalized


def create_user_profile(name: str, last_name: str, kod_meli: str) -> UserProfile:
    name = name.strip()
    last_name = last_name.strip()
    if not name:
        raise ValueError("نام نمی‌تواند خالی باشد.")
    if not last_name:
        raise ValueError("نام خانوادگی نمی‌تواند خالی باشد.")

    return UserProfile(
        id=None,
        name=name,
        last_name=last_name,
        kod_meli=validate_kod_meli(kod_meli),
    )


def prompt_user_profile() -> UserProfile:
    print("ورود کاربر")
    name = input("نام: ")
    last_name = input("نام خانوادگی: ")
    kod_meli = input("کد ملی: ")
    return create_user_profile(name, last_name, kod_meli)


def init_user_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                kod_meli TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.commit()


def save_user_profile(profile: UserProfile, db_path: Path) -> UserProfile:
    init_user_db(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO users (name, last_name, kod_meli)
            VALUES (?, ?, ?)
            ON CONFLICT(kod_meli) DO UPDATE SET
                name = excluded.name,
                last_name = excluded.last_name
            """,
            (profile.name, profile.last_name, profile.kod_meli),
        )
        cursor = connection.execute(
            "SELECT id FROM users WHERE kod_meli = ?",
            (profile.kod_meli,),
        )
        user_id = int(cursor.fetchone()[0])
        connection.commit()

    return UserProfile(
        id=user_id,
        name=profile.name,
        last_name=profile.last_name,
        kod_meli=profile.kod_meli,
    )
