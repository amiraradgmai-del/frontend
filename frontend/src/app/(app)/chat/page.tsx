"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Bot,
  Calculator,
  Gavel,
  History,
  Menu,
  MessageSquarePlus,
  Paperclip,
  Search,
  Send,
  ShieldAlert,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  UserRound,
  UserRoundCheck,
  Wrench,
  X,
} from "lucide-react";
import { api, apiStream } from "@/lib/api";
import type {
  AskResponse,
  ChatMessage,
  Citation,
  Conversation,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

type DisplayMessage = ChatMessage & {
  fullCitations?: Citation[];
  answerBasis?: AskResponse["answer_basis"];
  sourceNotice?: string | null;
  agentTitle?: string;
};
type AssistantCode = "auto" | "tax" | "accounting" | "legal" | "support";

const assistants = [
  {
    code: "auto",
    title: "انتخاب هوشمند",
    description: "تشخیص خودکار بهترین کارشناس",
    icon: Sparkles,
    tone: "bg-blue-600",
  },
  {
    code: "tax",
    title: "کارشناس مالیاتی",
    description: "اظهارنامه، ارزش افزوده، جرایم و معافیت",
    icon: Bot,
    tone: "bg-cyan-600",
  },
  {
    code: "accounting",
    title: "کارشناس حسابداری",
    description: "ثبت سند، تراز و صورت‌های مالی",
    icon: Calculator,
    tone: "bg-indigo-600",
  },
  {
    code: "legal",
    title: "کارشناس اعتراضات",
    description: "ابلاغ، اعتراض، لایحه و اختلاف مالیاتی",
    icon: Gavel,
    tone: "bg-violet-600",
  },
  {
    code: "support",
    title: "راهنمای سامانه",
    description: "ورود، اشتراک، پرداخت و امکانات چکاه",
    icon: Wrench,
    tone: "bg-sky-600",
  },
] as const;

export default function ChatPage() {
  const initialConversation = useSearchParams().get("conversation");
  const [conversationId, setConversationId] = useState<string | null>(
    initialConversation,
  );
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("در حال بررسی منابع");
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [assistantCode, setAssistantCode] = useState<AssistantCode>("auto");
  const [mobilePanel, setMobilePanel] = useState<
    "assistants" | "history" | null
  >(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const selectedAssistant =
    assistants.find((item) => item.code === assistantCode) ?? assistants[0];

  useEffect(() => {
    void loadConversations();
  }, []);
  useEffect(() => {
    if (initialConversation) void openConversation(initialConversation);
  }, [initialConversation]);
  useEffect(() => {
    chatScrollRef.current?.scrollTo({
      top: chatScrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  async function loadConversations() {
    try {
      setConversations(await api<Conversation[]>("api/v1/conversations"));
    } catch {
      setConversations([]);
    }
  }
  async function openConversation(id: string) {
    setConversationId(id);
    setMessages([]);
    setError("");
    setMobilePanel(null);
    try {
      setMessages(
        await api<ChatMessage[]>(`api/v1/conversations/${id}/messages`),
      );
    } catch {
      setError("گفت‌وگو پیدا نشد.");
    }
  }
  function newConversation() {
    setConversationId(null);
    setMessages([]);
    setQuestion("");
    setError("");
    setMobilePanel(null);
  }
  async function removeConversation(id: string) {
    if (!window.confirm("این گفت‌وگو برای همیشه حذف شود؟")) return;
    await api(`api/v1/conversations/${id}`, { method: "DELETE" });
    if (conversationId === id) newConversation();
    await loadConversations();
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (text.length < 3 || loading) return;
    setQuestion("");
    setError("");
    setLoadingStatus("در حال جست‌وجو در منابع معتبر");
    setLoading(true);
    setMessages((items) => [
      ...items,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        confidence: null,
        needs_expert: false,
        disclaimer: null,
        created_at: new Date().toISOString(),
        citations: [],
      },
    ]);
    try {
      const response = await apiStream<AskResponse>(
        "api/v1/chat/stream",
        {
          question: text,
          conversation_id: conversationId,
          assistant_code: assistantCode,
        },
        setLoadingStatus,
      );
      setConversationId(response.conversation_id);
      setMessages((items) => [
        ...items,
        {
          id: response.message_id,
          role: "assistant",
          content: response.answer,
          confidence: response.confidence,
          needs_expert: response.needs_expert,
          disclaimer: response.disclaimer,
          created_at: new Date().toISOString(),
          citations: [],
          fullCitations: response.citations,
          answerBasis: response.answer_basis,
          sourceNotice: response.source_notice,
          agentTitle: response.agent_title,
        },
      ]);
      await loadConversations();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "ارسال پرسش ناموفق بود.",
      );
    } finally {
      setLoading(false);
    }
  }
  async function feedback(
    messageId: string,
    rating: "helpful" | "not_helpful",
  ) {
    await api(`api/v1/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ rating, comment: "" }),
    }).catch(() => null);
  }
  async function requestExpert(message: DisplayMessage) {
    try {
      await api("api/v1/consultations", {
        method: "POST",
        body: JSON.stringify({
          subject: "بررسی پاسخ دستیار چکاه",
          description: `لطفاً این پاسخ را بررسی کنید:\n\n${message.content}`,
          source_message_id: message.id,
        }),
      });
      setError("درخواست بررسی توسط مشاور ثبت شد.");
    } catch {
      setError("ثبت درخواست مشاور انجام نشد.");
    }
  }

  return (
    <div
      className="-mx-4 -my-7 h-[calc(100dvh-5rem)] overflow-hidden bg-[#f5f9ff] sm:-mx-6 sm:-my-10 xl:grid xl:grid-cols-[17rem_22rem_minmax(0,1fr)]"
      dir="rtl"
    >
      <HistoryPanel
        conversations={conversations}
        active={conversationId}
        onOpen={openConversation}
        onRemove={removeConversation}
        onNew={newConversation}
        className="hidden xl:flex"
      />
      <AssistantPanel
        selected={assistantCode}
        onSelect={(code) => setAssistantCode(code)}
        className="hidden xl:flex"
      />
      <main className="flex h-full min-w-0 flex-col bg-white/70">
        <header className="flex h-[76px] shrink-0 items-center justify-between border-b border-blue-100 bg-white/90 px-4 backdrop-blur sm:px-6">
          <div className="flex items-center gap-3">
            <div
              className={`flex size-11 items-center justify-center rounded-2xl text-white shadow-lg ${selectedAssistant.tone}`}
            >
              <selectedAssistant.icon className="size-5" />
            </div>
            <div>
              <p className="font-black text-slate-900">
                {selectedAssistant.title}
              </p>
              <p className="text-xs text-slate-500">
                پاسخ‌گویی کنترل‌شده بر پایه منابع چکاه
              </p>
            </div>
          </div>
          <div className="flex gap-2 xl:hidden">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setMobilePanel("assistants")}
            >
              <Bot />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setMobilePanel("history")}
            >
              <Menu />
            </Button>
          </div>
        </header>
        <div
          ref={chatScrollRef}
          className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-8"
        >
          {!messages.length && !loading ? (
            <Welcome
              assistant={selectedAssistant.title}
              onExample={setQuestion}
            />
          ) : (
            <div className="mx-auto max-w-4xl space-y-6">
              {messages.map((message) => (
                <Message
                  key={message.id}
                  message={message}
                  onFeedback={feedback}
                  onRequestExpert={requestExpert}
                />
              ))}
              {loading && (
                <div className="flex gap-3">
                  <div className="flex size-9 items-center justify-center rounded-xl bg-blue-600 text-white">
                    <Bot className="size-4" />
                  </div>
                  <div className="rounded-2xl bg-blue-50 px-5 py-4 text-xs text-blue-700">
                    <span className="ml-3 inline-flex gap-1">
                      <i className="size-2 animate-bounce rounded-full bg-blue-500" />
                      <i className="size-2 animate-bounce rounded-full bg-blue-500 [animation-delay:150ms]" />
                      <i className="size-2 animate-bounce rounded-full bg-blue-500 [animation-delay:300ms]" />
                    </span>
                    {loadingStatus}
                  </div>
                </div>
              )}
              {error && (
                <p className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </p>
              )}
            </div>
          )}
        </div>
        <form
          onSubmit={submit}
          className="shrink-0 border-t border-blue-100 bg-white p-3 sm:p-5"
        >
          <div className="mx-auto max-w-4xl">
            <div className="flex items-end gap-2 rounded-2xl border border-blue-200 bg-white p-2 shadow-[0_12px_35px_-24px_rgba(37,99,235,.55)] focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-100">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                title="پیوست فایل"
              >
                <Paperclip />
              </Button>
              <Textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="پرسش خود را با ذکر سال، نوع مؤدی و جزئیات بنویسید..."
                className="min-h-12 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
              />
              <Button
                type="submit"
                size="icon"
                className="size-11 bg-blue-600"
                disabled={loading || question.trim().length < 3}
              >
                <Send />
              </Button>
            </div>
            <p className="mt-2 text-center text-[10px] text-slate-400">
              پاسخ چکاه جایگزین بررسی پرونده توسط مشاور نیست؛ اطلاعات محرمانه
              وارد نکنید.
            </p>
          </div>
        </form>
      </main>
      {mobilePanel && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-sm xl:hidden"
          onClick={() => setMobilePanel(null)}
        >
          <div
            className="h-full w-[min(88vw,22rem)] bg-white"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="m-3 flex size-10 items-center justify-center rounded-xl bg-slate-100"
              onClick={() => setMobilePanel(null)}
            >
              <X />
            </button>
            {mobilePanel === "assistants" ? (
              <AssistantPanel
                selected={assistantCode}
                onSelect={(code) => {
                  setAssistantCode(code);
                  setMobilePanel(null);
                }}
                className="flex h-[calc(100%-4rem)]"
              />
            ) : (
              <HistoryPanel
                conversations={conversations}
                active={conversationId}
                onOpen={openConversation}
                onRemove={removeConversation}
                onNew={newConversation}
                className="flex h-[calc(100%-4rem)]"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function HistoryPanel({
  conversations,
  active,
  onOpen,
  onRemove,
  onNew,
  className,
}: {
  conversations: Conversation[];
  active: string | null;
  onOpen: (id: string) => void;
  onRemove: (id: string) => void;
  onNew: () => void;
  className: string;
}) {
  return (
    <aside
      className={`${className} min-h-0 flex-col border-l border-blue-100 bg-slate-950 p-4 text-white`}
    >
      <div className="mb-5 flex items-center gap-3 px-2">
        <div className="flex size-10 items-center justify-center rounded-xl bg-blue-600">
          <Bot />
        </div>
        <div>
          <p className="font-black">دستیار چکاه</p>
          <p className="text-[10px] text-blue-200">مرکز پاسخ‌گویی هوشمند</p>
        </div>
      </div>
      <Button onClick={onNew} className="w-full justify-start bg-blue-600">
        <MessageSquarePlus /> گفت‌وگوی جدید
      </Button>
      <div className="mt-6 flex items-center justify-between px-2 text-xs text-slate-400">
        <span className="flex items-center gap-2">
          <History className="size-4" />
          گفت‌وگوها
        </span>
        <Search className="size-4" />
      </div>
      <div className="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto">
        {conversations.length ? (
          conversations.map((item) => (
            <div
              key={item.id}
              className={`group flex items-center rounded-xl ${active === item.id ? "bg-blue-600" : "hover:bg-white/10"}`}
            >
              <button
                onClick={() => onOpen(item.id)}
                className="min-w-0 flex-1 truncate px-3 py-3 text-right text-xs"
              >
                {item.title}
              </button>
              <button
                aria-label="حذف"
                onClick={() => onRemove(item.id)}
                className="p-2 text-red-300 opacity-0 group-hover:opacity-100"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))
        ) : (
          <p className="px-3 py-8 text-center text-xs text-slate-500">
            هنوز گفت‌وگویی ندارید.
          </p>
        )}
      </div>
      <p className="border-t border-white/10 pt-4 text-[10px] leading-5 text-slate-500">
        با حذف گفت‌وگو، پیام‌های همان گفت‌وگو نیز حذف می‌شوند.
      </p>
    </aside>
  );
}

function AssistantPanel({
  selected,
  onSelect,
  className,
}: {
  selected: AssistantCode;
  onSelect: (code: AssistantCode) => void;
  className: string;
}) {
  return (
    <aside
      className={`${className} min-h-0 flex-col border-l border-blue-100 bg-white`}
    >
      <div className="border-b border-blue-100 p-5">
        <p className="text-xs font-bold text-blue-600">کارشناسان هوشمند</p>
        <h2 className="mt-1 text-lg font-black">
          موضوع گفت‌وگو را انتخاب کنید
        </h2>
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
        {assistants.map((item) => (
          <button
            key={item.code}
            onClick={() => onSelect(item.code)}
            className={`flex w-full items-center gap-3 rounded-2xl border p-3 text-right transition ${selected === item.code ? "border-blue-300 bg-blue-50 shadow-sm" : "border-transparent hover:bg-slate-50"}`}
          >
            <span
              className={`flex size-10 shrink-0 items-center justify-center rounded-xl text-white ${item.tone}`}
            >
              <item.icon className="size-4" />
            </span>
            <span className="min-w-0">
              <b className="block text-sm text-slate-900">{item.title}</b>
              <small className="mt-1 block leading-5 text-slate-500">
                {item.description}
              </small>
            </span>
            <i
              className={`mr-auto size-2 rounded-full ${selected === item.code ? "bg-blue-500 ring-4 ring-blue-100" : "bg-slate-300"}`}
            />
          </button>
        ))}
      </div>
      <div className="border-t border-blue-100 bg-blue-50/50 p-4 text-[11px] leading-6 text-slate-500">
        <ShieldAlert className="ml-1 inline size-4 text-blue-600" />
        در مسائل حساس یا کم‌اطمینان، پرونده به مشاور انسانی ارجاع می‌شود.
      </div>
    </aside>
  );
}

function Welcome({
  assistant,
  onExample,
}: {
  assistant: string;
  onExample: (value: string) => void;
}) {
  const examples = [
    "مهلت و مراحل اعتراض به برگ تشخیص چیست؟",
    "مالیات ارزش افزوده فروش نسیه چگونه محاسبه می‌شود؟",
    "این هزینه از نظر مالیاتی قابل قبول است؟",
  ];
  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col items-center justify-center py-10 text-center">
      <div className="relative flex size-20 items-center justify-center rounded-[1.75rem] bg-gradient-to-br from-blue-700 to-cyan-500 text-white shadow-2xl shadow-blue-500/20">
        <Bot className="size-9" />
        <span className="absolute -left-1 -top-1 size-4 rounded-full border-4 border-white bg-emerald-400" />
      </div>
      <p className="mt-6 text-sm font-bold text-blue-600">{assistant}</p>
      <h1 className="mt-2 text-3xl font-black text-slate-900 sm:text-4xl">
        سؤال مالیاتی‌تان را از چکاه بپرسید
      </h1>
      <p className="mt-4 max-w-xl text-sm leading-8 text-slate-500">
        موضوع، سال مالی، نوع مؤدی و جزئیات مسئله را بنویسید تا پاسخ دقیق‌تر و
        همراه با منابع قابل بررسی دریافت کنید.
      </p>
      <div className="mt-8 grid w-full gap-2 sm:grid-cols-3">
        {examples.map((item) => (
          <button
            key={item}
            onClick={() => onExample(item)}
            className="rounded-2xl border border-blue-100 bg-white p-4 text-right text-xs leading-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-300 hover:shadow-lg"
          >
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

function Message({
  message,
  onFeedback,
  onRequestExpert,
}: {
  message: DisplayMessage;
  onFeedback: (id: string, rating: "helpful" | "not_helpful") => void;
  onRequestExpert: (message: DisplayMessage) => void;
}) {
  const assistant = message.role === "assistant";
  return (
    <article className={`flex gap-3 ${assistant ? "" : "flex-row-reverse"}`}>
      <div
        className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${assistant ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}
      >
        {assistant ? (
          <Bot className="size-4" />
        ) : (
          <UserRound className="size-4" />
        )}
      </div>
      <div className="max-w-[88%]">
        {assistant && message.agentTitle && (
          <p className="mb-1 text-[11px] font-bold text-blue-700">
            {message.agentTitle}
          </p>
        )}
        <div
          className={`whitespace-pre-wrap rounded-2xl px-5 py-4 text-sm leading-8 ${assistant ? "rounded-tr-sm border border-blue-100 bg-white text-slate-800 shadow-sm" : "rounded-tl-sm bg-blue-600 text-white"}`}
        >
          {message.content}
        </div>
        {assistant && message.sourceNotice && (
          <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-6 text-amber-800">
            {message.sourceNotice}
          </p>
        )}
        {assistant && message.fullCitations?.length ? (
          <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50/60 p-3">
            <p className="mb-2 text-xs font-black text-blue-800">منابع پاسخ</p>
            <div className="flex flex-wrap gap-2">
              {message.fullCitations.map((source) => (
                <Badge key={source.chunk_id} variant="outline">
                  {source.source_title}
                  {source.article_number
                    ? `، ماده ${source.article_number}`
                    : ""}
                </Badge>
              ))}
            </div>
          </div>
        ) : null}
        {assistant && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {message.confidence !== null && (
              <Badge variant="secondary">
                اطمینان {Math.round(message.confidence * 100)}٪
              </Badge>
            )}
            {message.needs_expert && (
              <Badge variant="destructive">نیازمند متخصص</Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onRequestExpert(message)}
            >
              <UserRoundCheck /> بررسی مشاور
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => onFeedback(message.id, "helpful")}
            >
              <ThumbsUp />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => onFeedback(message.id, "not_helpful")}
            >
              <ThumbsDown />
            </Button>
          </div>
        )}
      </div>
    </article>
  );
}
