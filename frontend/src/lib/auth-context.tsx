"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { apiClient } from "@/lib/api-client";
import { clearSessionHint, setSessionHint } from "@/lib/session-hint";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  google_id: string | null;
  avatar_url: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const token = await apiClient.refresh();
        if (token) {
          const userData = await apiClient.fetchWithAuth("/auth/me");
          setUser(userData);
          setSessionHint();
        } else {
          setUser(null);
          clearSessionHint();
        }
      } catch {
        setUser(null);
        clearSessionHint();
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, []);

  const login = (token: string, userData: User) => {
    apiClient.setToken(token);
    setUser(userData);
    setSessionHint();
  };

  const logout = () => {
    apiClient.setToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      clearSessionHint();
      window.location.href = "/login";
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}