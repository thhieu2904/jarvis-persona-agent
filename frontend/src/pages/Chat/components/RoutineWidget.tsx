import { useState, useEffect, useCallback } from "react";
import { Clock, Sun, Moon, X } from "lucide-react";
import styles from "../ChatPage.module.css";
import api from "../../../services/api";

interface ScheduleData {
  morning_routine_time: string | null;
  evening_routine_time: string | null;
}

export default function RoutineWidget() {
  const [schedule, setSchedule] = useState<ScheduleData>({
    morning_routine_time: null,
    evening_routine_time: null,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchSchedule = useCallback(async () => {
    try {
      const res = await api.get("/agent/routine_schedule");
      setSchedule(res.data);
    } catch (err) {
      console.error("Failed to load routine schedule:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchedule();
  }, [fetchSchedule]);

  const updateSchedule = async (
    type: "morning" | "evening",
    time: string | null,
  ) => {
    setSaving(true);
    try {
      await api.put("/agent/routine_schedule", {
        routine_type: type,
        time: time,
      });
      setSchedule((prev) => ({
        ...prev,
        [`${type}_routine_time`]: time,
      }));
    } catch (err) {
      console.error("Failed to update routine:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleTimeChange = (type: "morning" | "evening", value: string) => {
    if (value) {
      updateSchedule(type, value);
    }
  };

  const handleDisable = (type: "morning" | "evening") => {
    updateSchedule(type, null);
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
    <div className={`${styles.widget} ${styles.routineWidget} glass-panel`}>
      <div className={styles.widgetHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Clock size={16} className={styles.widgetIcon} />
          <h3 className={styles.widgetTitle}>Báo cáo tự động</h3>
        </div>
      </div>

      <div className={styles.routineList}>
        {/* Morning Routine */}
        <div className={styles.routineItem}>
          <div className={styles.routineInfo}>
            <Sun size={14} style={{ color: "#f59e0b" }} />
            <span className={styles.routineLabel}>Buổi sáng</span>
          </div>
          <div className={styles.routineActions}>
            {schedule.morning_routine_time ? (
              <>
                <input
                  type="time"
                  className={styles.routineTimePicker}
                  value={schedule.morning_routine_time}
                  onChange={(e) => handleTimeChange("morning", e.target.value)}
                  disabled={saving}
                />
                <button
                  className={styles.routineRemoveBtn}
                  onClick={() => handleDisable("morning")}
                  disabled={saving}
                  title="Tắt báo cáo sáng"
                >
                  <X size={12} />
                </button>
              </>
            ) : (
              <button
                className={styles.routineEnableBtn}
                onClick={() => updateSchedule("morning", "06:00")}
                disabled={saving}
              >
                Bật
              </button>
            )}
          </div>
        </div>

        {/* Evening Routine */}
        <div className={styles.routineItem}>
          <div className={styles.routineInfo}>
            <Moon size={14} style={{ color: "#8b5cf6" }} />
            <span className={styles.routineLabel}>Buổi tối</span>
          </div>
          <div className={styles.routineActions}>
            {schedule.evening_routine_time ? (
              <>
                <input
                  type="time"
                  className={styles.routineTimePicker}
                  value={schedule.evening_routine_time}
                  onChange={(e) => handleTimeChange("evening", e.target.value)}
                  disabled={saving}
                />
                <button
                  className={styles.routineRemoveBtn}
                  onClick={() => handleDisable("evening")}
                  disabled={saving}
                  title="Tắt báo cáo tối"
                >
                  <X size={12} />
                </button>
              </>
            ) : (
              <button
                className={styles.routineEnableBtn}
                onClick={() => updateSchedule("evening", "23:00")}
                disabled={saving}
              >
                Bật
              </button>
            )}
          </div>
        </div>
      </div>

      <div className={styles.routineHint}>Nhận báo cáo tự động qua Zalo</div>
    </div>
  );
}
