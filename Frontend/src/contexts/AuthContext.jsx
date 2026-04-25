// src/contexts/AuthContext.jsx
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { getCurrentUserData, isAuthenticated, getCurrentUser, logoutUser as apiLogoutUser } from '../api';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const hasAuth = isAuthenticated(); // ✅ checks JWT expiry locally, no network call
        console.log('🔐 Auth check - hasAuth:', hasAuth);

        if (hasAuth) {
          const storedUser = getCurrentUserData();
          console.log('🔐 Stored user:', storedUser);

          // Set from localStorage immediately so UI isn't blocked
          if (storedUser) {
            setUser(storedUser);
          }

          // Try to refresh from API in background
          try {
            const userData = await getCurrentUser();
            console.log('🔐 Fresh user data from API:', userData);

            if (userData) {
              setUser(userData);
              localStorage.setItem('user', JSON.stringify(userData));
            }
          } catch (apiError) {
            console.warn('🔐 Could not fetch fresh user data:', apiError.message);

            if (apiError.status === 401) {
              // Token is rejected by backend — clear everything
              console.log('🔐 401 from /auth/me — clearing auth');
              localStorage.removeItem('auth_token');
              localStorage.removeItem('user');
              setUser(null);
            } else if (!storedUser) {
              // Network error and no cached user to fall back on
              console.log('🔐 Network error and no stored user — clearing auth');
              setUser(null);
            }
            // If it's a network error but we DO have storedUser,
            // keep them logged in with cached data — don't clear
          }
        } else {
          // Token missing or expired locally — clear any stale data
          console.log('🔐 No valid auth token found');
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
          setUser(null);
        }
      } catch (err) {
        console.error('🔐 Auth check error:', err);
        // Unexpected error — don't block the app
      } finally {
        console.log('🔐 Auth check complete, setting loading to false');
        setLoading(false);
      }
    };

    checkAuth();

    // Cross-tab logout support
    const handleStorageChange = (e) => {
      if (e.key === 'auth_token' || e.key === 'user') {
        console.log('🔐 Storage changed, rechecking auth');
        checkAuth();
      }
    };

    // Fired by axios interceptor on 401 (non-auth endpoints)
    const handleAuthExpired = () => {
      console.log('🔐 Auth expired event received');
      setUser(null);
      setError('Session expired. Please login again.');
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('auth_expired', handleAuthExpired);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('auth_expired', handleAuthExpired);
    };
  }, []);

  const login = useCallback((userData, token) => {
    try {
      console.log('🔐 Login called with user:', userData);
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      setError(null);
      return true;
    } catch (err) {
      console.error('🔐 Login storage error:', err);
      setError('Failed to save authentication data');
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      console.log('🔐 Logout initiated');
      await apiLogoutUser();
    } catch (err) {
      console.warn('🔐 Logout API call failed (continuing anyway):', err);
    } finally {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      setUser(null);
      setError(null);
      console.log('🔐 Logout complete');
    }
  }, []);

  const updateUser = useCallback((userData) => {
    try {
      console.log('🔐 Updating user:', userData);
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      return true;
    } catch (err) {
      console.error('🔐 Update user error:', err);
      setError('Failed to update user data');
      return false;
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      console.log('🔐 Refreshing user data');
      if (isAuthenticated()) {
        const userData = await getCurrentUser();
        if (userData) {
          updateUser(userData);
          return userData;
        }
      }
      return null;
    } catch (err) {
      console.error('🔐 Refresh user error:', err);
      return user; // Return current user if refresh fails
    }
  }, [updateUser, user]);

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    updateUser,
    refreshUser,
    clearError: () => setError(null),
  };

  console.log('🔐 AuthProvider rendering - user:', user?.email || 'none', 'loading:', loading);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
