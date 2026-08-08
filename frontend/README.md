# Tax AI Advisor Web

فرانت وب فارسی و RTL پروژه با Next.js، TypeScript، Tailwind CSS و shadcn/ui.

## اجرای محلی

```powershell
Copy-Item .env.local.example .env.local
npm.cmd install
npm.cmd run dev
```

آدرس پیش‌فرض: `http://localhost:3000`

احراز هویت از طریق Route Handlerهای Next.js انجام می‌شود و Access/Refresh Token فقط در Cookieهای `HttpOnly` نگهداری می‌شوند.
