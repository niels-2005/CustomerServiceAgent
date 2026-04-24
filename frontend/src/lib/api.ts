const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8000").replace(/\/+$/, "");

export type ChatStatus = "answered" | "blocked" | "handoff" | "fallback";

export interface ChatRequest {
  user_message: string;
  session_id?: string;
}

export interface ChatResponse {
  answer: string;
  session_id: string;
  status: ChatStatus;
  guardrail_reason: string | null;
  handoff_required: boolean;
  retry_used: boolean;
  sanitized: boolean;
}

interface HealthResponse {
  status: "ok";
}

interface ApiErrorPayload {
  error?: {
    message?: string;
  };
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (payload.error?.message) {
      return payload.error.message;
    }
  } catch {
    // Fall back to status text when the backend does not return structured JSON.
  }

  if (response.status === 429) {
    return "Zu viele Anfragen. Bitte warte kurz und versuche es erneut.";
  }

  return `API request failed with status ${response.status}${response.statusText ? ` ${response.statusText}` : ""}.`;
}

export async function healthcheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
      return false;
    }

    const payload = (await response.json()) as HealthResponse;
    return payload.status === "ok";
  } catch {
    return false;
  }
}

export async function chat(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  return (await response.json()) as ChatResponse;
}
