import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getMe,
  googleLogin as apiGoogleLogin,
  login as apiLogin,
  register as apiRegister,
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Fetch the current user when a token exists
  const fetchUser = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const userData = await getMe();
      setUser(userData);
    } catch {
      // Token is invalid / expired
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const establishSession = async (jwt, expectedRole) => {
    localStorage.setItem('token', jwt);
    setToken(jwt);
    try {
      const userData = await getMe();
      if (userData.role !== expectedRole) {
        throw new Error(`This account does not have ${expectedRole} access.`)
      }
      setUser(userData);
      return userData;
    } catch (error) {
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      throw error;
    }
  };

  const login = async (username, password, expectedRole = 'user') => {
    const data = await apiLogin(username, password, expectedRole);
    return establishSession(data.access_token, expectedRole);
  };

  const googleLogin = async (credential) => {
    const data = await apiGoogleLogin(credential);
    return establishSession(data.access_token, 'user');
  };

  const register = async (username, email, password) => {
    const data = await apiRegister(username, email, password);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';
  const isAnalyst = user?.role === 'analyst';

  return (
    <AuthContext.Provider value={{ user, token, login, googleLogin, register, logout, loading, isAdmin, isAnalyst }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
