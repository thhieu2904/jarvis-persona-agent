export interface User {
  id: string;
  full_name: string;
  email: string;
  student_id?: string;
  avatar_url?: string;
  preferences: Record<string, unknown>;
  agent_config: Record<string, unknown>;
  created_at?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  full_name: string;
  email: string;
  password: string;
  student_id?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}
