import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { apiClient } from './apiClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadFromCache = () => {
    try {
      const cached = localStorage.getItem('user');
      if (cached) {
        const parsed = JSON.parse(cached);
        setUser(parsed);
        setIsAuthenticated(true);
      }
    } catch {
      // ignore cache errors
    }
  };

  const validateAuth = useCallback(async () => {
    try {
      const data = await apiClient.get('/api/auth/check-auth/');
      if (data?.authenticated) {
        setIsAuthenticated(true);
        setUser(data.user || null);
        if (data.user) localStorage.setItem('user', JSON.stringify(data.user));
      } else {
        setIsAuthenticated(false);
        setUser(null);
        localStorage.removeItem('user');
      }
    } catch {
      // network error: do not escalate, keep existing state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFromCache();
    // initialize CSRF cookie once
    try {
      apiClient.get('/api/auth/csrf/');
    } catch {
      // ignore
    }
    validateAuth();

    const onFocus = () => validateAuth();
    const onVisibility = () => {
      if (document.visibilityState === 'visible') validateAuth();
    };

    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [validateAuth]);

  const logout = useCallback(() => {
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUser(null);
    window.location.href = '/';
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const data = await apiClient.get('/api/auth/current-user/');
      if (data) {
        setUser(data);
        localStorage.setItem('user', JSON.stringify(data));
      }
    } catch {
      // ignore errors here
    }
  }, []);

  const value = {
    user,
    isAuthenticated,
    loading,
    validateAuth,
    logout,
    refreshUser,
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}

