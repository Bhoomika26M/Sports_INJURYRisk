import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post('/api/v1/auth/register', data),
  login: (data) => api.post('/api/v1/auth/login', data),
  getMe: () => api.get('/api/v1/auth/me'),
};

export const athletesAPI = {
  getAll: (params) => api.get('/api/v1/athletes', { params }),
  getById: (id) => api.get(`/api/v1/athletes/${id}`),
  getMe: () => api.get('/api/v1/athletes/me'),
  create: (data) => api.post('/api/v1/athletes', data),
  update: (id, data) => api.put(`/api/v1/athletes/${id}`, data),
  delete: (id) => api.delete(`/api/v1/athletes/${id}`),
};

export const datasetsAPI = {
  getAll: () => api.get('/api/v1/datasets'),
};

export default api;
