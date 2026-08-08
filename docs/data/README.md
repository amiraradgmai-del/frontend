# داده‌های پروژه

## فایل‌های خام

- `direct_tax_articles.csv`: داده ورودی؛ Pipeline این فایل را بازنویسی نمی‌کند.

## فایل‌های پردازش‌شده

- `processed/tax_laws.jsonl`: خروجی قدیمی با Schema ساده؛ فقط برای سازگاری نگه داشته شده است.
- `processed/tax_laws_v2.jsonl`: خروجی Chunkشده با شناسه، Hash، وضعیت و Metadata کیفیت.
- `processed/dataset_quality_report.json`: گزارش قابل‌خواندن ماشین از کیفیت خروجی نسخه ۲.

ساخت مجدد نسخه ۲ از پوشه `docs`:

```powershell
python rag_dataset.py
```

فیلد `retrieval_eligible` تا پیش از تأیید کارشناس `false` است. تغییر این فیلد نباید دستی و بدون ثبت Review انجام شود؛ در فاز مدیریت اسناد، Workflow تأیید و Audit Log مسئول این تغییر خواهند بود.

