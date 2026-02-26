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
  abortController: AbortController | null;

  loadSessions: () => Promise<void>;
  setActiveSession: (sessionId: string) => Promise<void>;
  sendMessage: (
    message: string,
    images?: File[],
    displayMessage?: string,
  ) => Promise<void>;
  stopStreaming: () => void;
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
  abortController: null,

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

  stopStreaming: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set({ abortController: null, isSending: false });
    }
  },

  sendMessage: async (
    message: string,
    images?: File[],
    displayMessage?: string,
  ) => {
    const { activeSessionId, messages } = get();

    // Optimistic: add user message immediately (with local preview)
    // Use displayMessage (clean user text) if provided, else fall back to full message
    const baseDisplay = displayMessage ?? message;
    const previewContent =
      images && images.length > 0
        ? images.map((f) => `![image](${URL.createObjectURL(f)})`).join("\n") +
          "\n\n" +
          baseDisplay
        : baseDisplay;

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: previewContent,
      created_at: new Date().toISOString(),
    };

    // Create empty AI message container for streaming
    const aiMsgId = `ai-${Date.now()}`;
    const initialAiMsg: ChatMessage = {
      id: aiMsgId,
      role: "assistant",
      content: "",
      tool_results: [],
      tools_used: [],
      thoughts: "",
      created_at: new Date().toISOString(),
    };

    set({
      messages: [...messages, userMsg, initialAiMsg],
      isSending: true,
      error: null,
    });

    const controller = new AbortController();
    set({ abortController: controller });

    try {
      // 1. Upload images first (if any)
      let imageUrls: string[] | undefined;
      if (images && images.length > 0) {
        imageUrls = await Promise.all(
          images.map((file) => chatService.uploadImage(file)),
        );
      }

      // 2. Send stream request with URLs
      await chatService.streamMessage(
        {
          message,
          session_id: activeSessionId || undefined,
          images: imageUrls,
          display_message: displayMessage,
        },
        controller.signal,
        (eventRaw) => {
          try {
            const data = JSON.parse(eventRaw);
            const currentMessages = get().messages;
            const msgIndex = currentMessages.findIndex((m) => m.id === aiMsgId);
            if (msgIndex === -1) return;

            const updatedAiMsg = { ...currentMessages[msgIndex] };

            if (data.type === "thinking") {
              updatedAiMsg.thoughts =
                (updatedAiMsg.thoughts || "") + data.content;
            } else if (data.type === "message") {
              updatedAiMsg.content =
                (updatedAiMsg.content || "") + data.content;
            } else if (data.type === "tool_call") {
              if (data.status === "end") {
                updatedAiMsg.tool_results = [
                  ...(updatedAiMsg.tool_results || []),
                  {
                    tool_name: data.name,
                    tool_args: {},
                    result: data.result || "",
                  },
                ];
                if (!updatedAiMsg.tools_used?.includes(data.name)) {
                  updatedAiMsg.tools_used = [
                    ...(updatedAiMsg.tools_used || []),
                    data.name,
                  ];
                }
              }
            } else if (data.type === "done") {
              set({ activeSessionId: data.session_id });
            } else if (data.type === "error") {
              updatedAiMsg.content =
                (updatedAiMsg.content || "") + data.content;
            }

            const newMessages = [...currentMessages];
            newMessages[msgIndex] = updatedAiMsg;
            set({ messages: newMessages });
          } catch (e) {
            console.error("Stream parse error:", e);
          }
        },
      );

      const serverContent =
        imageUrls && imageUrls.length > 0
          ? imageUrls.map((u) => `![image](${u})`).join("\n") + "\n\n" + message
          : message;

      const currentMessagesFinal = get().messages;
      const updatedMessages = currentMessagesFinal.map((m) =>
        m.id === userMsg.id ? { ...m, content: serverContent } : m,
      );

      // Determine if widget refresh needed based on tools uses
      const aiFinalMsg = updatedMessages.find((m) => m.id === aiMsgId);
      const toolsUsed = aiFinalMsg?.tools_used || [];
      const relatedTools = [
        // Tasks
        "create_task",
        "update_task",
        "delete_task",
        "complete_task",
        // Notes
        "save_quick_note",
        "update_note",
        "delete_note",
        // Calendar
        "create_event",
        "update_event",
        "delete_event",
      ];
      const shouldRefresh = toolsUsed.some((tool) =>
        relatedTools.includes(tool),
      );

      set({
        messages: updatedMessages,
        isSending: false,
        abortController: null,
        ...(shouldRefresh && { needsWidgetRefresh: Date.now() }),
      });

      // Refresh sessions list
      get().loadSessions();
    } catch (err: any) {
      if (err.name === "AbortError") {
        const currentMessages = get().messages;
        const msgIndex = currentMessages.findIndex((m) => m.id === aiMsgId);
        if (msgIndex !== -1) {
          const newMsgs = [...currentMessages];
          newMsgs[msgIndex] = {
            ...newMsgs[msgIndex],
            content: newMsgs[msgIndex].content + "\n\n*[Đã dừng tạo]*",
          };
          set({ messages: newMsgs });
        }
      } else {
        const msg =
          err.response?.data?.detail || err.message || "Gửi tin nhắn thất bại";
        set({ error: msg });
      }
      set({ isSending: false, abortController: null });
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
