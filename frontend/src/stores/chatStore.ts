import { create } from "zustand";
import type { ChatSession, ChatMessage } from "../types/chat";
import { chatService } from "../services/chat.service";

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: ChatMessage[];
  isLoading: boolean;
  isSending: boolean;
  error: string | null;

  loadSessions: () => Promise<void>;
  setActiveSession: (sessionId: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  startNewChat: () => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isLoading: false,
  isSending: false,
  error: null,

  loadSessions: async () => {
    set({ isLoading: true });
    try {
      const sessions = await chatService.getSessions();
      set({ sessions, isLoading: false });
    } catch (err: any) {
      set({ error: "Không thể tải lịch sử chat", isLoading: false });
    }
  },

  setActiveSession: async (sessionId: string) => {
    set({ activeSessionId: sessionId, isLoading: true });
    try {
      const messages = await chatService.getSessionMessages(sessionId);
      set({ messages, isLoading: false });
    } catch {
      // Session may not have a messages endpoint yet - just set the session
      set({ messages: [], isLoading: false });
    }
  },

  sendMessage: async (message: string) => {
    const { activeSessionId, messages } = get();

    // Optimistic: add user message immediately
    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    set({ messages: [...messages, userMsg], isSending: true, error: null });

    try {
      const res = await chatService.sendMessage({
        message,
        session_id: activeSessionId || undefined,
      });

      // Add AI response with tool results
      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: res.response,
        tool_results: res.tool_results || [],
        created_at: new Date().toISOString(),
      };

      const newSessionId = res.session_id;
      const currentMessages = get().messages;

      set({
        messages: [...currentMessages, aiMsg],
        activeSessionId: newSessionId,
        isSending: false,
      });

      // Refresh sessions list (new session might have been created)
      get().loadSessions();
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Gửi tin nhắn thất bại";
      set({ isSending: false, error: msg });
    }
  },

  startNewChat: () => {
    set({ activeSessionId: null, messages: [] });
  },

  clearError: () => set({ error: null }),
}));
