import api from "./api";
import type {
  ChatRequest,
  ChatResponse,
  ChatSession,
  ChatMessage,
} from "../types/chat";

export const chatService = {
  async sendMessage(data: ChatRequest): Promise<ChatResponse> {
    const res = await api.post<ChatResponse>("/agent/chat", data);
    return res.data;
  },

  async streamMessage(
    data: ChatRequest,
    signal: AbortSignal,
    onEvent: (eventRaw: string) => void,
  ): Promise<void> {
    const API_BASE =
      import.meta.env.VITE_API_URL || "http://localhost:8000/api";
    const token = localStorage.getItem("token");

    const response = await fetch(`${API_BASE}/agent/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
      signal,
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        window.location.href = "/login";
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        // Keep the last partial chunk in the buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.substring(6).trim();
            if (jsonStr) {
              onEvent(jsonStr);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  async uploadImage(file: File): Promise<string> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post<{ url: string }>(
      "/agent/upload_image",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return res.data.url;
  },

  async getSessions(): Promise<ChatSession[]> {
    const res = await api.get<{ data: ChatSession[] }>("/agent/sessions");
    return res.data.data;
  },

  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const res = await api.get<{ data: ChatMessage[] }>(
      `/agent/sessions/${sessionId}/messages`,
    );
    return res.data.data;
  },

  async deleteSession(sessionId: string): Promise<{ message: string }> {
    const res = await api.delete<{ message: string }>(
      `/agent/sessions/${sessionId}`,
    );
    return res.data;
  },
};
