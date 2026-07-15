/**
 * Auth token management for JWT-based authentication.
 * Handles storage of access/refresh tokens and provides helpers for auth state.
 */

const ACCESS_TOKEN_KEY = 'wimm_access_token';
const REFRESH_TOKEN_KEY = 'wimm_refresh_token';
const LEGACY_SESSION_KEY = 'wimm_session_token';

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface AuthUser {
  id: number;
  email: string | null;
  name: string;
  is_registered: boolean;
}

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getLegacySessionToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(LEGACY_SESSION_KEY);
}

export function storeTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearAuthTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(LEGACY_SESSION_KEY);
}

export function getActiveToken(): string | null {
  return getAccessToken() || getLegacySessionToken();
}

export function hasAuthTokens(): boolean {
  return !!(getAccessToken() || getLegacySessionToken());
}

export function isRegisteredUser(): boolean {
  return !!getAccessToken();
}
