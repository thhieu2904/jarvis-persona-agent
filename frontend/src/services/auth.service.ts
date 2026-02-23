import api from "./api";
import type {
  LoginRequest,
  RegisterRequest,
  LoginResponse,
  User,
} from "../types/auth";

export const authService = {
  async login(data: LoginRequest): Promise<LoginResponse> {
    const res = await api.post<LoginResponse>("/auth/login", data);
    return res.data;
  },

  async register(data: RegisterRequest): Promise<LoginResponse> {
    const res = await api.post<LoginResponse>("/auth/register", data);
    return res.data;
  },

  async getProfile(): Promise<User> {
    const res = await api.get<User>("/auth/profile");
    return res.data;
  },

  async updateProfile(data: Partial<User>): Promise<User> {
    const res = await api.put<User>("/auth/profile", data);
    return res.data;
  },

  async updateAgentConfig(config: Record<string, unknown>): Promise<User> {
    const res = await api.put<User>("/auth/profile", { agent_config: config });
    return res.data;
  },

  async saveSchoolCredentials(mssv: string, password: string) {
    const res = await api.put("/academic/credentials", { mssv, password });
    return res.data;
  },
};
