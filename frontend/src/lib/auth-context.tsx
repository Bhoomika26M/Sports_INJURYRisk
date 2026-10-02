"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, apiClient } from "@/lib/api-client";
import { setSessionHint } from "@/lib/session";
import type { Role, User } from "@/lib/types";

const SESSION_KEY = ["session"] as const;

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<User>;
  signUp: (input: { email: string; password: string; full_name: string; role: Role }) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function restoreSession(): Promise<User | null> {
  if (!apiClient.canRestoreSession()) return null; // nothing to restore — skip a pointless 401
  const token = await apiClient.refresh();
  if (!token) {
    setSessionHint(false);
    return null;
  }
  try {
    return await api.get<User>("/auth/me");
  } catch {
    setSessionHint(false);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const router = useRouter();

  const session = useQuery({
    queryKey: SESSION_KEY,
    queryFn: restoreSession,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: false,
    refetchOnWindowFocus: false,
  });

  /** Drop everything cached for the previous user, but keep the session entry itself. */
  const resetCache = useCallback(
    (user: User | null) => {
      queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== SESSION_KEY[0] });
      queryClient.setQueryData(SESSION_KEY, user);
    },
    [queryClient],
  );

  // If a refresh ever fails mid-session, send the person back to sign in (and bring them back after).
  useEffect(() => {
    apiClient.setSessionExpiredHandler(() => {
      apiClient.setToken(null);
      resetCache(null);
      const here = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(here)}`);
    });
    return () => apiClient.setSessionExpiredHandler(null);
  }, [resetCache, router]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.post<{ access_token: string }>("/auth/login", { email, password });
      apiClient.setToken(access_token);
      const user = await api.get<User>("/auth/me");
      setSessionHint(true);
      resetCache(user);
      return user;
    },
    [resetCache],
  );

  const signUp = useCallback<AuthContextType["signUp"]>(
    async (input) => {
      await api.post("/auth/register", input);
      return signIn(input.email, input.password);
    },
    [signIn],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout"); // revokes the refresh token and clears the httpOnly cookie
    } catch {
      /* even if the server is unreachable, end the session locally */
    }
    apiClient.setToken(null);
    setSessionHint(false);
    resetCache(null);
    router.replace("/login");
  }, [resetCache, router]);

  const value = useMemo<AuthContextType>(
    () => ({ user: session.data ?? null, loading: session.isPending, signIn, signUp, logout }),
    [session.data, session.isPending, signIn, signUp, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
