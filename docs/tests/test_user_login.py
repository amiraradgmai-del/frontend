import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from docs.user_login import (
    create_user_profile,
    init_user_db,
    normalize_kod_meli,
    save_user_profile,
)


class UserLoginTests(unittest.TestCase):
    def test_normalize_kod_meli_accepts_persian_digits(self) -> None:
        self.assertEqual(normalize_kod_meli("۰۰۱-۰۳۵-۰۸۲۹"), "0010350829")

    def test_create_user_profile_validates_required_fields(self) -> None:
        with self.assertRaises(ValueError):
            create_user_profile("", "رضایی", "0010350829")

    def test_create_user_profile_rejects_invalid_kod_meli(self) -> None:
        with self.assertRaises(ValueError):
            create_user_profile("علی", "رضایی", "1111111111")

    def test_init_user_db_creates_required_fields_and_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "users.db"
            init_user_db(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                columns = connection.execute("PRAGMA table_info(users)").fetchall()
                indexes = connection.execute("PRAGMA index_list(users)").fetchall()

        column_names = [column[1] for column in columns]
        self.assertEqual(column_names, ["id", "name", "last_name", "kod_meli"])
        self.assertEqual(columns[0][5], 1)
        self.assertTrue(any(index[2] for index in indexes))

    def test_save_user_profile_inserts_and_updates_by_kod_meli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "users.db"
            first_profile = create_user_profile("علی", "رضایی", "0010350829")
            second_profile = create_user_profile("علی", "احمدی", "0010350829")

            saved_first = save_user_profile(first_profile, db_path)
            saved_second = save_user_profile(second_profile, db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                rows = connection.execute(
                    "SELECT id, name, last_name, kod_meli FROM users"
                ).fetchall()

        self.assertEqual(saved_first.id, saved_second.id)
        self.assertEqual(rows, [(saved_first.id, "علی", "احمدی", "0010350829")])


if __name__ == "__main__":
    unittest.main()
