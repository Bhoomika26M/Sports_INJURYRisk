import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Response interceptor for unified error formatting
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const customError = {
      message: error.response?.data?.detail || error.message || 'An unexpected error occurred',
      status: error.response?.status,
      data: error.response?.data,
    };
    return Promise.reject(customError);
  }
);

export const apiService = {
  // Health checks
  getHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  },
  getApiHealth: async () => {
    const response = await api.get('/api/v1/health');
    return response.data;
  },
  getRoot: async () => {
    const response = await api.get('/');
    return response.data;
  },
};

export default api;
