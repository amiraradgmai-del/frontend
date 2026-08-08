# راه‌اندازی درگاه واقعی زرین‌پال

پس از دریافت Merchant ID، مقادیر زیر در فایل `.env` سرور قرار می‌گیرند:

```env
TAX_AI_ENVIRONMENT=production
TAX_AI_PAYMENT_PROVIDER=zarinpal
TAX_AI_ZARINPAL_MERCHANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TAX_AI_ZARINPAL_CALLBACK_URL=https://chekahtax.com/api/backend/api/v1/portal/payments/zarinpal/callback
NEXT_PUBLIC_SITE_URL=https://chekahtax.com
AUTH_COOKIE_SECURE=true
```

دامنه ثبت‌شده در پنل زرین‌پال باید `chekahtax.com` باشد. آدرس Callback باید دقیقاً با مقدار بالا یکسان باشد.

جریان پرداخت:

1. سفارش با وضعیت `pending` ثبت می‌شود.
2. کاربر به صفحه امن زرین‌پال منتقل می‌شود.
3. زرین‌پال کاربر را به Callback بازمی‌گرداند.
4. سرور مبلغ و Authority را با API رسمی Verify می‌کند.
5. فقط کدهای `100` و `101` معتبرند.
6. اشتراک پس از Verify فعال و شماره پیگیری ثبت می‌شود.

شماره کارت، CVV2، رمز دوم و تاریخ انقضا در چکاه دریافت یا ذخیره نمی‌شوند.
