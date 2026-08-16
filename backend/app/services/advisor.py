from __future__ import annotations

import re
import math
import threading
import time
from functools import lru_cache
from dataclasses import dataclass
from datetime import date, datetime, timezone
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.documents.text import normalize_persian
from app.models.advisor import Conversation
from app.models.auth import User
from app.models.documents import DocumentChunk
from app.models.portal import LawReferenceRecord
from app.models.portal import UserProfile
from app.repositories.advisor import AdvisorRepository
from app.repositories.auth import AuthRepository
from app.schemas.advisor import AskResponse, CitationResponse
from app.services.advisor_rules import evaluate_question
from app.services.site import get_ai_policy
from app.ai.providers import AnswerProvider, DisabledAIProvider, EmbeddingProvider, cosine_similarity
from app.ai.orchestrator import select_agent

DISCLAIMER = "این پاسخ صرفاً اطلاعات عمومی است و جایگزین مشاوره تخصصی مالیاتی نیست."
STOP_WORDS = {
    "از", "به", "در", "با", "برای", "که", "این", "آن", "را", "و", "یا",
    "چیست", "است", "شود", "تفاوت", "تکلیف", "تکالیف", "مالیاتی", "قانون",
    "چه", "چگونه", "کدام", "آیا", "ممکن", "امکان", "بررسی", "عمومی",
    "همزمان", "هم‌زمان", "مورد", "موارد", "دارد", "باشد", "کرده",
    "حکم", "موضوع",
}
TERM_ALIASES = {
    "حریم": "جریمه",
    "جرائم": "جریمه",
    "جرایم": "جریمه",
    "جرايم": "جریمه",
    "جریمه‌ها": "جریمه",
    "مؤدیان": "مؤدی",
    "مودیان": "مؤدی",
    "دانشبنیان": "دانش‌بنیان",
    "دانشبیان": "دانش‌بنیان",
    "دانشنیان": "دانش‌بنیان",
    "مالیاتب": "مالیات",
    "مالیایت": "مالیات",
    "اظهارنام": "اظهارنامه",
    "اظهارنامهی": "اظهارنامه",
}
FUZZY_DOMAIN_TERMS = {
    "مالیات", "مالیاتی", "اظهارنامه", "مؤدی", "مودیان", "معافیت",
    "جریمه", "دانش‌بنیان", "صورتحساب", "بخشودگی", "درآمد",
}
DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class ConversationNotFoundError(Exception):
    pass


class MessageNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class SearchHit:
    chunk: DocumentChunk
    score: float


@dataclass(frozen=True)
class LawHit:
    record: "LawRecordSnapshot | LawReferenceRecord"
    score: float


@dataclass(frozen=True)
class LawRecordSnapshot:
    id: str
    source_id: str
    law_name: str
    chapter: str
    article_number: str
    official_text: str
    keywords: str
    source_url: str
    source_type: str
    legal_status: str
    fiscal_year: int | None
    effective_date: date | None
    expiry_date: date | None
    last_verified_at: datetime | None


_law_index_cache: dict[str, tuple[float, list[tuple[LawRecordSnapshot, set[str], set[str], str]]]] = {}
_law_index_lock = threading.Lock()
_law_index_ttl_seconds = 120.0


@lru_cache(maxsize=32768)
def _cached_terms(text: str) -> frozenset[str]:
    tokens = {
        token
        for token in re.findall(r"\w+", normalize_persian(text).lower())
        if len(token) > 1 and token not in STOP_WORDS
    }
    normalized_tokens: set[str] = set()
    for token in tokens:
        aliased = TERM_ALIASES.get(token, token)
        if aliased == token and len(token) >= 5:
            match = max(
                FUZZY_DOMAIN_TERMS,
                key=lambda candidate: SequenceMatcher(None, token, candidate).ratio(),
            )
            ratio = SequenceMatcher(None, token, match).ratio()
            if ratio >= 0.78:
                aliased = match
        normalized_tokens.add(aliased)
    return frozenset(normalized_tokens)


def terms(text: str) -> set[str]:
    return set(_cached_terms(text))


class AdvisorService:
    def __init__(
        self,
        session: Session,
        provider: AnswerProvider | EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.repository = AdvisorRepository(session)
        self.audit = AuthRepository(session)
        self.provider = provider or DisabledAIProvider()

    def search(
        self,
        question: str,
        *,
        as_of_date: date | None = None,
        topics: list[str] | None = None,
        limit: int = 5,
    ) -> list[SearchHit]:
        query_terms = terms(question)
        if not query_terms:
            return []
        chunks = self.repository.active_chunks(as_of_date=as_of_date, topics=topics)
        lexical_scores: dict[str, float] = {}
        indexed_chunks: list[tuple[DocumentChunk, set[str]]] = []
        for chunk in chunks:
            chunk_terms = terms(f"{chunk.section_title or ''} {chunk.article_number or ''} {chunk.content}")
            indexed_chunks.append((chunk, chunk_terms))
            overlap = query_terms & chunk_terms
            if overlap:
                lexical_score = len(overlap) / len(query_terms) + len(overlap) / max(len(chunk_terms), 1)
                if chunk.article_number and chunk.article_number in question:
                    lexical_score += 0.5
                lexical_scores[chunk.id] = min(lexical_score, 1.0)

        query_vector = self.provider.embed_query(question)
        combined: list[SearchHit] = []
        for chunk, _chunk_terms in indexed_chunks:
            lexical = lexical_scores.get(chunk.id, 0.0)
            semantic = cosine_similarity(query_vector, chunk.embedding_json) if query_vector is not None and chunk.embedding_json else 0.0
            if lexical <= 0 and semantic < 0.32:
                continue
            score = (0.68 * lexical) + (0.32 * max(semantic, 0.0)) if lexical else semantic
            combined.append(SearchHit(chunk, min(score, 1.0)))
        return sorted(combined, key=lambda hit: hit.score, reverse=True)[:limit]

    def search_law_records(
        self,
        question: str,
        limit: int = 8,
        *,
        as_of_date: date | None = None,
    ) -> list[LawHit]:
        query_terms = terms(question)
        if not query_terms:
            return []
        normalized_question = normalize_persian(question).lower().translate(DIGIT_TRANSLATION)
        requested_year_match = re.search(r"\b(1[34]\d{2})\b", normalized_question)
        requested_year = int(requested_year_match.group(1)) if requested_year_match else None
        target_date = as_of_date or date.today()
        article_match = re.search(r"(?:ماده\s*)?(\d+)\s*(?:مکرر)?", normalized_question)
        requested_article = article_match.group(1) if article_match and "ماده" in normalized_question else None
        if "ارث" in normalized_question:
            query_terms.update({"متوفی", "وراث", "فوت", "ماترک"})
        if any(term in normalized_question for term in ("وقف", "وصیت", "نذر", "حبس")):
            query_terms.update({"متولی", "وصی", "واقف"})
        indexed_records = self._law_index()
        # Collapse duplicate imports of the same provision before scoring.
        # PDF/Excel imports commonly create a short table-of-contents row and
        # a second row containing the actual article.  Scoring both allows the
        # heading to win on keyword density even though it has no legal rule.
        deduplicated: dict[
            tuple[str, str, int | None, str],
            tuple[LawRecordSnapshot, set[str], set[str], str],
        ] = {}
        for indexed in indexed_records:
            record = indexed[0]
            if record.source_id == "curated-tax-qa" or not record.article_number.strip():
                key = (record.id, "", record.fiscal_year, record.legal_status)
            else:
                key = (
                    normalize_persian(record.law_name).replace("‌", " ").strip(),
                    record.article_number.translate(DIGIT_TRANSLATION).strip(),
                    record.fiscal_year,
                    record.legal_status,
                )
            current = deduplicated.get(key)
            if current is None or len(record.official_text.strip()) > len(current[0].official_text.strip()):
                deduplicated[key] = indexed
        indexed_records = list(deduplicated.values())
        document_frequency = {term: 0 for term in query_terms}
        for _record, record_terms, _keyword_terms, _keyword_text in indexed_records:
            for term in query_terms & record_terms:
                document_frequency[term] += 1
        term_weights = {
            term: math.log((len(indexed_records) + 1) / (document_frequency[term] + 1)) + 1
            for term in query_terms
        }
        total_query_weight = sum(term_weights.values()) or 1.0
        asks_for_article = self._asks_for_article(question)
        hits: list[LawHit] = []
        for record, record_terms, keyword_terms, keyword_text in indexed_records:
            if record.legal_status not in {"valid", "unknown"}:
                continue
            if record.effective_date and record.effective_date > target_date:
                continue
            if record.expiry_date and record.expiry_date < target_date:
                continue
            if requested_year and record.fiscal_year and record.fiscal_year != requested_year:
                continue
            if (
                record.source_id == "curated-tax-qa"
                and self._is_ambiguous_curated_question(keyword_text)
                and not asks_for_article
            ):
                continue
            # Chapter/index rows imported from PDFs often contain only a
            # heading and article number. They are not evidence for a topical
            # legal answer. Keep them available only for an explicit article
            # lookup, where the user can intentionally request that record.
            if (
                record.source_id != "curated-tax-qa"
                and len(record.official_text.strip()) < 120
                and not requested_article
            ):
                continue
            overlap = query_terms & record_terms
            if not overlap:
                continue
            keyword_similarity = SequenceMatcher(
                None, normalized_question, keyword_text
            ).ratio()
            keyword_overlap_terms = query_terms & keyword_terms
            keyword_overlap = (
                sum(term_weights[term] for term in keyword_overlap_terms)
                / total_query_weight
            )
            specific_query_terms = query_terms - {"مالیات"}
            if (
                len(query_terms) <= 2
                and not (specific_query_terms & keyword_terms)
                and keyword_similarity < 0.65
            ):
                continue
            if (
                len(query_terms) >= 4
                and len(overlap) < 2
                and keyword_similarity < 0.65
            ):
                continue
            score = sum(term_weights[term] for term in overlap) / total_query_weight
            score += 0.18 if record.source_type == "official" else 0.0
            score -= 0.12 if record.legal_status == "unknown" else 0.0
            # Imported legal datasets can contain both a chapter/index row and
            # the full provision under the same article number.  A heading-only
            # row is useful for navigation but must not outrank the legal text
            # used to answer a taxpayer.
            official_length = len(record.official_text.strip())
            if record.source_id != "curated-tax-qa":
                if official_length < 120:
                    score -= 0.45
                elif official_length >= 300:
                    score += 0.12
            if keyword_terms:
                if keyword_overlap >= 0.5 or keyword_similarity >= 0.65:
                    score += (0.45 * keyword_overlap) + (0.3 * keyword_similarity)
                if len(query_terms) <= 2 and re.match(
                    rf"^(?:مالیات\s+بر\s+)?{re.escape(normalized_question)}\s+چیست",
                    keyword_text,
                ):
                    score += 0.5
            record_article = record.article_number.translate(DIGIT_TRANSLATION).strip()
            if requested_article:
                if record_article == requested_article:
                    score += 0.9
                else:
                    continue
            score += self._legal_intent_boost(
                normalized_question,
                record.law_name,
                record_article,
            )
            hits.append(LawHit(record=record, score=score))
        return sorted(
            hits,
            key=lambda hit: (hit.score, len(hit.record.official_text.strip())),
            reverse=True,
        )[:limit]

    @staticmethod
    def _legal_intent_boost(
        question: str,
        law_name: str,
        article_number: str,
    ) -> float:
        """Route common tax intents to their governing law sections.

        This only ranks retrieved primary sources; it never manufactures a legal
        answer. Article ranges deliberately include adjacent procedural articles
        so amendments and cross references remain visible to the generator.
        """
        article_match = re.match(r"\d+", article_number)
        article = int(article_match.group()) if article_match else None
        direct_tax = "مالیات های مستقیم" in normalize_persian(law_name).replace("‌", " ")
        terminals = "پایانه های فروشگاهی" in normalize_persian(law_name).replace("‌", " ")
        vat = "ارزش افزوده" in law_name
        boost = 0.0

        if any(term in question for term in ("برگ تشخیص", "اعتراض", "ابلاغ")):
            if direct_tax and article in {219, 238, 239, 244, 247, 251}:
                boost += 0.9
            elif direct_tax:
                boost += 0.12
        if any(term in question for term in ("حقوق", "کارمند", "کارفرما", "مزایای غیرنقدی", "اضافه کاری")):
            if direct_tax and article is not None and 82 <= article <= 92:
                boost += 1.0
            elif direct_tax:
                boost += 0.15
        if any(term in question for term in ("هزینه قابل قبول", "هزینه های قابل قبول", "بدون فاکتور", "هزینه")):
            if direct_tax and article is not None and 147 <= article <= 151:
                boost += 1.0
            elif direct_tax:
                boost += 0.12
        if any(term in question for term in ("صورتحساب", "سامانه مودیان", "شناسه کالا")):
            if terminals:
                boost += 0.45
            if vat and any(term in question for term in ("اعتبار مالیاتی", "ارزش افزوده")):
                boost += 0.3
        if any(term in question for term in ("وراث", "ارث", "فوت", "متوفی", "ماترک")):
            if direct_tax and article is not None and 17 <= article <= 43:
                boost += 1.25
            elif direct_tax and article is not None:
                boost -= 0.2
        return boost

    def _law_index(self) -> list[tuple[LawRecordSnapshot, set[str], set[str], str]]:
        database_key = str(self.session.get_bind().url)
        now = time.monotonic()
        with _law_index_lock:
            cached = _law_index_cache.get(database_key)
            if cached and now - cached[0] < _law_index_ttl_seconds:
                return cached[1]
        records = (
            self.session.query(LawReferenceRecord)
            .filter(LawReferenceRecord.is_active.is_(True))
            .all()
        )
        indexed: list[tuple[LawRecordSnapshot, set[str], set[str], str]] = []
        for record in records:
            snapshot = LawRecordSnapshot(
                id=record.id,
                source_id=record.source_id,
                law_name=record.law_name,
                chapter=record.chapter,
                article_number=record.article_number,
                official_text=record.official_text,
                keywords=record.keywords,
                source_url=record.source_url,
                source_type=(
                    "practical"
                    if record.source_id == "curated-tax-qa"
                    else record.source_type
                ),
                legal_status=record.legal_status,
                fiscal_year=record.fiscal_year,
                effective_date=record.effective_date,
                expiry_date=record.expiry_date,
                last_verified_at=record.last_verified_at,
            )
            keyword_text = normalize_persian(snapshot.keywords).lower()
            keyword_terms = terms(keyword_text)
            record_terms = terms(
                f"{snapshot.law_name} {snapshot.chapter} {snapshot.article_number} "
                f"{snapshot.keywords} {snapshot.official_text}"
            )
            indexed.append((snapshot, record_terms, keyword_terms, keyword_text))
        with _law_index_lock:
            _law_index_cache[database_key] = (now, indexed)
        return indexed

    @staticmethod
    def _is_ambiguous_curated_question(question: str) -> bool:
        return bool(
            re.match(
                r"^(?:ماده|تبصره|بند)\s+.+\s+در\s+این\s+قانون\s+چه\s+حکمی",
                question,
            )
        )

    def ask(
        self,
        question: str,
        conversation_id: str | None,
        user: User,
        *,
        as_of_date: date | None = None,
        topics: list[str] | None = None,
    ) -> AskResponse:
        agent = select_agent(question)
        conversation = self._conversation(conversation_id, question, user)
        ai_question = self._question_with_memory(question, conversation, user)
        self.repository.add_message(conversation.id, "user", question)
        rules = evaluate_question(question)
        mandatory_clarification = self._requires_period_clarification(
            question, rules.clarifying_questions
        )
        policy = get_ai_policy(self.session)
        concept_answer = self._concept_answer(question)
        broad_general = self._is_broad_general_question(question)
        should_search = not (
            rules.prohibited_reason
            or (rules.casual_answer and policy.casual_chat_enabled)
            or mandatory_clarification
            or concept_answer
            or broad_general
        )
        candidate_law_hits = self.search_law_records(
            question, as_of_date=as_of_date
        ) if should_search else []
        strong_curated_match = bool(
            candidate_law_hits
            and candidate_law_hits[0].record.source_id == "curated-tax-qa"
            and candidate_law_hits[0].score >= 0.75
        )
        strong_law_match = bool(
            candidate_law_hits and candidate_law_hits[0].score >= 0.45
        )
        hits = (
            self.search(question, as_of_date=as_of_date, topics=topics)
            if should_search and not strong_curated_match and not strong_law_match
            else []
        )
        selected = [hit for hit in hits if hit.score >= 0.12][:5]
        law_hits = candidate_law_hits if should_search and not selected else []
        if law_hits:
            minimum_law_score = max(0.48, law_hits[0].score - 0.18)
            law_hits = [hit for hit in law_hits if hit.score >= minimum_law_score]
        law_citations: list[CitationResponse] = []
        source_notice = None
        if rules.prohibited_reason:
            answer = (
                "نمی‌توانم برای فرار مالیاتی، ثبت اطلاعات خلاف واقع یا دورزدن "
                "تکالیف قانونی راهنمایی عملی ارائه کنم. از مسیر قانونی اصلاح اطلاعات "
                "یا مشاوره با متخصص مالیاتی استفاده کنید."
            )
            confidence = 0.0
            answer_basis = "refusal"
        elif rules.casual_answer and policy.casual_chat_enabled:
            answer = rules.casual_answer
            confidence = 1.0
            answer_basis = "casual"
        elif rules.out_of_scope and not selected and not law_hits:
            answer = (
                "من برای موضوعات مالیاتی طراحی شده‌ام. اگر پرسش مالیاتی دارید، آن را "
                "با جزئیات بنویسید تا بر اساس بانک دانش بررسی کنم."
            )
            confidence = 0.0
            answer_basis = "out_of_scope"
        elif mandatory_clarification:
            answer = "برای پاسخ معتبر، ابتدا سال مالی یا سال عملکرد موردنظر را مشخص کنید."
            confidence = 0.0
            answer_basis = "insufficient_source"
        elif concept_answer:
            answer = concept_answer
            confidence = 0.85
            answer_basis = "general_knowledge"
        elif broad_general:
            answer = (
                self._general_fallback(question)
                or self.provider.generate_general(ai_question)
                or "لطفاً موضوع مالیاتی موردنظر را کمی دقیق‌تر بنویسید."
            )
            confidence = round(policy.general_knowledge_weight / 100, 2)
            answer_basis = "general_knowledge"
        elif selected:
            excerpts = [self._source_excerpt(hit.chunk) for hit in selected]
            generated = self.provider.generate(ai_question, excerpts)
            generated = self._attach_sentence_citations(generated, excerpts)
            provider_citations_valid = self._provider_citations_are_valid(generated, len(excerpts))
            if not provider_citations_valid:
                generated = None
            if type(self.provider).__name__ != "AvalAIProvider" and not self._answer_is_usable(generated, excerpts, question):
                generated = None
            answer = generated or self._general_fallback(question) or (
                "اطلاعات بازیابی‌شده برای یک پاسخ کامل و قابل‌اعتماد کافی نیست؛ "
                "لطفاً سؤال را دقیق‌تر بنویسید."
            )
            answer = self._attach_sentence_citations(answer, excerpts) or answer
            confidence = round(sum(hit.score for hit in selected) / len(selected), 2)
            answer_basis = "dataset"
        elif law_hits:
            if law_hits[0].record.source_id == "curated-tax-qa":
                top_score = law_hits[0].score
                curated_hits = [
                    hit
                    for hit in law_hits
                    if hit.record.source_id == "curated-tax-qa"
                    and hit.score >= top_score - 0.2
                ]
                other_hits = [
                    hit for hit in law_hits if hit.record.source_id != "curated-tax-qa"
                ]
                law_hits = curated_hits + other_hits
            diverse_law_hits: list[LawHit] = []
            seen_articles: set[str] = set()
            for hit in law_hits:
                article_key = f"{hit.record.law_name.strip()}::{hit.record.article_number.strip()}"
                if article_key and article_key in seen_articles:
                    continue
                if article_key:
                    seen_articles.add(article_key)
                diverse_law_hits.append(hit)
                if len(diverse_law_hits) == 5:
                    break
            law_hits = diverse_law_hits
            conflicting_sources = self._has_conflicting_law_sources(law_hits)
            excerpts = [
                (
                    f"{hit.record.law_name}\n{hit.record.chapter}\nماده {hit.record.article_number}\n"
                    if hit.record.article_number
                    else ""
                )
                + self._quote(hit.record.official_text)
                for hit in law_hits
            ]
            direct_answer = self._curated_answer(law_hits[0])
            if direct_answer:
                direct_answer = f"{direct_answer.rstrip()} [S1]"
            generated = None if conflicting_sources else (direct_answer or self.provider.generate(ai_question, excerpts))
            generated = self._attach_sentence_citations(generated, excerpts)
            provider_citations_valid = self._provider_citations_are_valid(generated, len(excerpts))
            if direct_answer is None and not provider_citations_valid:
                generated = None
            if type(self.provider).__name__ != "AvalAIProvider" and not self._answer_is_usable(generated, excerpts, question):
                generated = None
            answer = generated or self._general_fallback(question) or self._curated_sources_fallback(law_hits)
            answer = self._attach_sentence_citations(answer, excerpts) or answer
            if not answer and law_hits[0].score >= 0.72:
                answer = self._concise_sources(excerpts)
            if not answer:
                answer = "اطلاعات بازیابی‌شده برای پاسخ دقیق کافی نیست؛ لطفاً موضوع، نوع مؤدی و سال مالی را مشخص کنید."
            confidence = round(
                min(1.0, sum(hit.score for hit in law_hits) / len(law_hits)), 2
            )
            answer_basis = "dataset"
            if conflicting_sources:
                answer = "منابع معتبر بازیابی‌شده درباره این موضوع با یکدیگر تعارض دارند؛ پاسخ قطعی ارائه نمی‌شود و بررسی کارشناس مالیاتی لازم است."
                confidence = min(confidence, 0.25)
                source_notice = "تعارض منبع شناسایی شد؛ وضعیت اعتبار و تاریخ منابع باید بررسی شود."
            law_citations = [
                CitationResponse(
                    chunk_id=hit.record.id,
                    article_number=hit.record.article_number,
                    score=round(min(1.0, hit.score), 3),
                    source_title=hit.record.law_name.strip(),
                    source_url=hit.record.source_url or None,
                )
                for hit in law_hits
            ]
        elif policy.general_knowledge_enabled:
            generated = self._short_question_clarification(question) or self._general_fallback(question)
            if generated:
                answer = generated
                confidence = round(policy.general_knowledge_weight / 100, 2)
                answer_basis = "general_knowledge"
                source_notice = "پاسخ عمومی است؛ برای عدد، مهلت یا اقدام قطعی نیاز به بررسی تخصصی دارید."
            else:
                answer = "برای این پرسش منبع معتبر و کافی در بانک دانش پیدا نشد. لطفاً سؤال را دقیق‌تر مطرح کنید یا سند مرتبط را به بانک دانش اضافه کنید."
                confidence = 0.0
                answer_basis = "insufficient_source"
        else:
            answer = "برای این پرسش منبع معتبر و کافی در بانک دانش پیدا نشد. لطفاً سؤال را دقیق‌تر مطرح کنید یا سند مرتبط را به بانک دانش اضافه کنید."
            confidence = 0.0
            answer_basis = "insufficient_source"
        if rules.needs_expert and not rules.prohibited_reason:
            answer += "\n\nاین موضوع می‌تواند حساس یا مهلت‌دار باشد؛ بررسی کارشناس مالیاتی توصیه می‌شود."
            confidence = min(confidence, 0.6)
        if (
            rules.clarifying_questions
            and not rules.prohibited_reason
            and len(answer) < 300
        ):
            answer += "\n\nبرای پاسخ دقیق‌تر:\n" + "\n".join(
                f"- {item}" for item in rules.clarifying_questions
            )
            confidence = min(confidence, 0.5)
        answer = self._clean_legal_metadata(answer, show_article=self._asks_for_article(question))
        answer = self._plain_text_answer(answer)
        answer = self._concise(answer)
        disclaimer = "" if answer_basis == "casual" else DISCLAIMER
        assistant = self.repository.add_message(conversation.id, "assistant", answer, confidence=confidence, needs_expert=rules.needs_expert, disclaimer=disclaimer)
        citations = list(law_citations)
        for rank, hit in enumerate(hits, 1):
            is_selected = hit in selected
            self.repository.add_retrieval(assistant.id, hit.chunk, hit.score, rank, is_selected)
            if is_selected:
                quote = self._quote(hit.chunk.content)
                self.repository.add_citation(assistant.id, hit.chunk, quote, hit.score, rank)
                citations.append(CitationResponse(
                    chunk_id=hit.chunk.id,
                    article_number=hit.chunk.article_number,
                    score=round(hit.score, 3),
                    source_title=hit.chunk.version.document.title,
                    source_url=hit.chunk.version.document.source_url,
                ))
        self.repository.touch(conversation)
        self.audit.add_audit("advisor.question_answered", "conversation", actor_user_id=user.id, resource_id=conversation.id, metadata={"citations": len(citations), "needs_expert": rules.needs_expert, "escalation_reasons": rules.escalation_reasons, "refusal_reason": rules.prohibited_reason, "answer_basis": answer_basis, "general_knowledge_weight": policy.general_knowledge_weight if answer_basis == "general_knowledge" else 0})
        self.session.commit()
        return AskResponse(conversation_id=conversation.id, message_id=assistant.id, answer=answer, citations=citations, confidence=confidence, needs_expert=rules.needs_expert, disclaimer=disclaimer, clarifying_questions=rules.clarifying_questions, escalation_reasons=rules.escalation_reasons, refusal_reason=rules.prohibited_reason, answer_basis=answer_basis, source_notice=source_notice, agent=agent.code, agent_title=agent.title)

    def _question_with_memory(self, question: str, conversation: Conversation, user: User) -> str:
        profile = self.session.get(UserProfile, user.id)
        profile_parts = []
        if profile is not None:
            for label, value in (
                ("نوع مؤدی", profile.taxpayer_type),
                ("شهر", profile.city),
                ("حوزه فعالیت", profile.business_type or profile.job_title),
            ):
                if value:
                    profile_parts.append(f"{label}: {value}")
        short_history = [
            f"{message.role}: {message.content[:350]}"
            for message in conversation.messages[-6:]
        ]
        context = "\n".join((*profile_parts, *short_history))
        if not context:
            return question
        return f"زمینه کاربر و گفت‌وگو (فقط برای شخصی‌سازی؛ آن را تکرار نکن):\n{context}\n\nپرسش فعلی: {question}"

    @staticmethod
    def _requires_period_clarification(question: str, clarifications: list[str]) -> bool:
        normalized = normalize_persian(question).lower().translate(DIGIT_TRANSLATION)
        if re.search(r"\b1[34]\d{2}\b", normalized):
            return False
        time_sensitive = any(
            term in normalized
            for term in ("نرخ", "معافیت", "نصاب", "سقف", "امسال", "سال جاری")
        )
        return time_sensitive and any("سال" in item for item in clarifications)

    def _conversation(self, conversation_id: str | None, question: str, user: User) -> Conversation:
        if conversation_id is None:
            return self.repository.create_conversation(user.id, question.strip()[:80])
        item = self.repository.get_conversation(conversation_id, user.id)
        if item is None:
            raise ConversationNotFoundError
        return item

    def list_conversations(self, user: User):
        return self.repository.list_conversations(user.id)

    def get_messages(self, conversation_id: str, user: User):
        item = self.repository.get_conversation(conversation_id, user.id)
        if item is None:
            raise ConversationNotFoundError
        return item.messages

    def rename(self, conversation_id: str, title: str, user: User):
        item = self.repository.get_conversation(conversation_id, user.id)
        if item is None:
            raise ConversationNotFoundError
        item.title = title.strip()
        self.repository.touch(item)
        self.session.commit()
        return item

    def delete(self, conversation_id: str, user: User) -> None:
        item = self.repository.get_conversation(conversation_id, user.id)
        if item is None:
            raise ConversationNotFoundError
        item.deleted_at = datetime.now(timezone.utc)
        self.session.commit()

    def feedback(self, message_id: str, rating: str, comment: str, user: User) -> None:
        if self.repository.get_owned_assistant_message(message_id, user.id) is None:
            raise MessageNotFoundError
        self.repository.set_feedback(message_id, user.id, rating, comment)
        self.audit.add_audit("advisor.feedback_recorded", "chat_message", actor_user_id=user.id, resource_id=message_id, metadata={"rating": rating})
        self.session.commit()

    def list_feedback(self, rating: str | None):
        return self.repository.list_feedback(rating)

    def stats(self) -> dict[str, int]:
        return self.repository.stats()

    @staticmethod
    def _quote(content: str) -> str:
        return content.strip()[:1200]

    @staticmethod
    def _answer_is_usable(answer: str | None, sources: list[str], question: str = "") -> bool:
        if not answer or len(answer.strip()) < 20:
            return False
        normalized_answer = normalize_persian(answer).lower()
        if "…" in answer or normalized_answer.endswith((" یا", " و", " که", " به")):
            return False
        answer_terms = terms(answer)
        if not answer_terms:
            return False
        question_terms = terms(question)
        if question_terms and not (question_terms & answer_terms):
            return False
        specific_question_terms = question_terms - {"مالیات", "مالیاتی", "قانون"}
        if len(specific_question_terms) >= 3:
            coverage = len(specific_question_terms & answer_terms) / len(specific_question_terms)
            if coverage < 0.25:
                return False
        source_text = normalize_persian(" ".join(sources))
        precise_claim = re.search(
            r"(?:ماده\s*[۰-۹0-9]+|[۰-۹0-9]+\s*(?:درصد|روز|ماه|سال))",
            normalized_answer,
        )
        if precise_claim and precise_claim.group(0) not in source_text:
            return False
        return True

    def _provider_citations_are_valid(self, answer: str | None, source_count: int) -> bool:
        if type(self.provider).__name__ != "AvalAIProvider":
            return True
        if not answer:
            return False
        references = [int(value) for value in re.findall(r"\[S(\d+)\]", answer)]
        if not references or any(value < 1 or value > source_count for value in references):
            return False
        factual_markers = ("ماده", "تبصره", "نرخ", "درصد", "مهلت", "مشمول", "معاف", "موظف", "جریمه", "قانون")
        factual_sentences = [
            sentence.strip()
            for sentence in re.split(r"[.!?ØŸ\n]+", answer)
            if len(sentence.strip()) >= 24
            and (
                any(marker in sentence for marker in factual_markers)
                or any(char.isdigit() for char in sentence)
            )
        ]
        return all(re.search(r"\[S\d+\]", sentence) for sentence in factual_sentences)

    @staticmethod
    def _attach_sentence_citations(answer: str | None, sources: list[str]) -> str | None:
        if not answer or not sources:
            return answer
        source_terms = [terms(source) for source in sources]
        paragraphs: list[str] = []
        for paragraph in answer.splitlines():
            cleaned = paragraph.strip()
            if not cleaned or re.search(r"\[S\d+\]", cleaned):
                paragraphs.append(paragraph)
                continue
            paragraph_terms = terms(cleaned)
            ranked = [len(paragraph_terms & item) for item in source_terms]
            best = max(ranked, default=0)
            if best > 0:
                cleaned = f"{cleaned} [S{ranked.index(best) + 1}]"
            paragraphs.append(cleaned)
        return "\n".join(paragraphs)

    @staticmethod
    def _has_conflicting_law_sources(hits: list[LawHit]) -> bool:
        official: dict[tuple[str, str], set[str]] = {}
        for hit in hits:
            record = hit.record
            if record.source_type != "official" or record.legal_status != "valid":
                continue
            key = (normalize_persian(record.law_name).strip(), record.article_number.strip())
            text = re.sub(r"\s+", " ", normalize_persian(record.official_text)).strip()
            if key[1] and text:
                official.setdefault(key, set()).add(text)
        return any(len(texts) > 1 for texts in official.values())

    @staticmethod
    def _curated_answer(hit: LawHit) -> str | None:
        if hit.record.source_id != "curated-tax-qa" or hit.score < 0.75:
            return None
        match = re.search(r"(?:^|\n)پاسخ:\s*(.+)", hit.record.official_text, re.DOTALL)
        return match.group(1).strip() if match else None

    @classmethod
    def _curated_sources_fallback(cls, hits: list[LawHit]) -> str | None:
        answers = [
            answer
            for hit in hits
            if hit.record.source_id == "curated-tax-qa"
            and hit.score >= 0.75
            and (answer := cls._curated_answer_text(hit.record.official_text))
        ]
        return " ".join(dict.fromkeys(answers[:2])) if answers else None

    @staticmethod
    def _curated_answer_text(text: str) -> str | None:
        match = re.search(r"(?:^|\n)پاسخ:\s*(.+)", text, re.DOTALL)
        return match.group(1).strip() if match else None

    @staticmethod
    def _asks_for_article(question: str) -> bool:
        normalized = normalize_persian(question).lower().translate(DIGIT_TRANSLATION)
        patterns = (
            "چه ماده", "کدام ماده", "شماره ماده", "ماده چند",
            "مربوط به چه ماده", "طبق چه ماده",
        )
        return any(pattern in normalized for pattern in patterns) or bool(re.search(r"\bماده\s*\d+", normalized))

    @staticmethod
    def _is_broad_general_question(question: str) -> bool:
        normalized = normalize_persian(question).lower()
        compact = normalized.strip(" ؟?!،,.")
        if compact in {
            "مالیات",
            "مالیات چیست",
            "تعریف مالیات",
            "انواع مالیات",
        }:
            return True
        patterns = (
            "مالیات چند نوع",
            "چند نوع مالیات",
        )
        return any(pattern in normalized for pattern in patterns)

    @staticmethod
    def _short_question_clarification(question: str) -> str | None:
        normalized = normalize_persian(question).strip()
        if "مالیات" not in normalized or len(terms(normalized)) > 2:
            return None
        return (
            f"منظورتان از «{normalized}» دقیقاً چیست؟ لطفاً موضوع را با یک عبارت "
            "کامل‌تر بنویسید؛ مثلاً مالیات حقوق، ارزش افزوده، درآمد یا جرایم مالیاتی."
        )

    @staticmethod
    def _concept_answer(question: str) -> str | None:
        compact = normalize_persian(question).lower().strip(" ؟?!،,.")
        if AdvisorService._asks_for_article(question):
            return None
        if "شخص حقیقی" in compact and "شخص حقوقی" in compact:
            return (
                "شخص حقیقی یک فرد است که فعالیت اقتصادی را به نام خودش انجام می‌دهد؛ شخص حقوقی شرکت یا مؤسسه ثبت‌شده و مستقل از اعضای آن است. "
                "نوع اظهارنامه، نحوه نگهداری اسناد و مسئولیت‌های مالیاتی این دو با هم تفاوت دارد."
            )
        if any(term in compact for term in ("دانش‌بنیان", "دانش بنیان", "دانشبنیان")):
            if "چیست" in compact:
                return "شرکت دانش‌بنیان شرکتی است که محصول یا خدمت آن بر پایه دانش و فناوری ارزیابی و تأیید شده باشد؛ صرف ثبت شرکت یا داشتن فعالیت فنی برای این عنوان کافی نیست."
            return (
                "دانش‌بنیان بودن به‌تنهایی همه درآمد شرکت را معاف نمی‌کند. مزیت مالیاتی فقط برای فعالیت یا محصول تأییدشده، در دوره اعتبار تأیید و با رعایت تکالیف مالیاتی بررسی می‌شود."
            )
        if any(term in compact for term in ("دستگاه پوز", "کارتخوان", "کارت‌خوان")):
            return (
                "دستگاه کارت‌خوان خودش مالیات جداگانه ندارد؛ واریزی‌های آن در بررسی درآمد کسب‌وکار استفاده می‌شود. "
                "مالیات نهایی بر اساس درآمد و هزینه‌های قابل‌قبول و وضعیت پرونده مالیاتی محاسبه می‌شود."
            )
        aliases = {
            "شرکتها": "مالیات شرکت‌ها",
            "مالیات شرکتها": "مالیات شرکت‌ها",
            "مالیات شرکت ها": "مالیات شرکت‌ها",
            "جرائم مالیاتی": "جرایم مالیاتی",
            "حریم مالیاتی": "جرایم مالیاتی",
            "حریم مالیات": "جرایم مالیاتی",
        }
        key = aliases.get(compact, compact)
        answers = {
            "اظهارنامه": (
                "اظهارنامه مالیاتی گزارش رسمی مؤدی از درآمد، هزینه، دارایی، بدهی و "
                "مالیات یک دوره است که در مهلت مقرر ارسال می‌شود."
            ),
            "اظهارنامه مالیاتی": (
                "اظهارنامه مالیاتی گزارش رسمی مؤدی از درآمد، هزینه، دارایی، بدهی و "
                "مالیات یک دوره است که در مهلت مقرر ارسال می‌شود."
            ),
            "مالیات شرکت‌ها": (
                "شرکت‌ها بر درآمد مشمول مالیات خود پس از کسر هزینه‌های قابل‌قبول و "
                "معافیت‌های قانونی مالیات می‌پردازند و باید اظهارنامه، دفاتر و "
                "تکالیف صورتحساب را رعایت کنند."
            ),
            "مالیات مستقیم": (
                "مالیات مستقیم مستقیماً از درآمد یا دارایی اشخاص دریافت می‌شود؛ "
                "مانند مالیات بر درآمد، حقوق، مشاغل، شرکت‌ها و املاک."
            ),
            "مالیات غیرمستقیم": (
                "مالیات غیرمستقیم هنگام خرید یا مصرف کالا و خدمات دریافت می‌شود و "
                "معمولاً پرداخت‌کننده نهایی آن مصرف‌کننده است؛ مانند ارزش افزوده."
            ),
            "جرایم مالیاتی": (
                "جرایم مالیاتی پیامد انجام‌ندادن یا تأخیر در تکالیفی مانند ارسال "
                "اظهارنامه، پرداخت مالیات یا ثبت صورتحساب است. مبلغ و امکان بخشودگی "
                "به نوع تخلف و دوره مربوط بستگی دارد."
            ),
            "اعتراض مالیاتی": (
                "اعتراض مالیاتی درخواست رسمی مؤدی برای بازبینی برگ یا رأی مالیاتی "
                "است و باید در مهلت مقرر همراه دلایل و مدارک ثبت شود."
            ),
        }
        return answers.get(key)

    @staticmethod
    def _clean_legal_metadata(text: str, *, show_article: bool) -> str:
        cleaned = re.sub(r"\[\s*اصلاحی[^\]]*\]\s*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\(\s*اصلاحی[^)]*\)\s*", "", cleaned, flags=re.IGNORECASE)
        if not show_article:
            cleaned = re.sub(r"(?m)^\s*ماده\s*[\(\[]?\s*[۰-۹0-9]+\s*[\)\]]?\s*[-–—:]\s*", "", cleaned)
            cleaned = re.sub(r"\b(?:موضوع|طبق|بر اساس)\s+ماده\s*[\(\[]?\s*[۰-۹0-9]+\s*[\)\]]?", "", cleaned)
        return re.sub(r"[ \t]{2,}", " ", cleaned).strip()

    @staticmethod
    def _plain_text_answer(text: str) -> str:
        """Remove presentation markup while preserving readable Persian text."""
        cleaned = text.replace("\r\n", "\n")
        cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
        cleaned = re.sub(r"(?m)^\s*[-*+]\s+", "", cleaned)
        cleaned = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", cleaned)
        cleaned = re.sub(r"_{1,3}([^_\n]+)_{1,3}", r"\1", cleaned)
        cleaned = re.sub(r"`{1,3}([^`\n]+)`{1,3}", r"\1", cleaned)
        cleaned = re.sub(r"(?m)^\s*>\s?", "", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _concise(text: str, max_chars: int = 2400) -> str:
        cleaned = re.sub(r"[ \t]+", " ", text).strip()
        if len(cleaned) <= max_chars:
            return cleaned
        shortened = cleaned[:max_chars].rsplit(" ", 1)[0].rstrip("،؛:.-")
        return shortened + "…"

    @classmethod
    def _concise_sources(cls, sources: list[str]) -> str:
        summaries = []
        for source in sources[:2]:
            lines = source.splitlines()
            # Law excerpts have three metadata lines (law, chapter, article)
            # before the quoted provision.  Do not accidentally summarize
            # those headings as though they were the legal answer.
            if len(lines) >= 4 and lines[2].strip().startswith("ماده"):
                body = "\n".join(lines[3:]).strip()
            else:
                body = source.split("\n", 1)[-1]
            sentences = [part.strip() for part in re.split(r"(?<=[.!؟])\s+|\n+", body) if part.strip()]
            summary = " ".join(sentences[:2])
            summaries.append(f"{cls._concise(summary, 280)} [S{len(summaries) + 1}]")
        return "\n\n".join(summaries)

    @classmethod
    def _source_excerpt(cls, chunk: DocumentChunk) -> str:
        prefix = f"ماده {chunk.article_number}\n" if chunk.article_number else ""
        return prefix + cls._quote(chunk.content)

    @staticmethod
    def _general_fallback(question: str) -> str | None:
        normalized = normalize_persian(question).lower()
        if normalized.strip(" ؟?!،,.") == "مالیات":
            return (
                "مالیات مبلغی قانونی است که اشخاص و کسب‌وکارها بر اساس درآمد، "
                "دارایی یا مصرف پرداخت می‌کنند. اگر نوع خاصی مدنظر دارید، مانند "
                "حقوق، ارزش افزوده یا ارث، نام آن را بنویسید."
            )
        if (
            any(term in normalized for term in ("واریزی", "واریز", "حساب تجاری"))
            and any(term in normalized for term in ("قرض", "انتقال", "برگشت وجه"))
            and any(term in normalized for term in ("مدرک", "مدارک", "اثبات"))
        ):
            return (
                "برای تفکیک این مبالغ، رسید انتقال بین حساب‌های خود شخص، قرارداد یا "
                "رسید قرض و مسیر بازپرداخت، و برای برگشت وجه نیز فاکتور اولیه، سند "
                "ابطال یا اصلاح و رسید بازپرداخت را نگه دارید. ثبت حسابداری، گردش "
                "بانکی و مکاتبات طرفین باید تاریخ و مبلغ یکسان داشته باشند."
            )
        if "مالیات" in normalized and "چند نوع" in normalized:
            return (
                "مالیات به‌طور کلی دو نوع اصلی دارد: مالیات مستقیم، مانند مالیات بر درآمد "
                "و دارایی؛ و مالیات غیرمستقیم، مانند مالیات بر ارزش افزوده. هرکدام "
                "زیرمجموعه‌ها و تکالیف جداگانه‌ای دارند."
            )
        if "ارث" in normalized and any(term in normalized for term in ("وقف", "وصیت", "نذر", "حبس")):
            return (
                "در امور ارث، پیگیری و ارائه اطلاعات لازم بر عهده وراث یا نماینده قانونی آن‌هاست "
                "و مهلت اقدام یک سال از تاریخ فوت است. در وقف، حبس، نذر و وصیت، مسئولیت با متولی، "
                "ایجادکننده یا وصی است و مهلت ارائه اظهارنامه سه ماه از وقوع عقد یا فوت موصی است."
            )
        responses = {
            "اظهارنامه": "اظهارنامه مالیاتی گزارش دوره‌ای مؤدی از درآمد، هزینه و اطلاعات مالی است. نوع اظهارنامه و مهلت ارسال به نوع مؤدی و دوره مالی بستگی دارد؛ برای اقدام نهایی، سال و نوع فعالیت را مشخص کنید.",
            "ارزش افزوده": "مالیات بر ارزش افزوده در زنجیره عرضه کالا و خدمات محاسبه می‌شود. تکالیف ثبت صورتحساب، گزارش دوره و پرداخت به نوع فعالیت و وضعیت مؤدی بستگی دارد.",
            "سامانه مودیان": "سامانه مؤدیان برای ثبت و تبادل صورتحساب‌های الکترونیکی و انجام بخشی از تکالیف مالیاتی استفاده می‌شود. وضعیت عضویت، حافظه مالیاتی و نوع صورتحساب باید متناسب با کسب‌وکار بررسی شود.",
            "سامانه مؤدیان": "سامانه مؤدیان برای ثبت و تبادل صورتحساب‌های الکترونیکی و انجام بخشی از تکالیف مالیاتی استفاده می‌شود. وضعیت عضویت، حافظه مالیاتی و نوع صورتحساب باید متناسب با کسب‌وکار بررسی شود.",
            "کد اقتصادی": "کد اقتصادی شناسه فعالیت مالیاتی اشخاص و کسب‌وکارهاست و برای شناسایی مؤدی، پرونده مالیاتی و برخی معاملات استفاده می‌شود.",
            "صورتحساب": "نقص یا عدم ثبت صورتحساب الکترونیکی می‌تواند باعث جریمه، رد اعتبار مالیاتی یا افزایش ریسک رسیدگی شود. نوع خطا و امکان اصلاح آن باید در کارپوشه مؤدی بررسی شود.",
            "جریمه": "نوع جریمه به تکلیف انجام‌نشده و دوره مربوط بستگی دارد. پیش از محاسبه باید مشخص شود تخلف مربوط به اظهارنامه، پرداخت یا صورتحساب بوده است.",
            "جرایم": "نوع جریمه به تکلیف انجام‌نشده و دوره مربوط بستگی دارد. پیش از محاسبه باید مشخص شود تخلف مربوط به اظهارنامه، پرداخت یا صورتحساب بوده است.",
            "جرائم": "نوع جریمه به تکلیف انجام‌نشده و دوره مربوط بستگی دارد. پیش از محاسبه باید مشخص شود تخلف مربوط به اظهارنامه، پرداخت یا صورتحساب بوده است.",
            "بخشودگی": "بخشودگی خودکار نیست و معمولاً به نوع جریمه، انجام تکالیف عقب‌افتاده، پرداخت بدهی و شرایط اعلام‌شده برای همان دوره بستگی دارد.",
            "اعتراض": "برای اعتراض مالیاتی ابتدا نوع ابلاغ، تاریخ ابلاغ و مرحله رسیدگی را مشخص کنید. متن اعتراض باید مستند، روشن و همراه با مدارک مرتبط تنظیم شود.",
        }
        matches: list[str] = []
        if "اظهارنامه" in normalized and any(
            keyword in normalized for keyword in ("دیر", "تاخیر", "تأخیر")
        ):
            matches.append(
                "ارسال دیرهنگام اظهارنامه می‌تواند جریمه و آثار مرتبط با عدم انجام "
                "تکلیف در موعد مقرر داشته باشد؛ نوع اظهارنامه و دوره باید مشخص شود."
            )
        priority = (
            "صورتحساب", "بخشودگی", "جریمه", "جرایم", "جرائم", "اعتراض",
            "اظهارنامه", "ارزش افزوده", "سامانه مؤدیان", "سامانه مودیان",
            "کد اقتصادی",
        )
        matches.extend(
            responses[keyword]
            for keyword in priority
            if keyword in normalized
        )
        unique_matches = list(dict.fromkeys(matches))
        if len(unique_matches) > 1:
            return " ".join(unique_matches[:3])
        if unique_matches:
            return unique_matches[0]
        return None
