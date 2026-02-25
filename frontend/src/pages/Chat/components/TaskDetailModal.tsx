import { useState, useEffect } from "react";
import { X, Save, Eye, Edit3 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import styles from "../ChatPage.module.css";
import { tasksService, type Task } from "../../../services/tasks.service";

interface TaskDetailModalProps {
  /** Existing task to view/edit, or null to create new */
  task: Task | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function TaskDetailModal({
  task,
  onClose,
  onSaved,
}: TaskDetailModalProps) {
  const isNew = !task;

  const [title, setTitle] = useState(task?.title || "");
  const [description, setDescription] = useState(task?.description || "");
  const [dueDate, setDueDate] = useState(
    task?.due_date ? task.due_date.split("T")[0] : "",
  );
  const [priority, setPriority] = useState(task?.priority || "medium");
  const [preview, setPreview] = useState(!isNew); // Start in preview for existing tasks
  const [saving, setSaving] = useState(false);

  // Reset state when task prop changes
  useEffect(() => {
    setTitle(task?.title || "");
    setDescription(task?.description || "");
    setDueDate(task?.due_date ? task.due_date.split("T")[0] : "");
    setPriority(task?.priority || "medium");
    setPreview(!isNew);
  }, [task, isNew]);

  const handleSave = async () => {
    if (!title.trim()) return;
    setSaving(true);
    try {
      if (isNew) {
        await tasksService.createTask({
          title: title.trim(),
          description: description.trim(),
          due_date: dueDate || null,
          priority,
        });
      } else {
        await tasksService.updateTask(task.id, {
          title: title.trim(),
          description: description.trim(),
          due_date: dueDate || null,
          priority,
        });
      }
      onSaved();
      onClose();
    } catch (err) {
      console.error("Failed to save task:", err);
    } finally {
      setSaving(false);
    }
  };

  const priorityOptions = [
    { value: "low", label: "Thấp", color: "var(--text-muted)" },
    { value: "medium", label: "Trung bình", color: "#f59e0b" },
    { value: "high", label: "Cao", color: "var(--red)" },
  ];

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
            {isNew ? "Tạo nhiệm vụ mới" : "Chi tiết nhiệm vụ"}
          </span>
          <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
            {/* Toggle Preview/Edit for description */}
            {!isNew && description && (
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
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          {/* Title */}
          <div>
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
              Tiêu đề
            </label>
            {preview ? (
              <div
                style={{
                  fontSize: "var(--text-base)",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  padding: "8px 0",
                }}
              >
                {title || "—"}
              </div>
            ) : (
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Nhập tiêu đề nhiệm vụ..."
                autoFocus={isNew}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  background: "var(--bg-input)",
                  border: "1px solid var(--glass-border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: "var(--text-base)",
                  outline: "none",
                  transition: "border-color 0.15s ease",
                }}
                onFocus={(e) =>
                  (e.target.style.borderColor = "var(--blue-500)")
                }
                onBlur={(e) =>
                  (e.target.style.borderColor = "var(--glass-border)")
                }
              />
            )}
          </div>

          {/* Due date + Priority row */}
          <div style={{ display: "flex", gap: "12px" }}>
            <div style={{ flex: 1 }}>
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
                Hạn chót
              </label>
              {preview ? (
                <div
                  style={{
                    fontSize: "var(--text-sm)",
                    color: "var(--text-secondary)",
                    padding: "8px 0",
                  }}
                >
                  {dueDate
                    ? new Date(dueDate + "T00:00:00").toLocaleDateString(
                        "vi-VN",
                      )
                    : "Không có hạn"}
                </div>
              ) : (
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    background: "var(--bg-input)",
                    border: "1px solid var(--glass-border)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--text-primary)",
                    fontSize: "var(--text-sm)",
                    outline: "none",
                  }}
                />
              )}
            </div>

            <div style={{ flex: 1 }}>
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
                Ưu tiên
              </label>
              {preview ? (
                <div
                  style={{
                    fontSize: "var(--text-sm)",
                    padding: "8px 0",
                    color: priorityOptions.find((p) => p.value === priority)
                      ?.color,
                    fontWeight: 500,
                  }}
                >
                  {priorityOptions.find((p) => p.value === priority)?.label}
                </div>
              ) : (
                <div style={{ display: "flex", gap: "6px" }}>
                  {priorityOptions.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setPriority(opt.value)}
                      style={{
                        flex: 1,
                        padding: "6px 8px",
                        background:
                          priority === opt.value
                            ? `${opt.color}18`
                            : "var(--bg-input)",
                        border: `1px solid ${priority === opt.value ? opt.color : "var(--glass-border)"}`,
                        borderRadius: "var(--radius-sm)",
                        color:
                          priority === opt.value
                            ? opt.color
                            : "var(--text-muted)",
                        fontSize: "12px",
                        fontWeight: priority === opt.value ? 600 : 400,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          <div style={{ flex: 1 }}>
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
              Mô tả
            </label>
            {preview ? (
              <div
                className={styles.messageBubbleBot}
                style={{
                  padding: "12px",
                  borderRadius: "var(--radius-md)",
                  fontSize: "var(--text-sm)",
                  lineHeight: 1.6,
                  minHeight: "60px",
                  maxHeight: "260px",
                  overflowY: "auto",
                  border: "1px solid var(--glass-border)",
                  background: "var(--bg-input)",
                }}
              >
                {description ? (
                  <ReactMarkdown>{description}</ReactMarkdown>
                ) : (
                  <span
                    style={{ color: "var(--text-muted)", fontStyle: "italic" }}
                  >
                    Chưa có mô tả
                  </span>
                )}
              </div>
            ) : (
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Nhập mô tả (hỗ trợ Markdown)..."
                rows={5}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "var(--bg-input)",
                  border: "1px solid var(--glass-border)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: "var(--text-sm)",
                  resize: "vertical",
                  minHeight: "100px",
                  maxHeight: "260px",
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
            )}
            {!preview && (
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  marginTop: "4px",
                }}
              >
                💡 Hỗ trợ Markdown: **đậm**, *nghiêng*, - danh sách, # tiêu đề
              </div>
            )}
          </div>
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
              disabled={saving || !title.trim()}
              style={{
                padding: "8px 16px",
                borderRadius: "var(--radius-md)",
                border: "none",
                background:
                  saving || !title.trim()
                    ? "var(--text-muted)"
                    : "linear-gradient(135deg, var(--blue-600), var(--blue-700))",
                color: "white",
                cursor: saving || !title.trim() ? "not-allowed" : "pointer",
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "var(--text-sm)",
                transition: "all 0.15s ease",
                opacity: saving || !title.trim() ? 0.5 : 1,
              }}
            >
              <Save size={14} />
              {saving ? "Đang lưu..." : isNew ? "Tạo" : "Lưu"}
            </button>
          </div>
        )}

        {/* Edit button in preview mode */}
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
