# استقرار و نگهداری

## بررسی قبل از انتشار

```powershell
docker compose up -d --build
docker compose --profile test run --rm api-tests
powershell -ExecutionPolicy Bypass -File .\ops\verify.ps1
```

برای محیط واقعی، مقادیر زیر را در `.env` تنظیم کنید:

```env
TAX_AI_ENVIRONMENT=production
TAX_AI_DOCS_ENABLED=false
AUTH_COOKIE_SECURE=true
NEXT_PUBLIC_SITE_URL=https://example.com
```

انتشار واقعی باید پشت reverse proxy دارای HTTPS انجام شود. پورت دیتابیس و Redis به میزبان منتشر نشده‌اند و نباید منتشر شوند.

## بکاپ

سرویس `backup` پس از بالا آمدن دیتابیس یک بکاپ معتبر می‌سازد، سپس هر ۲۴ ساعت تکرار می‌کند و نسخه‌های بیشتر از ۱۴ روز را حذف می‌کند. فاصله و نگهداری با `BACKUP_INTERVAL_SECONDS` و `BACKUP_RETENTION_DAYS` قابل تنظیم است.

بکاپ دستی قابل انتقال به میزبان:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\backup-now.ps1
```

بازیابی فقط با تأیید صریح انجام می‌شود:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\restore.ps1 -BackupPath .\ops\backups\tax_ai_YYYYMMDDTHHMMSS.dump
```

قبل از بازیابی، یک بکاپ جدید بگیرید و سرویس‌های `api` و `worker` را متوقف کنید.
