import { useState, useEffect, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  GraduationCap,
  LogOut,
  FileText,
  StickyNote,
  CheckSquare,
  Settings as SettingsIcon,
  Eye,
  EyeOff,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { authService } from "../../services/auth.service";
import { tasksService } from "../../services/tasks.service";
import { notesService } from "../../services/notes.service";
import IoTManagementTab from "./components/IoTManagementTab";
import styles from "./SettingsPage.module.css";

function getInitials(name: string): string {
  if (!name) return "?";
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(-2)
    .join("")
    .toUpperCase();
}

export default function SettingsPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [stats, setStats] = useState({ docs: 0, notes: 0, tasks: 0 });
  const [activeTab, setActiveTab] = useState<"profile" | "iot" | "scheduler">(
    "profile",
  );

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [notesRes, tasksRes] = await Promise.all([
          notesService.listNotes(),
          tasksService.listTasks("pending"), // Shows pending tasks count
        ]);
        setStats({ docs: 0, notes: notesRes.length, tasks: tasksRes.length });
      } catch (err) {
        console.error("Failed to fetch user stats", err);
      }
    };
    fetchStats();
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const joinDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("vi-VN")
    : "Gần đây";

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
        <div className={styles.tabsContainer}>
          <button
            className={`${styles.tabButton} ${activeTab === "profile" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("profile")}
          >
            Hồ sơ & Dữ liệu
          </button>
          <button
            className={`${styles.tabButton} ${activeTab === "iot" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("iot")}
          >
            Nhà thông minh (IoT)
          </button>
          {/* Sẵn khung cho tab sau */}
          <button
            className={`${styles.tabButton} ${activeTab === "scheduler" ? styles.activeTab : ""}`}
            onClick={() => setActiveTab("scheduler")}
          >
            Lịch trình & Lối sống
          </button>
        </div>

        {activeTab === "profile" && (
          <>
            <h1 className={styles.pageTitle}>Tổng quan tài khoản</h1>

            <div className={styles.dashboardGrid}>
              {/* ── Left Column: Personal Info ─────────────────────── */}
              <div>
                <div className={styles.card}>
                  <div className={styles.avatarSection}>
                    <div className={styles.avatarCircle}>
                      {user?.avatar_url ? (
                        <img
                          src={user.avatar_url}
                          alt="Avatar"
                          style={{
                            width: "100%",
                            height: "100%",
                            borderRadius: "50%",
                            objectFit: "cover",
                          }}
                        />
                      ) : (
                        getInitials(user?.full_name || "?")
                      )}
                    </div>
                    <div className={styles.userName}>{user?.full_name}</div>
                    <div className={styles.userTenure}>
                      Tham gia từ {joinDate}
                    </div>
                  </div>
                  <ProfileForm />
                </div>
              </div>

              {/* ── Right Column ───────────────────────────────────── */}
              <div>
                {/* Stat Cards */}
                <div className={styles.statsRow}>
                  <div className={styles.statCard}>
                    <div className={styles.statLabel}>
                      <FileText size={14} className={styles.cardIcon} /> Tài
                      liệu RAG
                    </div>
                    <div className={styles.statValue}>{stats.docs}</div>
                  </div>
                  <div className={styles.statCard}>
                    <div className={styles.statLabel}>
                      <StickyNote size={14} className={styles.cardIcon} /> Ghi
                      chú
                    </div>
                    <div className={styles.statValue}>{stats.notes}</div>
                  </div>
                  <div className={styles.statCard}>
                    <div className={styles.statLabel}>
                      <CheckSquare size={14} className={styles.cardIcon} />{" "}
                      Nhiệm vụ
                    </div>
                    <div className={styles.statValue}>{stats.tasks}</div>
                  </div>
                </div>

                {/* School & Sync */}
                <SchoolForm />

                {/* System Settings */}
                <SystemConfig />
              </div>
            </div>
          </>
        )}

        {activeTab === "iot" && <IoTManagementTab />}

        {activeTab === "scheduler" && (
          <div
            className={styles.card}
            style={{ textAlign: "center", padding: "40px" }}
          >
            Tính năng cấu hình Lối sống AI và Thói quen đang được phát triển...
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Form Components ─────────────────────────────────── */

function ProfileForm() {
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
    <form onSubmit={handleSave}>
      {success && <div className={styles.success}>{success}</div>}
      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.field}>
        <label>Họ và tên</label>
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className={styles.field}>
        <label>Email</label>
        <input value={user?.email || ""} disabled />
      </div>
      <div className={styles.field}>
        <label>MSSV</label>
        <input value={user?.student_id || ""} disabled />
      </div>
      <button
        type="submit"
        className={styles.saveBtn}
        disabled={saving}
        style={{ width: "100%" }}
      >
        {saving ? "Đang lưu..." : "Lưu thay đổi"}
      </button>
    </form>
  );
}

function SchoolForm() {
  const [mssv, setMssv] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  // Placeholder sync status
  const isSyncSuccess = true;

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!mssv || !password) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const res = await authService.saveSchoolCredentials(mssv, password);
      setSuccess(res.message || "Kết nối thành công!");
      setPassword("");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Kết nối thất bại. Vui lòng thử lại.");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>
        <GraduationCap size={18} className={styles.cardIcon} />
        Tài khoản trường
        <span className={styles.syncStatus}>
          <span
            className={`${styles.syncDot} ${isSyncSuccess ? styles.syncSuccess : styles.syncError}`}
          />
          {isSyncSuccess ? "Đã đồng bộ" : "Lỗi đồng bộ"}
        </span>
      </h2>
      <p
        style={{
          color: "var(--text-muted)",
          marginBottom: "var(--space-md)",
          fontSize: "var(--text-sm)",
        }}
      >
        Kết nối tài khoản đào tạo để JARVIS có thể tra cứu TKB, điểm số, và lịch
        thi cho bạn.
      </p>

      {success && <div className={styles.success}>✅ {success}</div>}
      {error && <div className={styles.error}>{error}</div>}

      <form
        onSubmit={handleSave}
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "16px",
          alignItems: "end",
        }}
      >
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
            type={showPassword ? "text" : "password"}
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ paddingRight: "40px" }}
          />
          <button
            type="button"
            className={styles.passwordToggle}
            onClick={() => setShowPassword(!showPassword)}
            title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        <div
          style={{
            gridColumn: "1 / -1",
            display: "flex",
            gap: "12px",
            marginTop: "8px",
          }}
        >
          <button
            type="submit"
            className={styles.saveBtn}
            disabled={saving || !mssv || !password}
            style={{ margin: 0 }}
          >
            {saving ? "Đang kiểm tra & kết nối..." : "Kết nối & Đồng bộ ngay"}
          </button>
        </div>
      </form>
    </div>
  );
}

function SystemConfig() {
  const { user, updateAgentConfig, updatePreferences } = useAuthStore();
  const [updating, setUpdating] = useState(false);

  const currentVerbosity =
    (user?.agent_config?.response_detail as string) || "Đầy đủ (Chi tiết)";

  // Weather preferences state
  const prefs = (user?.preferences || {}) as Record<string, unknown>;
  const [defaultLoc, setDefaultLoc] = useState(
    (prefs.default_location as string) || "",
  );
  const [cacheTtl, setCacheTtl] = useState(
    String((prefs.weather_cache_ttl as number) || 1800),
  );
  const [weatherSaving, setWeatherSaving] = useState(false);
  const [weatherSuccess, setWeatherSuccess] = useState("");

  const handleVerbosityChange = async (
    e: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    const newVal = e.target.value;
    setUpdating(true);
    try {
      await updateAgentConfig({
        ...(user?.agent_config || {}),
        response_detail: newVal,
      });
    } finally {
      setUpdating(false);
    }
  };

  const handleSaveWeather = async () => {
    setWeatherSaving(true);
    setWeatherSuccess("");
    try {
      await updatePreferences({
        ...prefs,
        default_location: defaultLoc || undefined,
        weather_cache_ttl: parseInt(cacheTtl, 10) || 1800,
      });
      setWeatherSuccess("Đã lưu cấu hình thời tiết!");
      setTimeout(() => setWeatherSuccess(""), 3000);
    } finally {
      setWeatherSaving(false);
    }
  };

  const ttlOptions = [
    { label: "15 phút", value: "900" },
    { label: "30 phút", value: "1800" },
    { label: "1 giờ", value: "3600" },
    { label: "2 giờ", value: "7200" },
  ];

  return (
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>
        <SettingsIcon size={18} className={styles.cardIcon} /> Hệ thống & Trợ lý
        cá nhân
      </h2>

      <div className={styles.toggleRow}>
        <div>
          <div className={styles.toggleLabel}>Giao diện Tối / Sáng</div>
          <div className={styles.toggleDesc}>
            JARVIS hiện đang mặc định theo Tech Light Mode.
          </div>
        </div>
        <div style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)" }}>
          Light (Mặc định)
        </div>
      </div>

      <div className={styles.toggleRow}>
        <div>
          <div className={styles.toggleLabel}>Ngôn ngữ phản hồi mặc định</div>
          <div className={styles.toggleDesc}>
            Ngôn ngữ JARVIS ưu tiên khi trả lời.
          </div>
        </div>
        <select
          className={styles.field}
          style={{ width: "auto", margin: 0, padding: "6px 12px" }}
          disabled
        >
          <option>Tiếng Việt</option>
        </select>
      </div>

      <div className={styles.toggleRow}>
        <div>
          <div className={styles.toggleLabel}>Độ chi tiết câu trả lời</div>
          <div className={styles.toggleDesc}>
            Chỉnh mức độ dài/ngắn của AI Agent.
          </div>
        </div>
        <select
          className={styles.field}
          style={{
            width: "auto",
            margin: 0,
            padding: "6px 12px",
            opacity: updating ? 0.5 : 1,
            cursor: updating ? "wait" : "pointer",
          }}
          value={currentVerbosity}
          onChange={handleVerbosityChange}
          disabled={updating}
        >
          <option value="Đầy đủ (Chi tiết)">Đầy đủ (Chi tiết)</option>
          <option value="Ngắn gọn (Tóm tắt)">Ngắn gọn (Tóm tắt)</option>
        </select>
      </div>

      {/* ── Weather Settings ───────────────────────────────── */}
      <div
        style={{
          borderTop: "1px solid var(--border-light)",
          margin: "16px 0",
          paddingTop: "16px",
        }}
      >
        <div className={styles.toggleLabel} style={{ marginBottom: 8 }}>
          ☁️ Cấu hình thời tiết
        </div>
        <div className={styles.toggleDesc} style={{ marginBottom: 12 }}>
          Thiết lập vị trí mặc định và thời gian làm mới cho Widget thời tiết &
          AI Agent.
        </div>

        {weatherSuccess && (
          <div className={styles.success} style={{ marginBottom: 8 }}>
            ✅ {weatherSuccess}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            alignItems: "end",
          }}
        >
          <div className={styles.field}>
            <label>Vị trí mặc định</label>
            <input
              placeholder="VD: Trà Vinh, Hà Nội"
              value={defaultLoc}
              onChange={(e) => setDefaultLoc(e.target.value)}
            />
          </div>
          <div className={styles.field}>
            <label>Thời gian làm mới</label>
            <select
              value={cacheTtl}
              onChange={(e) => setCacheTtl(e.target.value)}
              style={{ padding: "8px 12px" }}
            >
              {ttlOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          className={styles.saveBtn}
          onClick={handleSaveWeather}
          disabled={weatherSaving}
          style={{ marginTop: 12, width: "100%" }}
        >
          {weatherSaving ? "Đang lưu..." : "Lưu cấu hình thời tiết"}
        </button>
      </div>
    </div>
  );
}
