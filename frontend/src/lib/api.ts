export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const detailMessages: Record<string, string> = {
  "Email is already registered":
    "این ایمیل قبلاً ثبت شده است.",
  "Phone is already registered":
    "این شماره موبایل قبلاً ثبت شده است.",
  "Please wait before requesting another code":
    "برای ارسال دوباره کد کمی صبر کنید.",
  "Verification email could not be sent":
    "ارسال ایمیل انجام نشد؛ دوباره تلاش کنید.",
  "Verification SMS could not be sent":
    "ارسال پیامک انجام نشد؛ دوباره تلاش کنید.",
  "Invalid or expired verification code":
    "کد تأیید اشتباه یا منقضی شده است.",
  "Invalid or expired password setup token":
    "زمان تعیین رمز تمام شده است؛ ثبت‌نام را دوباره شروع کنید.",
  "Invalid email or password":
    "ایمیل یا رمز عبور صحیح نیست.",
  "Invalid phone, email, or password":
    "شماره موبایل، ایمیل یا رمز عبور صحیح نیست.",
  "Account is temporarily locked":
    "حساب به‌دلیل تلاش ناموفق موقتاً قفل شده است.",
  "Insufficient permissions":
    "شما اجازه انجام این عملیات را ندارید.",
  "User not found":
    "کاربر موردنظر پیدا نشد.",
  "Document or version not found":
    "سند یا نسخه موردنظر پیدا نشد.",
  "Document worker is unavailable":
    "سرویس پردازش سند موقتاً در دسترس نیست.",
  "Registration is disabled":
    "ثبت‌نام در حال حاضر غیرفعال است.",
};

const fieldLabels: Record<string, string> = {
  email: "ایمیل",
  phone: "شماره موبایل",
  password: "رمز عبور",
  first_name: "نام",
  last_name: "نام خانوادگی",
  code: "کد تأیید",
  identifier: "شماره موبایل یا ایمیل",
  referral_code: "کد معرف",
  title: "عنوان",
  subject: "موضوع",
  description: "توضیحات",
};

function validationMessage(
  detail: unknown,
): string | null {
  if (
    !Array.isArray(detail) ||
    detail.length === 0
  ) {
    return null;
  }

  const issue = detail[0] as {
    loc?: unknown[];
    msg?: string;
    type?: string;
  };

  const field = String(
    issue.loc?.at(-1) ?? "",
  );
  const label =
    fieldLabels[field] ?? "اطلاعات واردشده";
  const message = issue.msg ?? "";

  if (message.includes("valid email")) {
    return "فرمت ایمیل صحیح نیست.";
  }

  if (message.includes("Persian letters only")) {
    return `${label} باید فقط با حروف فارسی نوشته شود.`;
  }

  if (message.includes("real Persian name")) {
    return `${label} واقعی و معتبر وارد کنید.`;
  }

  if (message.includes("lowercase")) {
    return "رمز عبور باید حرف کوچک انگلیسی داشته باشد.";
  }

  if (message.includes("uppercase")) {
    return "رمز عبور باید حرف بزرگ انگلیسی داشته باشد.";
  }

  if (message.includes("digit")) {
    return "رمز عبور باید حداقل یک عدد داشته باشد.";
  }

  if (message.includes("Invalid phone number")) {
    return "شماره موبایل معتبر نیست.";
  }

  if (message.includes("Email or phone is required")) {
    return "شماره موبایل یا ایمیل را وارد کنید.";
  }

  if (
    issue.type === "string_too_short"
  ) {
    return `${label} کوتاه‌تر از حد مجاز است.`;
  }

  if (
    issue.type === "string_too_long"
  ) {
    return `${label} طولانی‌تر از حد مجاز است.`;
  }

  if (
    issue.type === "string_pattern_mismatch"
  ) {
    return `${label} فرمت صحیحی ندارد.`;
  }

  return `${label} معتبر نیست.`;
}

function responseError(
  status: number,
  payload: unknown,
): string {
  const detail = (
    payload as { detail?: unknown } | null
  )?.detail;

  if (
    typeof detail === "string" &&
    detailMessages[detail]
  ) {
    return detailMessages[detail];
  }

  const validation =
    validationMessage(detail);

  if (validation) {
    return validation;
  }

  if (
    typeof detail === "string" &&
    detail.trim()
  ) {
    return detail;
  }

  if (status === 400) {
    return "اطلاعات درخواست صحیح نیست یا منقضی شده است.";
  }

  if (status === 401) {
    return "برای ادامه دوباره وارد حساب شوید.";
  }

  if (status === 403) {
    return "شما اجازه دسترسی به این بخش را ندارید.";
  }

  if (status === 404) {
    return "اطلاعات موردنظر پیدا نشد.";
  }

  if (status === 409) {
    return "این اطلاعات قبلاً ثبت شده‌اند.";
  }

  if (status === 422) {
    return "اطلاعات واردشده معتبر نیست؛ موارد فرم را بررسی کنید.";
  }

  if (status === 429) {
    return "تعداد درخواست‌ها زیاد است؛ کمی صبر کنید.";
  }

  if (status >= 500) {
    return "سرویس موقتاً در دسترس نیست؛ دوباره تلاش کنید.";
  }

  return "درخواست با خطا مواجه شد.";
}

export async function api<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const isFormData =
    typeof FormData !== "undefined" &&
    init?.body instanceof FormData;

  let response: Response;

  try {
    response = await fetch(
      `/api/backend/${path.replace(/^\//, "")}`,
      {
        ...init,
        headers: {
          ...(init?.body && !isFormData
            ? {
                "Content-Type":
                  "application/json",
              }
            : {}),
          ...init?.headers,
        },
      },
    );
  } catch {
    throw new ApiError(
      0,
      "ارتباط با سرور برقرار نشد؛ اتصال خود را بررسی کنید.",
    );
  }

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => null);

    throw new ApiError(
      response.status,
      responseError(
        response.status,
        payload,
      ),
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function apiStream<T>(path: string, body: unknown, onStatus?: (message: string) => void): Promise<T> {
  const response = await fetch(`/api/backend/${path.replace(/^\//, "")}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(response.status, responseError(response.status, payload));
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line) as { type: string; message?: string; data?: T };
      if (event.type === "status" && event.message) onStatus?.(event.message);
      if (event.type === "error") throw new ApiError(400, event.message ?? "پاسخ دریافت نشد.");
      if (event.type === "result" && event.data) return event.data;
    }
    if (done) break;
  }
  throw new ApiError(502, "پاسخ کامل از سرور دریافت نشد.");
}
