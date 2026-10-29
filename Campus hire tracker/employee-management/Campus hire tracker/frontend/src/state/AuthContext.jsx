import { createContext, useContext, useEffect, useState } from "react";

import { api } from "../utils/api";

const STORAGE_KEY = "campus-hire-tracker-auth";

const AuthContext = createContext(null);

function readStoredSession() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readStoredSession);

  useEffect(() => {
    if (session) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
      return;
    }
    window.localStorage.removeItem(STORAGE_KEY);
  }, [session]);

  async function login(credentials) {
    const payload = await api.login(credentials);
    setSession(payload);
    return payload;
  }

  async function changePassword(payload) {
    if (!session?.access_token) {
      throw new Error("Not authenticated");
    }

    await api.changePassword(session.access_token, payload);
    setSession((current) =>
      current
        ? {
            ...current,
            must_change_password: false
          }
        : current
    );
  }

  function logout() {
    setSession(null);
  }

  const value = {
    session,
    user: session
      ? {
          id: session.user_id,
          email: session.email,
          role: session.role,
          mustChangePassword: session.must_change_password
        }
      : null,
    accessToken: session?.access_token ?? null,
    login,
    changePassword,
    logout,
    isAuthenticated: Boolean(session)
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
