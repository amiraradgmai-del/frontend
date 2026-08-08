"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Bot, Send, ShieldAlert, Sparkles, ThumbsDown, ThumbsUp, UserRound, UserRoundCheck } from "lucide-react";
import { api, apiStream } from "@/lib/api";
import type { AskResponse, ChatMessage, Citation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type DisplayMessage = ChatMessage & { fullCitations?: Citation[]; answerBasis?: AskResponse["answer_basis"]; sourceNotice?: string | null };

export default function ChatPage() {
  const searchParams = useSearchParams();
  const initialConversation = searchParams.get("conversation");
  const [conversationId, setConversationId] = useState<string | null>(initialConversation);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("در حال بررسی پرسش");
  const [error, setError] = useState("");
  const chatScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!initialConversation) return;
    api<ChatMessage[]>(`api/v1/conversations/${initialConversation}/messages`).then(setMessages).catch(() => setError("گفت‌وگو پیدا نشد."));
  }, [initialConversation]);

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
      const response = await apiStream<AskResponse>("api/v1/chat/stream", { question: text, conversation_id: conversationId }, setLoadingStatus);
      setConversationId(response.conversation_id);
      setMessages((items) => [...items, { id: response.message_id, role: "assistant", content: response.answer, confidence: response.confidence, needs_expert: response.needs_expert, disclaimer: response.disclaimer, created_at: new Date().toISOString(), citations: [], answerBasis: response.answer_basis, sourceNotice: response.source_notice }]);
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
    <div className="flex h-[calc(100dvh-7rem)] min-h-[32rem] flex-col">
      <header className="mb-5"><p className="text-sm font-medium text-primary">دستیار مبتنی بر منبع</p><h1 className="mt-1 text-2xl font-black">گفت‌وگوی مالیاتی</h1></header>
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
      </Card>
    </div>
  );
}

function Welcome({ onExample }: { onExample: (value: string) => void }) {
  const examples = ["آیا هر واریزی بانکی درآمد است؟", "تفاوت شخص حقیقی و شخص حقوقی در مالیات چیست؟", "چه زمانی باید پرونده مالیاتی تشکیل داد؟"];
  return <div className="mx-auto flex max-w-2xl flex-col items-center py-12 text-center"><div className="mb-5 flex size-16 items-center justify-center rounded-3xl bg-primary/10 text-primary"><Sparkles className="size-7" /></div><h2 className="text-xl font-bold">چکاه چطور می‌تواند کمک کند؟</h2><p className="mt-3 max-w-lg text-sm leading-7 text-muted-foreground">بانک دانش اولویت پاسخ است؛ توضیحات عمومی نیز کنترل‌شده و بدون حدس‌زدن قانون ارائه می‌شوند.</p><div className="mt-8 grid w-full gap-2 sm:grid-cols-3">{examples.map((item) => <button key={item} onClick={() => onExample(item)} className="rounded-xl border bg-white p-3 text-right text-xs leading-6 transition hover:border-primary/40 hover:bg-primary/5">{item}</button>)}</div></div>;
}

function Message({ message, onFeedback, onRequestExpert }: { message: DisplayMessage; onFeedback: (id: string, rating: "helpful" | "not_helpful") => void; onRequestExpert: (message: DisplayMessage) => void }) {
  const assistant = message.role === "assistant";
  return <article className={`flex gap-3 ${assistant ? "" : "flex-row-reverse"}`}><div className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${assistant ? "bg-primary text-white" : "bg-slate-200 text-slate-700"}`}>{assistant ? <Bot className="size-4" /> : <UserRound className="size-4" />}</div><div className={`max-w-[88%] ${assistant ? "" : "text-left"}`}><div className={`whitespace-pre-wrap rounded-2xl px-5 py-4 text-sm leading-8 ${assistant ? "rounded-tr-sm bg-slate-100 text-slate-800" : "rounded-tl-sm bg-primary text-primary-foreground"}`}>{message.content}</div>{assistant && message.sourceNotice && <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-6 text-amber-800">{message.sourceNotice}</p>}{assistant && <div className="mt-2 flex flex-wrap items-center gap-2">{message.confidence !== null && <Badge variant="secondary">اطمینان {Math.round(message.confidence * 100)}٪</Badge>}{message.answerBasis === "general_knowledge" && <Badge variant="outline">پاسخ عمومی چکاه</Badge>}{message.needs_expert && <Badge variant="destructive"><ShieldAlert className="size-3" /> نیازمند متخصص</Badge>}<Button variant="outline" size="sm" onClick={() => onRequestExpert(message)}><UserRoundCheck /> درخواست مشاور انسانی</Button><Button variant="ghost" size="icon-sm" onClick={() => onFeedback(message.id, "helpful")}><ThumbsUp className="size-3.5" /></Button><Button variant="ghost" size="icon-sm" onClick={() => onFeedback(message.id, "not_helpful")}><ThumbsDown className="size-3.5" /></Button></div>}{assistant && message.fullCitations && message.fullCitations.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{message.fullCitations.filter((source) => source.article_number).map((source) => <Badge key={source.chunk_id} variant="outline">ماده {source.article_number}</Badge>)}</div>}</div></article>;
}
