import { cookies } from 'next/headers';

export type DjangoSession = {
  authenticated: boolean;
  name?: string;
  username?: string;
  avatar?: string | null;
  dashboard?: string;
  isAdmin?: boolean;
};

export async function getDjangoSession(): Promise<DjangoSession> {
  const backend = process.env.DJANGO_URL ?? 'http://127.0.0.1:8000';
  try {
    const cookieHeader = (await cookies()).toString();
    const response = await fetch(`${backend}/api/session/`, {
      headers: cookieHeader ? { cookie: cookieHeader } : undefined,
      cache: 'no-store',
    });
    if (response.ok) return await response.json() as DjangoSession;
  } catch {
    // Keep the public header usable if Django is temporarily unavailable.
  }
  return { authenticated: false };
}
