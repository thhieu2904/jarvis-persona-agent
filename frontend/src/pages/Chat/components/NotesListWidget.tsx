import { useState, useEffect } from "react";
import { StickyNote } from "lucide-react";
import styles from "../ChatPage.module.css";
import { notesService, type Note } from "../../../services/notes.service";
import { useChatStore } from "../../../stores/chatStore";

export default function NotesListWidget() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const needsWidgetRefresh = useChatStore((state) => state.needsWidgetRefresh);

  const fetchNotes = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await notesService.listNotes();
      setNotes(data.slice(0, 5)); // Show only latest 5 in the widget
    } catch {
      setError("Không thể tải ghi chú");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotes();
  }, [needsWidgetRefresh]);

  return (
    <div className={`${styles.widget} glass-panel`}>
      <div className={styles.widgetHeader}>
        <StickyNote size={16} className={styles.widgetIcon} />
        <h3 className={styles.widgetTitle}>Ghi chú nhanh</h3>
      </div>
      <div className={styles.notesList}>
        {loading ? (
          <div className={styles.noteItem}>Đang tải...</div>
        ) : error ? (
          <div className={styles.noteItem}>
            <span style={{ color: "var(--red)" }}>{error}</span>
            <button onClick={fetchNotes} className={styles.retryBtn}>
              Thử lại
            </button>
          </div>
        ) : notes.length === 0 ? (
          <div className={styles.noteItem}>Không có ghi chú nào</div>
        ) : (
          notes.map((note) => (
            <div key={note.id} className={styles.noteItem}>
              <p className={styles.noteText}>{note.content}</p>
              <span className={styles.noteTime}>
                {new Date(note.created_at).toLocaleDateString("vi-VN")}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
