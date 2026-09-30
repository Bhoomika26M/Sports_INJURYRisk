"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "./api-client";

type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (access_token: string, user_data: User) => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const token = await apiClient.refresh();
        if (token) {
          const userData = await apiClient.fetchWithAuth("/auth/me");
          setUser(userData);
        } else {
          setUser(null);
          apiClient.setToken(null);
          if (typeof document !== "undefined") {
            document.cookie = "refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT; Max-Age=0";
          }
        }
      } catch (err) {
        setUser(null);
        apiClient.setToken(null);
        if (typeof document !== "undefined") {
          document.cookie = "refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT; Max-Age=0";
        }
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, []);

  const login = (access_token: string, user_data: User) => {
    apiClient.setToken(access_token);
    setUser(user_data);
    
    // Cookie approach for middleware sync — just an indicator flag since 
    // the real refresh token is httpOnly
    document.cookie = `refresh_token=present; path=/; max-age=604800; SameSite=Lax`; 
    
    router.push("/dashboard");
  };

  const logout = async () => {
    try {
      await apiClient.fetchWithAuth("/auth/logout", { method: "POST" });
    } catch (err) {
      console.error("Logout failed:", err);
    } finally {
      apiClient.setToken(null);
      document.cookie = "refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
      setUser(null);
      router.push("/login");
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
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
