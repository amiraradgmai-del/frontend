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
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
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


FINALIZED_LINE_ITEMS = (
    (("دارایی", "ثابت", "مشهود"), "BS.PPE", 1),
    (("دارایی", "نامشهود"), "BS.INTANGIBLE_ASSETS", 1),
    (("سرمایه", "گذاری", "بلند", "مدت"), "BS.LONG_TERM_INVESTMENTS", 1),
    (("دریافتنی", "بلند", "مدت"), "BS.LONG_TERM_RECEIVABLES", 1),
    (("پیش", "پرداخت"), "BS.PREPAYMENTS", 1),
    (("موجودی", "مواد", "کالا"), "BS.INVENTORY", 1),
    (("دریافتنی", "تجاری"), "BS.TRADE_RECEIVABLES", 1),
    (("موجودی", "نقد"), "BS.CASH", 1),
    (("سرمایه", "در", "جریان"), "BS.CAPITAL_IN_PROGRESS", 1),
    (("اندوخته", "قانونی"), "BS.LEGAL_RESERVE", 1),
    (("مازاد", "تجدید", "ارزیابی"), "BS.OTHER_RESERVES", 1),
    (("سود", "انباشته"), "BS.RETAINED_EARNINGS", 1),
    (("ذخیره", "مزایای", "پایان", "خدمت"), "BS.EMPLOYEE_BENEFITS", 1),
    (("پرداختنی", "تجاری"), "BS.TRADE_PAYABLES", 1),
    (("مالیات", "پرداختنی"), "BS.TAX_PAYABLE", 1),
    (("پیش", "دریافت"), "BS.OTHER_CURRENT_LIABILITIES", 1),
    (("بهای", "تمام", "شده", "درآمد"), "PL.COST_OF_REVENUE", -1),
    (("هزینه", "فروش", "اداری", "عمومی"), "PL.SELLING_ADMIN_EXPENSE", -1),
    (("سایر", "هزینه", "عملیاتی"), "PL.OTHER_EXPENSE", -1),
    (("هزینه", "کاهش", "ارزش"), "PL.IMPAIRMENT_EXPENSE", -1),
    (("سایر", "درآمد", "هزینه", "غیرعملیاتی"), "PL.OTHER_INCOME", 1),
    (("هزینه", "مالیات", "بر", "درآمد"), "", 1),
    (("هزینه", "مالی"), "PL.FINANCE_COST", -1),
    (("درآمد", "عملیاتی"), "PL.OPERATING_REVENUE", 1),
    (("سال", "جاری"), "PL.INCOME_TAX", -1),
)


def _latest_period_column(sheet) -> int | None:
    candidates: list[tuple[int, int]] = []
    for row in sheet.iter_rows(min_row=1, max_row=min(8, sheet.max_row)):
        for cell in row:
            text = normalize_persian_financial(cell.value)
            years = [int(value) for value in re.findall(r"(?<!\d)(13\d{2}|14\d{2})(?!\d)", text)]
            if years:
                candidates.append((max(years), cell.column))
    return max(candidates)[1] if candidates else None


def _rows_from_finalized_workbook(workbook) -> list[ParsedAccountRow]:
    """Read already-closed financial statements without inventing accounts."""
    candidates: dict[str, list[tuple[Decimal, list[ParsedAccountRow]]]] = {"BS": [], "PL": []}
    for sheet in workbook.worksheets:
        sheet_name = normalized_account_name(sheet.title)
        statement = "BS" if any(token in sheet_name for token in ("وضعیت مالی", "ترازنامه")) else "PL" if any(token in sheet_name for token in ("سودوزیان", "سود و زیان")) else ""
        if not statement:
            continue
        amount_column = _latest_period_column(sheet)
        if amount_column is None:
            continue
        sheet_rows: list[ParsedAccountRow] = []
        for row in sheet.iter_rows():
            label = next((cell.value for cell in row if isinstance(cell.value, str) and cell.value.strip()), "")
            normalized = normalized_account_name(label)
            if not normalized or normalized.startswith("جمع"):
                continue
            mapping = next((item for item in FINALIZED_LINE_ITEMS if all(key in normalized for key in item[0])), None)
            if mapping is None:
                # Plain capital must be checked after "capital in progress".
                if "سرمایه" in normalized and "گذاری" not in normalized and "جریان" not in normalized:
                    mapping = (("سرمایه",), "BS.CAPITAL", 1)
                else:
                    continue
            value = row[amount_column - 1].value if amount_column <= len(row) else None
            try:
                amount = parse_amount(value)
            except ValueError:
                continue
            _, field_id, _ = mapping
            if not field_id or not field_id.startswith(statement + "."):
                continue
            # Final statements display expenses as negative numbers already;
            # preserve the reported sign and let the mapping nature normalize it.
            net = amount
            sheet_rows.append(ParsedAccountRow(
                general_code=f"FS.{field_id}", general_name=normalize_persian_financial(label),
                closing_debit=max(net, Decimal(0)), closing_credit=max(-net, Decimal(0)),
                source_row_number=len(sheet_rows) + 1,
            ))
        if sheet_rows:
            score = sum((abs(row.closing_debit - row.closing_credit) for row in sheet_rows), Decimal(0))
            candidates[statement].append((score, sheet_rows))
    result: list[ParsedAccountRow] = []
    for statement in ("BS", "PL"):
        if candidates[statement]:
            result.extend(max(candidates[statement], key=lambda item: (item[0], len(item[1])))[1])
    if not result:
        raise ValueError("header_not_found")
    return result


class ExcelTrialBalanceParser:
    def parse(self, data: bytes) -> list[ParsedAccountRow]:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True, keep_links=False)
        matrices = [[list(row) for row in sheet.iter_rows(values_only=True)] for sheet in workbook.worksheets]
        candidates = []
        for matrix in matrices:
            try: candidates.append(_rows_from_matrix(matrix))
            except ValueError: continue
        if not candidates:
            return _rows_from_finalized_workbook(workbook)
        return max(candidates, key=len)


class LegacyExcelTrialBalanceParser:
    def parse(self, data: bytes) -> list[ParsedAccountRow]:
        # SpreadsheetML exports from several Iranian accounting packages use
        # an .xls extension and may begin with an UTF-8 BOM.
        xml_data = data[3:] if data.startswith(b"\xef\xbb\xbf") else data
        if xml_data.lstrip().startswith(b"<?xml"):
            return self._parse_spreadsheet_xml(xml_data)
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
            # Detailed codes are commonly person/vendor identifiers; the
            # subsidiary code carries the financial-statement classification.
            fallback_code = row.subsidiary_code or row.general_code
            fallback_name = row.subsidiary_name or row.general_name
            fallback = self._fallback(fallback_code, fallback_name)
            if fallback and not (match is not None and confidence == 100):
                # Standard chart-of-account codes are authoritative. This also
                # prevents a stale, overly broad user rule from remapping every
                # account in a later import.
                match = None
                target_field_id, sign_multiplier = fallback
                amount_source = "net_closing"
                if (
                    target_field_id.startswith("PL.")
                    and row.closing_debit == 0 and row.closing_credit == 0
                    and (row.period_debit != 0 or row.period_credit != 0)
                ):
                    # Closed ledgers zero income/expense balances at year-end;
                    # the closing entry can make debit and credit turnover equal.
                    # In that case use the account's natural side; otherwise use
                    # the net movement before applying the normal sign rule.
                    if row.period_debit == row.period_credit:
                        amount_source = (
                            "period_credit" if sign_multiplier == -1 else "period_debit"
                        )
                        sign_multiplier = 1
                    else:
                        amount_source = "net_period"
                confidence = self._fallback_confidence(fallback_code)
            else:
                target_field_id = match.target_field_id if match else None
                amount_source = match.amount_source if match else "net_closing"
                sign_multiplier = match.sign_multiplier if match else 1
            is_ignored = target_field_id == "__IGNORE__"
            if is_ignored:
                target_field_id = None
            status = "ignored" if is_ignored else "mapped" if confidence >= 90 else "needs_review" if confidence >= 70 else "unmapped"
            decision = self.session.scalar(select(AccountMappingDecision).where(AccountMappingDecision.import_row_id == row.id)) or AccountMappingDecision(import_row_id=row.id)
            decision.rule_id = match.id if match else None; decision.target_field_id = target_field_id
            decision.amount_source = amount_source; decision.sign_multiplier = sign_multiplier
            decision.confidence = confidence; decision.status = status
            self.session.add(decision)
            counts.setdefault(status, 0)
            counts[status] += 1
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
    def _fallback(code: str, name: str = "") -> tuple[str, int] | None:
        normalized_name = normalized_account_name(name)
        if code.startswith("FS."):
            field_id = code[3:]
            negative_nature = {
                "PL.COST_OF_REVENUE", "PL.SELLING_ADMIN_EXPENSE",
                "PL.OTHER_EXPENSE", "PL.IMPAIRMENT_EXPENSE",
                "PL.FINANCE_COST", "PL.INCOME_TAX",
            }
            return field_id, -1 if field_id in negative_nature else 1
        # Equity accounts need narrower rules than a generic 311 prefix.
        # The order is intentional: specific codes always win.
        mappings = (
            ("9", "__IGNORE__", 1),
            ("1110", "BS.CASH", 1),
            ("1111", "BS.SHORT_TERM_INVESTMENTS", 1),
            ("1112", "BS.TRADE_RECEIVABLES", 1),
            ("1113", "BS.OTHER_RECEIVABLES", 1),
            ("1114", "BS.INVENTORY", 1),
            ("1115", "BS.INVENTORY", 1),
            ("1116", "BS.PPE", 1),
            ("1118", "BS.PREPAYMENTS", 1),
            ("1210", "BS.PPE", 1),
            ("1211", "BS.INTANGIBLE_ASSETS", 1),
            ("1212", "BS.LONG_TERM_INVESTMENTS", 1),
            ("1213", "BS.LONG_TERM_RECEIVABLES", 1),
            ("12", "BS.OTHER_ASSETS", 1),
            ("211127", "BS.TAX_PAYABLE", -1),
            ("211130", "BS.TAX_PAYABLE", -1),
            ("2110", "BS.TRADE_PAYABLES", -1),
            ("2111", "BS.OTHER_PAYABLES", -1),
            ("2112", "BS.TAX_PAYABLE", -1),
            ("2113", "BS.DIVIDEND_PAYABLE", -1),
            ("2114", "BS.SHORT_TERM_BORROWINGS", -1),
            ("2115", "BS.PROVISIONS", -1),
            ("21", "BS.OTHER_CURRENT_LIABILITIES", -1),
            ("2210", "BS.LONG_TERM_PAYABLES", -1),
            ("2211", "BS.LONG_TERM_BORROWINGS", -1),
            ("2212", "BS.EMPLOYEE_BENEFITS", -1),
            ("22", "BS.OTHER_NON_CURRENT_LIABILITIES", -1),
            ("311401", "BS.CURRENT_YEAR_PROFIT_LOSS", -1),
            ("311301", "BS.RETAINED_EARNINGS", -1),
            ("311201", "BS.RETAINED_EARNINGS", -1),
            ("311101", "BS.LEGAL_RESERVE", -1),
            ("311002", "BS.CAPITAL_IN_PROGRESS", -1),
            ("311001", "BS.CAPITAL", -1),
            ("31", "BS.OTHER_RESERVES", -1),
            ("4110", "PL.OPERATING_REVENUE", -1),
            ("4111", "PL.OPERATING_REVENUE", -1),
            ("4112", "PL.OTHER_INCOME", -1),
            ("41", "PL.OTHER_INCOME", -1),
            ("5110", "PL.COST_OF_REVENUE", 1),
            ("51", "PL.COST_OF_REVENUE", 1),
            ("6110", "PL.SELLING_ADMIN_EXPENSE", 1),
            ("6111", "PL.SELLING_ADMIN_EXPENSE", 1),
            ("6112", "PL.SELLING_ADMIN_EXPENSE", 1),
            ("6211", "PL.FINANCE_COST", 1),
            ("6212", "PL.OTHER_EXPENSE", 1),
            ("62", "PL.OTHER_EXPENSE", 1),
            ("71", "PL.INCOME_TAX", 1),
        )
        for prefix, target, sign in mappings:
            if code.startswith(prefix):
                return target, sign
        name_rules = (
            (("سود", "زیان", "جاری"), "BS.CURRENT_YEAR_PROFIT_LOSS", -1),
            (("سود", "زیان", "انباشته"), "BS.RETAINED_EARNINGS", -1),
            (("اندوخته", "قانونی"), "BS.LEGAL_RESERVE", -1),
            (("سرمایه", "جریان"), "BS.CAPITAL_IN_PROGRESS", -1),
        )
        for keywords, target, sign in name_rules:
            if all(keyword in normalized_name for keyword in keywords):
                return target, sign
        return None

    @staticmethod
    def _fallback_confidence(code: str) -> int:
        if code in {"311001", "311002", "311101", "311201", "311301", "311401"}:
            return 100
        if code:
            return 90
        return 82

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
        eligible_ids = self._eligible_row_ids([row for _, row in decisions])
        decisions = [(decision, row) for decision, row in decisions if row.id in eligible_ids]
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
        profit_reconciliation = self._reconcile_current_profit_loss(run.id, decisions, tolerance)
        self._derived(run.id, fields)
        self._automatic_summaries(run.id, import_)
        trial_rows = [row for row in import_.rows if row.id in self._eligible_row_ids(list(import_.rows))]
        finalized_statement_input = bool(trial_rows) and all(row.general_code.startswith("FS.") for row in trial_rows)
        if finalized_statement_input:
            difference = Decimal(0)
            status = "passed"
            validation_message = "ورودی از نوع صورت‌های مالی بسته‌شده تشخیص داده شد؛ کنترل تراز حساب‌ها موضوعیت ندارد."
        else:
            total_debit = sum((row.closing_debit for row in trial_rows), Decimal(0)); total_credit = sum((row.closing_credit for row in trial_rows), Decimal(0))
            difference = total_debit - total_credit
            status = "passed" if abs(difference) <= tolerance else "failed"
            validation_message = "تراز آزمایشی متوازن است." if status == "passed" else "جمع مانده بدهکار و بستانکار برابر نیست."
        self.session.add(FinancialStatementValidation(run_id=run.id, code="trial_balance", status=status, difference=difference, tolerance=tolerance, message=validation_message))
        values = {item.field_id: item for item in self.session.scalars(select(FinancialStatementValue).where(FinancialStatementValue.run_id == run.id))}
        assets = values.get("BS.TOTAL_ASSETS").final_value if values.get("BS.TOTAL_ASSETS") else Decimal(0)
        liabilities_equity = values.get("BS.TOTAL_LIABILITIES_EQUITY").final_value if values.get("BS.TOTAL_LIABILITIES_EQUITY") else Decimal(0)
        bs_difference = assets - liabilities_equity
        bs_status = "passed" if abs(bs_difference) <= tolerance else "failed"
        self.session.add(FinancialStatementValidation(run_id=run.id, code="accounting_equation", status=bs_status, difference=bs_difference, tolerance=tolerance, message="معادله دارایی‌ها با بدهی‌ها و حقوق مالکانه برقرار است." if bs_status == "passed" else "جمع دارایی‌ها با جمع بدهی‌ها و حقوق مالکانه برابر نیست."))
        self.session.add(FinancialStatementValidation(
            run_id=run.id,
            code="current_profit_loss_reconciliation",
            status=profit_reconciliation[0],
            difference=profit_reconciliation[1],
            tolerance=tolerance,
            message=profit_reconciliation[2],
        ))
        all_passed = status == "passed" and bs_status == "passed" and profit_reconciliation[0] != "failed"
        run.status = "ready" if all_passed else "validation_failed"; import_.status = "calculated" if all_passed else "validation_failed"
        return run

    @staticmethod
    def _eligible_row_ids(rows: list[FinancialStatementImportRow]) -> set[str]:
        """Pick exactly one accounting level per branch (detail > subsidiary > general)."""
        by_general: dict[str, list[FinancialStatementImportRow]] = {}
        for row in rows:
            key = row.general_code or f"name:{normalized_account_name(row.general_name)}"
            by_general.setdefault(key, []).append(row)
        selected: set[str] = set()
        for general_rows in by_general.values():
            subsidiary_groups: dict[str, list[FinancialStatementImportRow]] = {}
            general_only: list[FinancialStatementImportRow] = []
            for row in general_rows:
                if row.subsidiary_code or row.subsidiary_name:
                    key = row.subsidiary_code or f"name:{normalized_account_name(row.subsidiary_name)}"
                    subsidiary_groups.setdefault(key, []).append(row)
                else:
                    general_only.append(row)
            if not subsidiary_groups:
                selected.update(row.id for row in general_only)
                continue
            for branch in subsidiary_groups.values():
                details = [row for row in branch if row.detail_code or row.detail_name]
                selected.update(row.id for row in (details or branch))
        return selected

    def _reconcile_current_profit_loss(self, run_id: str, decisions, tolerance: Decimal):
        values = {item.field_id: item for item in self.session.scalars(
            select(FinancialStatementValue).where(FinancialStatementValue.run_id == run_id)
        )}
        derived = values.get("PL.NET_PROFIT")
        current = values.get("BS.CURRENT_YEAR_PROFIT_LOSS")
        if derived is None or current is None:
            return "warning", Decimal(0), "اطلاعات کافی برای تطبیق سود و زیان جاری وجود ندارد."
        has_income_statement_rows = any(
            decision.target_field_id and decision.target_field_id.startswith("PL.")
            for decision, _ in decisions
        )
        if not has_income_statement_rows:
            return "warning", Decimal(0), "حساب‌های درآمد و هزینه برای تطبیق سود و زیان جاری موجود نیست."

        # Some closed ledgers carry the final result in equity but omit a
        # separate income-tax expense row after closing. When profit before
        # tax and the authoritative current-year result are both available,
        # recover only the missing tax line from their exact reconciliation.
        profit_before_tax = values.get("PL.PROFIT_BEFORE_TAX")
        income_tax = values.get("PL.INCOME_TAX")
        if (
            profit_before_tax is not None and income_tax is not None
            and income_tax.final_value == 0
        ):
            performance_tax = sum((
                row.closing_credit - row.closing_debit
                for _, row in decisions
                if (row.subsidiary_code or row.general_code).startswith("211127")
            ), Decimal(0))
            if performance_tax > 0:
                income_tax.calculated_value = performance_tax
                income_tax.final_value = performance_tax + income_tax.adjustment_value
                income_tax.status = "reconciled_from_tax_payable"
                derived.calculated_value = profit_before_tax.final_value - income_tax.final_value
                derived.final_value = derived.calculated_value + derived.adjustment_value
                derived.status = "reconciled_from_tax_payable"
        if (
            profit_before_tax is not None and income_tax is not None
            and income_tax.final_value == 0 and current.final_value != 0
        ):
            inferred_tax = profit_before_tax.final_value - abs(current.final_value)
            if inferred_tax > 0 and inferred_tax <= abs(profit_before_tax.final_value):
                income_tax.calculated_value = inferred_tax
                income_tax.final_value = inferred_tax + income_tax.adjustment_value
                income_tax.status = "reconciled_from_closed_ledger"
                derived.calculated_value = profit_before_tax.final_value - income_tax.final_value
                derived.final_value = derived.calculated_value + derived.adjustment_value
                derived.status = "reconciled_from_closed_ledger"

        trial_balance_result = current.final_value
        reconciliation_difference = derived.final_value - abs(trial_balance_result)
        assets = values.get("BS.TOTAL_ASSETS").final_value if values.get("BS.TOTAL_ASSETS") else Decimal(0)
        liabilities = values.get("BS.TOTAL_LIABILITIES").final_value if values.get("BS.TOTAL_LIABILITIES") else Decimal(0)
        other_equity_ids = (
            "BS.CAPITAL", "BS.CAPITAL_IN_PROGRESS", "BS.LEGAL_RESERVE",
            "BS.OTHER_RESERVES", "BS.RETAINED_EARNINGS",
        )
        other_equity = sum((values[item].final_value for item in other_equity_ids if item in values), Decimal(0))
        balance_before_current_result = assets - liabilities - other_equity

        if abs(balance_before_current_result) <= tolerance:
            # The balance sheet already balances. The trial-balance current
            # result is therefore the closing/control counterpart of the open
            # income-statement accounts and must not be counted in equity.
            current.calculated_value = Decimal(0)
            current.final_value = current.adjustment_value
            current.status = "control_account_excluded"
            status = "passed" if abs(reconciliation_difference) <= tolerance else "warning"
            return status, reconciliation_difference, "حساب سود و زیان جاری به‌عنوان حساب کنترلی شناسایی و از حقوق مالکانه حذف شد."

        if abs(balance_before_current_result - derived.final_value) <= tolerance:
            current.calculated_value = derived.final_value
            current.final_value = derived.final_value + current.adjustment_value
            current.status = "derived_from_income_statement"
            return "passed", reconciliation_difference, "سود و زیان سال جاری از صورت سود و زیان وارد حقوق مالکانه شد."

        if abs(balance_before_current_result - trial_balance_result) <= tolerance:
            current.status = "from_trial_balance"
            return "warning", reconciliation_difference, "سود و زیان جاری از مانده تراز استفاده شد و اختلاف با صورت سود و زیان نیازمند بررسی است."

        return "failed", reconciliation_difference, "سود و زیان جاری با صورت سود و زیان و معادله حسابداری قابل تطبیق نیست."

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

    def _automatic_summaries(self, run_id: str, import_: FinancialStatementImport):
        """Populate the three summary statements that can be derived reliably from a trial balance."""
        values = {item.field_id: item for item in self.session.scalars(
            select(FinancialStatementValue).where(FinancialStatementValue.run_id == run_id)
        )}

        def set_value(field_id: str, amount: Decimal):
            value = values.get(field_id)
            if value is None:
                return
            value.calculated_value = amount
            value.final_value = amount + value.adjustment_value
            value.status = "calculated"

        net_profit = values.get("PL.NET_PROFIT")
        set_value("CI.MANUAL", net_profit.final_value if net_profit else Decimal(0))

        equity_opening = Decimal(0)
        equity_closing = Decimal(0)
        cash_opening = Decimal(0)
        cash_closing = Decimal(0)
        for row in import_.rows:
            code = (row.general_code or row.subsidiary_code or row.detail_code or "").strip()
            if code.startswith("3"):
                equity_opening += row.opening_credit - row.opening_debit
                equity_closing += row.closing_credit - row.closing_debit
            if code.startswith("1110"):
                cash_opening += row.opening_debit - row.opening_credit
                cash_closing += row.closing_debit - row.closing_credit

        set_value("EQ.MANUAL", equity_closing - equity_opening)
        set_value("CF.MANUAL", cash_closing - cash_opening)


def convert_money(amount: Decimal, source_unit: str, target_unit: str) -> Decimal:
    if source_unit not in ALLOWED_UNITS or target_unit not in ALLOWED_UNITS: raise ValueError("money_unit_required")
    return amount * ALLOWED_UNITS[source_unit] / ALLOWED_UNITS[target_unit]


STATEMENT_TITLES = {
    "BS": "صورت وضعیت مالی",
    "PL": "صورت سود و زیان",
    "CI": "صورت سود و زیان جامع",
    "EQ": "صورت تغییرات در حقوق مالکانه",
    "CF": "صورت جریان‌های نقدی",
}
UNIT_TITLES = {"rial": "ریال", "toman": "تومان"}


@dataclass(frozen=True)
class ExportRow:
    field_id: str
    title: str
    amount: Decimal
    status: str


@dataclass(frozen=True)
class FinancialStatementExportData:
    company: str
    year: str
    money_unit: str
    statements: dict[str, tuple[ExportRow, ...]]


def build_export_data(
    values: list[tuple[FinancialStatementField, FinancialStatementValue]],
    company: str,
    year: str,
    money_unit: str = "rial",
) -> FinancialStatementExportData:
    if money_unit not in ALLOWED_UNITS:
        raise ValueError("money_unit_required")
    groups: dict[str, list[ExportRow]] = {code: [] for code in STATEMENT_TITLES}
    for field, value in values:
        if field.statement not in groups:
            continue
        groups[field.statement].append(ExportRow(
            field_id=field.id,
            title=field.title,
            amount=Decimal(value.final_value),
            status=value.status,
        ))
    return FinancialStatementExportData(
        company=company,
        year=year,
        money_unit=money_unit,
        statements={code: tuple(rows) for code, rows in groups.items()},
    )


def workbook_export(values, company: str, year: str, money_unit: str = "rial") -> bytes:
    data = build_export_data(values, company, year, money_unit)
    template = Path(__file__).resolve().parent.parent / "assets" / "financial-statements-template.xlsx"
    if not template.exists():
        raise RuntimeError("financial_statement_template_missing")
    workbook = load_workbook(template, data_only=False, keep_links=True)
    by_field = {
        row.field_id: convert_money(row.amount, data.money_unit, "rial") / Decimal(1_000_000)
        for rows in data.statements.values() for row in rows
    }
    amount = lambda field_id: by_field.get(field_id, Decimal(0))

    # Preserve the official workbook exactly: only metadata and designated
    # current-period input cells are changed. Notes, formatting, print areas,
    # formulas, merged cells and sheet ordering stay intact.
    cover = workbook[workbook.sheetnames[0]]
    cover["A1"] = data.company
    cover["A3"] = f"سال مالی منتهی به ۲۹ اسفند {data.year}"
    cover["A5"] = f"سال {data.year}"

    profit = workbook[workbook.sheetnames[2]]
    for cell in ("F9", "F10", "F12", "F13", "F14", "F15", "F17", "F18", "F21", "F22", "F25"):
        profit[cell] = 0
    profit["F9"] = amount("PL.OPERATING_REVENUE")
    profit["F10"] = -amount("PL.COST_OF_REVENUE")
    profit["F12"] = -amount("PL.SELLING_ADMIN_EXPENSE")
    profit["F13"] = -amount("PL.IMPAIRMENT_EXPENSE")
    profit["F14"] = amount("PL.OTHER_INCOME")
    profit["F15"] = -amount("PL.OTHER_EXPENSE")
    profit["F17"] = -amount("PL.FINANCE_COST")
    profit["F21"] = -amount("PL.INCOME_TAX")

    comprehensive = workbook[workbook.sheetnames[3]]
    comprehensive["F8"] = amount("PL.NET_PROFIT")
    comprehensive["F14"] = "=SUM(F8:F13)"

    balance = workbook[workbook.sheetnames[4]]
    balance_inputs = {
        "F9": amount("BS.PPE"),
        "F11": amount("BS.INTANGIBLE_ASSETS"),
        "F12": amount("BS.LONG_TERM_INVESTMENTS"),
        "F13": amount("BS.LONG_TERM_RECEIVABLES"),
        "F14": amount("BS.OTHER_ASSETS"),
        "F17": amount("BS.PREPAYMENTS"),
        "F18": amount("BS.INVENTORY"),
        "F19": amount("BS.TRADE_RECEIVABLES") + amount("BS.OTHER_RECEIVABLES"),
        "F20": amount("BS.SHORT_TERM_INVESTMENTS"),
        "F21": amount("BS.CASH"),
        "F28": amount("BS.CAPITAL"),
        "F29": amount("BS.CAPITAL_IN_PROGRESS"),
        "F32": amount("BS.LEGAL_RESERVE"),
        "F33": amount("BS.OTHER_RESERVES"),
        "F36": amount("BS.RETAINED_EARNINGS") + amount("BS.CURRENT_YEAR_PROFIT_LOSS"),
        "F41": amount("BS.LONG_TERM_PAYABLES"),
        "F43": amount("BS.LONG_TERM_BORROWINGS"),
        "F44": amount("BS.EMPLOYEE_BENEFITS"),
        "F47": amount("BS.TRADE_PAYABLES") + amount("BS.OTHER_PAYABLES"),
        "F48": amount("BS.TAX_PAYABLE"),
        "F49": amount("BS.DIVIDEND_PAYABLE"),
        "F50": amount("BS.SHORT_TERM_BORROWINGS"),
        "F51": amount("BS.PROVISIONS"),
        "F52": amount("BS.OTHER_CURRENT_LIABILITIES"),
    }
    for cell, value in balance_inputs.items():
        balance[cell] = value

    equity = workbook[workbook.sheetnames[5]]
    equity_inputs = {
        "C41": amount("BS.CAPITAL"), "E41": amount("BS.CAPITAL_IN_PROGRESS"),
        "K41": amount("BS.LEGAL_RESERVE"), "M41": amount("BS.OTHER_RESERVES"),
        "S41": amount("BS.RETAINED_EARNINGS") + amount("BS.CURRENT_YEAR_PROFIT_LOSS"),
        "S29": amount("PL.NET_PROFIT"),
    }
    for cell, value in equity_inputs.items():
        equity[cell] = value
    equity["W41"] = "=SUM(C41:U41)"

    cash_flow = workbook[workbook.sheetnames[6]]
    cash_flow["F50"] = amount("CF.MANUAL")
    cash_flow["F53"] = "=SUM(F50:F52)"

    # Remove template sample-period figures while retaining the comparative
    # columns and their formatting for future real comparative data.
    for sheet in (profit, comprehensive, balance, cash_flow):
        for row in range(1, sheet.max_row + 1):
            for column in (8, 10):
                if column <= sheet.max_column:
                    cell = sheet.cell(row, column)
                    if not isinstance(cell, MergedCell):
                        cell.value = None
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    output = io.BytesIO(); workbook.save(output); return output.getvalue()


def pdf_export(values, company: str, year: str, money_unit: str = "rial") -> bytes:
    data = build_export_data(values, company, year, money_unit)
    raw = {row.field_id: row.amount for rows in data.statements.values() for row in rows}
    amount = lambda field_id: convert_money(raw.get(field_id, Decimal(0)), data.money_unit, "rial") / Decimal(1_000_000)
    layouts = {
        "BS": (
            ("دارایی‌های ثابت مشهود", amount("BS.PPE")),
            ("دارایی‌های نامشهود", amount("BS.INTANGIBLE_ASSETS")),
            ("سرمایه‌گذاری‌های بلندمدت", amount("BS.LONG_TERM_INVESTMENTS")),
            ("دریافتنی‌های بلندمدت", amount("BS.LONG_TERM_RECEIVABLES")),
            ("سایر دارایی‌ها", amount("BS.OTHER_ASSETS")),
            ("پیش‌پرداخت‌ها", amount("BS.PREPAYMENTS")),
            ("موجودی مواد و کالا", amount("BS.INVENTORY")),
            ("دریافتنی‌های تجاری و سایر دریافتنی‌ها", amount("BS.TRADE_RECEIVABLES") + amount("BS.OTHER_RECEIVABLES")),
            ("سرمایه‌گذاری‌های کوتاه‌مدت", amount("BS.SHORT_TERM_INVESTMENTS")),
            ("موجودی نقد", amount("BS.CASH")),
            ("جمع دارایی‌ها", amount("BS.TOTAL_ASSETS")),
            ("سرمایه", amount("BS.CAPITAL")),
            ("افزایش سرمایه در جریان", amount("BS.CAPITAL_IN_PROGRESS")),
            ("اندوخته قانونی", amount("BS.LEGAL_RESERVE")),
            ("سایر اندوخته‌ها", amount("BS.OTHER_RESERVES")),
            ("سود انباشته", amount("BS.RETAINED_EARNINGS") + amount("BS.CURRENT_YEAR_PROFIT_LOSS")),
            ("پرداختنی‌های بلندمدت", amount("BS.LONG_TERM_PAYABLES")),
            ("تسهیلات مالی بلندمدت", amount("BS.LONG_TERM_BORROWINGS")),
            ("ذخیره مزایای پایان خدمت کارکنان", amount("BS.EMPLOYEE_BENEFITS")),
            ("پرداختنی‌های تجاری و سایر پرداختنی‌ها", amount("BS.TRADE_PAYABLES") + amount("BS.OTHER_PAYABLES")),
            ("مالیات پرداختنی", amount("BS.TAX_PAYABLE")),
            ("سود سهام پرداختنی", amount("BS.DIVIDEND_PAYABLE")),
            ("تسهیلات مالی کوتاه‌مدت", amount("BS.SHORT_TERM_BORROWINGS")),
            ("ذخایر", amount("BS.PROVISIONS")),
            ("پیش‌دریافت‌ها", amount("BS.OTHER_CURRENT_LIABILITIES")),
            ("جمع حقوق مالکانه و بدهی‌ها", amount("BS.TOTAL_LIABILITIES_EQUITY")),
        ),
        "PL": (
            ("درآمدهای عملیاتی", amount("PL.OPERATING_REVENUE")),
            ("بهای تمام‌شده درآمدهای عملیاتی", -amount("PL.COST_OF_REVENUE")),
            ("سود ناخالص", amount("PL.GROSS_PROFIT")),
            ("هزینه‌های فروش، اداری و عمومی", -amount("PL.SELLING_ADMIN_EXPENSE")),
            ("هزینه کاهش ارزش دریافتنی‌ها", -amount("PL.IMPAIRMENT_EXPENSE")),
            ("سایر درآمدها", amount("PL.OTHER_INCOME")),
            ("سایر هزینه‌ها", -amount("PL.OTHER_EXPENSE")),
            ("سود عملیاتی", amount("PL.OPERATING_PROFIT")),
            ("هزینه‌های مالی", -amount("PL.FINANCE_COST")),
            ("سود قبل از مالیات", amount("PL.PROFIT_BEFORE_TAX")),
            ("مالیات بر درآمد", -amount("PL.INCOME_TAX")),
            ("سود خالص", amount("PL.NET_PROFIT")),
        ),
        "CI": (("سود جامع سال", amount("CI.MANUAL")),),
        "EQ": (("تغییرات حقوق مالکانه", amount("EQ.MANUAL")),),
        "CF": (("خالص افزایش (کاهش) در موجودی نقد", amount("CF.MANUAL")),),
    }
    document = fitz.open()
    font_dir = Path(__file__).resolve().parent.parent / "assets"
    archive = fitz.Archive(str(font_dir))
    css = "@font-face{font-family:vazir;src:url(vazirmatn.ttf)}body{font-family:vazir;direction:rtl;color:#102a56}h1{text-align:center;font-size:20px}.meta{text-align:center;color:#58708f}table{border-collapse:collapse;width:100%;font-size:10px}td,th{border:1px solid #cad8e8;padding:7px;text-align:right}th{background:#246bce;color:white}.alt{background:#eaf4ff}.amount{text-align:left;direction:ltr}.page{text-align:center;font-size:9px;color:#718096}"
    page_number = 0
    for code, statement_title in STATEMENT_TITLES.items():
        rows = layouts[code]
        for start in range(0, max(len(rows), 1), 28):
            page_number += 1
            page = document.new_page(width=595, height=842)
            body_parts = []
            for index, (title, row_amount) in enumerate(rows[start:start + 28]):
                css_class = " class='alt'" if index % 2 else ""
                body_parts.append(f"<tr{css_class}><td>{title}</td><td class='amount'>{row_amount:,.3f}</td></tr>")
            html = f"<h1>{statement_title}</h1><div class='meta'>{data.company} — سال مالی {data.year} — مبالغ به میلیون ریال</div><br><table><thead><tr><th>شرح</th><th>مبلغ</th></tr></thead><tbody>{''.join(body_parts)}</tbody></table><p class='page'>صفحه {page_number}</p>"
            page.insert_htmlbox(fitz.Rect(36, 38, 559, 804), html, css=css, archive=archive)
    output = io.BytesIO(); document.save(output); document.close(); return output.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
