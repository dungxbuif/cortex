import {
  Activity,
  Archive,
  BadgeDollarSign,
  BookOpen,
  Bot,
  CheckCircle2,
  Database,
  FileClock,
  Home,
  Loader2,
  MessageSquare,
  Send,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  UserRound,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { getDevToken, getHealth, streamChatCompletion } from "./api";
import type { ChatMessage, Citation, StreamEvent } from "./types";

const seedMessages: ChatMessage[] = [
  {
    id: "m-1",
    role: "assistant",
    content:
      "Cortex da san sang. Day la mot hoi thoai duy nhat cho user noi bo, co streaming va tool trace.",
    status: "complete",
  },
  {
    id: "m-2",
    role: "user",
    content: "Kiem tra tai lieu Obsidian vua sync va cho toi biet citation lien quan Homelab.",
    status: "complete",
  },
  {
    id: "m-3",
    role: "assistant",
    content:
      "Toi se tim trong Second Brain truoc, sau do fallback Homelab neu can. Ket qua se hien citation o panel ben phai.",
    status: "complete",
  },
];

const tabs = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "secondbrain", label: "Second Brain", icon: BookOpen },
  { id: "homelab", label: "Homelab", icon: Home },
  { id: "finance", label: "Finance", icon: BadgeDollarSign },
  { id: "ingestion", label: "Ingestion", icon: Database },
  { id: "audit", label: "Audit", icon: ShieldCheck },
] as const;

const seedEvents: StreamEvent[] = [
  { id: "e-1", label: "Streaming", detail: "OpenAI SSE compatible", status: "success" },
  { id: "e-2", label: "Tool calls", detail: "Second Brain search ready", status: "running" },
  { id: "e-3", label: "Audit trail", detail: "Single internal user", status: "success" },
];

const seedCitations: Citation[] = [
  {
    source: "second-brain/wiki/obsidian-sync.md",
    module: "Second Brain",
    detail: "Indexed Obsidian mirror chunk with Markdown source path.",
  },
  {
    source: "Homelab/docs/network/rathole.md",
    module: "Homelab",
    detail: "Read-only Homelab citation with source path.",
  },
];

export function App() {
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]["id"]>("chat");
  const [messages, setMessages] = useState<ChatMessage[]>(seedMessages);
  const [events, setEvents] = useState<StreamEvent[]>(seedEvents);
  const [citations] = useState<Citation[]>(seedCitations);
  const [input, setInput] = useState("");
  const [token, setToken] = useState("");
  const [userId, setUserId] = useState("loading");
  const [health, setHealth] = useState("checking");
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        const devToken = await getDevToken();
        if (cancelled) return;
        setToken(devToken.access_token);
        setUserId(devToken.user_id);
        const healthResponse = await getHealth(devToken.access_token);
        if (cancelled) return;
        setHealth(healthResponse.status ?? "ok");
      } catch (error) {
        if (!cancelled) {
          setHealth("error");
          appendEvent("Auth", error instanceof Error ? error.message : "bootstrap failed", "error");
        }
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const transcript = useMemo(
    () => messages.filter((message) => message.role === "user" || message.role === "assistant"),
    [messages],
  );

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const prompt = input.trim();
    if (!prompt || !token || isStreaming) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: prompt,
      status: "complete",
    };
    const assistantId = crypto.randomUUID();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      status: "streaming",
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setInput("");
    setIsStreaming(true);
    appendEvent("Streaming", "request opened", "running");

    try {
      await streamChatCompletion(
        token,
        [...messages, userMessage].map((message) => ({
          role: message.role,
          content: message.content,
        })),
        (delta) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId ? { ...message, content: message.content + delta } : message,
            ),
          );
        },
        (streamEvent) => appendEvent("Streaming", streamEvent, "success"),
      );
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? { ...message, status: "complete" } : message,
        ),
      );
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content: error instanceof Error ? error.message : "Stream failed",
                status: "error",
              }
            : message,
        ),
      );
      appendEvent("Streaming", error instanceof Error ? error.message : "stream failed", "error");
    } finally {
      setIsStreaming(false);
    }
  }

  function appendEvent(label: string, detail: string, status: StreamEvent["status"]) {
    setEvents((current) => [
      {
        id: crypto.randomUUID(),
        label,
        detail,
        status,
      },
      ...current,
    ]);
  }

  return (
    <div className="min-h-screen bg-cortex-bg text-cortex-ink">
      <div className="grid min-h-screen grid-cols-[260px_minmax(0,1fr)_340px] max-[1100px]:grid-cols-[220px_minmax(0,1fr)] max-[820px]:grid-cols-1">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

        <main className="flex min-h-screen min-w-0 flex-col border-x border-cortex-line bg-white/60">
          <header className="flex min-h-[76px] items-center justify-between gap-4 border-b border-cortex-line bg-white px-6 max-[640px]:items-start max-[640px]:flex-col max-[640px]:py-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-cortex-muted">
                <Sparkles className="h-4 w-4 text-cortex-teal" />
                Single conversation
              </div>
              <h1 className="mt-1 text-2xl font-bold leading-tight">Ask Cortex anything</h1>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill label={`User ${userId}`} tone="neutral" />
              <StatusPill label={health === "ok" ? "Gateway healthy" : health} tone={health === "ok" ? "ok" : "warn"} />
              <StatusPill label="Streaming" tone={isStreaming ? "warn" : "neutral"} />
            </div>
          </header>

          {activeTab === "chat" ? (
            <ChatView
              messages={transcript}
              input={input}
              isStreaming={isStreaming}
              onInputChange={setInput}
              onSubmit={handleSubmit}
            />
          ) : (
            <FutureTabView tab={tabs.find((tab) => tab.id === activeTab)?.label ?? "Module"} />
          )}
        </main>

        <DetailsPanel events={events} citations={citations} />
      </div>
    </div>
  );
}

function Sidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: (typeof tabs)[number]["id"];
  onTabChange: (tab: (typeof tabs)[number]["id"]) => void;
}) {
  return (
    <aside className="flex min-h-screen flex-col gap-6 bg-cortex-ink p-5 text-white max-[820px]:min-h-0">
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-lg bg-cortex-teal text-lg font-black">C</div>
        <div>
          <p className="text-lg font-bold leading-none">Cortex</p>
          <p className="mt-1 text-xs text-slate-300">Internal AI workspace</p>
        </div>
      </div>

      <nav className="grid gap-2" aria-label="Cortex workspace tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={`flex min-h-11 items-center gap-3 rounded-lg border px-3 text-left text-sm font-semibold transition ${
                isActive
                  ? "border-white/20 bg-white/12 text-white"
                  : "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/8"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </nav>

      <div className="mt-auto rounded-lg border border-white/10 bg-white/8 p-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <UserRound className="h-4 w-4 text-cortex-teal" />
          Hard-coded user
        </div>
        <p className="mt-2 break-all text-xs leading-5 text-slate-300">11111111-1111-1111-1111-111111111111</p>
      </div>
    </aside>
  );
}

function ChatView({
  messages,
  input,
  isStreaming,
  onInputChange,
  onSubmit,
}: {
  messages: ChatMessage[];
  input: string;
  isStreaming: boolean;
  onInputChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>
      <form onSubmit={onSubmit} className="border-t border-cortex-line bg-white p-4">
        <div className="flex items-end gap-3 rounded-lg border border-cortex-line bg-cortex-bg p-3">
          <textarea
            className="min-h-[54px] flex-1 resize-none bg-transparent text-sm leading-6 outline-none placeholder:text-cortex-muted"
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="Ask Cortex anything"
            rows={2}
          />
          <button className="button-primary shrink-0" type="submit" disabled={isStreaming || !input.trim()}>
            {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Send
          </button>
        </div>
      </form>
    </section>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <article className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-cortex-teal/10 text-cortex-teal">
          <Bot className="h-5 w-5" />
        </div>
      )}
      <div
        className={`max-w-[760px] rounded-lg border px-4 py-3 text-sm leading-6 ${
          isUser
            ? "border-cortex-teal bg-cortex-teal text-white"
            : "border-cortex-line bg-white text-cortex-ink"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content || " "}</p>
        {message.status === "streaming" && (
          <span className="mt-2 inline-flex items-center gap-2 text-xs font-semibold text-cortex-teal">
            <span className="h-2 w-2 animate-pulse rounded-full bg-cortex-teal" />
            Streaming
          </span>
        )}
      </div>
      {isUser && (
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-cortex-ink text-white">
          <UserRound className="h-5 w-5" />
        </div>
      )}
    </article>
  );
}

function DetailsPanel({ events, citations }: { events: StreamEvent[]; citations: Citation[] }) {
  return (
    <aside className="flex min-h-screen flex-col gap-4 bg-cortex-bg p-5 max-[1100px]:col-span-2 max-[1100px]:min-h-0 max-[820px]:col-span-1">
      <section className="panel p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-bold">Tool calls</h2>
          <TerminalSquare className="h-4 w-4 text-cortex-muted" />
        </div>
        <div className="mt-4 grid gap-3">
          {events.slice(0, 5).map((event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </div>
      </section>

      <section className="panel p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-bold">Citations</h2>
          <Archive className="h-4 w-4 text-cortex-muted" />
        </div>
        <div className="mt-4 grid gap-3">
          {citations.map((citation) => (
            <div key={citation.source} className="rounded-lg border border-cortex-line bg-white p-3">
              <p className="text-xs font-bold uppercase tracking-normal text-cortex-teal">{citation.module}</p>
              <p className="mt-1 break-words text-sm font-semibold">{citation.source}</p>
              <p className="mt-2 text-xs leading-5 text-cortex-muted">{citation.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="panel p-4">
        <div className="flex items-center gap-2 text-sm font-bold">
          <FileClock className="h-4 w-4 text-cortex-teal" />
          Audit trail
        </div>
        <p className="mt-2 text-xs leading-5 text-cortex-muted">
          JWT is validated on backend routes. The token has no expiry for this internal single-user deployment.
        </p>
      </section>
    </aside>
  );
}

function EventRow({ event }: { event: StreamEvent }) {
  const tone = {
    pending: "text-cortex-muted",
    running: "text-cortex-amber",
    success: "text-cortex-green",
    error: "text-cortex-red",
  }[event.status];
  return (
    <div className="flex gap-3 rounded-lg border border-cortex-line bg-white p-3">
      {event.status === "running" ? (
        <Loader2 className={`mt-0.5 h-4 w-4 animate-spin ${tone}`} />
      ) : event.status === "success" ? (
        <CheckCircle2 className={`mt-0.5 h-4 w-4 ${tone}`} />
      ) : (
        <Activity className={`mt-0.5 h-4 w-4 ${tone}`} />
      )}
      <div>
        <p className="text-sm font-semibold">{event.label}</p>
        <p className="text-xs leading-5 text-cortex-muted">{event.detail}</p>
      </div>
    </div>
  );
}

function FutureTabView({ tab }: { tab: string }) {
  return (
    <section className="grid flex-1 place-items-center p-8">
      <div className="panel max-w-xl p-6 text-center">
        <p className="text-sm font-bold uppercase tracking-normal text-cortex-teal">{tab}</p>
        <h2 className="mt-2 text-2xl font-bold">Dedicated UI tab reserved</h2>
        <p className="mt-3 text-sm leading-6 text-cortex-muted">
          This tab is intentionally wired into the shell now so each module can receive its own React UI later without
          changing the chat-first navigation model.
        </p>
      </div>
    </section>
  );
}

function StatusPill({ label, tone }: { label: string; tone: "ok" | "warn" | "neutral" }) {
  const classes = {
    ok: "border-green-200 bg-green-50 text-cortex-green",
    warn: "border-amber-200 bg-amber-50 text-cortex-amber",
    neutral: "border-cortex-line bg-cortex-bg text-cortex-muted",
  }[tone];
  return <span className={`inline-flex min-h-8 items-center rounded-full border px-3 text-xs font-semibold ${classes}`}>{label}</span>;
}
