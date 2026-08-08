const ones = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه", "ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"];
const tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"];
const hundreds = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"];
const scales = ["", "هزار", "میلیون", "میلیارد", "تریلیون", "کوادریلیون"];

function underThousand(value: number) {
  const parts: string[] = [];
  if (value >= 100) { parts.push(hundreds[Math.floor(value / 100)]); value %= 100; }
  if (value < 20) { if (value) parts.push(ones[value]); }
  else { parts.push(tens[Math.floor(value / 10)]); if (value % 10) parts.push(ones[value % 10]); }
  return parts.join(" و ");
}

export function numberToPersianWords(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "";
  value = Math.floor(value);
  if (value === 0) return "صفر";
  const parts: string[] = [];
  let scale = 0;
  while (value > 0) {
    const group = value % 1000;
    if (group) parts.unshift(`${underThousand(group)}${scales[scale] ? ` ${scales[scale]}` : ""}`);
    value = Math.floor(value / 1000); scale += 1;
  }
  return parts.join(" و ");
}

export function normalizeDigits(value: string): string {
  return value.replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit))).replace(/[^0-9]/g, "");
}

export function formatToman(value: string): string {
  return value ? Number(value).toLocaleString("fa-IR") : "";
}
