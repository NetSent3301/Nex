export interface Message {
  role: "user" | "assistant";
  text: string;
  timestamp?: number;
  image_data?: string;
  image_mime?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export interface SystemMetrics {
  memory: number;
  context_buffer: number;
  agent_status: "online" | "busy" | "offline";
  cpu: number;
}

export type SessionGroup = "today" | "yesterday" | "last7" | "older";

export interface ProviderInfo {
  name: string;
  models: string[];
  configured: boolean;
}
