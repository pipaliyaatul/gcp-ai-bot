import React, { createContext, useState, useContext, useEffect } from 'react';

interface User {
  username?: string;
  email?: string;
  name?: string;
  credentials?: any;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (userData: User) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
const AUTH_TIMESTAMP_KEY = 'auth_timestamp';
const USER_KEY = 'user';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const isSessionValid = (): boolean => {
  const timestamp = localStorage.getItem(AUTH_TIMESTAMP_KEY);
  if (!timestamp) return false;
  
  const now = Date.now();
  const sessionTime = parseInt(timestamp, 10);
  const elapsed = now - sessionTime;
  
  return elapsed < SESSION_DURATION;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in and session is valid
    const checkAuth = () => {
      try {
        if (isSessionValid()) {
          const storedUser = localStorage.getItem(USER_KEY);
          if (storedUser) {
            try {
              const parsedUser = JSON.parse(storedUser);
              setIsAuthenticated(true);
              setUser(parsedUser);
            } catch (e) {
              console.error('Error parsing stored user data:', e);
              logout();
            }
          }
        } else {
          // Session expired, clear storage
          logout();
        }
      } catch (error) {
        console.error('Error checking authentication:', error);
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = (userData: User) => {
    setIsAuthenticated(true);
    setUser(userData);
    const timestamp = Date.now().toString();
    localStorage.setItem(AUTH_TIMESTAMP_KEY, timestamp);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUser(null);
    localStorage.removeItem(AUTH_TIMESTAMP_KEY);
    localStorage.removeItem(USER_KEY);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

