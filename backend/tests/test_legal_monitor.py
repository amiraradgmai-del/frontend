from app.services.legal_monitor import clean_title, extract_visible_text, pdf_url


def test_official_source_metadata_is_extracted():
    page = """
    <html><head><title> قانون مالیات‌های مستقیم </title></head>
    <body><a href="/uploads/law.pdf">اصل قانون</a></body></html>
    """
    assert clean_title(page) == "قانون مالیات‌های مستقیم"
    assert pdf_url("https://regulation.tax.gov.ir/lwvi?id=1", page) == (
        "https://regulation.tax.gov.ir/uploads/law.pdf"
    )


def test_visible_text_ignores_scripts_when_page_has_content():
    page = (
        "<html><script>کد نمایشی طولانی و نامعتبر</script><body>"
        + "<p>متن رسمی قانون و توضیحات معتبر مالیاتی برای استفاده در سامانه.</p>" * 30
        + "</body></html>"
    )
    text = extract_visible_text(page)
    assert "متن رسمی قانون" in text
    assert "کد نمایشی" not in text
