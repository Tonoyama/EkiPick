import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';

export const GoogleLoginButton: React.FC = () => {
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    setIsLoading(true);
    try {
      await login();
    } catch (error) {
      console.error('Login error:', error);
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleLogin}
      disabled={isLoading}
      className="flex items-center justify-center gap-3 px-6 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow hover:shadow-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {/* Google Logo SVG */}
      <svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
        <path fill="none" d="M0 0h48v48H0z"/>
      </svg>

      {isLoading ? (
        <span className="text-gray-700 dark:text-gray-200">ログイン中...</span>
      ) : (
        <span className="text-gray-700 dark:text-gray-200 font-medium">Googleでログイン</span>
      )}
    </button>
  );
};

export const GoogleUserProfile: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();

  console.log('GoogleUserProfile - isAuthenticated:', isAuthenticated, 'user:', user);

  if (!isAuthenticated || !user) {
    return null;
  }

  return (
    <div className="flex items-center gap-3">
      {user.picture ? (
        <img
          src={user.picture}
          alt={user.name}
          className="w-8 h-8 rounded-full"
          onError={(e) => {
            console.error('Failed to load user picture:', user.picture);
            e.currentTarget.style.display = 'none';
          }}
        />
      ) : (
        <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {user.name?.charAt(0)?.toUpperCase() || '?'}
          </span>
        </div>
      )}
      <div className="flex flex-col">
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          {user.name || 'Unknown User'}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {user.email}
        </span>
      </div>
      <button
        onClick={logout}
        className="ml-2 px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded-md transition"
      >
        ログアウト
      </button>
    </div>
  );
};

export const AuthStatus: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();

  console.log('AuthStatus - isLoading:', isLoading, 'isAuthenticated:', isAuthenticated, 'user:', user);

  if (isLoading) {
    return (
      <div className="animate-pulse flex items-center gap-2">
        <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
        <div className="w-20 h-4 bg-gray-300 dark:bg-gray-600 rounded"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <GoogleUserProfile />;
  }

  return <GoogleLoginButton />;
};