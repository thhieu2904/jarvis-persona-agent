import { useState, useEffect } from "react";
import { CheckSquare, X } from "lucide-react";
import styles from "../ChatPage.module.css";
import { tasksService, type Task } from "../../../services/tasks.service";
import { useChatStore } from "../../../stores/chatStore";

export default function TasksWidget() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllModal, setShowAllModal] = useState(false);

  const needsWidgetRefresh = useChatStore((state) => state.needsWidgetRefresh);

  const fetchTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await tasksService.listTasks("pending");
      setTasks(data);
    } catch {
      setError("Không thể tải nhiệm vụ");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [needsWidgetRefresh]);

  return (
    <>
      <div className={`${styles.widget} glass-panel`}>
        <div className={styles.widgetHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckSquare size={16} className={styles.widgetIcon} />
            <h3 className={styles.widgetTitle}>Nhiệm vụ sắp tới</h3>
          </div>
        </div>
        <div className={styles.notesList}>
          {loading ? (
            <div className={styles.noteItem}>Đang tải...</div>
          ) : error ? (
            <div className={styles.noteItem}>
              <span style={{ color: "var(--red)" }}>{error}</span>
              <button onClick={fetchTasks} className={styles.retryBtn}>
                Thử lại
              </button>
            </div>
          ) : tasks.length === 0 ? (
            <div className={styles.noteItem}>Không có nhiệm vụ nào</div>
          ) : (
            <>
              {tasks.slice(0, 3).map((task) => (
                <div key={task.id} className={styles.noteItem}>
                  <p
                    className={styles.noteText}
                    style={{
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      margin: 0,
                      maxWidth: "100%",
                    }}
                  >
                    {task.title}
                  </p>
                  <span className={styles.noteTime}>
                    {task.due_date
                      ? new Date(task.due_date).toLocaleDateString("vi-VN")
                      : "Không có hạn"}
                  </span>
                </div>
              ))}
              {tasks.length > 3 && (
                <button
                  className={styles.btnCancel}
                  style={{
                    width: "100%",
                    marginTop: "4px",
                    fontSize: "12px",
                    padding: "6px",
                  }}
                  onClick={() => setShowAllModal(true)}
                >
                  Xem thêm ({tasks.length - 3})
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {showAllModal && (
        <div
          className={styles.modalOverlay}
          onClick={() => setShowAllModal(false)}
          style={{ zIndex: 1100 }}
        >
          <div
            className={styles.modalContent}
            style={{
              maxWidth: "500px",
              maxHeight: "80vh",
              display: "flex",
              flexDirection: "column",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className={styles.modalHeader}
              style={{ justifyContent: "space-between", marginBottom: "16px" }}
            >
              <span>Tất cả nhiệm vụ</span>
              <button
                onClick={() => setShowAllModal(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  display: "flex",
                }}
              >
                <X size={20} />
              </button>
            </div>
            <div
              className={styles.modalBody}
              style={{
                overflowY: "auto",
                flex: 1,
                paddingRight: "4px",
                marginBottom: 0,
              }}
            >
              <div className={styles.notesList}>
                {tasks.map((task) => (
                  <div key={task.id} className={styles.noteItem}>
                    <p className={styles.noteText} style={{ margin: 0 }}>
                      {task.title}
                    </p>
                    <span className={styles.noteTime}>
                      {task.due_date
                        ? new Date(task.due_date).toLocaleDateString("vi-VN")
                        : "Không có hạn"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
