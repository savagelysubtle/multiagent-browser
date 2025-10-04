import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAppStore } from '../stores/useAppStore';
import { authService } from '../services/authService';
import { LoginRequest, RegisterRequest } from '../../types';
import { getApiUrl } from '../utils/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
  });

  const { setUser, setTheme, setSidebarCollapsed } = useAppStore();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      let response;
      if (isLogin) {
        const loginData: LoginRequest = {
          email: formData.email,
          password: formData.password,
        };
        response = await authService.login(loginData);
      } else {
        const registerData: RegisterRequest = {
          email: formData.email,
          password: formData.password,
          name: formData.name || undefined,
        };
        response = await authService.register(registerData);
      }

      // Set user first
      setUser(response.user);
      console.log('User set in store:', response.user);

      // Apply user state if it exists
      if (response.user.state) {
        const userState = response.user.state;
        console.log('Applying user state:', userState);

        // Apply preferences
        if (userState.preferences) {
          if (userState.preferences.theme) {
            setTheme(userState.preferences.theme);
          }
          if (typeof userState.preferences.sidebarWidth === 'number') {
            setSidebarCollapsed(userState.preferences.sidebarWidth <= 64);
          }
        }
      }

      toast.success(`${isLogin ? 'Login' : 'Registration'} successful!`);
      console.log('Login successful, redirecting to dashboard');

      // Navigate to dashboard after successful login
      navigate('/', { replace: true });
    } catch (error: any) {
      console.error('Auth error:', error);
      toast.error(error.message || `${isLogin ? 'Login' : 'Registration'} failed`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearUsers = async () => {
    if (process.env.NODE_ENV !== 'development') {
      toast.error('This feature is only available in development mode.');
      return;
    }

    try {
      const response = await fetch(`${getApiUrl()}/api/auth/dev/clear-users`, {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message);
      } else {
        const text = await response.text();
        throw new Error(`Server responded with ${response.status}: ${text}`);
      }
    } catch (error: any) {
      console.error('Clear users error:', error);
      toast.error(error.message || 'An unexpected error occurred.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-gray-100">
            {isLogin ? 'Sign in to your account' : 'Create your account'}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            {isLogin ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="font-medium text-primary hover:text-primary/80 transition-colors"
            >
              {isLogin ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm space-y-4">
            {!isLogin && (
              <div>
                <label htmlFor="name" className="sr-only">
                  Name
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  autoComplete="name"
                  className="input"
                  placeholder="Full name (optional)"
                  value={formData.name}
                  onChange={handleInputChange}
                />
              </div>
            )}
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="input"
                placeholder="Email address"
                value={formData.email}
                onChange={handleInputChange}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                required
                className="input"
                placeholder="Password"
                value={formData.password}
                onChange={handleInputChange}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary btn-md w-full"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {isLogin ? 'Signing in...' : 'Creating account...'}
                </div>
              ) : (
                isLogin ? 'Sign in' : 'Create account'
              )}
            </button>
          </div>

          <div className="text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              By continuing, you agree to our terms of service and privacy policy.
            </p>
          </div>
        </form>

        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4">
            <button
              type="button"
              onClick={handleClearUsers}
              className="btn btn-danger btn-sm w-full"
            >
              Clear Users (Dev only)
            </button>
          </div>
        )}

        {/* Debug section for API connection */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 p-4 bg-gray-800 rounded-lg text-xs text-gray-400">
            <h4 className="font-semibold mb-2">Debug Info:</h4>
            <p>API URL: {import.meta.env.VITE_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000'}</p>
            <p>Actual API URL being used: {getApiUrl()}</p>
            <p>Environment: {process.env.NODE_ENV}</p>
            <p>Admin Email: admin@localhost</p>
            <p>Admin Password: admin123</p>
          </div>
        )}
      </div>
    </div>
  );
}