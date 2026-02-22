import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Send, Plus, Settings, MessageSquare, Wrench } from "lucide-react";
import { useChatStore } from "../../stores/chatStore";
import { useAuthStore } from "../../stores/authStore";
import styles from "./ChatPage.module.css";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(-2)
    .join("")
    .toUpperCase();
}

function groupSessionsByDate(
  sessions: typeof useChatStore.prototype extends never
    ? never
    : ReturnType<typeof useChatStore.getState>["sessions"],
) {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const groups: { label: string; items: typeof sessions }[] = [];
  const todayItems: typeof sessions = [];
  const yesterdayItems: typeof sessions = [];
  const olderItems: typeof sessions = [];

  for (const s of sessions) {
    const d = new Date(s.updated_at || s.created_at);
    if (d.toDateString() === today.toDateString()) todayItems.push(s);
    else if (d.toDateString() === yesterday.toDateString())
      yesterdayItems.push(s);
    else olderItems.push(s);
  }

  if (todayItems.length) groups.push({ label: "Hôm nay", items: todayItems });
  if (yesterdayItems.length)
    groups.push({ label: "Hôm qua", items: yesterdayItems });
  if (olderItems.length) groups.push({ label: "Trước đó", items: olderItems });

  return groups;
}

const SUGGESTIONS = [
  "Tuần này mình học gì?",
  "Cho xem điểm học kỳ",
  "Tạo task nộp bài OOP",
  "Ghi note nhanh",
];

export default function ChatPage() {
  const { user } = useAuthStore();
  const {
    sessions,
    activeSessionId,
    messages,
    isSending,
    error,
    loadSessions,
    setActiveSession,
    sendMessage,
    startNewChat,
    clearError,
  } = useChatStore();

  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || isSending) return;
    setInput("");
    sendMessage(msg);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestion = (text: string) => {
    setInput("");
    sendMessage(text);
  };

  const sessionGroups = groupSessionsByDate(sessions);

  return (
    <div className={styles.chatLayout}>
      {/* ── Sidebar ──────────────────────────────────── */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.sidebarLogo}>
            <Bot size={20} />
          </div>
          <span className={styles.sidebarTitle}>JARVIS</span>
        </div>

        <button className={styles.newChatBtn} onClick={startNewChat}>
          <Plus size={16} />
          Cuộc trò chuyện mới
        </button>

        <div className={styles.sessionList}>
          {sessionGroups.map((group) => (
            <div key={group.label} className={styles.sessionGroup}>
              <div className={styles.sessionGroupLabel}>{group.label}</div>
              {group.items.map((s) => (
                <button
                  key={s.id}
                  className={`${styles.sessionItem} ${s.id === activeSessionId ? styles.sessionItemActive : ""}`}
                  onClick={() => setActiveSession(s.id)}
                  title={s.title || "Chat"}
                >
                  <MessageSquare
                    size={14}
                    style={{
                      display: "inline",
                      marginRight: 6,
                      verticalAlign: -2,
                    }}
                  />
                  {s.title || "Cuộc trò chuyện"}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className={styles.sidebarFooter}>
          <Link to="/settings" className={styles.userInfo}>
            <div className={styles.userAvatar}>
              {user ? getInitials(user.full_name) : "?"}
            </div>
            <div>
              <div className={styles.userName}>{user?.full_name}</div>
              <div className={styles.userEmail}>
                <Settings
                  size={12}
                  style={{
                    display: "inline",
                    verticalAlign: -1,
                    marginRight: 4,
                  }}
                />
                Cài đặt
              </div>
            </div>
          </Link>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────── */}
      <main className={styles.chatMain}>
        {/* Messages */}
        <div className={styles.messagesArea}>
          {messages.length === 0 && !isSending ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>
                <Bot size={40} />
              </div>
              <div className={styles.emptyTitle}>
                Xin chào{user ? `, ${user.full_name.split(" ").pop()}` : ""}! 👋
              </div>
              <p style={{ color: "var(--text-muted)" }}>
                Mình là JARVIS, trợ lý AI cá nhân. Hỏi mình bất kỳ điều gì!
              </p>
              <div className={styles.emptySuggestions}>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className={styles.suggestionChip}
                    onClick={() => handleSuggestion(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`${styles.message} ${msg.role === "user" ? styles.messageUser : styles.messageAssistant}`}
                >
                  <div
                    className={`${styles.messageAvatar} ${msg.role === "user" ? styles.messageAvatarUser : styles.messageAvatarBot}`}
                  >
                    {msg.role === "user" ? (
                      user ? (
                        getInitials(user.full_name)
                      ) : (
                        "U"
                      )
                    ) : (
                      <Bot size={16} />
                    )}
                  </div>
                  <div
                    className={`${styles.messageBubble} ${msg.role === "user" ? styles.messageBubbleUser : styles.messageBubbleBot}`}
                  >
                    {msg.role === "assistant" ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    ) : (
                      msg.content
                    )}
                    {/* Tool Results - collapsible */}
                    {msg.role === "assistant" &&
                      msg.tool_results &&
                      msg.tool_results.length > 0 && (
                        <details className={styles.toolResults}>
                          <summary className={styles.toolResultsSummary}>
                            <Wrench
                              size={12}
                              style={{
                                display: "inline",
                                verticalAlign: -2,
                                marginRight: 4,
                              }}
                            />
                            Dữ liệu từ {msg.tool_results.length} tool
                            {msg.tool_results.length > 1 ? "s" : ""}
                          </summary>
                          <div className={styles.toolResultsList}>
                            {msg.tool_results.map((tr, idx) => (
                              <div key={idx} className={styles.toolResultItem}>
                                <div className={styles.toolResultHeader}>
                                  <span className={styles.toolResultName}>
                                    {tr.tool_name}
                                  </span>
                                  {Object.keys(tr.tool_args).length > 0 && (
                                    <span className={styles.toolResultArgs}>
                                      (
                                      {Object.entries(tr.tool_args)
                                        .map(([k, v]) => `${k}: ${v}`)
                                        .join(", ")}
                                      )
                                    </span>
                                  )}
                                </div>
                                <pre className={styles.toolResultData}>
                                  {tr.result}
                                </pre>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                  </div>
                </div>
              ))}

              {isSending && (
                <div className={styles.typingIndicator}>
                  <div
                    className={`${styles.messageAvatar} ${styles.messageAvatarBot}`}
                  >
                    <Bot size={16} />
                  </div>
                  <div className={styles.typingDots}>
                    <div className={styles.typingDot} />
                    <div className={styles.typingDot} />
                    <div className={styles.typingDot} />
                  </div>
                  <span className={styles.typingText}>
                    JARVIS đang suy nghĩ...
                  </span>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className={styles.inputArea}>
          {error && (
            <div className={styles.errorBanner}>
              {error}
              <button className={styles.errorClose} onClick={clearError}>
                ×
              </button>
            </div>
          )}
          <div className={styles.inputWrapper}>
            <textarea
              ref={textareaRef}
              className={styles.inputField}
              placeholder="Nhập tin nhắn... (Shift+Enter để xuống dòng)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isSending}
            />
            <button
              className={styles.sendBtn}
              onClick={handleSend}
              disabled={!input.trim() || isSending}
              title="Gửi"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
