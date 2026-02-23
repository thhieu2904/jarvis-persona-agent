import { create } from "zustand";
import type { User } from "../types/auth";
import { authService } from "../services/auth.service";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (
    name: string,
    email: string,
    password: string,
    studentId?: string,
  ) => Promise<void>;
  updateAgentConfig: (config: Record<string, unknown>) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.login({ email, password });
      localStorage.setItem("token", res.access_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      set({ user: res.user, token: res.access_token, isLoading: false });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Đăng nhập thất bại";
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  register: async (name, email, password, studentId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.register({
        full_name: name,
        email,
        password,
        student_id: studentId,
      });
      localStorage.setItem("token", res.access_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      set({ user: res.user, token: res.access_token, isLoading: false });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Đăng ký thất bại";
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  updateAgentConfig: async (config) => {
    try {
      const updatedUser = await authService.updateAgentConfig(config);
      localStorage.setItem("user", JSON.stringify(updatedUser));
      set({ user: updatedUser });
    } catch (err: any) {
      console.error("Failed to update agent config:", err);
      // Optional: set error state if you want UI feedback
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({ user: null, token: null });
  },

  loadFromStorage: () => {
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        set({ user, token });
      } catch {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
      }
    }
  },

  clearError: () => set({ error: null }),
}));
