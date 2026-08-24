from __future__ import annotations

import hashlib
import io
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Protocol

import fitz
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.financial_statements import (
    AccountMappingDecision, AccountMappingRule, FinancialStatementField,
    FinancialStatementImport, FinancialStatementImportRow, FinancialStatementRun,
    FinancialStatementValidation, FinancialStatementValue,
    FinancialStatementValueSource, utc_now,
)

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
ALLOWED_UNITS = {
    "rial": Decimal(1),
    "toman": Decimal(10),
}
HEADER_ALIASES = {
    "general": ("کل", "حساب کل"), "subsidiary": ("معین", "حساب معین"),
    "detail": ("تفصیلی", "تفضیلی", "حساب تفصیلی", "حساب تفضیلی"),
    "opening_debit": ("بدهکار اول دوره", "افتتاحیه بدهکار"),
    "opening_credit": ("بستانکار اول دوره", "افتتاحیه بستانکار"),
    "period_debit": ("بدهکار طی دوره", "گردش بدهکار", "بدهکار دوره"),
    "period_credit": ("بستانکار طی دوره", "گردش بستانکار", "بستانکار دوره"),
    "closing_debit": ("مانده بدهکار", "بدهکار پایان دوره"),
    "closing_credit": ("مانده بستانکار", "بستانکار پایان دوره"),
}
HEADER_ALIASES["opening_debit"] += ("بد اول دوره",)
HEADER_ALIASES["opening_credit"] += ("بس اول دوره",)
HEADER_ALIASES["period_debit"] += ("بد طی دوره",)
HEADER_ALIASES["period_credit"] += ("بس طی دوره",)
HEADER_ALIASES["closing_debit"] += ("مانده بد",)
HEADER_ALIASES["closing_credit"] += ("مانده بس",)


def normalize_persian_financial(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.translate(PERSIAN_DIGITS).replace("ي", "ی").replace("ك", "ک")
    text = text.replace("ـ", "")
    text = text.replace("ۀ", "ه").replace("ة", "ه")
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", text)
    text = text.replace("‌", " ").replace("٬", ",")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalized_account_name(value: object) -> str:
    text = normalize_persian_financial(value).lower()
    text = re.sub(r"\b(?:ریال|تومان)\b", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_amount(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal(0)
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = normalize_persian_financial(value).replace(",", "").replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = re.sub(r"(?:ریال|تومان)$", "", text)
    try:
        number = Decimal(text or "0")
    except InvalidOperation as exc:
        raise ValueError("invalid_amount") from exc
    return -number if negative else number


def extract_account(value: object) -> tuple[str, str]:
    text = normalize_persian_financial(value)
    match = re.match(r"^\s*(\d+)\s*[-–—:]?\s*(.*)$", text)
    return (match.group(1), match.group(2).strip()) if match else ("", text)


@dataclass(frozen=True)
class ParsedAccountRow:
    general_code: str = ""; general_name: str = ""
    subsidiary_code: str = ""; subsidiary_name: str = ""
    detail_code: str = ""; detail_name: str = ""
    opening_debit: Decimal = Decimal(0); opening_credit: Decimal = Decimal(0)
    period_debit: Decimal = Decimal(0); period_credit: Decimal = Decimal(0)
    closing_debit: Decimal = Decimal(0); closing_credit: Decimal = Decimal(0)
    source_row_number: int = 0


class ITrialBalanceParser(Protocol):
    def parse(self, data: bytes) -> list[ParsedAccountRow]: ...


class IDocumentOcrService(Protocol):
    def extract(self, data: bytes) -> tuple[str, float]: ...


class DisabledDocumentOcrService:
    def extract(self, data: bytes) -> tuple[str, float]:
        return "", 0.0


def _header_map(rows: list[list[object]]) -> tuple[int, dict[str, int]]:
    best: tuple[int, dict[str, int]] = (-1, {})
    for row_index, row in enumerate(rows[:30]):
        found: dict[str, int] = {}
        for index, cell in enumerate(row):
            name = normalized_account_name(cell)
            for key, aliases in HEADER_ALIASES.items():
                if any(normalized_account_name(alias) in name for alias in aliases):
                    found.setdefault(key, index)
        if len(found) > len(best[1]):
            best = row_index, found
    if best[0] < 0 or not any(key in best[1] for key in ("general", "subsidiary", "detail")):
        raise ValueError("header_not_found")
    return best


def _rows_from_matrix(matrix: list[list[object]]) -> list[ParsedAccountRow]:
    header_index, columns = _header_map(matrix)
    result: list[ParsedAccountRow] = []
    context = {"general": ("", ""), "subsidiary": ("", "")}
    for source_index, row in enumerate(matrix[header_index + 1:], header_index + 2):
        def cell(key: str):
            index = columns.get(key)
            return row[index] if index is not None and index < len(row) else None
        general = extract_account(cell("general")); subsidiary = extract_account(cell("subsidiary")); detail = extract_account(cell("detail"))
        if (
            normalized_account_name(general[1]) in {"کل", "حساب کل"}
            and "معین" in normalized_account_name(subsidiary[1])
        ):
            continue
        if general != ("", ""): context["general"] = general
        if subsidiary != ("", ""): context["subsidiary"] = subsidiary
        if not any((general[0], subsidiary[0], detail[0], general[1], subsidiary[1], detail[1])):
            continue
        amounts = {key: parse_amount(cell(key)) for key in ("opening_debit", "opening_credit", "period_debit", "period_credit", "closing_debit", "closing_credit")}
        if "closing_credit" not in columns or "closing_debit" not in columns:
            net = amounts["opening_debit"] - amounts["opening_credit"] + amounts["period_debit"] - amounts["period_credit"]
            amounts["closing_debit"] = max(net, Decimal(0))
            amounts["closing_credit"] = max(-net, Decimal(0))
        if not any(amounts.values()) and not any((detail[0], detail[1])):
            continue
        result.append(ParsedAccountRow(*context["general"], *context["subsidiary"], *detail, **amounts, source_row_number=source_index))
    if not result:
        raise ValueError("no_accounts_found")
    return result


class ExcelTrialBalanceParser:
    def parse(self, data: bytes) -> list[ParsedAccountRow]:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True, keep_links=False)
        matrices = [[list(row) for row in sheet.iter_rows(values_only=True)] for sheet in workbook.worksheets]
        candidates = []
        for matrix in matrices:
            try: candidates.append(_rows_from_matrix(matrix))
            except ValueError: continue
        if not candidates: raise ValueError("header_not_found")
        return max(candidates, key=len)


class LegacyExcelTrialBalanceParser:
    def parse(self, data: bytes) -> list[ParsedAccountRow]:
        if data.lstrip().startswith(b"<?xml"):
            return self._parse_spreadsheet_xml(data)
        try:
            import xlrd
            workbook = xlrd.open_workbook(file_contents=data, on_demand=True)
        except Exception as exc:
            raise ValueError("corrupted_excel") from exc
        candidates = []
        for sheet in workbook.sheets():
            matrix = [[sheet.cell_value(row, column) for column in range(sheet.ncols)] for row in range(sheet.nrows)]
            try: candidates.append(_rows_from_matrix(matrix))
            except ValueError: continue
        if not candidates: raise ValueError("header_not_found")
        return max(candidates, key=len)

    @staticmethod
    def _parse_spreadsheet_xml(data: bytes) -> list[ParsedAccountRow]:
        try:
            root = ET.fromstring(data)
        except ET.ParseError as exc:
            raise ValueError("corrupted_excel") from exc
        namespace = "urn:schemas-microsoft-com:office:spreadsheet"
        ss = f"{{{namespace}}}"
        candidates: list[list[ParsedAccountRow]] = []
        for worksheet in root.findall(f"{ss}Worksheet"):
            matrix: list[list[object]] = []
            table = worksheet.find(f"{ss}Table")
            if table is None:
                continue
            for row in table.findall(f"{ss}Row"):
                values: list[object] = []
                position = 1
                for cell in row.findall(f"{ss}Cell"):
                    index = cell.get(f"{ss}Index")
                    if index:
                        position = int(index)
                    while len(values) < position - 1:
                        values.append(None)
                    value = cell.find(f"{ss}Data")
                    values.append("" if value is None else "".join(value.itertext()).strip())
                    merge = int(cell.get(f"{ss}MergeAcross", "0"))
                    values.extend([None] * merge)
                    position += merge + 1
                matrix.append(values)
            try:
                candidates.append(_rows_from_matrix(matrix))
            except ValueError:
                continue
        if not candidates:
            raise ValueError("header_not_found")
        return max(candidates, key=len)


class PdfTrialBalanceParser:
    def __init__(self, ocr: IDocumentOcrService | None = None): self.ocr = ocr or DisabledDocumentOcrService()
    def parse(self, data: bytes) -> list[ParsedAccountRow]:
        document = fitz.open(stream=data, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in document)
        if len(text.strip()) < 80:
            text, confidence = self.ocr.extract(data)
            if confidence < 0.85: raise ValueError("ocr_needs_review")
        # PDF layouts are variable; only accept rows with six explicit numeric columns.
        matrix = [re.split(r"\s{2,}|\t", line.strip()) for line in text.splitlines() if line.strip()]
        return _rows_from_matrix(matrix)


class AccountMappingService:
    def __init__(self, session: Session): self.session = session

    def apply(self, import_: FinancialStatementImport) -> dict[str, int]:
        rules = list(self.session.scalars(select(AccountMappingRule).where(AccountMappingRule.is_active.is_(True), (AccountMappingRule.organization_id == import_.organization_id) | (AccountMappingRule.organization_id.is_(None))).order_by(AccountMappingRule.organization_id.desc(), AccountMappingRule.priority.desc())))
        counts = {"mapped": 0, "needs_review": 0, "unmapped": 0}
        for row in import_.rows:
            matches = []
            for level, code, name in self._identities(row):
                match, confidence = self._match(rules, import_.organization_id, level, code, name)
                matches.append((match, confidence))
            match, confidence = max(matches, key=lambda item: item[1])
            fallback = self._fallback(row.general_code)
            if fallback:
                # Standard chart-of-account codes are authoritative. This also
                # prevents a stale, overly broad user rule from remapping every
                # account in a later import.
                match = None
                target_field_id, sign_multiplier = fallback
                amount_source = "net_closing"
                confidence = 95
            else:
                target_field_id = match.target_field_id if match else None
                amount_source = match.amount_source if match else "net_closing"
                sign_multiplier = match.sign_multiplier if match else 1
            status = "mapped" if confidence >= 90 else "needs_review" if confidence >= 70 else "unmapped"
            decision = self.session.scalar(select(AccountMappingDecision).where(AccountMappingDecision.import_row_id == row.id)) or AccountMappingDecision(import_row_id=row.id)
            decision.rule_id = match.id if match else None; decision.target_field_id = target_field_id
            decision.amount_source = amount_source; decision.sign_multiplier = sign_multiplier
            decision.confidence = confidence; decision.status = status
            self.session.add(decision); counts[status] += 1
        import_.status = "ready_to_calculate" if counts["unmapped"] == 0 and counts["needs_review"] == 0 else "mapping_required"
        return counts

    @staticmethod
    def _identity(row):
        if row.detail_code or row.detail_name: return "detailed", row.detail_code, row.detail_name
        if row.subsidiary_code or row.subsidiary_name: return "subsidiary", row.subsidiary_code, row.subsidiary_name
        return "general", row.general_code, row.general_name

    @staticmethod
    def _identities(row):
        return (
            ("detailed", row.detail_code, row.detail_name),
            ("subsidiary", row.subsidiary_code, row.subsidiary_name),
            ("general", row.general_code, row.general_name),
        )

    @staticmethod
    def _fallback(code: str) -> tuple[str, int] | None:
        mappings = (
            ("1110", "BS.CASH", 1),
            ("1111", "BS.SHORT_TERM_INVESTMENTS", 1),
            ("1112", "BS.TRADE_RECEIVABLES", 1),
            ("1113", "BS.TRADE_RECEIVABLES", 1),
            ("1114", "BS.INVENTORY", 1),
            ("1115", "BS.INVENTORY", 1),
            ("1116", "BS.PPE", 1),
            ("1118", "BS.PREPAYMENTS", 1),
            ("12", "BS.PPE", 1),
            ("21", "BS.CURRENT_LIABILITIES", -1),
            ("22", "BS.NON_CURRENT_LIABILITIES", -1),
            ("3110", "BS.CAPITAL", -1),
            ("311", "BS.RETAINED_EARNINGS", -1),
            ("4112", "PL.OTHER_INCOME", -1),
            ("4", "PL.OPERATING_REVENUE", -1),
            ("5", "PL.COST_OF_REVENUE", 1),
            ("6211", "PL.FINANCE_COST", 1),
            ("6", "PL.SELLING_ADMIN_EXPENSE", 1),
        )
        for prefix, target, sign in mappings:
            if code.startswith(prefix):
                return target, sign
        return None

    @staticmethod
    def _match(rules, organization_id, level, code, name):
        normalized = normalized_account_name(name); best = (None, 0)
        for rule in rules:
            if rule.source_level not in ("any", level): continue
            company_bonus = 2 if rule.organization_id == organization_id else 0
            score = 0
            if rule.source_code and rule.source_code == code: score = 100
            elif rule.source_code_prefix and code.startswith(rule.source_code_prefix): score = 95
            elif rule.normalized_source_name and rule.normalized_source_name == normalized: score = 92
            elif rule.keywords_json and all(normalized_account_name(item) in normalized for item in rule.keywords_json): score = 82
            elif rule.normalized_source_name: score = round(SequenceMatcher(None, rule.normalized_source_name, normalized).ratio() * 75)
            score = min(100, score + company_bonus)
            if score > best[1]: best = (rule, score)
        return best


def amount_from_row(row, source: str) -> Decimal:
    values = {
        "closing_debit": row.closing_debit, "closing_credit": row.closing_credit,
        "net_closing": row.closing_debit - row.closing_credit,
        "opening_debit": row.opening_debit, "opening_credit": row.opening_credit,
        "net_opening": row.opening_debit - row.opening_credit,
        "period_debit": row.period_debit, "period_credit": row.period_credit,
        "net_period": row.period_debit - row.period_credit,
    }
    return Decimal(values.get(source, row.net_closing_balance))


class FinancialStatementCalculationService:
    def __init__(self, session: Session): self.session = session

    def calculate(self, import_: FinancialStatementImport, user_id: str, tolerance: Decimal = Decimal(0)) -> FinancialStatementRun:
        version = (self.session.scalar(select(func.max(FinancialStatementRun.version)).where(FinancialStatementRun.import_id == import_.id)) or 0) + 1
        run = FinancialStatementRun(import_id=import_.id, version=version, created_by=user_id, money_unit=import_.money_unit)
        self.session.add(run); self.session.flush()
        decisions = list(self.session.execute(select(AccountMappingDecision, FinancialStatementImportRow).join(FinancialStatementImportRow, FinancialStatementImportRow.id == AccountMappingDecision.import_row_id).where(FinancialStatementImportRow.import_id == import_.id, AccountMappingDecision.status == "mapped")).all())
        values: dict[str, FinancialStatementValue] = {}
        for decision, row in decisions:
            if not decision.target_field_id: continue
            amount = amount_from_row(row, decision.amount_source) * Decimal(decision.sign_multiplier)
            value = values.get(decision.target_field_id)
            if value is None:
                value = FinancialStatementValue(run_id=run.id, field_id=decision.target_field_id)
                self.session.add(value); self.session.flush(); values[decision.target_field_id] = value
            value.calculated_value += amount; value.final_value += amount
            self.session.add(FinancialStatementValueSource(value_id=value.id, import_row_id=row.id, mapping_rule_id=decision.rule_id, source_amount=amount_from_row(row, decision.amount_source), contribution_amount=amount, calculation_json={"amount_source": decision.amount_source, "sign": decision.sign_multiplier}))
        fields = list(self.session.scalars(select(FinancialStatementField).where(FinancialStatementField.is_active.is_(True)).order_by(FinancialStatementField.sort_order)))
        for field in fields:
            if field.id in values: continue
            status = "manual_input_required" if field.field_type == "manual_required" else "calculated"
            self.session.add(FinancialStatementValue(run_id=run.id, field_id=field.id, status=status))
        self.session.flush()
        self._derived(run.id, fields)
        total_debit = sum((row.closing_debit for row in import_.rows), Decimal(0)); total_credit = sum((row.closing_credit for row in import_.rows), Decimal(0))
        difference = total_debit - total_credit
        status = "passed" if abs(difference) <= tolerance else "failed"
        self.session.add(FinancialStatementValidation(run_id=run.id, code="trial_balance", status=status, difference=difference, tolerance=tolerance, message="تراز آزمایشی متوازن است." if status == "passed" else "جمع مانده بدهکار و بستانکار برابر نیست."))
        values = {item.field_id: item for item in self.session.scalars(select(FinancialStatementValue).where(FinancialStatementValue.run_id == run.id))}
        assets = values.get("BS.TOTAL_ASSETS").final_value if values.get("BS.TOTAL_ASSETS") else Decimal(0)
        liabilities_equity = values.get("BS.TOTAL_LIABILITIES_EQUITY").final_value if values.get("BS.TOTAL_LIABILITIES_EQUITY") else Decimal(0)
        bs_difference = assets - liabilities_equity
        bs_status = "passed" if abs(bs_difference) <= tolerance else "failed"
        self.session.add(FinancialStatementValidation(run_id=run.id, code="accounting_equation", status=bs_status, difference=bs_difference, tolerance=tolerance, message="معادله دارایی‌ها با بدهی‌ها و حقوق مالکانه برقرار است." if bs_status == "passed" else "جمع دارایی‌ها با جمع بدهی‌ها و حقوق مالکانه برابر نیست."))
        all_passed = status == "passed" and bs_status == "passed"
        run.status = "ready" if all_passed else "validation_failed"; import_.status = "calculated" if all_passed else "validation_failed"
        return run

    def _derived(self, run_id: str, fields: list[FinancialStatementField]):
        values = {item.field_id: item for item in self.session.scalars(select(FinancialStatementValue).where(FinancialStatementValue.run_id == run_id))}
        amount = lambda field_id: values[field_id].final_value if field_id in values else Decimal(0)
        for field in fields:
            target = values.get(field.id); formula = field.formula_json or {}
            if target is None or field.field_type != "derived": continue
            if "sum" in formula:
                calculated = sum((amount(item) for item in formula["sum"]), Decimal(0))
            elif "subtract" in formula:
                items = formula["subtract"]; calculated = amount(items[0]) - sum((amount(item) for item in items[1:]), Decimal(0))
            elif "add_subtract" in formula:
                rule = formula["add_subtract"]
                calculated = sum((amount(item) for item in rule.get("add", [])), Decimal(0)) - sum((amount(item) for item in rule.get("subtract", [])), Decimal(0))
            else: continue
            target.calculated_value = calculated; target.final_value = calculated


def convert_money(amount: Decimal, source_unit: str, target_unit: str) -> Decimal:
    if source_unit not in ALLOWED_UNITS or target_unit not in ALLOWED_UNITS: raise ValueError("money_unit_required")
    return amount * ALLOWED_UNITS[source_unit] / ALLOWED_UNITS[target_unit]


def workbook_export(values: list[tuple[FinancialStatementField, FinancialStatementValue]], company: str, year: str) -> bytes:
    wb = Workbook(); wb.remove(wb.active)
    titles = {"BS": "صورت وضعیت مالی", "PL": "سود و زیان", "CI": "سود و زیان جامع", "EQ": "تغییرات حقوق مالکانه", "CF": "جریان‌های نقدی"}
    for code, title in titles.items():
        ws = wb.create_sheet(title); ws.sheet_view.rightToLeft = True
        ws.append([company, year]); ws.append(["شرح", "مبلغ", "وضعیت"])
        for field, value in values:
            if field.statement == code: ws.append([field.title, float(value.final_value), value.status])
        ws.column_dimensions["A"].width = 45; ws.column_dimensions["B"].width = 22; ws.column_dimensions["C"].width = 24
    output = io.BytesIO(); wb.save(output); return output.getvalue()


def pdf_export(values: list[tuple[FinancialStatementField, FinancialStatementValue]], company: str, year: str) -> bytes:
    document = fitz.open()
    font_dir = Path(__file__).resolve().parent.parent / "assets"
    archive = fitz.Archive(str(font_dir))
    groups = {code: [] for code in ("BS", "PL", "CI", "EQ", "CF")}
    for field, value in values: groups.setdefault(field.statement, []).append((field, value))
    titles = {"BS": "صورت وضعیت مالی", "PL": "صورت سود و زیان", "CI": "صورت سود و زیان جامع", "EQ": "صورت تغییرات در حقوق مالکانه", "CF": "صورت جریان‌های نقدی"}
    css = "@font-face{font-family:vazir;src:url(vazirmatn.ttf)} body{font-family:vazir;direction:rtl;color:#102a56} h1{text-align:center;font-size:20px} .meta{text-align:center;color:#58708f} table{border-collapse:collapse;width:100%;font-size:11px} td,th{border:1px solid #cad8e8;padding:7px;text-align:right} th{background:#eaf4ff} .page{text-align:center;font-size:9px;color:#718096}"
    page_number = 0
    for code, rows in groups.items():
        for start in range(0, max(len(rows), 1), 28):
            page_number += 1; page = document.new_page(width=595, height=842)
            body = "".join(f"<tr><td>{field.title}</td><td>{value.final_value:,.0f}</td><td>{'نیازمند ورود دستی' if value.status == 'manual_input_required' else ''}</td></tr>" for field, value in rows[start:start+28])
            html = f"<h1>{titles.get(code, code)}</h1><div class='meta'>{company} — سال مالی {year}</div><br><table><thead><tr><th>شرح</th><th>مبلغ</th><th>وضعیت</th></tr></thead><tbody>{body}</tbody></table><p class='page'>صفحه {page_number}</p>"
            page.insert_htmlbox(fitz.Rect(36, 38, 559, 804), html, css=css, archive=archive)
    output = io.BytesIO(); document.save(output); document.close(); return output.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
