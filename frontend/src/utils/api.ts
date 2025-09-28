import axios, { AxiosError, AxiosResponse } from 'axios';
import { ApiError } from '../types';

// Create axios instance
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    // Handle authentication errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Clear invalid token
      localStorage.removeItem('auth_token');

      // Redirect to login
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // Transform error to our format
    const apiError: ApiError = {
      code: 'UNKNOWN_ERROR',
      message: 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
      retryable: false,
    };

    if (error.response?.data?.error) {
      const serverError = error.response.data.error;
      apiError.code = serverError.code || 'SERVER_ERROR';
      apiError.message = serverError.message || 'Server error occurred';
      apiError.field = serverError.field;
      apiError.timestamp = serverError.timestamp || apiError.timestamp;
      apiError.retryable = isRetryableError(apiError.code);
    } else if (!error.response) {
      apiError.code = 'NETWORK_ERROR';
      apiError.message = 'Network connection failed';
      apiError.retryable = true;
    }

    return Promise.reject(apiError);
  }
);

// Helper function to determine if an error is retryable
function isRetryableError(code: string): boolean {
  const retryableCodes = ['NETWORK_ERROR', 'TIMEOUT', 'RATE_LIMIT', 'SERVICE_UNAVAILABLE'];
  return retryableCodes.includes(code);
}

export default api;