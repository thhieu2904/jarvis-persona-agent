import CalendarWidget from "./CalendarWidget";
import TasksWidget from "./TasksWidget";
import NotesListWidget from "./NotesListWidget";
import styles from "../ChatPage.module.css";

export default function FeaturePanel() {
  return (
    <aside className={styles.featurePanel}>
      <div className={styles.featurePanelContent}>
        <CalendarWidget />
        <TasksWidget />
        <NotesListWidget />
      </div>
    </aside>
  );
}
