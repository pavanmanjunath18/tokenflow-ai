"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi, CurrentUser } from "@/lib/api";
import { getToken, setToken, clearToken } from "@/lib/auth";

interface UserContextValue {
  user: CurrentUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: string[]) => boolean;
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }

    authApi.getCurrentUser()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const token = await authApi.login(email, password);
    setToken(token);
    const me = await authApi.getCurrentUser();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    window.location.href = "/login";
  }, []);

  const hasRole = useCallback((...roles: string[]) => {
    return user ? roles.includes(user.role) : false;
  }, [user]);

  return (
    <UserContext.Provider value={{ user, loading, isAuthenticated: !!user, login, logout, hasRole }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used inside UserProvider");
  return ctx;
}
