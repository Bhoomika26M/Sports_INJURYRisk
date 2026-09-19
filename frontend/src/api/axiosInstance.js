/**
 * Axios instance pre-configured for the backend API.
 *
 * - Base URL reads from VITE_API_BASE_URL env var (falls back to localhost:8000)
 * - Authorization header is set/cleared by AuthContext
 * - Response interceptor: on 401, clear localStorage and redirect to /login
 */
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
});

// Response interceptor – handle global 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('sird_access_token');
      delete api.defaults.headers.common['Authorization'];
      // Avoid redirect loop if already on /login
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export default api;
