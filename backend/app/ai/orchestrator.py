from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDecision:
    code: str
    title: str
    capabilities: tuple[str, ...]


AGENTS = {
    "tax": AgentDecision("tax", "کارشناس مالیاتی", ("rag", "legal_search", "risk_flags")),
    "accounting": AgentDecision("accounting", "کارشناس حسابداری", ("document_analysis", "calculation")),
    "legal": AgentDecision("legal", "کارشناس حقوقی", ("legal_search", "drafting")),
    "support": AgentDecision("support", "راهنمای سامانه", ("site_navigation", "support")),
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
