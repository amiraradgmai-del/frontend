from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class FileValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    filename: str
    extension: str
    mime_type: str
    data: bytes


def safe_filename(filename: str) -> str:
    name = PurePath(filename.replace("\\", "/")).name.strip()
    name = re.sub(r"[^\w.() -]", "_", name, flags=re.UNICODE)
    if not name or name in {".", ".."}:
        raise FileValidationError("invalid_filename", "Filename is invalid")
    return name[:255]


def validate_upload(
    filename: str,
    declared_content_type: str | None,
    data: bytes,
    max_bytes: int,
) -> ValidatedUpload:
    if not data:
        raise FileValidationError("empty_file", "Uploaded file is empty")
    if len(data) > max_bytes:
        raise FileValidationError("file_too_large", "Uploaded file exceeds size limit")
    clean_name = safe_filename(filename)
    extension = PurePath(clean_name).suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise FileValidationError(
            "unsupported_extension", "Only PDF, DOCX, XLSX, TXT, JPG, PNG and WEBP are allowed"
        )
    expected_mime = ALLOWED_TYPES[extension]
    declared = (declared_content_type or "").lower().split(";", 1)[0].strip()
    if declared and declared not in {expected_mime, "application/octet-stream"}:
        raise FileValidationError(
            "mime_mismatch", "Declared file type does not match extension"
        )

    if extension == ".pdf" and not data.startswith(b"%PDF-"):
        raise FileValidationError("invalid_pdf", "PDF signature is invalid")
    if extension in {".docx", ".xlsx"}:
        try:
            with ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
                if (
                    "[Content_Types].xml" not in names
                    or (
                        extension == ".docx" and "word/document.xml" not in names
                    )
                    or (
                        extension == ".xlsx" and "xl/workbook.xml" not in names
                    )
                ):
                    raise FileValidationError(
                        "invalid_office_file", "Office document structure is invalid"
                    )
        except BadZipFile as error:
            raise FileValidationError(
                "invalid_office_file", "Office document archive is invalid"
            ) from error
    if extension in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8\xff"):
        raise FileValidationError("invalid_image", "JPEG signature is invalid")
    if extension == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise FileValidationError("invalid_image", "PNG signature is invalid")
    if extension == ".webp" and not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        raise FileValidationError("invalid_image", "WEBP signature is invalid")
    if extension == ".txt":
        if b"\x00" in data:
            raise FileValidationError("invalid_text", "Text file contains binary data")
        try:
            data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise FileValidationError(
                "invalid_encoding", "Text file must be UTF-8"
            ) from error
    return ValidatedUpload(clean_name, extension, expected_mime, data)
