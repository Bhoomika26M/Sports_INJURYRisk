/**
 * AuthContext
 *
 * Stores the JWT access token + decoded user info in memory (React state)
 * and persists the access token in localStorage so the session survives
 * a page refresh.
 *
 * Provided values:
 *   user          – { id, email, full_name, role, is_active, ... } | null
 *   token         – raw JWT string | null
 *   login(data)   – call with { access_token, refresh_token } from /auth/login
 *   logout()      – clear state + localStorage
 *   isLoading     – true while the initial token hydration is running
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api from '../api/axiosInstance';

const AuthContext = createContext(null);

const TOKEN_KEY = 'sird_access_token';

function decodePayload(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: restore token from localStorage, then fetch /auth/me
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setIsLoading(false);
      return;
    }
    // Check expiry before attempting the request
    const payload = decodePayload(stored);
    if (!payload || payload.exp * 1000 < Date.now()) {
      localStorage.removeItem(TOKEN_KEY);
      setIsLoading(false);
      return;
    }
    setToken(stored);
    api.defaults.headers.common['Authorization'] = `Bearer ${stored}`;
    api.get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (tokenData) => {
    const { access_token } = tokenData;
    localStorage.setItem(TOKEN_KEY, access_token);
    api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setToken(access_token);
    const res = await api.get('/auth/me');
    setUser(res.data);
    return res.data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    delete api.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
