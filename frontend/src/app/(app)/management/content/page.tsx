"use client";

import Image from "next/image";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  Edit3,
  FileText,
  ImagePlus,
  Newspaper,
  Plus,
  Trash2,
} from "lucide-react";

import { FormFeedbackDialog } from "@/components/form-feedback-dialog";
import { PersianDateInput } from "@/components/persian-date-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";

type Content = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  page_type: "page" | "post";
  seo_title: string;
  seo_description: string;
  cover_image_url: string;
  category: string;
  tags: string[];
  is_published: boolean;
  scheduled_at: string | null;
  updated_at: string;
};
type Comment = {
  id: string;
  page_title: string;
  full_name: string;
  message: string;
  status: string;
  admin_note: string;
};
type Feedback = {
  title: string;
  message: string;
  kind: "error" | "success" | "info";
} | null;

const empty: Omit<Content, "id" | "updated_at"> = {
  slug: "",
  title: "",
  excerpt: "",
  content: "",
  page_type: "post",
  seo_title: "",
  seo_description: "",
  cover_image_url: "",
  category: "",
  tags: [],
  is_published: false,
  scheduled_at: null,
};

export default function ContentManagementPage() {
  const [items, setItems] = useState<Content[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);

  const load = useCallback(async () => {
    try {
      const [content, commentItems] = await Promise.all([
        api<Content[]>("api/v1/site/manage/content"),
        api<Comment[]>("api/v1/site/manage/comments"),
      ]);
      setItems(content);
      setComments(commentItems);
    } catch (error) {
      setFeedback({
        title: "دریافت محتوا انجام نشد",
        message:
          error instanceof ApiError ? error.message : "دوباره تلاش کنید.",
        kind: "error",
      });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  function edit(item: Content) {
    setEditing(item.id);
    setForm({
      slug: item.slug,
      title: item.title,
      excerpt: item.excerpt,
      content: item.content,
      page_type: item.page_type,
      seo_title: item.seo_title,
      seo_description: item.seo_description,
      cover_image_url: item.cover_image_url,
      category: item.category,
      tags: item.tags,
      is_published: item.is_published,
      scheduled_at: item.scheduled_at,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function validate(): string | null {
    if (!form.title.trim()) return "عنوان مقاله وارد نشده است.";
    if (!form.slug.trim()) return "نشانی انگلیسی مقاله وارد نشده است.";
    if (form.content.trim().length < 10)
      return "متن مقاله باید حداقل ۱۰ نویسه داشته باشد.";
    return null;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const validation = validate();
    if (validation) {
      setFeedback({
        title: "اطلاعات مقاله کامل نیست",
        message: validation,
        kind: "error",
      });
      return;
    }
    setBusy(true);
    try {
      await api(
        editing
          ? `api/v1/site/manage/content/${editing}`
          : "api/v1/site/manage/content",
        { method: editing ? "PATCH" : "POST", body: JSON.stringify(form) },
      );
      setEditing(null);
      setForm(empty);
      await load();
      setFeedback({
        title: "مقاله ذخیره شد",
        message: form.is_published
          ? "مقاله در سایت منتشر شد."
          : "مقاله به‌صورت پیش‌نویس ذخیره شد.",
        kind: "success",
      });
    } catch (error) {
      setFeedback({
        title: "ذخیره انجام نشد",
        message:
          error instanceof ApiError ? error.message : "دوباره تلاش کنید.",
        kind: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm("این مقاله حذف شود؟")) return;
    try {
      await api(`api/v1/site/manage/content/${id}`, { method: "DELETE" });
      await load();
      setFeedback({
        title: "مقاله حذف شد",
        message: "محتوای انتخاب‌شده از فهرست حذف شد.",
        kind: "success",
      });
    } catch (error) {
      setFeedback({
        title: "حذف انجام نشد",
        message:
          error instanceof ApiError ? error.message : "دوباره تلاش کنید.",
        kind: "error",
      });
    }
  }

  async function uploadImage(file: File) {
    if (!file.type.startsWith("image/")) {
      setFeedback({
        title: "فایل نامعتبر است",
        message: "فقط تصویر JPG، PNG یا WebP بارگذاری کنید.",
        kind: "error",
      });
      return;
    }
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api<{ url: string }>(
        "api/v1/site/manage/content-media",
        { method: "POST", body },
      );
      setForm((current) => ({ ...current, cover_image_url: result.url }));
      setFeedback({
        title: "تصویر بارگذاری شد",
        message: "تصویر شاخص مقاله آماده است.",
        kind: "success",
      });
    } catch (error) {
      setFeedback({
        title: "بارگذاری انجام نشد",
        message:
          error instanceof ApiError ? error.message : "دوباره تلاش کنید.",
        kind: "error",
      });
    } finally {
      setBusy(false);
    }
  }

  async function reviewComment(id: string, status: "approved" | "rejected") {
    const adminNote =
      status === "rejected" ? (window.prompt("دلیل رد نظر") ?? "") : "";
    await api(`api/v1/site/manage/comments/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status, admin_note: adminNote }),
    });
    await load();
  }

  function insert(mark: string) {
    setForm((current) => ({
      ...current,
      content: `${current.content}\n${mark}`,
    }));
  }

  return (
    <div className="space-y-7">
      <header>
        <p className="text-sm font-bold text-blue-600">مدیریت محتوای سایت</p>
        <h1 className="mt-1 text-3xl font-black">صفحات و مقاله‌ها</h1>
        <p className="mt-2 text-slate-500">
          ساخت، ویرایش، پیش‌نویس و انتشار مقاله‌ها همراه با تصویر شاخص.
        </p>
      </header>
      <form
        noValidate
        onSubmit={submit}
        className="grid gap-4 rounded-3xl border bg-white p-6 sm:grid-cols-2"
      >
        <Input
          value={form.title}
          onChange={(event) => setForm({ ...form, title: event.target.value })}
          placeholder="عنوان مقاله"
        />
        <Input
          dir="ltr"
          value={form.slug}
          onChange={(event) =>
            setForm({
              ...form,
              slug: event.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""),
            })
          }
          placeholder="article-address"
        />
        <select
          value={form.page_type}
          onChange={(event) =>
            setForm({
              ...form,
              page_type: event.target.value as "page" | "post",
            })
          }
          className="h-10 rounded-lg border bg-white px-3"
        >
          <option value="post">مقاله</option>
          <option value="page">صفحه ثابت</option>
        </select>
        <Input
          value={form.category}
          onChange={(event) =>
            setForm({ ...form, category: event.target.value })
          }
          placeholder="دسته‌بندی (اختیاری)"
        />
        <Input
          value={form.tags.join("، ")}
          onChange={(event) =>
            setForm({
              ...form,
              tags: event.target.value
                .split(/[،,]/)
                .map((value) => value.trim())
                .filter(Boolean),
            })
          }
          placeholder="برچسب‌ها با ، جدا شوند"
        />
        <div><p className="mb-1 text-xs text-slate-500">زمان‌بندی انتشار (شمسی)</p><PersianDateInput includeTime value={form.scheduled_at?.slice(0, 16) ?? ""} onChange={(value) => setForm({ ...form, scheduled_at: value ? new Date(value).toISOString() : null })} /></div>
        <div className="grid gap-3 rounded-2xl border border-dashed border-blue-200 bg-blue-50/40 p-4 sm:col-span-2 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            {form.cover_image_url ? (
              <div className="flex items-center gap-3">
                <Image
                  src={form.cover_image_url}
                  alt="تصویر شاخص"
                  width={88}
                  height={56}
                  className="h-14 w-20 rounded-xl object-cover"
                  unoptimized
                />
                <Input
                  value={form.cover_image_url}
                  onChange={(event) =>
                    setForm({ ...form, cover_image_url: event.target.value })
                  }
                  dir="ltr"
                />
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                برای مقاله یک تصویر شاخص بارگذاری کنید.
              </p>
            )}
          </div>
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white">
            <ImagePlus className="size-4" /> انتخاب تصویر
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) =>
                event.target.files?.[0] &&
                void uploadImage(event.target.files[0])
              }
            />
          </label>
        </div>
        <Input
          className="sm:col-span-2"
          value={form.excerpt}
          onChange={(event) =>
            setForm({ ...form, excerpt: event.target.value })
          }
          placeholder="خلاصه کوتاه مقاله"
        />
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => insert("## تیتر جدید")}
          >
            تیتر
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => insert("**متن مهم**")}
          >
            پررنگ
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => insert("- مورد جدید")}
          >
            فهرست
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => insert("[عنوان لینک](https://)")}
          >
            لینک
          </Button>
        </div>
        <Textarea
          className="min-h-60 sm:col-span-2"
          value={form.content}
          onChange={(event) =>
            setForm({ ...form, content: event.target.value })
          }
          placeholder="متن کامل مقاله"
        />
        <Input
          value={form.seo_title}
          onChange={(event) =>
            setForm({ ...form, seo_title: event.target.value })
          }
          placeholder="عنوان سئو (اختیاری)"
        />
        <Input
          value={form.seo_description}
          onChange={(event) =>
            setForm({ ...form, seo_description: event.target.value })
          }
          placeholder="توضیحات سئو (اختیاری)"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.is_published}
            onChange={(event) =>
              setForm({
                ...form,
                is_published: event.target.checked,
                scheduled_at: event.target.checked ? null : form.scheduled_at,
              })
            }
          />{" "}
          انتشار فوری و عمومی
        </label>
        <Button disabled={busy}>
          <Plus />
          {editing ? "ذخیره ویرایش" : "افزودن مقاله"}
        </Button>
        {editing && (
          <Button
            type="button"
            variant="outline"
            className="sm:col-span-2"
            onClick={() => {
              setEditing(null);
              setForm(empty);
            }}
          >
            انصراف از ویرایش
          </Button>
        )}
      </form>
      <section className="grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.id} className="rounded-2xl border bg-white p-5">
            <div className="flex items-start justify-between">
              <span className="rounded-xl bg-blue-50 p-3 text-blue-700">
                {item.page_type === "post" ? <Newspaper /> : <FileText />}
              </span>
              <span
                className={`rounded-full px-3 py-1 text-xs ${item.is_published ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}
              >
                {item.is_published ? "منتشرشده" : "پیش‌نویس"}
              </span>
            </div>
            <h2 className="mt-4 font-black">{item.title}</h2>
            <p className="mt-2 text-xs text-slate-500">/{item.slug}</p>
            <p className="mt-3 line-clamp-2 text-sm text-slate-600">
              {item.excerpt}
            </p>
            <div className="mt-4 flex gap-2">
              <Button size="sm" variant="outline" onClick={() => edit(item)}>
                <Edit3 /> ویرایش
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => void remove(item.id)}
              >
                <Trash2 /> حذف
              </Button>
            </div>
          </article>
        ))}
      </section>
      <section className="rounded-3xl border bg-white p-6">
        <h2 className="text-xl font-black">مدیریت نظرات مقاله‌ها</h2>
        <div className="mt-4 space-y-3">
          {comments.map((item) => (
            <div key={item.id} className="rounded-xl bg-slate-50 p-4">
              <div className="flex justify-between gap-3">
                <div>
                  <p className="font-bold">
                    {item.full_name} · {item.page_title}
                  </p>
                  <p className="mt-2 text-sm text-slate-600">{item.message}</p>
                </div>
                <span className="text-xs">{item.status}</span>
              </div>
              {item.status === "pending" && (
                <div className="mt-3 flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => void reviewComment(item.id, "approved")}
                  >
                    تأیید
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => void reviewComment(item.id, "rejected")}
                  >
                    رد
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
      <FormFeedbackDialog
        open={Boolean(feedback)}
        title={feedback?.title ?? ""}
        message={feedback?.message ?? ""}
        kind={feedback?.kind}
        onClose={() => setFeedback(null)}
      />
    </div>
  );
}
