# استقرار چکاه روی cPanel

این پروژه برای اجرای کامل به این سرویس‌ها نیاز دارد:

- Python 3.12 یا جدیدتر با پشتیبانی ASGI
- Node.js 24
- PostgreSQL 17
- Redis
- یک پردازش API دائمی
- یک Celery Worker دائمی
- یک Celery Beat دائمی

اگر یکی از موارد بالا در cPanel موجود نباشد، اجرای کامل روی هاست اشتراکی ممکن نیست و باید از VPS استفاده شود.

## دامنه‌ها

- سایت اصلی: `https://chekahtax.com`
- Callback زرین‌پال: `https://chekahtax.com/api/backend/api/v1/portal/payments/zarinpal/callback`

## ترتیب نصب

1. ساخت PostgreSQL و کاربر اختصاصی
2. تنظیم Redis داخلی
3. بارگذاری Backend و نصب وابستگی‌ها
4. اجرای `alembic upgrade head`
5. اجرای API با Uvicorn
6. اجرای Worker و Scheduler
7. Build و اجرای Next.js
8. تنظیم Reverse Proxy برای مسیر `/api/backend`
9. فعال‌سازی SSL
10. ثبت متغیرهای محیطی تولید

## بررسی سلامت

- Backend: `/health`
- Frontend: `/login`
- Callback نباید در Sitemap قرار گیرد.
- PostgreSQL و Redis نباید پورت عمومی داشته باشند.
