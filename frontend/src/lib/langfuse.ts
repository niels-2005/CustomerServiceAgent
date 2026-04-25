import { LangfuseWeb } from "langfuse";

export type MessageFeedback = "up" | "down";

const LANGFUSE_SCORE_NAME = "user-thumbs";

const publicKey = __LANGFUSE_PUBLIC_KEY__.trim();
const baseUrl = __LANGFUSE_HOST__.trim() || undefined;

const langfuse = publicKey
  ? new LangfuseWeb({
      publicKey,
      baseUrl,
    })
  : null;

export function isLangfuseFeedbackEnabled(): boolean {
  return langfuse !== null;
}

export async function submitTraceFeedback(
  traceId: string,
  feedback: MessageFeedback,
  comment?: string,
): Promise<void> {
  if (langfuse === null) {
    throw new Error("Langfuse feedback is not configured.");
  }

  langfuse.score({
    id: `${traceId}-${LANGFUSE_SCORE_NAME}`,
    traceId,
    name: LANGFUSE_SCORE_NAME,
    value: feedback === "up" ? 1 : 0,
    dataType: "BOOLEAN",
    comment,
  });
  await langfuse.flush();
}
