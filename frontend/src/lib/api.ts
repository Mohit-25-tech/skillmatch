import $ from "jquery";
import type { User } from "./types";
let accessToken = "";
let refreshPromise: Promise<User> | null = null;
export function setToken(token: string): void {
  accessToken = token;
}
export async function refreshSession(): Promise<User> {
  if (!refreshPromise)
    refreshPromise = new Promise<User>((resolve, reject) => {
      $.ajax({
        url: "/api/v1/auth/refresh",
        method: "POST",
        xhrFields: { withCredentials: true },
      })
        .done((data) => {
          setToken(data.access_token);
          resolve(data.user);
        })
        .fail(() => reject(new Error("Please sign in to continue.")));
    }).finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  retry = true,
): Promise<T> {
  try {
    return await new Promise<T>((resolve, reject) => {
      const isFile = body instanceof FormData;
      $.ajax({
        url: `/api/v1${path}`,
        method,
        data: body ? (isFile ? body : JSON.stringify(body)) : undefined,
        processData: !isFile,
        contentType: isFile ? false : "application/json",
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        xhrFields: { withCredentials: true },
      })
        .done(resolve)
        .fail((xhr) => reject(xhr));
    });
  } catch (error) {
    const xhr = error as JQuery.jqXHR;
    if (xhr.status === 401 && retry && !path.startsWith("/auth")) {
      await refreshSession();
      return api<T>(path, method, body, false);
    }
    const detail = xhr.responseJSON?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join(". ")
          : xhr.status === 0
            ? "Unable to reach the API. Check that the backend is running."
            : "Something went wrong. Please try again.",
    );
  }
}

/** Streaming uses fetch because EventSource cannot attach a Bearer header. */
export function notificationStream(
  onData: (data: import("./product-types").Notices) => void,
  onState: (state: string) => void,
): () => void {
  const controller = new AbortController();
  let cursor = 0;
  const run = async () => {
    while (!controller.signal.aborted) {
      try {
        const response = await fetch(
          `/api/v1/notifications/stream?after=${cursor}`,
          {
            headers: { Authorization: `Bearer ${accessToken}` },
            signal: controller.signal,
          },
        );
        if (response.status === 401) {
          await refreshSession();
          continue;
        }
        if (!response.ok || !response.body)
          throw new Error("Stream unavailable");
        onState("Connected");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!controller.signal.aborted) {
          const chunk = await reader.read();
          if (chunk.done) break;
          buffer += decoder.decode(chunk.value, { stream: true });
          let boundary: number;
          while ((boundary = buffer.indexOf("\n\n")) >= 0) {
            const frame = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            const line = frame
              .split("\n")
              .find((row) => row.startsWith("data: "));
            if (line) {
              const data = JSON.parse(line.slice(6));
              cursor = data.next_cursor;
              onData(data);
            }
          }
        }
      } catch {
        if (!controller.signal.aborted) onState("Reconnecting");
      }
      if (!controller.signal.aborted)
        await new Promise<void>((resolve) => {
          const timer = setTimeout(resolve, 3000);
          controller.signal.addEventListener(
            "abort",
            () => {
              clearTimeout(timer);
              resolve();
            },
            { once: true },
          );
        });
    }
  };
  void run();
  return () => controller.abort();
}

/** Stream Career Assistant AI responses via SSE */
export function aiChatStream(
  message: string,
  onEvent: (data: { type: "tool" | "token" | "done"; content?: string; tools?: any[]; citations?: string[] }) => void,
): () => void {
  const controller = new AbortController();
  const run = async () => {
    try {
      const response = await fetch(
        `/api/v1/ai/chat/stream?message=${encodeURIComponent(message)}`,
        {
          headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
          signal: controller.signal,
        },
      );
      if (response.status === 401) {
        await refreshSession();
        return;
      }
      if (!response.ok || !response.body) throw new Error("AI stream unavailable");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!controller.signal.aborted) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        let boundary: number;
        while ((boundary = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const line = frame.split("\n").find((row) => row.startsWith("data: "));
          if (line) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch {
              // Ignore non-json chunk
            }
          }
        }
      }
    } catch (err: any) {
      if (!controller.signal.aborted) {
        onEvent({ type: "error" as any, content: (err as Error)?.message || "AI service timeout or connection error" });
      }
    }
  };
  void run();
  return () => controller.abort();
}
