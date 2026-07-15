import axios from 'axios';
import {
  getAccessToken,
  getRefreshToken,
  getLegacySessionToken,
  storeTokens,
  clearAuthTokens,
  getActiveToken,
} from './auth';

const SESSION_KEY = 'wimm_session_token';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface SessionResponse {
  token: string;
  user_id: number;
  name: string;
}

interface MeResponse {
  user_id: number;
  name: string;
  email: string | null;
  is_active: boolean;
  is_registered: boolean;
}

interface RefreshResponse {
  access_token: string;
}

/**
 * Get the current active token (JWT access token or legacy session token).
 */
export function getSessionToken(): string | null {
  return getActiveToken();
}

/**
 * Initialize the session: validate existing JWT or legacy token.
 * Returns the active token or null if not authenticated.
 */
export async function initSession(): Promise<string | null> {
  const accessToken = getAccessToken();

  if (accessToken) {
    try {
      await axios.get<MeResponse>(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      return accessToken;
    } catch {
      // Access token expired — try refresh
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const res = await axios.post<RefreshResponse>(
            `${API_BASE_URL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken }
          );
          storeTokens({ access_token: res.data.access_token, refresh_token: refreshToken });
          return res.data.access_token;
        } catch {
          clearAuthTokens();
          return null;
        }
      }
      clearAuthTokens();
      return null;
    }
  }

  // Check for legacy session token
  const legacyToken = getLegacySessionToken();
  if (legacyToken) {
    try {
      await axios.get<MeResponse>(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${legacyToken}` },
      });
      return legacyToken;
    } catch {
      if (typeof window !== 'undefined') {
        localStorage.removeItem(SESSION_KEY);
      }
      return null;
    }
  }

  return null;
}

/**
 * Create a new anonymous session (legacy flow, for backward compat).
 */
export async function createAnonymousSession(): Promise<string> {
  const response = await axios.post<SessionResponse>(
    `${API_BASE_URL}/api/v1/auth/session`,
    { token: null }
  );
  const { token } = response.data;
  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_KEY, token);
  }
  return token;
}

/**
 * Clear all auth state (for logout).
 */
export function clearSession(): void {
  clearAuthTokens();
}
