export type Role = "system" | "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  status?: "idle" | "streaming" | "complete" | "error";
}

export interface DevTokenResponse {
  access_token: string;
  token_type: "bearer";
  user_id: string;
}

export interface StreamEvent {
  id: string;
  label: string;
  detail: string;
  status: "pending" | "running" | "success" | "error";
}

export interface Citation {
  source: string;
  module: "Second Brain" | "Homelab";
  detail: string;
}
