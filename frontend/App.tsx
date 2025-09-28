import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import { useAppStore } from './src/stores/useAppStore';
import { authService } from './src/services/authService';

// Pages
import LoginPage from './src/pages/LoginPage';
import DashboardPage from './src/pages/DashboardPage';
import LoadingScreen from './src/components/ui/LoadingScreen';

// Styles
import 'react-toastify/dist/ReactToastify.css';
import './src/styles/globals.css';

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error: any) => {
        if (error?.code === 'AUTH_EXPIRED') return false;
        return failureCount < 3;
      }
    }
  }
});

function App() {
  const { user, setUser, setTheme, setSidebarCollapsed, theme } = useAppStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check authentication on app load
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (token) {
          const userData = await authService.getCurrentUserWithState();
          if (userData) {
            setUser(userData);

            // Apply user state if available
            if (userData.state?.preferences) {
              if (userData.state.preferences.theme) {
                setTheme(userData.state.preferences.theme);
              }
              if (typeof userData.state.preferences.sidebarWidth === 'number') {
                setSidebarCollapsed(userData.state.preferences.sidebarWidth <= 64);
              }
            }
          }
        }
      } catch (error) {
        console.error('Auth init failed:', error);
        localStorage.removeItem('auth_token');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, [setUser, setTheme, setSidebarCollapsed]);

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
          <Routes>
            <Route
              path="/login"
              element={user ? <Navigate to="/" replace /> : <LoginPage />}
            />
            <Route
              path="/*"
              element={user ? <DashboardPage /> : <Navigate to="/login" replace />}
            />
          </Routes>

          <ToastContainer
            position="top-right"
            theme={theme}
            closeOnClick
            pauseOnHover
            draggable
            newestOnTop
            hideProgressBar={false}
            autoClose={5000}
            className="mt-16"
          />
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;