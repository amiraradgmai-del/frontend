from app.ai.orchestrator import select_agent


def test_selects_accounting_agent():
    assert select_agent("این تراز و دفاتر حسابداری را بررسی کن").code == "accounting"


def test_selects_legal_agent():
    assert select_agent("برای اعتراض یک لایحه بنویس").code == "legal"


def test_defaults_to_tax_agent():
    assert select_agent("مالیات بر درآمد چیست؟").code == "tax"
