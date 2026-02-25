import { useState, useEffect, useCallback, useRef } from "react";
import { Clock, Sun, Moon, Settings, X, Plus, Save } from "lucide-react";
import styles from "../SettingsPage.module.css";
import api from "../../../services/api";

// Interfaces for Routine
interface ScheduleData {
  morning_routine_time: string | null;
  evening_routine_time: string | null;
  morning_routine_prompt: string | null;
  evening_routine_prompt: string | null;
}

interface ToolParam {
  id: string;
  label: string;
  text: string;
}

export default function RoutineConfig() {
  const [schedule, setSchedule] = useState<ScheduleData>({
    morning_routine_time: null,
    evening_routine_time: null,
    morning_routine_prompt: null,
    evening_routine_prompt: null,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [editingPrompt, setEditingPrompt] = useState<
    "morning" | "evening" | null
  >(null);
  const [draftPrompt, setDraftPrompt] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [draftTime, setDraftTime] = useState<string | null>(null);
  const [availableTools, setAvailableTools] = useState<ToolParam[]>([]);

  const fetchScheduleAndTools = useCallback(async () => {
    try {
      const [scheduleRes, toolsRes] = await Promise.all([
        api.get("/agent/routine_schedule"),
        api.get("/agent/available_tools"),
      ]);
      setSchedule(scheduleRes.data);
      setAvailableTools(toolsRes.data);
    } catch (err) {
      console.error("Failed to load routine data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScheduleAndTools();
  }, [fetchScheduleAndTools]);

  const updateSchedule = async (
    type: "morning" | "evening",
    time: string | null,
    promptParams: string | null = null,
  ) => {
    setSaving(true);
    try {
      const finalPrompt =
        promptParams !== null
          ? promptParams
          : schedule[`${type}_routine_prompt`];
      await api.put("/agent/routine_schedule", {
        routine_type: type,
        time: time,
        prompt: finalPrompt,
      });
      setSchedule((prev) => ({
        ...prev,
        [`${type}_routine_time`]: time,
        [`${type}_routine_prompt`]: finalPrompt,
      }));
    } catch (err) {
      console.error("Failed to update routine:", err);
    } finally {
      setSaving(false);
    }
  };

  const openEditPrompt = (type: "morning" | "evening") => {
    setEditingPrompt(type);
    setDraftPrompt(schedule[`${type}_routine_prompt`] || "");
    setDraftTime(
      schedule[`${type}_routine_time`] ||
        (type === "morning" ? "06:00" : "23:00"),
    );
  };

  const savePrompt = async () => {
    if (!editingPrompt) return;
    await updateSchedule(editingPrompt, draftTime, draftPrompt);
    setEditingPrompt(null);
  };

  const handleDisableFromModal = async () => {
    if (!editingPrompt) return;
    await updateSchedule(editingPrompt, null);
    setEditingPrompt(null);
  };

  const insertTag = (textToInsert: string) => {
    const textarea = textareaRef.current;
    if (!textarea) {
      setDraftPrompt(
        (prev) =>
          prev + (prev.endsWith(" ") || prev === "" ? "" : " ") + textToInsert,
      );
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const textBefore = draftPrompt.substring(0, start);
    const textAfter = draftPrompt.substring(end);

    const prefixSpace =
      textBefore.length > 0 &&
      !textBefore.endsWith(" ") &&
      !textBefore.endsWith("\\n")
        ? " "
        : "";
    const insertion = prefixSpace + textToInsert + " ";

    const newText = textBefore + insertion + textAfter;
    setDraftPrompt(newText);

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(
        start + insertion.length,
        start + insertion.length,
      );
    }, 0);
  };

  if (loading) {
    return (
      <div className={styles.card}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "16px",
          }}
        >
          <Clock size={18} className={styles.cardIcon} />
          <h2 className={styles.cardTitle} style={{ margin: 0 }}>
            Báo cáo tự động
          </h2>
        </div>
        <div style={{ color: "var(--text-muted)" }}>
          Đang tải cài đặt báo cáo...
        </div>
      </div>
    );
  }

  return (
    <div
      className={styles.card}
      style={{
        marginBottom: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <h2 className={styles.cardTitle}>
        <Clock size={18} className={styles.cardIcon} /> Báo cáo tự động
      </h2>
      <p
        style={{
          color: "var(--text-muted)",
          marginBottom: "var(--space-md)",
          fontSize: "var(--text-sm)",
        }}
      >
        Lên lịch để JARVIS tự động tổng hợp tin tức, thời tiết và báo cáo mỗi
        ngày.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {/* Morning Routine */}
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-light)",
            borderRadius: "8px",
            padding: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {schedule.morning_routine_time ? (
            <>
              {/* Left side */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  fontWeight: 500,
                  fontSize: "15px",
                  color: "var(--text-primary)",
                }}
              >
                <Sun size={18} style={{ color: "#f59e0b" }} /> Buổi sáng
              </div>

              {/* Right side */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "8px" }}
                >
                  <span
                    style={{
                      fontSize: "13px",
                      color: "var(--text-muted)",
                      fontWeight: 500,
                    }}
                  >
                    Thời gian:
                  </span>
                  <input
                    type="time"
                    style={{
                      background: "var(--bg-input)",
                      border: "1px solid var(--glass-border)",
                      borderRadius: "6px",
                      color: "var(--text-primary)",
                      fontSize: "13px",
                      padding: "4px 8px",
                      width: "110px",
                      outline: "none",
                    }}
                    value={schedule.morning_routine_time || ""}
                    onChange={(e) => updateSchedule("morning", e.target.value)}
                  />
                </div>
                <div
                  onClick={() => updateSchedule("morning", null)}
                  title="Tắt báo cáo"
                  style={{
                    width: "40px",
                    height: "22px",
                    background: "var(--blue-500)",
                    borderRadius: "11px",
                    position: "relative",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  <div
                    style={{
                      width: "18px",
                      height: "18px",
                      background: "white",
                      borderRadius: "50%",
                      position: "absolute",
                      top: "2px",
                      right: "2px",
                      transition: "all 0.2s",
                    }}
                  />
                </div>
                <div
                  style={{
                    width: "1px",
                    height: "20px",
                    background: "var(--border-light)",
                    margin: "0 4px",
                  }}
                ></div>
                <button
                  onClick={() => openEditPrompt("morning")}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "4px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                  title="Cài đặt báo cáo sáng"
                >
                  <Settings size={18} />
                </button>
              </div>
            </>
          ) : (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  fontWeight: 500,
                  fontSize: "15px",
                  color: "var(--text-primary)",
                }}
              >
                <Sun size={18} style={{ color: "#f59e0b" }} /> Buổi sáng
              </div>
              <button
                onClick={() => openEditPrompt("morning")}
                disabled={saving}
                style={{
                  background: "rgba(59, 130, 246, 0.15)",
                  color: "var(--blue-400)",
                  border: "1px solid rgba(59, 130, 246, 0.25)",
                  borderRadius: "6px",
                  padding: "6px 16px",
                  fontSize: "13px",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Bật
              </button>
            </>
          )}
        </div>

        {/* Evening Routine */}
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-light)",
            borderRadius: "8px",
            padding: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {schedule.evening_routine_time ? (
            <>
              {/* Left side */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  fontWeight: 500,
                  fontSize: "15px",
                  color: "var(--text-primary)",
                }}
              >
                <Moon size={18} style={{ color: "#8b5cf6" }} /> Buổi tối
              </div>

              {/* Right side */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                }}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "8px" }}
                >
                  <span
                    style={{
                      fontSize: "13px",
                      color: "var(--text-muted)",
                      fontWeight: 500,
                    }}
                  >
                    Thời gian:
                  </span>
                  <input
                    type="time"
                    style={{
                      background: "var(--bg-input)",
                      border: "1px solid var(--glass-border)",
                      borderRadius: "6px",
                      color: "var(--text-primary)",
                      fontSize: "13px",
                      padding: "4px 8px",
                      width: "110px",
                      outline: "none",
                    }}
                    value={schedule.evening_routine_time || ""}
                    onChange={(e) => updateSchedule("evening", e.target.value)}
                  />
                </div>
                <div
                  onClick={() => updateSchedule("evening", null)}
                  title="Tắt báo cáo"
                  style={{
                    width: "40px",
                    height: "22px",
                    background: "var(--blue-500)",
                    borderRadius: "11px",
                    position: "relative",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  <div
                    style={{
                      width: "18px",
                      height: "18px",
                      background: "white",
                      borderRadius: "50%",
                      position: "absolute",
                      top: "2px",
                      right: "2px",
                      transition: "all 0.2s",
                    }}
                  />
                </div>
                <div
                  style={{
                    width: "1px",
                    height: "20px",
                    background: "var(--border-light)",
                    margin: "0 4px",
                  }}
                ></div>
                <button
                  onClick={() => openEditPrompt("evening")}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "4px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                  title="Cài đặt báo cáo tối"
                >
                  <Settings size={18} />
                </button>
              </div>
            </>
          ) : (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  fontWeight: 500,
                  fontSize: "15px",
                  color: "var(--text-primary)",
                }}
              >
                <Moon size={18} style={{ color: "#8b5cf6" }} /> Buổi tối
              </div>
              <button
                onClick={() => openEditPrompt("evening")}
                disabled={saving}
                style={{
                  background: "rgba(59, 130, 246, 0.15)",
                  color: "var(--blue-400)",
                  border: "1px solid rgba(59, 130, 246, 0.25)",
                  borderRadius: "6px",
                  padding: "6px 16px",
                  fontSize: "13px",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Bật
              </button>
            </>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {editingPrompt && (
        <div
          className={styles.modalOverlay}
          onClick={() => setEditingPrompt(null)}
          style={{ zIndex: 300 }}
        >
          <div
            className={styles.modalContent}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>
                {editingPrompt === "morning" ? (
                  <Sun size={20} style={{ color: "#f59e0b" }} />
                ) : (
                  <Moon size={20} style={{ color: "#8b5cf6" }} />
                )}
                Cài đặt báo cáo {editingPrompt === "morning" ? "sáng" : "tối"}
              </h3>
              <button
                className={styles.closeButton}
                onClick={() => setEditingPrompt(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <div className={styles.field}>
                <label>Thời gian nhận báo cáo (Định dạng 24h)</label>
                <input
                  type="time"
                  value={draftTime || ""}
                  onChange={(e) => setDraftTime(e.target.value)}
                />
              </div>

              <div
                style={{
                  background: "rgba(59, 130, 246, 0.1)",
                  border: "1px solid rgba(59, 130, 246, 0.2)",
                  padding: "12px",
                  borderRadius: "8px",
                  fontSize: "13px",
                  color: "var(--blue-500)",
                  marginBottom: "16px",
                }}
              >
                💡 <strong>Mẹo:</strong> Sử dụng <code>{`{{location}}`}</code>{" "}
                để chèn vị trí hiện tại và <code>{`{{current_date}}`}</code> để
                chèn ngày hôm nay.
              </div>

              <div className={styles.field} style={{ marginBottom: 0 }}>
                <label>Nội dung yêu cầu (Prompt)</label>
                <textarea
                  ref={textareaRef}
                  style={{
                    width: "100%",
                    minHeight: "120px",
                    padding: "10px",
                    borderRadius: "8px",
                    border: "1px solid var(--glass-border)",
                    background: "var(--bg-input)",
                    color: "var(--text-primary)",
                    fontSize: "13px",
                    fontFamily: "inherit",
                    resize: "vertical",
                  }}
                  placeholder={`Nhập chỉ thị yêu cầu báo cáo ${editingPrompt === "morning" ? "sáng" : "tối"}...`}
                  value={draftPrompt}
                  onChange={(e) => setDraftPrompt(e.target.value)}
                />
              </div>

              {/* Tags */}
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "6px",
                  marginTop: "12px",
                }}
              >
                {availableTools.map((tool) => (
                  <button
                    key={`tool-${tool.id}`}
                    onClick={() => insertTag(tool.text)}
                    style={{
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--glass-border)",
                      padding: "4px 8px",
                      borderRadius: "16px",
                      fontSize: "11px",
                      color: "var(--text-secondary)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <Plus size={10} /> {tool.label}
                  </button>
                ))}
              </div>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                paddingTop: "16px",
                borderTop: "1px solid var(--border-light)",
              }}
            >
              {schedule[`${editingPrompt}_routine_time`] ? (
                <button
                  type="button"
                  onClick={handleDisableFromModal}
                  style={{
                    padding: "8px 16px",
                    background: "transparent",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    borderRadius: "8px",
                    cursor: "pointer",
                    color: "var(--error)",
                    fontSize: "14px",
                    fontWeight: 500,
                  }}
                >
                  Tắt báo cáo
                </button>
              ) : (
                <div></div>
              )}

              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  type="button"
                  style={{
                    padding: "8px 16px",
                    background: "transparent",
                    border: "1px solid var(--border-light)",
                    borderRadius: "8px",
                    cursor: "pointer",
                    color: "var(--text-primary)",
                    fontSize: "14px",
                    fontWeight: 500,
                  }}
                  onClick={() => setEditingPrompt(null)}
                >
                  Hủy
                </button>
                <button
                  className={styles.saveBtn}
                  style={{ margin: 0, padding: "8px 16px" }}
                  onClick={savePrompt}
                  disabled={saving || !draftTime}
                >
                  <Save
                    size={14}
                    style={{
                      display: "inline",
                      marginRight: "6px",
                      verticalAlign: "-2px",
                    }}
                  />
                  Lưu cài đặt
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
