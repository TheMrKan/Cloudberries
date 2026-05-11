const BASE_URL = "http://localhost:8000/api";

export interface PricingElement {
  name: string;
  unit: string;
  cost: string;
}

export interface ServiceItem {
  id: number;
  name: string;
  provider: string;
  description: string | null;
  compliance_tags: string[];
  regions: string[];
  pricing_elements: PricingElement[];
}

export interface ServiceResult {
  id: number;
  name: string;
  provider: string;
  description: string | null;
  compliance_tags: string[];
  regions: string[];
  pricing_elements: PricingElement[];
  rationale: string;
  scores: Record<string, string>;
  matched_keywords: string[];
}

export interface Message {
  role: "user" | "assistant";
  text: string;
}

export interface SessionData {
  session_id: string;
  messages: Message[];
  results: ServiceResult[];
}

export interface SSECallbacks {
  onSearchResult: (service: ServiceResult) => void;
  onToken: (text: string) => void;
  onDone: () => void;
  onError: (errorText: string) => void;
}

export function getSessionId(): string {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("session_id", id);
  }
  return id;
}

export function resetSessionId(): string {
  const id = crypto.randomUUID();
  localStorage.setItem("session_id", id);
  return id;
}

export async function fetchServices(): Promise<ServiceItem[]> {
  const res = await fetch(`${BASE_URL}/services`);
  if (!res.ok) throw new Error("Failed to fetch services");
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<SessionData | null> {
  const res = await fetch(`${BASE_URL}/session?session_id=${encodeURIComponent(sessionId)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch session");
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/chat/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  if (res.status !== 204 && res.status !== 404) throw new Error("Failed to delete session");
}

export async function sendChatMessage(
  sessionId: string,
  message: string,
  callbacks: SSECallbacks,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
      signal,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") return;
    callbacks.onError("Ошибка соединения с сервером");
    return;
  }

  if (!res.ok) {
    let detail = "Ошибка сервера";
    try { const body = await res.json(); detail = body.detail || detail; } catch { /* ignore */ }
    callbacks.onError(detail);
    return;
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = "";
  let eventData = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7);
        } else if (line.startsWith("data: ")) {
          eventData = line.slice(6);
        } else if (line === "") {
          if (eventType === "search_result" && eventData) {
            callbacks.onSearchResult(JSON.parse(eventData));
          } else if (eventType === "token" && eventData) {
            const parsed = JSON.parse(eventData);
            callbacks.onToken(parsed.text);
          } else if (eventType === "done") {
            callbacks.onDone();
          } else if (eventType === "error" && eventData) {
            const parsed = JSON.parse(eventData);
            callbacks.onError(parsed.text || "Неизвестная ошибка");
          }
          eventType = "";
          eventData = "";
        }
      }
    }
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") return;
    callbacks.onError("Ошибка чтения потока данных");
  }
}

