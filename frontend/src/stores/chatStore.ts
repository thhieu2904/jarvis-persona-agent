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
  needsWidgetRefresh: number;

  loadSessions: () => Promise<void>;
  setActiveSession: (sessionId: string) => Promise<void>;
  sendMessage: (message: string, images?: File[]) => Promise<void>;
  startNewChat: () => void;
  deleteSession: (sessionId: string) => Promise<void>;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isLoading: false,
  isSending: false,
  error: null,
  needsWidgetRefresh: 0,

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

  sendMessage: async (message: string, images?: File[]) => {
    const { activeSessionId, messages } = get();

    // Optimistic: add user message immediately (with local preview)
    const previewContent =
      images && images.length > 0
        ? images.map((f) => `![image](${URL.createObjectURL(f)})`).join("\n") +
          "\n\n" +
          message
        : message;

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: previewContent,
      created_at: new Date().toISOString(),
    };
    set({ messages: [...messages, userMsg], isSending: true, error: null });

    try {
      // 1. Upload images first (if any)
      let imageUrls: string[] | undefined;
      if (images && images.length > 0) {
        imageUrls = await Promise.all(
          images.map((file) => chatService.uploadImage(file)),
        );
      }

      // 2. Send chat request with URLs
      const res = await chatService.sendMessage({
        message,
        session_id: activeSessionId || undefined,
        images: imageUrls,
      });

      // Add AI response with tool results
      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: res.response,
        tool_results: res.tool_results || [],
        tools_used: res.tools_used || [],
        created_at: new Date().toISOString(),
      };

      const newSessionId = res.session_id;
      const currentMessages = get().messages;

      // Replace optimistic user message content with server-saved markdown
      const serverContent =
        imageUrls && imageUrls.length > 0
          ? imageUrls.map((u) => `![image](${u})`).join("\n") + "\n\n" + message
          : message;

      const updatedMessages = currentMessages.map((m) =>
        m.id === userMsg.id ? { ...m, content: serverContent } : m,
      );

      // Determine if we need to refresh widgets based on explicit backend flags
      const toolsUsed = res.tools_used || [];
      const relatedTools = [
        "create_task",
        "update_task",
        "delete_task",
        "create_note",
        "update_note",
        "delete_note",
      ];
      const shouldRefresh = toolsUsed.some((tool) =>
        relatedTools.includes(tool),
      );

      set({
        messages: [...updatedMessages, aiMsg],
        activeSessionId: newSessionId,
        isSending: false,
        ...(shouldRefresh && { needsWidgetRefresh: Date.now() }),
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

  deleteSession: async (sessionId: string) => {
    try {
      await chatService.deleteSession(sessionId);

      const { sessions, activeSessionId } = get();
      const updatedSessions = sessions.filter((s) => s.id !== sessionId);

      set({
        sessions: updatedSessions,
        ...(activeSessionId === sessionId
          ? { activeSessionId: null, messages: [] }
          : {}),
      });
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || "Không thể xóa cuộc trò chuyện",
      });
    }
  },

  clearError: () => set({ error: null }),
}));
