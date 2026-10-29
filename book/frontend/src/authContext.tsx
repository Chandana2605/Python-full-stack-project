
import React, { createContext, useContext, useEffect, useState } from "react";
import type { Role } from "./api";

interface AuthState {
  token: string | null;
  role: Role | null; // 'user' | 'admin'
}
interface AuthCtx extends AuthState {
  setAuth: (token: string | null, role: Role | null) => void;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({
  token: null, role: null, setAuth: () => {}, logout: () => {}
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("token");
    const r = localStorage.getItem("role") as Role | null;
    if (t) setToken(t);
    if (r) setRole(r);
  }, []);

  const setAuth = (t: string | null, r: Role | null) => {
    setToken(t); setRole(r);
    if (t) localStorage.setItem("token", t); else localStorage.removeItem("token");
    if (r) localStorage.setItem("role", r); else localStorage.removeItem("role");
  };

  const logout = () => setAuth(null, null);

  return <Ctx.Provider value={{ token, role, setAuth, logout }}>{children}</Ctx.Provider>;
};

export const useAuth = () => useContext(Ctx);

