// Client-side auth helpers
const TOKEN_KEY = "auth_token";

export const auth = {
  // Store token in localStorage
  setToken(token: string) {
    if (typeof window !== "undefined") {
      localStorage.setItem(TOKEN_KEY, token);
    }
  },

  // Get token from localStorage
  getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem(TOKEN_KEY);
    }
    return null;
  },

  // Remove token from localStorage
  removeToken() {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
    }
  },

  // Check if user is authenticated (token exists and not expired)
  isAuthenticated(): boolean {
    const token = this.getToken();
    if (!token) return false;
    const remaining = this.getTimeUntilExpiry();
    return remaining > 0;
  },

  // Decode JWT payload without verifying signature (client-side only)
  decodePayload(token: string): Record<string, unknown> | null {
    try {
      const parts = token.split(".");
      if (parts.length !== 3) return null;
      const payload = JSON.parse(atob(parts[1]));
      return payload;
    } catch {
      return null;
    }
  },

  // Get seconds until token expires (0 if expired or no token)
  getTimeUntilExpiry(): number {
    const token = this.getToken();
    if (!token) return 0;
    const payload = this.decodePayload(token);
    if (!payload || !payload.exp) return 0;
    const expiry = (payload.exp as number) * 1000; // convert to ms
    const remaining = expiry - Date.now();
    return Math.max(0, Math.floor(remaining / 1000));
  },

  // Check if token needs refresh (less than 10 minutes remaining)
  needsRefresh(): boolean {
    const remaining = this.getTimeUntilExpiry();
    return remaining > 0 && remaining < 600; // 10 minutes
  },
};
