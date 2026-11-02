import { cookies } from 'next/headers';
import { getDjangoBackendUrl } from './backend-url';

export type DjangoSession = {
  authenticated: boolean;
  available: boolean;
  name?: string;
  username?: string;
  avatar?: string | null;
  dashboard?: string;
  isAdmin?: boolean;
};

export async function getDjangoSession(): Promise<DjangoSession> {
  try {
    const cookieHeader = (await cookies()).toString();
    const response = await fetch(`${getDjangoBackendUrl()}/api/session/`, {
      headers: cookieHeader ? { cookie: cookieHeader } : undefined,
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) return { ...await response.json() as DjangoSession, available: true };
  } catch {
    // The header remains usable, but callers can distinguish an outage from sign-out.
  }
  return { authenticated: false, available: false };
}
