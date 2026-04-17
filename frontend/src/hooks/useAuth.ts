import { useState, useEffect, useCallback } from 'react';
import { apiLogin, apiLogout, apiCheckSession, fetchCsrfToken } from '@/api';
import type { AuthUser } from '@/api';

interface UseAuthReturn {
  user: AuthUser | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check existing session on mount
  useEffect(() => {
    (async () => {
      try {
        await fetchCsrfToken();
        const u = await apiCheckSession();
        setUser(u);
      } catch {
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setError(null);
    try {
      await fetchCsrfToken();
      const u = await apiLogin(email, password);
      setUser(u);
      return true;
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const resp = (err as { response?: { data?: { error?: string } } }).response;
        setError(resp?.data?.error ?? 'Login failed');
      } else {
        setError('Unable to connect to server');
      }
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  return { user, isLoading, error, login, logout };
}
