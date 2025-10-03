import axios from 'axios';
import { toast } from 'react-toastify';

// Get API URL from environment variables (set by PowerShell script)
// Support both Vite and React environment variable formats
const API_URL = import.meta.env.VITE_API_URL ||
                process.env.REACT_APP_API_URL ||
                'http://localhost:8000';

// Create axios instance with base configuration
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
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
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Extract error details
    const errorData = error.response?.data?.error || error.response?.data || {};

    // Create user-friendly error message
    let errorMessage = 'An unexpected error occurred';

    if (error.response) {
      // Server responded with error
      if (errorData.message) {
        errorMessage = errorData.message;
      } else if (error.response.status === 401) {
        errorMessage = 'Authentication required';
        // Clear invalid token
        localStorage.removeItem('auth_token');
        // Redirect to login if not already there
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      } else if (error.response.status === 422) {
        errorMessage = errorData.message || 'Invalid input data';
        // Include field errors if available
        if (errorData.details?.field_errors) {
          const fieldErrors = errorData.details.field_errors
            .map((e: any) => `${e.field}: ${e.message}`)
            .join(', ');
          errorMessage = `${errorMessage} (${fieldErrors})`;
        }
      }
    } else if (error.request) {
      // Request made but no response
      errorMessage = 'Unable to connect to server. Please check your connection.';
    }

    // Return a properly formatted error
    const formattedError = {
      code: errorData.code || 'UNKNOWN_ERROR',
      message: errorMessage,
      timestamp: errorData.timestamp || new Date().toISOString(),
      retryable: error.response?.status >= 500 || !error.response,
      field: errorData.details?.field || undefined,
    };

    return Promise.reject(formattedError);
  }
);

// Export the API URL for debugging
export const getApiUrl = () => API_URL;

// WebSocket URL helper
export const getWebSocketUrl = () => {
  const wsUrl = import.meta.env.VITE_WS_URL ||
                process.env.REACT_APP_WS_URL ||
                API_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws';
  return wsUrl;
};