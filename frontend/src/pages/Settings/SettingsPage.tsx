import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, User, GraduationCap, LogOut } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { authService } from "../../services/auth.service";
import styles from "./SettingsPage.module.css";

type Tab = "profile" | "school";

export default function SettingsPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("profile");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className={styles.settingsPage}>
      <aside className={styles.sidebar}>
        <Link to="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          Quay lại chat
        </Link>

        <nav className={styles.nav}>
          <button
            className={`${styles.navItem} ${tab === "profile" ? styles.navItemActive : ""}`}
            onClick={() => setTab("profile")}
          >
            <User size={16} /> Hồ sơ
          </button>
          <button
            className={`${styles.navItem} ${tab === "school" ? styles.navItemActive : ""}`}
            onClick={() => setTab("school")}
          >
            <GraduationCap size={16} /> Tài khoản trường
          </button>
        </nav>

        <button className={styles.logoutBtn} onClick={handleLogout}>
          <LogOut
            size={14}
            style={{ display: "inline", verticalAlign: -2, marginRight: 6 }}
          />
          Đăng xuất
        </button>
      </aside>

      <div className={styles.content}>
        {tab === "profile" && <ProfileSection />}
        {tab === "school" && <SchoolSection />}
      </div>
    </div>
  );
}

/* ── Profile Section ─────────────────────────────────── */
function ProfileSection() {
  const { user } = useAuthStore();
  const [name, setName] = useState(user?.full_name || "");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await authService.updateProfile({ full_name: name } as any);
      setSuccess("Cập nhật thành công!");
      // Update local storage
      const stored = localStorage.getItem("user");
      if (stored) {
        const u = JSON.parse(stored);
        u.full_name = name;
        localStorage.setItem("user", JSON.stringify(u));
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Cập nhật thất bại");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Hồ sơ cá nhân</h2>

      {success && <div className={styles.success}>{success}</div>}
      {error && <div className={styles.error}>{error}</div>}

      <form className={styles.card} onSubmit={handleSave}>
        <div className={styles.field}>
          <label>Họ và tên</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label>Email</label>
          <input value={user?.email || ""} disabled style={{ opacity: 0.5 }} />
        </div>
        <div className={styles.field}>
          <label>MSSV</label>
          <input
            value={user?.student_id || ""}
            disabled
            style={{ opacity: 0.5 }}
          />
        </div>
        <button type="submit" className={styles.saveBtn} disabled={saving}>
          {saving ? "Đang lưu..." : "Lưu thay đổi"}
        </button>
      </form>
    </div>
  );
}

/* ── School Credentials Section ──────────────────────── */
function SchoolSection() {
  const [mssv, setMssv] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!mssv || !password) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const res = await authService.saveSchoolCredentials(mssv, password);
      setSuccess(res.message || "Kết nối thành công!");
      setPassword(""); // Clear password after save
    } catch (err: any) {
      setError(err.response?.data?.detail || "Kết nối thất bại");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Tài khoản trường</h2>
      <p
        style={{
          color: "var(--text-muted)",
          marginBottom: "var(--space-lg)",
          fontSize: "var(--text-sm)",
        }}
      >
        Kết nối tài khoản đào tạo để JARVIS có thể tra cứu TKB, điểm số, và lịch
        thi cho bạn. Thông tin được mã hóa an toàn.
      </p>

      {success && <div className={styles.success}>✅ {success}</div>}
      {error && <div className={styles.error}>{error}</div>}

      <form className={styles.card} onSubmit={handleSave}>
        <div className={styles.field}>
          <label>MSSV</label>
          <input
            placeholder="110122xxx"
            value={mssv}
            onChange={(e) => setMssv(e.target.value)}
            required
          />
        </div>
        <div className={styles.field}>
          <label>Mật khẩu đào tạo</label>
          <input
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button
          type="submit"
          className={styles.saveBtn}
          disabled={saving || !mssv || !password}
        >
          {saving ? "Đang kết nối..." : "Kết nối tài khoản"}
        </button>
      </form>
    </div>
  );
}
