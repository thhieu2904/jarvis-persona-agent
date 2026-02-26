import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 60000, // 60s for LLM calls
});

// ── JWT Helper: decode payload without library ──────────
function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp ?? null;
  } catch {
    return null;
  }
}

// Prevent multiple simultaneous refresh calls
let refreshPromise: Promise<string | null> | null = null;

async function refreshTokenIfNeeded(): Promise<string | null> {
  const token = localStorage.getItem("token");
  if (!token) return null;

  const exp = getTokenExpiry(token);
  if (!exp) return token;

  const now = Math.floor(Date.now() / 1000);
  const REFRESH_THRESHOLD = 30 * 60; // 30 minutes before expiry

  if (exp - now > REFRESH_THRESHOLD) return token; // Still fresh

  // Token about to expire — refresh it
  if (refreshPromise) return refreshPromise; // Already refreshing

  refreshPromise = (async () => {
    try {
      const res = await axios.post(
        `${API_BASE}/auth/refresh`,
        {},
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const newToken = res.data.access_token;
      if (newToken) {
        localStorage.setItem("token", newToken);
        if (res.data.user) {
          localStorage.setItem("user", JSON.stringify(res.data.user));
        }
        return newToken;
      }
    } catch {
      // Refresh failed — token will expire naturally, 401 handler catches it
    } finally {
      refreshPromise = null;
    }
    return token;
  })();

  return refreshPromise;
}

// Auto-attach JWT (with auto-refresh)
api.interceptors.request.use(async (config) => {
  const token = await refreshTokenIfNeeded();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);

export default api;
