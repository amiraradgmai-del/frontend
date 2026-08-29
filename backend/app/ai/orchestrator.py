from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDecision:
    code: str
    title: str
    capabilities: tuple[str, ...]
    system_prompt: str


AGENTS = {
    "tax": AgentDecision("tax", "کارشناس مالیاتی", ("rag", "legal_search", "risk_flags"), "در نقش کارشناس مالیاتی ایران پاسخ بده. سال مالی، نوع مؤدی، قانون حاکم، مهلت، ریسک و اقدام بعدی را مشخص کن. حکم یا عدد قانونی را فقط با منبع بازیابی‌شده بیان کن و در نبود منبع قطعی سؤال تکمیلی بپرس."),
    "accounting": AgentDecision("accounting", "کارشناس حسابداری", ("document_analysis", "calculation"), "در نقش کارشناس حسابداری پاسخ بده. مسئله را به ثبت حسابداری، بدهکار و بستانکار، اثر بر تراز و صورت‌های مالی و کنترل‌های لازم تفکیک کن. عددسازی نکن و محاسبه حساس را به ابزار Backend ارجاع بده."),
    "legal": AgentDecision("legal", "کارشناس اعتراضات مالیاتی", ("legal_search", "drafting"), "در نقش کارشناس اعتراضات و دادرسی مالیاتی ایران پاسخ بده. مرجع رسیدگی، مهلت، مستند قانونی، مدارک، ترتیب اقدام و ریسک از دست‌رفتن حق اعتراض را روشن کن. متن لایحه را پیش‌نویس و نه نظر قطعی حقوقی معرفی کن."),
    "support": AgentDecision("support", "راهنمای سامانه چکاه", ("site_navigation", "support"), "در نقش راهنمای سامانه چکاه پاسخ کوتاه و مرحله‌ای بده. فقط درباره ورود، حساب، اشتراک، پرداخت، اسناد، ابزارها، مشاوران و مسیرهای داخل سامانه راهنمایی کن؛ اگر مشکل نیازمند بررسی انسانی است کاربر را به تیکت پشتیبانی هدایت کن."),
}


def select_agent(question: str) -> AgentDecision:
    normalized = " ".join(question.split()).lower()
    if any(term in normalized for term in ("تراز", "دفتر", "صورت مالی", "حسابداری", "سند حسابداری")):
        return AGENTS["accounting"]
    if any(term in normalized for term in ("قرارداد", "دادخواست", "حقوقی", "لایحه", "اعتراض")):
        return AGENTS["legal"]
    if any(term in normalized for term in ("ورود", "رمز", "اشتراک", "پرداخت", "پشتیبانی", "کار با سایت")):
        return AGENTS["support"]
    return AGENTS["tax"]


def get_agent(code: str | None, question: str) -> AgentDecision:
    """Honor an explicit UI choice; otherwise route from the question."""
    return AGENTS.get(code or "") or select_agent(question)
