import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { api, getToken, setToken } from "../api/client";
import type { MeResponse } from "../api/types";

interface AuthState {
  me: MeResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  has: (cap: string) => boolean;
}

const AuthCtx = createContext<AuthState>(null as any);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    if (!getToken()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get<MeResponse>("/me");
      setMe(data);
    } catch {
      setToken(null);
      setMe(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMe();
  }, []);

  async function login(email: string, password: string) {
    const { data } = await api.post("/auth/login", { email, password });
    setToken(data.access_token);
    await loadMe();
  }

  function logout() {
    setToken(null);
    setMe(null);
  }

  const value = useMemo<AuthState>(
    () => ({
      me,
      loading,
      login,
      logout,
      has: (cap: string) => !!me?.capabilities.includes(cap),
    }),
    [me, loading],
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  return useContext(AuthCtx);
}
