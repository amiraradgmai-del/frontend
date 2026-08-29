"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Bot, Calculator, Gavel, History, MessageSquarePlus, Send, ShieldAlert, Sparkles, ThumbsDown, ThumbsUp, Trash2, UserRound, UserRoundCheck, Wrench } from "lucide-react";
import { api, apiStream } from "@/lib/api";
import type { AskResponse, ChatMessage, Citation, Conversation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type DisplayMessage = ChatMessage & { fullCitations?: Citation[]; answerBasis?: AskResponse["answer_basis"]; sourceNotice?: string | null; agentTitle?: string };

const assistants = [
  { code: "auto", title: "انتخاب خودکار", description: "تشخیص بهترین کارشناس براساس سؤال", icon: Sparkles },
  { code: "tax", title: "کارشناس مالیاتی", description: "قوانین، اظهارنامه، ارزش افزوده و جرایم", icon: Bot },
  { code: "accounting", title: "کارشناس حسابداری", description: "ثبت سند، تراز و صورت‌های مالی", icon: Calculator },
  { code: "legal", title: "کارشناس حقوقی", description: "اعتراض، لایحه، ابلاغ و اختلافات", icon: Gavel },
  { code: "support", title: "راهنمای سامانه", description: "ورود، اشتراک، پرداخت و کار با چکاه", icon: Wrench },
] as const;

export default function ChatPage() {
  const searchParams = useSearchParams();
  const initialConversation = searchParams.get("conversation");
  const [conversationId, setConversationId] = useState<string | null>(initialConversation);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("در حال بررسی پرسش");
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [assistantCode, setAssistantCode] = useState("auto");
  const chatScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!initialConversation) return;
    api<ChatMessage[]>(`api/v1/conversations/${initialConversation}/messages`).then(setMessages).catch(() => setError("گفت‌وگو پیدا نشد."));
  }, [initialConversation]);

  useEffect(() => { void loadConversations(); }, []);

  async function loadConversations() {
    try { setConversations(await api<Conversation[]>("api/v1/conversations")); } catch { setConversations([]); }
  }

  async function openConversation(id: string) {
    setConversationId(id); setMessages([]); setError("");
    try { setMessages(await api<ChatMessage[]>(`api/v1/conversations/${id}/messages`)); } catch { setError("گفت‌وگو پیدا نشد."); }
  }

  function newConversation() { setConversationId(null); setMessages([]); setQuestion(""); setError(""); }

  async function removeConversation(id: string) {
    if (!window.confirm("این گفت‌وگو و اطلاعات وابسته حذف شود؟")) return;
    await api(`api/v1/conversations/${id}`, { method: "DELETE" });
    if (conversationId === id) newConversation();
    await loadConversations();
  }

  useEffect(() => {
    const container = chatScrollRef.current;
    if (!container) return;
    const distance = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distance < 220) container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (text.length < 3 || loading) return;
    setQuestion(""); setError(""); setLoadingStatus("در حال بررسی پرسش"); setLoading(true);
    const optimistic: DisplayMessage = { id: crypto.randomUUID(), role: "user", content: text, confidence: null, needs_expert: false, disclaimer: null, created_at: new Date().toISOString(), citations: [] };
    setMessages((items) => [...items, optimistic]);
    try {
      const response = await apiStream<AskResponse>("api/v1/chat/stream", { question: text, conversation_id: conversationId, assistant_code: assistantCode }, setLoadingStatus);
      setConversationId(response.conversation_id);
      setMessages((items) => [...items, { id: response.message_id, role: "assistant", content: response.answer, confidence: response.confidence, needs_expert: response.needs_expert, disclaimer: response.disclaimer, created_at: new Date().toISOString(), citations: [], fullCitations: response.citations, answerBasis: response.answer_basis, sourceNotice: response.source_notice, agentTitle: response.agent_title }]);
      await loadConversations();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "ارسال پرسش ناموفق بود.");
    } finally { setLoading(false); }
  }

  async function feedback(messageId: string, rating: "helpful" | "not_helpful") {
    await api(`api/v1/messages/${messageId}/feedback`, { method: "POST", body: JSON.stringify({ rating, comment: "" }) }).catch(() => null);
  }

  async function requestExpert(message: DisplayMessage) {
    try {
      await api("api/v1/consultations", { method: "POST", body: JSON.stringify({ subject: "بررسی پاسخ دستیار مالیاتی", description: `لطفاً این پاسخ هوش مصنوعی را از نظر قانونی و کاربردی بررسی کنید:\n\n${message.content}`, source_message_id: message.id }) });
      setError("درخواست بررسی انسانی با موفقیت ثبت شد.");
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "ثبت درخواست مشاور انجام نشد."); }
  }

  return (
    <div className="grid h-[calc(100dvh-7rem)] min-h-[38rem] gap-4 xl:grid-cols-[19rem_minmax(0,1fr)]">
      <aside className="hidden min-h-0 flex-col overflow-hidden rounded-3xl border border-sky-100 bg-white/90 shadow-lg xl:flex">
        <div className="border-b p-4"><Button className="w-full justify-start" onClick={newConversation}><MessageSquarePlus /> گفت‌وگوی جدید</Button></div>
        <div className="border-b p-4"><p className="mb-3 text-xs font-black text-slate-500">دستیارها</p><div className="space-y-1">{assistants.map((item) => <button key={item.code} onClick={() => setAssistantCode(item.code)} className={`flex w-full gap-3 rounded-xl p-3 text-right transition ${assistantCode === item.code ? "bg-blue-50 text-blue-800" : "hover:bg-slate-50"}`}><item.icon className="mt-0.5 size-4 shrink-0" /><span><b className="block text-sm">{item.title}</b><small className="mt-1 block leading-5 text-slate-500">{item.description}</small></span></button>)}</div></div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4"><p className="mb-3 flex items-center gap-2 text-xs font-black text-slate-500"><History className="size-4" /> گفت‌وگوها</p><div className="space-y-1">{conversations.map((item) => <div key={item.id} className={`group flex items-center rounded-xl ${conversationId === item.id ? "bg-slate-100" : "hover:bg-slate-50"}`}><button onClick={() => void openConversation(item.id)} className="min-w-0 flex-1 truncate px-3 py-2.5 text-right text-xs">{item.title}</button><button aria-label="حذف گفتگو" onClick={() => void removeConversation(item.id)} className="ml-1 hidden p-2 text-red-500 group-hover:block"><Trash2 className="size-3.5" /></button></div>)}</div></div>
        <p className="border-t p-4 text-[11px] leading-5 text-slate-500">با حذف گفتگو، پیام‌های وابسته نیز از حساب شما حذف می‌شوند.</p>
      </aside>
      <div className="flex min-h-0 flex-col"><header className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-medium text-primary">دستیار مبتنی بر منبع</p><h1 className="mt-1 text-2xl font-black">گفت‌وگوی مالی و مالیاتی</h1></div><select aria-label="انتخاب دستیار" value={assistantCode} onChange={(event) => setAssistantCode(event.target.value)} className="h-10 rounded-xl border bg-white px-3 text-sm font-bold xl:hidden">{assistants.map((item) => <option key={item.code} value={item.code}>{item.title}</option>)}</select></header>
      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden border-white/70 bg-white/80 shadow-xl shadow-slate-900/5 backdrop-blur">
        <div ref={chatScrollRef} className="min-h-0 flex-1 space-y-6 overflow-y-auto overscroll-contain p-4 [scrollbar-gutter:stable] sm:p-7">
          {!messages.length && !loading && <Welcome onExample={setQuestion} />}
          {messages.map((message) => <Message key={message.id} message={message} onFeedback={feedback} onRequestExpert={requestExpert} />)}
          {loading && <div className="flex gap-3"><div className="flex size-9 items-center justify-center rounded-xl bg-primary text-white"><Bot className="size-4" /></div><div className="rounded-2xl rounded-tr-sm bg-slate-100 px-5 py-4"><span className="ml-3 inline-flex gap-1"><i className="size-2 animate-bounce rounded-full bg-slate-400" /><i className="size-2 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" /><i className="size-2 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" /></span><span className="text-xs text-slate-500">{loadingStatus}</span></div></div>}
          {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </div>
        <form onSubmit={submit} className="border-t bg-white/90 p-3 sm:p-5">
          <div className="flex items-end gap-2 rounded-2xl border bg-slate-50 p-2 focus-within:border-primary/50 focus-within:ring-4 focus-within:ring-primary/5">
            <Textarea value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} placeholder="سؤال مالیاتی خود را با جزئیات بنویسید..." className="min-h-14 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0" />
            <Button type="submit" size="icon" className="size-11 shrink-0 rounded-xl" disabled={loading || question.trim().length < 3}><Send className="size-4" /></Button>
          </div>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">اطلاعات هویتی، شماره حساب یا متن محرمانه پرونده را وارد نکنید.</p>
        </form>
      </Card></div>
    </div>
  );
}

function Welcome({ onExample }: { onExample: (value: string) => void }) {
  const examples = ["برای اعتراض به برگ تشخیص چه مهلت و مدارکی لازم است؟", "فروش نسیه در ارزش افزوده چه زمانی شناسایی می‌شود؟", "هزینه قابل‌قبول مالیاتی چه شرایطی دارد؟"];
  return <div className="mx-auto flex max-w-2xl flex-col items-center py-12 text-center"><div className="mb-5 flex size-16 items-center justify-center rounded-3xl bg-primary/10 text-primary"><Sparkles className="size-7" /></div><h2 className="text-xl font-bold">چکاه چطور می‌تواند کمک کند؟</h2><p className="mt-3 max-w-lg text-sm leading-7 text-muted-foreground">بانک دانش اولویت پاسخ است؛ توضیحات عمومی نیز کنترل‌شده و بدون حدس‌زدن قانون ارائه می‌شوند.</p><div className="mt-8 grid w-full gap-2 sm:grid-cols-3">{examples.map((item) => <button key={item} onClick={() => onExample(item)} className="rounded-xl border bg-white p-3 text-right text-xs leading-6 transition hover:border-primary/40 hover:bg-primary/5">{item}</button>)}</div></div>;
}

function Message({ message, onFeedback, onRequestExpert }: { message: DisplayMessage; onFeedback: (id: string, rating: "helpful" | "not_helpful") => void; onRequestExpert: (message: DisplayMessage) => void }) {
  const assistant = message.role === "assistant";
  return <article className={`flex gap-3 ${assistant ? "" : "flex-row-reverse"}`}><div className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${assistant ? "bg-primary text-white" : "bg-slate-200 text-slate-700"}`}>{assistant ? <Bot className="size-4" /> : <UserRound className="size-4" />}</div><div className={`max-w-[88%] ${assistant ? "" : "text-left"}`}>{assistant && message.agentTitle && <p className="mb-1 text-[11px] font-bold text-blue-700">{message.agentTitle}</p>}<div className={`whitespace-pre-wrap rounded-2xl px-5 py-4 text-sm leading-8 ${assistant ? "rounded-tr-sm bg-slate-100 text-slate-800" : "rounded-tl-sm bg-primary text-primary-foreground"}`}>{message.content}</div>{assistant && message.sourceNotice && <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-6 text-amber-800">{message.sourceNotice}</p>}{assistant && message.fullCitations && message.fullCitations.length > 0 && <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50/60 p-3"><p className="mb-2 text-xs font-black text-blue-800">مستندات بازیابی‌شده</p><div className="flex flex-wrap gap-2">{message.fullCitations.map((source) => { const label = `${source.source_title}${source.article_number ? `، ماده ${source.article_number}` : ""} · ${Math.round(source.score * 100).toLocaleString("fa-IR")}٪`; return source.source_url ? <a key={source.chunk_id} href={source.source_url} target="_blank" rel="noreferrer" className="inline-flex"><Badge variant="outline" className="cursor-pointer hover:bg-blue-100">{label}</Badge></a> : <Badge key={source.chunk_id} variant="outline">{label}</Badge>; })}</div></div>}{assistant && <div className="mt-2 flex flex-wrap items-center gap-2">{message.confidence !== null && <Badge variant="secondary">اطمینان {Math.round(message.confidence * 100)}٪</Badge>}{message.answerBasis === "general_knowledge" && <Badge variant="outline">پاسخ عمومی چکاه</Badge>}{message.needs_expert && <Badge variant="destructive"><ShieldAlert className="size-3" /> نیازمند متخصص</Badge>}<Button variant="outline" size="sm" onClick={() => onRequestExpert(message)}><UserRoundCheck /> درخواست مشاور انسانی</Button><Button variant="ghost" size="icon-sm" onClick={() => onFeedback(message.id, "helpful")}><ThumbsUp className="size-3.5" /></Button><Button variant="ghost" size="icon-sm" onClick={() => onFeedback(message.id, "not_helpful")}><ThumbsDown className="size-3.5" /></Button></div>}</div></article>;
}
