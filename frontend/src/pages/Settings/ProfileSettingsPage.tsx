import { useState, type FormEvent } from "react";
import {
  GraduationCap,
  Settings as SettingsIcon,
  Eye,
  EyeOff,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { authService } from "../../services/auth.service";
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

export default function ProfileSettingsPage() {
  const { user } = useAuthStore();

  const joinDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("vi-VN")
    : "Gần đây";

  return (
    <>
      <h1 className={styles.pageTitle}>Hồ sơ & Dữ liệu</h1>

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
              <div className={styles.userTenure}>Tham gia từ {joinDate}</div>
            </div>
            <ProfileForm />
          </div>
        </div>

        {/* ── Right Column ───────────────────────────────────── */}
        <div>
          <SchoolForm />
          <SystemConfig />
        </div>
      </div>
    </>
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
  const { user, updateAgentConfig } = useAuthStore();
  const [updating, setUpdating] = useState(false);

  const currentVerbosity =
    (user?.agent_config?.response_detail as string) || "Đầy đủ (Chi tiết)";

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
        <select className={styles.selectSimple} disabled>
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
          className={styles.selectSimple}
          style={{
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

      <div className={styles.toggleRow}>
        <div>
          <div className={styles.toggleLabel}>
            Cho phép người khác nhắn Zalo
          </div>
          <div className={styles.toggleDesc}>
            Khi bật, bất kỳ ai nhắn tin cho Bot Zalo đều được JARVIS phản hồi
            (dùng khi demo). Khi tắt, chỉ chủ sở hữu mới được phản hồi.
          </div>
        </div>
        <label
          style={{
            position: "relative",
            display: "inline-block",
            width: 44,
            height: 24,
            flexShrink: 0,
          }}
        >
          <input
            type="checkbox"
            checked={!!user?.agent_config?.zalo_public_access}
            onChange={async (e) => {
              setUpdating(true);
              try {
                await updateAgentConfig({
                  ...(user?.agent_config || {}),
                  zalo_public_access: e.target.checked,
                });
              } finally {
                setUpdating(false);
              }
            }}
            disabled={updating}
            style={{
              opacity: 0,
              width: 0,
              height: 0,
              position: "absolute",
            }}
          />
          <span
            style={{
              position: "absolute",
              cursor: updating ? "wait" : "pointer",
              inset: 0,
              backgroundColor: user?.agent_config?.zalo_public_access
                ? "var(--blue-500, #3b82f6)"
                : "#cbd5e1",
              borderRadius: 24,
              transition: "background-color 0.2s",
            }}
          >
            <span
              style={{
                position: "absolute",
                height: 18,
                width: 18,
                left: user?.agent_config?.zalo_public_access ? 22 : 3,
                bottom: 3,
                backgroundColor: "white",
                borderRadius: "50%",
                transition: "left 0.2s",
              }}
            />
          </span>
        </label>
      </div>
    </div>
  );
}
