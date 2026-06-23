import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const encoder = new TextEncoder();

describe("Cortex client", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", {
      randomUUID: () => `test-${Math.random().toString(16).slice(2)}`,
    });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/auth/dev-token") {
        return jsonResponse({
          access_token: "token",
          token_type: "bearer",
          user_id: "11111111-1111-1111-1111-111111111111",
        });
      }
      if (url === "/api/ai/health") {
        return jsonResponse({ status: "ok" });
      }
      if (url === "/v1/chat/completions") {
        return new Response(
          new ReadableStream({
            start(controller) {
              controller.enqueue(
                encoder.encode(
                  'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
                ),
              );
              controller.enqueue(
                encoder.encode(
                  'data: {"choices":[{"delta":{"content":"Streamed answer"},"finish_reason":null}]}\n\n',
                ),
              );
              controller.enqueue(encoder.encode('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'));
              controller.enqueue(encoder.encode("data: [DONE]\n\n"));
              controller.close();
            },
          }),
          { status: 200, headers: { "Content-Type": "text/event-stream" } },
        );
      }
      return jsonResponse({}, 404);
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the single chat workspace and module tabs", async () => {
    render(<App />);

    expect(screen.getByText("Cortex")).toBeInTheDocument();
    expect(screen.getByText("Single conversation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Second Brain" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Homelab" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Finance" })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Gateway healthy")).toBeInTheDocument();
    });
  });

  it("sends chat over the OpenAI-compatible stream", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByPlaceholderText("Ask Cortex anything"), "Hello Cortex");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("Streamed answer")).toBeInTheDocument();
    });

    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/chat/completions",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
