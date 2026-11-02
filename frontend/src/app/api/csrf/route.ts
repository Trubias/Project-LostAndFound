import { NextRequest, NextResponse } from 'next/server';
import { getDjangoBackendUrl } from '@/lib/backend-url';

export async function GET(request: NextRequest) {
  try {
    const cookie = request.headers.get('cookie');
    const response = await fetch(`${getDjangoBackendUrl()}/api/csrf/`, {
      headers: cookie ? { cookie } : undefined,
      cache: 'no-store',
      signal: AbortSignal.timeout(8000),
    });
    const headers = new Headers({ 'content-type': response.headers.get('content-type') ?? 'application/json' });
    for (const cookie of response.headers.getSetCookie()) headers.append('set-cookie', cookie);
    return new NextResponse(response.body, { status: response.status, headers });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === 'TimeoutError';
    return NextResponse.json(
      { detail: timedOut ? 'The service took too long to respond. Please retry.' : 'The service is temporarily unavailable. Please retry.' },
      { status: timedOut ? 504 : 503 },
    );
  }
}
