# چکاه — دستیار هوشمند مالیاتی

چکاه یک وب‌اپ فارسی برای پاسخ‌گویی مالیاتی، جست‌وجوی قوانین، مدیریت اسناد، رزرو مشاور، پشتیبانی، اشتراک و مدیریت محتوای سایت است.

## ساختار پروژه

- `backend/`: سرویس FastAPI، دیتابیس، احراز هویت، نقش‌ها، RAG و APIها
- `frontend/`: رابط Next.js، پنل کاربران، مدیران و کارشناسان
- `docs/`: راهنمای فنی، استقرار، مسیرها و سیاست داده
- `ops/`: ابزارهای نگهداری و استقرار روی cPanel
- `data/`: داده‌های ورودی و بانک دانش

## اجرای محلی

### بک‌اند

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

### فرانت‌اند

```powershell
cd frontend
npm install
npm run dev
```

فرانت‌اند به‌صورت پیش‌فرض روی `http://localhost:3000` و بک‌اند روی `http://localhost:8000` اجرا می‌شود.

## امنیت

- کلیدها و رمزها فقط در فایل‌های `.env` قرار می‌گیرند.
- فایل‌های محیطی، دیتابیس محلی و فایل‌های بارگذاری‌شده نباید در Git ثبت شوند.
- سطح دسترسی APIها با RBAC کنترل می‌شود.

## مستندات بیشتر

- راهنمای کامل پروژه: `docs/PROJECT_GUIDE.md`
- راهنمای استقرار: `docs/DEPLOYMENT.md`
- پنل‌ها و مسیرها: `docs/PANELS_AND_ROUTES.md`
- راه‌اندازی درگاه: `docs/ZARINPAL_SETUP.md`

