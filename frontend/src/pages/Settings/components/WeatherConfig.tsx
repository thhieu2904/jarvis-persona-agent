import { useState } from "react";
import { CloudSun, MapPin, Loader2 } from "lucide-react";
import { useAuthStore } from "../../../stores/authStore";
import styles from "../SettingsPage.module.css";
import api from "../../../services/api";

const WEATHER_CACHE_KEY = "jarvis_weather_cache";

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
  const [locating, setLocating] = useState(false);

  const handleAutoLocate = () => {
    if (!navigator.geolocation) {
      alert("Trình duyệt không hỗ trợ định vị.");
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          // Gọi backend (dùng OpenWeather reverse geocoding) để lấy tên vị trí
          const res = await api.get("/agent/weather", {
            params: { lat: latitude, lon: longitude },
          });
          const data = res.data;
          const locationName = data?.location;

          if (locationName) {
            setDefaultLoc(locationName);

            // Auto-save vào DB để đồng bộ với WeatherWidget
            await updatePreferences({
              ...prefs,
              default_location: locationName,
              weather_cache_ttl: parseInt(cacheTtl, 10) || 1800,
            });

            // Xóa cache weather cũ để Widget tự fetch lại
            localStorage.removeItem(WEATHER_CACHE_KEY);

            setSuccess("Đã xác định và lưu vị trí hiện tại!");
            setTimeout(() => setSuccess(""), 3000);
          } else {
            alert("Không thể xác định tên vị trí từ tọa độ.");
          }
        } catch {
          alert("Lỗi khi lấy thông tin vị trí.");
        } finally {
          setLocating(false);
        }
      },
      () => {
        alert("Lỗi khi lấy tọa độ. Vui lòng kiểm tra quyền truy cập vị trí.");
        setLocating(false);
      },
    );
  };

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
      // Xóa cache weather cũ để Widget fetch lại với setting mới
      localStorage.removeItem(WEATHER_CACHE_KEY);

      setSuccess("Đã lưu cấu hình thời tiết!");
      setTimeout(() => setSuccess(""), 3000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className={styles.card}
      style={{
        marginBottom: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <h2 className={styles.cardTitle}>
        <CloudSun size={18} style={{ color: "var(--primary-color)" }} /> Cấu
        hình thời tiết
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
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "8px",
          }}
        >
          <label
            style={{
              margin: 0,
              minWidth: "150px",
              fontSize: "var(--text-sm)",
              fontWeight: 500,
              color: "var(--text-secondary)",
            }}
          >
            Vị trí mặc định
          </label>
          <div style={{ display: "flex", gap: "8px", flex: 1 }}>
            <input
              style={{
                flex: 1,
                padding: "8px 12px",
                background: "var(--bg-input)",
                border: "1px solid var(--glass-border)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                fontSize: "var(--text-sm)",
                outline: "none",
              }}
              placeholder="VD: Trà Vinh, Hà Nội"
              value={defaultLoc}
              onChange={(e) => setDefaultLoc(e.target.value)}
            />
            <button
              type="button"
              onClick={handleAutoLocate}
              disabled={locating}
              title="Tự động lấy vị trí hiện tại"
              style={{
                width: "36px",
                height: "36px",
                padding: 0,
                cursor: locating ? "wait" : "pointer",
                backgroundColor: "var(--bg-secondary)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {locating ? (
                <Loader2 size={16} className={styles.spinning} />
              ) : (
                <MapPin size={16} />
              )}
            </button>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <label
            style={{
              margin: 0,
              minWidth: "150px",
              fontSize: "var(--text-sm)",
              fontWeight: 500,
              color: "var(--text-secondary)",
            }}
          >
            Thời gian làm mới
          </label>
          <select
            style={{
              flex: 1,
              padding: "8px 12px",
              paddingRight: "32px",
              background: "var(--bg-input)",
              border: "1px solid var(--glass-border)",
              borderRadius: "var(--radius-md)",
              color: "var(--text-primary)",
              fontSize: "var(--text-sm)",
              outline: "none",
              appearance: "none",
              backgroundImage:
                'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20width%3D%2212%22%20height%3D%2212%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%2364748b%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E")',
              backgroundRepeat: "no-repeat",
              backgroundPosition: "right 12px center",
              backgroundSize: "16px",
              cursor: "pointer",
            }}
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

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginTop: "auto",
        }}
      >
        <button
          className={styles.saveBtn}
          style={{ marginTop: 0 }}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Đang lưu..." : "Lưu cấu hình"}
        </button>
      </div>
    </div>
  );
}
