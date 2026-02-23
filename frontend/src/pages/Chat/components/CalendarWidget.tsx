import { useState, useEffect } from "react";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import styles from "../ChatPage.module.css";
import { tasksService } from "../../../services/tasks.service";
import { useChatStore } from "../../../stores/chatStore";

export default function CalendarWidget() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [monthlyTasks, setMonthlyTasks] = useState<Record<string, string[]>>(
    {},
  );
  const needsWidgetRefresh = useChatStore((state) => state.needsWidgetRefresh);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const data = await tasksService.listTasks("pending");
        // Group tasks by date string (YYYY-MM-DD)
        const grouped: Record<string, string[]> = {};
        for (const t of data) {
          if (t.due_date) {
            const dateStr = new Date(t.due_date).toISOString().split("T")[0];
            if (!grouped[dateStr]) grouped[dateStr] = [];
            grouped[dateStr].push(t.title);
          }
        }
        setMonthlyTasks(grouped);
      } catch (err) {
        console.error("Failed to fetch tasks for calendar:", err);
      }
    };
    fetchTasks();
  }, [needsWidgetRefresh]);

  const prevMonth = () => {
    setCurrentDate(
      new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1),
    );
  };

  const nextMonth = () => {
    setCurrentDate(
      new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1),
    );
  };

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Get the first day of the month (0 = Sun, 1 = Mon, ... 6 = Sat)
  let firstDay = new Date(year, month, 1).getDay();
  // Adjust so Monday is 0, Sunday is 6
  firstDay = firstDay === 0 ? 6 : firstDay - 1;

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  const daysLabels = ["Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7", "CN"];
  const days = [];

  // Previous month padding
  for (let i = 0; i < firstDay; i++) {
    const day = daysInPrevMonth - firstDay + i + 1;
    days.push({
      date: day,
      isCurrentMonth: false,
      fullDate: `${month === 0 ? year - 1 : year}-${String(month === 0 ? 12 : month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
    });
  }

  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    days.push({
      date: i,
      isCurrentMonth: true,
      fullDate: `${year}-${String(month + 1).padStart(2, "0")}-${String(i).padStart(2, "0")}`,
    });
  }

  // Next month padding to complete the grid (usually 42 cells total for 6 rows)
  const remainingCells = 42 - days.length;
  for (let i = 1; i <= remainingCells; i++) {
    days.push({
      date: i,
      isCurrentMonth: false,
      fullDate: `${month === 11 ? year + 1 : year}-${String(month === 11 ? 1 : month + 2).padStart(2, "0")}-${String(i).padStart(2, "0")}`,
    });
  }

  const todayStr = new Date().toISOString().split("T")[0];

  return (
    <div className={`${styles.widget} glass-panel`}>
      <div className={styles.widgetHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Calendar size={16} className={styles.widgetIcon} />
          <h3 className={styles.widgetTitle}>
            Tháng {month + 1}, {year}
          </h3>
        </div>
        <div className={styles.calendarNav}>
          <button onClick={prevMonth} className={styles.calendarNavBtn}>
            <ChevronLeft size={16} />
          </button>
          <button onClick={nextMonth} className={styles.calendarNavBtn}>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      <div className={styles.calendarGrid}>
        {daysLabels.map((d) => (
          <div key={d} className={styles.calendarDayName}>
            {d}
          </div>
        ))}
        {days.map((d, idx) => {
          const tasks = monthlyTasks[d.fullDate];
          const isToday = d.fullDate === todayStr;

          return (
            <div
              key={idx}
              className={`${styles.calendarDate} ${
                d.isCurrentMonth ? "" : styles.calendarDateMuted
              } ${isToday ? styles.calendarDateActive : ""}`}
              title={tasks ? tasks.join(", ") : undefined}
            >
              <span>{d.date}</span>
              {tasks && <div className={styles.calendarTaskDot} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
