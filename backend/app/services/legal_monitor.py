from __future__ import annotations

import hashlib
import html
import re
import urllib.error
import urllib.parse
import urllib.request
import ipaddress
import socket
from datetime import datetime, timezone

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.portal import LegalExternalSource, LegalUpdateCandidate


USER_AGENT = "ChakaLegalMonitor/1.0"
MAX_SOURCE_BYTES = 12 * 1024 * 1024


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_public_source_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTPS legal sources are allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as error:
        raise ValueError("Legal source hostname cannot be resolved") from error
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Private or reserved legal source addresses are blocked")


def fetch_bytes(url: str, timeout: float = 30.0) -> bytes:
    opener = urllib.request.build_opener(_NoRedirect)
    current = url
    for _ in range(4):
        validate_public_source_url(current)
        request = urllib.request.Request(current, headers={"User-Agent": USER_AGENT})
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code not in {301, 302, 303, 307, 308}:
                raise
            location = error.headers.get("Location")
            if not location:
                raise ValueError("Invalid legal source redirect") from error
            current = urllib.parse.urljoin(current, location)
            continue
        with response:
            length = int(response.headers.get("Content-Length") or 0)
            if length > MAX_SOURCE_BYTES:
                raise ValueError("Legal source is too large")
            data = response.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise ValueError("Legal source is too large")
            return data
    raise ValueError("Too many legal source redirects")


def clean_title(page: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    title = html.unescape(re.sub(r"<[^>]+>", " ", match.group(1) if match else ""))
    return re.sub(r"\s+", " ", title).strip()[:300] or "به‌روزرسانی منبع قانونی"


def pdf_url(page_url: str, page: str) -> str | None:
    match = re.search(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', page, re.I)
    return urllib.parse.urljoin(page_url, html.unescape(match.group(1))) if match else None


def extract_pdf_text(data: bytes) -> str:
    document = fitz.open(stream=data, filetype="pdf")
    text = "\n".join(page.get_text("text") for page in document)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_visible_text(page: str) -> str:
    visible = re.sub(r"<script\b.*?</script>", " ", page, flags=re.I | re.S)
    visible = re.sub(r"<style\b.*?</style>", " ", visible, flags=re.I | re.S)
    visible = re.sub(r"<[^>]+>", "\n", visible)
    visible = html.unescape(visible)
    lines = [re.sub(r"\s+", " ", line).strip() for line in visible.splitlines()]
    ignored = {"صفحه اصلی", "لیست قوانین", "لیست مقررات", "لیست آرا", "لیست نظرات"}
    visible_text = "\n".join(line for line in lines if len(line) > 2 and line not in ignored)
    if len(visible_text) >= 1000:
        return visible_text
    snippets: list[str] = []
    seen: set[str] = set()
    for match in re.findall(r'["\'`](.*?[\u0600-\u06ff].*?)["\'`]', page, re.S):
        cleaned = html.unescape(re.sub(r"<[^>]+>", " ", match))
        cleaned = re.sub(r"\\u[0-9a-fA-F]{4}|\\[nrt]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) < 30 or cleaned in seen:
            continue
        if any(marker in cleaned for marker in ("function(", "onclick=", "class=", "${")):
            continue
        seen.add(cleaned)
        snippets.append(cleaned)
    return "\n".join([visible_text, *snippets])


def source_snapshot(source: LegalExternalSource) -> tuple[str, str, str]:
    page_bytes = fetch_bytes(source.base_url)
    page = page_bytes.decode("utf-8", errors="replace")
    title = clean_title(page)
    attachment = pdf_url(source.base_url, page)
    if attachment:
        content = extract_pdf_text(fetch_bytes(attachment))
        if len(content) < 100:
            content = extract_visible_text(page)
    else:
        content = extract_visible_text(page)
    if len(content) < 100:
        raise ValueError("متن قابل‌استفاده‌ای از منبع استخراج نشد")
    digest = hashlib.sha256(
        (title + "\n" + content).encode("utf-8")
    ).hexdigest()
    return title, content, digest


def check_source(session: Session, source: LegalExternalSource) -> dict[str, object]:
    source.last_checked_at = datetime.now(timezone.utc)
    try:
        title, content, digest = source_snapshot(source)
        changed = bool(source.content_hash and source.content_hash != digest)
        candidate_id = None
        if changed:
            pending = session.scalar(
                select(LegalUpdateCandidate).where(
                    LegalUpdateCandidate.source_id == source.id,
                    LegalUpdateCandidate.status == "pending",
                )
            )
            if pending is None:
                candidate = LegalUpdateCandidate(
                    source_id=source.id,
                    title=title,
                    proposed_text=content,
                    source_url=source.base_url,
                )
                session.add(candidate)
                session.flush()
                candidate_id = candidate.id
        source.content_hash = digest
        source.last_title = title
        source.last_content_length = len(content)
        source.last_status = "change_detected" if changed else "up_to_date"
        source.last_error = ""
        session.commit()
        return {
            "source_id": source.id,
            "status": source.last_status,
            "changed": changed,
            "candidate_id": candidate_id,
            "content_length": len(content),
        }
    except (urllib.error.URLError, TimeoutError, ValueError, fitz.FileDataError) as error:
        source.last_status = "failed"
        source.last_error = str(error)[:2000]
        session.commit()
        return {"source_id": source.id, "status": "failed", "error": source.last_error}


def check_all_sources(session: Session) -> list[dict[str, object]]:
    sources = session.scalars(
        select(LegalExternalSource)
        .where(LegalExternalSource.is_enabled.is_(True))
        .order_by(LegalExternalSource.created_at)
    ).all()
    return [check_source(session, source) for source in sources]
