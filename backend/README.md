# Tax AI Advisor Backend

زیرساخت فاز یک پروژه شامل FastAPI، تنظیمات محیطی، Logging ساختاریافته، SQLAlchemy، Alembic، PostgreSQL و تست‌های پایه است.

## اجرای محلی

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

اجرای سریع بدون PostgreSQL و Docker:

```powershell
$env:TAX_AI_DATABASE_URL="sqlite+pysqlite:///./dev.db"
$env:TAX_AI_JWT_SECRET="یک-مقدار-تصادفی-حداقل-۳۲-کاراکتری-برای-توسعه"
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

آدرس‌ها:

- `GET /health`: زنده‌بودن Process
- `GET /ready`: آمادگی و اتصال دیتابیس
- `GET /api/v1/status`: نسخه و وضعیت عمومی سرویس
- `POST /auth/register`: ثبت‌نام با ایمیل و رمز قوی
- `POST /auth/login`: دریافت Access و Refresh Token
- `POST /auth/refresh`: تعویض امن Refresh Token
- `POST /auth/logout`: لغو Refresh Token
- `GET/PATCH /users/me`: مشاهده یا ویرایش پروفایل با RBAC

هر کاربر یک سطح حساب `normal`، `plus` یا `pro` دارد؛ سطح اولیه ثبت‌نام `normal` است. این سطح با نقش‌های امنیتی مدیر و کارشناس متفاوت است. حداقل طول رمز عبور ۸ کاراکتر است و کد ملی در ثبت‌نام یا پروفایل دریافت نمی‌شود.
- `/docs`: مستندات تعاملی فقط در محیط غیر Production

## Migration

```powershell
alembic upgrade head
```

برای اجرای Docker Compose ابتدا `.env.example` ریشه را با نام `.env` کپی و رمز توسعه را تغییر دهید. فایل `.env` در Git نادیده گرفته می‌شود.

## تست

```powershell
pytest
```

## مدیریت و پردازش اسناد

Endpointهای فاز سه زیر مسیر `/api/v1/documents` قرار دارند و شامل ایجاد سند، آپلود نسخه PDF/DOCX/TXT، مشاهده نسخه‌ها، ارسال به صف پردازش، وضعیت و تأیید کارشناس هستند. فایل‌ها در توسعه داخل Storage خصوصی محلی و در محیط اصلی از طریق Interface سازگار با S3/MinIO ذخیره می‌شوند.

## گفت‌وگو و پاسخ مستند

- `POST /api/v1/chat/query`: جست‌وجو فقط در نسخه‌های تأییدشده، فعال و معتبر و ثبت پاسخ همراه Citation
- `GET /api/v1/conversations`: تاریخچه گفتگوهای کاربر
- `GET /api/v1/conversations/{id}/messages`: پیام‌های یک گفتگو با کنترل مالکیت
- `PATCH/DELETE /api/v1/conversations/{id}`: تغییر عنوان و حذف نرم گفتگو
- `POST /api/v1/messages/{id}/feedback`: ثبت یا اصلاح بازخورد پاسخ
- `GET /api/v1/admin/feedback`: مشاهده بازخوردها برای مدیر محتوا
- `GET /api/v1/admin/advisor-stats`: شاخص‌های پایه پاسخ و ارجاع
- `POST/GET /api/v1/consultations`: ثبت درخواست مشاور و پیگیری توسط کاربر
- `GET/PATCH /api/v1/consultations/manage/...`: صف، تخصیص و نتیجه مشاوره برای متخصص

Rule Engine درخواست‌های فرار مالیاتی و اطلاعات خلاف واقع را رد می‌کند، سؤال ناقص را تشخیص می‌دهد و پرونده حساس را همراه دلیل قابل‌ثبت به متخصص ارجاع می‌دهد. در نبود شاهد کافی، Backend پاسخ قطعی تولید نمی‌کند و در نبود Provider نیز پاسخ استخراجی و قابل‌ردیابی می‌سازد.

## Gemini API

Provider پیش‌فرض `gemini` است. کلید را فقط در فایل محلی `.env` قرار دهید:

```env
TAX_AI_GEMINI_API_KEY=your-google-ai-studio-key
```

مدل تولید پاسخ `gemini-2.5-flash` و مدل بردارسازی `gemini-embedding-001` است. مدل‌ها، Timeout و ابعاد Embedding از Environment قابل‌تغییر هستند. Gemini فقط Chunkهای بازیابی‌شده را دریافت می‌کند؛ در خطای شبکه، سهمیه یا خروجی نامعتبر، پاسخ استخراجی امن به‌صورت خودکار استفاده می‌شود.

پردازش پس‌زمینه با Celery و Redis انجام می‌شود. Celery روی Windows پشتیبانی رسمی ندارد؛ Worker را در Docker/Linux اجرا کنید. اجرای ساده Backend روی Windows با SQLite:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_dev.ps1
```

Secretها فقط از Environment Variables یا فایل محلی `.env` خوانده می‌شوند. فایل `.env` نباید Commit شود.
