import React, { createContext, useContext, useState } from "react";
import { apiFetch } from "../api/client";

interface AuthCtx {
  token: string | null;
  role: string | null;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
}
const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [role, setRole] = useState(localStorage.getItem("role"));
  async function login(u: string, p: string) {
    const r = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ username: u, password: p }) });
    localStorage.setItem("token", r.token);
    localStorage.setItem("role", r.role);
    setToken(r.token);
    setRole(r.role);
  }
  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    setToken(null);
    setRole(null);
  }
  return <Ctx.Provider value={{ token, role, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
