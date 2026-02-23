import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type KeyboardEvent,
  type ChangeEvent,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Bot,
  Send,
  Wrench,
  ImagePlus,
  X,
  Lightbulb,
  Square,
} from "lucide-react";
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
  const {
    messages,
    isSending,
    error,
    loadSessions,
    sendMessage,
    clearError,
    stopStreaming,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: isSending ? "auto" : "smooth",
    });
  }, [messages, isSending]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight + 2, 200)}px`; // +2 for borders
      textareaRef.current.style.overflowY =
        scrollHeight >= 200 ? "auto" : "hidden";
    }
  }, [input]);

  const handleSend = () => {
    const msg = input.trim();
    if ((!msg && selectedImages.length === 0) || isSending) return;
    const imagesToSend =
      selectedImages.length > 0 ? [...selectedImages] : undefined;
    setInput("");
    setSelectedImages([]);
    sendMessage(msg || "Phân tích ảnh này giúp mình", imagesToSend);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestion = (text: string) => {
    setInput("");
    setSelectedImages([]);
    sendMessage(text);
  };

  const handleImageSelect = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    setSelectedImages((prev) => [...prev, ...files].slice(0, 5)); // Max 5 images
    e.target.value = ""; // Reset so user can re-select same file
  }, []);

  const removeImage = useCallback((index: number) => {
    setSelectedImages((prev) => prev.filter((_, i) => i !== index));
  }, []);

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
                    {msg.role === "assistant" && msg.thoughts && (
                      <details
                        className={styles.toolResults}
                        style={{ marginBottom: msg.content ? "1rem" : "0" }}
                      >
                        <summary className={styles.toolResultsSummary}>
                          <Lightbulb
                            size={12}
                            style={{
                              display: "inline",
                              verticalAlign: -2,
                              marginRight: 4,
                            }}
                          />
                          Quá trình suy nghĩ
                        </summary>
                        <div className={styles.toolResultsList}>
                          <div className={styles.toolResultItem}>
                            <div
                              className={styles.toolResultData}
                              style={{ whiteSpace: "pre-wrap", opacity: 0.8 }}
                            >
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.thoughts}
                              </ReactMarkdown>
                            </div>
                          </div>
                        </div>
                      </details>
                    )}
                    {msg.content && (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    )}
                    {msg.role === "assistant" &&
                      msg.tool_results &&
                      msg.tool_results.length > 0 && (
                        <details
                          className={styles.toolResults}
                          style={{ marginTop: "1rem" }}
                        >
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
                    {msg.role === "assistant" &&
                      isSending &&
                      msg.id === messages[messages.length - 1]?.id && (
                        <div
                          className={styles.typingDots}
                          style={{ padding: "8px 0", margin: 0 }}
                        >
                          <div
                            className={styles.typingDot}
                            style={{ opacity: 0.5 }}
                          />
                          <div
                            className={styles.typingDot}
                            style={{ opacity: 0.5 }}
                          />
                          <div
                            className={styles.typingDot}
                            style={{ opacity: 0.5 }}
                          />
                        </div>
                      )}
                  </div>
                </div>
              ))}

              {/* Removed standalone top Stop button to place it in the input row */}
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
            {/* Image preview strip */}
            {selectedImages.length > 0 && (
              <div className={styles.imagePreviewStrip}>
                {selectedImages.map((file, idx) => (
                  <div key={idx} className={styles.imagePreviewItem}>
                    <img
                      src={URL.createObjectURL(file)}
                      alt={`preview-${idx}`}
                      className={styles.imagePreviewThumb}
                    />
                    <button
                      className={styles.imagePreviewRemove}
                      onClick={() => removeImage(idx)}
                      title="Xóa ảnh"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className={styles.inputRow}>
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
                multiple
                onChange={handleImageSelect}
                style={{ display: "none" }}
              />
              <button
                className={styles.attachBtn}
                onClick={() => fileInputRef.current?.click()}
                disabled={isSending}
                title="Đính kèm ảnh"
              >
                <ImagePlus size={20} />
              </button>
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
              {isSending ? (
                <button
                  className={`${styles.sendBtn} ${styles.stopBtn}`}
                  onClick={() => stopStreaming()}
                  title="Dừng sinh kết quả"
                  style={{ background: "#fee2e2", color: "#ef4444" }}
                >
                  <Square size={20} fill="currentColor" />
                </button>
              ) : (
                <button
                  className={styles.sendBtn}
                  onClick={handleSend}
                  disabled={!input.trim() && selectedImages.length === 0}
                  title="Gửi"
                >
                  <Send size={20} />
                </button>
              )}
            </div>
          </div>
        </div>
      </main>

      <FeaturePanel />
    </div>
  );
}
