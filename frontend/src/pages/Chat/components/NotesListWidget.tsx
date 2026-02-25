import { useState, useEffect } from "react";
import { StickyNote, Pin, Trash2, X } from "lucide-react";
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
      // Sort pinned first
      data.sort((a, b) => {
        if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
        return 0;
      });
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

  const handleTogglePin = async (note: Note) => {
    try {
      await notesService.updateNote(note.id, { is_pinned: !note.is_pinned });
      setNotes((prev) =>
        prev
          .map((n) =>
            n.id === note.id ? { ...n, is_pinned: !n.is_pinned } : n,
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

  const handleDelete = async (noteId: string) => {
    try {
      await notesService.deleteNote(noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch (err) {
      console.error("Failed to delete note:", err);
    }
  };

  const renderNoteItem = (note: Note) => (
    <div
      key={note.id}
      className={`${styles.noteItem} ${styles.itemWithActions} ${note.is_pinned ? styles.itemPinned : ""}`}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          className={styles.noteText}
          style={{
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            textOverflow: "ellipsis",
            margin: 0,
            maxWidth: "100%",
            lineHeight: "1.4",
          }}
        >
          {note.is_pinned && (
            <span style={{ marginRight: "4px", fontSize: "10px" }}>📌</span>
          )}
          {note.content}
        </p>
        <span className={styles.noteTime}>
          {new Date(note.created_at).toLocaleDateString("vi-VN")}
        </span>
      </div>

      {/* Action buttons - show on hover */}
      <div className={styles.itemActions}>
        <button
          className={`${styles.itemActionBtn} ${note.is_pinned ? styles.itemActionActive : ""}`}
          onClick={() => handleTogglePin(note)}
          title={note.is_pinned ? "Bỏ ghim" : "Ghim"}
        >
          <Pin size={12} />
        </button>
        <button
          className={`${styles.itemActionBtn} ${styles.itemActionDanger}`}
          onClick={() => handleDelete(note.id)}
          title="Xóa"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );

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
              {notes.slice(0, 3).map((note) => renderNoteItem(note))}
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
                {notes.map((note) => renderNoteItem(note))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
