import { useState, useEffect } from "react";
import { StickyNote, X } from "lucide-react";
import styles from "../ChatPage.module.css";
import { notesService, type Note } from "../../../services/notes.service";
import { useChatStore } from "../../../stores/chatStore";

export default function NotesListWidget() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllModal, setShowAllModal] = useState(false);

  const needsWidgetRefresh = useChatStore((state) => state.needsWidgetRefresh);

  const fetchNotes = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await notesService.listNotes();
      setNotes(data);
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
    <>
      <div className={`${styles.widget} glass-panel`}>
        <div className={styles.widgetHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <StickyNote size={16} className={styles.widgetIcon} />
            <h3 className={styles.widgetTitle}>Ghi chú nhanh</h3>
          </div>
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
            <>
              {notes.slice(0, 3).map((note) => (
                <div key={note.id} className={styles.noteItem}>
                  <p className={styles.noteText}>{note.content}</p>
                  <span className={styles.noteTime}>
                    {new Date(note.created_at).toLocaleDateString("vi-VN")}
                  </span>
                </div>
              ))}
              {notes.length > 3 && (
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
                  Xem thêm ({notes.length - 3})
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
              <span>Tất cả ghi chú</span>
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
                {notes.map((note) => (
                  <div key={note.id} className={styles.noteItem}>
                    <p className={styles.noteText}>{note.content}</p>
                    <span className={styles.noteTime}>
                      {new Date(note.created_at).toLocaleDateString("vi-VN")}
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
