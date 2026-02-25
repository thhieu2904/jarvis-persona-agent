import { useState, useEffect } from "react";
import { X, Save, Eye, Edit3 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import styles from "../ChatPage.module.css";
import { notesService, type Note } from "../../../services/notes.service";

interface NoteDetailModalProps {
  /** Existing note to view/edit, or null to create new */
  note: Note | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function NoteDetailModal({
  note,
  onClose,
  onSaved,
}: NoteDetailModalProps) {
  const isNew = !note;

  const [content, setContent] = useState(note?.content || "");
  const [preview, setPreview] = useState(!isNew);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setContent(note?.content || "");
    setPreview(!isNew);
  }, [note, isNew]);

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      if (isNew) {
        await notesService.createNote({ content: content.trim() });
      } else {
        await notesService.updateNote(note.id, { content: content.trim() });
      }
      onSaved();
      onClose();
    } catch (err) {
      console.error("Failed to save note:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className={styles.modalOverlay}
      onClick={onClose}
      style={{ zIndex: 1200 }}
    >
      <div
        className={styles.modalContent}
        style={{
          maxWidth: "520px",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "16px",
            paddingBottom: "12px",
            borderBottom: "1px solid var(--glass-border)",
          }}
        >
          <span
            style={{
              fontSize: "var(--text-lg)",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            {isNew ? "Ghi chú mới" : "Chi tiết ghi chú"}
          </span>
          <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
            {!isNew && content && (
              <button
                onClick={() => setPreview(!preview)}
                style={{
                  background: "transparent",
                  border: "1px solid var(--glass-border)",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  padding: "4px 8px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "12px",
                  transition: "all 0.15s ease",
                }}
                title={preview ? "Chỉnh sửa" : "Xem trước"}
              >
                {preview ? <Edit3 size={13} /> : <Eye size={13} />}
                {preview ? "Sửa" : "Xem"}
              </button>
            )}
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                display: "flex",
                padding: "4px",
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          <label
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: "var(--text-muted)",
              marginBottom: "4px",
              display: "block",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Nội dung
          </label>
          {preview ? (
            <div
              className={styles.messageBubbleBot}
              style={{
                padding: "12px",
                borderRadius: "var(--radius-md)",
                fontSize: "var(--text-sm)",
                lineHeight: 1.6,
                minHeight: "100px",
                maxHeight: "400px",
                overflowY: "auto",
                border: "1px solid var(--glass-border)",
                background: "var(--bg-input)",
              }}
            >
              {content ? (
                <ReactMarkdown>{content}</ReactMarkdown>
              ) : (
                <span
                  style={{ color: "var(--text-muted)", fontStyle: "italic" }}
                >
                  Chưa có nội dung
                </span>
              )}
            </div>
          ) : (
            <>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Nhập ghi chú (hỗ trợ Markdown)..."
                rows={8}
                autoFocus={isNew}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "var(--bg-input)",
                  border: "1px solid var(--glass-border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: "var(--text-sm)",
                  resize: "vertical",
                  minHeight: "140px",
                  maxHeight: "400px",
                  outline: "none",
                  lineHeight: 1.5,
                  fontFamily: "inherit",
                  transition: "border-color 0.15s ease",
                }}
                onFocus={(e) =>
                  (e.target.style.borderColor = "var(--blue-500)")
                }
                onBlur={(e) =>
                  (e.target.style.borderColor = "var(--glass-border)")
                }
              />
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  marginTop: "4px",
                }}
              >
                💡 Hỗ trợ Markdown: **đậm**, *nghiêng*, - danh sách, # tiêu đề
              </div>
            </>
          )}

          {/* Show created date for existing notes */}
          {!isNew && note?.created_at && (
            <div
              style={{
                fontSize: "11px",
                color: "var(--text-muted)",
                marginTop: "8px",
              }}
            >
              Tạo lúc: {new Date(note.created_at).toLocaleString("vi-VN")}
            </div>
          )}
        </div>

        {/* Footer */}
        {!preview && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "8px",
              marginTop: "16px",
              paddingTop: "12px",
              borderTop: "1px solid var(--glass-border)",
            }}
          >
            <button className={styles.btnCancel} onClick={onClose}>
              Hủy
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !content.trim()}
              style={{
                padding: "8px 16px",
                borderRadius: "var(--radius-md)",
                border: "none",
                background:
                  saving || !content.trim()
                    ? "var(--text-muted)"
                    : "linear-gradient(135deg, var(--blue-600), var(--blue-700))",
                color: "white",
                cursor: saving || !content.trim() ? "not-allowed" : "pointer",
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "var(--text-sm)",
                transition: "all 0.15s ease",
                opacity: saving || !content.trim() ? 0.5 : 1,
              }}
            >
              <Save size={14} />
              {saving ? "Đang lưu..." : isNew ? "Tạo" : "Lưu"}
            </button>
          </div>
        )}

        {preview && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "8px",
              marginTop: "16px",
              paddingTop: "12px",
              borderTop: "1px solid var(--glass-border)",
            }}
          >
            <button
              className={styles.btnCancel}
              onClick={() => setPreview(false)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <Edit3 size={14} />
              Chỉnh sửa
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
