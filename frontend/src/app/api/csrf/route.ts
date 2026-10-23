import { NextRequest, NextResponse } from 'next/server';

const backend = process.env.DJANGO_URL ?? 'http://127.0.0.1:8000';

export async function GET(request: NextRequest) {
  const cookie = request.headers.get('cookie');
  const response = await fetch(`${backend}/api/csrf/`, {
    headers: cookie ? { cookie } : undefined,
    cache: 'no-store',
  });
  const headers = new Headers({ 'content-type': response.headers.get('content-type') ?? 'application/json' });
  for (const cookie of response.headers.getSetCookie()) headers.append('set-cookie', cookie);
  return new NextResponse(response.body, { status: response.status, headers });
}
