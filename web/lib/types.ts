export interface Agent {
  id: string;
  name: string;
  type: "core" | "dynamic";
  status: "canary" | "active" | "deprecated" | "retired";
  capabilities: string[];
  knowledge_domains: string[];
  version: number;
  created_at: string;
  last_evolved_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  confidence?: number;
  follow_up_questions?: string[];
  timestamp: Date;
}

export type Altitude = "strategic" | "tactical" | "operational";

export interface DomainCoverage {
  domain: string;
  count: number;
  percentage: number;
}
