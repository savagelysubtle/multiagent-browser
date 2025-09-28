import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import { useAppStore } from './stores/useAppStore';
import { authService } from './services/authService';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import LoadingScreen from './components/ui/LoadingScreen';

// Styles
import 'react-toastify/dist/ReactToastify.css';
import './styles/globals.css';

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
  const { user, setUser, loadStateFromBackend, theme } = useAppStore();
  const [loading, setLoading] = useState(true);
  const [authChecking, setAuthChecking] = useState(false);

  useEffect(() => {
    // Check authentication on app load
    const initAuth = async () => {
      // Prevent multiple auth checks
      if (authChecking) return;

      setAuthChecking(true);
      try {
        const token = localStorage.getItem('auth_token');
        if (token) {
          const userData = await authService.getCurrentUser();
          if (userData) {
            setUser(userData);
            await loadStateFromBackend();
          }
        }
      } catch (error) {
        console.error('Auth init failed:', error);
        localStorage.removeItem('auth_token');
      } finally {
        setLoading(false);
        setAuthChecking(false);
      }
    };

    initAuth();
  }, [setUser, loadStateFromBackend]); // Remove authChecking from dependencies

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