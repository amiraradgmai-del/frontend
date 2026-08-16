from __future__ import annotations

import io
import base64

import pymupdf
import pytest
from docx import Document

from app.documents.storage import EncryptedObjectStorage, LocalObjectStorage
from app.documents.text import build_chunks, extract_pages, normalize_persian
from app.documents.validation import FileValidationError, safe_filename, validate_upload


def make_docx(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def make_pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def test_upload_validation_checks_extension_mime_signature_and_size() -> None:
    valid = validate_upload("law.txt", "text/plain", "ماده ۱ متن قانون".encode(), 1024)
    assert valid.extension == ".txt"
    with pytest.raises(FileValidationError) as invalid_pdf:
        validate_upload("fake.pdf", "application/pdf", b"not a pdf", 1024)
    assert invalid_pdf.value.code == "invalid_pdf"
    with pytest.raises(FileValidationError) as too_large:
        validate_upload("large.txt", "text/plain", b"x" * 20, 10)
    assert too_large.value.code == "file_too_large"


def test_docx_and_pdf_are_structurally_validated_and_extracted() -> None:
    docx_data = make_docx("ماده ۱۲ متن آزمایشی قانون")
    docx_upload = validate_upload(
        "law.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        docx_data,
        100_000,
    )
    assert "ماده ۱۲" in extract_pages(docx_upload.data, docx_upload.extension)[0].text

    pdf_data = make_pdf("Article 12 tax law")
    pdf_upload = validate_upload("law.pdf", "application/pdf", pdf_data, 100_000)
    assert "Article 12" in extract_pages(pdf_upload.data, pdf_upload.extension)[0].text


def test_persian_normalization_and_structural_chunking() -> None:
    text = "ماده ۱- ماليات بر كسب. " + ("توضیح تکمیلی. " * 100) + " ماده ۲- متن دوم"
    normalized = normalize_persian(text)
    assert "مالیات" in normalized
    assert "کسب" in normalized
    chunks = build_chunks(
        extract_pages(normalized.encode(), ".txt"), max_chars=300, overlap_chars=30
    )
    assert len(chunks) > 2
    assert all(len(chunk.content) <= 300 for chunk in chunks)
    assert chunks[0].article_number == "۱"
    assert chunks[-1].article_number == "۲"


def test_local_storage_rejects_path_traversal(tmp_path) -> None:
    storage = LocalObjectStorage(tmp_path)
    storage.put("documents/one.txt", b"safe", "text/plain")
    assert storage.get("documents/one.txt") == b"safe"
    with pytest.raises(ValueError):
        storage.put("../escape.txt", b"unsafe", "text/plain")
    assert safe_filename("../../tax-law.txt") == "tax-law.txt"


def test_encrypted_storage_hides_plaintext_supports_rotation_and_legacy(tmp_path) -> None:
    raw = LocalObjectStorage(tmp_path)
    old_key = base64.b64encode(b"o" * 32).decode()
    new_key = base64.b64encode(b"n" * 32).decode()
    old_storage = EncryptedObjectStorage(raw, old_key)
    old_storage.put("documents/private.txt", b"secret tax document", "text/plain")
    stored = (tmp_path / "documents" / "private.txt").read_bytes()
    assert stored.startswith(EncryptedObjectStorage.MAGIC)
    assert b"secret tax document" not in stored

    rotated = EncryptedObjectStorage(raw, f"{new_key},{old_key}")
    assert rotated.get("documents/private.txt") == b"secret tax document"
    rotated.put("documents/new.txt", b"new encrypted content", "text/plain")
    assert rotated.get("documents/new.txt") == b"new encrypted content"

    raw.put("documents/legacy.txt", b"legacy plaintext", "text/plain")
    assert rotated.get("documents/legacy.txt") == b"legacy plaintext"

    wrong = EncryptedObjectStorage(raw, base64.b64encode(b"x" * 32).decode())
    with pytest.raises(ValueError, match="authenticated"):
        wrong.get("documents/private.txt")
