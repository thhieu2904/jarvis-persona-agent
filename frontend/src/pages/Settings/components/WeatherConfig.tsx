import { useState } from "react";
import { useAuthStore } from "../../../stores/authStore";
import styles from "../SettingsPage.module.css";

export default function WeatherConfig() {
  const { user, updatePreferences } = useAuthStore();
  const prefs = (user?.preferences || {}) as Record<string, unknown>;

  const [defaultLoc, setDefaultLoc] = useState(
    (prefs.default_location as string) || "",
  );
  const [cacheTtl, setCacheTtl] = useState(
    String((prefs.weather_cache_ttl as number) || 1800),
  );
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");

  const ttlOptions = [
    { label: "15 phút", value: "900" },
    { label: "30 phút", value: "1800" },
    { label: "1 giờ", value: "3600" },
    { label: "2 giờ", value: "7200" },
  ];

  const handleSave = async () => {
    setSaving(true);
    setSuccess("");
    try {
      await updatePreferences({
        ...prefs,
        default_location: defaultLoc || undefined,
        weather_cache_ttl: parseInt(cacheTtl, 10) || 1800,
      });
      setSuccess("Đã lưu cấu hình thời tiết!");
      setTimeout(() => setSuccess(""), 3000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.card}>
      <h2 className={styles.cardTitle}>
        <span style={{ fontSize: "1.1em" }}>☁️</span> Cấu hình thời tiết
      </h2>
      <p
        style={{
          color: "var(--text-muted)",
          marginBottom: "var(--space-md)",
          fontSize: "var(--text-sm)",
        }}
      >
        Thiết lập vị trí mặc định và thời gian làm mới cho Widget thời tiết & AI
        Agent.
      </p>

      {success && (
        <div className={styles.success} style={{ marginBottom: 12 }}>
          ✅ {success}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "12px",
          alignItems: "start",
        }}
      >
        <div className={styles.field} style={{ marginBottom: 0 }}>
          <label>Vị trí mặc định</label>
          <input
            placeholder="VD: Trà Vinh, Hà Nội"
            value={defaultLoc}
            onChange={(e) => setDefaultLoc(e.target.value)}
          />
        </div>
        <div className={styles.field} style={{ marginBottom: 0 }}>
          <label>Thời gian làm mới</label>
          <select
            value={cacheTtl}
            onChange={(e) => setCacheTtl(e.target.value)}
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
        onClick={handleSave}
        disabled={saving}
        style={{ marginTop: 18 }}
      >
        {saving ? "Đang lưu..." : "Lưu cấu hình"}
      </button>
    </div>
  );
}

