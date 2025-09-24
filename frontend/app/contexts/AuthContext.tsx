import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

interface User {
  id: number;
  email: string;
  name: string;
  picture?: string;
  created_at: string;
  updated_at: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  refreshToken: () => Promise<void>;
  checkAuthStatus: () => Promise<void>;
  handleCallback: (code: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE_URL = 'https://a2a-estate-api-dev-301539410189.asia-northeast1.run.app';

  const saveTokens = (accessToken: string, refreshToken: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
    }
  };

  const getTokens = () => {
    if (typeof window === 'undefined') {
      return { accessToken: null, refreshToken: null };
    }
    return {
      accessToken: localStorage.getItem('access_token'),
      refreshToken: localStorage.getItem('refresh_token')
    };
  };

  const removeTokens = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  };

  const login = async () => {
    try {
      // Google認証URLを取得
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/google/url`);
      const data = await response.json();

      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const logout = async () => {
    try {
      const { accessToken } = getTokens();
      if (accessToken) {
        await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`
          }
        });
      }
      removeTokens();
      setUser(null);
      window.location.href = '/';
    } catch (error) {
      console.error('Logout failed:', error);
      removeTokens();
      setUser(null);
    }
  };

  const refreshToken = async () => {
    try {
      const tokens = getTokens();
      if (!tokens.refreshToken) {
        throw new Error('No refresh token');
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          refresh_token: tokens.refreshToken
        })
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      saveTokens(data.access_token, data.refresh_token);
    } catch (error) {
      console.error('Token refresh failed:', error);
      removeTokens();
      setUser(null);
    }
  };

  const handleCallback = async (code: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/google/callback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Auth callback failed:', errorText);
        throw new Error('Failed to authenticate');
      }

      const data = await response.json();
      console.log('Auth successful, saving tokens...');
      saveTokens(data.access_token, data.refresh_token);

      // トークン保存後すぐにユーザー情報を取得
      console.log('Fetching user info with new token...');
      const userResponse = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${data.access_token}`
        }
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        console.log('User data retrieved after login:', userData);
        setUser(userData);
        setIsLoading(false);
      } else {
        console.error('Failed to get user info after login');
        // フォールバックとしてcheckAuthStatusを呼ぶ
        await checkAuthStatus();
      }

      return data;
    } catch (error) {
      console.error('OAuth callback failed:', error);
      throw error;
    }
  };

  const checkAuthStatus = async () => {
    try {
      const { accessToken } = getTokens();
      if (!accessToken) {
        console.log('No access token found');
        setIsLoading(false);
        return;
      }

      console.log('Checking auth status with token...');
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });

      if (response.ok) {
        const userData = await response.json();
        console.log('User data retrieved:', userData);
        setUser(userData);
      } else if (response.status === 401) {
        console.log('Token expired, attempting refresh...');
        // トークンが無効な場合はリフレッシュを試みる
        await refreshToken();
        // リフレッシュ後に再度ユーザー情報を取得
        const retryResponse = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
          headers: {
            'Authorization': `Bearer ${getTokens().accessToken}`
          }
        });
        if (retryResponse.ok) {
          const userData = await retryResponse.json();
          console.log('User data retrieved after refresh:', userData);
          setUser(userData);
        } else {
          console.log('Failed to get user data after refresh');
          removeTokens();
          setUser(null);
        }
      } else {
        console.log('Auth check failed with status:', response.status);
        removeTokens();
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      removeTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  // 初期化時の認証状態確認
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // auth/callbackページでない場合のみ、認証状態を確認
      if (!window.location.pathname.includes('/auth/callback')) {
        checkAuthStatus();
      }
    }
  }, []);

  // 定期的にトークンをリフレッシュ
  useEffect(() => {
    if (user) {
      const interval = setInterval(() => {
        refreshToken();
      }, 30 * 60 * 1000); // 30分ごと

      return () => clearInterval(interval);
    }
  }, [user]);

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
      refreshToken,
      checkAuthStatus,
      handleCallback
    }}>
      {children}
    </AuthContext.Provider>
  );
};