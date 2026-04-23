import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, Bot, LoaderCircle, MessageSquareText, ShieldAlert, X } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";

import { chat, healthcheck, type ChatStatus } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type MessageRole = "assistant" | "user";

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  tone?: ChatStatus | "system";
}

const suggestedPrompts = [
  "Wie sende ich eine Bestellung zuruck?",
  "Wie lange dauert der Versand?",
  "Wie kann ich mein Konto erstellen?",
  "Bietet ihr Geschenkverpackungen an?",
];

const statusCopy: Record<ChatStatus, string> = {
  answered: "Antwort aus dem FAQ-Agenten.",
  blocked: "Die Anfrage wurde durch eine Schutzregel blockiert.",
  handoff: "Die Anfrage sollte an einen Menschen ubergeben werden.",
  fallback: "Es wurde eine sichere Fallback-Antwort verwendet.",
};

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createWelcomeMessage(apiReady: boolean): ChatMessage {
  return {
    id: createId(),
    role: "assistant",
    tone: "system",
    content: apiReady
      ? "Frag mich alles zu Versand, Retouren oder Konto-Themen."
      : "API noch nicht erreichbar. Starte zuerst das FastAPI-Backend auf Port 8000.",
  };
}

interface ChatWidgetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ChatWidget({ open, onOpenChange }: ChatWidgetProps) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [apiReady, setApiReady] = useState(false);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const scrollViewportRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void healthcheck()
      .then((ready) => {
        setApiReady(ready);
        setMessages([createWelcomeMessage(ready)]);
      })
      .catch(() => {
        setApiReady(false);
        setMessages([createWelcomeMessage(false)]);
      })
      .finally(() => {
        setBootstrapped(true);
      });
  }, []);

  useEffect(() => {
    const viewport = scrollViewportRef.current;
    if (!viewport) {
      return;
    }
    viewport.scrollTop = viewport.scrollHeight;
  }, [messages, open]);

  const canSend = draft.trim().length > 0 && !sending;
  const launcherLabel = useMemo(() => (open ? "Chat schliessen" : "Frag KI"), [open]);

  async function submitMessage(rawMessage: string) {
    const trimmedMessage = rawMessage.trim();
    if (!trimmedMessage || sending) {
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: trimmedMessage,
    };

    setSending(true);
    setErrorMessage(null);
    setDraft("");
    setMessages((current) => [...current, userMessage]);

    try {
      const response = await chat({
        user_message: trimmedMessage,
        session_id: sessionId ?? undefined,
      });

      setSessionId(response.session_id);
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: response.answer,
          tone: response.status,
        },
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unbekannter API-Fehler.";
      setErrorMessage(message);
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: "Die Verbindung zum Backend ist fehlgeschlagen. Prufe die API und versuche es erneut.",
          tone: "fallback",
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label={launcherLabel}
        className="group fixed right-5 bottom-5 z-40 flex items-center gap-3 rounded-full border border-white/12 bg-[linear-gradient(135deg,rgba(10,14,24,0.95),rgba(30,40,72,0.92))] px-5 py-4 text-left text-white shadow-[0_30px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_36px_120px_rgba(67,108,255,0.32)] sm:right-8 sm:bottom-8"
        onClick={() => onOpenChange(true)}
      >
        <span className="flex size-11 items-center justify-center rounded-full bg-[color:var(--accent)] text-[color:var(--accent-foreground)] shadow-[0_0_28px_rgba(91,130,255,0.55)] transition-transform duration-300 group-hover:scale-105">
          <MessageSquareText className="size-5" />
        </span>
        <span>
          <span className="block text-[0.65rem] uppercase tracking-[0.28em] text-white/46">
            Concierge AI
          </span>
          <span className="block text-sm font-medium tracking-[0.01em]">Frag KI</span>
        </span>
      </button>

      <Dialog.Root open={open} onOpenChange={onOpenChange}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/55 backdrop-blur-sm data-[state=closed]:animate-[fade-out_180ms_ease-in] data-[state=open]:animate-[fade-in_220ms_ease-out]" />
          <Dialog.Content className="fixed right-0 bottom-0 z-50 h-[100dvh] w-full border-l border-white/10 bg-[linear-gradient(180deg,rgba(9,11,19,0.98),rgba(8,10,16,0.98))] text-white shadow-[0_16px_120px_rgba(0,0,0,0.68)] outline-none data-[state=closed]:animate-[slide-down_220ms_ease-in] data-[state=open]:animate-[slide-up_280ms_cubic-bezier(0.22,1,0.36,1)] sm:right-6 sm:bottom-6 sm:h-[min(48rem,calc(100dvh-3rem))] sm:max-h-[48rem] sm:w-[28rem] sm:rounded-[2rem]">
            <div className="flex h-full flex-col">
              <div className="flex items-start justify-between border-b border-white/8 px-5 pt-5 pb-4">
                <div className="space-y-2">
                  <Dialog.Title className="flex items-center gap-3 text-lg font-medium">
                    <span className="flex size-10 items-center justify-center rounded-full bg-white/8">
                      <Bot className="size-5 text-[color:var(--accent)]" />
                    </span>
                    Frag KI
                  </Dialog.Title>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-white/48">
                    <span
                      className={cn(
                        "inline-flex items-center gap-2 rounded-full border px-3 py-1",
                        apiReady
                          ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
                          : "border-amber-300/20 bg-amber-300/10 text-amber-100",
                      )}
                    >
                      <span className="size-2 rounded-full bg-current" />
                      {apiReady ? "API verbunden" : "API offline"}
                    </span>
                    {sessionId ? <span>Session {sessionId.slice(0, 8)}</span> : null}
                  </div>
                </div>

                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="flex size-10 items-center justify-center rounded-full border border-white/10 bg-white/6 text-white/72 transition-colors hover:bg-white/10 hover:text-white"
                  >
                    <X className="size-4" />
                  </button>
                </Dialog.Close>
              </div>

              <div className="border-b border-white/8 px-5 py-4">
                <div className="flex flex-wrap gap-2">
                  {suggestedPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-left text-xs text-white/72 transition-colors hover:bg-white/10"
                      onClick={() => void submitMessage(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>

              <div
                ref={scrollViewportRef}
                className="flex-1 space-y-4 overflow-y-auto px-5 py-5"
              >
                {!bootstrapped ? (
                  <div className="flex h-full items-center justify-center">
                    <LoaderCircle className="size-5 animate-spin text-white/60" />
                  </div>
                ) : (
                  messages.map((message) => (
                    <article
                      key={message.id}
                      className={cn(
                        "max-w-[88%] rounded-[1.6rem] px-4 py-3 text-sm leading-6 shadow-[0_20px_60px_rgba(0,0,0,0.16)]",
                        message.role === "user"
                          ? "ml-auto bg-[color:var(--foreground)] text-[color:var(--background)]"
                          : "border border-white/8 bg-white/6 text-white/82",
                      )}
                    >
                      <p>{message.content}</p>
                      {message.role === "assistant" && message.tone && message.tone !== "system" ? (
                        <p className="mt-3 text-[0.68rem] uppercase tracking-[0.24em] text-white/40">
                          {statusCopy[message.tone]}
                        </p>
                      ) : null}
                    </article>
                  ))
                )}
              </div>

              <div className="border-t border-white/8 px-5 py-4">
                {errorMessage ? (
                  <div className="mb-3 flex items-center gap-2 rounded-2xl border border-amber-300/20 bg-amber-300/10 px-3 py-2 text-xs text-amber-100">
                    <ShieldAlert className="size-4 shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                ) : null}

                <form
                  className="flex items-center gap-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void submitMessage(draft);
                  }}
                >
                  <Input
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="Frage zu Versand, Retouren oder Konto..."
                    disabled={sending}
                  />
                  <Button type="submit" size="icon" disabled={!canSend}>
                    {sending ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
                  </Button>
                </form>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
