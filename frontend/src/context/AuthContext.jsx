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

  const register = async (userData) => {
    const response = await authAPI.register(userData);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    loading,
    login,
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
