import * as Dialog from "@radix-ui/react-dialog";
import { ArrowUp, Bot, MessageSquareText, RotateCcw, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chat } from "@/lib/api";
import { cn } from "@/lib/utils";

type MessageRole = "assistant" | "user";
type MessageDisplayMode = "final" | "streaming";

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  displayMode?: MessageDisplayMode;
  isLocalOnly?: boolean;
}

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createWelcomeMessage(): ChatMessage {
  return {
    id: createId(),
    role: "assistant",
    isLocalOnly: true,
    content: "Willkommen bei NexaMarket. Wie kann ich dir heute helfen?",
  };
}

interface ChatWidgetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function getNextStreamingSlice(fullText: string, progress: number): string {
  if (!fullText) {
    return "";
  }

  const chunkSize = Math.max(5, Math.ceil(fullText.length / 32));
  const nextIndex = Math.min(fullText.length, progress + chunkSize);
  return fullText.slice(0, nextIndex);
}

export function ChatWidget({ open, onOpenChange }: ChatWidgetProps) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(() => [createWelcomeMessage()]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);
  const scrollViewportRef = useRef<HTMLDivElement | null>(null);
  const shouldStickToBottomRef = useRef(true);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateReducedMotion = () => setReducedMotion(mediaQuery.matches);

    updateReducedMotion();
    mediaQuery.addEventListener("change", updateReducedMotion);
    return () => mediaQuery.removeEventListener("change", updateReducedMotion);
  }, []);

  useEffect(() => {
    const viewport = scrollViewportRef.current;
    if (!viewport) {
      return;
    }
    const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
    if (shouldStickToBottomRef.current || distanceFromBottom < 28) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [messages, open]);

  useEffect(() => {
    const viewport = scrollViewportRef.current;
    if (!viewport) {
      return;
    }

    const handleScroll = () => {
      const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
      shouldStickToBottomRef.current = distanceFromBottom < 48;
    };

    handleScroll();
    viewport.addEventListener("scroll", handleScroll);
    return () => viewport.removeEventListener("scroll", handleScroll);
  }, [open]);

  const canSend = draft.trim().length > 0 && !sending;
  const launcherLabel = useMemo(() => (open ? "Chat schliessen" : "Frag KI oeffnen"), [open]);

  function resetConversation() {
    setDraft("");
    setSessionId(null);
    setErrorMessage(null);
    setSending(false);
    shouldStickToBottomRef.current = true;
    setMessages([createWelcomeMessage()]);
  }

  async function revealAssistantMessage(messageId: string, finalContent: string) {
    if (reducedMotion) {
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? { ...message, content: finalContent, displayMode: "final" }
            : message,
        ),
      );
      return;
    }

    let visibleContent = "";
    while (visibleContent.length < finalContent.length) {
      visibleContent = getNextStreamingSlice(finalContent, visibleContent.length);
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? { ...message, content: visibleContent, displayMode: "streaming" }
            : message,
        ),
      );
      await new Promise((resolve) => window.setTimeout(resolve, 46));
    }

    setMessages((current) =>
      current.map((message) =>
        message.id === messageId
          ? { ...message, content: finalContent, displayMode: "final" }
          : message,
      ),
    );
  }

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
    shouldStickToBottomRef.current = true;
    setMessages((current) => [...current, userMessage]);

    try {
      const response = await chat({
        user_message: trimmedMessage,
        session_id: sessionId ?? undefined,
      });

      setSessionId(response.session_id);

      const assistantMessageId = createId();
      setMessages((current) => [
        ...current,
        {
          id: assistantMessageId,
          role: "assistant",
          content: "",
          displayMode: "streaming",
        },
      ]);
      await revealAssistantMessage(assistantMessageId, response.answer);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unbekannter API-Fehler.";
      setErrorMessage(message);
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content:
            "Ich konnte gerade keine Antwort laden. Versuch es bitte gleich noch einmal.",
          displayMode: "final",
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
        className="group fixed right-5 bottom-5 z-40 flex items-center gap-3 rounded-full border border-white/12 bg-[linear-gradient(135deg,#080b12,#171727)] px-5 py-4 text-left text-white shadow-[0_30px_90px_rgba(0,0,0,0.55)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_40px_120px_rgba(121,66,245,0.28)] sm:right-8 sm:bottom-8"
        onClick={() => onOpenChange(true)}
      >
        <span className="flex size-11 items-center justify-center rounded-full bg-[linear-gradient(135deg,#1e7288,#38a9bf)] text-white shadow-[0_0_28px_rgba(54,154,180,0.4)] transition-transform duration-300 group-hover:scale-105">
          <MessageSquareText className="size-5" />
        </span>
        <span>
          <span className="block text-sm font-medium tracking-[0.01em]">NexaSupport</span>
        </span>
      </button>

      <Dialog.Root open={open} onOpenChange={onOpenChange}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/25 data-[state=closed]:animate-[fade-out_180ms_ease-in] data-[state=open]:animate-[fade-in_220ms_ease-out]" />
          <Dialog.Content className="fixed right-4 bottom-4 z-50 h-[min(46rem,calc(100dvh-2rem))] w-[calc(100vw-2rem)] max-w-[28rem] overflow-hidden rounded-[1.9rem] border border-white/10 bg-[#0b0d15] text-white shadow-[0_30px_140px_rgba(0,0,0,0.62)] outline-none data-[state=closed]:animate-[popup-out_180ms_ease-in] data-[state=open]:animate-[popup-in_260ms_cubic-bezier(0.22,1,0.36,1)] sm:right-8 sm:bottom-8">
            <div className="flex h-full flex-col">
              <div className="border-b border-white/8 px-5 pt-5 pb-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2">
                    <Dialog.Title className="flex items-center gap-3 text-base font-medium">
                      <span className="flex size-10 items-center justify-center rounded-full bg-[linear-gradient(135deg,rgba(30,114,136,0.28),rgba(255,255,255,0.06))]">
                        <Bot className="size-5 text-white" />
                      </span>
                      NexaSupport
                    </Dialog.Title>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="flex size-10 items-center justify-center rounded-full border border-white/10 bg-white/6 text-white/72 transition-colors hover:bg-white/10 hover:text-white"
                      onClick={resetConversation}
                      aria-label="Neuer Chat"
                    >
                      <RotateCcw className="size-4" />
                    </button>

                    <Dialog.Close asChild>
                      <button
                        type="button"
                        className="flex size-10 items-center justify-center rounded-full border border-white/10 bg-white/6 text-white/72 transition-colors hover:bg-white/10 hover:text-white"
                      >
                        <X className="size-4" />
                      </button>
                    </Dialog.Close>
                  </div>
                </div>
              </div>

              <div
                ref={scrollViewportRef}
                className="chat-widget-scrollbar flex-1 space-y-2.5 overflow-y-auto px-5 py-3"
              >
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={cn(
                      "w-fit rounded-[1.15rem] px-3.5 py-2.5 text-[0.95rem] leading-[1.5] tracking-[-0.01em] shadow-[0_18px_40px_rgba(0,0,0,0.18)]",
                      message.role === "user"
                        ? "ml-auto max-w-[72%] border border-white/10 bg-[rgba(255,255,255,0.22)] text-white/95"
                        : "max-w-[82%] border border-white/8 bg-[rgba(255,255,255,0.065)] text-white/86",
                    )}
                  >
                    <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">
                      {message.content}
                    </p>
                    {message.displayMode === "streaming" ? (
                      <span
                        aria-hidden="true"
                        className="mt-2 inline-block h-4 w-2 rounded-full bg-white/80 align-middle animate-pulse"
                      />
                    ) : null}
                  </article>
                ))}

                {sending ? (
                  <article className="w-fit max-w-[82%] rounded-[1.15rem] border border-white/8 bg-[rgba(255,255,255,0.065)] px-3.5 py-2.5 text-[0.825rem] leading-[1.5] tracking-[-0.01em] text-white/74 shadow-[0_18px_40px_rgba(0,0,0,0.18)]">
                    <p className="thinking-shimmer inline-block text-[0.825rem] font-medium text-white/58">
                      Denke nach...
                    </p>
                  </article>
                ) : null}
              </div>

              <div className="border-t border-white/8 px-5 py-4">
                {errorMessage ? (
                  <div className="mb-3 rounded-2xl border border-rose-300/16 bg-rose-300/10 px-3 py-2 text-[0.75rem] text-rose-100">
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
                    placeholder="Deine Frage an NexaSupport..."
                    disabled={sending}
                  />
                  <Button type="submit" size="icon" disabled={!canSend}>
                    <ArrowUp className="size-4" />
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
