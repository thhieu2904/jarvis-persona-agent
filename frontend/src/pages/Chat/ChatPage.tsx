import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Send, Wrench } from "lucide-react";
import { useChatStore } from "../../stores/chatStore";
import { useAuthStore } from "../../stores/authStore";
import Sidebar from "./components/Sidebar";
import FeaturePanel from "./components/FeaturePanel";
import styles from "./ChatPage.module.css";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(-2)
    .join("")
    .toUpperCase();
}

const SUGGESTIONS = [
  "Tuần này mình học gì?",
  "Cho xem điểm học kỳ",
  "Tạo task nộp bài OOP",
  "Ghi note nhanh",
];

export default function ChatPage() {
  const { user } = useAuthStore();
  const { messages, isSending, error, loadSessions, sendMessage, clearError } =
    useChatStore();

  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

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

  return (
    <div className={styles.chatLayout}>
      <Sidebar />

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

      <FeaturePanel />
    </div>
  );
}
