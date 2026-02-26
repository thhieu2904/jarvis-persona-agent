import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  User,
  Wifi,
  CalendarClock,
  LogOut,
  ChevronRight,
  BookOpen,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import styles from "./SettingsMenu.module.css";

function getInitials(name: string): string {
  if (!name) return "?";
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(-2)
    .join("")
    .toUpperCase();
}

interface MenuItem {
  icon: React.ReactNode;
  label: string;
  path: string;
  separator?: boolean;
}

const MENU_ITEMS: MenuItem[] = [
  {
    icon: <User size={18} />,
    label: "Hồ sơ & Dữ liệu",
    path: "/settings/profile",
  },
  {
    icon: <BookOpen size={18} />,
    label: "Quản lý Kiến thức (RAG)",
    path: "/settings/knowledge-base",
  },
  {
    icon: <Wifi size={18} />,
    label: "Nhà thông minh (IoT)",
    path: "/settings/iot",
  },
  {
    icon: <CalendarClock size={18} />,
    label: "Lịch trình & Lối sống",
    path: "/settings/scheduler",
    separator: true,
  },
];

interface SettingsMenuProps {
  onClose: () => void;
}

export default function SettingsMenu({ onClose }: SettingsMenuProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleNavigate = (path: string) => {
    navigate(path);
    onClose();
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
    onClose();
  };

  return (
    <div className={styles.overlay}>
      <div ref={menuRef} className={styles.menu}>
        {/* User Header */}
        <div className={styles.userHeader}>
          <div className={styles.avatarCircle}>
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt="Avatar"
                className={styles.avatarImg}
              />
            ) : (
              getInitials(user?.full_name || "?")
            )}
          </div>
          <div className={styles.userInfo}>
            <div className={styles.userName}>
              {user?.full_name || "Người dùng"}
            </div>
            <div className={styles.userEmail}>{user?.email || ""}</div>
          </div>
        </div>

        <div className={styles.divider} />

        {/* Menu Items */}
        <nav className={styles.nav}>
          {MENU_ITEMS.map((item) => (
            <div key={item.path}>
              {item.separator && <div className={styles.divider} />}
              <button
                className={styles.menuItem}
                onClick={() => handleNavigate(item.path)}
              >
                <span className={styles.menuIcon}>{item.icon}</span>
                <span className={styles.menuLabel}>{item.label}</span>
                <ChevronRight size={16} className={styles.menuChevron} />
              </button>
            </div>
          ))}
        </nav>

        <div className={styles.divider} />

        {/* Logout */}
        <button className={styles.logoutBtn} onClick={handleLogout}>
          <LogOut size={16} />
          Đăng xuất
        </button>
      </div>
    </div>
  );
}
