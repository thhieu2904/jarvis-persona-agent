import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { useAuthStore } from "./stores/authStore";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/Login/LoginPage";
import RegisterPage from "./pages/Register/RegisterPage";
import ChatPage from "./pages/Chat/ChatPage";
import SettingsLayout from "./pages/Settings/SettingsLayout";
import ProfileSettingsPage from "./pages/Settings/ProfileSettingsPage";
import IoTManagementTab from "./pages/Settings/IoTManagementTab";
import SchedulerSettingsPage from "./pages/Settings/SchedulerSettingsPage";

export default function App() {
  const { loadFromStorage, token } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route
          path="/login"
          element={token ? <Navigate to="/" replace /> : <LoginPage />}
        />
        <Route
          path="/register"
          element={token ? <Navigate to="/" replace /> : <RegisterPage />}
        />

        {/* Protected */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          }
        />

        {/* Settings — nested routes */}
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="profile" replace />} />
          <Route path="profile" element={<ProfileSettingsPage />} />
          <Route path="iot" element={<IoTManagementTab />} />
          <Route path="scheduler" element={<SchedulerSettingsPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
