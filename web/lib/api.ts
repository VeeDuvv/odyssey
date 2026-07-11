const API_BASE = "/api";
const API_KEY = "odyssey-dev-key";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// --- Chat ---

export interface ChatResponse {
  content: string;
  agent: string;
  confidence: number;
  sources: string[];
  follow_up_questions: string[];
  metadata: Record<string, unknown>;
}

export async function sendChat(
  query: string,
  enterpriseId?: string,
  altitude: string = "tactical"
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ query, enterprise_id: enterpriseId, altitude }),
  });
}

// --- Knowledge ---

export interface KnowledgeSearchResult {
  query: string;
  count: number;
  results: Record<string, unknown>[];
}

export async function searchKnowledge(q: string): Promise<KnowledgeSearchResult> {
  return request<KnowledgeSearchResult>(`/knowledge/search?q=${encodeURIComponent(q)}`);
}

export async function getTechnology(id: string) {
  return request<Record<string, unknown>>(`/knowledge/technology/${id}`);
}

export async function compareTechnologies(ids: string[]) {
  return request<Record<string, unknown>>(`/knowledge/compare?technologies=${ids.join(",")}`);
}

export async function getGraphStats() {
  return request<Record<string, unknown>>("/knowledge/stats");
}

// --- Enterprise ---

export async function listEnterprises() {
  return request<{ enterprises: import("./types").EnterpriseListItem[]; count: number }>(
    "/enterprise"
  );
}

export async function createEnterprise(data: Record<string, unknown>) {
  return request<{ id: string; name: string; status: string }>("/enterprise", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getEnterprise(id: string) {
  return request<Record<string, unknown>>(`/enterprise/${id}`);
}

export async function updateEnterprise(id: string, data: Record<string, unknown>) {
  return request<Record<string, unknown>>(`/enterprise/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function getEnterpriseAlerts(id: string) {
  return request<Record<string, unknown>>(`/enterprise/${id}/alerts`);
}

export async function getEnterpriseRecommendations(id: string) {
  return request<Record<string, unknown>>(`/enterprise/${id}/recommendations`);
}

export async function getEnterpriseDecisions(id: string) {
  return request<Record<string, unknown>>(`/enterprise/${id}/decisions`);
}

// --- Admin ---

export interface SystemStatus {
  evolution_engine: {
    running: boolean;
    cycle_count: number;
    last_cycle_at: string | null;
    last_gap_report: Record<string, unknown> | null;
    governor: Record<string, unknown>;
  };
  health: {
    total_queries_24h: number;
    avg_quality: number;
    avg_latency_ms: number;
    dead_end_rate: number;
  };
  agents: Record<string, { id: string; type: string; status: string; version: number }>;
  knowledge: {
    total_nodes: number;
    stale_nodes: number;
    avg_confidence: number;
    domain_coverage: Record<string, number>;
  };
  governor: Record<string, unknown>;
}

export async function getSystemStatus(): Promise<SystemStatus> {
  return request<SystemStatus>("/admin/status");
}

export async function triggerEvolutionCycle() {
  return request<Record<string, unknown>>("/admin/evolution/cycle", { method: "POST" });
}

export async function startEvolutionLoop(intervalMinutes: number = 60) {
  return request<Record<string, unknown>>(
    `/admin/evolution/start?interval_minutes=${intervalMinutes}`,
    { method: "POST" }
  );
}

export async function stopEvolutionLoop() {
  return request<Record<string, unknown>>("/admin/evolution/stop", { method: "POST" });
}

export async function getGapReport(windowHours: number = 24) {
  return request<Record<string, unknown>>(`/admin/gaps?window_hours=${windowHours}`);
}

export async function activateKillSwitch() {
  return request<Record<string, unknown>>("/admin/governor/kill-switch/activate", {
    method: "POST",
  });
}

export async function deactivateKillSwitch() {
  return request<Record<string, unknown>>("/admin/governor/kill-switch/deactivate", {
    method: "POST",
  });
}

export async function getAgents() {
  return request<{ agents: Record<string, unknown>[]; total: number }>("/admin/agents");
}

// --- Health ---

export async function getHealth() {
  return request<Record<string, unknown>>("/health".replace("/api", ""));
}
