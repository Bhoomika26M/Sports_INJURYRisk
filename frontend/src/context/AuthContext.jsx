import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');
      
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
        
        // Verify token is still valid
        try {
          const response = await authAPI.getMe();
          setUser(response.data);
          localStorage.setItem('user', JSON.stringify(response.data));
        } catch (error) {
          logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email, password) => {
    const response = await authAPI.login({ email, password });
    const { access_token } = response.data;
    
    // Store token first
    localStorage.setItem('token', access_token);
    setToken(access_token);
    
    // Get user info with the token
    const userResponse = await authAPI.getMe();
    const userData = userResponse.data;
    
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    
    return userData;
  };

  const completeLogin = async (accessToken) => {
    // Shared by password login and federated (Google) sign-in.
    localStorage.setItem('token', accessToken);
    setToken(accessToken);

    const userResponse = await authAPI.getMe();
    const userData = userResponse.data;

    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);

    return userData;
  };

  const loginWithGoogle = async (code, state) => {
    const response = await authAPI.googleExchange({ code, state });
    const { access_token } = response.data;
    return completeLogin(access_token);
  };

  const startGoogleLogin = async (next) => {
    // Ask the backend for the consent-screen URL (keeps client id server-side)
    // then hand the browser over to Google.
    const response = await authAPI.googleAuthorizeUrl(next);
    const { authorization_url } = response.data;
    window.location.href = authorization_url;
  };

  const register = async (userData) => {
    const response = await authAPI.register(userData);
    return response.data;
  };

  const logout = async () => {
    try {
      // Call backend logout to revoke session
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local state
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setToken(null);
      setUser(null);
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    loginWithGoogle,
    startGoogleLogin,
    completeLogin,
    register,
    logout,
    isAuthenticated: !!token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
