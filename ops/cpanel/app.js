process.env.NODE_ENV = "production";
process.env.UV_THREADPOOL_SIZE = "2";
process.env.NEXT_TELEMETRY_DISABLED = "1";
process.env.BACKEND_URL = "http://127.0.0.1:18765";
process.env.AUTH_COOKIE_SECURE = "true";
process.env.NEXT_PUBLIC_SITE_URL = "https://chekahtax.com";
require("./server.js");
