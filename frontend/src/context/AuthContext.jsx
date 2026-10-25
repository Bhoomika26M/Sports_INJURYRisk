import { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/client';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = async () => {
    try {
      const res = await api.get('/users/me');
      setUser(res.data);
      return res.data;
    } catch (err) {
      if (err.response && (err.response.status === 401 || err.response.status === 403)) {
        localStorage.removeItem('token');
        setUser(null);
      }
      return null;
    }
  };

  useEffect(() => {
    // Attempt session restoration via HttpOnly cookie or Bearer token
    fetchCurrentUser().finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    
    localStorage.setItem('token', response.data.access_token);
    if (response.data.user) {
      setUser(response.data.user);
      return response.data.user;
    }
    return await fetchCurrentUser();
  };

  const loginOAuth = async ({ provider = 'google', email, full_name, role = 'athlete' }) => {
    const response = await api.post('/auth/oauth/login', {
      provider,
      email,
      full_name,
      role
    });
    
    localStorage.setItem('token', response.data.access_token);
    if (response.data.user) {
      setUser(response.data.user);
      return response.data.user;
    }
    return await fetchCurrentUser();
  };

  const loginGoogle = async (credential, role = 'athlete') => {
    const response = await api.post('/auth/google', {
      credential,
      role
    });
    
    localStorage.setItem('token', response.data.access_token);
    if (response.data.user) {
      setUser(response.data.user);
      return response.data.user;
    }
    return await fetchCurrentUser();
  };

  const register = async (userData) => {
    await api.post('/auth/register', userData);
    return await login(userData.email, userData.password);
  };

  const updateProfile = async (profileData) => {
    const res = await api.put('/users/me', profileData);
    setUser(res.data);
    return res.data;
  };

  const changePassword = async (currentPassword, newPassword) => {
    const res = await api.put('/users/me/password', {
      current_password: currentPassword,
      new_password: newPassword
    });
    return res.data;
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Continue client cleanup even if network request fails
    } finally {
      localStorage.removeItem('token');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      login,
      loginOAuth,
      loginGoogle,
      register,
      updateProfile,
      changePassword,
      logout,
      loading,
      refetchUser: fetchCurrentUser
    }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

