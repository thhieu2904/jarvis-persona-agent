import { Outlet } from "react-router-dom";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, LogOut } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import styles from "./SettingsPage.module.css";

export default function SettingsLayout() {
  const { logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className={styles.settingsPage}>
      <header className={styles.header}>
        <Link to="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          Quay lại chat
        </Link>
        <button className={styles.logoutBtn} onClick={handleLogout}>
          <LogOut size={14} style={{ display: "inline", verticalAlign: -2 }} />
          Đăng xuất
        </button>
      </header>
      <div className={styles.content}>
        <Outlet />
      </div>
    </div>
  );
}
