from __future__ import annotations

import io

import pymupdf
import pytest
from docx import Document
from openpyxl import Workbook

from app.documents.storage import LocalObjectStorage
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


def make_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "اظهارنامه"
    sheet.append(["عنوان", "مبلغ"])
    sheet.append(["فروش", 1250000])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


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

    xlsx_data = make_xlsx()
    xlsx_upload = validate_upload(
        "declaration.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        xlsx_data,
        100_000,
    )
    extracted_sheet = extract_pages(xlsx_upload.data, xlsx_upload.extension)[0].text
    assert "اظهارنامه" in extracted_sheet
    assert "1250000" in extracted_sheet


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
