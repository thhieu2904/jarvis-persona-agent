import { useState, useEffect } from "react";
import { CheckSquare, Pin, Trash2, X, Plus } from "lucide-react";
import styles from "../ChatPage.module.css";
import { tasksService, type Task } from "../../../services/tasks.service";
import { useChatStore } from "../../../stores/chatStore";
import TaskDetailModal from "./TaskDetailModal";

export default function TasksWidget() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllModal, setShowAllModal] = useState(false);
  const [completingIds, setCompletingIds] = useState<Set<string>>(new Set());
  const [detailTask, setDetailTask] = useState<Task | null | undefined>(
    undefined,
  );
  // undefined = closed, null = create new, Task = view/edit existing

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

  const handleComplete = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    setCompletingIds((prev) => new Set(prev).add(taskId));
    try {
      await tasksService.updateTask(taskId, { status: "done" });
      setTimeout(() => {
        setTasks((prev) => prev.filter((t) => t.id !== taskId));
        setCompletingIds((prev) => {
          const next = new Set(prev);
          next.delete(taskId);
          return next;
        });
      }, 600);
    } catch (err) {
      console.error("Failed to complete task:", err);
      setCompletingIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    }
  };

  const handleTogglePin = async (e: React.MouseEvent, task: Task) => {
    e.stopPropagation();
    try {
      await tasksService.updateTask(task.id, { is_pinned: !task.is_pinned });
      setTasks((prev) =>
        prev
          .map((t) =>
            t.id === task.id ? { ...t, is_pinned: !t.is_pinned } : t,
          )
          .sort((a, b) => {
            if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
            return 0;
          }),
      );
    } catch (err) {
      console.error("Failed to toggle pin:", err);
    }
  };

  const handleDelete = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    try {
      await tasksService.deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err) {
      console.error("Failed to delete task:", err);
    }
  };

  const renderTaskItem = (task: Task) => {
    const isCompleting = completingIds.has(task.id);

    return (
      <div
        key={task.id}
        className={`${styles.noteItem} ${styles.itemWithActions} ${isCompleting ? styles.itemCompleting : ""} ${task.is_pinned ? styles.itemPinned : ""}`}
        onClick={() => setDetailTask(task)}
        style={{ cursor: "pointer" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
            flex: 1,
            minWidth: 0,
          }}
        >
          {/* Checkbox */}
          <button
            className={styles.checkboxBtn}
            onClick={(e) => handleComplete(e, task.id)}
            title="Đánh dấu hoàn thành"
            disabled={isCompleting}
          >
            <div
              className={`${styles.checkbox} ${isCompleting ? styles.checkboxChecked : ""}`}
            >
              {isCompleting && <span>✓</span>}
            </div>
          </button>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p
              className={styles.noteText}
              style={{
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                margin: 0,
                maxWidth: "100%",
                textDecoration: isCompleting ? "line-through" : "none",
                opacity: isCompleting ? 0.5 : 1,
                transition: "all 0.3s ease",
              }}
            >
              {task.is_pinned && (
                <span style={{ marginRight: "4px", fontSize: "10px" }}>📌</span>
              )}
              {task.title}
            </p>
            <span className={styles.noteTime}>
              {task.due_date
                ? new Date(task.due_date).toLocaleDateString("vi-VN")
                : "Không có hạn"}
            </span>
          </div>
        </div>

        {/* Action buttons - show on hover */}
        <div className={styles.itemActions}>
          <button
            className={`${styles.itemActionBtn} ${task.is_pinned ? styles.itemActionActive : ""}`}
            onClick={(e) => handleTogglePin(e, task)}
            title={task.is_pinned ? "Bỏ ghim" : "Ghim"}
          >
            <Pin size={12} />
          </button>
          <button
            className={`${styles.itemActionBtn} ${styles.itemActionDanger}`}
            onClick={(e) => handleDelete(e, task.id)}
            title="Xóa"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>
    );
  };

  return (
    <>
      <div className={`${styles.widget} glass-panel`}>
        <div className={styles.widgetHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckSquare size={16} className={styles.widgetIcon} />
            <h3 className={styles.widgetTitle}>Nhiệm vụ sắp tới</h3>
          </div>
          <button
            className={styles.weatherLocationBtn}
            onClick={() => setDetailTask(null)}
            title="Thêm nhiệm vụ mới"
          >
            <Plus size={14} />
          </button>
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
              {tasks.slice(0, 3).map((task) => renderTaskItem(task))}
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

      {/* "See all" modal */}
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
                {tasks.map((task) => renderTaskItem(task))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Task Detail Modal (create / view / edit) */}
      {detailTask !== undefined && (
        <TaskDetailModal
          task={detailTask}
          onClose={() => setDetailTask(undefined)}
          onSaved={fetchTasks}
        />
      )}
    </>
  );
}
