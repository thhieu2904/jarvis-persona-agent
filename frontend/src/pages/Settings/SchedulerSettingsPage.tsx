import { CalendarClock } from "lucide-react";
import styles from "./SettingsPage.module.css";
import RoutineConfig from "./components/RoutineConfig";
import WeatherConfig from "./components/WeatherConfig";

export default function SchedulerSettingsPage() {
  return (
    <>
      <h1 className={styles.pageTitle}>Lịch trình & Lối sống</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "24px",
          alignItems: "stretch",
          marginBottom: "24px",
        }}
      >
        {/* Routine Config Section */}
        <RoutineConfig />

        {/* Weather Config Section */}
        <WeatherConfig />
      </div>

      {/* Placeholder for future features */}
      <div
        className={styles.card}
        style={{
          textAlign: "center",
          padding: "40px",
          color: "var(--text-muted)",
        }}
      >
        <CalendarClock size={36} style={{ marginBottom: 12, opacity: 0.4 }} />
        <div style={{ fontWeight: 500, marginBottom: 8 }}>
          Cấu hình Lối sống AI & Thói quen
        </div>
        <div style={{ fontSize: "var(--text-sm)" }}>
          Tính năng đang được phát triển...
        </div>
      </div>
    </>
  );
}
