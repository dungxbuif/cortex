import type { DevTokenResponse } from "./types";

export async function getDevToken(): Promise<DevTokenResponse> {
  const response = await fetch("/api/auth/dev-token");
  if (!response.ok) {
    throw new Error(`Token request failed: ${response.status}`);
  }
  return response.json();
}

export async function getHealth(token: string) {
  const response = await fetch("/api/ai/health", {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`);
  }
  return response.json();
}

export async function streamChatCompletion(
  token: string,
  messages: Array<{ role: string; content: string }>,
  onDelta: (delta: string) => void,
  onEvent?: (event: string) => void,
): Promise<void> {
  const response = await fetch("/v1/chat/completions", {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "cortex-orchestrator-router",
      stream: true,
      conversation_id: "single-conversation",
      messages,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat stream failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.split("\n").find((entry) => entry.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") {
        onEvent?.("done");
        continue;
      }
      const json = JSON.parse(payload);
      const delta = json.choices?.[0]?.delta?.content;
      if (delta) onDelta(delta);
      const finishReason = json.choices?.[0]?.finish_reason;
      if (finishReason) onEvent?.(finishReason);
    }
  }
}

function authHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  };
}
