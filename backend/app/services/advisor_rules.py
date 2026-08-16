from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from app.documents.text import normalize_persian

PROHIBITED_TERMS = {
    "فرار مالیاتی": "tax_evasion",
    "فاکتور صوری": "fake_invoice",
    "پنهان کردن درآمد": "income_concealment",
    "پنهان‌کردن درآمد": "income_concealment",
    "ثبت اطلاعات خلاف واقع": "false_information",
    "دور زدن مالیات": "tax_evasion",
    "دورزدن مالیات": "tax_evasion",
    "پنهان کردن فروش": "sales_concealment",
    "پنهان‌کردن فروش": "sales_concealment",
    "ثبت نکردن فروش": "sales_concealment",
    "پنهان کنم": "income_concealment",
    "حذف درآمد": "income_concealment",
    "اطلاعات خلاف واقع": "false_information",
    "دور زدن ثبت صورتحساب": "tax_evasion",
    "دور زدن صورتحساب": "tax_evasion",
}
SENSITIVE_TERMS = {
    "برگ تشخیص": "assessment_notice",
    "ابلاغ": "official_notice",
    "اعتراض": "appeal",
    "هیئت حل اختلاف": "tax_dispute_board",
    "اجرائیه": "enforcement_order",
    "لایحه": "legal_brief",
    "بدهی": "tax_debt",
    "قرارداد": "contract_review",
}
DEADLINE_TERMS = {"مهلت", "تا چه تاریخی", "چند روز", "اعتراض"}
SOURCE_REQUIRED_TERMS = {
    "ماده", "تبصره", "بند", "نرخ", "درصد", "مبلغ", "مهلت", "جریمه",
    "معافیت", "نصاب", "بخشنامه", "رأی", "رای", "جدیدترین", "آخرین",
    "امروز", "امسال", "سال", "تاریخ", "قانون فعلی",
}
TAX_TERMS = {
    "مالیات", "مالیاتی", "اظهارنامه", "مودی", "مؤدی", "ارزش افزوده",
    "صورتحساب", "سامانه مودیان", "درگاه مالیاتی", "بخشودگی", "جرایم",
    "درآمد", "هزینه قابل قبول", "دفاتر قانونی", "کد اقتصادی", "تکالیف",
    "دانش بنیان", "دانش‌بنیان", "دانشبنیان", "شرکت دانش بنیان",
    "اعتبار مالیاتی", "معافیت", "بیمه", "حقوق", "دستمزد", "ارث",
    "وقف", "وصیت", "کسب و کار", "شرکت", "اشخاص حقیقی", "اشخاص حقوقی",
}
TAX_KEYWORDS = {
    token
    for term in TAX_TERMS
    for token in re.findall(r"\w+", normalize_persian(term).lower())
    if len(token) >= 4
}


@dataclass(frozen=True)
class RuleResult:
    prohibited_reason: str | None
    escalation_reasons: list[str]
    clarifying_questions: list[str]
    out_of_scope: bool
    source_required: bool
    casual_answer: str | None

    @property
    def needs_expert(self) -> bool:
        return bool(self.escalation_reasons)


def evaluate_question(question: str) -> RuleResult:
    normalized = normalize_persian(question).lower()
    casual_answer = detect_casual_response(normalized)
    prohibited_reason = next(
        (reason for phrase, reason in PROHIBITED_TERMS.items() if phrase in normalized),
        None,
    )
    escalation_reasons = sorted(
        {reason for phrase, reason in SENSITIVE_TERMS.items() if phrase in normalized}
    )
    tax_related = any(term in normalized for term in TAX_TERMS) or _looks_tax_related(
        normalized
    )
    source_required = any(term in normalized for term in SOURCE_REQUIRED_TERMS) or any(
        char.isdigit() for char in normalized
    )
    unsupported_context = any(term in normalized for term in ("مریخ", "سیاره", "فضانوردی"))
    out_of_scope = casual_answer is None and (not tax_related or unsupported_context)
    questions: list[str] = []
    if any(term in normalized for term in DEADLINE_TERMS):
        if not any(char.isdigit() for char in normalized):
            questions.append("تاریخ رویداد یا ابلاغ موردنظر چیست؟")
        questions.append("نوع مؤدی و دوره مالیاتی را مشخص می‌کنید؟")
    if "جریمه" in normalized and not any(char.isdigit() for char in normalized):
        questions.append("نوع جریمه و دوره مالیاتی موردنظر چیست؟")
    time_sensitive = any(
        term in normalized
        for term in ("نرخ", "معافیت", "نصاب", "سقف", "مهلت", "جریمه", "امسال", "سال جاری")
    )
    has_fiscal_year = bool(re.search(r"\b1[34]\d{2}\b", normalized.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))))
    if time_sensitive and not has_fiscal_year:
        questions.append("سال مالی یا سال عملکرد موردنظر چیست؟")
    return RuleResult(
        prohibited_reason=prohibited_reason,
        escalation_reasons=escalation_reasons,
        clarifying_questions=list(dict.fromkeys(questions)),
        out_of_scope=out_of_scope,
        source_required=source_required,
        casual_answer=casual_answer,
    )


def _looks_tax_related(normalized: str) -> bool:
    tokens = [
        token
        for token in re.findall(r"\w+", normalized)
        if len(token) >= 4
    ]
    for token in tokens:
        for keyword in TAX_KEYWORDS:
            threshold = 0.78 if min(len(token), len(keyword)) < 6 else 0.72
            if SequenceMatcher(None, token, keyword).ratio() >= threshold:
                return True
    return False


def detect_casual_response(normalized: str) -> str | None:
    compact = normalized.strip(" ؟?!،,.\n\t")
    if compact.startswith(("سلام", "درود", "صبح بخیر", "عصر بخیر", "شب بخیر")):
        return "سلام! خوش آمدید. درباره موضوعات مالیاتی، اظهارنامه، ارزش افزوده یا سامانه مؤدیان چه کمکی از من برمی‌آید؟"
    if compact.startswith(("ممنون", "مرسی", "سپاس")):
        return "خواهش می‌کنم. اگر پرسش مالیاتی دیگری دارید، در خدمتم."
    if compact.startswith(("خداحافظ", "فعلا", "فعلاً")):
        return "خدانگهدار؛ هر زمان پرسش مالیاتی داشتید، در خدمتم."
    if "تو کی هستی" in compact or "شما کی هستید" in compact:
        return "من چکاه، دستیار هوشمند مالیاتی هستم؛ پاسخ‌های مستند را از بانک دانش می‌دهم و برای توضیحات عمومی کم‌ریسک نیز به‌صورت کنترل‌شده کمک می‌کنم."
    if compact in {"خوبی", "حالت چطوره", "چه خبر"}:
        return "ممنون، آماده‌ام کمک کنم. سؤال مالیاتی‌تان را بنویسید."
    return None
