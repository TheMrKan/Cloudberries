const BASE_URL = "http://localhost:8000/api";

export interface PricingElement {
  name: string;
  unit: string;
  cost: string;
}

export interface BackendServiceItem {
  id: number;
  name: string;
  provider: string;
  description: string | null;
  compliance_tags: string[];
  regions: string[];
  pricing_elements: BackendPricingElement[];
}

export interface BackendPricingElement {
  description?: string;
  uom?: string;
  price?: number;
  name?: string;
  unit?: string;
  cost?: string;
}

export interface BackendServiceResult {
  id: number;
  name: string;
  provider: string;
  description: string | null;
  compliance_tags: string[];
  regions: string[];
  pricing_elements: BackendPricingElement[];
  rationale: string;
  scores: Record<string, string>;
  matched_keywords: string[];
}

export interface FrontendServiceItem {
  id: string;
  name: string;
  provider: string;
  tags: string[];
  description: string;
  url: string;
  fz152: boolean;
  platform?: string;
  region: string;
}

export interface FrontendServiceResult {
  id: string;
  name: string;
  provider: string;
  tags: string[];
  description: string;
  url: string;
  fz152: boolean;
  platform?: string;
  region: string;
  rationale: string;
  priceScore: number;
  taskMatchScore: number;
  criteriaMatchScore: number;
  pricing_elements: BackendPricingElement[];
}

function mapRegions(regions: string[]): string {
  return regions.join(", ") || "Москва";
}

function hasFz152(tags: string[]): boolean {
  return tags.some((t) => t.includes("152-ФЗ") || t.includes("ФЗ-152"));
}

function scoreFromDict(scores: Record<string, string>, ...keys: string[]): number {
  for (const key of keys) {
    const val = scores[key];
    if (val) {
      const m = val.match(/(\d+)\/10/);
      if (m) return parseInt(m[1], 10);
    }
  }
  return 5;
}

export function toFrontendServiceItem(s: BackendServiceItem): FrontendServiceItem {
  return {
    id: String(s.id),
    name: s.name,
    provider: s.provider,
    tags: [...(s.compliance_tags || [])],
    description: s.description || "",
    url: "",
    fz152: hasFz152(s.compliance_tags || []),
    region: mapRegions(s.regions || []),
  };
}

export function toFrontendServiceResult(r: BackendServiceResult): FrontendServiceResult {
  const tags = [...(r.compliance_tags || [])];
  return {
    id: String(r.id),
    name: r.name,
    provider: r.provider,
    tags,
    description: r.description || "",
    url: "",
    fz152: hasFz152(tags),
    region: mapRegions(r.regions || []),
    rationale: r.rationale,
    priceScore: scoreFromDict(r.scores, "Стоимость", "Цена", "Price"),
    taskMatchScore: scoreFromDict(r.scores, "Соответствие задаче", "Task Match"),
    criteriaMatchScore: scoreFromDict(r.scores, "Соответствие критериям", "Criteria Match", "Соответствие"),
    pricing_elements: r.pricing_elements,
  };
}

export interface Message {
  role: "user" | "assistant";
  text: string;
}

export interface SessionData {
  session_id: string;
  messages: Message[];
  results: FrontendServiceResult[];
}

export interface SSECallbacks {
  onSearchResult: (service: FrontendServiceResult) => void;
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

export async function fetchServices(): Promise<FrontendServiceItem[]> {
  const res = await fetch(`${BASE_URL}/services`);
  if (!res.ok) throw new Error("Failed to fetch services");
  const data: BackendServiceItem[] = await res.json();
  return data.map(toFrontendServiceItem);
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
            const raw: BackendServiceResult = JSON.parse(eventData);
            callbacks.onSearchResult(toFrontendServiceResult(raw));
          } else if (eventType === "token" && eventData) {
            const parsed = JSON.parse(eventData);
            callbacks.onToken(parsed.text ?? parsed);
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

