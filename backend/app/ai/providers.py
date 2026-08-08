from __future__ import annotations

import json
import hashlib
import base64
import http.client
import logging
import math
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings

logger = logging.getLogger(__name__)
_response_cache: OrderedDict[str, dict] = OrderedDict()
_response_cache_lock = threading.Lock()
_response_cache_limit = 512
_provider_blocked_until: dict[str, float] = {}
_provider_block_lock = threading.Lock()


class GeneratedAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=6000)


class AnswerProvider(Protocol):
    def generate(self, question: str, sources: list[str]) -> str | None: ...

    def generate_general(self, question: str) -> str | None: ...


class EmbeddingProvider(Protocol):
    model_name: str | None

    def embed_query(self, text: str) -> list[float] | None: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]] | None: ...


class DisabledAIProvider:
    model_name = None

    def generate(self, question: str, sources: list[str]) -> None:
        return None

    def generate_general(self, question: str) -> None:
        return None

    def embed_query(self, text: str) -> None:
        return None

    def embed_documents(self, texts: list[str]) -> None:
        return None

    def extract_document_text(self, data: bytes, mime_type: str) -> None:
        return None


@dataclass(frozen=True)
class GeminiProvider:
    api_key: str
    base_url: str
    generation_model: str
    general_model: str
    advanced_model: str
    embedding_model: str
    timeout_seconds: float
    embedding_dimensions: int

    @property
    def model_name(self) -> str:
        return self.embedding_model

    def generate(self, question: str, sources: list[str]) -> str | None:
        source_text = "\n\n".join(
            f"[متن تأییدشده {index}]\n{source}" for index, source in enumerate(sources, 1)
        )
        prompt = (
            "به پرسش فارسی ابتدا بر اساس اطلاعات زیر پاسخ بده و مستقیماً همان چیزی را که کاربر "
            "پرسیده توضیح بده. متن‌ها را عیناً تکرار نکن و آن‌ها را به زبان ساده جمع‌بندی کن. "
            "اگر سؤال مقایسه‌ای است، تفاوت هر مورد را جدا و روشن بیان کن. اگر اطلاعات برای یک توضیح کامل "
            "و قابل‌فهم کافی نبود، فقط بخش مفهومی و کم‌ریسک پاسخ را با دانش عمومی خودت تکمیل کن. "
            "هیچ ماده، مبلغ، نرخ، مهلت، تاریخ یا حکم قطعی را حدس نزن و اگر چنین جزئیاتی در اطلاعات "
            "زیر وجود ندارد، کوتاه بگو نیازمند بررسی دقیق‌تر است. نام منبع، عنوان سند، لینک، شماره "
            "تاریخ تصویب و تاریخ اصلاحیه را در پاسخ نیاور. شماره ماده را هم نیاور، مگر اینکه خود "
            "کاربر صریحاً پرسیده باشد پاسخ مربوط به چه ماده یا شماره ماده‌ای است. فقط نتیجه کاربردی را با زبان خیلی "
            "ساده و حداکثر در سه جمله کوتاه بنویس.\n\n"
            f"پرسش: {question}\n\n{source_text}"
        )
        payload = {
            "system_instruction": {
                "parts": [{"text": "شما دستیار اطلاع‌رسانی مالیاتی مبتنی بر منبع هستید، نه مشاور قطعی."}]
            },
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 240,
                "responseMimeType": "application/json",
                "responseJsonSchema": GeneratedAnswer.model_json_schema(),
            },
        }
        models = (
            [self.advanced_model, self.generation_model, self.general_model]
            if self._is_complex(question)
            else [self.general_model, self.generation_model, self.advanced_model]
        )
        return self._generate(payload, models)

    def generate_general(self, question: str) -> str | None:
        prompt = (
            "به پرسش فارسی فقط در حد آموزش عمومی مالیاتی پاسخ بده. از ساختن یا "
            "حدس‌زدن ماده قانونی، نرخ، مبلغ، مهلت، تاریخ یا حکم جاری خودداری کن. "
            "هیچ نام منبع، عنوان سند، نام کتاب یا لینکی در پاسخ نیاور. "
            "اگر پاسخ به اطلاعات دقیق یا مقررات روز نیاز دارد، صریحاً بگو باید منبع "
            "رسمی یا کارشناس بررسی کند. پاسخ را ساده و حداکثر در سه جمله کوتاه بنویس.\n\n"
            f"پرسش: {question}"
        )
        payload = {
            "system_instruction": {
                "parts": [{"text": "شما دستیار آموزش عمومی مالیاتی ایران هستید و پاسخ شما منبع حقوقی قطعی نیست."}]
            },
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 200,
                "responseMimeType": "application/json",
                "responseJsonSchema": GeneratedAnswer.model_json_schema(),
            },
        }
        return self._generate(payload, [self.general_model, self.generation_model, self.advanced_model])

    def _generate(self, payload: dict, models: list[str]) -> str | None:
        primary_models = list(dict.fromkeys(models))[:1]
        for model in primary_models:
            data = self._request(f"models/{model}:generateContent", payload)
            if data.get("_provider_error_status") in {401, 402, 403, 429}:
                break
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                try:
                    return GeneratedAnswer.model_validate_json(text).answer.strip()
                except (ValidationError, json.JSONDecodeError):
                    cleaned = str(text).strip()
                    if cleaned:
                        return cleaned[:6000]
            except (KeyError, IndexError, TypeError):
                logger.warning("gemini_invalid_generation_response", extra={"model": model})
        return None

    @staticmethod
    def _is_complex(question: str) -> bool:
        normalized = " ".join(question.split()).lower()
        markers = ("تحلیل", "مقایسه", "ریسک", "اعتراض", "لایحه", "اظهارنامه", "جرائم", "سناریو", "راهکار", "دفاتر", "صورت مالی", "پرونده")
        return len(normalized) >= 220 or sum(marker in normalized for marker in markers) >= 2

    def embed_query(self, text: str) -> list[float] | None:
        return self._embed_one(text, "RETRIEVAL_QUERY")

    def embed_documents(self, texts: list[str]) -> list[list[float]] | None:
        vectors: list[list[float]] = []
        for text in texts:
            vector = self._embed_one(text, "RETRIEVAL_DOCUMENT")
            if vector is None:
                return None
            vectors.append(vector)
        return vectors

    def extract_document_text(self, data: bytes, mime_type: str) -> str | None:
        payload = {
            "system_instruction": {"parts": [{"text": "متن سند را دقیق استخراج کن و هیچ اطلاعاتی حدس نزن."}]},
            "contents": [{"role": "user", "parts": [
                {"text": "تمام متن خوانای این سند را با حفظ ترتیب سطرها استخراج کن."},
                {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(data).decode("ascii")}},
            ]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 3000,
                "responseMimeType": "application/json",
                "responseJsonSchema": GeneratedAnswer.model_json_schema(),
            },
        }
        return self._generate(payload, [self.general_model, self.generation_model])

    def _embed_one(self, text: str, task_type: str) -> list[float] | None:
        payload = {
            "model": f"models/{self.embedding_model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": self.embedding_dimensions,
        }
        data = self._request(
            f"models/{self.embedding_model}:embedContent", payload
        )
        try:
            values = [float(value) for value in data["embedding"]["values"]]
            return normalize_vector(values)
        except (KeyError, TypeError, ValueError):
            logger.warning("gemini_invalid_embedding_response")
            return None

    def _request(self, endpoint: str, payload: dict) -> dict:
        circuit_key = hashlib.sha256(
            f"{self.base_url}\0{self.api_key}".encode("utf-8")
        ).hexdigest()
        with _provider_block_lock:
            if time.monotonic() < _provider_blocked_until.get(circuit_key, 0.0):
                return {"_provider_error_status": 429, "_circuit_open": True}
        encoded_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        cache_key = hashlib.sha256(endpoint.encode("utf-8") + b"\0" + encoded_payload).hexdigest()
        with _response_cache_lock:
            cached = _response_cache.get(cache_key)
            if cached is not None:
                _response_cache.move_to_end(cache_key)
                return cached
        request = urllib.request.Request(
            f"{self.base_url}/{endpoint}",
            data=encoded_payload,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
                with _response_cache_lock:
                    _response_cache[cache_key] = result
                    _response_cache.move_to_end(cache_key)
                    while len(_response_cache) > _response_cache_limit:
                        _response_cache.popitem(last=False)
                return result
        except urllib.error.HTTPError as error:
            if error.code in {401, 402, 403, 429}:
                with _provider_block_lock:
                    _provider_blocked_until[circuit_key] = time.monotonic() + (300 if error.code == 429 else 60)
            logger.warning("gemini_request_failed", extra={"error_type": type(error).__name__, "status": error.code})
            return {"_provider_error_status": error.code}
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            http.client.HTTPException,
            json.JSONDecodeError,
        ) as error:
            logger.warning("gemini_request_failed", extra={"error_type": type(error).__name__})
            return {}


def normalize_vector(values: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        return values
    return [value / magnitude for value in values]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def create_ai_provider(settings: Settings) -> DisabledAIProvider | GeminiProvider:
    if settings.ai_provider != "gemini" or not settings.gemini_api_key:
        return DisabledAIProvider()
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        base_url=settings.gemini_base_url,
        generation_model=settings.gemini_generation_model,
        general_model=settings.gemini_general_model,
        advanced_model=settings.gemini_advanced_model,
        embedding_model=settings.gemini_embedding_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        embedding_dimensions=settings.embedding_dimensions,
    )
