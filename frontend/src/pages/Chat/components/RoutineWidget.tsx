import { useState, useEffect, useCallback, useRef } from "react";
import { Clock, Sun, Moon, X, Settings, Plus, Save } from "lucide-react";
import styles from "../ChatPage.module.css";
import api from "../../../services/api";

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

export default function RoutineWidget() {
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
      <div className={`${styles.widget} ${styles.routineWidget} glass-panel`}>
        <div className={styles.widgetHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Clock size={16} className={styles.widgetIcon} />
            <h3 className={styles.widgetTitle}>Báo cáo tự động</h3>
          </div>
        </div>
        <div className={styles.weatherSkeleton}>
          <div className={styles.skeletonLine} style={{ width: "70%" }} />
          <div className={styles.skeletonLine} style={{ width: "50%" }} />
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`${styles.widget} ${styles.routineWidget} glass-panel`}>
        <div className={styles.widgetHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Clock size={16} className={styles.widgetIcon} />
            <h3 className={styles.widgetTitle}>Báo cáo tự động</h3>
          </div>
        </div>

        <div className={styles.routineList}>
          {/* Morning Routine Widget */}
          <div className={styles.routineItem}>
            {schedule.morning_routine_time ? (
              <>
                <div className={styles.routineItemHeader}>
                  <div className={styles.routineInfo}>
                    <Sun size={14} style={{ color: "#f59e0b" }} />
                    <span className={styles.routineLabel}>Buổi sáng</span>
                  </div>
                  <div className={styles.routineActions}>
                    <button
                      className={styles.settingsBtn}
                      onClick={() => openEditPrompt("morning")}
                      title="Cài đặt báo cáo sáng"
                    >
                      <Settings size={14} />
                    </button>
                  </div>
                </div>

                <div className={styles.routineContent}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--text-muted)",
                        fontWeight: 500,
                      }}
                    >
                      Thời gian:
                    </span>
                    <input
                      type="time"
                      className={styles.routineTimePicker}
                      value={schedule.morning_routine_time || ""}
                      onChange={(e) =>
                        updateSchedule("morning", e.target.value)
                      }
                      style={{
                        padding: "2px 4px",
                        fontSize: "12px",
                        width: "100px",
                      }}
                    />
                  </div>
                  <div
                    className={styles.routineToggleBtn}
                    onClick={() => updateSchedule("morning", null)}
                    title="Tắt báo cáo"
                    style={{
                      width: "36px",
                      height: "20px",
                      background: "var(--blue-500)",
                      borderRadius: "10px",
                      position: "relative",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      style={{
                        width: "16px",
                        height: "16px",
                        background: "white",
                        borderRadius: "50%",
                        position: "absolute",
                        top: "2px",
                        right: "2px",
                        transition: "all 0.2s",
                      }}
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className={styles.routineItemHeader}>
                <div className={styles.routineInfo}>
                  <Sun size={14} style={{ color: "#f59e0b" }} />
                  <span className={styles.routineLabel}>Buổi sáng</span>
                </div>
                <div className={styles.routineActions}>
                  <button
                    className={styles.routineEnableBtn}
                    onClick={() => openEditPrompt("morning")}
                    disabled={saving}
                  >
                    Bật
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Evening Routine Widget */}
          <div className={styles.routineItem}>
            {schedule.evening_routine_time ? (
              <>
                <div className={styles.routineItemHeader}>
                  <div className={styles.routineInfo}>
                    <Moon size={14} style={{ color: "#8b5cf6" }} />
                    <span className={styles.routineLabel}>Buổi tối</span>
                  </div>
                  <div className={styles.routineActions}>
                    <button
                      className={styles.settingsBtn}
                      onClick={() => openEditPrompt("evening")}
                      title="Cài đặt báo cáo tối"
                    >
                      <Settings size={14} />
                    </button>
                  </div>
                </div>

                <div className={styles.routineContent}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--text-muted)",
                        fontWeight: 500,
                      }}
                    >
                      Thời gian:
                    </span>
                    <input
                      type="time"
                      className={styles.routineTimePicker}
                      value={schedule.evening_routine_time || ""}
                      onChange={(e) =>
                        updateSchedule("evening", e.target.value)
                      }
                      style={{
                        padding: "2px 4px",
                        fontSize: "12px",
                        width: "100px",
                      }}
                    />
                  </div>
                  <div
                    className={styles.routineToggleBtn}
                    onClick={() => updateSchedule("evening", null)}
                    title="Tắt báo cáo"
                    style={{
                      width: "36px",
                      height: "20px",
                      background: "var(--blue-500)",
                      borderRadius: "10px",
                      position: "relative",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      style={{
                        width: "16px",
                        height: "16px",
                        background: "white",
                        borderRadius: "50%",
                        position: "absolute",
                        top: "2px",
                        right: "2px",
                        transition: "all 0.2s",
                      }}
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className={styles.routineItemHeader}>
                <div className={styles.routineInfo}>
                  <Moon size={14} style={{ color: "#8b5cf6" }} />
                  <span className={styles.routineLabel}>Buổi tối</span>
                </div>
                <div className={styles.routineActions}>
                  <button
                    className={styles.routineEnableBtn}
                    onClick={() => openEditPrompt("evening")}
                    disabled={saving}
                  >
                    Bật
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className={styles.routineHint}>
          Nhận báo cáo cá nhân hóa qua thư ký Zalo
        </div>
      </div>

      {/* Settings Modal */}
      {editingPrompt && (
        <div
          className={styles.modalOverlay}
          onClick={() => setEditingPrompt(null)}
        >
          <div
            className={styles.modalContent}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                {editingPrompt === "morning" ? (
                  <Sun size={18} style={{ color: "#f59e0b" }} />
                ) : (
                  <Moon size={18} style={{ color: "#8b5cf6" }} />
                )}
                Cài đặt báo cáo {editingPrompt === "morning" ? "sáng" : "tối"}
              </div>
              <button
                className={styles.modalCloseBtn}
                onClick={() => setEditingPrompt(null)}
              >
                <X size={16} />
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.timeSettingGroup}>
                <div className={styles.timeSettingLabel}>
                  <strong>Thời gian nhận báo cáo</strong>
                  <span>Định dạng 24h</span>
                </div>
                <div>
                  <input
                    type="time"
                    className={styles.routineTimePicker}
                    value={draftTime || ""}
                    onChange={(e) => setDraftTime(e.target.value)}
                  />
                </div>
              </div>

              <div className={styles.tooltipBox}>
                💡 <strong>Mẹo:</strong> Sử dụng <code>{`{{location}}`}</code>{" "}
                để chèn vị trí hiện tại và <code>{`{{current_date}}`}</code> để
                chèn ngày hôm nay.
              </div>

              <div className={styles.promptBuilderGroup}>
                <label>Nội dung yêu cầu (Prompt)</label>
                <textarea
                  ref={textareaRef}
                  className={styles.routineTextarea}
                  placeholder={`Nhập chỉ thị yêu cầu báo cáo ${editingPrompt === "morning" ? "sáng" : "tối"}...`}
                  value={draftPrompt}
                  onChange={(e) => setDraftPrompt(e.target.value)}
                />
                <div className={styles.tagContainer}>
                  {availableTools.map((tool) => (
                    <div
                      key={`tool-${tool.id}`}
                      className={styles.toolTag}
                      onClick={() => insertTag(tool.text)}
                    >
                      <Plus size={10} /> {tool.label}
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className={styles.modalFooter}>
              {schedule[`${editingPrompt}_routine_time`] && (
                <button
                  className={styles.routineRemoveBtn}
                  style={{
                    marginRight: "auto",
                    width: "auto",
                    padding: "6px 12px",
                  }}
                  onClick={handleDisableFromModal}
                >
                  Tắt báo cáo
                </button>
              )}
              <button
                className={styles.cancelBtn}
                onClick={() => setEditingPrompt(null)}
              >
                Hủy
              </button>
              <button
                className={styles.savePromptBtn}
                onClick={savePrompt}
                disabled={saving || !draftTime}
              >
                <Save size={14} /> Lưu cài đặt
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
