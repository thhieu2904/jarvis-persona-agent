import { useState, useEffect } from "react";
import { CheckSquare } from "lucide-react";
import styles from "../ChatPage.module.css";
import { tasksService, type Task } from "../../../services/tasks.service";
import { useChatStore } from "../../../stores/chatStore";

export default function TasksWidget() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    <div className={`${styles.widget} glass-panel`}>
      <div className={styles.widgetHeader}>
        <CheckSquare size={16} className={styles.widgetIcon} />
        <h3 className={styles.widgetTitle}>Nhiệm vụ sắp tới</h3>
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
          tasks.map((task) => (
            <div key={task.id} className={styles.noteItem}>
              <p className={styles.noteText}>{task.title}</p>
              <span className={styles.noteTime}>
                {task.due_date
                  ? new Date(task.due_date).toLocaleDateString("vi-VN")
                  : "Không có hạn"}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
