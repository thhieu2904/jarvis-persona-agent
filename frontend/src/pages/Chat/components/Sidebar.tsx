import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Bot,
  Plus,
  MessageSquare,
  Settings,
  Trash2,
  Loader2,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import styles from "../ChatPage.module.css";
import { useAuthStore } from "../../../stores/authStore";
import { useChatStore } from "../../../stores/chatStore";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(-2)
    .join("")
    .toUpperCase();
}

function groupSessionsByDate(
  sessions: typeof useChatStore.prototype extends never
    ? never
    : ReturnType<typeof useChatStore.getState>["sessions"],
) {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const groups: { label: string; items: typeof sessions }[] = [];
  const todayItems: typeof sessions = [];
  const yesterdayItems: typeof sessions = [];
  const olderItems: typeof sessions = [];

  for (const s of sessions) {
    const d = new Date(s.updated_at || s.created_at);
    if (d.toDateString() === today.toDateString()) todayItems.push(s);
    else if (d.toDateString() === yesterday.toDateString())
      yesterdayItems.push(s);
    else olderItems.push(s);
  }

  if (todayItems.length) groups.push({ label: "Hôm nay", items: todayItems });
  if (yesterdayItems.length)
    groups.push({ label: "Hôm qua", items: yesterdayItems });
  if (olderItems.length) groups.push({ label: "Trước đó", items: olderItems });

  return groups;
}

export default function Sidebar() {
  const { user } = useAuthStore();
  const {
    sessions,
    activeSessionId,
    setActiveSession,
    startNewChat,
    deleteSession,
  } = useChatStore();

  const [collapsed, setCollapsed] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  const sessionGroups = groupSessionsByDate(sessions);

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSessionToDelete(id);
  };

  const confirmDelete = async () => {
    if (!sessionToDelete) return;
    setDeletingId(sessionToDelete);
    await deleteSession(sessionToDelete);
    setDeletingId(null);
    setSessionToDelete(null);
  };

  return (
    <aside
      className={`${styles.sidebar} ${collapsed ? styles.sidebarCollapsed : ""}`}
    >
      <div className={styles.sidebarHeader}>
        <a
          href="/"
          className={styles.headerLeft}
          style={{ textDecoration: "none" }}
        >
          <div className={styles.sidebarLogo}>
            <Bot size={20} />
          </div>
          <span className={styles.sidebarTitle}>JARVIS</span>
        </a>
        <button
          className={styles.collapseBtn}
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? "Mở rộng" : "Thu gọn"}
        >
          {collapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <button
        className={styles.newChatBtn}
        onClick={startNewChat}
        title={collapsed ? "Cuộc trò chuyện mới" : undefined}
      >
        <Plus size={16} />
        <span>Cuộc trò chuyện mới</span>
      </button>

      <div className={styles.sessionList}>
        {sessionGroups.map((group) => (
          <div key={group.label} className={styles.sessionGroup}>
            <div className={styles.sessionGroupLabel}>{group.label}</div>
            {group.items.map((s) => (
              <div
                key={s.id}
                className={`${styles.sessionItem} ${s.id === activeSessionId ? styles.sessionItemActive : ""}`}
                onClick={() => setActiveSession(s.id)}
                title={s.title || "Chat"}
                role="button"
                tabIndex={0}
              >
                <div className={styles.sessionLabel}>
                  <MessageSquare
                    size={14}
                    style={{
                      display: "inline",
                      marginRight: 6,
                      verticalAlign: -2,
                      flexShrink: 0,
                    }}
                  />
                  <span>{s.title || "Cuộc trò chuyện"}</span>
                </div>

                <button
                  className={styles.sessionDeleteBtn}
                  onClick={(e) => handleDeleteClick(e, s.id)}
                  disabled={deletingId === s.id}
                  title="Xóa"
                >
                  {deletingId === s.id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className={styles.sidebarFooter}>
        <Link to="/settings" className={styles.userInfo}>
          <div
            className={styles.userAvatar}
            title={collapsed ? "Cài đặt" : undefined}
          >
            {user ? getInitials(user.full_name) : "?"}
          </div>
          <div>
            <div className={styles.userName}>{user?.full_name}</div>
            <div className={styles.userEmail}>
              <Settings
                size={12}
                style={{
                  display: "inline",
                  verticalAlign: -1,
                  marginRight: 4,
                }}
              />
              Cài đặt
            </div>
          </div>
        </Link>
      </div>

      {/* Delete Confirmation Modal */}
      {sessionToDelete && (
        <div
          className={styles.modalOverlay}
          onClick={() => setSessionToDelete(null)}
        >
          <div
            className={styles.modalContent}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>Xác nhận xóa</div>
            <div className={styles.modalBody}>
              Bạn có chắc chắn muốn xóa cuộc trò chuyện này không? Hành động này
              không thể hoàn tác.
            </div>
            <div className={styles.modalFooter}>
              <button
                className={styles.btnCancel}
                onClick={() => setSessionToDelete(null)}
              >
                Hủy
              </button>
              <button
                className={styles.btnDanger}
                onClick={confirmDelete}
                disabled={deletingId !== null}
              >
                {deletingId !== null ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Trash2 size={14} />
                )}
                Xóa
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
