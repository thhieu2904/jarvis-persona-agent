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
