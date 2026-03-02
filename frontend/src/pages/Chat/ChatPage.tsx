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
  Paperclip,
  FileText,
  Loader2,
  X,
  Lightbulb,
  Square,
  Mic,
} from "lucide-react";
import { useChatStore } from "../../stores/chatStore";
import { useAuthStore } from "../../stores/authStore";
import { knowledgeService } from "../../services/knowledge.service";
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

// Render tool result: convert ![...](url) → clickable link, rest in <pre>
function ToolResultRenderer({
  result,
  className,
}: {
  result: string;
  className: string;
}) {
  const imageRegex = /!\[.*?\]\((https?:\/\/[^)]+)\)/g;
  const imgs: string[] = [];
  let match;
  while ((match = imageRegex.exec(result)) !== null) {
    imgs.push(match[1]);
  }
  const textOnly = result.replace(/!\[.*?\]\(https?:\/\/[^)]+\)\n?/g, "").trim();
  return (
    <>
      {imgs.map((url, i) => (
        <a
          key={i}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ display: "block", fontSize: "11px", wordBreak: "break-all", marginBottom: "4px" }}
        >
          🖼 {url}
        </a>
      ))}
      {textOnly && <pre className={className}>{textOnly}</pre>}
    </>
  );
}

const SUGGESTIONS = [
  "Tạo ảnh minh họa cho khái niệm OOP", // Image Gen tool
  "Tìm tin tức công nghệ mới nhất hôm nay", // Web Search tool
  // "Giải thích chi tiết về tính đa hình", // RAG / Academic tool
  "Tóm tắt lịch học tuần này của mình", // Schedule / User Data
  "Phân tích hệ thống qua ảnh upload", // Vision
];

interface AttachedDoc {
  file: File;
  text?: string;
  storage_path?: string;
  safe_file_name?: string; // secure_filename() result from backend
  isLoading: boolean;
  error?: string;
}

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
  const [interimInput, setInterimInput] = useState("");
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [attachedDocs, setAttachedDocs] = useState<AttachedDoc[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debounceRef = useRef<boolean>(false);

  const resetSilenceTimeout = useCallback(() => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
    }
    // Auto stop if silence for 3 seconds
    silenceTimeoutRef.current = setTimeout(() => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // ignore
        }
      }
      setIsListening(false);
      setInterimInput(""); // Clear interim on stop
    }, 3000);
  }, []);

  useEffect(() => {
    // Initialize SpeechRecognition
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "vi-VN";

      recognition.onresult = (event: any) => {
        let finalTranscript = "";
        let currentInterim = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            currentInterim += event.results[i][0].transcript;
          }
        }

        setInterimInput(currentInterim);

        if (finalTranscript) {
          setInput((prev) => {
            const separator = prev && !prev.endsWith(" ") ? " " : "";
            return prev + separator + finalTranscript;
          });
        }
        resetSilenceTimeout();
      };

      recognition.onerror = (event: any) => {
        if (event.error !== "no-speech" && event.error !== "aborted") {
          console.error("Speech recognition error:", event.error);
        }
        if (event.error === "not-allowed") {
          alert(
            "Vui lòng cấp quyền sử dụng Micro cho trình duyệt để dùng tính năng này.",
          );
        }
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
        setIsListening(false);
        setInterimInput("");
      };

      recognition.onend = () => {
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
        setIsListening(false);
        setInterimInput("");
      };

      recognitionRef.current = recognition;
    } else {
      setSpeechSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // ignore
        }
      }
      if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
    };
  }, [resetSilenceTimeout]);

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
    // If we have an interim input but no final input, just clear it mostly or append
    const textToSend =
      input.trim() + (interimInput ? " " + interimInput.trim() : "");
    const msg = textToSend.trim();

    const validDocs = attachedDocs.filter(
      (d) => !d.isLoading && !d.error && d.text,
    );

    if (
      (!msg && selectedImages.length === 0 && validDocs.length === 0) ||
      isSending
    )
      return;

    // Build context payload for RAG
    let finalMessage = msg;
    let displayMessage: string | undefined;
    if (validDocs.length > 0) {
      const docContext = validDocs
        .map(
          (d) =>
            // Use safe_file_name (ASCII, no spaces) so the agent can locate the file on storage
            `[SYS_FILE: ${d.safe_file_name || d.file.name}${d.storage_path ? ` - Path: ${d.storage_path}` : ""}]\n<document_content>\n${d.text}\n</document_content>`,
        )
        .join("\n\n");
      finalMessage = `${docContext}\n\n${msg || "Hãy phân tích tài liệu này giúp mình nhé."}`;
      // Clean display: show doc names + user text (no raw document dump)
      const docNames = validDocs.map((d) => `📎 ${d.file.name}`).join("  ");
      displayMessage = msg ? `${docNames}\n${msg}` : docNames;
    }

    const imagesToSend =
      selectedImages.length > 0 ? [...selectedImages] : undefined;

    setInput("");
    setInterimInput("");
    setSelectedImages([]);
    setAttachedDocs([]);

    sendMessage(finalMessage || "Phân tích ảnh này giúp mình", imagesToSend, displayMessage);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestion = (text: string) => {
    setInput("");
    setInterimInput("");
    setSelectedImages([]);
    setAttachedDocs([]);
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

  const handleDocSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    // Process up to 3 docs at a time
    const newDocs: AttachedDoc[] = files
      .slice(0, 3)
      .map((f) => ({ file: f, isLoading: true }));
    setAttachedDocs((prev) => [...prev, ...newDocs].slice(0, 3));
    e.target.value = ""; // Reset input

    for (const doc of newDocs) {
      try {
        const res = await knowledgeService.extractText(doc.file);
        setAttachedDocs((prev) =>
          prev.map((d) =>
            d.file.name === doc.file.name
              ? {
                  ...d,
                  isLoading: false,
                  text: res.text,
                  storage_path: res.metadata?.storage_path,
                  safe_file_name: res.metadata?.file_name,
                }
              : d,
          ),
        );
      } catch (err: any) {
        setAttachedDocs((prev) =>
          prev.map((d) =>
            d.file.name === doc.file.name
              ? {
                  ...d,
                  isLoading: false,
                  error: err.response?.data?.detail || "Lỗi đọc file",
                }
              : d,
          ),
        );
      }
    }
  };

  const removeDoc = useCallback((index: number) => {
    setAttachedDocs((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current || debounceRef.current) return;

    // Anti-spam debounce
    debounceRef.current = true;
    setTimeout(() => {
      debounceRef.current = false;
    }, 500);

    if (isListening) {
      if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
      recognitionRef.current.stop();
      setIsListening(false);
      setInterimInput("");
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
        resetSilenceTimeout();
      } catch (err) {
        console.error("Error starting speech recognition:", err);
      }
    }
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
                                <ToolResultRenderer
                                  result={tr.result}
                                  className={styles.toolResultData}
                                />
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
            {/* Document preview strip */}
            {attachedDocs.length > 0 && (
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  padding: "8px 12px",
                  overflowX: "auto",
                  borderBottom: "1px solid var(--border-color, #e5e7eb)",
                }}
              >
                {attachedDocs.map((doc, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "var(--hover-bg, #f3f4f6)",
                      padding: "6px 10px",
                      borderRadius: "8px",
                      fontSize: "13px",
                      border: doc.error
                        ? "1px solid #ef4444"
                        : "1px solid transparent",
                    }}
                  >
                    {doc.isLoading ? (
                      <Loader2
                        size={14}
                        style={{ animation: "spin 1s linear infinite" }}
                      />
                    ) : (
                      <FileText
                        size={14}
                        color={doc.error ? "#ef4444" : "#2563eb"}
                      />
                    )}
                    <span
                      style={{
                        maxWidth: "140px",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        color: doc.error ? "#ef4444" : "var(--text-color)",
                      }}
                      title={doc.error || doc.file.name}
                    >
                      {doc.error || doc.file.name}
                    </span>
                    <button
                      onClick={() => removeDoc(idx)}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        padding: 2,
                        display: "flex",
                        color: "var(--text-secondary)",
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className={styles.inputRow}>
              {/* Hidden file input for documents */}
              <input
                ref={docInputRef}
                type="file"
                accept=".txt,.md,.pdf,.docx"
                multiple
                onChange={handleDocSelect}
                style={{ display: "none" }}
              />
              <button
                className={styles.attachBtn}
                onClick={() => docInputRef.current?.click()}
                disabled={isSending}
                title="Đính kèm tài liệu (PDF, DOCX, TXT, MD)"
              >
                <Paperclip size={20} />
              </button>

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
                value={
                  input +
                  (interimInput ? (input ? " " : "") + interimInput : "")
                }
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={isSending}
              />
              {speechSupported && (
                <button
                  className={`${styles.micBtn} ${isListening ? styles.micBtnRecording : ""}`}
                  onClick={toggleListening}
                  disabled={isSending}
                  title={
                    isListening
                      ? "Ngừng thu âm (sẽ tự động dừng nếu không có tiếng)"
                      : "Nhập bằng giọng nói"
                  }
                >
                  <Mic size={20} />
                </button>
              )}
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
                  disabled={
                    !input.trim() &&
                    selectedImages.length === 0 &&
                    attachedDocs.every((d) => d.isLoading || d.error)
                  }
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
