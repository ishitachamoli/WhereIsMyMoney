'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { initSession, clearSession } from '@/lib/session';
import { AuthUser } from '@/lib/auth';
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

const PUBLIC_PATHS = ['/login', '/register'];

interface SessionContextValue {
  token: string | null;
  user: AuthUser | null;
  isReady: boolean;
  error: string | null;
  isRegistered: boolean;
  logout: () => void;
}

const SessionContext = createContext<SessionContextValue>({
  token: null,
  user: null,
  isReady: false,
  error: null,
  isRegistered: false,
  logout: () => {},
});

export function useSession() {
  return useContext(SessionContext);
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname?.startsWith(p));

  useEffect(() => {
    async function init() {
      try {
        const activeToken = await initSession();

        if (activeToken) {
          setToken(activeToken);

          // Fetch user info
          try {
            const res = await axios.get(`${API_BASE_URL}/api/v1/auth/me`, {
              headers: { Authorization: `Bearer ${activeToken}` },
            });
            setUser({
              id: res.data.user_id,
              email: res.data.email,
              name: res.data.name,
              is_registered: res.data.is_registered,
            });
          } catch {
            setUser(null);
          }

          // Redirect away from public pages if already authenticated
          if (isPublicPath) {
            router.replace('/dashboard');
            return;
          }
        } else {
          // Not authenticated
          if (!isPublicPath) {
            router.replace('/login');
            return;
          }
        }
      } catch (err) {
        console.error('Session initialization failed:', err);
        setError('Failed to initialize session');
        if (!isPublicPath) {
          router.replace('/login');
          return;
        }
      } finally {
        setIsReady(true);
      }
    }

    init();
  }, []);

  function logout() {
    clearSession();
    setToken(null);
    setUser(null);
    router.push('/login');
  }

  return (
    <SessionContext.Provider
      value={{
        token,
        user,
        isReady,
        error,
        isRegistered: user?.is_registered ?? false,
        logout,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}
